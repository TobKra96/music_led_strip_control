import json
from types import SimpleNamespace

import pytest

from mlsc.webserver.sse import EventBroker
from mlsc.webserver.status_publisher import StatusPublisher, create_status_publisher, run_status_publisher, start_status_publisher

pytestmark = pytest.mark.unit

ONLINE = {"devices": [{"id": "device_0", "name": "Desk", "connected": True}]}
OFFLINE = {"devices": [{"id": "device_0", "name": "Desk", "connected": False}]}
STATS = {"performance": {"cpu": 1}, "temperature": {"celsius": 40}}


class Sources:
    """Stands in for the system information the publisher reads, and counts how often it was asked."""

    def __init__(self) -> None:
        self.devices = ONLINE
        self.reads = 0

    def read_devices(self):
        self.reads += 1
        return self.devices

    def read_stats(self):
        self.reads += 1
        return STATS


@pytest.fixture
def sources():
    return Sources()


@pytest.fixture
def published():
    return []


@pytest.fixture
def broker():
    return EventBroker()


@pytest.fixture
def publisher(sources, published, broker):
    return StatusPublisher(lambda event, data: published.append((event, data)), broker.has_subscribers, sources.read_devices, sources.read_stats)


def test_nothing_is_read_or_published_while_nobody_listens(publisher, sources, published):
    publisher.poll()

    assert published == []
    assert sources.reads == 0


def test_a_listener_gets_the_device_status_and_the_system_stats(publisher, published, broker):
    broker.subscribe()

    publisher.poll()

    assert ("device.status", ONLINE) in published
    assert ("system.stats", STATS) in published


def test_device_status_is_only_sent_again_when_it_changed(publisher, sources, published, broker):
    broker.subscribe()
    publisher.poll()
    publisher.poll()
    sources.devices = OFFLINE
    publisher.poll()

    statuses = [data for event, data in published if event == "device.status"]
    assert statuses == [ONLINE, OFFLINE]
    assert len([event for event, _ in published if event == "system.stats"]) == 3


def test_a_listener_that_arrives_later_still_gets_the_current_status(publisher, published, broker):
    first = broker.subscribe()
    publisher.poll()
    broker.unsubscribe(first)
    publisher.poll()
    broker.subscribe()
    publisher.poll()

    assert [data for event, data in published if event == "device.status"] == [ONLINE, ONLINE]


def test_a_failing_source_does_not_stop_the_other_events(sources, published, broker):
    publisher = StatusPublisher(lambda event, data: published.append((event, data)), broker.has_subscribers, lambda: 1 / 0, sources.read_stats)
    broker.subscribe()

    publisher.poll()

    assert [event for event, _ in published] == ["system.stats"]


def test_the_loop_polls_every_interval_until_stopped(publisher, published, broker):
    broker.subscribe()
    waits = []

    def wait(interval):
        waits.append(interval)
        return len(waits) > 2

    run_status_publisher(publisher, wait, interval=10)

    assert waits == [10, 10, 10]
    assert len([event for event, _ in published if event == "system.stats"]) == 3


def test_the_publisher_thread_stops_when_asked(publisher):
    runner = start_status_publisher(publisher, interval=0.01)

    runner.stop()

    assert not runner.thread.is_alive()


def test_the_stats_event_carries_the_performance_and_the_temperature(broker, monkeypatch):
    monkeypatch.setattr("mlsc.webserver.status_publisher.sse.broker", broker)
    system_info = SimpleNamespace(
        get_system_info_device_status=lambda: ONLINE,
        get_system_info_performance=lambda: {"system": {"cpu_info": {"percent": 3.0}}},
        get_system_info_temperature=lambda: {"system": {"raspi": {"celsius": 40}}},
    )
    subscriber = broker.subscribe()

    create_status_publisher(system_info).poll()

    messages = [subscriber.get_nowait() for _ in range(subscriber.qsize())]
    stats = next(m for m in messages if m.startswith("event: system.stats"))
    assert json.loads(stats.split("data: ")[1]) == {"system": {"cpu_info": {"percent": 3.0}, "raspi": {"celsius": 40}}}
