from libs.webserver.executer_base import ExecuterBase

class DeviceSettingsExecuter(ExecuterBase):

    # Return setting_value
    def GetDeviceSetting(self, device, setting_key):
        return self._config["device_configs"][device][setting_key]

    def GetDeviceSettings(self, device, setting_key):
        device_settings_dict = dict()
        for device_setting_key in self._config["device_configs"][device]:
            device_settings_dict[device_setting_key] = self._config["device_configs"][device][device_setting_key]        
        return device_settings_dict

    def SetDeviceSetting(self, device, settings):
        for setting_key in settings:
            self._config["device_configs"][device][setting_key] = settings[setting_key]
        self.SaveConfig()

        self.RefreshDevice(device)

    # Return setting_value
    def GetOutputTypeDeviceSetting(self, device, output_type_key, setting_key):
        return self._config["device_configs"][device]["output"][output_type_key][setting_key]

    def SetOutputTypeDeviceSetting(self, device, output_type_key, settings):
        for setting_key in settings:
            self._config["device_configs"][device]["output"][output_type_key][setting_key] = settings[setting_key]
        self.SaveConfig()

        self.RefreshDevice(device)