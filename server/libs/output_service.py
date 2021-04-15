import logging
import numpy as np
from time import time

from libs.notification_enum import NotificationEnum  # pylint: disable=E0611, E0401
from libs.outputs.output_raspi import OutputRaspi  # pylint: disable=E0611, E0401
from libs.outputs.output_dummy import OutputDummy  # pylint: disable=E0611, E0401
from libs.outputs.output_udp import OutputUDP  # pylint: disable=E0611, E0401
from libs.output_enum import OutputsEnum  # pylint: disable=E0611, E0401
from libs.fps_limiter import FPSLimiter  # pylint: disable=E0611, E0401


class OutputService():
    def start(self, device):
        self.logger = logging.getLogger(__name__)

        self._device = device
        self._led_strip = self._device.device_config["output"]["output_raspi"]["LED_Strip"]

        self.logger.info(f'Starting Output service... Device: {self._device.device_config["DEVICE_NAME"]}')

        # Initial config load.
        self._config = self._device.config

        self._output_queue = self._device.output_queue
        self._device_notification_queue_in = self._device.device_notification_queue_in
        self._device_notification_queue_out = self._device.device_notification_queue_out

        self.ten_seconds_counter = time()
        self.sec_ten_seconds_counter = time()
        self.start_time = time()

        # Init FPS Limiter.
        self._fps_limiter = FPSLimiter(self._device.device_config["FPS"])

        self._skip_output = False
        self._cancel_token = False

        self._available_outputs = {
            OutputsEnum.output_dummy: OutputDummy,
            OutputsEnum.output_raspi: OutputRaspi,
            OutputsEnum.output_udp: OutputUDP
        }

        current_output_enum = OutputsEnum[self._device.device_config["OUTPUT_TYPE"]]
        self.logger.debug(f"Found output: {current_output_enum}")
        self._current_output = self._available_outputs[current_output_enum](self._device)

        self.logger.debug(f'Output component started. Device: {self._device.device_config["DEVICE_NAME"]}')

        while not self._cancel_token:
            try:
                self.output_routine()
            except KeyboardInterrupt:
                break

    def output_routine(self):
        # Limit the fps to decrease lags caused by 100 percent CPU.
        self._fps_limiter.fps_limiter()

        # Check the notification queue.
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
            # Add another Array of LEDS for White Channel
            if "SK6812" in self._led_strip and len(current_output_array) == 3:
                current_output_array = np.vstack((current_output_array, np.zeros(self._device.device_config["LED_Count"])))

            self._current_output.show(current_output_array)

        self.end_time = time()

        if time() - self.ten_seconds_counter > 10:
            self.ten_seconds_counter = time()
            self.time_dif = self.end_time - self.start_time
            self.fps = 1 / self.time_dif
            self.logger.info(f'FPS: {self.fps:.2f} | Device: {self._device.device_config["DEVICE_NAME"]}')

        self.start_time = time()

    def stop(self):
        self._cancel_token = True
        self._current_output.clear()

    def refresh(self):
        self.logger.debug("Refreshing output...")

        # Refresh the config,
        self._config = self._device.config

        # Notify the master component, that I'm finished.
        self._device_notification_queue_out.put(NotificationEnum.config_refresh_finished)

        self.logger.debug("Output refreshed.")
