import pytest

from mlsc.diagnosis import Status
from mlsc.wifi import CLIENT, HOTSPOT, WifiError
from mlsc.wifi.nmcli import NmcliWifiManager, split_terse

pytestmark = pytest.mark.unit

# Terse `nmcli -t` output in the shape of NetworkManager 1.42 on Raspberry Pi OS Bookworm, SSIDs changed.
DEVICES = "eth0:ethernet:unavailable\nwlan0:wifi:connected\nlo:loopback:unmanaged"
WIFI_LIST = "*:Home\\:5G:78:WPA2\n :Cafe:40:\n :Neighbour:55:WPA1 WPA2\n ::20:WPA2"
CONNECTIONS = "Home\\:5G:802-11-wireless\nWired connection 1:802-3-ethernet\nOld Phone:802-11-wireless"
DEVICE_SHOW_HOME = "GENERAL.CONNECTION:Home\\:5G\nIP4.ADDRESS[1]:192.168.1.50/24"
DEVICE_SHOW_IDLE = "GENERAL.CONNECTION:--\nIP4.ADDRESS[1]:"
REG_GET = "global\ncountry DE: DFS-ETSI\n\tUNSET"

LIST_DEVICES = ("nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device")
AP_SUPPORT = ("nmcli", "-t", "-g", "WIFI-PROPERTIES.AP", "device", "show", "wlan0")
REG_GET_COMMAND = ("iw", "reg", "get")
LIST_CONNECTIONS = ("nmcli", "-t", "-f", "NAME,TYPE", "connection", "show")
DEVICE_SHOW = ("nmcli", "-t", "-f", "GENERAL.CONNECTION,IP4.ADDRESS", "device", "show", "wlan0")
WIFI_LIST_COMMAND = ("nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi", "list", "--rescan", "yes")
HOTSPOT_SECRETS = ("nmcli", "-t", "-s", "-g", "802-11-wireless.ssid,802-11-wireless-security.psk", "connection", "show", "MLSC-Hotspot")
HOTSPOT_BASE = ("nmcli", "device", "wifi", "hotspot", "ifname", "wlan0", "con-name", "MLSC-Hotspot")
DELETE_HOTSPOT = ("nmcli", "connection", "delete", "id", "MLSC-Hotspot")


class FakeRunner:
    """Answers command lines from a table and records every call; anything unexpected fails like a broken command."""

    def __init__(self, answers) -> None:
        self.answers = dict(answers)
        self.calls = []

    def __call__(self, command, timeout=None) -> tuple[int, str]:  # ruff: ignore[unused-method-argument]
        self.calls.append(command)
        return self.answers.get(tuple(command), (1, f"unexpected command: {command}"))

    def ran(self, *prefix):
        return any(call[:len(prefix)] == list(prefix) for call in self.calls)


def manager():
    """Build a manager on a Pi whose adapter works."""
    answers = {
        LIST_DEVICES: (0, DEVICES),
        AP_SUPPORT: (0, "yes"),
        REG_GET_COMMAND: (0, REG_GET),
        LIST_CONNECTIONS: (0, CONNECTIONS),
        DEVICE_SHOW: (0, DEVICE_SHOW_HOME),
        WIFI_LIST_COMMAND: (0, WIFI_LIST),
    }
    runner = FakeRunner(answers)
    return NmcliWifiManager(runner), runner


def manager_with(answers):
    wifi, runner = manager()
    runner.answers.update(answers)
    return wifi, runner


@pytest.mark.parametrize(("line", "fields"), [
    ("a:b:c", ["a", "b", "c"]),
    ("Home\\:5G:78:WPA2", ["Home:5G", "78", "WPA2"]),
    ("back\\\\slash:1", ["back\\slash", "1"]),
    (":empty::", ["", "empty", "", ""]),
])
def test_split_terse_honours_the_escaping_of_nmcli(line, fields):
    assert split_terse(line) == fields


def test_scan_parses_the_terse_list_and_marks_known_and_in_use_networks():
    wifi, _ = manager()

    networks = {network.ssid: network for network in wifi.scan()}

    home = networks["Home:5G"]
    assert set(networks) == {"Home:5G", "Cafe", "Neighbour"}
    assert (home.signal, home.security, home.in_use, home.known) == (78, "WPA2", True, True)
    assert (networks["Cafe"].security, networks["Cafe"].known, networks["Cafe"].in_use) == (None, False, False)
    assert networks["Neighbour"].security == "WPA1 WPA2"


def test_scan_is_empty_when_nmcli_fails():
    wifi, _ = manager_with({WIFI_LIST_COMMAND: (1, "boom")})

    assert wifi.scan() == []


def test_capabilities_read_ap_support_and_country():
    wifi, _ = manager()

    capabilities = wifi.capabilities()

    assert (capabilities.supported, capabilities.hotspot, capabilities.country) == (True, True, "DE")


def test_capabilities_say_no_ap_and_no_country_when_the_adapter_lacks_them():
    wifi, _ = manager_with({AP_SUPPORT: (0, "no"), REG_GET_COMMAND: (0, "global\ncountry 00: DFS-UNSET")})

    capabilities = wifi.capabilities()

    assert (capabilities.hotspot, capabilities.country) == (False, None)


def test_capabilities_have_no_country_when_iw_is_missing():
    wifi, _ = manager_with({REG_GET_COMMAND: (127, "iw: command not found")})

    assert wifi.capabilities().country is None


@pytest.mark.parametrize("devices", [(127, "nmcli: command not found")])
def test_unsupported_without_nmcli(devices):
    wifi, _ = manager_with({LIST_DEVICES: devices})

    assert wifi.capabilities().supported is False
    assert wifi.scan() == []
    assert wifi.status().connected is False
    with pytest.raises(WifiError, match="not supported"):
        wifi.connect("Home", "pw")


def test_status_of_a_connected_client():
    wifi, _ = manager()

    status = wifi.status()

    assert (status.mode, status.connected, status.ssid, status.ip, status.hotspot) == (CLIENT, True, "Home:5G", "192.168.1.50", None)


def test_status_of_an_idle_adapter():
    wifi, _ = manager_with({DEVICE_SHOW: (0, DEVICE_SHOW_IDLE)})

    status = wifi.status()

    assert (status.mode, status.connected, status.ssid, status.ip) == (CLIENT, False, None, None)


def test_status_of_the_hotspot_includes_its_credentials():
    wifi, _ = manager_with({
        DEVICE_SHOW: (0, "GENERAL.CONNECTION:MLSC-Hotspot\nIP4.ADDRESS[1]:10.42.0.1/24"),
        HOTSPOT_SECRETS: (0, "MLSC-ab12\nhunter22pw"),
    })

    status = wifi.status()

    assert (status.mode, status.connected, status.ip) == (HOTSPOT, False, "10.42.0.1")
    assert (status.hotspot.ssid, status.hotspot.password) == ("MLSC-ab12", "hunter22pw")


def test_connect_passes_the_ssid_and_password_to_nmcli():
    command = ("nmcli", "device", "wifi", "connect", "Home:5G", "password", "secret123", "ifname", "wlan0")
    wifi, runner = manager_with({command: (0, "Device 'wlan0' successfully activated")})

    wifi.connect("Home:5G", "secret123")

    assert list(command) in runner.calls


def test_connect_to_an_open_network_sends_no_password():
    command = ("nmcli", "device", "wifi", "connect", "Cafe", "ifname", "wlan0")
    wifi, runner = manager_with({command: (0, "ok")})

    wifi.connect("Cafe", None)

    assert list(command) in runner.calls


def test_failed_connect_raises_and_removes_the_profile_nmcli_left_behind():
    command = ("nmcli", "device", "wifi", "connect", "Cafe", "password", "hunter22pw", "ifname", "wlan0")
    wifi, runner = manager_with({command: (4, "Error: Connection activation failed: Secrets were required, but not provided."),
                                 ("nmcli", "connection", "delete", "id", "Cafe"): (0, "deleted")})

    with pytest.raises(WifiError, match="password for Cafe is missing or wrong") as error:
        wifi.connect("Cafe", "hunter22pw")

    assert runner.ran("nmcli", "connection", "delete", "id", "Cafe")
    assert "hunter22pw" not in str(error.value)


def test_failed_connect_keeps_the_profile_of_an_already_saved_network():
    command = ("nmcli", "device", "wifi", "connect", "Home:5G", "password", "wrong", "ifname", "wlan0")
    wifi, runner = manager_with({command: (4, "Error: failed")})

    with pytest.raises(WifiError):
        wifi.connect("Home:5G", "wrong")

    assert not runner.ran("nmcli", "connection", "delete")


def test_forget_deletes_the_saved_connection():
    command = ("nmcli", "connection", "delete", "id", "Old Phone")
    wifi, runner = manager_with({command: (0, "deleted")})

    wifi.forget("Old Phone")

    assert list(command) in runner.calls


def test_forget_of_an_unsaved_network_raises():
    wifi, runner = manager()

    with pytest.raises(WifiError, match="not saved"):
        wifi.forget("Cafe")

    assert not runner.ran("nmcli", "connection", "delete")


def test_start_hotspot_creates_the_named_profile_with_the_given_credentials():
    command = (*HOTSPOT_BASE, "ssid", "MLSC-ab12", "password", "hunter22pw")
    wifi, runner = manager_with({command: (0, "ok")})

    wifi.start_hotspot("MLSC-ab12", "hunter22pw")

    assert list(command) in runner.calls


def test_start_hotspot_lets_nmcli_generate_missing_credentials():
    wifi, runner = manager_with({HOTSPOT_BASE: (0, "ok")})

    wifi.start_hotspot(None, None)

    assert list(HOTSPOT_BASE) in runner.calls


def test_start_hotspot_refuses_without_access_point_support():
    wifi, runner = manager_with({AP_SUPPORT: (0, "no")})

    with pytest.raises(WifiError, match="Hotspot"):
        wifi.start_hotspot(None, None)

    assert not runner.ran("nmcli", "device", "wifi", "hotspot")


def test_start_hotspot_failure_raises():
    wifi, _ = manager_with({HOTSPOT_BASE: (1, "Error: boom")})

    with pytest.raises(WifiError, match="boom"):
        wifi.start_hotspot(None, None)


def test_stop_hotspot_deletes_the_profile_when_it_exists():
    wifi, runner = manager_with({LIST_CONNECTIONS: (0, f"{CONNECTIONS}\nMLSC-Hotspot:802-11-wireless"), DELETE_HOTSPOT: (0, "deleted")})

    wifi.stop_hotspot()

    assert list(DELETE_HOTSPOT) in runner.calls


def test_stop_hotspot_without_a_profile_does_nothing():
    wifi, runner = manager()

    wifi.stop_hotspot()

    assert not runner.ran("nmcli", "connection", "delete")


def test_stop_hotspot_failure_raises():
    wifi, _ = manager_with({LIST_CONNECTIONS: (0, "MLSC-Hotspot:802-11-wireless"), DELETE_HOTSPOT: (1, "Error: busy")})

    with pytest.raises(WifiError, match="busy"):
        wifi.stop_hotspot()


def test_diagnose_is_ok_on_a_ready_adapter_and_warns_without_a_country():
    ready, _ = manager()
    no_country, _ = manager_with({REG_GET_COMMAND: (0, "global\ncountry 00: DFS-UNSET")})

    assert ready.diagnose().status is Status.OK
    assert no_country.diagnose().status is Status.WARNING


def test_scan_keeps_one_entry_per_ssid_and_reads_a_dash_as_open():
    wifi, _ = manager_with({WIFI_LIST_COMMAND: (0, " :Mesh:30:WPA2\n :Mesh:70:WPA2\n :Cafe:40:--")})

    networks = {network.ssid: network for network in wifi.scan()}

    assert networks["Mesh"].signal == 70
    assert networks["Cafe"].security is None


def test_status_of_the_hotspot_unescapes_the_credentials():
    wifi, _ = manager_with({
        DEVICE_SHOW: (0, "GENERAL.CONNECTION:MLSC-Hotspot\nIP4.ADDRESS[1]:10.42.0.1/24"),
        HOTSPOT_SECRETS: (0, "My\\:Net\npw\\:with\\\\colon"),
    })

    hotspot = wifi.status().hotspot

    assert (hotspot.ssid, hotspot.password) == ("My:Net", "pw:with\\colon")


RADIO = ("nmcli", "-t", "-f", "WIFI-HW,WIFI", "radio")
TWO_ADAPTERS = "eth0:ethernet:connected\nwlan0:wifi:unavailable\nwlan1:wifi:disconnected\nlo:loopback:unmanaged"


def adapter_manager(devices, radio="enabled:enabled", interface=None, ap_support=None):
    answers = {LIST_DEVICES: (0, devices), RADIO: (0, radio), REG_GET_COMMAND: (0, REG_GET), LIST_CONNECTIONS: (0, CONNECTIONS)}
    for name, supported in (ap_support or {}).items():
        answers[("nmcli", "-t", "-g", "WIFI-PROPERTIES.AP", "device", "show", name)] = (0, "yes" if supported else "no")
    runner = FakeRunner(answers)
    return NmcliWifiManager(runner, interface=interface), runner


def test_the_automatic_pick_skips_an_unavailable_adapter():
    wifi, _ = adapter_manager(TWO_ADAPTERS, ap_support={"wlan1": True})

    capabilities = wifi.capabilities()

    assert (capabilities.interface, capabilities.radio) == ("wlan1", "ready")


def test_the_automatic_pick_prefers_the_adapter_holding_the_connection():
    devices = "wlan0:wifi:disconnected\nwlan1:wifi:connected"

    wifi, _ = adapter_manager(devices, ap_support={"wlan0": True, "wlan1": False})

    assert wifi.capabilities().interface == "wlan1"


def test_the_automatic_pick_then_prefers_hotspot_support_then_the_first_name():
    devices = "wlan1:wifi:disconnected\nwlan0:wifi:disconnected\nwlan2:wifi:disconnected"

    first, _ = adapter_manager(devices, ap_support={"wlan0": False, "wlan1": False, "wlan2": False})
    capable, _ = adapter_manager(devices, ap_support={"wlan0": False, "wlan1": False, "wlan2": True})

    assert first.capabilities().interface == "wlan0"
    assert capable.capabilities().interface == "wlan2"


def test_without_a_usable_adapter_the_first_one_is_still_returned_and_is_unavailable():
    wifi, _ = adapter_manager("wlan0:wifi:unavailable\nwlan1:wifi:unmanaged", ap_support={"wlan0": False})

    capabilities = wifi.capabilities()

    assert (capabilities.interface, capabilities.radio) == ("wlan0", "unavailable")


def test_a_pinned_adapter_is_used_even_when_another_one_is_better():
    wifi, runner = adapter_manager(TWO_ADAPTERS, interface="wlan0")

    assert wifi.capabilities().interface == "wlan0"
    assert wifi.status().ssid is None
    assert not any("wlan1" in call for call in runner.calls)


def test_a_missing_pinned_adapter_is_no_adapter_and_every_change_fails_with_its_message():
    wifi, runner = adapter_manager(TWO_ADAPTERS, interface="wlan9")

    capabilities = wifi.capabilities()

    assert (capabilities.radio, capabilities.interface, capabilities.pinned, capabilities.supported) == ("no_adapter", "wlan9", True, True)
    for change in (lambda: wifi.connect("Home", "x"), lambda: wifi.forget("Home"), lambda: wifi.start_hotspot(None, None)):
        with pytest.raises(WifiError, match="configured Wi-Fi adapter wlan9 was not found"):
            change()
    assert not runner.ran("nmcli", "device", "wifi", "connect")


def test_networkmanager_without_a_wifi_device_is_no_adapter_but_still_supported():
    wifi, _ = adapter_manager("eth0:ethernet:connected")

    capabilities = wifi.capabilities()

    assert (capabilities.supported, capabilities.radio, capabilities.pinned) == (True, "no_adapter", False)


def test_networkmanager_that_does_not_answer_is_unsupported():
    wifi = NmcliWifiManager(FakeRunner({}))

    assert wifi.capabilities().supported is False


@pytest.mark.parametrize(("radio", "state"), [
    ("disabled:enabled", "blocked"),
    ("enabled:disabled", "switched_off"),
    ("disabled:disabled", "blocked"),
    ("enabled:enabled", "ready"),
])
def test_the_radio_state_comes_from_nmcli_radio(radio, state):
    wifi, _ = adapter_manager("wlan0:wifi:disconnected", radio=radio, ap_support={"wlan0": True})

    assert wifi.capabilities().radio == state


def test_an_adapter_that_nmcli_calls_unavailable_while_the_radio_is_on_is_unavailable():
    wifi, _ = adapter_manager("wlan0:wifi:unavailable", ap_support={"wlan0": True})

    assert wifi.radio() == "unavailable"


def test_the_status_of_an_unusable_radio_is_a_disconnected_client():
    wifi, _ = adapter_manager("wlan0:wifi:unavailable", radio="enabled:disabled")

    assert wifi.status().connected is False


class Sleeper:
    def __init__(self) -> None:
        self.slept = 0

    def __call__(self, seconds):
        self.slept += seconds


def switched_off_manager(becomes_ready_after=1):
    """A Pi whose radio is off until `nmcli radio wifi on` ran and `becomes_ready_after` seconds passed."""
    sleeper = Sleeper()
    state = {"on": False}
    runner = FakeRunner({LIST_DEVICES: (0, "wlan0:wifi:unavailable"), REG_GET_COMMAND: (0, REG_GET)})

    def answer(command, timeout=None):
        runner.calls.append(command)
        if tuple(command) == ("nmcli", "radio", "wifi", "on"):
            state["on"] = True
            return 0, ""
        if tuple(command) == LIST_DEVICES:
            ready = state["on"] and sleeper.slept >= becomes_ready_after
            return 0, "wlan0:wifi:disconnected" if ready else "wlan0:wifi:unavailable"
        if tuple(command) == RADIO:
            return 0, "enabled:enabled" if state["on"] else "enabled:disabled"
        return 0, ""

    return NmcliWifiManager(answer, sleep=sleeper), runner, sleeper


def test_enable_radio_unblocks_rfkill_switches_nmcli_on_and_waits_for_the_adapter():
    wifi, runner, sleeper = switched_off_manager(becomes_ready_after=3)

    wifi.enable_radio()

    assert runner.ran("rfkill", "unblock", "wifi")
    assert runner.ran("nmcli", "radio", "wifi", "on")
    assert 3 <= sleeper.slept <= 10
    assert wifi.radio() == "ready"


def test_enable_radio_fails_when_the_adapter_stays_unavailable():
    wifi, _, sleeper = switched_off_manager(becomes_ready_after=999)

    with pytest.raises(WifiError):
        wifi.enable_radio()

    assert sleeper.slept <= 10


def test_enable_radio_is_refused_unless_the_radio_is_switched_off():
    wifi, runner = adapter_manager("wlan0:wifi:disconnected", radio="disabled:enabled")

    with pytest.raises(WifiError, match="hardware switch"):
        wifi.enable_radio()

    assert not runner.ran("nmcli", "radio", "wifi", "on")


def test_a_connect_without_the_secret_names_the_network_and_asks_for_the_password():
    command = ("nmcli", "device", "wifi", "connect", "In einem LAN", "ifname", "wlan0")
    output = "Error: Connection activation failed: Secrets were required, but not provided."
    wifi, _ = manager_with({command: (4, output), ("nmcli", "connection", "delete", "id", "In einem LAN"): (0, "")})

    with pytest.raises(WifiError) as error:
        wifi.connect("In einem LAN", None)

    assert str(error.value) == "The password for In einem LAN is missing or wrong. Enter it and try again."


def duplicated_hotspot_manager(profiles):
    """A Pi that has `profiles` profiles named like the Hotspot; deleting by name removes one at a time."""
    state = {"profiles": profiles}
    runner = FakeRunner({LIST_DEVICES: (0, DEVICES), AP_SUPPORT: (0, "yes"), HOTSPOT_BASE: (0, "ok")})

    def answer(command, timeout=None):
        runner.calls.append(command)
        if tuple(command) == LIST_CONNECTIONS:
            return 0, "Wired connection 1:802-3-ethernet" + "\nMLSC-Hotspot:802-11-wireless" * state["profiles"]
        if tuple(command) == DELETE_HOTSPOT:
            state["profiles"] -= 1
            return 0, "deleted"
        return runner.answers.get(tuple(command), (1, f"unexpected command: {command}"))

    return NmcliWifiManager(answer), runner, state


def test_stop_hotspot_removes_every_profile_with_the_hotspot_name():
    wifi, _, state = duplicated_hotspot_manager(2)

    wifi.stop_hotspot()

    assert state["profiles"] == 0


def test_start_hotspot_replaces_the_profiles_a_earlier_start_left_behind():
    wifi, runner, state = duplicated_hotspot_manager(2)

    wifi.start_hotspot(None, None)

    assert state["profiles"] == 0
    assert list(HOTSPOT_BASE) in runner.calls
    assert runner.calls.index(list(DELETE_HOTSPOT)) < runner.calls.index(list(HOTSPOT_BASE))
