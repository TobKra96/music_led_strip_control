# Research: pip-installable audio capture without system packages (ticket #221)

Date: 2026-10-23. Planning only, no project code changed. Scope: replace PyAudio in MLSC 3.0 on Raspberry Pi OS (Pi 4), Windows, WSL.

## Current state in this repo

- `setup.sh` installs `python3-pyaudio` via apt (comment: "Avoids needing to build from source"); `requirements.txt` has PyAudio commented out. PyPI PyAudio 0.2.14 ships wheels for Windows only plus an sdist ([PyPI JSON API](https://pypi.org/pypi/pyaudio/json)), so Linux needs apt or a PortAudio build.
- `server/libs/audio_process_service.py` uses: mono int16 input, a fixed `rate` and `frames_per_buffer` from config, `input_device_index`, and a push callback. Any replacement needs exactly that.
- `microphone_settings_executer.py` shells out to `/usr/bin/amixer -D hw:Device ... Mic` (ALSA mixer level, USB mic). This is independent of the capture library.

## Findings per backend

Wheel lists are from the PyPI JSON API (`https://pypi.org/pypi/<name>/json`, queried 2026-10-23).

| | sounddevice 0.5.6 | soundcard 0.4.6 | miniaudio 1.71 | PyAudio 0.2.14 |
|---|---|---|---|---|
| Wheels | `py3-none-any`, macOS, win32, win_amd64, win_arm64. **No Linux wheel** | one `py3-none-any` wheel | cp310-cp314 for Windows, macOS, manylinux **x86_64**, musllinux x86_64. **No aarch64/armv7 on PyPI** | Windows only |
| Pi wheels (piwheels) | pure-Python wheel only | not checked | **linux_armv6l/armv7l only**, cp39/cp311/cp313; no aarch64 ([piwheels](https://www.piwheels.org/project/miniaudio/)) | n/a |
| Native lib on Linux | PortAudio **not bundled**; install `libportaudio2` or similar ([install docs](https://python-sounddevice.readthedocs.io/en/0.5.6/installation.html)) | PulseAudio: libpulse loaded at import via cffi `dlopen('pulse')` ([source](https://github.com/bastibe/SoundCard/blob/master/soundcard/pulseaudio.py)); README: "you have to install PulseAudio first" ([README](https://raw.githubusercontent.com/bastibe/SoundCard/master/README.rst)) | Built from bundled C; miniaudio.h: "The Linux build only requires linking to -ldl, -lpthread and -lm" ([miniaudio.h](https://github.com/mackron/miniaudio/blob/master/miniaudio.h)). ALSA/PulseAudio/JACK backends are enumerated by `Backend` ([README](https://raw.githubusercontent.com/irmen/pyminiaudio/master/README.md)) | PortAudio via apt |
| Windows | PortAudio DLL bundled in wheel (ASIO optional) | WASAPI, no deps | wheel | wheel |
| WSL | needs `libportaudio2` plus a PulseAudio route | libpulse plus WSLg PulseAudio server | via ALSA/Pulse backends | apt |
| Device enumeration | `sd.query_devices()`, `python -m sounddevice` | `all_microphones()`, `get_microphone(name)` (substring/fuzzy) | `Devices().get_captures()` | existing |
| Select device / rate in code | `device=` index or name substring; `samplerate=` | `samplerate=` per recorder; device object | `CaptureDevice(device_id, sample_rate, nchannels, buffersize_msec)` | existing |
| Callback API | `InputStream(callback=...)`, int16 supported, `blocksize`, `latency` ('low'/'high'/seconds) ([docs](https://python-sounddevice.readthedocs.io/en/0.5.6/api/streams.html)) | pull style: `recorder(blocksize).record(numframes)`; no callback | generator-based `start(callback_generator)`, `buffersize_msec` default 200 | callback |
| Loopback | Not exposed. `WasapiSettings` has only `exclusive`, `auto_convert`, `explicit_sample_format` ([docs](https://python-sounddevice.readthedocs.io/en/0.5.6/api/platform-specific-settings.html), [source](https://github.com/spatialaudio/python-sounddevice/blob/0.5.6/src/sounddevice.py)) | Windows loopback added 2018 (README changelog); no usage in README | `is_loopback_supported(backend)`; miniaudio.h: loopback "(WASAPI only)" | no |

### Wheel availability on aarch64 / armv7 (the key question)

- No candidate gives a complete pip-only capture stack on 64-bit Raspberry Pi OS (aarch64, the default for Pi 4).
- sounddevice and soundcard install cleanly everywhere (pure Python plus cffi) but both `dlopen` a system library at runtime: libportaudio (sounddevice) or libpulse (soundcard).
- miniaudio is the only one with the audio engine in its own binary, but on aarch64 pip falls back to the sdist, which compiles C and needs a compiler, Python headers and cffi. On 32-bit Pi OS (armv7l) piwheels has cp311 and cp313 wheels; confirm they match the OS Python.
- Inference, not verified on a device: Pi OS normally has `libasound2`, and libpulse comes with the desktop audio stack; `libportaudio2` is the package most likely to be missing.

### System steps still required

- apt for sounddevice on Pi and WSL (`libportaudio2`). Avoidable only with miniaudio (which then needs a compile on aarch64).
- `asound.conf`: capture does not need it if the device is chosen by id/name in code (inference). The commented-out block in `setup.sh` forced the ALSA default card, which explicit selection replaces.
- `amixer`: mic gain is an ALSA mixer control that none of the libraries manage. miniaudio has `get_master_volume`/`set_master_volume` (per README; per-backend semantics undocumented). Keep `alsa-utils`/`amixer` on the Pi or give up gain control. Raspberry Pi docs mention `wpctl` and `pactl` for device profiles ([Raspberry Pi docs](https://www.raspberrypi.com/documentation/computers/configuration.html), partially read), which suggests PipeWire on current Pi OS.
- WSL: WSLg runs a PulseAudio server for mic in and speakers out and presets the user distro's `PULSE_SERVER` ([WSLg README](https://raw.githubusercontent.com/microsoft/wslg/main/README.md)). The ALSA `hw:Device` path used by the existing `amixer` call will not exist there, so Pulse-based access is required.

### Latency

No first-party latency figures for any of them. Knobs: sounddevice `blocksize`/`latency`; soundcard `blocksize`/`numframes` (README: 256-sample blocks, about 10 ms, usually work; on WASAPI it may ignore blocksize and record garbage when single-channel); miniaudio `buffersize_msec` (default 200, must be lowered for visualisation). All can meet MLSC's `frames_per_buffer` in principle; needs measurement on the Pi.

## Recommendation

1. Use **sounddevice** as the 3.0 default: closest API to the current PyAudio code (callback, int16, mono, device by index or name, fixed rate and blocksize), nothing but pip on Windows. Pi and WSL need one apt line (`libportaudio2`) instead of `python3-pyaudio`, `python3-dev`, `build-essential`.
2. **miniaudio** is the fallback if zero apt is a hard requirement. Needs build tools on aarch64, or 32-bit Pi OS.
3. **soundcard** only if Windows speaker (loopback) capture matters; on Pi it depends on Pulse/PipeWire and has no callback.
4. Put a small capture interface in front of the backend so the choice stays reversible.
5. Keep `amixer` for gain; orthogonal to the capture library.

## Open uncertainties

- Whether sounddevice's bundled Windows PortAudio supports WASAPI loopback: `PaWasapi_IsLoopback` exists in PortAudio master ([pa_win_wasapi.h](https://raw.githubusercontent.com/PortAudio/portaudio/master/include/pa_win_wasapi.h)), but sounddevice exposes no loopback option and the bundled DLL's version was not checked.
- miniaudio aarch64 sdist build prerequisites and time on a real Pi 4 (not tested).
- Whether Pi OS Lite has libpulse and libportaudio2 preinstalled; how `hw:Device` USB mics appear in each library's enumeration under PipeWire.
- Real capture latency and CPU on Pi 4 for each backend; soundcard Linux loopback behaviour.
- Pages were read through a summarising fetcher; Pi docs and miniaudio.h only partially. Statements marked "inference" are not sourced.
