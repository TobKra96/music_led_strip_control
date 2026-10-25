"""Keeps the audio stream of the selected device running and reports how it is doing.

Runs in the audio process. It picks the device stored as name and host API, falls back to the system default,
applies the software gain, notices a stream that stopped delivering, and retries with backoff.
"""
from __future__ import annotations

import time
from collections.abc import Callable

import numpy as np
from loguru import logger

from mlsc.audio_capture import AudioCapture
from mlsc.audio_device import AudioDevice

FULL_SCALE = np.iinfo(np.int16).max
FIRST_RETRY_SECONDS = 1.0
MAX_RETRY_SECONDS = 30.0
# A stream that delivers nothing for this long counts as gone, as when a USB microphone is unplugged.
STALL_SECONDS = 2.0

_PERMISSION_MARKERS = ("permission", "errno 13", "access is denied", "access denied")
_NO_DEVICE_MARKERS = ("no input device", "device unavailable", "no such device", "invalid device", "-9996", "-9985")

_EMPTY_STATUS = {"device": None, "host_api": None, "sample_rate": None, "fallback": False}


def classify_error(error: Exception) -> str:
    """Return the kind of a failed open: `permission_denied`, `no_device` or `open_failed`."""
    text = str(error).lower()
    if isinstance(error, PermissionError) or any(marker in text for marker in _PERMISSION_MARKERS):
        return "permission_denied"
    if any(marker in text for marker in _NO_DEVICE_MARKERS):
        return "no_device"
    return "open_failed"


class MicSupervisor:
    """Status `state` is `starting` until the first buffer arrives, then `ok`, or `error` with a `kind` and `retry_in` seconds.

    `restarts` counts the configs applied with `start`, so whoever applied one can tell when its status arrives.
    """

    def __init__(self, capture: AudioCapture, on_buffer: Callable[[bytes], None], report: Callable[[dict], None] = lambda _status: None,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self._capture = capture
        self._on_buffer = on_buffer
        self._report = report
        self._clock = clock
        self.status: dict = {}
        self._audio: dict = {}
        self._gain = 1.0
        self._retry_delay = FIRST_RETRY_SECONDS
        self._retry_at: float | None = None
        self._last_audio_at = 0.0
        self._restarts = 0

    def start(self, audio: dict) -> None:
        """Open the device that `audio` (the config section) selects. A failure is reported and retried by `poll`."""
        self._audio = audio
        self._restarts += 1
        self._retry_delay = FIRST_RETRY_SECONDS
        self._open()

    def poll(self) -> None:
        """Call regularly from the audio process: notices a stalled stream and retries a failed device once its backoff has passed."""
        now = self._clock()
        if self._retry_at is not None and now >= self._retry_at:
            self._open()
        elif self.status.get("state") in {"starting", "ok"} and now - self._last_audio_at >= STALL_SECONDS:
            self._fail(f"No audio from {self.status['device']!r} for {STALL_SECONDS:g} s. It may have been unplugged.", "no_device")

    def _open(self) -> None:
        self._retry_at = None
        self._capture.close()
        self._gain = self._audio["gain"]
        try:
            device, message = self._select(self._audio["device_name"], self._audio["host_api"])
            sample_rate = self._audio["sample_rate"] or int(device.default_sample_rate)
            self._set_status({
                "state": "starting", "device": device.name, "host_api": device.host_api, "sample_rate": sample_rate,
                "fallback": message is not None, "message": message, "kind": None, "retry_in": None,
                "restarts": self._restarts,
            })
            self._last_audio_at = self._clock()
            self._capture.open(device, sample_rate, self._audio["frames_per_buffer"], on_data=self._receive)
        except Exception as e:
            self._fail(str(e) or type(e).__name__, classify_error(e))
        else:
            self._retry_delay = FIRST_RETRY_SECONDS

    def _fail(self, message: str, kind: str) -> None:
        logger.error(f"Microphone problem: {message}")
        self._capture.close()
        self._set_status({
            **_EMPTY_STATUS, **self.status, "state": "error", "kind": kind, "message": message, "retry_in": self._retry_delay,
            "restarts": self._restarts,
        })
        self._retry_at = self._clock() + self._retry_delay
        self._retry_delay = min(self._retry_delay * 2, MAX_RETRY_SECONDS)

    def _select(self, name: str | None, host_api: str | None) -> tuple[AudioDevice, str | None]:
        """Return the stored device, or the system default and why it was not used."""
        if name is None:
            return self._capture.default_device(), None
        match = next((d for d in self._capture.list_devices() if d.matches(name, host_api)), None)
        if match is not None:
            return match, None
        return self._capture.default_device(), f"Microphone {name!r} not found. Using the system default."

    def _set_status(self, status: dict) -> None:
        self.status = status
        self._report(dict(status))

    def _receive(self, data: bytes) -> None:
        self._last_audio_at = self._clock()
        if self.status.get("state") != "ok":
            self._set_status({**self.status, "state": "ok"})
        if self._gain != 1.0:
            samples = np.frombuffer(data, dtype=np.int16) * self._gain
            data = np.clip(samples, -FULL_SCALE, FULL_SCALE).astype(np.int16).tobytes()
        self._on_buffer(data)
