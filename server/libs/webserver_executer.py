from libs.config_service import ConfigService # pylint: disable=E0611, E0401
from libs.effect_item import EffectItem # pylint: disable=E0611, E0401
from libs.effects_enum import EffectsEnum # pylint: disable=E0611, E0401
from libs.notification_enum import NotificationEnum # pylint: disable=E0611, E0401
from libs.notification_item import NotificationItem # pylint: disable=E0611, E0401

import copy
import json

class WebserverExecuter:
    def __init__(self, config_lock, notification_queue_in, notification_queue_out, effects_queue):
        self._config_lock = config_lock
        self.notification_queue_in = notification_queue_in
        self.notification_queue_out = notification_queue_out
        self.effects_queue = effects_queue

        # Initial config load.
        self._config_instance = ConfigService.instance(self._config_lock)
        self._config = self._config_instance.config
    # Ajax Commands

    #return all devices in dictornary format: "device_id" = device_name
    def GetDevices(self):
        
        devices = dict()
        
        for device_key in self._config["device_configs"]:
            devices[device_key] = self._config["device_configs"][device_key]["DEVICE_NAME"]

        return devices
      

    #return active effect
    def GetActiveEffect(self, device):
        return self._config["device_configs"][device]["effects"]["last_effect"]

    def SetActiveEffect(self, device, effect):
        self._config["device_configs"][device]["effects"]["last_effect"] = effect
        self.SaveConfig()

        self.PutIntoEffectQueue(device, effect)

    def SetActiveEffectForAll(self, effect):
        for device_key in self._config["device_configs"]:
            self.SetActiveEffect(device_key, effect)


    # return setting_value
    def GetEffectSetting(self, device, effect, setting_key):
        return self._config["device_configs"][device]["effects"][effect][setting_key]

    def SetEffectSetting(self, device, effect, settings):
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

    #return setting_value
    def GetDeviceSetting(self,device, setting_key):
        return self._config["device_configs"][device][setting_key]

    def SetDeviceSetting(self, device, settings):
        for setting_key in settings:
            self._config["device_configs"][device][setting_key] = settings[setting_key]
        self.SaveConfig()

        self.RefreshDevice(device)

    #return setting_value
    def GetOutputTypeDeviceSetting(self,device, output_type_key, setting_key):
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
            if not new_device_id in self._config["device_configs"]:
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
            print("Could not import Config. Config is none.")
            return False
        
        print("Type of Imported config: " + str(type(imported_config)))
        if type(imported_config) is dict:
            self._config = imported_config
            self.SaveConfig()
            self.RefreshDevice("all_devices")
            return True
        else:
            print("Unknown Type")
            return False

    # Helper

    def SaveConfig(self):
        self._config_instance.save_config(self._config)

    def ResetConfig(self):
        self._config_instance.reset_config()
        self._config = self._config_instance.config

    def PutIntoEffectQueue(self, device, effect):
        print("Prepare new EnumItem")
        effect_item = EffectItem(EffectsEnum[effect], device)
        print("EnumItem prepared: " + str(effect_item.effect_enum) + " " + effect_item.device_id)
        self.effects_queue.put(effect_item)
        print("EnumItem put into queue.")
        print("Effect queue id Webserver " + str(id(self.effects_queue)))

    def PutIntoNotificationQueue(self, notificication, device):
        print("Prepare new Notification")
        notification_item = NotificationItem(notificication, device)
        print("Notification Item prepared: " + str(notification_item.notification_enum) + " " + notification_item.device_id)
        self.notification_queue_out.put(notification_item)
        print("Notification Item put into queue.")

    def RefreshDevice(self, deviceId):
        self.PutIntoNotificationQueue(NotificationEnum.config_refresh, deviceId)

    def ValidateDataIn(self, dictionary, keys):
        
        if not (type(dictionary) is dict):
            print("Error in ValidateDataIn: dictionary is not a dict")
            return False
        
        if keys is None:
            print("Error in ValidateDataIn: keys tuple is none")
            return False

        for currentkey in keys:
            if not (currentkey in dictionary): 
                print("Error in ValidateDataIn: Could not find the key: " + currentkey)
                print("Dict:")
                print(dictionary)
                return False
            
            if dictionary[currentkey] is None:
                print("Error in ValidateDataIn: dictionary entry is none. Key: " + currentkey)
                print("Dict:")
                print(dictionary)
                return False

        return True

    def GetWebserverPort(self):
        webserver_port = 80
        if 'WEBSERVER_PORT' in self._config["general_settings"]:
            webserver_port = self._config["general_settings"]["WEBSERVER_PORT"]

        return webserver_port
    