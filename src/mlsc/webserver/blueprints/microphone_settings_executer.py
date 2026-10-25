from __future__ import annotations

import copy
import time
from collections.abc import Callable

from loguru import logger

from mlsc import operations
from mlsc.audio_capture import AudioCaptureError, create_capture
from mlsc.audio_info import AudioInfo
from mlsc.audio_status import AudioStatus
from mlsc.mic_level import MicLevel
from mlsc.mixer import Mixer, MixerError, find_mixer
from mlsc.notification_enum import NotificationEnum
from mlsc.operations import Operation, RetryPolicy
from mlsc.webserver.executer_base import ExecuterBase, merge

FRAMES_PER_BUFFER_CHOICES = (256, 512, 1024, 2048, 4096)
# Changing only these reopens the audio stream; anything else also reaches the effects, so every process reloads the config.
STREAM_ONLY_KEYS = frozenset({"device_name", "host_api", "gain"})
# How long an applied change may take until audio arrives from the new device.
APPLY_SECONDS = 8.0
TEST_SECONDS = 2.0
POLL_SECONDS = 0.1
# Peak level below which the test counts the input as silent.
SILENCE_LEVEL = 0.01

TEST_RESULTS = {
    "ok": ("The microphone works.", None),
    "silence": (
        "The microphone delivers only silence.",
        (
            "Check that it is not muted, raise the hardware or software gain, or play something louder. "
            "For a Monitor Device, make sure audio is playing."
        ),
    ),
    "no_device": (
        "No audio arrives from the microphone.",
        "Plug the microphone in or pick another device, then apply.",
    ),
    "permission_denied": (
        "MLSC is not allowed to open the microphone.",
        (
            "On Linux, add the user that runs MLSC to the audio group (sudo usermod -aG audio <user>) and restart MLSC. "
            "On Windows or macOS, allow microphone access for Python in the privacy settings."
        ),
    ),
    "error": ("The microphone could not be opened.", "Pick another device or a different sample rate, then apply."),
}


def _mixer_state(mixer: Mixer) -> dict:
    return {"available": True, "card": mixer.card, "control": mixer.control, "level": mixer.get_level()}


class MicrophoneApplyError(Exception):
    """Why an applied microphone change did not work."""


class MicrophoneSettingsExecuter(ExecuterBase):
    _mic_level: MicLevel | None = None
    _audio_status: AudioStatus | None = None
    # Injectable for tests, so the apply and test waits never sleep for real.
    _clock: Callable[[], float] = staticmethod(time.monotonic)
    _sleep: Callable[[float], None] = staticmethod(time.sleep)

    def connect_audio(self, mic_level: MicLevel | None, audio_status: AudioStatus | None) -> None:
        """Give access to the level and status that the audio process shares."""
        self._mic_level = mic_level
        self._audio_status = audio_status

    # Settings and devices

    def get_settings(self) -> dict:
        return copy.deepcopy(self._config["audio"])

    def get_status(self) -> dict:
        """Return the status of the audio stream, as reported by the audio process. Empty until it has started."""
        return self._audio_status.read() if self._audio_status is not None else {}

    def list_devices(self) -> list[dict]:
        """Return the input devices with their host API, native and supported rates, and whether each is a Monitor Device."""
        try:
            capture = create_capture(self._audio_backend)
        except AudioCaptureError as e:
            logger.warning(f"No audio backend: {e}")
            return []
        default = AudioInfo.get_default_audio_device(capture)
        return [
            {
                "name": device.name,
                "host_api": device.host_api,
                "default_sample_rate": int(device.default_sample_rate),
                "sample_rates": capture.supported_sample_rates(device),
                "monitor": device.is_monitor,
                "default": device.matches(default.name, default.host_api),
            }
            for device in AudioInfo.get_audio_devices(capture)
        ]

    def validate(self, patch: dict) -> list[dict]:
        """Return a field error for each value of `patch` that the selected device cannot use."""
        target = merge(self.get_settings(), patch)
        errors = []
        if "frames_per_buffer" in patch and patch["frames_per_buffer"] not in FRAMES_PER_BUFFER_CHOICES:
            errors.append({"field": "frames_per_buffer", "detail": f"Must be one of {', '.join(map(str, FRAMES_PER_BUFFER_CHOICES))}."})
        if target["min_frequency"] >= target["max_frequency"]:
            errors.append({"field": "min_frequency", "detail": "Must be lower than max_frequency."})
        if not {"device_name", "host_api", "sample_rate"} & patch.keys():
            return errors
        selects_device = bool({"device_name", "host_api"} & patch.keys())

        devices = self.list_devices()
        if target["device_name"] is None:
            device = next((d for d in devices if d["default"]), None)
        else:
            device = next((d for d in devices if d["name"] == target["device_name"]
                           and target["host_api"] in {None, d["host_api"]}), None)
            if device is None and selects_device:
                errors.append({"field": "device_name", "detail": f"There is no input device {target['device_name']!r}."})
        if target["sample_rate"] is not None and device is not None and target["sample_rate"] not in device["sample_rates"]:
            rates = ", ".join(map(str, device["sample_rates"]))
            errors.append({"field": "sample_rate", "detail": f"{device['name']} supports {rates} Hz, or null for its native rate."})
        return errors

    # Apply

    def apply(self, patch: dict) -> Operation:
        """Save `patch` and restart the audio stream as an Operation that rolls back to the last working settings when no audio arrives."""
        previous = self.get_settings()
        target = merge(self.get_settings(), patch)
        notification = NotificationEnum.audio_restart if patch.keys() <= STREAM_ONLY_KEYS else NotificationEnum.config_refresh
        # Falling back to the system default only fails a change that picks a device; while the stored one is unplugged, other changes still apply.
        fallback_fails = bool({"device_name", "host_api"} & patch.keys())
        restarts_before = 0

        def apply() -> None:
            nonlocal restarts_before
            restarts_before = self.get_status().get("restarts", 0)
            self._save_audio(target, notification)

        def verify() -> bool:
            deadline = self._clock() + APPLY_SECONDS
            while self._clock() < deadline:
                status = self.get_status()
                if status.get("restarts", 0) > restarts_before:
                    fallback = status["fallback"] and fallback_fails
                    if status["state"] == "ok" and not fallback:
                        return True
                    if status["state"] == "error" or fallback:
                        raise MicrophoneApplyError(status["message"])
                self._sleep(POLL_SECONDS)
            message = "No audio arrived from the new device in time."
            raise MicrophoneApplyError(message)

        def rollback() -> None:
            self._save_audio(previous, notification)

        return operations.registry.start("microphone", apply, verify, rollback, policy=RetryPolicy(attempts=1))

    def _save_audio(self, audio: dict, notification: NotificationEnum) -> None:
        self._config["audio"] = copy.deepcopy(audio)
        self.save_config()
        self.put_into_notification_queue(notification, self.all_devices_id)

    # Test

    def test(self) -> dict:
        """Watch the live input for a moment and say whether it works, and if not, how to fix it."""
        peak = 0.0
        deadline = self._clock() + TEST_SECONDS
        while self._clock() < deadline and self.get_status().get("state") != "error":
            if self._mic_level is not None:
                peak = max(peak, self._mic_level.read())
            self._sleep(POLL_SECONDS)

        status = self.get_status()
        if status.get("state") == "error":
            result = status["kind"] if status["kind"] in TEST_RESULTS else "error"
        elif status.get("state") != "ok":
            result = "no_device"
        elif peak < SILENCE_LEVEL:
            result = "silence"
        else:
            result = "ok"
        message, hint = TEST_RESULTS[result]
        return {"result": result, "message": message, "hint": hint, "peak": round(peak, 3), "device": status.get("device")}

    # Hardware gain

    def find_mixer(self) -> Mixer | None:
        """Return the capture control of the device in use, or of the stored one before the audio process has reported."""
        return find_mixer(self.get_status().get("device") or self._config["audio"]["device_name"])

    def get_mixer(self) -> dict:
        mixer = self.find_mixer()
        if mixer is None:
            return {"available": False, "card": None, "control": None, "level": None}
        return _mixer_state(mixer)

    def set_mixer(self, level: int) -> dict | None:
        """Set the hardware capture level. Returns None when the device has no hardware gain."""
        mixer = self.find_mixer()
        if mixer is None:
            return None
        mixer.set_level(level)
        return _mixer_state(mixer)

    # API v1

    def microphone_get_volume(self) -> dict:
        """Return information about the microphone volume."""
        try:
            mixer = self.get_mixer()
        except MixerError as e:
            return {"level": 0, "output": "", "error": str(e), "returncode": 1}
        if not mixer["available"]:
            return {"level": 0, "output": "", "error": "The microphone has no hardware gain.", "returncode": 1}
        return {"level": mixer["level"], "output": f"{mixer['control']} on card {mixer['card']}: {mixer['level']}%", "error": "", "returncode": 0}

    def microphone_set_volume(self, level) -> dict:
        """Set the microphone volume."""
        try:
            mixer = self.set_mixer(int(level))
        except (MixerError, ValueError) as e:
            return {"output": "", "error": str(e), "returncode": 1}
        if mixer is None:
            return {"output": "", "error": "The microphone has no hardware gain.", "returncode": 1}
        return {"output": f"{mixer['control']} on card {mixer['card']}: {mixer['level']}%", "error": "", "returncode": 0}
