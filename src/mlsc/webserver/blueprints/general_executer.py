from __future__ import annotations

from loguru import logger

from mlsc.audio_capture import AudioCaptureError, create_capture
from mlsc.audio_device import AudioDevice
from mlsc.audio_info import AudioInfo
from mlsc.effects_enum import EffectNames, EffectsEnum
from mlsc.webserver.executer_base import ExecuterBase


class GeneralExecuter(ExecuterBase):

    def get_colors(self) -> dict[str, str]:
        """Return colors."""
        return {key: key for key in self._config["colors"]}

    def get_gradients(self) -> dict[str, str]:
        """Return gradients."""
        return {key: key for key in self._config["gradients"]}

    def get_logging_levels(self) -> dict[str, str]:
        """Return logging levels."""
        return dict(self._config["logging_levels"])

    def list_audio_devices(self) -> list[AudioDevice]:
        """Return the input devices, or none if no audio backend is available."""
        try:
            capture = create_capture(self._audio_backend)
        except AudioCaptureError as e:
            logger.warning(f"Cannot list the audio devices: {e}")
            return []
        try:
            return AudioInfo.get_audio_devices(capture)
        finally:
            capture.close()

    def get_audio_devices(self) -> dict:
        """Return audio devices."""
        return {value.device_id: value.to_string() for value in self.list_audio_devices()}

    @staticmethod
    def get_output_types() -> dict[str, str]:
        """Return output types."""
        return {
            "output_raspi": "Output Raspberry Pi",
            "output_udp": "Output Network via UDP"
        }

    @staticmethod
    def get_effects() -> dict[str, dict]:
        """Return effects."""
        return {
            "non_music": EffectNames.non_music,
            "music": EffectNames.music,
            "special": EffectNames.special,
            "order": {effect.name: index for index, effect in enumerate(EffectsEnum, 1)}
        }
