from __future__ import annotations

import miniaudio

from mlsc.audio_capture import AudioCapture
from mlsc.audio_device import AudioDevice

DEFAULT_SAMPLE_RATE = 44100


class MiniaudioCapture(AudioCapture):
    """miniaudio fallback for hosts without PortAudio. Device ids are positions in the capture list."""

    def __init__(self) -> None:
        super().__init__()
        self._device = None

    def list_devices(self) -> list[AudioDevice]:
        return [AudioDevice(i, info["name"], DEFAULT_SAMPLE_RATE) for i, info in enumerate(miniaudio.Devices().get_captures())]

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
            device_id = miniaudio.Devices().get_captures()[device.device_id]["id"]
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
