from __future__ import annotations

from libs.webserver.executer_base import ExecuterBase
from libs.webserver.messages import BadRequest, DeviceNotFound, NotFound, SettingNotFound


class EffectSettingsExecuter(ExecuterBase):

    # TODO: Fix returning "all_devices" instead of actual device ID.

    def get_effect_setting(self, device: str, effect: str, setting_key: str) -> dict | DeviceNotFound | SettingNotFound:
        """Return the value of a setting for an effect."""
        # TODO: Get the effect setting for groups.
        # selected_device = device
        # if device == self.all_devices_id:
        #     selected_device = next(iter(self._config["device_configs"]))

        if device not in self._config["device_configs"]:
            return DeviceNotFound

        if setting_key not in self._config["device_configs"][device]["effects"][effect]:
            return SettingNotFound

        return {
            "device": device,
            "effect": effect,
            "setting_key": setting_key,
            "setting_value": self._config["device_configs"][device]["effects"][effect][setting_key]
        }

    def get_effect_settings(self, device: str, effect: str) -> dict | DeviceNotFound:
        """Return all settings for an effect."""
        # settings = dict()
        # selected_device = device

        # if device == self.all_devices_id:
        #     selected_device = next(iter(self._config["device_configs"]))

        # for effect_setting_key in self._config["device_configs"][selected_device]["effects"][effect]:
        #     settings[effect_setting_key] = self._config["device_configs"][selected_device]["effects"][effect][effect_setting_key]

        if device not in self._config["device_configs"]:
            return DeviceNotFound

        return {
            "device": device,
            "effect": effect,
            "settings": self._config["device_configs"][device]["effects"][effect]
        }

    def set_effect_settings(self, device: str, effect: str, settings: dict) -> dict | NotFound | BadRequest:
        """Set effect settings for a device."""
        # if device == self.all_devices_id:
        #     return self.set_effect_setting_for_all(effect, settings)

        if not settings:
            return BadRequest  # Don't let an empty dict through.

        if device not in self._config["device_configs"] or effect not in self._config["device_configs"][device]["effects"]:
            return NotFound

        for setting_key, setting_value in settings.items():
            if setting_key not in self._config["device_configs"][device]["effects"][effect]:
                return NotFound
            self._config["device_configs"][device]["effects"][effect][setting_key] = setting_value
        self.update_cycle_job(device, effect)

        self.save_config()
        self.refresh_device(device)
        return {
            "device": device,
            "effect": effect,
            "settings": settings
        }

    def set_effect_settings_for_all(self, effect: str, settings: dict) -> dict | NotFound | BadRequest:
        """Set effect settings for all devices."""
        if not settings:
            return BadRequest  # Don't let an empty dict through.

        for device in self._config["device_configs"]:
            for setting_key, setting_value in settings.items():
                if setting_key not in self._config["device_configs"][device]["effects"][effect]:
                    return NotFound
                self._config["device_configs"][device]["effects"][effect][setting_key] = setting_value
            self.update_cycle_job(device, effect)

        self.save_config()
        self.refresh_device(self.all_devices_id)
        return {
            "effect": effect,
            "settings": settings
        }

    def update_cycle_job(self, device: str, effect: str) -> None:
        """Change the Random Cycle Effect job interval on save."""
        if effect != "effect_random_cycle":
            return

        job = self.scheduler.get_job(device)
        if job:
            was_running = job.next_run_time
            interval = self._config["device_configs"][device]["effects"]["effect_random_cycle"]["interval"]
            self.scheduler.reschedule_job(device, trigger="interval", seconds=interval)
            if not was_running:  # Workaround flag because `reschedule_job()` unpauses jobs.
                self.scheduler.pause_job(device)
