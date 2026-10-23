from mlsc.webserver.blueprints.authentication_executer import AuthenticationExecuter
from mlsc.webserver.blueprints.device_executer import DeviceExecuter
from mlsc.webserver.blueprints.device_settings_executer import DeviceSettingsExecuter
from mlsc.webserver.blueprints.effect_executer import EffectExecuter
from mlsc.webserver.blueprints.effect_settings_executer import EffectSettingsExecuter
from mlsc.webserver.blueprints.general_executer import GeneralExecuter
from mlsc.webserver.blueprints.general_settings_executer import GeneralSettingsExecuter
from mlsc.webserver.blueprints.microphone_settings_executer import MicrophoneSettingsExecuter
from mlsc.webserver.blueprints.system_info_executer import SystemInfoExecuter


class Executer:
    def __init__(self, config_lock, notification_queue_in, notification_queue_out, effects_queue, py_audio) -> None:
        self.authentication_executer = AuthenticationExecuter(
            config_lock, notification_queue_in, notification_queue_out, effects_queue, py_audio)
        self.device_executer = DeviceExecuter(
            config_lock, notification_queue_in, notification_queue_out, effects_queue, py_audio)
        self.device_settings_executer = DeviceSettingsExecuter(
            config_lock, notification_queue_in, notification_queue_out, effects_queue, py_audio)
        self.effect_executer = EffectExecuter(
            config_lock, notification_queue_in, notification_queue_out, effects_queue, py_audio)
        self.effect_settings_executer = EffectSettingsExecuter(
            config_lock, notification_queue_in, notification_queue_out, effects_queue, py_audio)
        self.general_executer = GeneralExecuter(
            config_lock, notification_queue_in, notification_queue_out, effects_queue, py_audio)
        self.general_settings_executer = GeneralSettingsExecuter(
            config_lock, notification_queue_in, notification_queue_out, effects_queue, py_audio)
        self.system_info_executer = SystemInfoExecuter(
            config_lock, notification_queue_in, notification_queue_out, effects_queue, py_audio)
        self.microphone_settings_executer = MicrophoneSettingsExecuter(
            config_lock, notification_queue_in, notification_queue_out, effects_queue, py_audio)

        Executer.instance = self
