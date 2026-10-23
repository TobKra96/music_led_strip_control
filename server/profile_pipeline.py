"""Throwaway profiling harness for ticket #225 (profile effect rendering on the Pi 4).

Do not commit or ship. Measures each stage of the frame pipeline in isolation, using the
real MLSC code with fake queues, so the numbers show where the time per frame goes:

  1. dsp      DSP.update() on synthetic audio (runs in the audio process)
  2. effects  Effect.run() for every effect (runs in the effect process)
  3. output   OutputRaspi.show() split into numpy prep, ws2811_led_set loop and render
  4. queue    multiprocessing.Queue round trip of an audio dict and a frame

Run from the server directory, as root for the output stage (stop mlsc.service first):

    sudo /share/.venv/bin/python profile_pipeline.py --leds 60 300 900 --out results.json
"""
import argparse
import copy
import importlib
import inspect
import json
import pickle
import platform
import statistics
import subprocess
import sys
from multiprocessing import Process, Queue
from pathlib import Path
from time import perf_counter, perf_counter_ns

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from libs.dsp import DSP  # noqa: E402
from libs.effects.effect import Effect  # noqa: E402

LIBS = Path(__file__).resolve().parent / "libs"
WS_NS_PER_LED = 30_000  # 24 bits at 800 kHz


class FakeQueue:
    """Stands in for QueueWrapper. Audio side always has data, output side keeps the last frame."""

    def __init__(self, items=None):
        self._items = items
        self._i = 0
        self.last = None

    def empty(self):
        return self._items is None

    def get_blocking(self):
        item = self._items[self._i % len(self._items)]
        self._i += 1
        return item

    def put_blocking(self, element):
        self.last = element

    put_none_blocking = put_blocking


class FakeDevice:
    def __init__(self, config, device_config, audio_items):
        self.config = config
        self.device_config = device_config
        self.audio_queue = FakeQueue(audio_items)
        self.output_queue = FakeQueue()
        self.effect_queue = FakeQueue()
        self.device_notification_queue_in = FakeQueue()
        self.device_notification_queue_out = FakeQueue()
        from libs.color_service_global import ColorServiceGlobal  # noqa: PLC0415
        self.color_service_global = ColorServiceGlobal(config)


def load_config(led_count, led_strip, fps):
    config = json.loads((LIBS / "config_template.json").read_text())
    device_config = copy.deepcopy(config["default_device"])
    device_config["led_count"] = led_count
    device_config["led_mid"] = led_count // 2
    device_config["led_strip"] = led_strip
    device_config["fps"] = fps
    config["device_configs"] = {"0": device_config}
    return config, device_config


def stats(samples_ns):
    ms = sorted(s / 1e6 for s in samples_ns)
    mean = statistics.fmean(ms)
    return {
        "mean_ms": round(mean, 3),
        "p95_ms": round(ms[int(len(ms) * 0.95) - 1], 3),
        "max_ms": round(ms[-1], 3),
        "max_fps": round(1000 / mean, 1) if mean else None,
    }


def time_calls(fn, iterations, warmup):
    for _ in range(warmup):
        fn()
    samples = []
    for _ in range(iterations):
        t = perf_counter_ns()
        fn()
        samples.append(perf_counter_ns() - t)
    return stats(samples)


def synthetic_audio(frames, frames_per_buffer, sample_rate):
    """Tones that change over time plus noise, as int16 frames cast to float32 like the audio service does."""
    rng = np.random.default_rng(1)
    t = np.arange(frames * frames_per_buffer) / sample_rate
    freqs = [110, 440, 1760, 5000]
    y = sum(np.sin(2 * np.pi * f * t) * (0.5 + 0.5 * np.sin(2 * np.pi * (0.5 + i) * t)) for i, f in enumerate(freqs))
    y = y / len(freqs) + rng.normal(0, 0.05, t.size)
    y = (np.clip(y, -1, 1) * 2**14).astype(np.int16).astype(np.float32)
    return [y[i * frames_per_buffer:(i + 1) * frames_per_buffer] for i in range(frames)]


def profile_dsp(config, iterations, warmup):
    gs = config["general_settings"]
    chunks = synthetic_audio(iterations + warmup, gs["frames_per_buffer"], gs["default_sample_rate"])
    dsp = DSP(config)
    it = iter(chunks)
    result = time_calls(lambda: dsp.update(next(it)), iterations, warmup)
    # Produce audio dicts for the effect stage with a fresh DSP.
    dsp = DSP(config)
    audio = [dsp.update(c) for c in chunks[:200]]
    return result, audio


def discover_effects():
    found = {}
    for path in sorted((LIBS / "effects").glob("effect_*.py")):
        module = importlib.import_module(f"libs.effects.{path.stem}")
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls, Effect) and cls is not Effect and cls.__module__ == module.__name__:
                found[path.stem] = cls
    return found


def profile_effects(config, device_config, audio, only, iterations, warmup):
    results = {}
    for name, cls in discover_effects().items():
        if only and name not in only:
            continue
        try:
            device = FakeDevice(config, device_config, audio)
            effect = cls(device)
            results[name] = time_calls(effect.run, iterations, warmup)
            results[name]["_last_frame"] = device.output_queue.last
        except Exception as e:  # noqa: BLE001
            results[name] = {"error": f"{type(e).__name__}: {e}"}
    return results


def profile_output(config, device_config, frame, iterations, warmup):
    """Time OutputRaspi.show() and its parts. Needs root and a connected (or at least powered-off) strip."""
    from libs.outputs.output_raspi import OutputRaspi  # noqa: PLC0415
    import _rpi_ws281x as ws  # noqa: PLC0415

    device = FakeDevice(config, device_config, None)
    out = OutputRaspi(device)
    n = device_config["led_count"]

    result = {"show_total": time_calls(lambda: out.show(frame), iterations, warmup)}

    def prep():
        a = frame.clip(0, 255).astype(int)
        g = np.left_shift(a[1][:].astype(int), 16)
        r = np.left_shift(a[0][:].astype(int), 8)
        b = a[2][:].astype(int)
        return np.bitwise_or(np.bitwise_or(r, g), b).astype(int)

    result["numpy_prep"] = time_calls(prep, iterations, warmup)
    grb = prep()

    def led_set():
        for i in range(n):
            ws.ws2811_led_set(out.channel, i, grb[i].item())

    result["led_set_loop"] = time_calls(led_set, iterations, warmup)
    result["ws2811_render"] = time_calls(lambda: ws.ws2811_render(out._leds), iterations, warmup)  # noqa: SLF001
    result["wire_time_floor_ms"] = round(n * WS_NS_PER_LED / 1e6 + 0.3, 3)
    ws.ws2811_fini(out._leds)  # noqa: SLF001
    return result


def _echo(q_in, q_out):
    while True:
        item = q_in.get()
        if item is None:
            return
        q_out.put(item)


def profile_queue(audio, frame, iterations):
    q_in, q_out = Queue(2), Queue(2)
    proc = Process(target=_echo, args=(q_in, q_out))
    proc.start()
    result = {}
    for label, payload in (("audio_dict", audio[0]), ("frame", frame)):
        for _ in range(20):
            q_in.put(payload)
            q_out.get()
        samples = []
        for _ in range(iterations):
            t = perf_counter_ns()
            q_in.put(payload)
            q_out.get()
            samples.append(perf_counter_ns() - t)
        result[label] = {
            "roundtrip": stats(samples),
            "payload_bytes": len(pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL)),
        }
        t = perf_counter()
        for _ in range(iterations):
            pickle.loads(pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL))  # noqa: S301
        result[label]["pickle_roundtrip_ms"] = round((perf_counter() - t) / iterations * 1000, 3)
    q_in.put(None)
    proc.join()
    return result


def system_info():
    def run(*cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=5, check=False).stdout.strip()
        except Exception:  # noqa: BLE001
            return None

    temp = None
    try:
        temp = int(Path("/sys/class/thermal/thermal_zone0/temp").read_text()) / 1000
    except OSError:
        pass
    model_file = Path("/proc/device-tree/model")
    return {
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "model": model_file.read_bytes().decode(errors="ignore").strip("\x00") if model_file.exists() else None,
        "temp_c": temp,
        "throttled": run("vcgencmd", "get_throttled"),
        "arm_clock": run("vcgencmd", "measure_clock", "arm"),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--leds", type=int, nargs="+", default=[60, 300, 900])
    p.add_argument("--strip", default="ws2811_strip_rgb", help="led_strip value for the output stage")
    p.add_argument("--fps", type=int, default=60)
    p.add_argument("--iterations", type=int, default=300)
    p.add_argument("--warmup", type=int, default=30)
    p.add_argument("--effects", nargs="*", help="only these effects, e.g. effect_energy effect_wave")
    p.add_argument("--no-output", action="store_true", help="skip the real GPIO output stage")
    p.add_argument("--out", default="profile_results.json")
    args = p.parse_args()

    report = {"system_start": system_info(), "args": vars(args), "runs": {}}
    for n in args.leds:
        print(f"\n=== {n} LEDs ===", flush=True)
        config, device_config = load_config(n, args.strip, args.fps)
        run = {}

        run["dsp"], audio = profile_dsp(config, args.iterations, args.warmup)
        print(f"dsp: {run['dsp']}", flush=True)

        run["effects"] = profile_effects(config, device_config, audio, args.effects, args.iterations, args.warmup)
        frame = next((r["_last_frame"] for r in run["effects"].values() if r.get("_last_frame") is not None), None)
        if frame is None:
            frame = np.random.default_rng(2).integers(0, 255, (3, n)).astype(np.float64)
        for name, r in run["effects"].items():
            print(f"{name:28s} " + (r.get("error") or f"mean {r['mean_ms']:7.3f} ms  p95 {r['p95_ms']:7.3f}  max {r['max_ms']:7.3f}  -> {r['max_fps']} fps"), flush=True)
            r.pop("_last_frame", None)

        if not args.no_output:
            try:
                run["output"] = profile_output(config, device_config, frame, args.iterations, args.warmup)
                print(f"output: {json.dumps(run['output'], indent=1)}", flush=True)
            except Exception as e:  # noqa: BLE001
                run["output"] = {"error": f"{type(e).__name__}: {e}"}
                print(f"output stage failed: {run['output']['error']}", flush=True)

        run["queue"] = profile_queue(audio, frame, min(args.iterations, 300))
        print(f"queue: {json.dumps(run['queue'], indent=1)}", flush=True)
        report["runs"][str(n)] = run

    report["system_end"] = system_info()
    Path(args.out).write_text(json.dumps(report, indent=1))
    print(f"\nWrote {args.out}\nstart: {report['system_start']}\nend:   {report['system_end']}")


if __name__ == "__main__":
    main()
