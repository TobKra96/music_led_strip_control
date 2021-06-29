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

            devices.append(current_device)

        return devices

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
