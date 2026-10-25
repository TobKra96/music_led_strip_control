# Debugging on Windows

MLSC runs natively on Windows 11 with the Mock Output, so you can develop and debug without WSL. WSL is only useful to exercise Linux-only paths (`fcntl` lock, `systemctl`, `amixer`, `nmcli`, real `rpi_ws281x`), and most of those need a Pi anyway.

## Setup

Use Python 3.13 or newer. Audio capture uses `sounddevice`, whose Windows wheel bundles PortAudio.

```powershell
py install 3.13
uv sync --python 3.13        # or: py -3.13 -m venv .venv; .venv\Scripts\python -m pip install -e . --group dev
```

`rpi-ws281x-mock` is installed automatically on Windows, so every strip uses the Mock Output.

## JavaScript tests

The browser JavaScript is tested with Vitest and jsdom. Node.js (current LTS) is a dev prerequisite; nothing in the app itself needs it.

```powershell
npm ci        # once, installs the dev tooling from package-lock.json
npm test      # vitest run; tests live in tests/js/<Module>.test.js
```

## Run

```powershell
.venv\Scripts\python -m mlsc run     # UI at http://localhost:8080
```

Use `--config-dir DIR` (or `MLSC_CONFIG_DIR`) to keep a throwaway config out of your user profile.

## Debug in VS Code

Open the repo in VS Code with the Python Debugger extension. `.vscode/launch.json` has two configurations:

- **MLSC: run** launches `mlsc run` under the debugger. `subProcess` is on, so breakpoints also hit in the webserver, audio and device manager child processes.
- **MLSC: attach (debugpy)** attaches to a server you started yourself:

  ```powershell
  .venv\Scripts\python -m debugpy --listen 5678 -m mlsc run
  ```

## Known limitations

- **Audio capture works on Windows.** Each process builds its own capture object (`mlsc.audio_capture.create_capture`), so no native audio handle crosses the spawn boundary.
- **Choosing the audio backend.** Set `MLSC_AUDIO_BACKEND` to `auto` (default), `sounddevice`, `miniaudio` or `fake` before `mlsc run`. The audio process and the web device list both use it. An unknown value stops startup with an `AudioCaptureError` and a log message.
- **Verified by hand on Windows 11 (2026-10-25)** with `MLSC_AUDIO_BACKEND=sounddevice`: the device list was non-empty (2 inputs, including `Mikrofon (Realtek(R) Audio)`), and a spawned child process opened the default device and received 20 of 20 buffers of 512 frames (1024 bytes each).
- Linux-only code (`fcntl` single-instance lock, `systemctl` check) is skipped on Windows.
- Port 8080 must be free. A leftover debug session holding it makes `/` answer with a 500 from another server; stop it or change `webserver_port` in the config.
