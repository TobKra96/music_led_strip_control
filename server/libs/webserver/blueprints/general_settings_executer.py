from libs.webserver.executer_base import ExecuterBase, handle_config_errors


class GeneralSettingsExecuter(ExecuterBase):

    @handle_config_errors
    def get_general_setting(self, setting_key):
        return self._config["general_settings"][setting_key]

    @handle_config_errors
    def get_general_settings(self):
        general_settings = dict()
        for setting_key in self._config["general_settings"]:
            general_settings[setting_key] = self._config["general_settings"][setting_key]
        return general_settings

    @handle_config_errors
    def set_general_setting(self, settings):
        for setting_key in settings:
            self._config["general_settings"][setting_key] = settings[setting_key]
        self.save_config()
        self.refresh_device("all_devices")
        return self._config["general_settings"][setting_key]

    def get_webserver_port(self):
        webserver_port = 8080
        if 'webserver_port' in self._config["general_settings"]:
            webserver_port = self._config["general_settings"]["webserver_port"]
        return webserver_port

    def reset_settings(self):
        self.reset_config()
        self.refresh_device("all_devices")

    def reset_config(self):
        self._config_instance.reset_config()
        self._config = self._config_instance.config

    def import_config(self, imported_config):
        if imported_config is None:
            self.logger.error("Could not import Config. Config is None.")
            return False

        self.logger.debug(f"Type of imported config: {type(imported_config)}")
        if type(imported_config) is dict:
            self._config = imported_config
            self.save_config()
            self._config_instance.check_compatibility()
            self.refresh_device("all_devices")
            return True
        self.logger.error("Unknown Type.")
        return False
