# Python and OS support on Raspberry Pi OS, including Pi 5 LED driver support

Research for ticket #220 (parent map #219, blocks #227). Planning only; no project code changed.
Researched 2026-10-23 from primary sources (vendor docs, upstream repos/issues, PyPI metadata). Each claim cites its source.

## Short answer

- Target Raspberry Pi OS **Trixie (Debian 13, Python 3.13)** and **Bookworm (Debian 12, Python 3.11)**, both with a **virtualenv** (PEP 668 blocks system-wide `pip`). Declare Python >= 3.11.
- **Pi 3, Pi 4, Zero 2 W**: keep `rpi_ws281x` (PWM/PCM/SPI). Pi 4 (the owner's board) is covered.
- **Pi 5**: `rpi_ws281x` 5.0.0 does not work. Needs a different backend; viable options are the Raspberry Pi kernel PIO driver (`ws2812-pio-rp1`), Adafruit's `Adafruit-Blinka-Raspberry-Pi5-Neopixel` (PIO via `/dev/pio0`), or the unmerged `rp1_ws281x_pwm` kernel module.
- Recommended: put LED output behind a small backend interface in 3.0; ship `rpi_ws281x` as default, add a Pi 5 backend as optional.

## 1. OS releases and Python versions

- Raspberry Pi OS is based on Debian; latest release is based on Debian Trixie, previous on Bookworm. Upgrading between them is recommended via a clean install, not in-place. Source: https://www.raspberrypi.com/documentation/computers/os.html
- Trixie-based Raspberry Pi OS was announced 2 October 2025 (Debian 13). Source: https://www.raspberrypi.com/news/trixie-the-new-version-of-raspberry-pi-os/
- Debian 13 ships Python 3.13; Debian 12 ships Python 3.11. Source: https://www.debian.org/releases/trixie/release-notes/whats-new.en.html (the page lists both).
- From Bookworm onward, `pip install` into the system Python fails with `externally-managed-environment` (PEP 668, a Python-community rule, not Raspberry Pi's). Options: `apt` `python3-*` packages, or `python3 -m venv`. Raspberry Pi does not recommend `--break-system-packages`. Source: Raspberry Pi OS docs above.
- Bullseye (Debian 11) is the only OS where the old global-pip installer worked, per the issue below. It is end-of-line and should not be a 3.0 target.

## 2. What blocked installation on Bookworm (issue #204)

Source: https://github.com/TobKra96/music_led_strip_control/issues/204
- Global `pip` installs rejected (`externally-managed-environment`), so `coloredlogs` / `pyaudio` were missing after install; mixing `apt` and `pip` packages was also a problem.
- Bookworm replaced `dhcpcd` with NetworkManager (Wi-Fi setup in the installer broke).
- Bookworm uses PipeWire instead of plain ALSA, which can affect microphone detection and audio effects.
- Some modules on `master` were too old for Python 3.11.
- Fix path: installer moved to a venv at `/share/venv`; maintainer said on 2026-02-02 that MLSC should now work on Bookworm and Trixie.
- Current `requirements.txt` on master already comments out PyAudio in favour of the apt package `python3-pyaudio` (0.2.13), pins `rpi_ws281x 5.0.0` on Linux, and uses `rpi-ws281x-mock` on Windows. Source: https://github.com/TobKra96/music_led_strip_control/blob/master/requirements.txt
- Implication: a venv must be able to see the apt-installed PyAudio (`--system-site-packages`) or PyAudio must be built from source (needs `portaudio19-dev`). Not verified here; test on hardware.

## 3. rpi_ws281x and the Pi models

- Upstream README documents PWM (GPIO 12/18/13/19...), PCM (GPIO 21) and SPI (GPIO 10) outputs; it names B+, 2B, Zero, 3B and, for SPI, Pi 3 and Pi 4 (Pi 3 needs `core_freq=250`; Pi 4 needs `core_freq=500` and `core_freq_min=500`). PWM conflicts with onboard analog audio; the SPI string must be the only device on the bus. Source: https://github.com/jgarff/rpi_ws281x
- PyPI: latest `rpi_ws281x` is 5.0.0 (2023-05-16), sdist only (no wheels), `requires_python >=3.6`. It compiles at install time (needs a compiler/swig toolchain). Source: https://pypi.org/project/rpi-ws281x/ and https://pypi.org/pypi/rpi-ws281x/json
- Pi 5: upstream issue #528 "Support for Raspberry Pi 5" is open. The maintainer found that adding the hardware ID is insufficient: mailbox memory allocation fails, and GPIO now goes through the RP1 chip so the SoC PWM no longer reaches the pins. Source: https://github.com/jgarff/rpi_ws281x/issues/528
- Related open items: #555 (new Pi 5 revision 0xd04171 rejected), #556/#557/#558 (open PRs: hwver, kernel-module fix, Compute Module 5), #554 (RP1 module build fails with non-16K page size). Source: https://github.com/jgarff/rpi_ws281x/issues?q=pi+5
- Models: Pi 3, Pi 4, Zero 2 W are the same BCM283x/2711 family and work with the existing library (the README covers Pi 3 and Pi 4 explicitly; Zero 2 W is not named in the README text I could read, so treat as expected-but-unverified). Pi 5 does not work.

## 4. Pi 5 alternatives and trade-offs

| Option | How it works | Pros | Cons / unknowns |
|---|---|---|---|
| Raspberry Pi kernel `ws2812-pio-rp1` | Official kernel driver using the RP1 PIO; configured with a device-tree overlay, e.g. `dtoverlay=ws2812-pio,gpio=18,num_leds=30,rgbw,brightness=0`. Source: https://github.com/raspberrypi/linux/issues/7108 | First-party; no userspace timing hacks. Gamma was hard-coded; fixed 2025-10-31 with a `brightness=0` pass-through mode (same issue). | Fixed LED count in the overlay; the userspace write interface was not shown in the sources read; needs a recent Pi kernel. Pi 5 only. |
| `Adafruit-Blinka-Raspberry-Pi5-Neopixel` | Python package that needs `/dev/pio0` (Pi 5 firmware with PIO support, recent kernel; udev rule for `gpio` group). GPL-2.0. Source: https://github.com/adafruit/Adafruit_Blinka_Raspberry_Pi5_Neopixel | Python API; wheels for cp311/cp312/cp313 on aarch64 and armv7l (1.0.0rc2, 2025-01-23, `requires_python >=3.11`). Source: https://pypi.org/pypi/Adafruit-Blinka-Raspberry-Pi5-Neopixel/json | Release candidate only; GPL-2.0 license implications for MLSC; frame-rate/latency for large strips unmeasured; more dependencies (Blinka). |
| `rp1_ws281x_pwm` kernel module + overlay (from jgarff) | Out-of-tree module making RP1 PWM drive WS281x; reported working by users. Source: https://github.com/jgarff/rpi_ws281x/issues/528 | Reuses `rpi_ws281x` API. | Not merged; kernel updates broke the build (Apr 2025); PRs open; fragile for end-user installs. |
| Adafruit `neopixel_spi` (SPI MOSI) | Generic SPI-driven NeoPixel driver. Source: https://github.com/adafruit/Adafruit_CircuitPython_NeoPixel_SPI | Same approach works on any Pi with SPI. | The README read does not state Pi 5 support or limits; needs SPI clock tuning (see core_freq notes above for older Pi). Unverified on Pi 5. |

Not found: the `rpi5-ws2812` repository named in the ticket (the URL guessed, github.com/ppcamp/rpi5-ws2812, returned 404). I could not confirm any project by that name from a primary source, so it is excluded.

## 5. Recommendation for 3.0

1. Supported OS: Raspberry Pi OS Bookworm and Trixie (64-bit preferred); drop Bullseye. Python >= 3.11 (3.13 on Trixie).
2. Installer: always a venv; keep apt for system pieces (PyAudio via `python3-pyaudio` or portaudio headers); no `--break-system-packages`. Document NetworkManager and PipeWire differences.
3. LED output: introduce a backend abstraction. Default `rpi_ws281x` (Pi 3/4/Zero 2 W). Add an optional Pi 5 backend; evaluate the kernel PIO driver and the Adafruit package on a Pi 5 before choosing. Mark Pi 5 as "experimental" in 3.0 unless tested.
4. Because the owner has only a Pi 4, Pi 5 support cannot be validated in-house; ship it behind a flag with community testing.

## 6. Open uncertainties

- Whether `rpi_ws281x` 5.0.0 builds cleanly under Python 3.13 on Trixie (sdist only; not tested here).
- Zero 2 W support is not stated in the README text read.
- Userspace interface and throughput (fps, max LEDs) of `ws2812-pio-rp1` and the Adafruit Pi 5 package; the driver source and docs were not directly readable, so details come from the linked kernel issue.
- Whether the venv can use apt PyAudio (`--system-site-packages`) in the current installer.
- Bookworm release date and exact Python on Pi OS images were not confirmed from a Raspberry Pi page; the Debian figures are used.
- Licence compatibility (GPL-2.0) of the Adafruit Pi 5 package with MLSC's licence.
