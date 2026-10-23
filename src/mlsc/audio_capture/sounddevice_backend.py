from __future__ import annotations

import sounddevice

from mlsc.audio_capture import AudioCapture
from mlsc.audio_device import AudioDevice


def _to_device(index: int, info: dict) -> AudioDevice:
    return AudioDevice(index, info["name"], info["default_samplerate"])


class SoundDeviceCapture(AudioCapture):
    """PortAudio through sounddevice. Needs libportaudio2 on Linux; Windows and macOS wheels bundle it."""

    def __init__(self) -> None:
        super().__init__()
        self._stream = None

    def list_devices(self) -> list[AudioDevice]:
        # Only the default host API: Windows exposes every device once per API (MME, DirectSound, WASAPI...).
        indexes = sounddevice.query_hostapis(sounddevice.default.hostapi)["devices"]
        devices = []
        for index in indexes:
            info = sounddevice.query_devices(index)
            if info["max_input_channels"] >= 1:
                devices.append(_to_device(index, info))
        return devices

    def default_device(self) -> AudioDevice:
        info = sounddevice.query_devices(kind="input")
        return _to_device(info["index"], info)

    def _start(self, device, sample_rate, frames_per_buffer) -> None:
        def callback(indata, frames, time_info, status):
            self._deliver(indata.tobytes())

        self._stream = sounddevice.InputStream(
            device=device.device_id, channels=1, samplerate=sample_rate, blocksize=frames_per_buffer,
            dtype="int16", callback=callback)
        self._stream.start()

    def close(self) -> None:
        stream, self._stream = self._stream, None
        self._on_data = None
        if stream is not None:
            stream.stop()
            stream.close()
