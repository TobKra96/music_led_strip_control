import copy
from types import SimpleNamespace

import pytest

from mlsc import operations, strip_pattern
from mlsc.host import Host
from mlsc.operations import OperationRegistry, OperationState
from mlsc.strip_pattern import Pattern
from mlsc.webserver import messages
from mlsc.webserver.blueprints.device_settings_executer import DeviceSettingsExecuter

pytestmark = pytest.mark.unit


class PiHost(Host):
    def __init__(self) -> None:
        super().__init__(boot_configs=())

    def pi_model(self):  # ruff: ignore[no-self-use]
        return "Raspberry Pi 4 Model B Rev 1.5"


def device_config():
    return {
        "device_name": "Desk", "led_count": 100, "led_mid": 50, "led_brightness": 100, "output_type": "output_udp",
        "chip_family": "ws2812", "colour_order": "grb", "white_channel": False,
        "power_limit": {"enabled": False, "supply_amps": 5.0, "ma_per_led": 60, "mode": "warn"},
        "output": {
            "output_raspi": {"led_pin": 18, "led_channel": 0, "led_dma": 10, "led_freq_hz": 800000, "led_invert": False},
            "output_udp": {"udp_client_ip": "127.0.0.1", "udp_client_port": 7777},
        },
    }


class Hub:
    """Stands in for the Strip Preview hub: the output process answers every refresh with a Diagnosis."""

    def __init__(self, executer, status="ok") -> None:
        self.sequence = 0
        self.status = status
        self.silent = False
        self._executer = executer

    def latest(self, device_id):
        return (self.sequence, {"device_id": device_id, "status": self.status, "message": "The strip said so.", "suggested_fix": "Try again."})

    def answer(self):
        self.sequence += 1


class Patterns:
    def __init__(self) -> None:
        self.started = []

    def start(self, device_id, pattern, seconds):
        self.started.append((device_id, pattern, seconds))


@pytest.fixture
def rig(fake_clock, monkeypatch):
    registry = OperationRegistry(clock=fake_clock.time, sleep=fake_clock.sleep, publish=lambda *_: None, spawn=lambda target: target())
    monkeypatch.setattr(operations, "registry", registry)
    config = {"device_configs": {"device_0": device_config()}}
    saved = []
    executer = DeviceSettingsExecuter.__new__(DeviceSettingsExecuter)
    executer._config_instance = SimpleNamespace(config=config, save_config=lambda saving: saved.append(copy.deepcopy(saving)))  # ruff: ignore[private-member-access]
    refreshed = []
    executer.refresh_device = lambda device_id: (refreshed.append(device_id), hub.answer())
    hub = Hub(executer)
    patterns = Patterns()
    monkeypatch.setattr(executer, "_clock", fake_clock.time, raising=False)
    monkeypatch.setattr(executer, "_sleep", fake_clock.sleep, raising=False)
    monkeypatch.setattr(executer, "_host", PiHost(), raising=False)
    monkeypatch.setattr(executer, "_diagnoses", hub, raising=False)
    monkeypatch.setattr(strip_pattern, "channel", patterns)
    return SimpleNamespace(executer=executer, config=config, saved=saved, refreshed=refreshed, hub=hub, patterns=patterns, registry=registry)


def test_a_valid_change_is_saved_refreshed_verified_and_confirmed(rig):
    operation = rig.executer.apply_output("device_0", {"led_count": 60, "led_mid": 30})

    assert operation.kind == "output"
    assert operation.state is OperationState.CONFIRMED
    assert rig.config["device_configs"]["device_0"]["led_count"] == 60
    assert rig.refreshed == ["device_0"]
    assert rig.saved[-1]["device_configs"]["device_0"]["led_count"] == 60


def test_a_confirmed_change_shows_a_test_frame_on_the_strip(rig):
    rig.executer.apply_output("device_0", {"led_count": 60, "led_mid": 30})

    assert [(device, pattern) for device, pattern, _ in rig.patterns.started] == [("device_0", Pattern.markers)]


def test_a_failed_check_rolls_back_the_config_and_the_file(rig):
    rig.hub.status = "error"

    operation = rig.executer.apply_output("device_0", {"led_count": 60, "led_mid": 30})

    assert operation.state is OperationState.ROLLED_BACK
    assert "The strip said so." in operation.error
    assert rig.config["device_configs"]["device_0"]["led_count"] == 100
    assert rig.saved[-1]["device_configs"]["device_0"]["led_count"] == 100
    assert rig.patterns.started == []


def test_the_rollback_refreshes_the_device_so_it_runs_the_old_config_again(rig):
    rig.hub.status = "error"

    rig.executer.apply_output("device_0", {"led_count": 60, "led_mid": 30})

    assert rig.refreshed[-1] == "device_0"
    assert len(rig.refreshed) == 2  # one try, then the rollback


def test_the_retry_of_the_banner_tries_again_with_a_growing_wait(rig, fake_clock):
    rig.hub.status = "error"

    operation = rig.executer.retry_output("device_0")

    assert operation.state is OperationState.ROLLED_BACK
    assert fake_clock.sleeps[:2] == [1.0, 2.0]


def test_an_apply_the_output_process_never_reports_on_is_rolled_back(rig):
    rig.executer.refresh_device = rig.refreshed.append

    operation = rig.executer.apply_output("device_0", {"led_count": 60, "led_mid": 30})

    assert operation.state is OperationState.ROLLED_BACK
    assert "did not report" in operation.error


def test_a_diagnosis_from_before_the_apply_does_not_confirm_it(rig):
    rig.hub.answer()
    rig.executer.refresh_device = rig.refreshed.append

    assert rig.executer.apply_output("device_0", {"led_count": 60, "led_mid": 30}).state is OperationState.ROLLED_BACK


def test_a_config_the_output_cannot_use_fails_the_static_check_without_waiting_for_the_process(rig):
    rig.config["device_configs"]["device_0"]["output"]["output_udp"]["udp_client_ip"] = ""

    operation = rig.executer.apply_output("device_0", {"led_count": 60, "led_mid": 30})

    assert operation.state is OperationState.ROLLED_BACK
    assert "No UDP client host" in operation.error


def test_validation_rejects_values_the_hardware_cannot_use(rig):
    errors = rig.executer.validate_output("device_0", {"led_mid": 500})

    assert [error["field"] for error in errors] == ["led_mid"]


def test_validation_looks_at_the_result_of_the_patch_not_the_patch_alone(rig):
    assert rig.executer.validate_output("device_0", {"led_count": 40}) == [
        {"field": "led_mid", "detail": "Must be a pixel of the strip, from 0 to 39."}]


def test_a_gpio_pin_change_derives_the_channel(rig):
    rig.config["device_configs"]["device_0"]["output_type"] = "output_raspi"

    patch = rig.executer.derive_channel("device_0", {"output": {"output_raspi": {"led_pin": 13}}})

    assert patch["output"]["output_raspi"]["led_channel"] == 1


def test_a_patch_without_a_pin_is_left_alone(rig):
    patch = {"led_count": 60}

    assert rig.executer.derive_channel("device_0", patch) == {"led_count": 60}


def test_retry_applies_the_stored_config_again_as_an_operation(rig):
    operation = rig.executer.retry_output("device_0")

    assert operation.kind == "output"
    assert operation.state is OperationState.CONFIRMED
    assert rig.refreshed == ["device_0"]
    assert rig.config["device_configs"]["device_0"]["led_count"] == 100


def test_an_unknown_device_is_reported_as_not_found(rig):
    assert rig.executer.apply_output("device_9", {"led_count": 1}) is messages.DeviceNotFound
    assert rig.executer.validate_output("device_9", {}) is messages.DeviceNotFound
    assert rig.executer.retry_output("device_9") is messages.DeviceNotFound
