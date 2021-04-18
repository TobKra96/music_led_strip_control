from libs.webserver.executer_base import ExecuterBase


class EffectSettingsExecuter(ExecuterBase):

    # Return setting_value.
    def GetEffectSetting(self, device, effect, setting_key):
        if device == self.all_devices_id:
            return self._config["all_devices"]["effects"][effect][setting_key]
        else:
            return self._config["device_configs"][device]["effects"][effect][setting_key]

    def GetEffectSettings(self, device, effect):
        settings = dict()
        if device == self.all_devices_id:
            for effect_setting_key in self._config["all_devices"]["effects"][effect]:
                settings[effect_setting_key] = self._config["all_devices"]["effects"][effect][setting_key]
            return settings
        else:
            for effect_setting_key in self._config["device_configs"][device]["effects"][effect]:
                settings[effect_setting_key] = self._config["device_configs"][device]["effects"][effect][setting_key]
            return settings

    def SetEffectSetting(self, device, effect, settings):

        if device == self.all_devices_id:
            for setting_key in settings:
                self._config["all_devices"]["effects"][effect][setting_key] = settings[setting_key]
        else:
            for setting_key in settings:
                self._config["device_configs"][device]["effects"][effect][setting_key] = settings[setting_key]

        self.SaveConfig()

        self.RefreshDevice(device)

    def SetEffectSettingForAll(self, effect, settings):
        for device_key in self._config["device_configs"]:
            for setting_key in settings:
                self._config["device_configs"][device_key]["effects"][effect][setting_key] = settings[setting_key]

        self.SaveConfig()

        self.RefreshDevice("all_devices")
