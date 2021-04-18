from libs.webserver.executer_base import ExecuterBase


class GeneralSettingsExecuter(ExecuterBase):

    def GetGeneralSetting(self, setting_key):
        return self._config["general_settings"][setting_key]

    def GetGeneralSettings(self):
        general_settings = dict()
        for setting_key in self._config["general_settings"]:
            general_settings[setting_key] = self._config["general_settings"][setting_key]

        return general_settings

    def SetGeneralSetting(self, settings):
        for setting_key in settings:
            self._config["general_settings"][setting_key] = settings[setting_key]
        self.SaveConfig()

        self.RefreshDevice("all_devices")

    def GetWebserverPort(self):
        webserver_port = 8080
        if 'WEBSERVER_PORT' in self._config["general_settings"]:
            webserver_port = self._config["general_settings"]["WEBSERVER_PORT"]

        return webserver_port

    def ResetSettings(self):
        self.ResetConfig()
        self.RefreshDevice("all_devices")

    def ResetConfig(self):
        self._config_instance.reset_config()
        self._config = self._config_instance.config

    def ImportConfig(self, imported_config):
        if imported_config is None:
            self.logger.error("Could not import Config. Config is None.")
            return False

        self.logger.debug(f"Type of imported config: {type(imported_config)}")
        if type(imported_config) is dict:
            self._config = imported_config
            self.SaveConfig()
            self._config_instance.check_compatibility()
            self.RefreshDevice("all_devices")
            return True
        else:
            self.logger.error("Unknown Type.")
            return False
