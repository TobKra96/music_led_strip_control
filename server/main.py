# Main File
# ----------------
#
# The program will start here.
# This file will only initialize and start the processes.

from libs.device_manager import DeviceManager
from libs.config_service import ConfigService
from libs.effects_enum import EffectsEnum
from libs.notification_enum import NotificationEnum
from libs.notification_service import NotificationService
from libs.webserver import Webserver
from libs.audio_process_service import AudioProcessService

import numpy as np
from multiprocessing import Process, Queue, Manager, Lock
from time import sleep


class Main():
    """
    This is the main class. It controls everything.
    It's the first starting point of the program.
    """
    def start(self):
        """
        This function will start all necessary components.
        Let's go :-D
        """
        print("Initializing MLSC...")

        # We need a lock to prevent too fast saving and loading actions of the config
        self._config_lock = Lock()

        # Create the instance of the config
        self._config_instance = ConfigService.instance(self._config_lock)
        self._config = self._config_instance.config

        # Check config compatibility
        self._config_instance.check_compatibility()

        # Prepare the queue for the output
        self._output_queue = Queue(2)
        self._effects_queue = Queue(100)
        self._audio_queue = Queue(2)

        # Prepare all notification queues
        self._notification_queue_audio_in = Queue(100)
        self._notification_queue_audio_out = Queue(100)

        self._notification_queue_device_manager_in = Queue(100)
        self._notification_queue_device_manager_out = Queue(100)

        self._notification_queue_webserver_in = Queue(100)
        self._notification_queue_webserver_out = Queue(100)

        # Start the DeviceManager Service
        self._device_manager = DeviceManager()
        self._device_manager_process = Process(
            target=self._device_manager.start,
            args=(
                self._config_lock,
                self._notification_queue_device_manager_in,
                self._notification_queue_device_manager_out,
                self._effects_queue,
                self._audio_queue,
            ))
        self._device_manager_process.start()

        # Start Notification Service
        self._notification_service = NotificationService()
        self._notification_service_process = Process(
            target=self._notification_service.start,
            args=(
                self._config_lock,
                self._notification_queue_device_manager_in,
                self._notification_queue_device_manager_out,
                self._notification_queue_audio_in,
                self._notification_queue_audio_out,
                self._notification_queue_webserver_in,
                self._notification_queue_webserver_out,
            ))
        self._notification_service_process.start()

        # Start Webserver
        self._webserver = Webserver()
        self._webserver_process = Process(
            target=self._webserver.start,
            args=(
                self._config_lock,
                self._notification_queue_webserver_in,
                self._notification_queue_webserver_out,
                self._effects_queue
            ))
        self._webserver_process.start()

        # Start audio process
        self._audio = AudioProcessService()
        self._audio_process = Process(
            target=self._audio.start,
            args=(
                self._config_lock,
                self._notification_queue_audio_in,
                self._notification_queue_audio_out,
                self._audio_queue
            ))
        self._audio_process.start()

        print("Initialization finished.")

        try:
            print("MLSC started...")

            self._cancel_token = False

            # Do nothing with this thread. Just wait for the exit.
            while not self._cancel_token:
                sleep(10)

        except KeyboardInterrupt:
            print("\nStopping MLSC...")
            self._notification_service_process.terminate()
            self._webserver_process.terminate()
            print("MLSC stopped")


if __name__ == "__main__":
    main = Main()
    main.start()
