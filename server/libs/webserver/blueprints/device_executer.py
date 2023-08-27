from __future__ import annotations

from copy import deepcopy
from re import compile

from libs.webserver.executer_base import ExecuterBase
from libs.webserver.messages import DeviceLimitReached, DeviceNotFound, GroupAlreadyExists, GroupLimitReached, GroupNotFound


def find_missing(lst: list[int]) -> list[int]:
    """Find missing numbers in a sorted list of integers."""
    return [x for x in range(lst[0], lst[-1] + 1) if x not in lst]


def index_default_devices(device_configs: dict, default_name: str) -> str:
    """Index 'Default Device' names to prevent duplicates.

    This does not prevent manually naming devices with duplicate names.
    """
    index_list = []

    for d in device_configs.values():
        if default_name in d.values():
            index_list.append(1)  # If 'Default Device' exists, append the first index as it is not specified in the name.
        if default_name in d["device_name"]:
            try:
                pattern = compile(r"\((\d+)\)")
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

        new_index = missing_indices[0] if len(missing_indices) >= 1 else max(index_list) + 1

        default_name = f"Default Device ({new_index})"

    return default_name


class DeviceExecuter(ExecuterBase):

    def get_devices(self) -> list[dict[str, str | dict]]:
        """Return all devices. If no devices exist, return empty list."""
        return [
            {
                "name": self._config["device_configs"][device]["device_name"],
                "id": device,
                "assigned_to": self._config["device_configs"][device]["device_groups"]
            }
            for device in self._config["device_configs"]
        ]

    def create_new_device(self) -> dict[str, str] | DeviceLimitReached:
        """Create a new device with default values."""
        max_devices = 100
        # Check if a device already exists with "output_raspi" output.
        output_raspi_exists = any(device["output_type"] == "output_raspi" for device in self._config["device_configs"].values())

        for i in range(max_devices):
            new_device_id = f"device_{i}"

            if new_device_id in self._config["device_configs"]:
                continue

            default_name = index_default_devices(self._config["device_configs"], self._config["default_device"]["device_name"])

            new_device_config = deepcopy(self._config["default_device"])
            new_device_config["device_name"] = default_name
            if output_raspi_exists:
                new_device_config["output_type"] = "output_udp"

            self._config["device_configs"][new_device_id] = new_device_config
            self.save_config()

            self.refresh_device(self.all_devices_id)
            return {
                "device_id": new_device_id
            }

        return DeviceLimitReached

    def delete_device(self, device: str) -> dict[str, str] | DeviceNotFound:
        """Delete a device from the config."""
        if self._config["device_configs"].pop(device, DeviceNotFound) is DeviceNotFound:
            return DeviceNotFound

        self.save_config()
        self.refresh_device(self.all_devices_id)
        return {
            "deleted_device": device
        }

    def get_groups(self) -> dict[str, dict]:
        """Get all global groups."""
        return {"groups": self._config["general_settings"]["device_groups"]}

    def get_assigned_groups(self) -> list[dict[str, str | dict]]:
        """Only get the groups that are assigned to devices atleast once.

        Return a list of "all devices that are assigned to a group", and skip groups that are not assigned.
        """
        global_groups = self.get_groups()["groups"]
        return [
            {
                "name": group,
                "id": group_id,
                "assigned_to": {
                    device_id: device["device_name"]
                    for device_id, device in self._config["device_configs"].items()
                    if group_id in device["device_groups"]
                }
            }
            for group_id, group in global_groups.items()
            if any(group_id in device["device_groups"] for device in self._config["device_configs"].values())
        ]

    def create_new_group(self, new_group_name: str) -> dict[str, dict] | GroupLimitReached | GroupAlreadyExists:
        """Return all groups if successfully created."""
        max_groups = 100
        device_groups = self._config["general_settings"]["device_groups"]

        if new_group_name in device_groups.values():
            return GroupAlreadyExists

        for i in range(max_groups):
            new_group_id = f"group_{i}"

            if new_group_id in self._config["general_settings"]["device_groups"]:
                continue

            device_groups[new_group_id] = new_group_name
            self.save_config()
            self.refresh_device(self.all_devices_id)
            return self.get_groups()

        return GroupLimitReached

    def delete_group(self, group_id: str) -> dict[str, dict] | GroupNotFound:
        """Delete a global group and all references to it in devices from the config."""
        # Delete global group if exists.
        if self._config["general_settings"]["device_groups"].pop(group_id, GroupNotFound) is GroupNotFound:
            return GroupNotFound

        # Delete group from each device if exists.
        for device in self._config["device_configs"]:
            self._config["device_configs"][device]["device_groups"].pop(group_id, None)

        self.save_config()
        self.refresh_device(self.all_devices_id)
        return self.get_groups()

    def remove_invalid_device_groups(self) -> dict[str, dict[str, str]]:
        """Compare device groups with global groups and remove any that do not exist.

        Used when global groups are saved from general settings.
        This prevents deleted groups from still displaying on devices.
        """
        removed_groups = {}
        for device in self._config["device_configs"]:
            removed_groups.update({
                device_group: self._config["device_configs"][device]["device_groups"].pop(device_group)
                for device_group in list(self._config["device_configs"][device]["device_groups"])
                if device_group not in self._config["general_settings"]["device_groups"]
            })

        if removed_groups:
            self.save_config()
            self.refresh_device(self.all_devices_id)
        return {
            "removed_groups": removed_groups
        }
