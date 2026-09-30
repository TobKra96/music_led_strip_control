from libs.webserver.executer_base import ExecuterBase


class GroupExecuter(ExecuterBase):

    # Device settings that can be applied to every device of a group at once.
    GROUP_DEVICE_SETTINGS = ("led_brightness", "fps")

    def get_groups(self):
        groups = []
        for group_key, group_config in self.get_groups_config().items():
            groups.append({
                "id": group_key,
                "name": group_config["group_name"],
                "devices": self.get_group_devices(group_key)
            })
        return groups

    def get_group(self, group):
        if not self.is_group(group):
            return None

        group_config = self.get_groups_config()[group]
        return {
            "id": group,
            "name": group_config["group_name"],
            "devices": self.get_group_devices(group)
        }

    def validate_devices(self, devices):
        return type(devices) is list and all(device in self._config["device_configs"] for device in devices)

    def create_new_group(self, group_name=None, devices=None):
        groups = self.get_groups_config()

        i = 0
        while f"{self.group_id_prefix}{i}" in groups:
            i += 1
        new_group_id = f"{self.group_id_prefix}{i}"

        default_device = self._config["default_device"]
        groups[new_group_id] = {
            "group_name": group_name or f"Group {i + 1}",
            "devices": list(dict.fromkeys(devices or [])),
            "last_effect": default_device["effects"]["last_effect"],
            "led_brightness": default_device["led_brightness"],
            "fps": default_device["fps"]
        }
        self.save_config()

        return new_group_id

    def update_group(self, group, group_name=None, devices=None):
        group_config = self.get_groups_config()[group]

        if group_name is not None:
            group_config["group_name"] = group_name
        if devices is not None:
            group_config["devices"] = list(dict.fromkeys(devices))

        self.save_config()

    def delete_group(self, group):
        del self.get_groups_config()[group]
        self.save_config()

    def get_group_settings(self, group):
        group_config = self.get_groups_config()[group]
        return {key: group_config[key] for key in self.GROUP_DEVICE_SETTINGS}

    def set_group_settings(self, group, settings):
        group_config = self.get_groups_config()[group]

        for setting_key in settings:
            group_config[setting_key] = settings[setting_key]
            for device_key in self.get_group_devices(group):
                self._config["device_configs"][device_key][setting_key] = settings[setting_key]

        self.save_config()

        self.refresh_device(group)
