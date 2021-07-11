from libs.webserver.executer_base import ExecuterBase


class EffectSettingsExecuter(ExecuterBase):

    # Return setting_value.
    def get_effect_setting(self, device, effect, setting_key):
        if device == self.all_devices_id:
            return self._config["all_devices"]["effects"][effect][setting_key]
        else:
            return self._config["device_configs"][device]["effects"][effect][setting_key]

    def get_effect_settings(self, device, effect):
        settings = dict()
        if device == self.all_devices_id:
            for effect_setting_key in self._config["all_devices"]["effects"][effect]:
                settings[effect_setting_key] = self._config["all_devices"]["effects"][effect][effect_setting_key]
            return settings
        else:
            for effect_setting_key in self._config["device_configs"][device]["effects"][effect]:
                settings[effect_setting_key] = self._config["device_configs"][device]["effects"][effect][effect_setting_key]
            return settings

    def set_effect_setting(self, device, effect, settings):

        if device == self.all_devices_id:
            for setting_key in settings:
                self._config["all_devices"]["effects"][effect][setting_key] = settings[setting_key]
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
