"""Golden-output (characterization) tests: every effect rendered from the fake capture's noise bursts through the real DSP.

Regenerate after an intended change with ``MLSC_UPDATE_GOLDEN=1 pytest tests/unit/test_effect_golden.py``.
"""
import json
import os
import random
from pathlib import Path

import numpy as np
import pytest

from mlsc.audio_capture import fake
from mlsc.audio_device import AudioDevice
from mlsc.color_service_global import ColorServiceGlobal
from mlsc.dsp import DSP
from mlsc.effect_service import AVAILABLE_EFFECTS

pytestmark = pytest.mark.unit

GOLDEN_DIR = Path(__file__).parent / "golden"
CONFIG = GOLDEN_DIR / "config_v2_real_v4.json"
GOLDEN = GOLDEN_DIR / "effects_v4.json"

FRAMES = 200
BURST_FRAMES = 30
FRAME_SECONDS = 1 / 60
CLOCK_START = 1_000.0


def dsp_frames(config, count):
    """Feed the DSP the way the audio process does and return the audio data of each buffer."""
    sample_rate = config["audio"]["sample_rate"]
    capture = fake.FakeCapture(fake.sine_sweep(100, 8000, seconds=1.0))
    capture.open(AudioDevice(0, "Fake Mic", sample_rate, "Fake API"), sample_rate, config["audio"]["frames_per_buffer"])
    dsp = DSP(config, sample_rate=sample_rate)
    frames = []
    for _ in range(count):
        capture.feed()
        samples = np.frombuffer(capture.read(0), dtype=np.int16).astype(np.float32)
        frames.append(dsp.update(samples))

    return frames


def pulsed_audio(config, count):
    """Scripted audio data with a beat every BURST_FRAMES, loud enough for the beat and frequency detection to fire."""
    bins = config["general_settings"]["n_fft_bins"]
    tilt = np.linspace(1.0, 0.4, bins)
    frames = []
    for index in range(count):
        level = 1.0 if index % BURST_FRAMES < BURST_FRAMES // 3 else 0.15
        wobble = 0.5 + 0.5 * np.sin(np.arange(bins) / 3 + index / 5)
        frames.append({"mel": level * tilt * (0.5 + 0.5 * wobble), "vol": level * 0.5})

    return frames


def render(effect_enum, monkeypatch):
    """Run one effect for FRAMES frames on a deterministic clock and seed; return the frames (None where skipped)."""
    config = json.loads(CONFIG.read_text())
    device_config = config["device_configs"]["device_0"]
    clock = [CLOCK_START]
    for module in ("mlsc.effects.effect", "mlsc.effects.effect_strobe", "mlsc.color_service_global"):
        monkeypatch.setattr(f"{module}.time", lambda: clock[0])
    random.seed(1234)
    np.random.seed(1234)  # ruff: ignore[numpy-legacy-random]
    effect = AVAILABLE_EFFECTS[effect_enum](config, device_config, ColorServiceGlobal(config))
    rendered = []
    for audio_data in pulsed_audio(config, FRAMES):
        clock[0] += FRAME_SECONDS
        rendered.append(effect.run(audio_data) if effect.needs_audio else effect.run())

    return rendered


def summarise(frames):
    shown = [np.asarray(frame, dtype=float) for frame in frames if frame is not None]
    last = shown[-1] if shown else None

    return {
        "frames": len(shown),
        "totals": [round(float(frame.sum()), 2) for frame in shown],
        "last": None if last is None else np.round(last).astype(int).tolist(),
    }


@pytest.mark.parametrize("effect_enum", list(AVAILABLE_EFFECTS), ids=lambda effect_enum: effect_enum.name)
def test_effect_output_matches_golden(effect_enum, monkeypatch):
    actual = summarise(render(effect_enum, monkeypatch))

    if os.environ.get("MLSC_UPDATE_GOLDEN"):
        golden = json.loads(GOLDEN.read_text()) if GOLDEN.exists() else {}
        golden[effect_enum.name] = actual
        GOLDEN.write_text(json.dumps(dict(sorted(golden.items())), separators=(",", ":")) + "\n")
        return

    expected = json.loads(GOLDEN.read_text())[effect_enum.name]
    assert actual["frames"] == expected["frames"]
    np.testing.assert_allclose(actual["totals"], expected["totals"], rtol=1e-4, atol=1.0)
    np.testing.assert_allclose(actual["last"], expected["last"], atol=1)


def test_dsp_output_matches_golden():
    config = json.loads(CONFIG.read_text())
    frames = dsp_frames(config, 60)
    actual = {
        "vol": [round(float(frame["vol"]), 4) for frame in frames],
        "mel": [np.round(frame["mel"], 3).tolist() for frame in frames[::10]],
    }
    golden_file = GOLDEN_DIR / "dsp_v4.json"

    if os.environ.get("MLSC_UPDATE_GOLDEN"):
        golden_file.write_text(json.dumps(actual, separators=(",", ":")) + "\n")
        return

    expected = json.loads(golden_file.read_text())
    np.testing.assert_allclose(actual["vol"], expected["vol"], atol=1e-3)
    np.testing.assert_allclose(actual["mel"], expected["mel"], atol=1e-2)
