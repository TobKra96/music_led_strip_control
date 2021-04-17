
from libs.webserver.blueprints.authentication_executer import AuthenticationExecuter
from libs.webserver.blueprints.device_executer import DeviceExecuter
from libs.webserver.blueprints.device_settings_executer import DeviceSettingsExecuter
from libs.webserver.blueprints.effect_executer import EffectExecuter
from libs.webserver.blueprints.effect_settings_executer import EffectSettingsExecuter
from libs.webserver.blueprints.general_executer import GeneralExecuter
from libs.webserver.blueprints.general_settings_executer import GeneralSettingsExecuter
from libs.webserver.executer_base import ExecuterBase

import logging

class Executer():
    def __init__(self, config_lock, notification_queue_in, notification_queue_out, effects_queue, py_audio):
        self.logger = logging.getLogger(__name__)

        self.authentication_executer = AuthenticationExecuter(config_lock, notification_queue_in, notification_queue_out, effects_queue, py_audio)
        self.device_executer = DeviceExecuter(config_lock, notification_queue_in, notification_queue_out, effects_queue, py_audio)
        self.device_settings_executer = DeviceSettingsExecuter(config_lock, notification_queue_in, notification_queue_out, effects_queue, py_audio)
        self.effect_executer = EffectExecuter(config_lock, notification_queue_in, notification_queue_out, effects_queue, py_audio)
        self.effect_settings_executer = EffectSettingsExecuter(config_lock, notification_queue_in, notification_queue_out, effects_queue, py_audio)
        self.general_executer = GeneralExecuter(config_lock, notification_queue_in, notification_queue_out, effects_queue, py_audio)
        self.general_settings_executer = GeneralSettingsExecuter(config_lock, notification_queue_in, notification_queue_out, effects_queue, py_audio)

        Executer.instance = self

