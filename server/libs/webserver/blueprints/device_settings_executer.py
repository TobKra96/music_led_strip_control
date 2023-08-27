from __future__ import annotations

from copy import deepcopy

from libs.webserver.executer_base import ExecuterBase, update
from libs.webserver.messages import DeviceNotFound, SettingNotFound


class DeviceSettingsExecuter(ExecuterBase):

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
