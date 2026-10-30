import copy
import json
from pathlib import Path

import pytest

from mlsc.config_migration import migrate_data
from mlsc.webserver.schemas.config_validator_service import ConfigValidatorService

pytestmark = pytest.mark.unit

GOLDEN = Path(__file__).parent / "golden"
GOLDEN_SOURCES = ["config_v1_real.json", "config_v2_real.json"]


def load(name):
    return json.loads((GOLDEN / name).read_text(encoding="utf-8"))


def errors(config, **kwargs):
    return ConfigValidatorService().errors(config, **kwargs)


@pytest.fixture
def config():
    return load("config_v2_real_v4.json")


@pytest.mark.parametrize("name", GOLDEN_SOURCES)
def test_golden_configs_migrate_to_a_valid_v4_config(name):
    migrated, _ = migrate_data(load(name))

    assert errors(migrated, allow_unknown_keys=True) == []


def test_version_other_than_4_is_rejected(config):
    config["version"] = 3
    assert errors(config)


@pytest.mark.parametrize(("path", "value"), [
    (("audio", "source"), "radio"),
    (("audio", "gain"), 0),
    (("audio", "sample_rate"), 0),
    (("audio", "frames_per_buffer"), -1),
    (("audio", "min_frequency"), -5),
    (("audio", "min_volume_threshold"), -0.1),
    (("wifi", "setup_fallback"), "yes"),
    (("id_counters", "device"), -1),
    (("id_counters", "group"), 1.5),
])
def test_out_of_range_top_level_section_values_are_rejected(config, path, value):
    config[path[0]][path[1]] = value
    assert errors(config)


@pytest.mark.parametrize(("key", "value"), [
    ("chip_family", "ws2813"),
    ("colour_order", "xyz"),
    ("white_channel", "no"),
])
def test_invalid_device_strip_fields_are_rejected(config, key, value):
    next(iter(config["device_configs"].values()))[key] = value
    assert errors(config)


@pytest.mark.parametrize(("key", "value"), [
    ("enabled", "on"),
    ("supply_amps", 0),
    ("ma_per_led", -1),
    ("mode", "kill"),
])
def test_invalid_power_limit_values_are_rejected(config, key, value):
    next(iter(config["device_configs"].values()))["power_limit"][key] = value
    assert errors(config)


def test_legacy_strip_and_microphone_keys_are_rejected(config):
    next(iter(config["device_configs"].values()))["led_strip"] = "ws2812_strip"
    assert errors(config)

    config = load("config_v2_real_v4.json")
    config["led_strips"] = {}
    assert errors(config)

    config = load("config_v2_real_v4.json")
    config["general_settings"]["device_id"] = 3
    assert errors(config)


def test_missing_v4_section_is_rejected(config):
    del config["audio"]
    assert errors(config)


def test_unknown_key_is_rejected_by_default(config):
    config["future_section"] = {"a": 1}
    assert errors(config)


def test_unknown_keys_are_accepted_when_preserved_but_known_keys_stay_checked(config):
    config["future_section"] = {"a": 1}
    next(iter(config["device_configs"].values()))["future_field"] = True
    assert errors(copy.deepcopy(config), allow_unknown_keys=True) == []

    config["audio"]["gain"] = 0
    assert errors(config, allow_unknown_keys=True)


def test_the_supply_voltage_of_the_power_limit_is_optional_and_positive(config):
    limit = next(iter(config["device_configs"].values()))["power_limit"]
    limit["supply_volts"] = 12
    assert not errors(config)
    limit["supply_volts"] = 0
    assert errors(config)
