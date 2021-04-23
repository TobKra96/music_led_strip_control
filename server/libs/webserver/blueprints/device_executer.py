from libs.webserver.executer_base import ExecuterBase
import copy


class DeviceExecuter(ExecuterBase):

    # Return all devices in a dictionary format: "device_id" = device_name.
    def get_devices(self):

        devices = dict()

        for device_key in self._config["device_configs"]:
            devices[device_key] = self._config["device_configs"][device_key]["device_name"]

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
