from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from mlsc.api.v2 import register_api_v2
from mlsc.app import create_app
from mlsc.webserver.executer import Executer
from mlsc.wifi import CLIENT, MockNetwork, MockWifiManager
from mlsc.wifi.credentials import HotspotCredentials
from mlsc.wifi.supervisor import WifiSupervisor

pytestmark = pytest.mark.integration

HOME = MockNetwork("Home", signal=80, security="WPA2", password="secret123")  # ruff: ignore[hardcoded-password-func-arg]
CAFE = MockNetwork("Cafe", signal=40, security=None)


@dataclass
class Settings:
    mode: str = CLIENT
    setup_fallback: bool = True


def make_client(wifi, monkeypatch, *, auth_enabled=False):
    supervisor = WifiSupervisor(wifi, Settings(), lambda: 0.0, lambda: False, HotspotCredentials(None, lambda: None))
    monkeypatch.setattr(Executer, "instance", SimpleNamespace(wifi_manager=wifi, wifi_supervisor=supervisor), raising=False)
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
        "supported": True, "hotspot_supported": True, "country": "DE", "interface": "wlan0", "radio": "ready",
        "diagnosis": {"status": "ok", "message": "Wi-Fi is ready (country DE).", "suggested_fix": None},
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
        client.put("/api/v2/wifi/radio", json={"enabled": True}),
    ]

    assert [response.status_code for response in requests] == [401] * 6
    assert wifi.status().mode == "client"


def test_the_endpoints_are_open_while_auth_is_off(client):
    assert client.get("/api/v2/wifi/status").status_code == 200


def test_the_status_of_a_switched_off_radio_carries_the_diagnosis_for_the_banner(monkeypatch):
    client = make_client(MockWifiManager(networks=[HOME], radio="switched_off"), monkeypatch)

    body = client.get("/api/v2/wifi/status").get_json()

    assert body["radio"] == "switched_off"
    assert body["diagnosis"] == {"status": "warning", "message": "Wi-Fi is switched off.",
                                 "suggested_fix": "Turn it on from the Wi-Fi page, or run: sudo nmcli radio wifi on"}


def test_a_missing_pinned_adapter_is_reported_with_its_name(monkeypatch):
    client = make_client(MockWifiManager(pinned_interface="wlan1"), monkeypatch)

    body = client.get("/api/v2/wifi/status").get_json()

    assert (body["interface"], body["radio"]) == ("wlan1", "no_adapter")
    assert body["diagnosis"]["message"] == "The configured Wi-Fi adapter wlan1 was not found."


def test_changes_while_the_radio_is_not_ready_fail_with_the_message_of_its_state(monkeypatch):
    client = make_client(MockWifiManager(networks=[HOME], radio="blocked"), monkeypatch)

    responses = [
        client.post("/api/v2/wifi/connect", json={"ssid": "Home", "password": "secret123"}),
        client.post("/api/v2/wifi/forget", json={"ssid": "Home"}),
        client.put("/api/v2/wifi/hotspot", json={"enabled": True}),
    ]

    assert [r.status_code for r in responses] == [422] * 3
    assert all("hardware switch" in r.get_json()["detail"] for r in responses)


def test_put_radio_switches_a_switched_off_radio_on_and_returns_the_status(monkeypatch):
    client = make_client(MockWifiManager(radio="switched_off"), monkeypatch)

    response = client.put("/api/v2/wifi/radio", json={"enabled": True})

    assert response.status_code == 200
    assert response.get_json()["radio"] == "ready"


def test_put_radio_is_refused_from_other_states(monkeypatch):
    client = make_client(MockWifiManager(radio="blocked"), monkeypatch)

    response = client.put("/api/v2/wifi/radio", json={"enabled": True})

    assert response.status_code == 422
    assert "hardware switch" in response.get_json()["detail"]


def test_put_radio_cannot_switch_the_radio_off(monkeypatch):
    client = make_client(MockWifiManager(), monkeypatch)

    assert client.put("/api/v2/wifi/radio", json={"enabled": False}).status_code == 422


def test_put_radio_reports_a_radio_that_stays_unusable(monkeypatch):
    client = make_client(MockWifiManager(radio="switched_off", radio_stuck=True), monkeypatch)

    assert client.put("/api/v2/wifi/radio", json={"enabled": True}).status_code == 422


def test_put_radio_on_an_unsupported_host_is_a_503(monkeypatch):
    client = make_client(MockWifiManager(supported=False), monkeypatch)

    assert client.put("/api/v2/wifi/radio", json={"enabled": True}).status_code == 503


def test_the_wifi_settings_page_renders_with_its_script_and_a_menu_entry(wifi, monkeypatch):
    client = make_client(wifi, monkeypatch)
    client.application.add_url_rule("/logout", "authentication_api.logout", lambda: "")  # The sidebar links to the v1 logout.
    monkeypatch.setattr(Executer.instance, "device_executer", SimpleNamespace(get_devices=dict, get_groups=dict, get_assigned_groups=dict), raising=False)

    response = client.get("/settings/wifi_settings")

    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "assets/js/settings.wifi.js" in page
    assert 'href="/settings/wifi_settings"' in page
