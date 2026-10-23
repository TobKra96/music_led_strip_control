import threading
from queue import Queue

import pytest

from mlsc.app import create_app
from mlsc.config_service import ConfigService
from mlsc.webserver.executer import Executer
from mlsc.webserver.webserver import register_api_blueprints

pytestmark = pytest.mark.integration

V1_DEVICE_KEYS = {"device_groups", "device_name", "effects", "fps", "led_brightness", "led_count", "led_mid", "led_strip", "output", "output_type"}
V1_GENERAL_KEYS = {
    "default_sample_rate", "device_groups", "device_id", "frames_per_buffer", "log_file_enabled", "log_level_console",
    "log_level_file", "max_frequency", "min_frequency", "min_volume_threshold", "n_fft_bins", "n_rolling_history", "webserver_port",
}


@pytest.fixture
def executer(config_dir, monkeypatch):  # ruff: ignore[unused-function-argument]
    """Real executers over a config in a temporary dir, with the fake audio backend (devices 0 `Fake Mic`, 1 `Fake Monitor`)."""
    monkeypatch.delattr(ConfigService, "current_instance", raising=False)
    instance = Executer(threading.Lock(), Queue(), Queue(), Queue(), "fake")
    monkeypatch.setattr(Executer, "instance", instance, raising=False)
    return instance


@pytest.fixture
def client(executer):  # ruff: ignore[unused-function-argument]
    app = create_app()
    app.config["AUTH_ENABLED"] = False
    app.secret_key = "test"  # ruff: ignore[hardcoded-password-string]
    register_api_blueprints(app)
    return app.test_client()


@pytest.fixture
def device(executer):
    return executer.device_executer.create_new_device()["device_id"]


def device_config(executer, device_id):
    return executer.device_settings_executer.get_device_settings(device_id)["settings"]


def post_device(client, device, settings):
    return client.post("/api/settings/device", json={"device": device, "settings": settings})


def test_device_settings_show_the_v1_keys_with_a_derived_led_strip(client, device):
    settings = client.get("/api/settings/device", query_string={"device": device}).get_json()["settings"]

    assert set(settings) == V1_DEVICE_KEYS
    assert settings["led_strip"] == "ws2812_strip"


@pytest.mark.parametrize(("led_strip", "triple"), [
    ("ws2811_strip_bgr", ("ws2811", "bgr", False)),
    ("sk6812_strip", ("sk6812", "grb", False)),
    ("sk6812_strip_rgbw", ("sk6812", "rgb", True)),
])
def test_posting_a_led_strip_sets_chip_family_colour_order_and_white_channel(client, executer, device, led_strip, triple):
    response = post_device(client, device, {"led_strip": led_strip})

    config = device_config(executer, device)
    assert response.get_json() == {"device": device, "settings": {"led_strip": led_strip}}
    assert (config["chip_family"], config["colour_order"], config["white_channel"]) == triple
    assert "led_strip" not in config
    assert client.get("/api/settings/device", query_string={"device": device, "setting_key": "led_strip"}).get_json() == {
        "device": device, "setting_key": "led_strip", "setting_value": led_strip,
    }


@pytest.mark.parametrize("led_strip", ["sk6812w_strip", "sk6812_strip_grbw", "sk6812_shift_wmask"])
def test_strips_with_the_same_settings_read_back_as_sk6812w_strip(client, device, led_strip):
    post_device(client, device, {"led_strip": led_strip})

    response = client.get("/api/settings/device", query_string={"device": device, "setting_key": "led_strip"})

    assert response.get_json()["setting_value"] == "sk6812w_strip"


def test_a_strip_with_no_v1_name_reads_back_as_the_default_of_its_chip(client, executer, device):
    executer.device_settings_executer.set_device_settings(device, {"colour_order": "rgb"})

    response = client.get("/api/settings/device", query_string={"device": device, "setting_key": "led_strip"})

    assert response.get_json()["setting_value"] == "ws2812_strip"


def test_excluding_led_strip_leaves_the_other_v1_keys(client, device):
    response = client.get("/api/settings/device", query_string={"device": device, "excluded_key": "led_strip"}).get_json()

    assert response["excluded_key"] == "led_strip"
    assert set(response["settings"]) == V1_DEVICE_KEYS - {"led_strip"}


@pytest.mark.parametrize("settings", [{"chip_family": "ws2812"}, {"led_strip": "nope"}])
def test_device_settings_stay_frozen_to_the_v1_keys(client, executer, device, settings):
    before = device_config(executer, device)

    assert post_device(client, device, settings).status_code == 422
    assert device_config(executer, device) == before


def test_v4_only_device_keys_are_not_readable_through_v1(client, device):
    response = client.get("/api/settings/device", query_string={"device": device, "setting_key": "chip_family"})

    assert response.status_code == 422


def test_general_settings_show_the_v1_keys_from_the_audio_section(client, executer):
    executer.general_settings_executer.set_general_setting({}, {"device_name": "Fake Monitor", "sample_rate": 44100})

    settings = client.get("/api/settings/general").get_json()["setting_value"]

    assert set(settings) == V1_GENERAL_KEYS
    assert settings["device_id"] == 1
    assert settings["default_sample_rate"] == 44100


def test_general_settings_without_a_named_microphone_report_minus_one(client):
    assert client.get("/api/settings/general", query_string={"setting_key": "device_id"}).get_json() == {
        "setting_key": "device_id", "setting_value": -1,
    }


def test_posting_microphone_keys_edits_the_audio_section_and_refreshes(client, executer):
    posted = {
        "device_id": 1, "default_sample_rate": 44100, "frames_per_buffer": 256,
        "min_frequency": 60, "max_frequency": 12000, "min_volume_threshold": 0.01,
    }
    executer.general_settings_executer.notification_queue_out.queue.clear()

    response = client.post("/api/settings/general", json={"settings": posted})

    audio = executer.general_settings_executer.get_audio_settings()
    assert response.get_json() == {"settings": posted}
    assert (audio["device_name"], audio["host_api"]) == ("Fake Monitor", None)
    assert (audio["sample_rate"], audio["frames_per_buffer"], audio["min_frequency"], audio["max_frequency"]) == (44100, 256, 60, 12000)
    assert audio["min_volume_threshold"] == pytest.approx(0.01)
    assert not executer.general_settings_executer.notification_queue_out.empty()
    assert client.get("/api/settings/general").get_json()["setting_value"]["device_id"] == 1


@pytest.mark.parametrize("device_id", [-1, 42])
def test_an_unknown_or_missing_microphone_falls_back_to_the_system_default(client, executer, device_id):
    executer.general_settings_executer.set_general_setting({}, {"device_name": "Fake Mic", "host_api": "ALSA"})

    client.post("/api/settings/general", json={"settings": {"device_id": device_id}})

    audio = executer.general_settings_executer.get_audio_settings()
    assert (audio["device_name"], audio["host_api"]) == (None, None)


def test_other_general_settings_still_go_to_general_settings(client):
    client.post("/api/settings/general", json={"settings": {"n_fft_bins": 12}})

    assert client.get("/api/settings/general", query_string={"setting_key": "n_fft_bins"}).get_json()["setting_value"] == 12


def test_led_strips_resource_keeps_the_frozen_display_names(client):
    strips = client.get("/api/resources/led-strips").get_json()

    assert len(strips) == 16
    assert strips["ws2812_strip"] == "ws281x_default"
    assert strips["sk6812_strip"] == "sk6812_default"
    assert strips["sk6812w_strip"] == "sk6812w_default"
    assert strips["ws2811_strip_bgr"] == "ws281x_bgr"
    assert strips["sk6812_strip_grbw"] == "sk6812_strip_grbw"


def test_audio_devices_resource_is_unchanged(client):
    assert client.get("/api/resources/audio-devices").get_json() == {
        "0": "0 - Fake Mic - 44100 Hz", "1": "1 - Fake Monitor - 48000 Hz",
    }


def test_v1_responses_carry_deprecation_headers_and_v2_ones_do_not(client):
    v1 = client.get("/api/resources/colors")
    v2 = client.get("/api/v2/devices")

    assert v1.headers["Deprecation"].startswith("@")
    assert '</api/v2/openapi.json>; rel="successor-version"' in v1.headers.getlist("Link")
    assert "Deprecation" not in v2.headers
    assert "Deprecation" not in client.get("/api/").headers
    assert "Deprecation" not in client.get("/api/no-such-path").headers


def test_v1_spec_is_its_own_document_with_every_operation_deprecated(client):
    spec = client.get("/openapi.json").get_json()

    assert spec["paths"]
    assert not [path for path in spec["paths"] if path.startswith("/api/v2/") or not path.startswith("/api/") or path == "/api/"]
    operations = [operation for item in spec["paths"].values() for operation in item.values()]
    assert all(operation["deprecated"] is True for operation in operations)
    assert "Problem" not in spec.get("components", {}).get("schemas", {})


def test_v2_spec_still_lists_only_v2(client):
    spec = client.get("/api/v2/openapi.json").get_json()

    assert spec["paths"]
    assert all(path.startswith("/api/v2/") for path in spec["paths"])
