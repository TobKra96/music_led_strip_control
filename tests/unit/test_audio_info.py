import pytest

from mlsc.audio_capture.fake import FakeCapture
from mlsc.audio_device import AudioDevice
from mlsc.audio_info import AudioInfo

pytestmark = pytest.mark.unit

DEVICES = [AudioDevice(0, "Built-in Mic", 44100), AudioDevice(3, "USB Mic", 48000)]


class BrokenCapture(FakeCapture):
    def list_devices(self):
        raise OSError("no audio")

    def default_device(self):
        raise OSError("no audio")


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
