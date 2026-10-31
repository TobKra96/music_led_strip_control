# Release checklist

Work through this top to bottom for every release. The Pi steps need a person with hardware, so they are not in CI. A release candidate (`v3.0.0rc1`) goes through the same list and is published to PyPI as a pre-release (`pip install --pre`).

## 1. CI and version

- [ ] CI is green on the release commit (the publish workflow does not run the tests itself) (Linux and Windows, Python 3.11 and 3.13, JavaScript tests).
- [ ] `version` in `pyproject.toml` is the release version (for example `3.0.0rc1`). The publish workflow fails if it differs from the tag.
- [ ] The MQTT and UDP client protocols are unchanged (`client/` and the contract tests).

## 2. Rehearse on TestPyPI

- [ ] Run the **Publish** workflow by hand (Actions, Publish, Run workflow). It builds, smoke-installs the wheel and uploads to TestPyPI.
- [ ] On a clean machine: `uv tool install --index https://test.pypi.org/simple/ --index-strategy unsafe-best-match music-led-strip-control` (dependencies come from PyPI) and `mlsc --version`.

Trusted Publishing must be registered once on PyPI and TestPyPI: owner `TobKra96`, repository `music_led_strip_control`, workflow `publish.yml`, environments `pypi` and `testpypi`.

## 3. Pi hardware verification

Use a Pi 4 with a real strip and live audio capture. Install the build under test the way users do (`uv tool install "music-led-strip-control[pi]"`) and stop `mlsc.service` before the benchmark.

- [ ] `pytest -m hardware` passes on the Pi 4 (strandtest on a real strip).
- [ ] `mlsc doctor` reports no errors.
- [ ] **Loaded benchmark.** From a clone: `sudo python tools/loaded_benchmark.py --leds 60 300 900 --effect effect_wave --out loaded.json`. It runs the whole app with live audio, two open browser tabs (SSE and API polling) and reads the achieved fps per Output. Repeat on a Pi 3 and a Zero 2 W, which are still unmeasured. A `below target` verdict means the fps is under 90% of what the wire allows (about 25,600 divided by the LED count, capped at the Device fps). Only the Output service's frame rate counts. A non-zero `web_failures` in the JSON means the web load never reached the server (is auth on?), so rerun. `tools/loaded_benchmark.py` replaces the extended `profile_pipeline.py` of decision #237: that harness was throwaway and lives on `prototype/pi4-profiling`. Record the numbers in #268.
- [ ] **SSE meter under waitress.** Open the Microphone page with sound playing and the effect running at 900 LEDs. The meter moves smoothly and the strip fps in the benchmark does not drop. If the stream starves the effect loop, switch to Flask-Sock with gunicorn-gevent (decision #229).
- [ ] **Concurrent Hotspot and client mode.** `iw list` shows `#{ AP } <= 1, #{ managed } <= 1` under "valid interface combinations" on the Pi. Record the result for the deferred concurrent-mode work (decision #232).
- [ ] **nmcli option names.** On the shipped NetworkManager (`nmcli --version`), start and stop the Hotspot and connect to a network from the Wi-Fi panel. Fix any option name nmcli rejects in `NmcliWifiManager` and refresh the recorded nmcli output in the tests.
- [ ] **Discovery.** `avahi-daemon` is running and `http://mlsc.local:8080` opens from a phone on the same network, including after the Wi-Fi Rollback.

## 4. Decisions

- [ ] Compare the benchmark with the decisions it informs (#237 effect architecture and process model, #229 SSE under waitress, #232 Hotspot). Reopen a decision only if the numbers contradict it.

## 5. Publish

- [ ] Tag the release commit: `git tag v3.0.0rc1 && git push origin v3.0.0rc1`. The **Publish** workflow uploads to PyPI.
- [ ] On a clean Pi: `uv tool install "music-led-strip-control[pi]"` (add `--prerelease allow` for an rc), then `sudo mlsc service install`, and open the web UI.
- [ ] Write the GitHub release notes and mark rc tags as pre-release.
