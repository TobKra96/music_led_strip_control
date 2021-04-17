from libs.webserver.executer_base import ExecuterBase
import copy

class DeviceExecuter(ExecuterBase):

    # Return all devices in a dictionary format: "device_id" = device_name.
    def GetDevices(self):

        devices = dict()

        for device_key in self._config["device_configs"]:
            devices[device_key] = self._config["device_configs"][device_key]["DEVICE_NAME"]

        return devices

    def CreateNewDevice(self):
        i = 0
        while i < 100:
            new_device_id = "device_" + str(i)
            if new_device_id not in self._config["device_configs"]:
                self._config["device_configs"][new_device_id] = copy.deepcopy(self._config["default_device"])
                self.SaveConfig()

                self.RefreshDevice("all_devices")
                break

            i += 1
        return i

    def DeleteDevice(self, device):
        del self._config["device_configs"][device]
        self.SaveConfig()
        self.RefreshDevice("all_devices")