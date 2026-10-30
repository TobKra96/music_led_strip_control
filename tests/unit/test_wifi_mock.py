import pytest

from mlsc.diagnosis import Status
from mlsc.wifi import MockNetwork, MockWifiManager, WifiError

pytestmark = pytest.mark.unit

HOME = MockNetwork("Home", signal=80, security="WPA2", password="secret123")  # ruff: ignore[hardcoded-password-func-arg]
CAFE = MockNetwork("Cafe", signal=40, security=None)


def test_scan_lists_the_networks_and_marks_the_known_and_connected_one():
    wifi = MockWifiManager(networks=[HOME, CAFE])
    wifi.connect("Home", "secret123")

    networks = {network.ssid: network for network in wifi.scan()}

    assert networks["Home"].in_use is True
    assert networks["Home"].known is True
    assert networks["Home"].security == "WPA2"
    assert networks["Cafe"].in_use is False
    assert networks["Cafe"].known is False
    assert networks["Cafe"].security is None


def test_connect_with_the_right_password_makes_the_status_a_connected_client():
    wifi = MockWifiManager(networks=[HOME])

    wifi.connect("Home", "secret123")

    status = wifi.status()
    assert (status.mode, status.connected, status.ssid) == ("client", True, "Home")
    assert status.ip is not None


def test_connect_with_a_wrong_password_fails_and_stays_disconnected():
    wifi = MockWifiManager(networks=[HOME])

    with pytest.raises(WifiError, match="password"):
        wifi.connect("Home", "wrong")

    assert wifi.status().connected is False


def test_connect_to_an_unknown_ssid_fails():
    with pytest.raises(WifiError, match="Nowhere"):
        MockWifiManager(networks=[HOME]).connect("Nowhere", "x")


def test_connect_to_an_open_network_needs_no_password():
    wifi = MockWifiManager(networks=[CAFE])

    wifi.connect("Cafe", None)

    assert wifi.status().ssid == "Cafe"


def test_a_scripted_connect_failure_wins_over_a_correct_password():
    wifi = MockWifiManager(networks=[HOME], failing_connects={"Home"})

    with pytest.raises(WifiError):
        wifi.connect("Home", "secret123")


def test_forget_removes_the_saved_network_and_drops_its_connection():
    wifi = MockWifiManager(networks=[HOME])
    wifi.connect("Home", "secret123")

    wifi.forget("Home")

    assert wifi.status().connected is False
    assert not any(network.known for network in wifi.scan())


def test_forget_of_an_unsaved_network_fails():
    with pytest.raises(WifiError):
        MockWifiManager(networks=[HOME]).forget("Home")


def test_hotspot_start_switches_the_mode_and_exposes_the_credentials_and_stop_returns_to_client():
    wifi = MockWifiManager(networks=[HOME])
    wifi.connect("Home", "secret123")

    wifi.start_hotspot("MLSC-ab12", "hotspotpw")

    status = wifi.status()
    assert (status.mode, status.connected) == ("hotspot", False)
    assert (status.hotspot.ssid, status.hotspot.password) == ("MLSC-ab12", "hotspotpw")

    wifi.stop_hotspot()

    assert wifi.status().mode == "client"
    assert wifi.status().hotspot is None


def test_hotspot_without_a_password_gets_a_generated_one():
    wifi = MockWifiManager()

    wifi.start_hotspot(None, None)

    assert wifi.status().hotspot.ssid
    assert len(wifi.status().hotspot.password) >= 8


def test_hotspot_fails_when_the_adapter_has_no_access_point_support():
    wifi = MockWifiManager(hotspot_supported=False)

    with pytest.raises(WifiError, match="Hotspot"):
        wifi.start_hotspot("x", "12345678")

    assert wifi.capabilities().hotspot is False


def test_unsupported_manager_reports_it_and_refuses_changes():
    wifi = MockWifiManager(supported=False)

    assert wifi.capabilities().supported is False
    assert wifi.scan() == []
    with pytest.raises(WifiError, match="not supported"):
        wifi.connect("Home", "x")


def test_capabilities_report_the_country():
    assert MockWifiManager(country="DE").capabilities().country == "DE"
    assert MockWifiManager(country=None).capabilities().country is None


@pytest.mark.parametrize(("kwargs", "status", "fragment"), [
    ({}, Status.OK, "ready"),
    ({"supported": False}, Status.WARNING, "NetworkManager"),
    ({"hotspot_supported": False}, Status.WARNING, "Hotspot"),
    ({"country": None}, Status.WARNING, "country"),
])
def test_diagnose_uses_the_shared_diagnosis(kwargs, status, fragment):
    diagnosis = MockWifiManager(**kwargs).diagnose()

    assert diagnosis.status is status
    assert fragment in diagnosis.message
