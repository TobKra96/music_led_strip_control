import importlib.util
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_PATH = Path(__file__).resolve().parents[2] / "tools" / "loaded_benchmark.py"
_spec = importlib.util.spec_from_file_location("loaded_benchmark", _PATH)
bench = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bench)


def test_parse_fps_reads_the_output_service_log_lines():
    log = (
        "2026-01-01 | INFO | mlsc.output_service:output_routine:109 - FPS: 59.80 | Device: Strip A\n"
        "noise\n"
        "2026-01-01 | INFO | mlsc.output_service:output_routine:109 - FPS: 27.50 | Device: Strip B\n"
        "2026-01-01 | INFO | mlsc.output_service:output_routine:109 - FPS: 60.10 | Device: Strip A\n"
    )

    assert bench.parse_fps(log.splitlines()) == {"Strip A": [59.8, 60.1], "Strip B": [27.5]}


def test_summarise_reports_mean_min_and_sample_count():
    assert bench.summarise([60.0, 58.0, 62.0]) == {"samples": 3, "mean": 60.0, "min": 58.0}


def test_summarise_without_samples_is_empty():
    assert bench.summarise([]) == {"samples": 0, "mean": None, "min": None}


@pytest.mark.parametrize(("mean", "verdict"), [(59.0, "ok"), (40.0, "below target"), (None, "no data")])
def test_verdict_compares_the_mean_with_the_expected_fps(mean, verdict):
    assert bench.verdict(mean, 60) == verdict


def test_expected_max_fps_follows_the_wire_limit():
    assert bench.expected_max_fps(900) == pytest.approx(28.4, abs=0.1)
    assert bench.expected_max_fps(60) == 60  # capped by the target, not the wire


def test_report_is_json_serialisable():
    report = bench.build_report({"A": [60.0]}, leds=60, target_fps=60, duration=30, system={"model": "x"}, clients=2)

    assert json.loads(json.dumps(report))["devices"]["A"]["verdict"] == "ok"


def test_seed_config_writes_one_device_with_the_requested_effect(tmp_path):
    bench.seed_config(tmp_path, leds=300, fps=60, output="output_dummy", effect="effect_wave")

    device = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))["device_configs"]["0"]
    assert (device["led_count"], device["output_type"], device["effects"]["last_effect"]) == (300, "output_dummy", "effect_wave")


def test_parse_fps_ignores_loguru_colour_codes():
    line = "\x1b[36mmlsc.output_service\x1b[0m:output_routine:109 - \x1b[1mFPS: 59.80 | Device: Strip A\x1b[0m"

    assert bench.parse_fps([line]) == {"Strip A": [59.8]}


def test_parse_fps_skips_the_effect_service_lines():
    lines = [
        "x | mlsc.effect_service:effect_routine:172 - FPS: 61.00 | Device: Strip A",
        "x | mlsc.output_service:output_routine:109 - FPS: 28.00 | Device: Strip A",
    ]

    assert bench.parse_fps(lines) == {"Strip A": [28.0]}
