from libs.webserver.executer_base import ExecuterBase

import copy


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
            new_device_id = "device_" + str(i)
            if new_device_id not in self._config["device_configs"]:
                self._config["device_configs"][new_device_id] = copy.deepcopy(self._config["default_device"])
                self.save_config()

                self.refresh_device("all_devices")
                break

            i += 1
        return i

    def delete_device(self, device):
        del self._config["device_configs"][device]
        self.save_config()
        self.refresh_device("all_devices")
