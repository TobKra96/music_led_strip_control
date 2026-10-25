from types import SimpleNamespace

import numpy as np

from mlsc.audio_process_service import AudioProcessService
from mlsc.mic_recording import MicRecording


def service(recording, rate=48000, skip=False):
    service = object.__new__(AudioProcessService)
    service._skip_routine = skip
    service._mic_level = None
    service._mic_recording = recording
    service._supervisor = SimpleNamespace(status={"sample_rate": rate})
    service.audio_buffer_queue = SimpleNamespace(put_none_blocking=lambda _data: None)
    service.start_time_1 = service.end_time_1 = 0.0
    service.ten_seconds_counter_1 = 1e12
    return service


def test_the_buffers_delivered_while_armed_are_kept_at_the_rate_of_the_stream():
    recording = MicRecording()
    recording.arm()
    audio = service(recording, rate=44100)

    audio._on_buffer(np.full(30000, 9, dtype=np.int16).tobytes())  # ruff: ignore[private-member-access]

    assert recording.wav() is not None


def test_nothing_is_kept_while_disarmed():
    recording = MicRecording()
    audio = service(recording)

    audio._on_buffer(np.full(48000, 9, dtype=np.int16).tobytes())  # ruff: ignore[private-member-access]

    assert recording.wav() is None
