from __future__ import annotations

import miniaudio

from mlsc.audio_capture import AudioCapture, AudioCaptureError
from mlsc.audio_device import AudioDevice

DEFAULT_SAMPLE_RATE = 44100


def _native_sample_rate(info: dict) -> int:
    """Return the device's rate: a common one when it supports it, else the highest it reports, else the default."""
    rates = [int(entry[2]) for entry in info.get("formats", ()) if len(entry) > 2 and entry[2]]
    return next((rate for rate in (48000, 44100) if rate in rates), max(rates, default=DEFAULT_SAMPLE_RATE))


class MiniaudioCapture(AudioCapture):
    """miniaudio fallback for hosts without PortAudio. Device ids are positions in the capture list."""

    def __init__(self) -> None:
        super().__init__()
        self._device = None

    def list_devices(self) -> list[AudioDevice]:
        return [AudioDevice(i, info["name"], _native_sample_rate(info)) for i, info in enumerate(miniaudio.Devices().get_captures())]

    def default_device(self) -> AudioDevice:
        # miniaudio picks the system default when no device id is given, so the id is never used for it.
        return AudioDevice(-1, "Default", DEFAULT_SAMPLE_RATE)

    def _start(self, device, sample_rate, frames_per_buffer) -> None:
        size = frames_per_buffer * 2
        pending = bytearray()

        def stream():
            while True:
                pending.extend((yield))
                while len(pending) >= size:
                    self._deliver(bytes(pending[:size]))
                    del pending[:size]

        generator = stream()
        next(generator)
        device_id = None
        if device.device_id >= 0:
            # The position can shift between `list_devices` and here when a device is plugged in, so go by name.
            named = [(i, info) for i, info in enumerate(miniaudio.Devices().get_captures()) if info["name"] == device.name]
            # Two identical devices share a name, so the listed position breaks the tie while it still fits.
            match = next((info for i, info in named if i == device.device_id), named[0][1] if named else None)
            if match is None:
                raise AudioCaptureError(f"The audio device {device.name!r} is no longer available.")
            device_id = match["id"]
        self._device = miniaudio.CaptureDevice(
            input_format=miniaudio.SampleFormat.SIGNED16, nchannels=1, sample_rate=sample_rate,
            buffersize_msec=max(1, frames_per_buffer * 1000 // sample_rate), device_id=device_id)
        self._device.start(generator)

    def close(self) -> None:
        device, self._device = self._device, None
        self._on_data = None
        if device is not None:
            device.stop()
            device.close()
