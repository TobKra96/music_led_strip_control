"""Pushes device status and system statistics to the SSE clients, so the UI does not have to poll for them."""
import threading
from collections.abc import Callable
from dataclasses import dataclass

from loguru import logger

from mlsc.webserver import sse

POLL_SECONDS = 10.0


class StatusPublisher:
    """Reads the system information and publishes it, but only while somebody listens.

    `device.status` is sent when it changed since the last poll that had a listener, `system.stats` on every poll.
    """

    def __init__(self, publish: Callable[[str, dict], None], has_subscribers: Callable[[], bool],
                 read_devices: Callable[[], dict], read_stats: Callable[[], dict]) -> None:
        self._publish = publish
        self._has_subscribers = has_subscribers
        self._read_devices = read_devices
        self._read_stats = read_stats
        self._last_devices: dict | None = None

    def poll(self) -> None:
        if not self._has_subscribers():
            # A client that connects later must get the current status again, even if it did not change meanwhile.
            self._last_devices = None
            return
        self._publish_devices()
        self._publish_stats()

    def _publish_devices(self) -> None:
        try:
            devices = self._read_devices()
        except Exception:
            logger.exception("Could not read the device status.")
            return
        if devices != self._last_devices:
            self._last_devices = devices
            self._publish("device.status", devices)

    def _publish_stats(self) -> None:
        try:
            stats = self._read_stats()
        except Exception:
            logger.exception("Could not read the system stats.")
            return
        self._publish("system.stats", stats)


def run_status_publisher(publisher: StatusPublisher, wait: Callable[[float], bool], interval: float = POLL_SECONDS) -> None:
    """Poll every `interval` until `wait` reports a stop. The first poll happens at once."""
    publisher.poll()
    while not wait(interval):
        publisher.poll()


@dataclass
class StatusPublisherRunner:
    thread: threading.Thread
    _stopped: threading.Event

    def stop(self) -> None:
        self._stopped.set()
        self.thread.join()


def start_status_publisher(publisher: StatusPublisher, interval: float = POLL_SECONDS) -> StatusPublisherRunner:
    """Run `run_status_publisher` in a daemon thread."""
    stopped = threading.Event()
    thread = threading.Thread(target=run_status_publisher, args=(publisher, stopped.wait, interval), daemon=True)
    thread.start()
    return StatusPublisherRunner(thread, stopped)


def create_status_publisher(system_info) -> StatusPublisher:
    """Wire the publisher to the SSE broker and a SystemInfoExecuter."""
    return StatusPublisher(
        sse.broker.publish,
        sse.broker.has_subscribers,
        system_info.get_system_info_device_status,
        lambda: read_stats(system_info),
    )


def read_stats(system_info) -> dict:
    """Return the performance and the temperature under one `system` key, the shape both endpoints already use."""
    return {"system": {**system_info.get_system_info_performance()["system"], **system_info.get_system_info_temperature()["system"]}}
