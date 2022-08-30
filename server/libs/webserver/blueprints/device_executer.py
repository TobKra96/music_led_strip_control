from libs.webserver.executer_base import ExecuterBase, handle_config_errors

import copy
import re


def find_missing(lst):
    """Find missing numbers in a sorted list of integers."""
    return [x for x in range(lst[0], lst[-1] + 1) if x not in lst]


def index_default_devices(device_configs, default_name):
    """
    Index 'Default Device' names to prevent duplicates.
    This does not prevent manually naming devices with duplicate names.
    """
    index_list = []

    for d in device_configs.values():
        if default_name in d.values():
            index_list.append(1)  # If 'Default Device' exists, append the first index as it is not specified in the name.
        if default_name in d["device_name"]:
            try:
                pattern = re.compile(r"\((\d+)\)")
                index = pattern.findall(d["device_name"])[0]  # Get all indices from "Default Device (X)" names.
                index_list.append(int(index))
            except IndexError:
                pass

    if not index_list or 1 not in index_list:
        new_index = 1
    else:
        # Check if any device indices are missing and select the first one if exists.
        # Else, increment the max index.
        missing_indices = find_missing(sorted(index_list))
        if len(missing_indices) >= 1:
            new_index = missing_indices[0]
        else:
            new_index = max(index_list) + 1

        default_name = f"Default Device ({new_index})"

    return default_name


class DeviceExecuter(ExecuterBase):

    @handle_config_errors
    def get_devices(self):
        devices = []
        for device_key in self._config["device_configs"]:
            current_device = dict()
            current_device["name"] = self._config["device_configs"][device_key]["device_name"]
            current_device["id"] = device_key
            current_device["assigned_to"] = self._config["device_configs"][device_key]["device_groups"]

            devices.append(current_device)
        return devices

    @handle_config_errors
    def create_new_device(self):
        # If a device already exists with "output_raspi" output, set new device to "output_udp".
        output_raspi_exists = False
        for device in self._config["device_configs"].values():
            if device["output_type"] == "output_raspi":
                output_raspi_exists = True
                break

        i = 0
        while i < 100:
            new_device_id = f"device_{i}"
            if new_device_id not in self._config["device_configs"]:
                default_name = index_default_devices(self._config["device_configs"], self._config["default_device"]["device_name"])

                new_device_config = copy.deepcopy(self._config["default_device"])
                new_device_config["device_name"] = default_name
                if output_raspi_exists:
                    new_device_config["output_type"] = "output_udp"

                self._config["device_configs"][new_device_id] = new_device_config
                self.save_config()

                self.refresh_device(self.all_devices_id)
                return new_device_id

            i += 1
        return None

    @handle_config_errors
    def delete_device(self, device):
        del self._config["device_configs"][device]
        self.save_config()
        self.refresh_device(self.all_devices_id)
        return self._config["device_configs"]

    @handle_config_errors
    def get_groups(self):
        """
        Get all global groups.
        """
        global_groups = dict()
        global_groups["groups"] = self._config["general_settings"]["device_groups"]
        return global_groups

    @handle_config_errors
    def get_assigned_groups(self):
        """
        Get all groups assigned to devices.
        """
        assigned_groups = []

        global_groups = self.get_groups()["groups"]
        for group_id, group_name in global_groups.items():
            devices = {}  # Clear device list on every group iteration.
            for device_id, device in self._config["device_configs"].items():
                if group_id in device["device_groups"]:
                    devices[device_id] = device["device_name"]
            if devices:
                assigned_groups.append({
                    "name": group_name,
                    "id": group_id,
                    "assigned_to": devices
                })

        return assigned_groups

    @handle_config_errors
    def create_new_group(self, new_group_name):
        """
        Return all groups if successfully created.
        Otherwise, return None.
        """
        device_groups = self._config["general_settings"]["device_groups"]

        if new_group_name and new_group_name not in device_groups.values():
            i = 0
            while i < 100:
                new_group_id = f"group_{i}"
                if new_group_id not in self._config["general_settings"]["device_groups"]:
                    device_groups[new_group_id] = new_group_name
                    break
                i += 1

            self.save_config()
            self.refresh_device(self.all_devices_id)
            return self.get_groups()
        return None

    @handle_config_errors
    def delete_group(self, group_id):
        # Delete group from each device.
        for device_key in self._config["device_configs"]:
            if group_id in self._config["device_configs"][device_key]["device_groups"]:
                del self._config["device_configs"][device_key]["device_groups"][group_id]
        # Delete global group.
        del self._config["general_settings"]["device_groups"][group_id]

        self.save_config()
        self.refresh_device(self.all_devices_id)
        return self.get_groups()

    @handle_config_errors
    def remove_invalid_device_groups(self):
        """
        Compare device groups with global groups and remove any that do not exist.
        Used when global groups are saved from general settings.
        This prevents deleted groups from still displaying on devices.
        """
        removed_groups = {}
        groups_to_remove = {}
        for device_key in self._config["device_configs"]:
            for device_group in list(self._config["device_configs"][device_key]["device_groups"]):
                if device_group not in self._config["general_settings"]["device_groups"]:
                    groups_to_remove[device_group] = self._config["device_configs"][device_key]["device_groups"][device_group]
                    del self._config["device_configs"][device_key]["device_groups"][device_group]

        removed_groups["removed_groups"] = groups_to_remove

        self.save_config()
        self.refresh_device(self.all_devices_id)
        return removed_groups
