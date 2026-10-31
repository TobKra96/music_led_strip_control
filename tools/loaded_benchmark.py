"""Loaded end-to-end benchmark for the release checklist (#268, decision #237).

Starts the whole app (audio, DeviceManager, effect and output processes, web server) with a throwaway config,
puts web load on it (SSE streams and API polling, like open browser tabs) and reads the achieved frame rate
of each Output from the app's own `FPS:` log lines. Run it on the Pi with live audio capture and a real strip:

    sudo python tools/loaded_benchmark.py --leds 60 300 900 --effect effect_wave --out results.json

Stop `mlsc.service` first. Use `--output output_dummy` to rehearse without a strip. Standard library only.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import platform
import re
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

WIRE_US_PER_LED = 39  # Measured on a Pi 4 (#225), about 25,600 divided by the LED count.
# The effect service logs the same FPS line; only the Output rate is the strip frame rate.
OUTPUT_LOGGER = "mlsc.output_service"
ANSI = re.compile(r"\x1b\[[\d;]*m")
FPS_LINE = re.compile(r"FPS: (?P<fps>[\d.]+) \| Device: (?P<device>.+?)\s*$")
ROOT = Path(__file__).resolve().parents[1]
LOG_INTERVAL_S = 10  # OutputService logs its FPS this often.


def parse_fps(lines) -> dict[str, list[float]]:
    result: dict[str, list[float]] = {}
    for line in lines:
        text = ANSI.sub("", line)
        if OUTPUT_LOGGER in text and (match := FPS_LINE.search(text)):
            result.setdefault(match["device"], []).append(float(match["fps"]))
    return result


def summarise(samples: list[float]) -> dict:
    if not samples:
        return {"samples": 0, "mean": None, "min": None}
    return {"samples": len(samples), "mean": round(statistics.fmean(samples), 2), "min": min(samples)}


def expected_max_fps(leds: int, target_fps: int = 60) -> float:
    # Frame rate the wire allows for `leds` LEDs, capped at the target.
    return min(target_fps, 1_000_000 / (leds * WIRE_US_PER_LED))


def verdict(mean: float | None, expected: float) -> str:
    if mean is None:
        return "no data"
    return "ok" if mean >= expected * 0.9 else "below target"


def build_report(fps: dict[str, list[float]], *, leds: int, target_fps: int, duration: int, system: dict, clients: int) -> dict:
    expected = expected_max_fps(leds, target_fps)
    devices = {}
    for name, samples in fps.items():
        summary = summarise(samples)
        devices[name] = {**summary, "verdict": verdict(summary["mean"], expected)}
    return {
        "leds": leds, "target_fps": target_fps, "expected_fps": round(expected, 1), "duration_s": duration,
        "web_clients": clients, "system": system, "devices": devices,
    }


def system_info() -> dict:
    def run(*cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=5, check=False).stdout.strip()
        except Exception:
            return None

    model = Path("/proc/device-tree/model")
    temp = None
    with contextlib.suppress(OSError, ValueError):
        temp = int(Path("/sys/class/thermal/thermal_zone0/temp").read_text(encoding="utf-8")) / 1000
    return {
        "platform": platform.platform(), "python": sys.version.split()[0], "temp_c": temp,
        "model": model.read_bytes().decode(errors="ignore").strip("\x00") if model.exists() else None,
        "throttled": run("vcgencmd", "get_throttled"),
    }


def seed_config(config_dir: Path, *, leds: int, fps: int, output: str, effect: str) -> None:
    config = json.loads((ROOT / "src" / "mlsc" / "config_template.json").read_text(encoding="utf-8"))
    device = config["default_device"]
    device.update(led_count=leds, led_mid=leds // 2, fps=fps, output_type=output)
    device["effects"]["last_effect"] = effect
    config["device_configs"] = {"0": device}
    (config_dir / "config.json").write_text(json.dumps(config), encoding="utf-8")


def web_port(config_dir: Path) -> int:
    return json.loads((config_dir / "config.json").read_text(encoding="utf-8"))["general_settings"]["webserver_port"]


web_failures: list[str] = []  # One entry per failed request, so a load that never reached the server is visible.


def _poll(url: str, stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            urllib.request.urlopen(url, timeout=5).read()  # ruff: ignore[suspicious-url-open-usage]
        except OSError:
            web_failures.append(url)
        stop.wait(1)


def _stream(url: str, stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            response = urllib.request.urlopen(url, timeout=5)  # ruff: ignore[suspicious-url-open-usage]
            while not stop.is_set() and response.readline():
                pass
        except OSError:
            web_failures.append(url)
        stop.wait(1)


def start_web_load(port: int, clients: int, stop: threading.Event) -> None:
    base = f"http://127.0.0.1:{port}"
    for _ in range(clients):
        threading.Thread(target=_stream, args=(f"{base}/api/v2/events", stop), daemon=True).start()
        threading.Thread(target=_poll, args=(f"{base}/api/v2/system/performance", stop), daemon=True).start()


def run_once(args, leds: int) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        config_dir = Path(tmp)
        seed_config(config_dir, leds=leds, fps=args.fps, output=args.output, effect=args.effect)
        env = {**os.environ, "MLSC_CONFIG_DIR": str(config_dir), "PYTHONUNBUFFERED": "1"}
        proc = subprocess.Popen([sys.executable, "-m", "mlsc", "run"], cwd=ROOT, env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        lines: list[str] = []
        threading.Thread(target=lambda: lines.extend(proc.stdout), daemon=True).start()
        stop = threading.Event()
        try:
            time.sleep(args.warmup)
            start_web_load(web_port(config_dir), args.clients, stop)
            mark = len(lines)
            time.sleep(args.duration)
            fps = parse_fps(lines[mark:])
            system = system_info()
        finally:
            stop.set()
            proc.terminate()
            try:
                proc.wait(15)
            except subprocess.TimeoutExpired:
                proc.kill()
    report = build_report(fps, leds=leds, target_fps=args.fps, duration=args.duration, system=system, clients=args.clients)
    report["web_failures"] = len(web_failures)  # Many failures mean the load did not reach the server (is auth on?).
    web_failures.clear()
    return report


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--leds", type=int, nargs="+", default=[60, 300, 900])
    p.add_argument("--fps", type=int, default=60)
    p.add_argument("--output", default="output_raspi", help="output_raspi, output_udp or output_dummy (the Mock Output)")
    p.add_argument("--effect", default="effect_energy")
    p.add_argument("--clients", type=int, default=2, help="browser tabs: one SSE stream and one API poller each")
    p.add_argument("--warmup", type=int, default=20, help="seconds before measuring")
    p.add_argument("--duration", type=int, default=60, help="seconds measured per LED count")
    p.add_argument("--out", default="loaded_benchmark.json")
    args = p.parse_args(argv)
    if args.duration < 2 * LOG_INTERVAL_S:
        p.error(f"--duration must be at least {2 * LOG_INTERVAL_S} seconds, the app logs its FPS every {LOG_INTERVAL_S}.")

    runs = []
    for leds in args.leds:
        print(f"=== {leds} LEDs ===", flush=True)  # ruff: ignore[print]
        runs.append(run_once(args, leds))
        print(json.dumps(runs[-1]["devices"], indent=1), flush=True)  # ruff: ignore[print]
    Path(args.out).write_text(json.dumps(runs, indent=1), encoding="utf-8")
    print(f"Wrote {args.out}")  # ruff: ignore[print]
    return 0


if __name__ == "__main__":
    sys.exit(main())
