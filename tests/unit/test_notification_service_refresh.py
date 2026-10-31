from queue import Queue

import pytest

from mlsc.notification_enum import NotificationEnum
from mlsc.notification_item import NotificationItem
from mlsc.notification_service import NotificationService
from mlsc.queue_wrapper import QueueWrapper

pytestmark = pytest.mark.unit


def make_service(device_manager_reply=True, audio_reply=True, timeout=0.05):
    service = NotificationService()
    queues = {name: QueueWrapper(Queue(100)) for name in
              ("device_manager_in", "device_manager_out", "audio_in", "audio_out", "webserver_in")}
    service._notification_queue_device_manager_in = queues["device_manager_in"]  # ruff: ignore[private-member-access]
    service._notification_queue_device_manager_out = queues["device_manager_out"]  # ruff: ignore[private-member-access]
    service._notification_queue_audio_in = queues["audio_in"]  # ruff: ignore[private-member-access]
    service._notification_queue_audio_out = queues["audio_out"]  # ruff: ignore[private-member-access]
    service._notification_queue_webserver_in = queues["webserver_in"]  # ruff: ignore[private-member-access]
    service._refresh_timeout = timeout  # ruff: ignore[private-member-access]
    finished = NotificationItem(NotificationEnum.config_refresh_finished, "dev")
    if device_manager_reply:
        queues["device_manager_out"].put_blocking(finished)
    if audio_reply:
        queues["audio_out"].put_blocking(finished)
    return service, queues


def drain(queue):
    items = []
    while not queue.empty():
        items.append(queue.get_blocking())
    return items


def test_a_finished_refresh_is_reported_to_the_webserver():
    service, queues = make_service()

    service.config_refresh(NotificationItem(NotificationEnum.config_refresh, "dev"))

    assert [(i.notification_enum, i.device_id) for i in drain(queues["webserver_in"])] == [
        (NotificationEnum.config_refresh_finished, "dev")]


def test_a_refresh_that_times_out_is_reported_as_failed_and_the_processes_continue():
    service, queues = make_service(audio_reply=False)

    service.config_refresh(NotificationItem(NotificationEnum.config_refresh, "dev"))

    assert [(i.notification_enum, i.device_id) for i in drain(queues["webserver_in"])] == [
        (NotificationEnum.config_refresh_failed, "dev")]
    assert NotificationEnum.process_continue in [i.notification_enum for i in drain(queues["device_manager_in"])]
