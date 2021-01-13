from libs.device import Device # pylint: disable=E0611, E0401
from libs.config_service import ConfigService # pylint: disable=E0611, E0401
from libs.color_service_global import ColorServiceGlobal # pylint: disable=E0611, E0401
from libs.effect_item import EffectItem # pylint: disable=E0611, E0401
from libs.notification_item import NotificationItem # pylint: disable=E0611, E0401
from libs.notification_enum import NotificationEnum # pylint: disable=E0611, E0401
import copy

import time
from time import sleep

class DeviceManager:
    def start(self, config_lock, notification_queue_in, notification_queue_out, effect_queue , audio_queue):
        
        self._config_lock = config_lock
        self._config = ConfigService.instance(self._config_lock).config

        self._notification_queue_in = notification_queue_in
        self._notification_queue_out = notification_queue_out
        self._effect_queue = effect_queue
        print("Effect queue id DeviceManager " + str(id(self._effect_queue)))
        self._audio_queue = audio_queue
        self._skip_routine = False
        self._devices = {}
        self.init_devices()
        self.start_devices()

        self.start_time = time.time()
        self.ten_seconds_counter = time.time()

        while True:
            self.routine()

    def routine(self):
        # Check the effect queue
        if not self._effect_queue.empty():
            current_effect_item = self._effect_queue.get()
            print("Device Manager received new effect: " + str(current_effect_item.effect_enum) + current_effect_item.device_id)
            current_device = self._devices[current_effect_item.device_id]
            current_device.effect_queue.put(current_effect_item)

        if not self._notification_queue_in.empty():
            current_notification_item = self._notification_queue_in.get()
            print("Device Manager received new notification: " + str(current_notification_item.notification_enum) + " - " + str(current_notification_item.device_id))

            if current_notification_item.notification_enum is NotificationEnum.config_refresh:
                
                devices_count_before_reload = len(self._config["device_configs"].keys())
                print("Device count before: " + str(devices_count_before_reload))
                self.reload_config()
                devices_count_after_reload = len(self._config["device_configs"].keys())
                print("Device count after: " + str(devices_count_after_reload))

                if(devices_count_before_reload != devices_count_after_reload):
                    self.reinit_devices()

                
                if(current_notification_item.device_id == "all_devices"):
                    for key, value in self._devices.items():
                            self.restart_device(key)
                else:
                    self.restart_device(current_notification_item.device_id)
                self._notification_queue_out.put(NotificationItem(NotificationEnum.config_refresh_finished, current_notification_item.device_id))

            elif current_notification_item.notification_enum is NotificationEnum.process_continue:
                self._skip_routine = False
            elif current_notification_item.notification_enum is NotificationEnum.process_pause:
                self._skip_routine = True

        if self._skip_routine:
            return

        audio_data = self.get_audio_data()
        self.refresh_audio_queues(audio_data)

        self.end_time = time.time()
                    
        if time.time() - self.ten_seconds_counter > 10:
            self.ten_seconds_counter = time.time()
            self.time_dif = self.end_time - self.start_time
            self.fps = 1 / self.time_dif
            print("Device Manager | FPS: " + str(self.fps))

        self.start_time = time.time()

    def get_audio_data(self):
        audio_data = None
        if not self._audio_queue.empty():
            audio_data = self._audio_queue.get()
        return audio_data
        
    def refresh_audio_queues(self, audio_data):
        if audio_data is None:
            return
        for key, value in self._devices.items():
            if value.audio_queue.full():
                try:
                    pre_audio_data = value.audio_queue.get(False)
                    del pre_audio_data
                except:
                    pass
            value.audio_queue.put(copy.deepcopy(audio_data))

    def init_devices(self):
        print("Enter init_devices()")

        self._color_service_global = ColorServiceGlobal(self._config)

        for key in self._config["device_configs"].keys():
            device_id = key
            print("Init device with device id:" + device_id)
            self._devices[device_id] = Device(self._config, self._config["device_configs"][device_id], self._color_service_global)
        print("Leave init_devices()")

    def reinit_devices(self):
        print("Enter reinit_devices()")
        for key, value in self._devices.items():
            self.stop_device(key)
        self._devices = {}
        self.init_devices()
        self.start_devices()
        print("Leave reinit_devices()")

    def start_devices(self):
        for key, value in self._devices.items():
            print("Start device:" + key)
            value.start_device()
    
    def reload_config(self):
        print("Enter reload_config()")
        ConfigService.instance(self._config_lock).load_config()
        self._config = ConfigService.instance(self._config_lock).config
        print("Leave reload_config()")

    def restart_device(self, device_id):
        print("Restart " + device_id)
        self._devices[device_id].refresh_config(self._config, self._config["device_configs"][device_id])
        print("Restarted " + device_id)

    def stop_device(self, device_id):
        print("Stop " + device_id)
        self._devices[device_id].stop_device()
        print("Stopped " + device_id)
        

  
    

    