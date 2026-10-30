import json
from pathlib import Path

import numpy as np
import pytest

from mlsc.effects.effect_power import EffectPower
from mlsc.effects.effect_vu_meter import EffectVuMeter

pytestmark = pytest.mark.unit

GOLDEN_CONFIG = Path(__file__).parent / "golden" / "config_v2_real_v4.json"


class FakeQueue:
    def __init__(self, items=()) -> None:
        self.items = list(items)

    def empty(self):
        return not self.items

    def get_blocking(self):
        return self.items.pop(0)

    def put_none_blocking(self, item):
        self.items.append(item)


class FakeEffectDevice:
    def __init__(self, config, device_config, audio) -> None:
        self.config = config
        self.device_config = device_config
        self.audio_queue = FakeQueue([audio])
        self.output_queue = FakeQueue()


def make_device(audio):
    config = json.loads(GOLDEN_CONFIG.read_text())
    device_config = config["device_configs"]["device_0"]

    return FakeEffectDevice(config, device_config, audio)


@pytest.mark.parametrize("scale", [0.0, 1.0, 5.0, 1000.0, -3.0])
def test_power_clips_the_bass_bar_for_out_of_range_mel(scale):
    device = make_device({"mel": np.full(24, scale), "vol": 1.0})
    led_count = device.device_config["led_count"]
    effect = EffectPower(device)

    effect.run()

    frame = device.output_queue.items[0]
    assert frame.shape == (3, led_count)


def test_power_survives_nan_mel():
    device = make_device({"mel": np.full(24, np.nan), "vol": 1.0})
    effect = EffectPower(device)

    effect.run()

    assert len(device.output_queue.items) == 1


def test_vu_meter_handles_flat_volume_history():
    device = make_device({"mel": None, "vol": 0.5})
    effect = EffectVuMeter(device)
    effect.vol_history = np.full(300, 0.5)

    effect.run()

    assert device.output_queue.items[0].shape == (3, device.device_config["led_count"])


def test_vu_meter_max_bar_does_not_wrap_below_zero():
    device = make_device({"mel": None, "vol": 0.0})
    device.device_config["effects"]["effect_vu_meter"]["bar_length"] = 50
    effect = EffectVuMeter(device)
    effect.vol_history[:] = np.linspace(0, 1, 300)
    effect.max_vol = 0.01

    effect.run()

    assert not device.output_queue.items[0][:, -10:].any()
