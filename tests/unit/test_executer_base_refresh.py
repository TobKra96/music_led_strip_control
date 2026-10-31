from queue import Queue

import pytest

from mlsc.api.v2.errors import ProblemError
from mlsc.notification_enum import NotificationEnum
from mlsc.notification_item import NotificationItem
from mlsc.webserver.executer_base import ExecuterBase
from mlsc.webserver.messages import RefreshFailed

pytestmark = pytest.mark.unit


class _OutQueue:
    """Plays the NotificationService: answers each refresh request with `reply`."""

    def __init__(self, inbox, reply):
        self.inbox = inbox
        self.reply = reply
        self.requested = []

    def put(self, item):
        self.requested.append((item.notification_enum, item.device_id))
        if self.reply is not None:
            self.inbox.put(NotificationItem(self.reply, item.device_id))


def make_executer(reply=NotificationEnum.config_refresh_finished):
    inbox = Queue()
    executer = ExecuterBase.__new__(ExecuterBase)
    executer.notification_queue_in = inbox
    executer.notification_queue_out = _OutQueue(inbox, reply)
    executer._config_instance = type("C", (), {"config": {
        "device_configs": {
            "0": {"effects": {"effect_bars": {"color_mode": "mine"}}},
            "1": {"effects": {"effect_bars": {"color_mode": "spectral"}}},
            "2": {"effects": {"effect_bars": {"color_mode": "mine"}}},
        }}})()
    return executer


def test_only_the_devices_using_the_entry_are_refreshed():
    executer = make_executer()

    executer.refresh_devices_using("gradient", "mine", timeout=1)

    assert executer.notification_queue_out.requested == [
        (NotificationEnum.config_refresh, "0"), (NotificationEnum.config_refresh, "2")]


def test_an_unused_entry_refreshes_nothing():
    executer = make_executer()

    executer.refresh_devices_using("gradient", "unused", timeout=1)

    assert executer.notification_queue_out.requested == []


def test_a_failed_refresh_raises_refresh_failed():
    executer = make_executer(reply=NotificationEnum.config_refresh_failed)

    with pytest.raises(ProblemError) as raised:
        executer.refresh_devices_using("gradient", "mine", timeout=1)

    assert raised.value.message is RefreshFailed


def test_a_refresh_nobody_answers_times_out_as_refresh_failed():
    executer = make_executer(reply=None)

    with pytest.raises(ProblemError) as raised:
        executer.refresh_devices_using("gradient", "mine", timeout=0.05)

    assert raised.value.message is RefreshFailed
