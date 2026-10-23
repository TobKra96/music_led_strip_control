import copy
import json
from pathlib import Path

import pytest

from mlsc.config_converter.config_converter_service import ConfigConverterService
from mlsc.config_converter.config_converter_v4 import (
    LED_STRIP_MAPPING,
    ConfigConverterV4,
    MigrationReport,
)

pytestmark = pytest.mark.unit

GOLDEN = Path(__file__).parent / "golden"

LED_STRIP_VALUES = [
    "sk6812_strip_rgbw", "sk6812_strip_rbgw", "sk6812_strip_grbw", "sk6812_strip_gbrw", "sk6812_strip_brgw",
    "sk6812_strip_bgrw", "sk6812_shift_wmask", "ws2811_strip_rgb", "ws2811_strip_rbg", "ws2811_strip_grb",
    "ws2811_strip_gbr", "ws2811_strip_brg", "ws2811_strip_bgr", "ws2812_strip", "sk6812_strip", "sk6812w_strip",
]


def v3_config(**device_overrides):
    device = {"device_name": "Desk", "led_strip": "ws2812_strip", "output": {"output_raspi": {"led_pin": 18}}}
    device.update(device_overrides)
    return {
        "version": 3,
        "general_settings": {
            "device_id": -1, "device_groups": {"group_0": ["a"], "group_4": ["b"]},
            "default_sample_rate": 48000, "frames_per_buffer": 512, "min_frequency": 50, "max_frequency": 16000,
            "min_volume_threshold": 0.001,
        },
        "default_device": {"led_strip": "ws2812_strip", "output": {"output_raspi": {"led_pin": 18}}},
        "device_configs": {"device_0": device, "device_7": copy.deepcopy(device)},
    }


def upgrade(config, **kwargs):
    return ConfigConverterV4().upgrade(config, **kwargs)


def test_mapping_table_covers_exactly_the_16_led_strip_values():
    assert sorted(LED_STRIP_MAPPING) == sorted(LED_STRIP_VALUES)


@pytest.mark.parametrize("led_strip", LED_STRIP_VALUES)
def test_every_led_strip_value_maps_to_a_chip_family_and_colour_order(led_strip):
    config, _ = upgrade(v3_config(led_strip=led_strip))

    device = config["device_configs"]["device_0"]
    chip_family, colour_order, white_channel = LED_STRIP_MAPPING[led_strip][:3]
    assert (device["chip_family"], device["colour_order"], device["white_channel"]) == (chip_family, colour_order, white_channel)
    assert chip_family in {"ws2811", "ws2812", "sk6812"}
    assert sorted(colour_order) == ["b", "g", "r"]


@pytest.mark.parametrize(("led_strip", "expected"), [
    ("ws2812_strip", ("ws2812", "grb", False)),
    ("ws2811_strip_bgr", ("ws2811", "bgr", False)),
    ("sk6812_strip_brgw", ("sk6812", "brg", True)),
    ("sk6812w_strip", ("sk6812", "grb", True)),
    ("sk6812_strip", ("sk6812", "grb", False)),
])
def test_known_mappings(led_strip, expected):
    assert LED_STRIP_MAPPING[led_strip][:3] == expected


def test_lossless_mappings_do_not_warn():
    _, report = upgrade(v3_config(led_strip="ws2811_strip_rbg"))

    assert not [e for e in report.entries if e["level"] == "warning" and e["path"].startswith("device_configs")]


def test_lossy_mapping_warns_and_keeps_the_original_in_the_report():
    config, report = upgrade(v3_config(led_strip="sk6812_shift_wmask"))

    warnings = [e for e in report.entries if e["code"] == "led_strip_lossy"]
    assert len(warnings) == 2  # device_0 and device_7
    assert warnings[0]["level"] == "warning"
    assert warnings[0]["original"] == "sk6812_shift_wmask"
    assert warnings[0]["path"] == "device_configs.device_0.led_strip"
    assert config["device_configs"]["device_0"]["chip_family"] == "sk6812"


def test_unknown_led_strip_falls_back_with_a_warning_and_never_fails():
    config, report = upgrade(v3_config(led_strip="bogus"))

    device = config["device_configs"]["device_0"]
    assert (device["chip_family"], device["colour_order"]) == ("ws2812", "grb")
    assert any(e["code"] == "led_strip_unknown" and e["original"] == "bogus" for e in report.entries)


def test_legacy_keys_are_dropped_and_their_originals_kept_in_the_report():
    old = v3_config(led_strip="sk6812_strip_rgbw")
    old["led_strips"] = {"ws2812_strip": "ws281x_default"}
    old["general_settings"]["device_id"] = 3

    config, report = upgrade(old)

    assert "led_strip" not in config["device_configs"]["device_0"]
    assert "led_strip" not in config["default_device"]
    assert "led_strips" not in config
    assert "device_id" not in config["general_settings"]
    originals = {e["path"]: e["original"] for e in report.entries if e["code"].endswith("_removed")}
    assert originals["device_configs.device_0.led_strip"] == "sk6812_strip_rgbw"
    assert originals["led_strips"] == {"ws2812_strip": "ws281x_default"}
    assert originals["general_settings.device_id"] == 3


def test_default_device_is_converted_too():
    config, _ = upgrade(v3_config())

    assert config["default_device"]["chip_family"] == "ws2812"
    assert config["default_device"]["gpio_backend"] == "auto"


def test_new_device_fields_have_safe_defaults():
    config, _ = upgrade(v3_config())

    device = config["device_configs"]["device_0"]
    assert device["gpio_backend"] == "auto"
    assert device["power_limit"] == {"enabled": False, "supply_amps": 5.0, "ma_per_led": 60, "mode": "warn"}


def test_existing_power_limit_is_preserved():
    limit = {"enabled": True, "supply_amps": 2.0, "ma_per_led": 40, "mode": "limit"}
    config, _ = upgrade(v3_config(power_limit=limit))

    assert config["device_configs"]["device_0"]["power_limit"] == limit


@pytest.mark.parametrize(("led_pin", "expected"), [(18, 18), ("12", 12), (0, 0), (27, 27)])
def test_valid_led_pin_is_kept_as_an_int(led_pin, expected):
    config, report = upgrade(v3_config(output={"output_raspi": {"led_pin": led_pin}}))

    assert config["device_configs"]["device_0"]["output"]["output_raspi"]["led_pin"] == expected
    assert not [e for e in report.entries if e["code"] == "led_pin_invalid"]


@pytest.mark.parametrize("led_pin", [28, -1, "gpio18", None, True, 1.5])
def test_invalid_led_pin_falls_back_to_18_with_a_warning(led_pin):
    config, report = upgrade(v3_config(output={"output_raspi": {"led_pin": led_pin}}))

    assert config["device_configs"]["device_0"]["output"]["output_raspi"]["led_pin"] == 18
    warning = next(e for e in report.entries if e["code"] == "led_pin_invalid")
    assert warning["original"] == led_pin


def test_device_without_raspi_output_is_left_alone():
    config, _ = upgrade(v3_config(output={"output_udp": {"udp_client_ip": "1.2.3.4", "udp_client_port": 7777}}))

    assert config["device_configs"]["device_0"]["output"] == {"output_udp": {"udp_client_ip": "1.2.3.4", "udp_client_port": 7777}}


def test_mqtt_and_udp_keys_keep_names_and_values():
    output = {
        "output_mqtt": {"mqtt_broker": "broker", "mqtt_path": "led/a"},
        "output_udp": {"udp_client_ip": "1.2.3.4", "udp_client_port": 7777},
    }
    config, _ = upgrade(v3_config(output=copy.deepcopy(output)))

    assert config["device_configs"]["device_0"]["output"] == output


def test_audio_device_index_is_resolved_to_name_and_host_api():
    config = v3_config()
    config["general_settings"]["device_id"] = 3
    devices = [{"index": 3, "name": "Loopback", "host_api": "ALSA"}]

    new_config, report = upgrade(config, audio_devices=devices)

    audio = new_config["audio"]
    assert (audio["source"], audio["device_name"], audio["host_api"]) == ("device", "Loopback", "ALSA")
    assert not [e for e in report.entries if e["level"] == "warning" and e["path"] == "general_settings.device_id"]


@pytest.mark.parametrize("devices", [None, [], [{"index": 1, "name": "Other", "host_api": "ALSA"}]])
def test_unresolvable_audio_device_uses_system_default_with_a_warning(devices):
    config = v3_config()
    config["general_settings"]["device_id"] = 3

    new_config, report = upgrade(config, audio_devices=devices)

    assert new_config["audio"]["device_name"] is None
    assert new_config["audio"]["host_api"] is None
    warning = next(e for e in report.entries if e["code"] == "audio_device_unresolved")
    assert warning["original"] == 3


def test_no_microphone_marker_maps_to_system_default_without_a_warning():
    new_config, report = upgrade(v3_config())  # device_id == -1

    assert new_config["audio"]["device_name"] is None
    assert not [e for e in report.entries if e["code"] == "audio_device_unresolved"]


def test_audio_section_carries_over_settings_and_adds_gain():
    audio = upgrade(v3_config())[0]["audio"]

    assert audio["gain"] == pytest.approx(1.0)
    assert audio["sample_rate"] == 48000
    assert audio["frames_per_buffer"] == 512
    assert (audio["min_frequency"], audio["max_frequency"]) == (50, 16000)
    assert audio["min_volume_threshold"] == pytest.approx(0.001)


def test_wifi_section_has_no_passwords():
    wifi = upgrade(v3_config())[0]["wifi"]

    assert set(wifi) == {"hotspot_ssid", "mode", "setup_fallback"}
    assert wifi["setup_fallback"] is True


def test_existing_audio_and_wifi_sections_are_preserved():
    config = v3_config()
    config["audio"] = {"source": "browser"}
    config["wifi"] = {"mode": "hotspot"}

    new_config, _ = upgrade(config)

    assert new_config["audio"] == {"source": "browser"}
    assert new_config["wifi"] == {"mode": "hotspot"}


def test_id_counters_are_one_past_the_highest_existing_id():
    counters = upgrade(v3_config())[0]["id_counters"]

    assert counters == {"device": 8, "group": 5}


def test_id_counters_start_at_zero_for_an_empty_config():
    config = v3_config()
    config["device_configs"] = {}
    config["general_settings"]["device_groups"] = {}

    assert upgrade(config)[0]["id_counters"] == {"device": 0, "group": 0}


def test_version_is_bumped_to_4():
    assert upgrade(v3_config())[0]["version"] == 4


def test_converter_is_pure_and_does_not_mutate_its_input():
    config = v3_config(led_strip="sk6812_strip_rgbw")
    before = copy.deepcopy(config)

    upgrade(config)

    assert config == before


def test_report_is_structured_and_json_serialisable():
    _, report = upgrade(v3_config(led_strip="sk6812_shift_wmask"))

    assert isinstance(report, MigrationReport)
    assert (report.from_version, report.to_version) == (3, 4)
    assert report.has_warnings
    assert json.loads(json.dumps(report.to_dict()))["from_version"] == 3


def test_chain_returns_config_and_report_and_upgrade_keeps_returning_only_the_config():
    old = json.loads((GOLDEN / "config_v2_real.json").read_text())

    config, report = ConfigConverterService.migrate(copy.deepcopy(old))
    assert config["version"] == 4
    assert (report.from_version, report.to_version) == (2, 4)

    assert ConfigConverterService.upgrade(copy.deepcopy(old)) == config


def test_chain_does_not_rerun_on_a_v4_config():
    config, _ = upgrade(v3_config())

    again, report = ConfigConverterService.migrate(copy.deepcopy(config))

    assert again == config
    assert report.entries == []


@pytest.mark.parametrize("name", ["v1", "v2"])
def test_golden_real_configs_migrate_to_the_expected_v4(name):
    old = json.loads((GOLDEN / f"config_{name}_real.json").read_text())
    expected = json.loads((GOLDEN / f"config_{name}_real_v4.json").read_text())

    config, report = ConfigConverterService.migrate(old, audio_devices=[{"index": 3, "name": "USB Mic", "host_api": "ALSA"}])

    assert config == expected
    assert report.from_version == (1 if name == "v1" else 2)
    assert {d["chip_family"] for d in config["device_configs"].values()} == {"sk6812", "ws2811"}
    assert config["audio"]["device_name"] == "USB Mic"
