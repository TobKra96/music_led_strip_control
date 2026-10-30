"""Strip Preview: carries the frames and Diagnoses of the Outputs from the output processes to the webserver process."""
import base64
import multiprocessing
import queue
import threading
import time
from collections.abc import Callable

import numpy as np
from loguru import logger

from mlsc.diagnosis import Diagnosis
from mlsc.webserver.sse import EventBroker

PREVIEW_FPS = 30
BACKLOG = 64
# One stream per browser tab; the cap keeps previews from using up the webserver threads.
MAX_STREAMS_PER_DEVICE = 2
DRAIN_TIMEOUT_SECONDS = 0.25


def encode_frame(device_id: str, frame: np.ndarray, brightness: int = 100) -> dict:
    """The `preview` event payload: the red, green and blue of every pixel as base64, with the brightness applied."""
    rgb = np.clip(np.asarray(frame)[:3] * brightness / 100, 0, 255).astype(np.uint8)
    return {"device_id": device_id, "leds": int(rgb.shape[1]), "frame": base64.b64encode(rgb.T.tobytes()).decode()}


class PreviewChannel:
    """Created before the processes start and passed to both sides as an argument."""

    def __init__(self) -> None:
        self.queue = multiprocessing.Queue(BACKLOG)
        # 1 while somebody watches a preview, so the outputs do not encode frames nobody sees.
        self.demand = multiprocessing.RawValue("i", 0)


class PreviewSink:
    """The output side: pushes at most `PREVIEW_FPS` frames per second, and only while somebody watches."""

    def __init__(self, channel: PreviewChannel | None, device_id: str | None, brightness: int = 100,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self._channel = channel
        self._device_id = device_id
        self._brightness = brightness
        self._clock = clock
        self._last = float("-inf")

    def frame(self, frame: np.ndarray) -> None:
        if self._channel is None or not self._channel.demand.value:
            return
        now = self._clock()
        if now - self._last < 1 / PREVIEW_FPS:
            return
        self._last = now
        self._put(("frame", encode_frame(self._device_id, frame, self._brightness)))

    def diagnosis(self, diagnosis: Diagnosis) -> None:
        if self._channel is not None:
            self._put(("diagnosis", diagnosis.to_event(self._device_id)))

    def _put(self, message) -> None:
        try:
            self._channel.queue.put_nowait(message)
        except queue.Full:
            pass


class PreviewHub:
    """The webserver side: hands the frames to the streams of their Device and the Diagnoses to the event stream."""

    def __init__(self, channel: PreviewChannel, publish: Callable[[str, dict], None]) -> None:
        self._channel = channel
        self._publish = publish
        self._brokers: dict[str, EventBroker] = {}
        self._lock = threading.Lock()
        self._diagnoses: dict[str, tuple[int, dict]] = {}
        self._sequence = 0

    def broker(self, device_id: str) -> EventBroker:
        with self._lock:
            if device_id not in self._brokers:
                self._brokers[device_id] = EventBroker(MAX_STREAMS_PER_DEVICE)
            return self._brokers[device_id]

    def latest(self, device_id: str) -> tuple[int, dict] | None:
        """The last Diagnosis the output process of `device_id` reported, with a number that grows with every report."""
        with self._lock:
            return self._diagnoses.get(device_id)

    def drain(self, timeout: float = DRAIN_TIMEOUT_SECONDS) -> None:
        """Handle one message, if there is one, and update the demand."""
        try:
            kind, payload = self._channel.queue.get(timeout=timeout)
        except queue.Empty:
            pass
        else:
            if kind == "frame":
                self.broker(payload["device_id"]).publish("preview", payload)
            elif kind == "diagnosis":
                with self._lock:
                    self._sequence += 1
                    self._diagnoses[payload["device_id"]] = (self._sequence, payload)
                self._publish("diagnosis", payload)
        with self._lock:
            watched = any(broker.has_subscribers() for broker in self._brokers.values())
        self._channel.demand.value = int(watched)

    def run(self, stopped: threading.Event) -> None:
        while not stopped.is_set():
            try:
                self.drain()
            except Exception:
                logger.exception("Could not handle a preview message.")


# The hub of the webserver process, set by `start_preview_hub`.
hub: PreviewHub | None = None


def start_preview_hub(preview_hub: PreviewHub) -> Callable[[], None]:
    """Run the hub in a daemon thread. Returns the function that stops it."""
    global hub  # ruff: ignore[global-statement]
    hub = preview_hub
    stopped = threading.Event()
    thread = threading.Thread(target=preview_hub.run, args=(stopped,), daemon=True)
    thread.start()

    def stop() -> None:
        stopped.set()
        thread.join()

    return stop
