from libs.notification_enum import NotificationEnum  # pylint: disable=E0611, E0401
from libs.notification_item import NotificationItem  # pylint: disable=E0611, E0401
from libs.config_service import ConfigService  # pylint: disable=E0611, E0401
from libs.effects_enum import EffectsEnum  # pylint: disable=E0611, E0401
from libs.effect_item import EffectItem  # pylint: disable=E0611, E0401

import logging
import copy


class ExecuterBase():
    def __init__(self, config_lock, notification_queue_in, notification_queue_out, effects_queue, py_audio):
        self.logger = logging.getLogger(__name__)

        self._config_lock = config_lock
        self.notification_queue_in = notification_queue_in
        self.notification_queue_out = notification_queue_out
        self.effects_queue = effects_queue
        self._py_audio = py_audio

        # Initial config load.
        self._config_instance = ConfigService.instance(self._config_lock)
        self._config = self._config_instance.config

        self.export_config_path = self._config_instance.get_config_path()

        self.all_devices_id = "all_devices"

    # Helper
    def SaveConfig(self):
        self._config_instance.save_config(self._config)

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
