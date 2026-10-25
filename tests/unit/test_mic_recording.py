import io
import wave

import numpy as np

from mlsc.mic_recording import MicRecording


def samples(count, value=1000):
    return np.full(count, value, dtype=np.int16).tobytes()


def decode(wav):
    with wave.open(io.BytesIO(wav)) as file:
        return file.getframerate(), file.getnchannels(), file.getsampwidth(), np.frombuffer(file.readframes(file.getnframes()), dtype=np.int16)


def test_nothing_is_kept_until_armed():
    recording = MicRecording()

    recording.write(samples(48000), 48000)

    assert recording.wav() is None


def test_an_armed_recording_becomes_a_mono_16_bit_wav_at_the_captured_rate():
    recording = MicRecording()
    recording.arm()

    recording.write(samples(30000, 5), 44100)
    recording.write(samples(30000, 7), 44100)
    recording.disarm()

    rate, channels, width, pcm = decode(recording.wav())
    assert (rate, channels, width) == (44100, 1, 2)
    assert pcm.tolist() == [5] * 30000 + [7] * 30000


def test_writes_after_disarming_are_ignored():
    recording = MicRecording()
    recording.arm()
    recording.write(samples(30000), 48000)
    recording.disarm()

    recording.write(samples(30000), 48000)

    assert len(decode(recording.wav())[3]) == 30000


def test_a_clip_shorter_than_half_a_second_is_not_kept():
    recording = MicRecording()
    recording.arm()

    recording.write(samples(23999), 48000)

    assert recording.wav() is None


def test_a_rate_change_mid_test_drops_what_was_captured_before():
    recording = MicRecording()
    recording.arm()
    recording.write(samples(30000, 1), 48000)

    recording.write(samples(30000, 2), 44100)

    rate, _, _, pcm = decode(recording.wav())
    assert (rate, pcm.tolist()) == (44100, [2] * 30000)


def test_the_clip_stops_growing_at_the_test_window():
    recording = MicRecording(seconds=1.0)
    recording.arm()

    recording.write(samples(30000), 48000)
    recording.write(samples(30000), 48000)

    assert len(decode(recording.wav())[3]) == 48000


def test_arming_clears_the_previous_clip():
    recording = MicRecording()
    recording.arm()
    recording.write(samples(30000), 48000)

    recording.arm()

    assert recording.wav() is None


def test_clear_discards_the_clip():
    recording = MicRecording()
    recording.arm()
    recording.write(samples(30000), 48000)
    recording.disarm()

    recording.clear()

    assert recording.wav() is None
