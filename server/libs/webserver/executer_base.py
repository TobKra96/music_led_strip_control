from libs.notification_enum import NotificationEnum  # pylint: disable=E0611, E0401
from libs.notification_item import NotificationItem  # pylint: disable=E0611, E0401
from libs.config_service import ConfigService  # pylint: disable=E0611, E0401
from libs.effects_enum import EffectsEnum  # pylint: disable=E0611, E0401
from libs.effect_item import EffectItem  # pylint: disable=E0611, E0401

import logging


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
    def save_config(self):
        self._config_instance.save_config(self._config)

    def put_into_effect_queue(self, device, effect, put_all=False):
        self.logger.debug("Preparing new EnumItem...")
        effect_item = EffectItem(EffectsEnum[effect], device)
        self.logger.debug(
            f"EnumItem prepared: {effect_item.effect_enum} {effect_item.device_id}")
        if put_all:
            # If 'all_devices' is selected, wait for queue to clear.
            # This prevents the LED strip flashing the effect from the wrong device config.
            # There is also a noticable gap between clicking the effect button and the LED strip reacting.
            # This is because the refresh_config() function in device.py is slow.
            while not self.effects_queue.empty():
                self.effects_queue.put(effect_item)
        else:
            self.effects_queue.put(effect_item)
        self.logger.debug("EnumItem put into queue.")

    def put_into_notification_queue(self, notificication, device):
        self.logger.debug("Preparing new Notification...")
        notification_item = NotificationItem(notificication, device)
        self.logger.debug(
            f"Notification Item prepared: {notification_item.notification_enum} {notification_item.device_id}")
        self.notification_queue_out.put(notification_item)
        self.logger.debug("Notification Item put into queue.")

    def refresh_device(self, deviceId):
        self.put_into_notification_queue(
            NotificationEnum.config_refresh, deviceId)

    def validate_data_in(self, dictionary, keys):
        if not (type(dictionary) is dict):
            self.logger.error(
                "Error in validate_data_in: dictionary is not a dict.")
            return False

        if keys is None:
            self.logger.error("Error in validate_data_in: keys tuple is None.")
            return False

        for currentkey in keys:
            if not (currentkey in dictionary):
                self.logger.error(
                    f"Error in validate_data_in: Could not find the key: {currentkey}")
                self.logger.error("Dict:")
                self.logger.error(str(dictionary))
                return False

            if dictionary[currentkey] is None:
                self.logger.error(
                    f"Error in validate_data_in: dictionary entry is None. Key: {currentkey}")
                self.logger.error("Dict:")
                self.logger.error(str(dictionary))
                return False

        return True
