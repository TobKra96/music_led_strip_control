from __future__ import annotations

import time
from collections.abc import Callable
from copy import deepcopy

from mlsc import operations, strip_pattern, strip_preview
from mlsc.diagnosis import Status
from mlsc.gpio_backends import GpioBackendError, select_backend
from mlsc.host import Host
from mlsc.operations import Operation, RetryPolicy
from mlsc.output_setup import LOCAL_GPIO, OUTPUTS, validate_output
from mlsc.strip_pattern import Pattern
from mlsc.webserver.executer_base import ExecuterBase, merge, update
from mlsc.webserver.messages import DeviceNotFound, SettingNotFound

# How long the output process has to report on a new config, and how often it is asked.
REPORT_SECONDS = 5.0
POLL_SECONDS = 0.1
TEST_FRAME_SECONDS = 3


class OutputApplyError(Exception):
    """Why an applied Output change did not work."""


class DeviceSettingsExecuter(ExecuterBase):
    # Injectable for tests, so the apply waits never sleep for real.
    _clock: Callable[[], float] = staticmethod(time.monotonic)
    _sleep: Callable[[float], None] = staticmethod(time.sleep)
    _host: Host | None = None
    # Where the Diagnoses of the output processes come from: the Strip Preview hub unless a test brings its own.
    _diagnoses = None

    def get_device_setting(self, device: str, setting_key: str) -> dict | DeviceNotFound:
        """Return the value of a setting for a device."""
        device_configs = self._config["device_configs"]

        if device not in device_configs:
            return DeviceNotFound

        return {
            "device": device,
            "setting_key": setting_key,
            "setting_value": device_configs[device][setting_key]
        }

    def get_device_settings(self, device: str, excluded_setting: str = "") -> dict | DeviceNotFound:
        """Return all settings for a device. If `excluded_setting` is given, it will be excluded from the result."""
        device_configs = self._config["device_configs"]

        if device not in device_configs:
            return DeviceNotFound

        if excluded_setting:
            device_settings = deepcopy(device_configs[device])
            device_settings.pop(excluded_setting, None)

            return {
                "device": device,
                "excluded_key": excluded_setting,
                "settings": device_settings
            }

        return {
            "device": device,
            "settings": device_configs[device]
        }

    def set_device_settings(self, device: str, settings: dict) -> dict | DeviceNotFound:
        """Set any number of settings for a device."""
        device_configs = self._config["device_configs"]

        if device not in device_configs:
            return DeviceNotFound

        update(device_configs[device], settings)

        self.save_config()
        self.refresh_device(device)

        return {
            "device": device,
            "settings": settings
        }

    def get_all_output_type_settings(self, device: str) -> dict | DeviceNotFound:
        """Return all output type settings for a device."""
        device_configs = self._config["device_configs"]

        if device not in device_configs:
            return DeviceNotFound

        # Flatten output type settings, one level deep.
        settings = {k: v for settings in device_configs[device]["output"].values() for k, v in settings.items()}

        return {
            "device": device,
            "output_settings": settings
        }

    def get_output_type_device_setting(
        self,
        device: str,
        output_type_key: str,
        setting_key: str
    ) -> dict | DeviceNotFound | SettingNotFound:
        """Return a single output type setting for a device."""
        device_configs = self._config["device_configs"]

        if device not in device_configs:
            return DeviceNotFound

        if setting_key not in device_configs[device]["output"][output_type_key]:
            return SettingNotFound  # Check if only correct settings are passed for a given output type.

        return {
            "device": device,
            "output_type_key": output_type_key,
            "setting_key": setting_key,
            "setting_value": device_configs[device]["output"][output_type_key][setting_key]
        }

    def set_output_type_device_settings(self, device: str, output_type_key: str, settings: dict) -> dict | DeviceNotFound | SettingNotFound:
        """Set output type settings for a device."""
        device_configs = self._config["device_configs"]

        if device not in device_configs:
            return DeviceNotFound

        if any(setting_key not in device_configs[device]["output"][output_type_key] for setting_key in settings):
            return SettingNotFound  # Check if only correct settings are passed for a given output type.

        update(device_configs[device]["output"][output_type_key], settings)

        self.save_config()
        self.refresh_device(device)

        return {
            "device": device,
            "output_type_key": output_type_key,
            "settings": settings
        }

    # Output setup

    def validate_output(self, device: str, patch: dict) -> list[dict] | DeviceNotFound:
        """Field errors for the settings the hardware cannot use, judged on the Device as it would be after `patch`."""
        device_configs = self._config["device_configs"]
        if device not in device_configs:
            return DeviceNotFound
        return validate_output(merge(deepcopy(device_configs[device]), patch), self._host)

    def derive_channel(self, device: str, patch: dict) -> dict:
        """Add the PWM channel that belongs to the GPIO pin in `patch`, so the user never picks it."""
        raspi = patch.get("output", {}).get(LOCAL_GPIO, {})
        if "led_pin" not in raspi:
            return patch
        try:
            channel = select_backend(self._host).pin_channels.get(raspi["led_pin"])
        except GpioBackendError:
            return patch
        return patch if channel is None else merge(deepcopy(patch), {"output": {LOCAL_GPIO: {"led_channel": channel}}})

    def apply_output(self, device: str, patch: dict) -> Operation | DeviceNotFound:
        """Save `patch` and restart the Device as an Operation, tried once, that rolls back to the previous config when the Output does not work."""
        device_configs = self._config["device_configs"]
        if device not in device_configs:
            return DeviceNotFound
        previous = deepcopy(device_configs[device])
        target = merge(deepcopy(previous), self.derive_channel(device, patch))
        return operations.registry.start("output", *self._steps(device, previous, target), policy=RetryPolicy(attempts=1))

    def retry_output(self, device: str) -> Operation | DeviceNotFound:
        """Start the Device with its stored config again, for after the cause of a fallback to the Mock Output is fixed."""
        device_configs = self._config["device_configs"]
        if device not in device_configs:
            return DeviceNotFound
        stored = deepcopy(device_configs[device])
        return operations.registry.start("output", *self._steps(device, stored, stored), policy=RetryPolicy())

    def _steps(self, device: str, previous: dict, target: dict) -> tuple[Callable, Callable, Callable]:
        reported = 0

        def apply() -> None:
            nonlocal reported
            latest = self._latest_diagnosis(device)
            reported = latest[0] if latest else 0
            self._save_device(device, target)

        def verify() -> bool:
            failure = OUTPUTS[target["output_type"]].diagnose(target, self._host or Host())
            if failure.status is Status.ERROR:
                raise OutputApplyError(self._describe(failure.message, failure.suggested_fix))
            if self._wait_for_report(device, reported):
                self._show_test_frame(device)
            return True

        def rollback() -> None:
            self._save_device(device, previous)

        return apply, verify, rollback

    def _save_device(self, device: str, device_config: dict) -> None:
        self._config["device_configs"][device] = deepcopy(device_config)
        self.save_config()
        self.refresh_device(device)

    def _latest_diagnosis(self, device: str) -> tuple[int, dict] | None:
        source = self._diagnoses or strip_preview.hub
        return source.latest(device) if source is not None else None

    def _wait_for_report(self, device: str, after: int) -> bool:
        """Wait for the output process to report on the new config. False when nothing reports, as in a headless setup."""
        if (self._diagnoses or strip_preview.hub) is None:
            return False
        deadline = self._clock() + REPORT_SECONDS
        while self._clock() < deadline:
            latest = self._latest_diagnosis(device)
            if latest and latest[0] > after:
                payload = latest[1]
                if payload["status"] != Status.OK.value:
                    raise OutputApplyError(self._describe(payload["message"], payload["suggested_fix"]))
                return True
            self._sleep(POLL_SECONDS)
        msg = "The output did not report back in time."
        raise OutputApplyError(msg)

    def _show_test_frame(self, device: str) -> None:
        if strip_pattern.channel is not None:
            strip_pattern.channel.start(device, Pattern.markers, TEST_FRAME_SECONDS)

    @staticmethod
    def _describe(message: str, suggested_fix: str | None) -> str:
        return f"{message} {suggested_fix}" if suggested_fix else message
