import atexit
import queue
from collections.abc import Mapping
from functools import wraps
from time import monotonic

from apscheduler.schedulers.background import BackgroundScheduler
from jsonschema import Draft202012Validator, ValidationError, validate
from loguru import logger

from mlsc.color_registry import find_usages
from mlsc.config_service import ConfigService
from mlsc.effect_item import EffectItem
from mlsc.effects_enum import EffectsEnum
from mlsc.notification_enum import NotificationEnum
from mlsc.notification_item import NotificationItem
from mlsc.webserver.messages import RefreshFailed

scheduler = BackgroundScheduler()


def handle_config_errors(func):
    """# WARNING: DEPRECATED.

    Decorator for catching any `Key` or `Value` errors in the config when calling API endpoints.
    In case of error, None is returned.
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> None:
        try:
            return func(*args, **kwargs)
        except (KeyError, ValueError):
            return None
    return wrapper


def update(orig: dict, new: dict) -> dict:
    """Update a dict recursively with new values.

    Also, overwrite `device_groups` without keeping old values.

    https://stackoverflow.com/questions/3232943.
    """
    for k, v in new.items():
        if k == "device_groups":
            orig[k] = v
        if isinstance(v, Mapping):
            orig[k] = update(orig.get(k, {}), v)
        else:
            orig[k] = v
    return orig


def merge(orig: dict, patch: dict) -> dict:
    """Merge `patch` into `orig` recursively: mappings are merged, every other value (lists too) replaces the old one."""
    for k, v in patch.items():
        if isinstance(v, Mapping) and isinstance(orig.get(k), dict):
            merge(orig[k], v)
        else:
            orig[k] = v
    return orig


def validate_schema(data: dict, schema: dict) -> bool:
    """Validate the request data against a JSON schema.

    All API schemas are defined in `mlsc/webserver/schemas/`.
    """
    try:
        validate(data, schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    except ValidationError as e:
        path_fmt = " -> ".join([str(p) for p in e.absolute_path])
        logger.error(f"Schema validation error in request:\n{path_fmt} - {e.message}")

        return False

    return True


class ExecuterBase:
    def __init__(self, config_lock, notification_queue_in, notification_queue_out, effects_queue, audio_backend) -> None:
        self._config_lock = config_lock
        self.notification_queue_in = notification_queue_in
        self.notification_queue_out = notification_queue_out
        self.effects_queue = effects_queue
        self._audio_backend = audio_backend

        # Initial config load.
        self._config_instance = ConfigService.instance(self._config_lock)

        self.export_config_path = self._config_instance.get_config_path()

        self.all_devices_id = "all_devices"

        self.scheduler = scheduler
        if not self.scheduler.running:
            self.scheduler.start()

        atexit.register(self.shutdown_scheduler)

    @property
    def _config(self) -> dict:
        """The live config. Read through the service, so that an import or reset is seen by every executer."""
        return self._config_instance.config

    @_config.setter
    def _config(self, config: dict) -> None:
        self._config_instance.config = config

    def shutdown_scheduler(self):
        if self.scheduler.running:
            self.scheduler.shutdown()

    # Helper
    def save_config(self):
        self._config_instance.save_config(self._config)

    def put_into_effect_queue(self, device, effect):
        logger.debug("Preparing new EnumItem...")
        effect_item = EffectItem(EffectsEnum[effect], device)
        logger.debug(f"EnumItem prepared: {effect_item.effect_enum} {effect_item.device_id}")

        self.effects_queue.put(effect_item)
        logger.debug("EnumItem put into queue.")

    def put_into_notification_queue(self, notificication, device):
        logger.debug("Preparing new Notification...")
        notification_item = NotificationItem(notificication, device)
        logger.debug(f"Notification Item prepared: {notification_item.notification_enum} {notification_item.device_id}")
        self.notification_queue_out.put(notification_item)
        logger.debug("Notification Item put into queue.")

    def refresh_device(self, device_id):
        self.put_into_notification_queue(NotificationEnum.config_refresh, device_id)

    def refresh_devices_using(self, kind: str, name: str, timeout: float = 60) -> None:
        """Restart the Devices that use the Colour or Gradient `name`, and wait until each has applied the saved config.

        Raise `ProblemError(RefreshFailed)` if a refresh fails or takes longer than `timeout` seconds. The config stays saved.
        """
        device_ids = list(dict.fromkeys(usage["target"] for usage in find_usages(self._config, kind, name)))
        deadline = monotonic() + timeout
        for device_id in device_ids:
            self._refresh_and_wait(device_id, deadline)

    def _refresh_and_wait(self, device_id: str, deadline: float) -> None:
        from mlsc.api.v2.errors import ProblemError  # Imported late: the api package imports the executers.

        while True:  # Forget answers to refreshes nobody waits for any more.
            try:
                self.notification_queue_in.get_nowait()
            except queue.Empty:
                break
        self.refresh_device(device_id)
        while True:
            try:
                answer = self.notification_queue_in.get(timeout=max(deadline - monotonic(), 0))
            except queue.Empty:
                raise ProblemError(RefreshFailed) from None
            if answer.device_id != device_id:
                continue
            if answer.notification_enum is NotificationEnum.config_refresh_finished:
                return
            if answer.notification_enum is NotificationEnum.config_refresh_failed:
                raise ProblemError(RefreshFailed)

    @staticmethod
    def validate_data_in(dictionary: dict, keys: tuple) -> bool:
        """WARNING: DEPRECATED."""
        if not isinstance(dictionary, dict):
            logger.error("Error in validate_data_in: dictionary is not a dict.")
            return False

        if keys is None:
            logger.error("Error in validate_data_in: keys tuple is None.")
            return False

        for currentkey in keys:
            if currentkey not in dictionary:
                logger.error(f"Error in validate_data_in: Could not find the key: {currentkey}")
                logger.error("Dict:")
                logger.error(str(dictionary))
                return False

            if dictionary[currentkey] is None:
                logger.error(f"Error in validate_data_in: dictionary entry is None. Key: {currentkey}")
                logger.error("Dict:")
                logger.error(str(dictionary))
                return False

        return True
