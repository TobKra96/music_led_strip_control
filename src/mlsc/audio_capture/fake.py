"""Deterministic capture for tests and hardware-free runs: synthetic signals and WAV fixtures, fed on demand."""

from __future__ import annotations

import wave
from collections.abc import Callable, Iterator
from pathlib import Path

import numpy as np

from mlsc.audio_capture import AudioCapture, AudioCaptureError
from mlsc.audio_device import AudioDevice

FULL_SCALE = np.iinfo(np.int16).max

# A source maps (frames, sample_rate) to a generator that yields one int16 array of `frames` samples per next().
Source = Callable[[int, int], Iterator[np.ndarray]]


def silence() -> Source:
    def source(frames, sample_rate):
        while True:
            yield np.zeros(frames, dtype=np.int16)
    return source


def clipping() -> Source:
    """Full-scale square wave."""
    def source(frames, sample_rate):
        buffer = np.where(np.arange(frames) % 2 == 0, FULL_SCALE, -FULL_SCALE).astype(np.int16)
        while True:
            yield buffer
    return source


def sine_sweep(start_hz: float, end_hz: float, seconds: float = 5.0, amplitude: float = 0.5) -> Source:
    """Linear chirp from `start_hz` to `end_hz` over `seconds`, then repeating."""
    def source(frames, sample_rate):
        total = int(seconds * sample_rate)
        position = 0
        while True:
            t = (position + np.arange(frames)) % total / sample_rate
            phase = 2 * np.pi * (start_hz * t + (end_hz - start_hz) / (2 * seconds) * t**2)
            yield (amplitude * FULL_SCALE * np.sin(phase)).astype(np.int16)
            position += frames
    return source


def wav_file(path: str | Path) -> Source:
    """Replay a 16-bit mono WAV in buffer-sized chunks, looping; a short tail is zero-padded."""
    def source(frames, sample_rate):
        with wave.open(str(path), "rb") as wav:
            data = np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.int16)
        position = 0
        while True:
            chunk = np.zeros(frames, dtype=np.int16)
            part = data[position:position + frames]
            chunk[:len(part)] = part
            yield chunk
            position = position + frames if position + frames < len(data) else 0
    return source


class FakeCapture(AudioCapture):
    """Produces one buffer per `feed()` call, so tests control timing without threads."""

    def __init__(self, source: Source | None = None) -> None:
        super().__init__()
        self._source = source or silence()
        self._generator: Iterator[np.ndarray] | None = None

    def list_devices(self) -> list[AudioDevice]:
        return [AudioDevice(0, "Fake Mic", 44100), AudioDevice(1, "Fake Monitor", 48000)]

    def default_device(self) -> AudioDevice:
        return self.list_devices()[0]

    def _start(self, device, sample_rate, frames_per_buffer) -> None:
        self._generator = self._source(frames_per_buffer, sample_rate)

    def feed(self) -> None:
        if self._generator is None:
            raise AudioCaptureError("The fake capture is not open.")
        self._deliver(next(self._generator).tobytes())

    def close(self) -> None:
        self._generator = None
        self._on_data = None
