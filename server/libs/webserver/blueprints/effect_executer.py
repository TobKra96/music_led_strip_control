from libs.webserver.executer_base import ExecuterBase

class EffectExecuter(ExecuterBase):
    
    # Return active effect.
    def GetActiveEffect(self, device):
        if device == self.all_devices_id:
            return self._config["all_devices"]["effects"]["last_effect"]
        else:
            return self._config["device_configs"][device]["effects"]["last_effect"]

    def SetActiveEffect(self, device, effect):
        if device == self.all_devices_id:
            self.SetActiveEffectForAll(effect)
            return
        else:
            self._config["device_configs"][device]["effects"]["last_effect"] = effect
            self.SaveConfig()

        self.PutIntoEffectQueue(device, effect)

    def SetActiveEffectForAll(self, effect):
        self._config["all_devices"]["effects"]["last_effect"] = effect
        self.SaveConfig()
        self.RefreshDevice("all_devices")
        for device_key in self._config["device_configs"]:
            self.SetActiveEffect(device_key, effect)