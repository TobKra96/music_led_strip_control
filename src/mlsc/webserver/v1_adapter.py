"""Adapters that keep the `/api/*` (v1) payloads frozen over the v4 config.

v1 clients know `led_strip` and a numeric microphone `device_id`, and edit the microphone under `general_settings`.
The v4 config has `chip_family`, `colour_order` and `white_channel` per device, and an `audio` section. These functions
translate in both directions so the executers and the config never see the v1 names.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from mlsc.config_converter.config_converter_v4 import LED_STRIP_MAPPING

if TYPE_CHECKING:
    from mlsc.audio_device import AudioDevice

# Display names of the old `led_strips` resource, frozen for `GET /api/resources/led-strips`.
LED_STRIP_NAMES = {
    "sk6812_shift_wmask": "sk6812_shift_wmask",
    "sk6812_strip": "sk6812_default",
    "sk6812_strip_bgrw": "sk6812_strip_bgrw",
    "sk6812_strip_brgw": "sk6812_strip_brgw",
    "sk6812_strip_gbrw": "sk6812_strip_gbrw",
    "sk6812_strip_grbw": "sk6812_strip_grbw",
    "sk6812_strip_rbgw": "sk6812_strip_rbgw",
    "sk6812_strip_rgbw": "sk6812_strip_rgbw",
    "sk6812w_strip": "sk6812w_default",
    "ws2811_strip_bgr": "ws281x_bgr",
    "ws2811_strip_brg": "ws281x_brg",
    "ws2811_strip_gbr": "ws281x_gbr",
    "ws2811_strip_grb": "ws281x_grb",
    "ws2811_strip_rbg": "ws281x_rbg",
    "ws2811_strip_rgb": "ws281x_rgb",
    "ws2812_strip": "ws281x_default",
}

# Device settings that did not exist in v1; hidden from v1 responses and rejected in v1 requests.
V4_ONLY_DEVICE_KEYS = ("chip_family", "colour_order", "white_channel", "gpio_backend", "power_limit")

# v1 `general_settings` key -> `audio` key, for the microphone settings that moved.
MICROPHONE_KEYS = {
    "default_sample_rate": "sample_rate",
    "frames_per_buffer": "frames_per_buffer",
    "min_frequency": "min_frequency",
    "max_frequency": "max_frequency",
    "min_volume_threshold": "min_volume_threshold",
}

NO_DEVICE_ID = -1

# Several v1 names share one triple (`sk6812w_strip`, `sk6812_strip_grbw`, `sk6812_shift_wmask`); the first in the mapping wins.
_STRIP_FOR_SETTINGS: dict[tuple[str, str, bool], str] = {}
for _name, (_chip, _order, _white, _) in LED_STRIP_MAPPING.items():
    _STRIP_FOR_SETTINGS.setdefault((_chip, _order, _white), _name)

# A triple v1 cannot name (for example a WS2812 in RGB order) is reported as the plain strip of its chip.
_DEFAULT_STRIP_FOR_CHIP = {"ws2812": "ws2812_strip", "sk6812": "sk6812_strip"}


def led_strip_to_settings(led_strip: str) -> dict:
    chip_family, colour_order, white_channel, _ = LED_STRIP_MAPPING[led_strip]
    return {"chip_family": chip_family, "colour_order": colour_order, "white_channel": white_channel}


def led_strip_from_settings(chip_family: str, colour_order: str, white_channel: bool) -> str:
    white_channel = white_channel and chip_family == "sk6812"  # Only sk6812 strips have a white channel.
    return _STRIP_FOR_SETTINGS.get((chip_family, colour_order, white_channel)) or _DEFAULT_STRIP_FOR_CHIP[chip_family]


def device_settings_to_v1(settings: dict) -> dict:
    """Return the v1 view of a device's settings: no v4-only keys, plus the derived `led_strip`."""
    view = {key: value for key, value in settings.items() if key not in V4_ONLY_DEVICE_KEYS}
    view["led_strip"] = led_strip_from_settings(settings["chip_family"], settings["colour_order"], settings["white_channel"])
    return view


def device_settings_from_v1(settings: dict) -> dict:
    """Return v1 device settings as v4 device settings."""
    settings = dict(settings)
    if "led_strip" in settings:
        settings.update(led_strip_to_settings(settings.pop("led_strip")))
    return settings


def audio_device_id(device_name: str | None, audio_devices: list[AudioDevice]) -> int:
    """Return the id of the device called `device_name`, or -1 for the system default."""
    return next((device.device_id for device in audio_devices if device.name == device_name), NO_DEVICE_ID)


def general_settings_to_v1(general: dict, audio: dict, audio_devices: list[AudioDevice]) -> dict:
    """Return the v1 `general_settings`, with the microphone keys read from the `audio` section."""
    view = dict(general)
    view.update({v1_key: audio[key] for v1_key, key in MICROPHONE_KEYS.items()})
    view["device_id"] = audio_device_id(audio["device_name"], audio_devices)
    return view


def general_settings_from_v1(settings: dict, audio_devices: list[AudioDevice]) -> tuple[dict, dict]:
    """Split v1 general settings into the `general_settings` and the `audio` changes they stand for."""
    general = {key: value for key, value in settings.items() if key not in MICROPHONE_KEYS and key != "device_id"}
    audio = {MICROPHONE_KEYS[key]: value for key, value in settings.items() if key in MICROPHONE_KEYS}
    if "device_id" in settings:
        match = next((device for device in audio_devices if device.device_id == settings["device_id"]), None)
        audio["device_name"] = match.name if match is not None and settings["device_id"] != NO_DEVICE_ID else None
        audio["host_api"] = None  # v1 cannot name a host API, so a stale one would never match the new device.
    return general, audio
