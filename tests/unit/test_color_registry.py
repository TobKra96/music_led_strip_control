import copy
import json
from importlib import resources
from operator import itemgetter

import pytest

from mlsc.color_registry import (
    COLOUR,
    GRADIENT,
    entry_errors,
    find_name,
    find_usages,
    name_errors,
    registry,
    rename_usages,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def config():
    config = json.loads((resources.files("mlsc") / "config_template.json").read_text())
    config["device_configs"] = {
        "device_0": copy.deepcopy(config["default_device"]),
        "device_1": copy.deepcopy(config["default_device"]),
    }
    return config


# Naming rules


@pytest.mark.parametrize("name", ["red", "Café", "ünï", "my-grad_1", "two words", "a", "x" * 32, "123"])
def test_valid_names_are_accepted(name):
    assert name_errors(name) == []


@pytest.mark.parametrize("name", ["", " ", "  padded", "padded ", "x" * 33, "no/slash", "dot.", "emoji🙂", "tab\tname", "new\nline"])
def test_invalid_names_are_rejected(name):
    assert name_errors(name)


def test_non_string_names_are_rejected():
    assert name_errors(5)


def test_find_name_is_case_insensitive_and_returns_the_stored_spelling():
    assert find_name({"Sunset": [], "red": []}, "SUNSET") == "Sunset"
    assert find_name({"red": []}, "blue") is None


# Value rules


@pytest.mark.parametrize("value", [[0, 0, 0], [255, 128, 1]])
def test_valid_rgb_is_accepted(value):
    assert entry_errors(COLOUR, value) == []


@pytest.mark.parametrize("value", [[0, 0], [0, 0, 0, 0], [256, 0, 0], [-1, 0, 0], [1.5, 0, 0], ["1", 0, 0], [True, 0, 0], "red", None])
def test_invalid_rgb_is_rejected(value):
    assert entry_errors(COLOUR, value)


def test_gradient_needs_between_two_and_sixteen_stops():
    stop = [1, 2, 3]
    assert entry_errors(GRADIENT, [stop]) != []
    assert entry_errors(GRADIENT, [stop] * 2) == []
    assert entry_errors(GRADIENT, [stop] * 16) == []
    assert entry_errors(GRADIENT, [stop] * 17) != []


def test_gradient_stops_are_validated():
    assert entry_errors(GRADIENT, [[1, 2, 3], [1, 2, 300]])
    assert entry_errors(GRADIENT, "spectral")


# Registry


def test_registry_marks_colour_and_gradient_settings_from_the_schema():
    reg = registry()

    assert reg["effect_advanced_scroll"]["bass_color"] == COLOUR
    assert reg["effect_gradient"]["gradient"] == GRADIENT
    assert reg["effect_bars"]["color_mode"] == GRADIENT


def test_registry_leaves_other_settings_out():
    assert "speed" not in registry()["effect_gradient"]
    assert "mirror" not in registry()["effect_gradient"]


def test_every_registry_entry_exists_in_the_template(config):
    for effect, settings in registry().items():
        for setting in settings:
            assert setting in config["default_device"]["effects"][effect]


# Usage scan


def test_unused_entry_has_no_usages(config):
    config["colors"]["mine"] = [1, 2, 3]
    assert find_usages(config, COLOUR, "mine") == []


def test_usage_scan_covers_every_effect_of_every_device(config):
    config["colors"]["mine"] = [1, 2, 3]
    config["device_configs"]["device_0"]["effects"]["effect_beat"]["color"] = "mine"
    config["device_configs"]["device_1"]["effects"]["effect_pendulum"]["color"] = "mine"
    config["device_configs"]["device_1"]["effects"]["effect_advanced_scroll"]["bass_color"] = "mine"

    usages = find_usages(config, COLOUR, "mine")

    assert sorted(usages, key=itemgetter("target", "effect")) == [
        {"target": "device_0", "effect": "effect_beat", "setting": "color"},
        {"target": "device_1", "effect": "effect_advanced_scroll", "setting": "bass_color"},
        {"target": "device_1", "effect": "effect_pendulum", "setting": "color"},
    ]


def test_usage_scan_does_not_mix_up_kinds(config):
    config["gradients"]["shared"] = [[0, 0, 0], [1, 1, 1]]
    config["colors"]["shared"] = [1, 1, 1]
    config["device_configs"]["device_0"]["effects"]["effect_gradient"]["gradient"] = "shared"

    assert find_usages(config, COLOUR, "shared") == []
    assert find_usages(config, GRADIENT, "shared") == [{"target": "device_0", "effect": "effect_gradient", "setting": "gradient"}]


def test_usage_scan_sees_inactive_effects(config):
    config["device_configs"]["device_0"]["effects"]["last_effect"] = "effect_off"
    config["device_configs"]["device_0"]["effects"]["effect_wave"]["color_flash"] = "pink"

    assert {"target": "device_0", "effect": "effect_wave", "setting": "color_flash"} in find_usages(config, COLOUR, "pink")


def test_usage_scan_tolerates_devices_missing_an_effect(config):
    del config["device_configs"]["device_0"]["effects"]["effect_beat"]
    find_usages(config, COLOUR, "red")


# Rename rewrite


def test_rename_rewrites_every_usage_and_the_entry(config):
    config["gradients"]["mine"] = [[0, 0, 0], [9, 9, 9]]
    config["device_configs"]["device_0"]["effects"]["effect_gradient"]["gradient"] = "mine"
    config["device_configs"]["device_1"]["effects"]["effect_bars"]["color_mode"] = "mine"

    rename_usages(config, GRADIENT, "mine", "yours")

    assert config["device_configs"]["device_0"]["effects"]["effect_gradient"]["gradient"] == "yours"
    assert config["device_configs"]["device_1"]["effects"]["effect_bars"]["color_mode"] == "yours"
    assert find_usages(config, GRADIENT, "mine") == []
    assert len(find_usages(config, GRADIENT, "yours")) == 2


def test_rename_leaves_other_values_and_kinds_alone(config):
    config["device_configs"]["device_0"]["effects"]["effect_beat"]["color"] = "red"
    config["device_configs"]["device_0"]["effects"]["effect_gradient"]["gradient"] = "red"
    rename_usages(config, COLOUR, "red", "crimson")

    assert config["device_configs"]["device_0"]["effects"]["effect_beat"]["color"] == "crimson"
    assert config["device_configs"]["device_0"]["effects"]["effect_gradient"]["gradient"] == "red"
    assert config["device_configs"]["device_1"]["effects"]["effect_beat"]["color"] == "crimson"


def test_rename_returns_the_rewritten_usages(config):
    config["device_configs"]["device_0"]["effects"]["effect_beat"]["color"] = "blue"

    rewritten = rename_usages(config, COLOUR, "blue", "navy")

    assert {"target": "device_0", "effect": "effect_beat", "setting": "color"} in rewritten
