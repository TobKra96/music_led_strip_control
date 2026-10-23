from loguru import logger

from mlsc.audio_capture import AudioCapture
from mlsc.audio_device import AudioDevice


class AudioInfo:
    @staticmethod
    def get_audio_devices(capture: AudioCapture) -> list[AudioDevice]:
        logger.debug("Get audio devices.")
        try:
            audio_devices = capture.list_devices()
        except OSError as e:
            logger.error(f"OS error: {e}")
            return []
        except Exception:
            logger.exception("Unexpected error in AudioInfo.")
            return []

        for audio_device in audio_devices:
            logger.debug(f"Found audio Device: {audio_device.to_string()}")
        logger.debug(f"Found {len(audio_devices)} audio devices.")
        return audio_devices

    @staticmethod
    def select_audio_device(capture: AudioCapture, audio_devices: list[AudioDevice], device_name: str | None) -> AudioDevice:
        """Return the device called `device_name`, or the system default when there is no such device."""
        match = next((device for device in audio_devices if device.name == device_name), None)
        return match if match is not None else AudioInfo.get_default_audio_device(capture)

    @staticmethod
    def get_default_audio_device(capture: AudioCapture) -> AudioDevice:
        try:
            return capture.default_device()
        except OSError as e:
            logger.error(f"OS error: {e}")
        except Exception:
            logger.error("Unexpected error in AudioInfo get_default_audio_device.")
        return AudioDevice(0, "Error", 44100)
