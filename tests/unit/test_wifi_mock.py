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


def test_the_mock_reports_wlan0_as_its_adapter_and_is_ready():
    capabilities = MockWifiManager().capabilities()

    assert (capabilities.interface, capabilities.radio) == ("wlan0", "ready")


def test_a_pinned_adapter_that_does_not_exist_is_no_adapter_and_names_the_pin():
    wifi = MockWifiManager(pinned_interface="wlan1")

    capabilities = wifi.capabilities()
    diagnosis = wifi.diagnose()

    assert (capabilities.radio, capabilities.interface) == ("no_adapter", "wlan1")
    assert diagnosis.status is Status.WARNING
    assert diagnosis.message == "The configured Wi-Fi adapter wlan1 was not found."


@pytest.mark.parametrize(("radio", "message", "fix"), [
    ("no_adapter", "No Wi-Fi adapter was found.", "Plug in a Wi-Fi adapter, or manage the network yourself."),
    ("blocked", "Wi-Fi is blocked by a hardware switch.", "Switch the hardware Wi-Fi switch on."),
    ("switched_off", "Wi-Fi is switched off.", "Turn it on from the Wi-Fi page, or run: sudo nmcli radio wifi on"),
    ("unavailable", "The Wi-Fi adapter wlan0 is not available.", "Check the adapter's driver and firmware (dmesg | grep -i wlan)."),
])
def test_every_radio_state_but_ready_is_a_warning_with_the_agreed_wording(radio, message, fix):
    diagnosis = MockWifiManager(radio=radio).diagnose()

    assert (diagnosis.status, diagnosis.message, diagnosis.suggested_fix) == (Status.WARNING, message, fix)


def test_a_radio_that_is_not_ready_beats_the_hotspot_and_country_warnings():
    diagnosis = MockWifiManager(radio="switched_off", hotspot_supported=False, country=None).diagnose()

    assert diagnosis.message == "Wi-Fi is switched off."


def test_changes_fail_up_front_with_the_message_of_the_radio_state():
    wifi = MockWifiManager(networks=[HOME], radio="blocked")

    with pytest.raises(WifiError, match="hardware switch"):
        wifi.require_ready()


def test_enable_radio_brings_a_switched_off_radio_to_ready():
    wifi = MockWifiManager(radio="switched_off")

    wifi.enable_radio()

    assert wifi.capabilities().radio == "ready"


def test_enable_radio_refuses_other_states_with_their_message():
    with pytest.raises(WifiError, match="hardware switch"):
        MockWifiManager(radio="blocked").enable_radio()


def test_enable_radio_fails_when_the_radio_stays_unusable():
    wifi = MockWifiManager(radio="switched_off", radio_stuck=True)

    with pytest.raises(WifiError):
        wifi.enable_radio()


def test_enable_radio_is_refused_for_a_missing_pinned_adapter_even_when_the_radio_is_off():
    wifi = MockWifiManager(radio="switched_off", pinned_interface="wlan1")

    with pytest.raises(WifiError, match="wlan1 was not found"):
        wifi.enable_radio()
