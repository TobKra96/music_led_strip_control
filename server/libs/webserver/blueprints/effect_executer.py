from libs.webserver.executer_base import ExecuterBase

from random import choice


class EffectExecuter(ExecuterBase):

    # Return active effect.
    def get_active_effect(self, device):
        if device == self.all_devices_id:
            return self._config[self.all_devices_id]["effects"]["last_effect"]
        else:
            return self._config["device_configs"][device]["effects"]["last_effect"]

    def get_active_effects(self):
        devices = []
        for device_key in self._config["device_configs"]:
            current_device = dict()
            current_device["device"] = device_key
            current_device["effect"] = self._config["device_configs"][device_key]["effects"]["last_effect"]
            devices.append(current_device)
        return devices

    def get_enabled_effects(self):
        """
        Return list of effects enabled for Random Cycle.
        If less than two effects in list, return all effects.
        """
        effect_dict = self._config[self.all_devices_id]["effects"]["effect_random_cycle"]
        enabled_effects = [k for k, v in effect_dict.items() if v is True]
        if len(enabled_effects) < 2:
            return [k for k, _ in effect_dict.items() if k != "interval"]
        return enabled_effects

    def get_random_effect(self, effect_list, device):
        active_effect = self.get_active_effect(device)
        if len(effect_list) < 2:
            return effect_list[0]
        while True:
            effect = choice(effect_list)
            if effect != active_effect:
                break
        return effect

    def set_active_effect(self, device, effect, for_all=False):
        if effect == "effect_random_cycle":
            effect_list = self.get_enabled_effects()
            effect = self.get_random_effect(effect_list, device)

        if device == self.all_devices_id:
            self.set_active_effect_for_all(effect)
            return {"effect": effect}
        else:
            self._config["device_configs"][device]["effects"]["last_effect"] = effect
            self.save_config()

        self.put_into_effect_queue(device, effect, put_all=for_all)
        return {"device": device, "effect": effect}

    def set_active_effect_for_all(self, effect):
        if effect == "effect_random_cycle":
            effect_list = self.get_enabled_effects()
            effect = self.get_random_effect(effect_list, device)

        self._config[self.all_devices_id]["effects"]["last_effect"] = effect
        self.save_config()
        self.refresh_device(self.all_devices_id)
        for device_key in self._config["device_configs"]:
            self.set_active_effect(device_key, effect, for_all=True)
        return {"effect": effect}
