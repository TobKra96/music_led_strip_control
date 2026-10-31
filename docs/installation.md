# Installing MLSC on Raspberry Pi OS

MLSC 3.x runs on Raspberry Pi OS **Bookworm** (Debian 12, Python 3.11) and **Trixie** (Debian 13, Python 3.13), always inside a virtual environment. Both `uv tool` and `pipx` create one for you. Bullseye is no longer supported (this also closes [#204](https://github.com/TobKra96/music_led_strip_control/issues/204)).

Pi 3, Pi 4 and Zero 2 W drive WS281x strips through `rpi_ws281x`. The Pi 5 is [experimental](#raspberry-pi-5-experimental).

## Install

```bash
sudo apt install libportaudio2 build-essential python3-dev
curl -LsSf https://astral.sh/uv/install.sh | sh          # or: sudo apt install pipx
uv tool install "music-led-strip-control[pi]"            # or: pipx install "music-led-strip-control[pi]"
sudo "$(command -v mlsc)" service install
```

`mlsc service install` writes `/etc/systemd/system/mlsc.service`, enables it and starts it. The web UI is then on `http://<hostname>.local:8080`.

`setup.sh` does the same steps in one go: `curl -sSL https://raw.githubusercontent.com/TobKra96/music_led_strip_control/master/setup.sh | bash`.

### The service

| Command | What it does |
| --- | --- |
| `sudo mlsc service install` | Writes the unit, enables and (re)starts it. An existing `mlsc.service`, such as the one from 2.x, is replaced. |
| `sudo mlsc service uninstall` | Stops and removes the unit. The config is kept. |
| `mlsc service status` | Shows `systemctl status`. |
| `sudo mlsc service restart` | Restarts the service. |

The service runs as `root` in 3.0 because `rpi_ws281x` needs `/dev/mem`. It is hardened with `ProtectHome=read-only`, `NoNewPrivileges=true` and only the config directory as `ReadWritePaths`. The unit pins the config directory of the user who ran the install (also through `sudo`), or the one given with `--config-dir` / `MLSC_CONFIG_DIR`. Check where it is with `mlsc config path`.

## Upgrading

**Within 3.x:**

```bash
uv tool upgrade music-led-strip-control     # or: pipx upgrade music-led-strip-control
sudo mlsc service restart
```

**From 2.x:**

1. Install 3.x as above, but do not start it yet if you want to review the config: `uv tool install ...`.
2. Run `mlsc config migrate` (add `--dry-run` to preview). It reads `./.mlsc` or `/share/.mlsc`, or the path from `--from PATH`, and writes to the new config directory.
3. Run `sudo mlsc service install`. This replaces the old 2.x `mlsc.service`.

The 2.x clone, its virtual environment and its config are never deleted or modified, so you can go back by reinstalling the old unit.

## Raspberry Pi 5 (experimental)

`rpi_ws281x` does not support the Pi 5, because GPIO goes through the RP1 chip ([upstream issue](https://github.com/jgarff/rpi_ws281x/issues/528)). There is no supported GPIO Backend for it yet. The candidates, which need community testing, are:

- the Raspberry Pi kernel `ws2812-pio-rp1` overlay,
- `Adafruit-Blinka-Raspberry-Pi5-Neopixel` (PIO, RC only, GPL-2.0),
- the unmerged `rp1_ws281x_pwm` kernel module.

`adafruit neopixel_spi` is unverified on the Pi 5. Until a backend lands, use a Pi 5 with a UDP client or the Mock Output. Details: [research notes](https://github.com/TobKra96/music_led_strip_control/blob/research/pi-os-python-support/docs/research/pi-os-python-support.md).
