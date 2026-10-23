import pickle
import wave

import numpy as np
import pytest

from mlsc.audio_capture import AudioCaptureError, create_capture
from mlsc.audio_capture.fake import FakeCapture, clipping, silence, sine_sweep, wav_file

pytestmark = pytest.mark.unit

RATE = 44100
BUFFER = 512


def samples(data):
    return np.frombuffer(data, dtype=np.int16)


def open_fake(**kwargs):
    capture = FakeCapture(**kwargs)
    capture.open(capture.default_device(), RATE, BUFFER)
    return capture


def test_lists_input_devices_and_a_default():
    capture = FakeCapture()

    assert [device.name for device in capture.list_devices()] == ["Fake Mic", "Fake Monitor"]
    assert capture.default_device().name == "Fake Mic"


def test_pushes_each_buffer_to_the_callback():
    received = []
    capture = FakeCapture(source=silence())
    capture.open(capture.default_device(), RATE, BUFFER, on_data=received.append)

    capture.feed()
    capture.feed()

    assert [len(data) for data in received] == [BUFFER * 2, BUFFER * 2]


def test_read_returns_fed_buffers_in_order_and_none_when_empty():
    capture = open_fake(source=sine_sweep(100, 2000))

    capture.feed()
    first = capture.read(timeout=0)
    capture.feed()
    second = capture.read(timeout=0)

    assert len(samples(first)) == BUFFER
    assert not np.array_equal(samples(first), samples(second))
    assert capture.read(timeout=0) is None


def test_read_drops_the_oldest_buffers_when_nobody_reads():
    capture = open_fake(source=sine_sweep(100, 2000))
    for _ in range(5):
        capture.feed()

    assert capture.read(timeout=0) is not None
    assert capture.read(timeout=0) is not None
    assert capture.read(timeout=0) is None


def test_silence_is_all_zero():
    capture = open_fake(source=silence())
    capture.feed()

    assert not samples(capture.read(timeout=0)).any()


def test_clipping_reaches_full_scale():
    capture = open_fake(source=clipping())
    capture.feed()

    assert samples(capture.read(timeout=0)).max() == np.iinfo(np.int16).max


def test_sine_sweep_oscillates_within_full_scale():
    capture = open_fake(source=sine_sweep(100, 2000))
    capture.feed()
    data = samples(capture.read(timeout=0))

    assert 0 < np.abs(data).max() <= np.iinfo(np.int16).max
    assert (np.diff(np.sign(data)) != 0).sum() > 2


def test_wav_fixture_is_replayed_in_buffer_sized_chunks(tmp_path):
    path = tmp_path / "tone.wav"
    expected = (np.arange(BUFFER * 2) % 100).astype(np.int16)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes(expected.tobytes())
    capture = open_fake(source=wav_file(path))

    capture.feed()
    capture.feed()

    assert np.array_equal(samples(capture.read(timeout=0)), expected[:BUFFER])
    assert np.array_equal(samples(capture.read(timeout=0)), expected[BUFFER:])


def test_feed_requires_an_open_stream():
    with pytest.raises(AudioCaptureError):
        FakeCapture().feed()


def test_close_stops_delivery_and_is_idempotent():
    received = []
    capture = FakeCapture(source=silence())
    capture.open(capture.default_device(), RATE, BUFFER, on_data=received.append)

    capture.close()
    capture.close()

    with pytest.raises(AudioCaptureError):
        capture.feed()
    assert received == []


def test_a_capture_is_created_by_backend_name_and_the_name_pickles():
    assert isinstance(create_capture("fake"), FakeCapture)
    assert pickle.loads(pickle.dumps("fake")) == "fake"
    with pytest.raises(AudioCaptureError):
        create_capture("nope")
