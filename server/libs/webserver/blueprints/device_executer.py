from libs.webserver.executer_base import ExecuterBase

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
        if default_name in list(d.values())[0]:
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

    def get_devices(self):
        devices = []

        for device_key in self._config["device_configs"]:
            current_device = dict()
            current_device["name"] = self._config["device_configs"][device_key]["device_name"]
            current_device["id"] = device_key
            current_device["groups"] = self._config["device_configs"][device_key]["device_groups"]

            devices.append(current_device)

        return devices

    def get_groups(self):
        groups = []

        for group_key in self._config["device_groups"]:
            current_group = dict()
            current_group["name"] = self._config["device_groups"][group_key]
            current_group["id"] = group_key

            groups.append(current_group)

        return groups

    def create_new_group(self, new_group_name):
        """
        Return the created group if does not exist.
        Otherwise, return all groups.
        """
        device_groups = self._config["device_groups"]

        i = 0
        while i < 100:
            new_group_id = f"group_{i}"
            if new_group_id not in device_groups and new_group_name not in device_groups.values():
                device_groups[new_group_id] = new_group_name
                self.save_config()

                self.refresh_device("all_devices")
                return [self.get_groups()[i]]

            i += 1

        return self.get_groups()

    def delete_group(self, group):
        try:
            group_name = copy.deepcopy(self._config["device_groups"][group])
            del self._config["device_groups"][group]
            for device_key in self._config["device_configs"]:
                self._config["device_configs"][device_key]["device_groups"].remove(group_name)
        except (KeyError, ValueError):
            pass
        self.save_config()
        self.refresh_device("all_devices")
        return self.get_groups()

    def create_new_device(self):
        i = 0
        while i < 100:
            new_device_id = f"device_{i}"
            if new_device_id not in self._config["device_configs"]:
                default_name = index_default_devices(self._config["device_configs"], self._config["default_device"]["device_name"])

                new_device_config = copy.deepcopy(self._config["default_device"])
                new_device_config["device_name"] = default_name

                self._config["device_configs"][new_device_id] = new_device_config
                self.save_config()

                self.refresh_device("all_devices")
                break

            i += 1
        return i

    def delete_device(self, device):
        del self._config["device_configs"][device]
        self.save_config()
        self.refresh_device("all_devices")
