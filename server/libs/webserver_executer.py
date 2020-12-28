from libs.config_service import ConfigService # pylint: disable=E0611, E0401
from libs.effect_item import EffectItem # pylint: disable=E0611, E0401
from libs.effects_enum import EffectsEnum # pylint: disable=E0611, E0401

class WebserverExecuter:
    def __init__(self, config_lock, notification_queue_in, notification_queue_out, effects_queue, effects_queue_lock):
        self._config_lock = config_lock
        self.notification_queue_in = notification_queue_in
        self.notification_queue_out = notification_queue_out
        self.effects_queue = effects_queue
        self.effects_queue_lock = effects_queue_lock

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

    #def SetEffectSettingForAll(effect, setting_key, setting_value):

    # return setting_value
    #def GetEffectSetting(device, effect, setting_key):

    #def SetEffectSetting(device, effect, setting_key, setting_value):
    
    #return setting_value
    #def GetDeviceSetting(device, setting_key):

    #def SetDeviceSetting(device, setting_key, setting_value):

    #def GetGeneralSetting(setting_key):

    #def SetGeneralSetting(setting_key, setting_value):

    #def CreateNewDevice():

    #def DeleteDevice(device):

    #def ResetSettings():

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
        self.effects_queue_lock.acquire()
        self.effects_queue.put(effect_item)
        self.effects_queue_lock.release()
        print("EnumItem put into queue.")
        print("Effect queue id Webserver " + str(id(self.effects_queue)))

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
                return False
            
            if dictionary[currentkey] is None:
                print("Error in ValidateDataIn: dictionary entry is none. Key: " + currentkey)
                return False

        return True


    