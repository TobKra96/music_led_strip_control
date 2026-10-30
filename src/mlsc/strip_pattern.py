"""Test Pattern: a temporary, server-driven pattern that takes over a Device's strip, then hands it back to the effect."""
import enum
import multiprocessing
import time
from collections.abc import Callable

import numpy as np

# One step of the colour order check: red, green, blue, white.
COLOUR_STEP_SECONDS = 1.0
CHASE_PIXELS_PER_SECOND = 20
DEFAULT_SECONDS = 10
MAX_SECONDS = 60

_STEP_COLOURS = ((255, 0, 0), (0, 255, 0), (0, 0, 255), None)
_RED, _GREEN, _BLUE = _STEP_COLOURS[:3]


class Pattern(enum.IntEnum):
    colour_order = 1
    markers = 2
    chase = 3
    power = 4


def _fill(frame: np.ndarray, index, colour: tuple[int, int, int] | None) -> None:
    """Set pixels to `colour`, or to white when it is None: the white channel where the strip has one, else all colours."""
    if colour is not None:
        frame[:3, index] = np.array(colour, dtype=frame.dtype).reshape(3, *([1] * np.ndim(frame[0, index])))
    elif frame.shape[0] == 4:
        frame[3, index] = 255
    else:
        frame[:3, index] = 255


def render(pattern: Pattern, led_count: int, led_mid: int, elapsed: float, white_channel: bool = False) -> np.ndarray:
    """One frame of `pattern` as rows of red, green, blue (and white) values, `elapsed` seconds after it started."""
    frame = np.zeros((4 if white_channel else 3, led_count))
    if led_count < 1:
        return frame
    if pattern is Pattern.colour_order:
        _fill(frame, slice(None), _STEP_COLOURS[int(elapsed // COLOUR_STEP_SECONDS) % len(_STEP_COLOURS)])
    elif pattern is Pattern.markers:
        _fill(frame, 0, _RED)
        _fill(frame, min(max(led_mid, 0), led_count - 1), _GREEN)
        _fill(frame, led_count - 1, _BLUE)
    elif pattern is Pattern.chase:
        _fill(frame, int(elapsed * CHASE_PIXELS_PER_SECOND) % led_count, None)
    else:
        # The most the strip can draw: every colour and the white channel at full.
        frame[:, :] = 255
    return frame


class PatternChannel:
    """Which Test Pattern runs on which Device. The webserver process starts and stops, the output processes read.

    Created before the processes start and passed to both sides as an argument. The clock must be the same in both.
    """

    SLOTS = 32
    ID_BYTES = 64

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._lock = multiprocessing.Lock()
        self._ids = multiprocessing.RawArray("c", self.SLOTS * self.ID_BYTES)
        self._patterns = multiprocessing.RawArray("i", self.SLOTS)
        self._started = multiprocessing.RawArray("d", self.SLOTS)
        self._deadlines = multiprocessing.RawArray("d", self.SLOTS)

    def _slot(self, device_id: str, create: bool) -> int | None:
        key = device_id.encode()[: self.ID_BYTES]
        free = None
        for slot in range(self.SLOTS):
            stored = self._ids[slot * self.ID_BYTES:(slot + 1) * self.ID_BYTES].rstrip(b"\0")
            if stored == key:
                return slot
            if not stored and free is None:
                free = slot
        if not create:
            return None
        if free is None:
            msg = "Too many devices run a Test Pattern."
            raise RuntimeError(msg)
        padded = key.ljust(self.ID_BYTES, b"\0")
        self._ids[free * self.ID_BYTES:(free + 1) * self.ID_BYTES] = padded
        return free

    def start(self, device_id: str, pattern: Pattern, seconds: float) -> None:
        """Take over the strip of `device_id` for `seconds`, at most `MAX_SECONDS`. Replaces a running pattern."""
        now = self._clock()
        with self._lock:
            slot = self._slot(device_id, create=True)
            self._started[slot] = now
            self._deadlines[slot] = now + min(seconds, MAX_SECONDS)
            self._patterns[slot] = int(pattern)

    def stop(self, device_id: str) -> None:
        with self._lock:
            slot = self._slot(device_id, create=False)
            if slot is not None:
                self._patterns[slot] = 0

    def active(self, device_id: str) -> tuple[Pattern, float] | None:
        """The running pattern of `device_id` and the seconds since it started, or None once it ran out."""
        with self._lock:
            slot = self._slot(device_id, create=False)
            if slot is None or not self._patterns[slot]:
                return None
            now = self._clock()
            if now >= self._deadlines[slot]:
                self._patterns[slot] = 0
                return None
            return Pattern(self._patterns[slot]), now - self._started[slot]


class PatternPlayer:
    """The output side: gives the frame that replaces the effect while a Test Pattern runs on the Device."""

    def __init__(self, channel: PatternChannel | None, device_id: str | None, led_count: int, led_mid: int, white_channel: bool) -> None:
        self._channel = channel
        self._device_id = device_id
        self._led_count = led_count
        self._led_mid = led_mid
        self._white_channel = white_channel

    def frame(self) -> np.ndarray | None:
        """The frame to show instead of the effect, or None when no pattern runs."""
        if self._channel is None or self._device_id is None:
            return None
        running = self._channel.active(self._device_id)
        if running is None:
            return None
        pattern, elapsed = running
        return render(pattern, self._led_count, self._led_mid, elapsed, self._white_channel)


# The channel of the webserver process, set by `Webserver.start`.
channel: PatternChannel | None = None
