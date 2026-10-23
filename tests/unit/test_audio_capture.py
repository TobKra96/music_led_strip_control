import sys
import types
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


def test_a_capture_is_created_by_backend_name():
    assert isinstance(create_capture("fake"), FakeCapture)
    with pytest.raises(AudioCaptureError):
        create_capture("nope")


def test_a_failing_callback_does_not_break_delivery_or_read():
    def broken(_):
        message = "boom"
        raise ValueError(message)

    capture = FakeCapture(source=silence())
    capture.open(capture.default_device(), RATE, BUFFER, on_data=broken)

    capture.feed()

    assert capture.read(timeout=0) is not None


class StubSoundDevice(types.ModuleType):
    """Stands in for the sounddevice module: two devices (one output-only) on one host API."""

    def __init__(self) -> None:
        super().__init__("sounddevice")
        self.default = types.SimpleNamespace(hostapi=0)
        self.streams = []
        outer = self

        class InputStream:
            def __init__(self, **kwargs) -> None:
                self.kwargs, self.started, self.closed = kwargs, False, False
                outer.streams.append(self)

            def start(self):
                self.started = True

            def stop(self):
                self.started = False

            def close(self):
                self.closed = True

        self.InputStream = InputStream

    @staticmethod
    def query_hostapis(_index):
        return {"devices": [0, 1]}

    @staticmethod
    def query_devices(index=None, kind=None):
        devices = [
            {"name": "Speakers", "max_input_channels": 0, "default_samplerate": 48000.0, "index": 0},
            {"name": "USB Mic", "max_input_channels": 1, "default_samplerate": 44100.0, "index": 1},
        ]
        return devices[1] if kind == "input" else devices[index]


@pytest.fixture
def sounddevice_stub(monkeypatch):
    stub = StubSoundDevice()
    monkeypatch.setitem(sys.modules, "sounddevice", stub)
    monkeypatch.delitem(sys.modules, "mlsc.audio_capture.sounddevice_backend", raising=False)
    return stub


@pytest.mark.usefixtures("sounddevice_stub")
def test_sounddevice_lists_only_input_devices():
    capture = create_capture("sounddevice")

    assert [(d.device_id, d.name) for d in capture.list_devices()] == [(1, "USB Mic")]
    assert capture.default_device().name == "USB Mic"


def test_sounddevice_streams_int16_mono_buffers_and_closes(sounddevice_stub):
    capture = create_capture("sounddevice")
    received = []
    capture.open(capture.default_device(), RATE, BUFFER, on_data=received.append)
    stream = sounddevice_stub.streams[0]

    stream.kwargs["callback"](np.arange(4, dtype=np.int16).reshape(4, 1), 4, None, None)
    capture.close()
    capture.close()

    assert (stream.kwargs["device"], stream.kwargs["channels"], stream.kwargs["dtype"], stream.kwargs["blocksize"]) == (1, 1, "int16", BUFFER)
    assert samples(received[0]).tolist() == [0, 1, 2, 3]
    assert stream.closed
    assert not stream.started


class StubMiniaudio(types.ModuleType):
    def __init__(self) -> None:
        super().__init__("miniaudio")
        self.devices = []
        outer = self
        self.SampleFormat = types.SimpleNamespace(SIGNED16="s16")

        class Devices:
            @staticmethod
            def get_captures():
                return [{"name": "Mic A", "id": "a"}, {"name": "Mic B", "id": "b"}]

        class CaptureDevice:
            def __init__(self, **kwargs) -> None:
                self.kwargs, self.stopped, self.closed = kwargs, False, False
                outer.devices.append(self)

            def start(self, generator):
                self.generator = generator

            def stop(self):
                self.stopped = True

            def close(self):
                self.closed = True

        self.Devices, self.CaptureDevice = Devices, CaptureDevice


@pytest.fixture
def miniaudio_stub(monkeypatch):
    stub = StubMiniaudio()
    monkeypatch.setitem(sys.modules, "miniaudio", stub)
    monkeypatch.delitem(sys.modules, "mlsc.audio_capture.miniaudio_backend", raising=False)
    return stub


@pytest.mark.usefixtures("miniaudio_stub")
def test_miniaudio_lists_captures_by_position():
    capture = create_capture("miniaudio")

    assert [(d.device_id, d.name) for d in capture.list_devices()] == [(0, "Mic A"), (1, "Mic B")]
    assert capture.default_device().device_id == -1


def test_miniaudio_rechunks_to_the_requested_buffer_size(miniaudio_stub):
    capture = create_capture("miniaudio")
    capture.open(capture.list_devices()[1], RATE, 4)
    device = miniaudio_stub.devices[0]

    device.generator.send(b"\x01\x00" * 3)
    device.generator.send(b"\x02\x00" * 6)

    assert device.kwargs["device_id"] == "b"
    assert samples(capture.read(timeout=0)).tolist() == [1, 1, 1, 2]
    assert samples(capture.read(timeout=0)).tolist() == [2, 2, 2, 2]
    assert capture.read(timeout=0) is None
    capture.close()
    assert device.stopped
    assert device.closed


def test_miniaudio_default_device_passes_no_device_id(miniaudio_stub):
    capture = create_capture("miniaudio")
    capture.open(capture.default_device(), RATE, BUFFER)

    assert miniaudio_stub.devices[0].kwargs["device_id"] is None


@pytest.mark.usefixtures("miniaudio_stub")
def test_auto_falls_back_to_miniaudio_without_sounddevice(monkeypatch):
    monkeypatch.setitem(sys.modules, "sounddevice", None)
    monkeypatch.delitem(sys.modules, "mlsc.audio_capture.sounddevice_backend", raising=False)

    assert type(create_capture("auto")).__name__ == "MiniaudioCapture"
    with pytest.raises(AudioCaptureError):
        create_capture("sounddevice")


def test_no_backend_available_is_a_clear_error(monkeypatch):
    for name in ("sounddevice", "miniaudio"):
        monkeypatch.setitem(sys.modules, name, None)
    monkeypatch.delitem(sys.modules, "mlsc.audio_capture.sounddevice_backend", raising=False)
    monkeypatch.delitem(sys.modules, "mlsc.audio_capture.miniaudio_backend", raising=False)

    with pytest.raises(AudioCaptureError):
        create_capture("auto")
