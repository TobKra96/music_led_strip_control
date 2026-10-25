"""The Browser Microphone: a capture that is pushed samples instead of reading a device.

The webserver process receives the chunks and queues them; the audio process builds this capture around that queue.
Chunks pass a jitter buffer (about 100 ms, at most about 250 ms) and are resampled to the rate the effects run at.
"""

from __future__ import annotations

import queue
import threading
import time
from collections import deque
from collections.abc import Callable

import numpy as np

from mlsc.audio_capture import AudioCapture
from mlsc.audio_device import AudioDevice

BROWSER_DEVICE_NAME = "Browser Microphone"
BROWSER_HOST_API = "Browser"
# The rate the effects run at when the config does not pick one: the browser's own rate is not known before it streams.
DEFAULT_SAMPLE_RATE = 44100
TARGET_SECONDS = 0.1
MAX_SECONDS = 0.25
# A missing chunk is bridged by this much faded-out audio at most, so a lost chunk does not add a long silence.
BRIDGE_SECONDS = 0.02
# The length of the crossfade that hides the seam where audio past the maximum was cut out.
FADE_SECONDS = 0.005
# A stream that sent nothing for this long has stopped, and the capture reports it so the banner can say so.
STALL_SECONDS = 2.0
# Underruns this recent and this many make the connection count as unstable.
UNSTABLE_WINDOW_SECONDS = 10.0
UNSTABLE_UNDERRUNS = 3

FULL_SCALE = np.iinfo(np.int16).max


class LinearResampler:
    """Streaming linear resampler: carries the phase across chunks, so chunk edges do not click."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._last: float | None = None
        self._position = 0.0
        self._source_rate: int | None = None

    def process(self, samples: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
        """Return `samples` at `target_rate` as int16. Start over when the source rate changes."""
        if source_rate == target_rate:
            self.reset()
            return samples.astype(np.int16, copy=False)
        if source_rate != self._source_rate:
            self.reset()
            self._source_rate = source_rate
        if samples.size == 0:
            return np.zeros(0, dtype=np.int16)
        values = samples.astype(np.float64)
        if self._last is not None:
            values = np.concatenate(([self._last], values))
        step = source_rate / target_rate
        positions = np.arange(self._position, len(values) - 1 + 1e-9, step)
        out = np.interp(positions, np.arange(len(values)), values)
        self._position = positions[-1] + step - (len(values) - 1) if positions.size else self._position
        self._last = values[-1]
        return np.clip(np.rint(out), -FULL_SCALE, FULL_SCALE).astype(np.int16)


class JitterBuffer:
    """Smooths chunks that arrive unevenly into the steady buffers the effects expect.

    Waits until `target_seconds` of audio is queued before it starts. Past `max_seconds` it cuts the buffer back to the
    middle between target and maximum, with a crossfade over the seam. When it runs short it plays silence without
    touching what is queued and carries on as soon as one full buffer is there again; a missing chunk is bridged with a
    short fade-out. Each of those counts as an underrun.
    """

    def __init__(self, sample_rate: int, clock: Callable[[], float] = time.monotonic,
                 target_seconds: float = TARGET_SECONDS, max_seconds: float = MAX_SECONDS, frames: int = 0) -> None:
        self.sample_rate = sample_rate
        self._clock = clock
        # Large effect buffers need more than the usual 100 ms to be served from the buffer at all.
        self._target = max(int(target_seconds * sample_rate), frames)
        self._max = max(int(max_seconds * sample_rate), 2 * frames)
        self._resampler = LinearResampler()
        self._underruns: deque[float] = deque()
        self.underruns = 0
        # Why the stream stutters, beside `underruns`: audio cut at the maximum, and the longest wait between two chunks.
        self.trims = 0
        self.longest_gap = 0.0
        self.last_chunk_at: float | None = None
        self.reset()

    def reset(self) -> None:
        """Forget the stream, for a new one that numbers its chunks from the start."""
        self._buffer = np.zeros(0, dtype=np.int16)
        self._primed = False
        self._starved = False
        self._next_sequence: int | None = None
        self._resampler.reset()
        self.last_chunk_at = None

    def push(self, sequence: int, source_rate: int, samples: np.ndarray) -> None:
        """Queue one chunk. A late or repeated one is dropped, a gap is filled with silence."""
        if self._next_sequence is not None:
            if sequence < self._next_sequence:
                return
            missing = sequence - self._next_sequence
            if missing:
                self._count_underrun()
                gap = min(missing * len(samples) * self.sample_rate // source_rate, int(BRIDGE_SECONDS * self.sample_rate))
                self._append(self._bridge(gap))
        self._next_sequence = sequence + 1
        now = self._clock()
        # A pause longer than a stall is the stream stopping, not a slow connection.
        if self.last_chunk_at is not None and now - self.last_chunk_at < STALL_SECONDS:
            self.longest_gap = max(self.longest_gap, now - self.last_chunk_at)
        self.last_chunk_at = now
        self._append(self._resampler.process(samples, source_rate, self.sample_rate))

    def pull(self, frames: int) -> np.ndarray:
        """Return `frames` samples: queued audio once the buffer has filled, silence while it fills or after it ran dry."""
        if not self._primed and len(self._buffer) >= self._target:
            self._primed = True
        if not self._primed:
            return np.zeros(frames, dtype=np.int16)
        if len(self._buffer) < frames + (self._target // 2 if self._starved else 0):
            # Wait for half the target on top of one buffer instead of all of it: the queued audio stays and plays after.
            if self.streaming:
                if not self._starved:
                    self._count_underrun()
                self._starved = True
            else:
                # The stream stopped: what is queued is stale, so start over with the full target when it resumes.
                self._primed = self._starved = False
            return np.zeros(frames, dtype=np.int16)
        self._starved = False
        out, self._buffer = self._buffer[:frames], self._buffer[frames:]
        return out

    @property
    def buffered_seconds(self) -> float:
        return len(self._buffer) / self.sample_rate

    @property
    def streaming(self) -> bool:
        """Whether a chunk arrived lately."""
        return self.last_chunk_at is not None and self._clock() - self.last_chunk_at < STALL_SECONDS

    def recent_underruns(self) -> int:
        now = self._clock()
        while self._underruns and now - self._underruns[0] > UNSTABLE_WINDOW_SECONDS:
            self._underruns.popleft()
        return len(self._underruns)

    def _count_underrun(self) -> None:
        self.underruns += 1
        self._underruns.append(self._clock())

    def _bridge(self, length: int) -> np.ndarray:
        """`length` samples to cover a lost chunk: the last queued sample fading out, silence if there is none."""
        if not len(self._buffer):
            return np.zeros(length, dtype=np.int16)
        return np.rint(self._buffer[-1] * np.linspace(1.0, 0.0, length)).astype(np.int16)

    def _append(self, samples: np.ndarray) -> None:
        self._buffer = np.concatenate((self._buffer, samples))
        if len(self._buffer) > self._max:
            self.trims += 1
            self._buffer = self._cut(self._buffer, len(self._buffer) - (self._target + self._max) // 2)

    def _cut(self, buffer: np.ndarray, drop: int) -> np.ndarray:
        """Skip `drop` samples at the front, crossfading the audio after them in so the seam does not click."""
        fade = min(int(FADE_SECONDS * self.sample_rate), len(buffer) - drop)
        weight = np.linspace(0.0, 1.0, fade)
        seam = buffer[:fade] * (1.0 - weight) + buffer[drop:drop + fade] * weight
        return np.concatenate((np.rint(seam).astype(np.int16), buffer[drop + fade:]))


class BrowserCapture(AudioCapture):
    """Capture fed by chunks from `source`, a queue of `("chunk", sequence, sample_rate, pcm)` and `("reset",)` messages.

    While open it delivers one buffer per `frames_per_buffer` in real time, silence when no audio is queued, so a stopped
    stream means silence. `streaming` and `unstable` tell the supervisor what to put in the status.
    """

    def __init__(self, source: queue.Queue | None = None, clock: Callable[[], float] = time.monotonic) -> None:
        super().__init__()
        self._source = source
        self._clock = clock
        self._jitter: JitterBuffer | None = None
        self._frames = 0
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        # Real time the ticks fell behind and did not make up for, so that much less audio was played than arrived.
        self.lost_seconds = 0.0

    def list_devices(self) -> list[AudioDevice]:
        return [self.device(DEFAULT_SAMPLE_RATE)]

    def default_device(self) -> AudioDevice:
        return self.device(DEFAULT_SAMPLE_RATE)

    @staticmethod
    def device(sample_rate: int) -> AudioDevice:
        return AudioDevice("browser", BROWSER_DEVICE_NAME, sample_rate, BROWSER_HOST_API)

    @property
    def streaming(self) -> bool:
        return self._jitter is not None and self._jitter.streaming

    @property
    def underruns(self) -> int:
        return self._jitter.underruns if self._jitter is not None else 0

    @property
    def trims(self) -> int:
        return self._jitter.trims if self._jitter is not None else 0

    @property
    def longest_gap(self) -> float:
        return self._jitter.longest_gap if self._jitter is not None else 0.0

    @property
    def unstable(self) -> bool:
        return self._jitter is not None and self._jitter.recent_underruns() >= UNSTABLE_UNDERRUNS

    def ingest(self, message: tuple) -> None:
        """Take one message from the webserver."""
        if self._jitter is None:
            return
        if message[0] == "reset":
            self._jitter.reset()
        elif message[0] == "chunk":
            _, sequence, sample_rate, pcm = message
            self._jitter.push(sequence, sample_rate, np.frombuffer(pcm, dtype=np.int16))

    def tick(self) -> None:
        """Deliver the next buffer."""
        jitter = self._jitter
        if jitter is not None:
            self._deliver(jitter.pull(self._frames).tobytes())

    def _start(self, device: AudioDevice, sample_rate: int, frames_per_buffer: int) -> None:
        self._jitter = JitterBuffer(sample_rate, self._clock, frames=frames_per_buffer)
        self.lost_seconds = 0.0
        self._discard_queued()
        self._frames = frames_per_buffer
        if self._source is not None:
            self._stop = threading.Event()
            self._thread = threading.Thread(target=self._run, args=(self._stop, frames_per_buffer / sample_rate), daemon=True)
            self._thread.start()

    def _discard_queued(self) -> None:
        """Drop what an earlier stream left in the queue while another source was selected."""
        while self._source is not None:
            try:
                self._source.get_nowait()
            except queue.Empty:
                return

    def _run(self, stop: threading.Event, period: float) -> None:
        next_tick = self._clock() + period
        while not stop.is_set():
            remaining = next_tick - self._clock()
            if remaining > 0:
                try:
                    self.ingest(self._source.get(timeout=remaining))
                except queue.Empty:
                    pass
                continue
            self.tick()
            # A late tick does not try to catch up with a burst of buffers.
            now = self._clock()
            self.lost_seconds += max(0.0, now - (next_tick + period))
            next_tick = max(next_tick + period, now)

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=1)
        self._thread = None
        self._jitter = None
        self._on_data = None
