from types import SimpleNamespace

import pytest

from mlsc.app import create_app
from mlsc.webserver.blueprints.authentication_executer import AuthenticationExecuter
from mlsc.webserver.executer import Executer
from mlsc.webserver.webserver import register_api_blueprints

pytestmark = pytest.mark.integration

PIN = "1234"
NEW_PIN = "5678"
PROTECTED = "/api/v2/devices"
V2_PIN = "/api/v2/auth/pin"
V1_PIN = "/api/auth/pin"


@pytest.fixture
def executer(tmp_path, monkeypatch):
    real = AuthenticationExecuter.__new__(AuthenticationExecuter)
    real.default_values = {"DEFAULT_PIN": "", "USE_PIN_LOCK": False}
    real.config = __import__("configparser").ConfigParser()
    real.config_path = tmp_path / "security.ini"
    real.config_values = real.read_config()
    real.USER_PIN = real.config_values["DEFAULT_PIN"]
    real.IS_PIN_ACTIVE = real.config_values["USE_PIN_LOCK"]
    facade = SimpleNamespace(
        authentication_executer=real,
        device_executer=SimpleNamespace(get_devices=list),
    )
    monkeypatch.setattr(Executer, "instance", facade, raising=False)
    return real


@pytest.fixture
def app(executer):
    app = create_app()
    executer.add_server_authentication(app)
    register_api_blueprints(app)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def enable_lock(client, pin=PIN):
    return client.put(V2_PIN, json={"default_pin": pin, "use_pin_lock": True})


def test_enabling_the_lock_blocks_an_unauthenticated_client_without_a_restart(app, client):
    assert client.get(PROTECTED).status_code == 200

    assert enable_lock(client).status_code == 200

    assert app.test_client().get(PROTECTED).status_code == 401


def test_the_saving_session_stays_authenticated(client):
    enable_lock(client)

    assert client.get(PROTECTED).status_code == 200


def test_a_new_pin_is_accepted_at_login(app, client):
    enable_lock(client)
    other = app.test_client()
    assert other.post("/api/v2/auth/login", json={"pin": NEW_PIN}).status_code == 401

    enable_lock(client, NEW_PIN)

    assert other.post("/api/v2/auth/login", json={"pin": PIN}).status_code == 401
    assert other.post("/api/v2/auth/login", json={"pin": NEW_PIN}).status_code == 200
    assert other.get(PROTECTED).status_code == 200


@pytest.mark.parametrize("disable", [
    lambda client: client.put(V2_PIN, json={"default_pin": PIN, "use_pin_lock": False}),
    lambda client: client.delete(V2_PIN),
    lambda client: client.post(V1_PIN, json={"DEFAULT_PIN": PIN, "USE_PIN_LOCK": False}),
    lambda client: client.delete(V1_PIN),
])
def test_disabling_or_resetting_the_lock_opens_access_again(app, client, disable):
    enable_lock(client)
    assert app.test_client().get(PROTECTED).status_code == 401

    assert disable(client).status_code == 200

    assert app.test_client().get(PROTECTED).status_code == 200


def test_the_legacy_endpoint_applies_the_lock_immediately(app, client):
    assert client.post(V1_PIN, json={"DEFAULT_PIN": PIN, "USE_PIN_LOCK": True}).status_code == 200

    assert app.test_client().get(PROTECTED).status_code == 401
    assert client.get(PROTECTED).status_code == 200


def test_an_old_session_cookie_is_rejected_after_the_lock_is_re_enabled(app):
    stale = app.test_client()
    assert stale.post("/api/v2/auth/login", json={}).status_code == 200  # Lock off: login just opens a session.
    admin = app.test_client()
    enable_lock(admin)
    assert admin.put(V2_PIN, json={"default_pin": PIN, "use_pin_lock": False}).status_code == 200
    assert stale.get(PROTECTED).status_code == 200

    enable_lock(admin)

    assert stale.get(PROTECTED).status_code == 401
    assert admin.get(PROTECTED).status_code == 200


def test_the_legacy_endpoint_rejects_an_invalid_pin_before_locking(app, client):
    assert client.post(V1_PIN, json={"DEFAULT_PIN": "ab", "USE_PIN_LOCK": True}).status_code == 400

    assert app.test_client().get(PROTECTED).status_code == 200
