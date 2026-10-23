"""Pushes the microphone level to the SSE clients for the live meter."""
from collections.abc import Callable

from loguru import logger

from mlsc.mic_level import MicLevel
from mlsc.webserver import sse

MIC_LEVEL_POLL_SECONDS = 0.1
LEVEL_DIGITS = 3


class MicLevelPublisher:
    """Publishes `mic.level` when the level changed, but only while somebody listens."""

    def __init__(self, publish: Callable[[str, dict], None], has_subscribers: Callable[[], bool], read_level: Callable[[], float]) -> None:
        self._publish = publish
        self._has_subscribers = has_subscribers
        self._read_level = read_level
        self._last_level: float | None = None

    def poll(self) -> None:
        if not self._has_subscribers():
            # A client that connects later must get the current level, even if it did not change meanwhile.
            self._last_level = None
            return
        try:
            level = round(self._read_level(), LEVEL_DIGITS)
        except Exception:
            logger.exception("Could not read the microphone level.")
            return
        if level != self._last_level:
            self._last_level = level
            self._publish("mic.level", {"level": level})


def create_mic_level_publisher(mic_level: MicLevel) -> MicLevelPublisher:
    """Wire the publisher to the SSE broker and the shared `MicLevel`."""
    return MicLevelPublisher(sse.broker.publish, sse.broker.has_subscribers, mic_level.read)
