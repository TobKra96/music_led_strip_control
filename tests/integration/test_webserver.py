import http.client
import re
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
import waitress

from mlsc import app as app_package
from mlsc.app import create_app
from mlsc.webserver import auth, sse
from mlsc.webserver.blueprints.authentication_executer import AuthenticationExecuter
from mlsc.webserver.executer import Executer
from mlsc.webserver.sse import EventBroker
from mlsc.webserver.webserver import register_api_blueprints

pytestmark = pytest.mark.integration

PIN = "1234"
PROTECTED_URLS = ("/api/resources/colors", "/dashboard")
REMOTE_ASSET = re.compile(r"""<(?:script|link|img)\s[^>]*(?:src|href)\s*=\s*["'](?:https?:)?//|url\(\s*["']?(?:https?:)?//""")


class FakeAuthenticationExecuter:
    USER_PIN = PIN

    def __init__(self, enabled) -> None:
        self.enabled = enabled

    def is_pin_active(self):
        return self.enabled

    @staticmethod
    def validate_pin(pin):
        return len(pin) >= 4

    @staticmethod
    def login():
        auth.login_user()

    @staticmethod
    def is_safe_url(target):
        return target.startswith("/")

    @staticmethod
    def get_pin_setting():
        return {"DEFAULT_PIN": PIN, "USE_PIN_LOCK": True}


def build_app(auth_enabled):
    app = create_app()
    app.config["AUTH_ENABLED"] = auth_enabled
    app.secret_key = "test"  # ruff: ignore[hardcoded-password-string]
    register_api_blueprints(app)
    return app


@pytest.fixture(autouse=True)  # ruff: ignore[pytest-fixture-autouse]
def fake_executer(monkeypatch):
    executer = SimpleNamespace(
        authentication_executer=FakeAuthenticationExecuter(enabled=True),
        general_executer=SimpleNamespace(get_colors=lambda: {"red": "red"}),
        device_executer=SimpleNamespace(get_devices=dict, get_assigned_groups=dict),
    )
    monkeypatch.setattr(Executer, "instance", executer, raising=False)
    return executer


@pytest.fixture
def client():
    return build_app(auth_enabled=True).test_client()


def log_in(client):
    return client.post("/login", data={"pin": PIN})


def test_api_is_open_when_auth_is_disabled():
    response = build_app(auth_enabled=False).test_client().get("/api/resources/colors")

    assert response.status_code == 200
    assert response.get_json() == {"red": "red"}


@pytest.mark.parametrize("url", PROTECTED_URLS)
def test_protected_urls_redirect_to_login_without_session(client, url):
    response = client.get(url)

    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login")


def test_pin_login_opens_protected_urls_and_logout_closes_them(client):
    assert log_in(client).status_code == 302
    assert client.get("/api/resources/colors").status_code == 200

    client.get("/logout")

    assert client.get("/api/resources/colors").status_code == 302


def test_wrong_pin_does_not_log_in(client):
    client.post("/login", data={"pin": "9999"})

    assert client.get("/api/resources/colors").status_code == 302


def test_login_returns_to_the_page_that_asked_for_it(client):
    client.get("/dashboard")

    response = log_in(client)

    assert response.headers["Location"] == "/dashboard"


def test_pin_setting_requires_login_only_when_a_pin_is_active(client, fake_executer):
    assert client.get("/api/auth/pin").status_code == 401

    log_in(client)
    assert client.get("/api/auth/pin").get_json() == {"DEFAULT_PIN": PIN, "USE_PIN_LOCK": True}

    fake_executer.authentication_executer.enabled = False
    assert build_app(auth_enabled=False).test_client().get("/api/auth/pin").status_code == 200


def test_api_errors_stay_json_and_pages_render_html(client):
    api_error = client.get("/api/does-not-exist")
    page_error = client.get("/does-not-exist")

    assert api_error.is_json
    assert page_error.status_code == 404
    assert not page_error.is_json


def test_spec_documents_the_existing_api():
    spec = build_app(auth_enabled=False).test_client().get("/openapi.json").get_json()

    assert spec["info"]["title"] == "MLSC API"
    colors = spec["paths"]["/api/resources/colors"]["get"]
    assert colors["summary"] == "Return colors"
    assert "200" in colors["responses"]
    assert "requestBody" in spec["paths"]["/api/system/devices"]["delete"]
    assert spec["paths"]["/api/settings/microphone/volume"]["get"]["deprecated"] is True
    assert "/api/v2/events" not in spec["paths"]


def test_api_docs_page_loads_bundled_swagger_ui():
    response = build_app(auth_enabled=False).test_client().get("/api/")

    assert response.status_code == 200
    assert "/static/assets/plugins/swagger-ui/js/swagger-ui-bundle.js" in response.get_data(as_text=True)


def test_front_end_assets_are_bundled():
    package = Path(app_package.__file__).parent
    files = [*(package / "templates").rglob("*.html"), *(package / "static" / "assets" / "css").glob("*.css")]

    offenders = [path.name for path in files if REMOTE_ASSET.search(path.read_text(encoding="utf-8"))]

    assert offenders == []


class WaitressServer:
    def __init__(self, app) -> None:
        self._server = waitress.create_server(app, host="127.0.0.1", port=0, threads=8)
        self.port = self._server.effective_port
        self._thread = threading.Thread(target=self._server.run, daemon=True)

    def __enter__(self):  # ruff: ignore[missing-return-type-special-method]
        self._thread.start()
        return self

    def __exit__(self, *_) -> None:
        self._server.close()
        self._thread.join(timeout=5)

    def connect(self):
        return http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)


def read_event(response):
    """Read one SSE event (up to its blank line) from the de-chunked response body."""
    lines = []
    while (line := response.readline().decode()) != "\n":
        lines.append(line.rstrip("\n"))
    return "\n".join(lines)


def test_events_stream_under_waitress_alongside_normal_requests():
    with WaitressServer(build_app(auth_enabled=False)) as server:
        stream = server.connect()
        stream.request("GET", "/api/v2/events")
        response = stream.getresponse()
        assert response.status == 200
        assert response.getheader("Content-Type").startswith("text/event-stream")
        assert read_event(response).startswith("event: ready")

        sse.broker.publish("meter", {"level": 3})
        assert read_event(response) == 'event: meter\ndata: {"level": 3}'

        other = server.connect()
        other.request("GET", "/api/resources/colors")
        assert other.getresponse().status == 200
        stream.close()


def test_events_stream_requires_login_under_waitress():
    with WaitressServer(build_app(auth_enabled=True)) as server:
        connection = server.connect()
        connection.request("GET", "/api/v2/events")

        assert connection.getresponse().status == 401


def test_broker_drops_events_for_a_stalled_client_instead_of_blocking():
    local = EventBroker()
    subscriber = local.subscribe()

    for _ in range(sse.SUBSCRIBER_BACKLOG * 2):
        local.publish("tick", 1)

    assert subscriber.qsize() == subscriber.maxsize


def test_stream_sends_keepalive_and_unsubscribes_on_close():
    local = EventBroker(max_subscribers=1)
    subscriber = local.subscribe()
    stream = local.stream(subscriber, keepalive=0.01)

    assert next(stream).startswith("event: ready")
    assert next(stream) == ": keepalive\n\n"
    stream.close()

    assert local.subscribe() is not None


def test_stream_ends_and_unsubscribes_when_the_session_is_no_longer_valid():
    local = EventBroker(max_subscribers=1)
    subscriber = local.subscribe()
    valid = [True]
    stream = local.stream(subscriber, keepalive=0.01, is_valid=lambda: valid[0], recheck_seconds=0)

    assert next(stream).startswith("event: ready")
    assert next(stream) == ": keepalive\n\n"
    valid[0] = False

    assert list(stream) == []
    assert local.subscribe() is not None


def test_stream_rechecks_the_session_even_while_events_keep_flowing():
    local = EventBroker()
    subscriber = local.subscribe()
    valid = [True]
    stream = local.stream(subscriber, keepalive=60, is_valid=lambda: valid[0], recheck_seconds=0)

    next(stream)
    local.publish("mic.level", {"level": 1})
    assert next(stream).startswith("event: mic.level")
    valid[0] = False
    local.publish("mic.level", {"level": 2})

    assert list(stream) == []


@pytest.mark.parametrize("pin_lock", [True, False])
def test_server_authentication_follows_the_pin_lock_setting(pin_lock):
    executer = AuthenticationExecuter.__new__(AuthenticationExecuter)
    executer.USER_PIN = PIN
    executer.IS_PIN_ACTIVE = pin_lock
    server = create_app()

    executer.add_server_authentication(server)

    assert server.config["AUTH_ENABLED"] is pin_lock
    assert server.secret_key


def test_server_authentication_rejects_an_invalid_pin_while_locked():
    executer = AuthenticationExecuter.__new__(AuthenticationExecuter)
    executer.USER_PIN = "12"
    executer.IS_PIN_ACTIVE = True

    with pytest.raises(ValueError, match="4 to 8 digits"):
        executer.add_server_authentication(create_app())


def test_pages_render_with_a_link_to_the_bundled_api_docs(client):
    log_in(client)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert 'href="/api/"' in response.get_data(as_text=True)
