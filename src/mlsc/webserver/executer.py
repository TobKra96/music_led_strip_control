import time

from mlsc.config_service import ConfigService
from mlsc.host import Host
from mlsc.webserver.blueprints.authentication_executer import AuthenticationExecuter
from mlsc.webserver.blueprints.device_executer import DeviceExecuter
from mlsc.webserver.blueprints.device_settings_executer import DeviceSettingsExecuter
from mlsc.webserver.blueprints.effect_executer import EffectExecuter
from mlsc.webserver.blueprints.effect_settings_executer import EffectSettingsExecuter
from mlsc.webserver.blueprints.general_executer import GeneralExecuter
from mlsc.webserver.blueprints.general_settings_executer import GeneralSettingsExecuter
from mlsc.webserver.blueprints.microphone_settings_executer import MicrophoneSettingsExecuter
from mlsc.webserver.blueprints.system_info_executer import SystemInfoExecuter
from mlsc.wifi.credentials import HotspotCredentials
from mlsc.wifi.factory import create_wifi_manager
from mlsc.wifi.supervisor import ConfigWifiSettings, WifiSupervisor


class Executer:
    def __init__(self, config_lock, notification_queue_in, notification_queue_out, effects_queue, audio_backend) -> None:
        self.authentication_executer = AuthenticationExecuter(
            config_lock, notification_queue_in, notification_queue_out, effects_queue, audio_backend)
        self.device_executer = DeviceExecuter(
            config_lock, notification_queue_in, notification_queue_out, effects_queue, audio_backend)
        self.device_settings_executer = DeviceSettingsExecuter(
            config_lock, notification_queue_in, notification_queue_out, effects_queue, audio_backend)
        self.effect_executer = EffectExecuter(
            config_lock, notification_queue_in, notification_queue_out, effects_queue, audio_backend)
        self.effect_settings_executer = EffectSettingsExecuter(
            config_lock, notification_queue_in, notification_queue_out, effects_queue, audio_backend)
        self.general_executer = GeneralExecuter(
            config_lock, notification_queue_in, notification_queue_out, effects_queue, audio_backend)
        self.general_settings_executer = GeneralSettingsExecuter(
            config_lock, notification_queue_in, notification_queue_out, effects_queue, audio_backend)
        self.system_info_executer = SystemInfoExecuter(
            config_lock, notification_queue_in, notification_queue_out, effects_queue, audio_backend)
        self.microphone_settings_executer = MicrophoneSettingsExecuter(
            config_lock, notification_queue_in, notification_queue_out, effects_queue, audio_backend)
        host = Host()
        self.wifi_manager = create_wifi_manager(host=host)
        self.wifi_supervisor = WifiSupervisor(
            self.wifi_manager, ConfigWifiSettings(ConfigService.instance(config_lock)), time.monotonic, host.ethernet_up,
            HotspotCredentials(host.boot_dir(), host.mac_address))

        Executer.instance = self
