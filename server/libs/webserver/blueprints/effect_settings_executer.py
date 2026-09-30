from libs.webserver.executer_base import ExecuterBase


class EffectSettingsExecuter(ExecuterBase):

    def _get_effects_config(self, device):
        if device == self.all_devices_id:
            return self._config["all_devices"]["effects"]
        elif self.is_group(device):
            # A group has no effect settings of its own, so display the first member's settings.
            members = self.get_group_devices(device)
            if members:
                return self._config["device_configs"][members[0]]["effects"]
            return self._config["default_device"]["effects"]
        else:
            return self._config["device_configs"][device]["effects"]

    # Return setting_value.
    def get_effect_setting(self, device, effect, setting_key):
        return self._get_effects_config(device)[effect][setting_key]

    def get_effect_settings(self, device, effect):
        settings = dict()
        effects_config = self._get_effects_config(device)
        for effect_setting_key in effects_config[effect]:
            settings[effect_setting_key] = effects_config[effect][effect_setting_key]
        return settings

    def set_effect_setting(self, device, effect, settings):

        if device == self.all_devices_id:
            for setting_key in settings:
                self._config["all_devices"]["effects"][effect][setting_key] = settings[setting_key]
        elif self.is_group(device):
            for device_key in self.get_group_devices(device):
                for setting_key in settings:
                    self._config["device_configs"][device_key]["effects"][effect][setting_key] = settings[setting_key]
        else:
            for setting_key in settings:
                self._config["device_configs"][device]["effects"][effect][setting_key] = settings[setting_key]

        self.save_config()

        self.refresh_device(device)

    def set_effect_setting_for_all(self, effect, settings):
        for device_key in self._config["device_configs"]:
            for setting_key in settings:
                self._config["device_configs"][device_key]["effects"][effect][setting_key] = settings[setting_key]

        self.save_config()

        self.refresh_device("all_devices")
