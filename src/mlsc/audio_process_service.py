import sys
from multiprocessing import Queue
from time import time

import numpy as np
from loguru import logger

from mlsc.audio_capture import create_capture
from mlsc.audio_info import AudioInfo
from mlsc.config_service import ConfigService
from mlsc.dsp import DSP
from mlsc.fps_limiter import FPSLimiter
from mlsc.notification_enum import NotificationEnum
from mlsc.notification_item import NotificationItem
from mlsc.queue_wrapper import QueueWrapper


class AudioProcessService:
    def start(self, config_lock, notification_queue_in, notification_queue_out, audio_queue, audio_backend, mic_level=None):
        self._config_lock = config_lock
        self._notification_queue_in = QueueWrapper(notification_queue_in)
        self._notification_queue_out = QueueWrapper(notification_queue_out)
        self._audio_queue = QueueWrapper(audio_queue)
        self._mic_level = mic_level

        self.audio_buffer_queue = QueueWrapper(Queue(2))
        # Built here, inside the audio process: capture objects hold native handles and cannot be pickled.
        self._capture = create_capture(audio_backend)

        self.init_audio_service(show_output=True)

        try:
            while True:
                self.audio_service_routine()
                self._fps_limiter.fps_limiter()
        except KeyboardInterrupt:
            sys.exit()

    def init_audio_service(self, show_output=False):
        try:
            # Initial config load.
            ConfigService.instance(self._config_lock).load_config()
            self._config = ConfigService.instance(self._config_lock).config

            # Init FPS Limiter.
            self._fps_limiter = FPSLimiter(120)
            self._skip_routine = False
            self._devices = AudioInfo.get_audio_devices(self._capture)

            self.log_output(show_output, "INFO", "Found the following audio sources:")

            audio_config = self._config["audio"]

            # Select the audio device by name. No name means the system default.
            device_name = audio_config["device_name"]
            self.selected_device = AudioInfo.select_audio_device(self._capture, self._devices, device_name)
            if device_name is not None and self.selected_device.name != device_name:
                self.log_output(show_output, "ERROR", f"Could not find the mic named {device_name!r}. Using the system default.")

            logger.debug(f"Selected Device: {self.selected_device}")

            self._device_rate = audio_config["sample_rate"]
            self._frames_per_buffer = audio_config["frames_per_buffer"]
            self.n_fft_bins = self._config["general_settings"]["n_fft_bins"]
            self.log_output(show_output, "INFO", f"Selected Device: {self.selected_device.to_string()}")

            # Init Timer
            self.start_time_1 = time()
            self.ten_seconds_counter_1 = time()
            self.start_time_2 = time()
            self.ten_seconds_counter_2 = time()

            self._dsp = DSP(self._config)

            # Reinit buffer queue
            self.audio_buffer_queue = QueueWrapper(Queue(2))

            # Called from the capture thread with each buffer of int16 samples.
            def callback(in_data):
                if self._skip_routine:
                    return

                if self._mic_level is not None:
                    self._mic_level.update(in_data)

                self.audio_buffer_queue.put_none_blocking(in_data)

                self.end_time_1 = time()

                if time() - self.ten_seconds_counter_1 > 10:
                    self.ten_seconds_counter_1 = time()
                    time_dif = self.end_time_1 - self.start_time_1
                    fps = 1 / time_dif
                    logger.info(f"Callback | FPS: {fps:.2f}")

                self.start_time_1 = time()

            self.log_output(show_output, "DEBUG", "Starting Open Audio Stream...")
            self._capture.open(self.selected_device, self._device_rate, self._frames_per_buffer, on_data=callback)
        except Exception:
            logger.exception("Unexpected error in init_audio_service.")

    @staticmethod
    def log_output(show_output, log_level, message) -> None:
        if show_output:
            if log_level == "INFO":
                logger.info(message)
            elif log_level == "DEBUG":
                logger.debug(message)
            elif log_level == "ERROR":
                logger.error(message)
            else:
                logger.debug(message)
        else:
            logger.debug(message)

    def audio_service_routine(self):
        try:
            if not self._notification_queue_in.empty():
                current_notification_item = self._notification_queue_in.get_blocking()

                if current_notification_item.notification_enum is NotificationEnum.config_refresh:
                    self._capture.close()
                    self.init_audio_service()
                    self._notification_queue_out.put_blocking(NotificationItem(
                        NotificationEnum.config_refresh_finished, current_notification_item.device_id))
                elif current_notification_item.notification_enum is NotificationEnum.process_continue:
                    self._skip_routine = False
                elif current_notification_item.notification_enum is NotificationEnum.process_pause:
                    self._skip_routine = True

            if self._skip_routine:
                return

            in_data = None
            in_data = self.audio_buffer_queue.get_blocking_with_timeout()
            if in_data is None:
                logger.debug("Audio in timeout. Queue is Empty")
                return

            # Convert the raw string audio stream to an array.
            y = np.frombuffer(in_data, dtype=np.int16)
            # Use the type float32.
            y = y.astype(np.float32)

            # Process the audio stream.
            audio_datas = self._dsp.update(y)

            # Check if value is higher than min value.
            if audio_datas["vol"] < self._config["audio"]["min_volume_threshold"]:
                # Fill the array with zeros, to fade out the effect.
                audio_datas["mel"] = np.zeros(self.n_fft_bins)

            self._audio_queue.put_none_blocking(audio_datas)

            self.end_time_2 = time()

            if time() - self.ten_seconds_counter_2 > 10:
                self.ten_seconds_counter_2 = time()
                time_dif = self.end_time_2 - self.start_time_2
                fps = 1 / time_dif
                logger.info(f"Routine | FPS: {fps:.2f}")

            self.start_time_2 = time()

        except OSError:
            logger.exception("OSError while reading the Microphone Stream.")
        except Exception:
            logger.exception("Unexpected error in routine.")
