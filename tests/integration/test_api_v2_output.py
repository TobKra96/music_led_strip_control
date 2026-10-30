from types import SimpleNamespace

import pytest

from mlsc.api.v2 import register_api_v2
from mlsc.app import create_app
from mlsc.host import Host
from mlsc.webserver.blueprints.device_settings_executer import DeviceSettingsExecuter
from mlsc.webserver.executer import Executer
from mlsc.webserver.messages import DeviceNotFound

pytestmark = pytest.mark.integration


class PiHost(Host):
    def __init__(self) -> None:
        super().__init__(boot_configs=())

    def pi_model(self):  # ruff: ignore[no-self-use]
        return "Raspberry Pi 4 Model B Rev 1.5"


def device_config():
    return {
        "led_count": 100, "led_mid": 50, "led_brightness": 100, "output_type": "output_raspi",
        "chip_family": "ws2812", "colour_order": "grb", "white_channel": False,
        "power_limit": {"enabled": True, "supply_amps": 5.0, "ma_per_led": 60, "mode": "warn"},
        "output": {
            "output_raspi": {"led_pin": 18, "led_channel": 0, "led_dma": 10, "led_freq_hz": 800000, "led_invert": False},
            "output_udp": {"udp_client_ip": "127.0.0.1", "udp_client_port": 7777},
        },
    }


class Settings:
    def __init__(self) -> None:
        self.config = device_config()
        self.applied = []
        self.retried = []

    def get_device_settings(self, device_id):
        return {"device": device_id, "settings": self.config}

    def validate_output(self, device_id, patch):
        return DeviceSettingsExecuter.validate_output(self._executer(), device_id, patch)

    def _executer(self):
        executer = DeviceSettingsExecuter.__new__(DeviceSettingsExecuter)
        executer._config_instance = SimpleNamespace(config={"device_configs": {"device_0": self.config}})  # ruff: ignore[private-member-access]
        executer._host = PiHost()  # ruff: ignore[private-member-access]
        return executer

    def apply_output(self, device_id, patch):
        self.applied.append((device_id, patch))
        return SimpleNamespace(as_dict=lambda: {"id": "op1", "kind": "output", "state": "pending", "attempts": 0, "error": None}, id="op1")

    def retry_output(self, device_id):
        self.retried.append(device_id)
        return self.apply_output(device_id, {})


@pytest.fixture
def settings(monkeypatch):
    settings = Settings()
    executer = SimpleNamespace(
        device_executer=SimpleNamespace(
            get_devices=lambda: [{"name": "Desk", "id": "device_0", "assigned_to": {}}],
            get_device=lambda device_id: {"name": "Desk", "id": "device_0", "assigned_to": {}} if device_id == "device_0" else DeviceNotFound,
        ),
        device_settings_executer=settings,
    )
    monkeypatch.setattr(Executer, "instance", executer, raising=False)
    monkeypatch.setattr("mlsc.output_setup.Host", PiHost)
    return settings


@pytest.fixture
def client(settings):  # ruff: ignore[unused-function-argument]
    app = create_app()
    app.config["AUTH_ENABLED"] = False
    app.secret_key = "test"  # ruff: ignore[hardcoded-password-string]
    register_api_v2(app)
    return app.test_client()


def test_the_setup_choices_list_the_pins_of_the_host_with_their_channel(client):
    body = client.get("/api/v2/devices/device_0/output/setup").get_json()

    assert body["pin_channels"] == {"10": 0, "12": 0, "13": 1, "18": 0, "19": 1, "21": 0}
    assert body["backend"] == "rpi_ws281x"
    assert body["max_fps"] == 256
    assert body["power"]["warning"] is None or "A" in body["power"]["warning"]


def test_the_setup_choices_for_an_unknown_device_are_a_404(client):
    assert client.get("/api/v2/devices/device_9/output/setup").status_code == 404


def test_a_valid_change_is_accepted_as_an_operation(client, settings):
    response = client.patch("/api/v2/devices/device_0/output", json={"led_count": 60, "led_mid": 30})

    assert response.status_code == 202
    assert response.headers["Location"] == "/api/v2/operations/op1"
    assert settings.applied == [("device_0", {"led_count": 60, "led_mid": 30})]


def test_a_value_the_hardware_cannot_use_is_a_field_error_and_changes_nothing(client, settings):
    response = client.patch("/api/v2/devices/device_0/output", json={"output": {"output_raspi": {"led_pin": 4}}})

    assert response.status_code == 422
    assert response.get_json()["errors"][0]["field"] == "output.output_raspi.led_pin"
    assert settings.applied == []


def test_settings_outside_the_output_are_rejected(client, settings):
    assert client.patch("/api/v2/devices/device_0/output", json={"fps": 30}).status_code == 422
    assert settings.applied == []


def test_an_empty_change_is_rejected(client):
    assert client.patch("/api/v2/devices/device_0/output", json={}).status_code == 422


def test_retry_starts_the_output_again_as_an_operation(client, settings):
    response = client.post("/api/v2/devices/device_0/output/retry", json={})

    assert response.status_code == 202
    assert settings.retried == ["device_0"]
