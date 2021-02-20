from libs.device import Device  # pylint: disable=E0611, E0401
from libs.config_service import ConfigService  # pylint: disable=E0611, E0401
from libs.color_service_global import ColorServiceGlobal  # pylint: disable=E0611, E0401
from libs.effect_item import EffectItem  # pylint: disable=E0611, E0401
from libs.notification_item import NotificationItem  # pylint: disable=E0611, E0401
from libs.notification_enum import NotificationEnum  # pylint: disable=E0611, E0401
from libs.fps_limiter import FPSLimiter  # pylint: disable=E0611, E0401
import copy

import time
from time import sleep


class DeviceManager():
    def start(self, config_lock, notification_queue_in, notification_queue_out, effect_queue, audio_queue):
        self._config_lock = config_lock
        self._config = ConfigService.instance(self._config_lock).config

        self._notification_queue_in = notification_queue_in
        self._notification_queue_out = notification_queue_out
        self._effect_queue = effect_queue
        print(f"Effect queue id DeviceManager: {id(self._effect_queue)}")
        self._audio_queue = audio_queue

        # Init FPS Limiter.
        self._fps_limiter = FPSLimiter(120)

        self._skip_routine = False
        self._devices = {}
        self.init_devices()
        self.start_devices()

        self.start_time = time.time()
        self.ten_seconds_counter = time.time()

        while True:
            self.routine()

    def routine(self):
        # Check the effect queue.
        if not self._effect_queue.empty():
            current_effect_item = self._effect_queue.get()
            print(f"Device Manager received new effect: {current_effect_item.effect_enum} {current_effect_item.device_id}")
            current_device = self._devices[current_effect_item.device_id]
            current_device.effect_queue.put(current_effect_item)

        if not self._notification_queue_in.empty():
            current_notification_item = self._notification_queue_in.get()
            print(f"Device Manager received new notification: {current_notification_item.notification_enum} - {current_notification_item.device_id}")

            if current_notification_item.notification_enum is NotificationEnum.config_refresh:

                devices_count_before_reload = len(self._config["device_configs"].keys())
                print(f"Device count before: {devices_count_before_reload}")
                self.reload_config()
                devices_count_after_reload = len(self._config["device_configs"].keys())
                print(f"Device count after: {devices_count_after_reload}")

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

        # Limit the fps to decrease lags caused by 100 percent CPU.
        self._fps_limiter.fps_limiter()

        if self._skip_routine:
            return

        audio_data = self.get_audio_data()
        self.refresh_audio_queues(audio_data)

        self.end_time = time.time()

        if time.time() - self.ten_seconds_counter > 10:
            self.ten_seconds_counter = time.time()
            self.time_dif = self.end_time - self.start_time
            self.fps = 1 / self.time_dif
            print(f"Device Manager | FPS: {self.fps:.2f}")

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
                except Exception as e:
                    pass

            audio_copy = copy.deepcopy(audio_data)
            try:
                value.audio_queue.put(audio_copy, block=True, timeout=0.33)
            except Exception as e:
                pass

    def init_devices(self):
        print("Entering init_devices()")
        self._color_service_global = ColorServiceGlobal(self._config)

        for key in self._config["device_configs"].keys():
            device_id = key
            print(f"Init device with device id: {device_id}")
            self._devices[device_id] = Device(self._config, self._config["device_configs"][device_id], self._color_service_global)
        print("Leaving init_devices()")

    def reinit_devices(self):
        print("Entering reinit_devices()")
        for key, value in self._devices.items():
            self.stop_device(key)
        self._devices = {}
        self.init_devices()
        self.start_devices()
        print("Leaving reinit_devices()")

    def start_devices(self):
        for key, value in self._devices.items():
            print(f"Starting device: {key}")
            value.start_device()

    def reload_config(self):
        print("Entering reload_config()")
        ConfigService.instance(self._config_lock).load_config()
        self._config = ConfigService.instance(self._config_lock).config
        print("Leaving reload_config()")

    def restart_device(self, device_id):
        print(f"Restarting {device_id}")
        self._devices[device_id].refresh_config(self._config, self._config["device_configs"][device_id])
        print(f"Restarted {device_id}")

    def stop_device(self, device_id):
        print(f"Stopping {device_id}")
        self._devices[device_id].stop_device()
        print(f"Stopped {device_id}")
