"""The webserver side of the Browser Microphone: who may stream, and checking and queueing their chunks."""
from __future__ import annotations

import queue
import secrets
import threading
import time
from collections.abc import Callable

# A stream that sent no chunk for this long gives up its claim.
IDLE_SECONDS = 5.0
MIN_SAMPLE_RATE = 8000
MAX_SAMPLE_RATE = 192000
# Chunks are about 40 ms; this leaves room for slower batching without letting one request flood the buffer.
MAX_CHUNK_SECONDS = 1.0
BYTES_PER_SAMPLE = 2


class BrowserStreamError(Exception):
    """Why a request about the Browser Microphone stream was refused. `kind` is `busy`, `unknown_stream` or `invalid_chunk`."""

    def __init__(self, kind: str, detail: str) -> None:
        super().__init__(detail)
        self.kind = kind
        self.detail = detail


class BrowserStream:
    """Hands out the single stream claim and passes valid chunks on to the audio process through `sink`."""

    def __init__(self, sink: queue.Queue, clock: Callable[[], float] = time.monotonic) -> None:
        self._sink = sink
        self._clock = clock
        self._lock = threading.Lock()
        self._stream_id: str | None = None
        self._last_chunk_at = 0.0

    def open(self) -> str:
        """Claim the stream and return its id. Refused while another stream is live."""
        with self._lock:
            if self._live():
                raise BrowserStreamError("busy", "Another browser is already streaming its microphone.")
            self._stream_id = secrets.token_urlsafe(16)
            self._last_chunk_at = self._clock()
            self._clear()
            self._put(("reset",))
            return self._stream_id

    def chunk(self, stream_id: str, sequence: int, sample_rate: int, pcm: bytes) -> None:
        """Queue one chunk of mono int16 samples. A stream whose id is unknown or expired must be opened again."""
        if not MIN_SAMPLE_RATE <= sample_rate <= MAX_SAMPLE_RATE:
            raise BrowserStreamError("invalid_chunk", f"The sample rate must be between {MIN_SAMPLE_RATE} and {MAX_SAMPLE_RATE} Hz.")
        if not pcm or len(pcm) % BYTES_PER_SAMPLE or len(pcm) > MAX_CHUNK_SECONDS * sample_rate * BYTES_PER_SAMPLE:
            raise BrowserStreamError("invalid_chunk", "The body must be 16-bit mono samples of at most one second.")
        with self._lock:
            self._require(stream_id)
            self._last_chunk_at = self._clock()
            self._put(("chunk", sequence, sample_rate, pcm))

    def close(self, stream_id: str) -> None:
        """Give the claim up. A stream that already expired is not an error."""
        with self._lock:
            if stream_id == self._stream_id:
                self._stream_id = None

    @property
    def active(self) -> bool:
        with self._lock:
            return self._live()

    def _live(self) -> bool:
        return self._stream_id is not None and self._clock() - self._last_chunk_at < IDLE_SECONDS

    def _require(self, stream_id: str) -> None:
        if not self._live() or not secrets.compare_digest(stream_id.encode(), self._stream_id.encode()):
            raise BrowserStreamError("unknown_stream", "This stream is not open or has expired. Open a new one.")

    def _clear(self) -> None:
        """Drop chunks of the previous stream, so the `reset` that follows fits and is not lost."""
        try:
            while True:
                self._sink.get_nowait()
        except queue.Empty:
            pass

    def _put(self, message: tuple) -> None:
        # A full queue means the audio process is not consuming; drop rather than block a request thread.
        try:
            self._sink.put_nowait(message)
        except queue.Full:
            pass
