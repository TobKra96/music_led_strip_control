from libs.config_service import ConfigService # pylint: disable=E0611, E0401
from libs.notification_enum import NotificationEnum # pylint: disable=E0611, E0401
from libs.fps_limiter import FPSLimiter # pylint: disable=E0611, E0401
from libs.outputs.output_raspi import OutputRaspi # pylint: disable=E0611, E0401
#from libs.outputs.output_mqtt import OutputMptt # pylint: disable=E0611, E0401
from libs.outputs.output_udp import OutputUDP # pylint: disable=E0611, E0401
from libs.outputs.output_dummy import OutputDummy # pylint: disable=E0611, E0401
from libs.output_enum import OutputsEnum # pylint: disable=E0611, E0401

import numpy as np
from numpy import asarray
from ctypes import c_uint8
import time
from time import sleep
import cProfile
import pprint
import array

class OutputService:

    def start(self, device):
        self._device = device

        print("Starting Output service.. Device: " + self._device.device_config["DEVICE_NAME"])

        # Initial config load.
        self._config = self._device.config

        self._output_queue = self._device.output_queue
        self._device_notification_queue_in = self._device.device_notification_queue_in
        self._device_notification_queue_out = self._device.device_notification_queue_out
        
        self.ten_seconds_counter = time.time()
        self.sec_ten_seconds_counter = time.time()
        self.start_time = time.time()
              
        #Init FPS Limiter
        self._fps_limiter = FPSLimiter(self._device.device_config["FPS"])

        self._skip_output = False
        self._cancel_token = False

        self._available_outputs = {
            OutputsEnum.output_dummy: OutputDummy,
            OutputsEnum.output_raspi:OutputRaspi,
            OutputsEnum.output_udp:OutputUDP
            }

        current_output_enum = OutputsEnum[self._device.device_config["OUTPUT_TYPE"]]
        print("Found output: " + str(current_output_enum))
        self._current_output = self._available_outputs[current_output_enum](self._device)

        print("Output component started. Device: " + self._device.device_config["DEVICE_NAME"])
        
        while not self._cancel_token:
            self.output_routine()
           

    def output_routine(self):
        # Limit the fps to decrease laggs caused by 100 percent cpu
        self._fps_limiter.fps_limiter()

        # Check the nofitication queue
        if not self._device_notification_queue_in.empty():
            self._current_notification_in = self._device_notification_queue_in.get()

        if hasattr(self, "_current_notification_in"):
            if self._current_notification_in is NotificationEnum.config_refresh:
                self.refresh()
            elif self._current_notification_in is NotificationEnum.process_continue:
                self._skip_output = False
            elif self._current_notification_in is NotificationEnum.process_pause:
                self._skip_output = True
            elif self._current_notification_in is NotificationEnum.process_stop:
                self.stop() 

        # Reset the current in notification, to do it only one time.
        self._current_notification_in = None

        # Skip the output sequence, for example to "pause" the process.
        if self._skip_output:
            if not self._output_queue.empty():
                skip_output_queue = self._output_queue.get()
                del skip_output_queue
            return

        # Check if the queue is empty and stop if its empty.
        if not self._output_queue.empty():
            current_output_array = self._output_queue.get()
            self._current_output.show(current_output_array)

        self.end_time = time.time()
                    
        if time.time() - self.ten_seconds_counter > 10:
            self.ten_seconds_counter = time.time()
            self.time_dif = self.end_time - self.start_time
            self.fps = 1 / self.time_dif
            print("Output Service | FPS: " + str(self.fps) + " | Device: " + self._device.device_config["DEVICE_NAME"])

        self.start_time = time.time()

    def stop(self):
        self._cancel_token = True
        self._current_output.clear()

    def refresh(self):
        print("Refresh Output...")

        # Refresh the config
        self._config = self._device.config

        # Notifiy the master component, that I'm finished.
        self._device_notification_queue_out.put(NotificationEnum.config_refresh_finished)

        print("Output refreshed.")