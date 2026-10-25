"""Audio capture behind one interface, so the backend is swappable and constructed inside the process that uses it.

A capture object holds native handles and must never cross a process boundary (Windows spawns processes, so a
pickled PyAudio copy is dead on arrival). Only the backend name crosses; each process calls `create_capture`.
"""

from __future__ import annotations

import contextlib
import queue
from abc import ABC, abstractmethod
from collections.abc import Callable

from loguru import logger

from mlsc.audio_device import AudioDevice

BACKENDS = ("auto", "sounddevice", "miniaudio", "fake")


class AudioCaptureError(Exception):
    """Raised when a capture backend is missing or misused."""


class AudioCapture(ABC):
    """Mono int16 capture. Buffers are pushed to `on_data` and queued for `read`, whichever the caller uses."""

    def __init__(self) -> None:
        self._on_data: Callable[[bytes], None] | None = None
        self._buffers: queue.Queue[bytes] = queue.Queue(2)

    @abstractmethod
    def list_devices(self) -> list[AudioDevice]:
        """Return the input devices."""

    @abstractmethod
    def default_device(self) -> AudioDevice:
        """Return the system default input device."""

    def supported_sample_rates(self, device: AudioDevice) -> list[int]:
        """Return the rates `device` can capture at. Backends that cannot ask the device report only its native rate."""
        return [int(device.default_sample_rate)]

    def open(self, device: AudioDevice, sample_rate: int, frames_per_buffer: int, on_data: Callable[[bytes], None] | None = None) -> None:
        """Start capturing from `device`. Closes a previously opened stream first."""
        self.close()
        self._on_data = on_data
        self._start(device, sample_rate, frames_per_buffer)

    def read(self, timeout: float | None = None) -> bytes | None:
        """Return the next buffer, or None when none arrived within `timeout` seconds."""
        try:
            return self._buffers.get(block=timeout != 0, timeout=timeout or None)
        except queue.Empty:
            return None

    @abstractmethod
    def close(self) -> None:
        """Stop capturing. Safe to call more than once."""

    @abstractmethod
    def _start(self, device: AudioDevice, sample_rate: int, frames_per_buffer: int) -> None:
        """Open the stream; the backend calls `_deliver` for each buffer."""

    def _deliver(self, data: bytes) -> None:
        """Queue one buffer for `read` (dropping the oldest when nobody reads), then push it to the callback."""
        while True:
            try:
                self._buffers.put_nowait(data)
                break
            except queue.Full:
                with contextlib.suppress(queue.Empty):
                    self._buffers.get_nowait()
        if self._on_data is not None:
            try:
                self._on_data(data)
            except Exception:
                # This runs on the native audio thread, where an exception would kill the stream.
                logger.exception("Error in the audio capture callback.")


def create_capture(backend: str = "auto") -> AudioCapture:
    """Construct a capture for `backend`. `auto` prefers sounddevice and falls back to miniaudio."""
    if backend not in BACKENDS:
        raise AudioCaptureError(f"Unknown audio backend {backend!r}. Use one of {', '.join(BACKENDS)}.")
    # Imported here so a missing optional library only fails the backend that needs it.
    if backend == "fake":
        from mlsc.audio_capture.fake import FakeCapture  # ruff: ignore[import-outside-top-level]
        return FakeCapture()
    if backend in ("auto", "sounddevice"):
        try:
            from mlsc.audio_capture.sounddevice_backend import SoundDeviceCapture  # ruff: ignore[import-outside-top-level]
            return SoundDeviceCapture()
        except (ImportError, OSError) as e:
            if backend == "sounddevice":
                raise AudioCaptureError(f"sounddevice is unavailable: {e}. On Linux install libportaudio2.") from e
    try:
        from mlsc.audio_capture.miniaudio_backend import MiniaudioCapture  # ruff: ignore[import-outside-top-level]
        return MiniaudioCapture()
    except ImportError as e:
        raise AudioCaptureError("No audio backend is available. Install sounddevice (and libportaudio2 on Linux) or the miniaudio extra.") from e
