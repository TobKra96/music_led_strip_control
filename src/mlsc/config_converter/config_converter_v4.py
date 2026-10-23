import copy
from dataclasses import dataclass, field

from loguru import logger

from mlsc.config_converter.config_converter_base import ConfigConverterBase

# Old `led_strip` value -> (chip_family, colour_order, white_channel, lossy_reason).
# `rpi_ws281x` aliases: WS2812_STRIP and SK6812_STRIP are GRB, SK6812W_STRIP is GRBW.
LED_STRIP_MAPPING = {
    "ws2812_strip": ("ws2812", "grb", False, None),
    "sk6812_strip": ("sk6812", "grb", False, None),
    "sk6812w_strip": ("sk6812", "grb", True, None),
    "ws2811_strip_rgb": ("ws2811", "rgb", False, None),
    "ws2811_strip_rbg": ("ws2811", "rbg", False, None),
    "ws2811_strip_grb": ("ws2811", "grb", False, None),
    "ws2811_strip_gbr": ("ws2811", "gbr", False, None),
    "ws2811_strip_brg": ("ws2811", "brg", False, None),
    "ws2811_strip_bgr": ("ws2811", "bgr", False, None),
    "sk6812_strip_rgbw": ("sk6812", "rgb", True, None),
    "sk6812_strip_rbgw": ("sk6812", "rbg", True, None),
    "sk6812_strip_grbw": ("sk6812", "grb", True, None),
    "sk6812_strip_gbrw": ("sk6812", "gbr", True, None),
    "sk6812_strip_brgw": ("sk6812", "brg", True, None),
    "sk6812_strip_bgrw": ("sk6812", "bgr", True, None),
    "sk6812_shift_wmask": ("sk6812", "grb", True, "it shifts the white mask, which has no Chip Family and Colour Order equivalent"),
}
FALLBACK_LED_STRIP = ("ws2812", "grb", False)

DEFAULT_LED_PIN = 18
MAX_LED_PIN = 27  # Highest BCM GPIO on the 40-pin header.
DEFAULT_POWER_LIMIT = {"enabled": False, "supply_amps": 5.0, "ma_per_led": 60, "mode": "warn"}
DEFAULT_WIFI = {"hotspot_ssid": "mlsc", "mode": "client", "setup_fallback": True}


@dataclass
class MigrationReport:
    """What a Config Migration changed and which values could not be carried over exactly."""

    from_version: int = 0
    to_version: int = 0
    entries: list = field(default_factory=list)

    @property
    def has_warnings(self) -> bool:
        return any(entry["level"] == "warning" for entry in self.entries)

    def add(self, level, code, path, message, original=None) -> None:
        self.entries.append({"level": level, "code": code, "path": path, "message": message, "original": original})
        logger.log(level.upper(), f"Config migration: {message} ({path})")

    def extend(self, other: "MigrationReport") -> None:
        self.entries.extend(other.entries)
        self.to_version = other.to_version

    def to_dict(self) -> dict:
        return {"from_version": self.from_version, "to_version": self.to_version, "entries": copy.deepcopy(self.entries)}


class ConfigConverterV4(ConfigConverterBase):
    """Config V4 splits `led_strip` into chip family and colour order and adds audio, wifi, power and id sections."""

    def __init__(self) -> None:
        self.from_version = 3
        self.to_version = 4

    def upgrade(self, old_config: dict, audio_devices: list | None = None) -> tuple[dict, MigrationReport]:
        """Upgrade config from version 3 to version 4 without touching the input or any file.

        `audio_devices` is a list of `{"index", "name", "host_api"}` dicts used to resolve the old microphone index.
        """
        config = copy.deepcopy(old_config)
        report = MigrationReport(from_version=self.from_version, to_version=self.to_version)

        general_settings = config.setdefault("general_settings", {})
        self.convert_devices(config, report)
        self.add_audio_section(config, general_settings, audio_devices, report)
        self.drop_legacy_keys(config, general_settings, report)
        config.setdefault("wifi", copy.deepcopy(DEFAULT_WIFI))
        config["id_counters"] = self.id_counters(config)
        config["version"] = 4

        return config, report

    def convert_devices(self, config: dict, report: MigrationReport) -> None:
        if "default_device" in config:
            self.convert_device(config["default_device"], "default_device", report)
        for device_id, device in config.get("device_configs", {}).items():
            self.convert_device(device, f"device_configs.{device_id}", report)

    def convert_device(self, device: dict, path: str, report: MigrationReport) -> None:
        self.convert_led_strip(device, path, report)
        device.setdefault("gpio_backend", "auto")
        device.setdefault("power_limit", copy.deepcopy(DEFAULT_POWER_LIMIT))

        raspi = device.get("output", {}).get("output_raspi")
        if raspi is not None and "led_pin" in raspi:
            raspi["led_pin"] = self.validated_led_pin(raspi["led_pin"], f"{path}.output.output_raspi.led_pin", report)

    @staticmethod
    def convert_led_strip(device: dict, path: str, report: MigrationReport) -> None:
        led_strip = device.pop("led_strip", None)
        if led_strip is not None:
            report.add("info", "led_strip_removed", f"{path}.led_strip", f"Replaced LED strip {led_strip!r} by chip family, colour order and white channel.", led_strip)

        if "chip_family" in device:
            return

        mapping = LED_STRIP_MAPPING.get(led_strip)

        if mapping is None:
            chip_family, colour_order, white_channel = FALLBACK_LED_STRIP
            report.add("warning", "led_strip_unknown", f"{path}.led_strip",
                       f"Unknown LED strip {led_strip!r}, using {chip_family}/{colour_order}.", led_strip)
        else:
            chip_family, colour_order, white_channel, lossy_reason = mapping
            if lossy_reason:
                report.add("warning", "led_strip_lossy", f"{path}.led_strip",
                           f"LED strip {led_strip!r} mapped to the nearest {chip_family}/{colour_order}: {lossy_reason}.", led_strip)

        device["chip_family"] = chip_family
        device["colour_order"] = colour_order
        device["white_channel"] = white_channel

    @staticmethod
    def validated_led_pin(led_pin, path: str, report: MigrationReport) -> int:
        pin = None
        if isinstance(led_pin, int) and not isinstance(led_pin, bool):
            pin = led_pin
        elif isinstance(led_pin, str) and led_pin.strip().isdigit():
            pin = int(led_pin)
        if pin is not None and 0 <= pin <= MAX_LED_PIN:
            return pin

        report.add("warning", "led_pin_invalid", path, f"Invalid LED pin {led_pin!r}, using GPIO {DEFAULT_LED_PIN}.", led_pin)
        return DEFAULT_LED_PIN

    @staticmethod
    def add_audio_section(config: dict, general_settings: dict, audio_devices: list | None, report: MigrationReport) -> None:
        if "audio" in config:
            return

        device_name = None
        host_api = None
        index = general_settings.get("device_id", -1)

        if index != -1:
            match = next((d for d in audio_devices or [] if d.get("index") == index), None)
            if match is not None:
                device_name, host_api = match["name"], match.get("host_api")
            else:
                report.add("warning", "audio_device_unresolved", "general_settings.device_id",
                           f"Microphone index {index!r} could not be resolved, using the system default.", index)

        config["audio"] = {
            "source": "device",
            "device_name": device_name,
            "host_api": host_api,
            "gain": 1.0,
            "sample_rate": general_settings.get("default_sample_rate", 48000),
            "frames_per_buffer": general_settings.get("frames_per_buffer", 512),
            "min_frequency": general_settings.get("min_frequency", 50),
            "max_frequency": general_settings.get("max_frequency", 16000),
            "min_volume_threshold": general_settings.get("min_volume_threshold", 0.001),
        }

    @staticmethod
    def drop_legacy_keys(config: dict, general_settings: dict, report: MigrationReport) -> None:
        if "led_strips" in config:
            report.add("info", "led_strips_removed", "led_strips", "Removed the LED strip table, which chip family and colour order replace.", config.pop("led_strips"))
        if "device_id" in general_settings:
            report.add("info", "device_id_removed", "general_settings.device_id",
                       "Removed the microphone index, which the audio device name replaces.", general_settings.pop("device_id"))

    @staticmethod
    def id_counters(config: dict) -> dict:
        """Next free `device_N` / `group_N` number, one past the highest ever seen so ids are never reused."""
        existing = config.get("id_counters", {})

        def next_free(keys, prefix, stored):
            numbers = [int(key[len(prefix):]) for key in keys if key.startswith(prefix) and key[len(prefix):].isdigit()]
            return max([stored, *(n + 1 for n in numbers)])

        return {
            "device": next_free(config.get("device_configs", {}), "device_", existing.get("device", 0)),
            "group": next_free(config.get("general_settings", {}).get("device_groups", {}), "group_", existing.get("group", 0)),
        }
