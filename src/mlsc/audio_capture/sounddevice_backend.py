from __future__ import annotations

import sounddevice

from mlsc.audio_capture import AudioCapture
from mlsc.audio_device import AudioDevice


# Probed for each device; PortAudio cannot list the rates a device supports, only check one at a time.
COMMON_SAMPLE_RATES = (8000, 11025, 16000, 22050, 32000, 44100, 48000, 88200, 96000)


def _to_device(index: int, info: dict) -> AudioDevice:
    host_api = sounddevice.query_hostapis(info["hostapi"])["name"]
    return AudioDevice(index, info["name"], info["default_samplerate"], host_api)


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

    def supported_sample_rates(self, device: AudioDevice) -> list[int]:
        rates = []
        for rate in COMMON_SAMPLE_RATES:
            try:
                sounddevice.check_input_settings(device=device.device_id, channels=1, dtype="int16", samplerate=rate)
            except Exception:  # PortAudio raises its own error types, and ValueError for an unknown device.
                continue
            rates.append(rate)
        # A device in use by the running stream may refuse every probe, but its native rate always works.
        return sorted({*rates, int(device.default_sample_rate)})

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
