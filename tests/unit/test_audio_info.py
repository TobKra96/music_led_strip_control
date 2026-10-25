import pytest

from mlsc.audio_capture.fake import FakeCapture
from mlsc.audio_device import AudioDevice
from mlsc.audio_info import AudioInfo

pytestmark = pytest.mark.unit

DEVICES = [AudioDevice(0, "Built-in Mic", 44100), AudioDevice(3, "USB Mic", 48000)]


def raise_no_audio():
    message = "no audio"
    raise OSError(message)


def raise_unexpected():
    message = "boom"
    raise RuntimeError(message)


class CrashingCapture(FakeCapture):
    @staticmethod
    def list_devices():
        raise_unexpected()

    @staticmethod
    def default_device():
        raise_unexpected()


class BrokenCapture(FakeCapture):
    @staticmethod
    def list_devices():
        raise_no_audio()

    @staticmethod
    def default_device():
        raise_no_audio()


def test_device_is_selected_by_name():
    selected = AudioInfo.select_audio_device(FakeCapture(), DEVICES, "USB Mic")

    assert (selected.device_id, selected.name) == (3, "USB Mic")


@pytest.mark.parametrize("device_name", [None, "Unplugged Mic"])
def test_no_or_unknown_name_selects_the_system_default(device_name):
    selected = AudioInfo.select_audio_device(FakeCapture(), DEVICES, device_name)

    assert (selected.device_id, selected.name) == (0, "Fake Mic")


def test_unreadable_system_default_still_returns_a_device():
    selected = AudioInfo.select_audio_device(BrokenCapture(), [], None)

    assert selected.name == "Error"


def test_unreadable_device_list_is_empty():
    assert AudioInfo.get_audio_devices(BrokenCapture()) == []


def test_unexpected_error_in_the_device_list_is_empty():
    assert AudioInfo.get_audio_devices(CrashingCapture()) == []


def test_unexpected_error_in_the_system_default_still_returns_a_device():
    assert AudioInfo.get_default_audio_device(CrashingCapture()).name == "Error"
