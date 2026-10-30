import json
from pathlib import Path

import numpy as np
import pytest

from mlsc.effects.effect_power import EffectPower
from mlsc.effects.effect_vu_meter import EffectVuMeter

pytestmark = pytest.mark.unit

GOLDEN_CONFIG = Path(__file__).parent / "golden" / "config_v2_real_v4.json"


def make_config():
    config = json.loads(GOLDEN_CONFIG.read_text())

    return config, config["device_configs"]["device_0"]


@pytest.mark.parametrize("scale", [0.0, 1.0, 5.0, 1000.0, -3.0])
def test_power_clips_the_bass_bar_for_out_of_range_mel(scale):
    config, device_config = make_config()
    led_count = device_config["led_count"]
    effect = EffectPower(config, device_config)

    frame = effect.run({"mel": np.full(24, scale), "vol": 1.0})

    assert frame.shape == (3, led_count)
    assert np.isfinite(frame).all()


def test_power_survives_nan_mel():
    effect = EffectPower(*make_config())

    frame = effect.run({"mel": np.full(24, np.nan), "vol": 1.0})

    assert np.isfinite(frame).all()


def test_vu_meter_skips_nan_volume():
    effect = EffectVuMeter(*make_config())

    assert effect.run({"mel": None, "vol": np.nan}) is None


def test_vu_meter_handles_flat_volume_history():
    config, device_config = make_config()
    effect = EffectVuMeter(config, device_config)
    effect.vol_history = np.full(300, 0.5)

    frame = effect.run({"mel": None, "vol": 0.5})

    assert frame.shape == (3, device_config["led_count"])


def test_vu_meter_max_bar_does_not_wrap_below_zero():
    config, device_config = make_config()
    device_config["effects"]["effect_vu_meter"]["bar_length"] = 50
    effect = EffectVuMeter(config, device_config)
    effect.vol_history[:] = np.linspace(0, 1, 300)
    effect.max_vol = 0.01

    frame = effect.run({"mel": None, "vol": 0.0})

    max_vol_end = int(0.01 * device_config["led_count"])
    assert not frame[:, max_vol_end:].any()
