from dataclasses import dataclass

import pytest

from mlsc.wifi import CLIENT, HOTSPOT, MockNetwork, MockWifiManager, WifiError
from mlsc.wifi.credentials import HotspotCredentials
from mlsc.wifi.supervisor import WifiSupervisor

pytestmark = pytest.mark.unit

CAFE = MockNetwork("Cafe", security=None)
HOME = MockNetwork("Home", signal=80, security="WPA2", password="secret123")  # ruff: ignore[hardcoded-password-func-arg]


@dataclass
class Settings:
    mode: str = CLIENT
    setup_fallback: bool = True


class Rig:
    def __init__(self, fake_clock, tmp_path, **manager_options) -> None:
        self.clock = fake_clock
        self.wifi = MockWifiManager(networks=[HOME, CAFE], **manager_options)
        self.settings = Settings()
        self.ethernet = False
        self.boot_dir = tmp_path
        credentials = HotspotCredentials(tmp_path, lambda: "aa:bb:cc:dd:12:34")
        self.supervisor = WifiSupervisor(self.wifi, self.settings, fake_clock.time, lambda: self.ethernet, credentials)

    def run(self, seconds, step=5):
        for _ in range(seconds // step):
            self.clock.advance(step)
            self.supervisor.tick()

    def connect_home(self):
        self.wifi.connect("Home", "secret123")


@pytest.fixture
def rig(fake_clock, tmp_path):
    return Rig(fake_clock, tmp_path)


def test_the_setup_fallback_is_raised_when_nothing_connects_within_60_seconds_of_boot(rig):
    rig.run(55)
    assert rig.wifi.status().mode == CLIENT

    rig.run(10)

    status = rig.wifi.status()
    assert status.mode == HOTSPOT
    assert status.hotspot.ssid == "MLSC-1234"
    assert rig.settings.mode == CLIENT


def test_a_connection_at_boot_means_no_setup_fallback(rig):
    rig.connect_home()

    rig.run(600)

    assert rig.wifi.status().mode == CLIENT


def test_a_lost_connection_raises_the_setup_fallback_only_after_5_minutes(rig):
    rig.connect_home()
    rig.run(120)
    rig.wifi.forget("Home")

    rig.run(290)
    assert rig.wifi.status().mode == CLIENT

    rig.run(20)
    assert rig.wifi.status().mode == HOTSPOT


def test_the_setup_fallback_is_never_raised_while_ethernet_is_up(rig):
    rig.ethernet = True

    rig.run(600)
    assert rig.wifi.status().mode == CLIENT

    rig.ethernet = False
    rig.run(50)
    assert rig.wifi.status().mode == CLIENT
    rig.run(20)
    assert rig.wifi.status().mode == HOTSPOT


def test_the_setup_fallback_can_be_switched_off(rig):
    rig.settings.setup_fallback = False

    rig.run(600)

    assert rig.wifi.status().mode == CLIENT


def test_a_saved_hotspot_mode_is_not_a_fallback(rig):
    rig.settings.mode = HOTSPOT
    rig.supervisor.set_hotspot(True)

    rig.run(600)

    assert rig.wifi.status().mode == HOTSPOT
    assert rig.supervisor.fallback_active is False


def raise_fallback(rig):
    rig.run(65)
    assert rig.supervisor.fallback_active


def test_the_setup_fallback_is_dropped_when_the_retry_reaches_a_known_network(rig):
    raise_fallback(rig)
    rig.run(115)
    assert rig.wifi.status().mode == CLIENT  # the Hotspot is down for the retry

    rig.connect_home()  # the router answers
    rig.run(10)

    assert rig.supervisor.fallback_active is False
    assert rig.wifi.status().ssid == "Home"


def test_the_retry_brings_the_hotspot_back_when_no_known_network_answers(rig):
    raise_fallback(rig)

    rig.run(120)
    assert rig.wifi.status().mode == CLIENT

    rig.run(25)
    assert rig.wifi.status().mode == HOTSPOT
    assert rig.supervisor.fallback_active


def test_the_retry_waits_while_a_phone_is_connected_to_the_hotspot(rig):
    raise_fallback(rig)
    rig.wifi.clients = 1

    rig.run(600)

    assert rig.wifi.status().mode == HOTSPOT


def test_joining_a_network_from_the_setup_fallback_drops_it(rig):
    raise_fallback(rig)

    rig.supervisor.connect("Home", "secret123")
    rig.run(60)

    assert rig.supervisor.fallback_active is False
    assert rig.wifi.status().ssid == "Home"
    assert rig.settings.mode == CLIENT


def test_a_wrong_password_leaves_the_setup_fallback_up(rig):
    raise_fallback(rig)

    with pytest.raises(WifiError):
        rig.supervisor.connect("Home", "wrong-password")
    rig.run(60)

    assert rig.wifi.status().mode == HOTSPOT
    assert rig.supervisor.fallback_active


def test_a_change_that_does_not_connect_within_45_seconds_rolls_back_to_the_hotspot(rig):
    rig.settings.mode = HOTSPOT
    rig.supervisor.set_hotspot(True)
    rig.wifi.clients = 0
    original = rig.wifi.status().hotspot

    rig.supervisor.set_hotspot(False)
    rig.run(40)
    assert rig.settings.mode == CLIENT

    rig.run(10)

    assert rig.settings.mode == HOTSPOT
    assert rig.wifi.status().mode == HOTSPOT
    assert rig.wifi.status().hotspot.ssid == original.ssid


def test_a_change_that_connects_in_time_is_kept(rig):
    rig.supervisor.connect("Home", "secret123")

    rig.run(120)

    assert rig.wifi.status().ssid == "Home"


def test_the_hotspot_password_is_the_one_from_the_boot_partition(rig):
    (rig.boot_dir / "mlsc-hotspot-password.txt").write_text("my-own-password\n")

    rig.supervisor.set_hotspot(True)

    assert rig.wifi.status().hotspot.password == "my-own-password"


def test_a_generated_password_is_written_to_the_boot_partition_and_reused(rig):
    rig.supervisor.set_hotspot(True)
    first = rig.wifi.status().hotspot.password
    rig.supervisor.set_hotspot(True)

    assert rig.wifi.status().hotspot.password == first
    assert f"Password: {first}" in (rig.boot_dir / "mlsc-hotspot.txt").read_text()
    assert "MLSC-1234" in (rig.boot_dir / "mlsc-hotspot.txt").read_text()


def test_a_too_short_password_file_is_ignored(rig):
    (rig.boot_dir / "mlsc-hotspot-password.txt").write_text("short")

    rig.supervisor.set_hotspot(True)

    assert rig.wifi.status().hotspot.password != "short"


def test_turning_the_hotspot_off_is_kept_while_ethernet_is_up(rig):
    rig.supervisor.set_hotspot(True)
    rig.ethernet = True

    rig.supervisor.set_hotspot(False)
    rig.run(120)

    assert rig.settings.mode == CLIENT
    assert rig.wifi.status().mode == CLIENT


def test_a_failed_connect_that_dropped_the_current_network_rejoins_it(rig):
    rig.wifi.connect("Cafe", None)
    rig.run(10)
    rig.wifi.drop_on_failed_connect = True

    with pytest.raises(WifiError):
        rig.supervisor.connect("Home", "wrong-password")

    assert rig.wifi.status().ssid == "Cafe"


def test_a_second_change_rolls_back_to_the_last_working_mode(rig):
    rig.wifi.connect("Cafe", None)
    rig.run(10)
    rig.supervisor.set_hotspot(True)
    rig.supervisor.set_hotspot(False)

    rig.run(60)

    assert rig.wifi.status().ssid == "Cafe"
    assert rig.settings.mode == CLIENT


def test_a_saved_hotspot_mode_is_raised_again_after_a_restart(rig):
    rig.settings.mode = HOTSPOT

    rig.run(10)

    assert rig.wifi.status().mode == HOTSPOT
    assert rig.supervisor.fallback_active is False
