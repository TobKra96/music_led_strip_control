from types import SimpleNamespace

import pytest

from mlsc.api.v2 import register_api_v2
from mlsc.app import create_app
from mlsc.webserver.executer import Executer
from mlsc.wifi import MockNetwork, MockWifiManager

pytestmark = pytest.mark.integration

HOME = MockNetwork("Home", signal=80, security="WPA2", password="secret123")  # ruff: ignore[hardcoded-password-func-arg]
CAFE = MockNetwork("Cafe", signal=40, security=None)


def make_client(wifi, monkeypatch, *, auth_enabled=False):
    monkeypatch.setattr(Executer, "instance", SimpleNamespace(wifi_manager=wifi), raising=False)
    app = create_app()
    app.config["AUTH_ENABLED"] = auth_enabled
    app.secret_key = "test"  # ruff: ignore[hardcoded-password-string]
    register_api_v2(app)
    return app.test_client()


@pytest.fixture
def wifi():
    return MockWifiManager(networks=[HOME, CAFE])


@pytest.fixture
def client(wifi, monkeypatch):
    return make_client(wifi, monkeypatch)


def test_status_of_a_disconnected_host_reports_the_capabilities(client):
    body = client.get("/api/v2/wifi/status").get_json()

    assert body == {
        "supported": True, "hotspot_supported": True, "country": "DE",
        "mode": "client", "connected": False, "ssid": None, "ip": None, "hotspot": None,
    }


def test_scan_lists_the_networks(client):
    networks = client.get("/api/v2/wifi/scan").get_json()["networks"]

    assert {n["ssid"]: (n["signal"], n["security"], n["in_use"], n["known"]) for n in networks} == {
        "Home": (80, "WPA2", False, False), "Cafe": (40, None, False, False),
    }


def test_connect_joins_the_network_and_the_status_follows(client):
    response = client.post("/api/v2/wifi/connect", json={"ssid": "Home", "password": "secret123"})

    assert response.status_code == 200
    assert response.get_json()["ssid"] == "Home"
    assert client.get("/api/v2/wifi/status").get_json()["connected"] is True


def test_connect_with_a_wrong_password_is_a_problem_that_does_not_echo_it(client):
    response = client.post("/api/v2/wifi/connect", json={"ssid": "Home", "password": "wrong-pw"})

    assert response.status_code == 422
    assert response.mimetype == "application/problem+json"
    assert response.get_json()["code"] == "WifiChangeFailed"
    assert "wrong-pw" not in response.get_data(as_text=True)


def test_the_password_of_a_saved_network_is_never_returned(client):
    client.post("/api/v2/wifi/connect", json={"ssid": "Home", "password": "secret123"})

    for path in ("status", "scan"):
        assert "secret123" not in client.get(f"/api/v2/wifi/{path}").get_data(as_text=True)


def test_forget_removes_a_saved_network(client):
    client.post("/api/v2/wifi/connect", json={"ssid": "Home", "password": "secret123"})

    assert client.post("/api/v2/wifi/forget", json={"ssid": "Home"}).status_code == 204
    assert client.get("/api/v2/wifi/status").get_json()["connected"] is False


def test_forget_of_an_unsaved_network_is_a_problem(client):
    assert client.post("/api/v2/wifi/forget", json={"ssid": "Home"}).status_code == 422


def test_hotspot_on_returns_its_credentials_and_off_drops_it(client):
    on = client.put("/api/v2/wifi/hotspot", json={"enabled": True, "ssid": "MLSC-ab12", "password": "hotspotpw"})

    assert on.status_code == 200
    assert on.get_json()["mode"] == "hotspot"
    assert on.get_json()["hotspot"] == {"ssid": "MLSC-ab12", "password": "hotspotpw"}

    off = client.put("/api/v2/wifi/hotspot", json={"enabled": False})

    assert off.get_json()["mode"] == "client"
    assert off.get_json()["hotspot"] is None


def test_hotspot_without_adapter_support_is_a_problem(monkeypatch):
    client = make_client(MockWifiManager(hotspot_supported=False), monkeypatch)

    response = client.put("/api/v2/wifi/hotspot", json={"enabled": True})

    assert response.status_code == 422
    assert "Hotspot" in response.get_json()["detail"]


def test_an_unsupported_host_reports_it_in_the_status_and_refuses_changes_with_a_503(monkeypatch):
    client = make_client(MockWifiManager(supported=False), monkeypatch)

    assert client.get("/api/v2/wifi/status").get_json()["supported"] is False
    assert client.get("/api/v2/wifi/scan").status_code == 503
    response = client.post("/api/v2/wifi/connect", json={"ssid": "Home", "password": "x"})
    assert response.status_code == 503
    assert response.get_json()["code"] == "WifiUnsupported"


def test_an_empty_ssid_is_a_validation_error(client):
    response = client.post("/api/v2/wifi/connect", json={"ssid": ""})

    assert response.status_code == 422
    assert response.get_json()["errors"][0]["field"] == "ssid"


def test_every_endpoint_needs_a_login_session_while_auth_is_on(wifi, monkeypatch):
    client = make_client(wifi, monkeypatch, auth_enabled=True)

    requests = [
        client.get("/api/v2/wifi/status"),
        client.get("/api/v2/wifi/scan"),
        client.post("/api/v2/wifi/connect", json={"ssid": "Home"}),
        client.post("/api/v2/wifi/forget", json={"ssid": "Home"}),
        client.put("/api/v2/wifi/hotspot", json={"enabled": True}),
    ]

    assert [response.status_code for response in requests] == [401] * 5
    assert wifi.status().mode == "client"


def test_the_endpoints_are_open_while_auth_is_off(client):
    assert client.get("/api/v2/wifi/status").status_code == 200
