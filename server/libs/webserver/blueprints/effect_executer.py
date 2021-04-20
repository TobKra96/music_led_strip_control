from libs.webserver.executer_base import ExecuterBase


class EffectExecuter(ExecuterBase):

    # Return active effect.
    def get_active_effect(self, device):
        if device == self.all_devices_id:
            return self._config["all_devices"]["effects"]["last_effect"]
        else:
            return self._config["device_configs"][device]["effects"]["last_effect"]

    def set_active_effect(self, device, effect):
        if device == self.all_devices_id:
            self.set_active_effect_for_all(effect)
            return
        else:
            self._config["device_configs"][device]["effects"]["last_effect"] = effect
            self.save_config()

        self.put_into_effect_queue(device, effect)

    def set_active_effect_for_all(self, effect):
        self._config["all_devices"]["effects"]["last_effect"] = effect
        self.save_config()
        self.refresh_device("all_devices")
        for device_key in self._config["device_configs"]:
            self.set_active_effect(device_key, effect)
