import logging
import copy

from libs.notification_enum import NotificationEnum  # pylint: disable=E0611, E0401
from libs.notification_item import NotificationItem  # pylint: disable=E0611, E0401
from libs.config_service import ConfigService  # pylint: disable=E0611, E0401
from libs.effects_enum import EffectsEnum  # pylint: disable=E0611, E0401
from libs.effect_item import EffectItem  # pylint: disable=E0611, E0401


class WebserverExecuter():
    def __init__(self, config_lock, notification_queue_in, notification_queue_out, effects_queue):
        self.logger = logging.getLogger(__name__)

        self._config_lock = config_lock
        self.notification_queue_in = notification_queue_in
        self.notification_queue_out = notification_queue_out
        self.effects_queue = effects_queue

        # Initial config load.
        self._config_instance = ConfigService.instance(self._config_lock)
        self._config = self._config_instance.config

        self.all_devices_id = "all_devices"
    # Ajax Commands.

    # Return all devices in a dictionary format: "device_id" = device_name.
    def GetDevices(self):

        devices = dict()

        for device_key in self._config["device_configs"]:
            devices[device_key] = self._config["device_configs"][device_key]["DEVICE_NAME"]

        return devices

    # Return active effect.
    def GetActiveEffect(self, device):
        if device == self.all_devices_id:
            return self._config["all_devices"]["effects"]["last_effect"]
        else:
            return self._config["device_configs"][device]["effects"]["last_effect"]

    def SetActiveEffect(self, device, effect):
        if device == self.all_devices_id:
            self.SetActiveEffectForAll(effect)
            return
        else:
            self._config["device_configs"][device]["effects"]["last_effect"] = effect
            self.SaveConfig()

        self.PutIntoEffectQueue(device, effect)

    def SetActiveEffectForAll(self, effect):
        self._config["all_devices"]["effects"]["last_effect"] = effect
        self.SaveConfig()
        self.RefreshDevice("all_devices")
        for device_key in self._config["device_configs"]:
            self.SetActiveEffect(device_key, effect)

    # Return setting_value.
    def GetEffectSetting(self, device, effect, setting_key):
        if device == self.all_devices_id:
            return self._config["all_devices"]["effects"][effect][setting_key]
        else:
            return self._config["device_configs"][device]["effects"][effect][setting_key]

    def SetEffectSetting(self, device, effect, settings):

        if device == self.all_devices_id:
            for setting_key in settings:
                self._config["all_devices"]["effects"][effect][setting_key] = settings[setting_key]
        else:
            for setting_key in settings:
                self._config["device_configs"][device]["effects"][effect][setting_key] = settings[setting_key]

        self.SaveConfig()

        self.RefreshDevice(device)

    def SetEffectSettingForAll(self, effect, settings):
        for device_key in self._config["device_configs"]:
            for setting_key in settings:
                self._config["device_configs"][device_key]["effects"][effect][setting_key] = settings[setting_key]

        self.SaveConfig()

        self.RefreshDevice("all_devices")

    def GetColors(self):
        colors = dict()
        for colorID in self._config["colours"]:
            colors[colorID] = colorID
        return colors

    def GetGradients(self):
        gradients = dict()
        for gradientID in self._config["gradients"]:
            gradients[gradientID] = gradientID
        return gradients

    def GetLEDStrips(self):
        led_strips = dict()
        for led_strip_ID in self._config["led_strips"]:
            led_strips[led_strip_ID] = self._config["led_strips"][led_strip_ID]
        return led_strips

    def GetLoggingLevels(self):
        logging_levels = dict()
        for logging_level_ID in self._config["logging_levels"]:
            logging_levels[logging_level_ID] = self._config["logging_levels"][logging_level_ID]
        return logging_levels

    def GetGeneralSetting(self, setting_key):
        return self._config["general_settings"][setting_key]

    def SetGeneralSetting(self, settings):
        for setting_key in settings:
            self._config["general_settings"][setting_key] = settings[setting_key]
        self.SaveConfig()

        self.RefreshDevice("all_devices")

    def GetOutputTypes(self):
        output_types = dict()
        output_types["output_raspi"] = "Output Raspberry Pi"
        output_types["output_udp"] = "Output Network via UDP"
        return output_types

    # Return setting_value
    def GetDeviceSetting(self, device, setting_key):
        return self._config["device_configs"][device][setting_key]

    def SetDeviceSetting(self, device, settings):
        for setting_key in settings:
            self._config["device_configs"][device][setting_key] = settings[setting_key]
        self.SaveConfig()

        self.RefreshDevice(device)

    # Return setting_value
    def GetOutputTypeDeviceSetting(self, device, output_type_key, setting_key):
        return self._config["device_configs"][device]["output"][output_type_key][setting_key]

    def SetOutputTypeDeviceSetting(self, device, output_type_key, settings):
        for setting_key in settings:
            self._config["device_configs"][device]["output"][output_type_key][setting_key] = settings[setting_key]
        self.SaveConfig()

        self.RefreshDevice(device)

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

    def DeleteDevice(self, device):
        del self._config["device_configs"][device]
        self.SaveConfig()
        self.RefreshDevice("all_devices")

    def ResetSettings(self):
        self.ResetConfig()
        self.RefreshDevice("all_devices")

    def ImportConfig(self, imported_config):
        if imported_config is None:
            self.logger.error("Could not import Config. Config is None.")
            return False

        self.logger.debug(f"Type of imported config: {type(imported_config)}")
        if type(imported_config) is dict:
            self._config = imported_config
            self.SaveConfig()
            self._config_instance.check_compatibility()
            self.RefreshDevice("all_devices")
            return True
        else:
            self.logger.error("Unknown Type.")
            return False

    # Helper
    def SaveConfig(self):
        self._config_instance.save_config(self._config)

    def ResetConfig(self):
        self._config_instance.reset_config()
        self._config = self._config_instance.config

    def PutIntoEffectQueue(self, device, effect):
        self.logger.debug("Preparing new EnumItem...")
        effect_item = EffectItem(EffectsEnum[effect], device)
        self.logger.debug(f"EnumItem prepared: {effect_item.effect_enum} {effect_item.device_id}")
        self.effects_queue.put(effect_item)
        self.logger.debug("EnumItem put into queue.")

    def PutIntoNotificationQueue(self, notificication, device):
        self.logger.debug("Preparing new Notification...")
        notification_item = NotificationItem(notificication, device)
        self.logger.debug(f"Notification Item prepared: {notification_item.notification_enum} {notification_item.device_id}")
        self.notification_queue_out.put(notification_item)
        self.logger.debug("Notification Item put into queue.")

    def RefreshDevice(self, deviceId):
        self.PutIntoNotificationQueue(NotificationEnum.config_refresh, deviceId)

    def ValidateDataIn(self, dictionary, keys):
        if not (type(dictionary) is dict):
            self.logger.error("Error in ValidateDataIn: dictionary is not a dict.")
            return False

        if keys is None:
            self.logger.error("Error in ValidateDataIn: keys tuple is None.")
            return False

        for currentkey in keys:
            if not (currentkey in dictionary):
                self.logger.error(f"Error in ValidateDataIn: Could not find the key: {currentkey}")
                self.logger.error("Dict:")
                self.logger.error(str(dictionary))
                return False

            if dictionary[currentkey] is None:
                self.logger.error(f"Error in ValidateDataIn: dictionary entry is None. Key: {currentkey}")
                self.logger.error("Dict:")
                self.logger.error(str(dictionary))
                return False

        return True

    def GetWebserverPort(self):
        webserver_port = 8080
        if 'WEBSERVER_PORT' in self._config["general_settings"]:
            webserver_port = self._config["general_settings"]["WEBSERVER_PORT"]

        return webserver_port
