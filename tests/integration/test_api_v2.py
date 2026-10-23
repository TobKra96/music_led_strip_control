from types import SimpleNamespace

import pytest

from mlsc.api.v2 import register_api_v2
from mlsc.app import create_app
from mlsc.webserver import auth, sse
from mlsc.webserver.executer import Executer
from mlsc.webserver.sse import EventBroker

pytestmark = pytest.mark.integration

PIN = "1234"
PROBLEM_JSON = "application/problem+json"
JSON = {"Content-Type": "application/json"}


class FakeAuthenticationExecuter:
    USER_PIN = PIN

    def __init__(self, enabled=True) -> None:
        self.enabled = enabled
        self.pin_config = {"DEFAULT_PIN": PIN, "USE_PIN_LOCK": True}

    def is_pin_active(self):
        return self.enabled

    @staticmethod
    def validate_pin(pin):
        return 4 <= len(pin) <= 8 and pin.isdigit()

    @staticmethod
    def login():
        auth.login_user()

    def get_pin_setting(self):
        return self.pin_config

    def set_pin_setting(self, data):
        self.pin_config = data

    def reset_pin_settings(self):
        self.pin_config = {"DEFAULT_PIN": "", "USE_PIN_LOCK": False}
        return self.pin_config


def build_app(auth_enabled=True, clock=None):
    app = create_app()
    app.config["AUTH_ENABLED"] = auth_enabled
    app.secret_key = "test"  # ruff: ignore[hardcoded-password-string]
    register_api_v2(app, **({"clock": clock} if clock else {}))
    return app


@pytest.fixture(autouse=True)  # ruff: ignore[pytest-fixture-autouse]
def fake_executer(monkeypatch):
    executer = SimpleNamespace(
        authentication_executer=FakeAuthenticationExecuter(),
        device_executer=SimpleNamespace(
            get_devices=lambda: [{"name": "Desk", "id": "device_0", "assigned_to": {}}],
        ),
        system_info_executer=SimpleNamespace(get_system_version=lambda: {"versions": [{"name": "mlsc", "version": "3.0.0"}]}),
    )
    monkeypatch.setattr(Executer, "instance", executer, raising=False)
    return executer


@pytest.fixture
def client():
    return build_app().test_client()


def log_in(client, pin=PIN):
    return client.post("/api/v2/auth/login", json={"pin": pin})


def assert_problem(response, status, code):
    assert response.status_code == status
    assert response.mimetype == PROBLEM_JSON
    body = response.get_json()
    assert body["status"] == status
    assert body["code"] == code
    assert body["title"]
    assert "type" in body
    return body


def test_unauthenticated_call_gets_json_401_not_a_redirect(client):
    assert_problem(client.get("/api/v2/devices"), 401, "Unauthorized")


def test_login_opens_the_api_and_logout_closes_it(client):
    response = log_in(client)
    assert response.status_code == 200
    assert response.get_json() == {"authenticated": True, "pin_required": True}

    assert client.get("/api/v2/devices").status_code == 200

    assert client.post("/api/v2/auth/logout", json={}).status_code == 204
    assert_problem(client.get("/api/v2/devices"), 401, "Unauthorized")


def test_wrong_pin_is_rejected_with_problem_json(client):
    assert_problem(log_in(client, "9999"), 401, "InvalidPin")
    assert_problem(client.get("/api/v2/devices"), 401, "Unauthorized")


def test_api_is_open_when_no_pin_is_active():
    client = build_app(auth_enabled=False).test_client()

    assert client.get("/api/v2/devices").status_code == 200
    assert client.get("/api/v2/auth/session").get_json() == {"authenticated": False, "pin_required": False}


def test_session_reports_login_state(client):
    assert client.get("/api/v2/auth/session").get_json() == {"authenticated": False, "pin_required": True}

    log_in(client)

    assert client.get("/api/v2/auth/session").get_json() == {"authenticated": True, "pin_required": True}


@pytest.mark.parametrize("method", ["post", "put", "patch"])
def test_writes_must_be_json(client, method):
    response = getattr(client, method)("/api/v2/auth/login", data={"pin": PIN})

    assert_problem(response, 415, "UnsupportedMediaType")


def test_session_cookie_is_same_site_lax(client):
    cookie = log_in(client).headers["Set-Cookie"]

    assert "SameSite=Lax" in cookie


def test_validation_errors_list_the_bad_fields(client):
    response = client.post("/api/v2/auth/login", json={})

    body = assert_problem(response, 422, "ValidationError")
    assert body["errors"][0]["field"] == "pin"
    assert body["errors"][0]["detail"]


def test_malformed_json_is_a_400_problem(client):
    response = client.post("/api/v2/auth/login", data="{nope", headers=JSON)

    assert_problem(response, 400, "BadRequest")


def test_unknown_v2_path_is_a_404_problem(client):
    assert_problem(client.get("/api/v2/nope"), 404, "NotFound")


def test_wrong_method_is_a_405_problem(client):
    log_in(client)

    assert_problem(client.delete("/api/v2/devices"), 405, "MethodNotAllowed")


def test_missing_resource_raises_a_coded_problem(client):
    log_in(client)

    body = assert_problem(client.get("/api/v2/devices/device_9"), 404, "DeviceNotFound")
    assert body["detail"] == "Device does not exist."


def test_unexpected_errors_are_a_500_problem(client, fake_executer):
    def boom():
        msg = "boom"
        raise RuntimeError(msg)

    fake_executer.device_executer.get_devices = boom
    log_in(client)
    client.application.testing = False
    client.application.config["PROPAGATE_EXCEPTIONS"] = False

    body = assert_problem(client.get("/api/v2/devices"), 500, "ServerError")
    assert "boom" not in str(body)


def test_v1_errors_keep_their_old_shape(client):
    response = client.get("/api/does-not-exist")

    assert response.mimetype == "application/json"
    assert response.get_json()["message_id"] == "NotFound"


def test_login_is_throttled_with_backoff_after_repeated_failures():
    now = [100.0]
    client = build_app(clock=lambda: now[0]).test_client()

    for _ in range(5):
        assert_problem(log_in(client, "9999"), 401, "InvalidPin")

    throttled = log_in(client, PIN)
    assert_problem(throttled, 429, "TooManyAttempts")
    assert int(throttled.headers["Retry-After"]) >= 1

    now[0] += int(throttled.headers["Retry-After"])
    assert log_in(client, PIN).status_code == 200


def test_pin_endpoints_read_write_and_reset(client, fake_executer):
    assert_problem(client.get("/api/v2/auth/pin"), 401, "Unauthorized")
    log_in(client)

    assert client.get("/api/v2/auth/pin").get_json() == {"default_pin": PIN, "use_pin_lock": True}

    response = client.put("/api/v2/auth/pin", json={"default_pin": "5678", "use_pin_lock": False})
    assert response.get_json() == {"default_pin": "5678", "use_pin_lock": False}
    assert fake_executer.authentication_executer.pin_config == {"DEFAULT_PIN": "5678", "USE_PIN_LOCK": False}

    assert_problem(client.put("/api/v2/auth/pin", json={"default_pin": "12", "use_pin_lock": True}), 422, "ValidationError")

    assert client.delete("/api/v2/auth/pin").get_json() == {"default_pin": "", "use_pin_lock": False}


def test_resources_call_executers(client):
    log_in(client)

    assert client.get("/api/v2/devices").get_json() == [{"id": "device_0", "name": "Desk", "assigned_to": {}}]
    assert client.get("/api/v2/devices/device_0").get_json()["name"] == "Desk"
    assert client.get("/api/v2/system/version").get_json() == {"versions": [{"name": "mlsc", "version": "3.0.0"}]}


def read_events(stream, count):
    return [next(stream).decode() for _ in range(count)]


def test_events_require_login_and_answer_with_a_json_401(client):
    assert_problem(client.get("/api/v2/events"), 401, "Unauthorized")


def test_events_replay_missed_low_rate_events_after_last_event_id(client, monkeypatch):
    local = EventBroker()
    monkeypatch.setattr(sse, "broker", local)
    log_in(client)
    local.publish("operation", {"id": "a", "state": "pending"})
    local.publish("mic.level", {"level": 3})
    local.publish("operation", {"id": "a", "state": "confirmed"})

    response = client.get("/api/v2/events", headers={"Last-Event-ID": "1"})
    chunks = read_events(response.response, 2)

    assert chunks[0].startswith("event: ready")
    assert chunks[1] == 'id: 2\nevent: operation\ndata: {"id": "a", "state": "confirmed"}\n\n'
    response.close()


def test_events_without_last_event_id_skip_history(client, monkeypatch):
    local = EventBroker()
    monkeypatch.setattr(sse, "broker", local)
    log_in(client)
    local.publish("operation", {"state": "pending"})

    response = client.get("/api/v2/events")
    local.publish("wifi.state", {"mode": "hotspot"})
    chunks = read_events(response.response, 2)

    assert chunks[1] == 'id: 2\nevent: wifi.state\ndata: {"mode": "hotspot"}\n\n'
    response.close()


def test_continuous_events_carry_no_id(client, monkeypatch):
    local = EventBroker()
    monkeypatch.setattr(sse, "broker", local)
    log_in(client)

    response = client.get("/api/v2/events")
    local.publish("mic.level", {"level": 3})

    assert read_events(response.response, 2)[1] == 'event: mic.level\ndata: {"level": 3}\n\n'
    response.close()


def test_events_beyond_the_stream_limit_get_a_503_problem(client, monkeypatch):
    monkeypatch.setattr(sse, "broker", EventBroker(max_subscribers=1))
    log_in(client)

    first = client.get("/api/v2/events")
    second = client.get("/api/v2/events")

    assert first.status_code == 200
    assert_problem(second, 503, "TooManyStreams")
    first.close()
