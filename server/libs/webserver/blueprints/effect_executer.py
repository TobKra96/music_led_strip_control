from libs.webserver.executer_base import ExecuterBase, handle_config_errors

from random import choice


class EffectExecuter(ExecuterBase):

    # Return active effect.
    @handle_config_errors
    def get_active_effect(self, device):
        selected_device = device
        if device == self.all_devices_id:
            selected_device = next(iter(self._config["device_configs"]))
        return self._config["device_configs"][selected_device]["effects"]["last_effect"]

    @handle_config_errors
    def get_active_effects(self):
        devices = []
        for device_key in self._config["device_configs"]:
            current_device = dict()
            current_device["device"] = device_key
            current_device["effect"] = self._config["device_configs"][device_key]["effects"]["last_effect"]
            devices.append(current_device)
        return devices

    def get_enabled_effects(self, device):
        """
        Return list of effects enabled for Random Cycle.
        If less than two effects in list, return all effects.
        """
        effect_dict = self._config["device_configs"][device]["effects"]["effect_random_cycle"]
        enabled_effects = [k for k, v in effect_dict.items() if v is True]
        if len(enabled_effects) < 2:
            return [k for k, _ in effect_dict.items() if k != "interval"]
        return enabled_effects

    def get_random_effect(self, effect_list, device):
        """
        Return a random effect from effect list.
        Device is required to prevent repeating effects twice.
        """
        active_effect = self.get_active_effect(device)
        if len(effect_list) < 2:
            return effect_list[0]
        while True:
            effect = choice(effect_list)
            if effect != active_effect:
                break
        return effect

    def parse_special_effects(self, effect, effect_dict, device):
        """Return random effect based on selected special effect."""
        if effect not in ({*effect_dict["non_music"], *effect_dict["music"], *effect_dict["special"]}):
            return None

        if effect == "effect_random_cycle":
            effect_list = self.get_enabled_effects(device)
        elif effect == "effect_random_non_music":
            effect_list = [k for k in effect_dict["non_music"].keys()]
        elif effect == "effect_random_music":
            effect_list = [k for k in effect_dict["music"].keys()]
        else:
            return effect

        effect = self.get_random_effect(effect_list, device)
        return effect

    @handle_config_errors
    def set_active_effect(self, device, effect, effect_dict, for_all=False):
        if device == self.all_devices_id:
            self.set_active_effect_for_all(effect, effect_dict)
            return {"effect": effect}  # BUG: Special effects are not parsed.

        effect = self.parse_special_effects(effect, effect_dict, device)
        if effect is None:
            return None

        self._config["device_configs"][device]["effects"]["last_effect"] = effect
        self.save_config()
        self.put_into_effect_queue(device, effect, put_all=for_all)
        return {"device": device, "effect": effect}

    def set_active_effect_for_multiple(self, devices, effect_dict):
        parsed = dict()
        result_list = []
        for item in devices:
            result = self.set_active_effect(
                item["device"], item["effect"], effect_dict)
            if result is None:
                return None
            result_list.append(result)

        parsed["devices"] = result_list
        return parsed

    @handle_config_errors
    def set_active_effect_for_all(self, effect, effect_dict):
        for device in self._config["device_configs"]:
            effect = self.parse_special_effects(effect, effect_dict, device)
            if effect is None:
                return None
            self._config["device_configs"][device]["effects"]["last_effect"] = effect

        self.save_config()
        self.refresh_device(self.all_devices_id)
        for device_key in self._config["device_configs"]:
            self.set_active_effect(
                device_key, effect, effect_dict, for_all=True)
        return {"effect": effect}
