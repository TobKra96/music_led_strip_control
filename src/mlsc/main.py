# Main File
# ----------------
#
# The program will start here.
# This file will only initialize and start the processes.

import os
import subprocess
import sys
from multiprocessing import Lock, Process, Queue
from sys import platform
from time import sleep

from loguru import logger

from mlsc import paths
from mlsc.audio_process_service import AudioProcessService
from mlsc.config_migration import ConfigMigrationError
from mlsc.config_service import ConfigService
from mlsc.device_manager import DeviceManager
from mlsc.mic_level import MicLevel
from mlsc.notification_service import NotificationService
from mlsc.webserver.webserver import Webserver

if platform == "linux":
    import fcntl


RED = "\x1b[91m"


def instance_already_running():
    """Detect if an an instance is already running, globally at the operating system level.

    Using `os.open` ensures that the file pointer won't be closed
    by Python's garbage collector after the function's scope is exited.

    The lock will be released when the program exits, or could be
    released if the file pointer were closed.
    """
    data_dir = paths.data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    lock_path = data_dir / "default.lock"

    try:
        lock_file_pointer = os.open(lock_path, os.O_WRONLY | os.O_CREAT)
    except PermissionError:
        sys.exit(RED + "Error: Run MLSC as root (sudo).")

    try:
        fcntl.lockf(lock_file_pointer, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return False
    except OSError:
        return True


def exit_if_instance_running():
    if platform != "linux" or not instance_already_running():
        return

    x = subprocess.Popen(
        ["/usr/bin/systemctl", "is-active", "mlsc"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=False,
        text=True
    )
    systemctl_status = x.communicate()[0].strip()
    if systemctl_status == "active":
        sys.exit(RED + "Error: MLSC is already running as a service.\nStop the running service with 'sudo systemctl stop mlsc'.")
    else:
        sys.exit(RED + "Error: MLSC is already running directly.\nStop the running instance with 'CTRL+C'.")


class Main:
    """Main class. It controls everything.

    It's the first starting point of the program.
    """

    def start(self):
        """Start all necessary components."""
        # We need a lock to prevent too fast saving and loading actions of the config
        self._config_lock = Lock()

        # Create the instance of the config
        self._config_instance = ConfigService.instance(self._config_lock)
        self._config = self._config_instance.config

        logger.info("Initializing MLSC...")

        # Check config compatibility
        self._config_instance.check_compatibility()

        # Only the backend name crosses the process boundary. Each process builds its own capture object.
        self._audio_backend = "auto"

        # Written by the audio process, read by the webserver process for the `mic.level` events.
        self._mic_level = MicLevel()

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
                self._audio_queue
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
                self._notification_queue_webserver_out
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
                self._effects_queue,
                self._audio_backend,
                self._mic_level
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
                self._audio_queue,
                self._audio_backend,
                self._mic_level
            ))
        self._audio_process.start()

        logger.info("Initialization finished.")

        try:
            logger.info("MLSC started...")

            self._cancel_token = False

            # Do nothing with this thread. Just wait for the exit.
            while not self._cancel_token:
                sleep(10)

        except KeyboardInterrupt:
            logger.info("Stopping MLSC...")
            self._notification_service_process.terminate()
            self._webserver_process.terminate()
            logger.info("MLSC stopped")


def run() -> int:
    exit_if_instance_running()
    try:
        Main().start()
    except ConfigMigrationError as e:
        print(f"{RED}Error: {e}", file=sys.stderr)  # ruff: ignore[print]
        return 1
    return 0
