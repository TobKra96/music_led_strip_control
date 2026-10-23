from types import SimpleNamespace

import pytest

from mlsc.audio_device import AudioDevice
from mlsc.audio_info import AudioInfo

pytestmark = pytest.mark.unit

DEVICES = [AudioDevice(0, "Built-in Mic", 44100), AudioDevice(3, "USB Mic", 48000)]


class FakePyAudio:
    @staticmethod
    def get_default_input_device_info():
        return {"index": 7, "name": "System Default", "defaultSampleRate": 48000}


def test_device_is_selected_by_name():
    selected = AudioInfo.select_audio_device(FakePyAudio(), DEVICES, "USB Mic")

    assert (selected.device_id, selected.name) == (3, "USB Mic")


@pytest.mark.parametrize("device_name", [None, "Unplugged Mic"])
def test_no_or_unknown_name_selects_the_system_default(device_name):
    selected = AudioInfo.select_audio_device(FakePyAudio(), DEVICES, device_name)

    assert (selected.device_id, selected.name) == (7, "System Default")


def test_unreadable_system_default_still_returns_a_device():
    py_audio = SimpleNamespace(get_default_input_device_info=lambda: (_ for _ in ()).throw(OSError("no audio")))

    selected = AudioInfo.select_audio_device(py_audio, [], None)

    assert selected.name == "Error"
