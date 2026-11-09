# Fewest-step pip-style install on Raspberry Pi OS Bookworm and Trixie

Research for issue #348 (child of map #346). Researched 2026-11-09 from primary sources only (PyPI JSON API, piwheels JSON API and FAQ, PEP 668, Raspberry Pi docs, pi-gen, Debian package pages, uv docs, upstream source). Where a conclusion is my inference rather than a stated fact, it is marked **Inference**. Nothing here was run on a Pi.

## Summary

- Plain `pip install` does not work on Bookworm or Trixie. PEP 668 makes pip refuse system-wide installs; a venv, pipx or uv tool is required. [1][2]
- The current `setup.sh` approach (apt, then uv, then `uv tool install`) is consistent with that. The apt step cannot be folded into a `pip install`; only a script can do it, and `setup.sh` already does.
- `rpi_ws281x` has **no wheel on PyPI** (sdist only). piwheels has armv6l/armv7l wheels (32-bit OS only, Python 3.11 and 3.13). **No aarch64 wheel exists anywhere**, so on 64-bit Pi OS it always compiles and needs a C compiler plus Python headers. `build-essential` and `python3-dev` therefore cannot be dropped. [3][4][10]
- numpy and scipy have PyPI aarch64 wheels for both Python 3.11 and 3.13. On armv7l they exist only on piwheels, and are linked to system libraries (`libopenblas0-pthread`, `libgfortran5`). [6][4]
- `libportaudio2` is the only runtime apt package MLSC itself needs (PyPI `sounddevice` ships no Linux binary). [7]
- Cold install time and size on a Zero 2 W vs a Pi 4: no primary source documents this. Only wheel sizes are known.

## 1. Does plain `pip install` work?

No.

- PEP 668: when an `EXTERNALLY-MANAGED` file exists in the stdlib dir and pip runs outside a virtual environment, pip must exit with an error. `--break-system-packages` overrides it and is meant to be risky. [1]
- Raspberry Pi docs: "From Raspberry Pi OS Bookworm onwards, you cannot install libraries directly into the system version of Python." They point to a virtual environment (`python -m venv`) or `apt`, and do not recommend the override. The change came from the Python community, not Raspberry Pi. [2] The page says Bookworm onwards, which covers Trixie; it says nothing Trixie-specific.
- Python versions: Bookworm ships Python 3.11.2, Trixie 3.13.5 (Debian package pages). [8] piwheels also states Bookworm uses 3.11 and Trixie 3.13. [4]

### What a fresh Pi OS Lite image ships

From the pi-gen stage package lists (the tool that builds the official images; `stage2` is Lite), branches `master` and `bookworm`: [9]

| Item | In the Lite package lists? |
|---|---|
| `curl`, `ca-certificates` | yes |
| `build-essential` | yes (so gcc and make are present) |
| `python3-venv` | yes |
| `python3` | not listed explicitly (a dependency of listed packages; chain not verified) |
| `python3-pip`, `pipx`, `python3-dev`, `git` | not in the stage0-2 `00-packages` lists |

**Inference**: `pip` is not available as a command on Lite out of the box, and `git` and `python3-dev` are missing. This only reads the explicit lists, not a built image; transitive dependencies were not checked. `python3-pip`, `pipx` and `python3-dev` all exist in both Debian releases (pip 23.0.1 / 25.1.1, pipx 1.1.0 / 1.7.1). [8]

## 2. `rpi_ws281x` wheels

- PyPI `rpi-ws281x` 5.0.0 (the latest release, 2023-05-16): the only file is `rpi_ws281x-5.0.0.tar.gz` (sdist, about 64 KB). No wheels for any platform. [3]
- Upstream `setup.py` builds a C extension from `lib/*.c`, so the sdist needs a compiler and `Python.h`. [10]
- piwheels has 5.0.0 wheels tagged `linux_armv6l` and `linux_armv7l` for cp37, cp39, cp311, cp313. [4]
- piwheels FAQ: wheels are armv6l/armv7l; it "does not currently support the 64-bit version of the Raspberry Pi OS". [4]

| Target | Wheel? | Needs build-essential + python3-dev? |
|---|---|---|
| Pi Zero 2 W / Pi 3 on 32-bit OS (armv7l) | yes, from piwheels only, and only if the installer is configured to use piwheels | no, if the wheel is used |
| Pi 4 / Pi 3 on 64-bit OS (aarch64) | no | **yes** (gcc from `build-essential` is on Lite; `python3-dev` is not) |

## 3. numpy and scipy wheels

PyPI aarch64 `manylinux` wheels (PyPI has no armv7l Linux wheels for these) [6]:

| | Python 3.11 | Python 3.13 |
|---|---|---|
| numpy | 1.23.2 to 2.4.6 | 2.1.0 to 2.5.4 |
| scipy | 1.9.2 to 1.17.1 | 1.14.1 to 1.18.1 |

The project pins `numpy>=2.0,<3` and `scipy>=1.14,<2` (`pyproject.toml`); both ranges are satisfiable on both Pythons. Sample sizes: numpy 2.0.0 cp311 aarch64 13.9 MB, scipy 1.14.0 cp311 aarch64 35.6 MB; latest cp313 aarch64 numpy 15.7 MB, scipy 34.0 MB. [6]

piwheels (armv7l), newest versions [4]:

| | cp311 | cp313 |
|---|---|---|
| numpy | 2.4.6 | 2.5.4 |
| scipy | 1.17.1 | 1.18.1 |

piwheels wheels declare apt dependencies, e.g. numpy 2.5.4 needs `libopenblas0-pthread` and `libgfortran5`; scipy 1.14.0 needs `libgfortran5` and `libopenblas0-pthread` (plus `libatomic1` on cp313). The FAQ says missing libraries cause a "cannot open shared object file" ImportError, fixed by installing the apt packages. [4] PyPI aarch64 manylinux wheels are self-contained and have no such requirement.

### uv does not use piwheels by default

- Raspberry Pi OS pip uses piwheels through `/etc/pip.conf` (piwheels FAQ). uv does not read pip config; it reads `uv.toml` or `pyproject.toml` at project level, `~/.config/uv/uv.toml` and `/etc/uv/uv.toml`. [4][11]
- The piwheels FAQ gives a uv recipe: `extra-index-url = ["https://www.piwheels.org/simple"]` in `~/.config/uv/uv.toml`. [4]
- uv's default `index-strategy` is `first-index`: it only considers the first index that contains a package. PyPI is always the lowest-priority index and numpy, scipy and rpi-ws281x exist there (as sdists on armv7l), so piwheels would not be consulted for them. `--index-strategy unsafe-best-match` (or `UV_INDEX_STRATEGY`) makes uv search all indexes. [12]
- **Inference**: on 32-bit OS, `uv tool install` with only the documented extra-index recipe may still select PyPI sdists and try to compile numpy/scipy, which is impractical on a Zero 2 W. It would need `--index-strategy unsafe-best-match`. Not tested; verify on hardware.

## 4. Is `libportaudio2` the only apt package needed?

- `sounddevice` on PyPI has bundled-PortAudio wheels only for macOS and Windows; for Linux there is a pure-Python wheel and an sdist. Its README says it provides bindings for the PortAudio library. [7] Linux therefore needs the system library `libportaudio2` (Debian 19.6.0 in both Bookworm and Trixie). [8]
- Also needed depending on route: `python3-dev` plus a compiler for `rpi_ws281x` on aarch64 (section 2); `libopenblas0-pthread` and `libgfortran5` for piwheels numpy/scipy on armv7l (section 3); `git` only for `--source git+https://...` installs (existing `setup.sh` comment).
- Could one command install `libportaudio2`? A bare `pip` or `uv` cannot run apt. `setup.sh` already does it (`sudo apt-get install ... libportaudio2`).
- Current state: `music-led-strip-control` returns 404 on PyPI today, so a pure `uv tool install music-led-strip-control[pi]` is not yet possible; `setup.sh` defaults to that package name. [3]

## 5. Cold-install time and size

No primary source documents install time for a Pi Zero 2 W or a Pi 4. Neither PyPI, piwheels, the Raspberry Pi docs nor the uv docs publish it. Only wheel sizes (above) are verifiable: roughly 50 MB for the numpy plus scipy wheels on aarch64, before other dependencies. Timings would need to be measured on hardware.

## 6. uv facts relevant to the current approach

- `uv tool install` creates an isolated venv per tool and symlinks executables into the bin dir, which satisfies PEP 668. [13]
- The standalone installer is `curl -LsSf https://astral.sh/uv/install.sh | sh`; uv is also on PyPI. [14]
- `aarch64-unknown-linux-gnu` (glibc 2.28+) and `armv7-unknown-linux-gnueabihf` (glibc 2.17+) are both Tier 2 ("guaranteed to build", tests not run on them). [15] The latest uv release has assets for both targets. [16]
- uv prefers an existing system Python over downloading one, so system `python3-dev` is what the `rpi_ws281x` sdist build uses. [17]

## Conclusions for the install design (#350)

1. A venv-based tool (uv or pipx) is mandatory; plain pip will not work. Keep `uv tool install`.
2. Keep `build-essential` and `python3-dev` in the apt step for aarch64. They can only be dropped for 32-bit installs that actually resolve to the piwheels wheel.
3. `libportaudio2` stays in `setup.sh`; a pip-only command cannot cover it.
4. For 32-bit Pi OS, the script would need piwheels configured for uv plus `--index-strategy unsafe-best-match` (Inference, untested) and the runtime apt packages `libopenblas0-pthread libgfortran5` (plus `libatomic1` on Trixie).
5. Open items needing hardware: whether a built Lite image lacks `pip`/`git`/`python3-dev`, 32-bit uv behaviour, and install timings.

## Sources

1. PEP 668, https://peps.python.org/pep-0668/
2. Raspberry Pi OS docs, https://www.raspberrypi.com/documentation/computers/os.html
3. PyPI JSON API, https://pypi.org/pypi/rpi-ws281x/json and https://pypi.org/pypi/music-led-strip-control/json
4. piwheels FAQ https://www.piwheels.org/faq.html and project JSON https://www.piwheels.org/project/rpi-ws281x/json/ , /numpy/json/ , /scipy/json/
6. PyPI JSON API, https://pypi.org/pypi/numpy/json and https://pypi.org/pypi/scipy/json
7. PyPI https://pypi.org/pypi/sounddevice/json ; README https://github.com/spatialaudio/python-sounddevice
8. Debian package pages, https://packages.debian.org/bookworm/python3 , /trixie/python3 , and python3-pip, pipx, python3-dev, libportaudio2, git
9. pi-gen, https://github.com/RPi-Distro/pi-gen (`stage2/01-sys-tweaks/00-packages`, branches master and bookworm)
10. rpi-ws281x-python `library/setup.py`, https://github.com/rpi-ws281x/rpi-ws281x-python
11. uv configuration files, https://docs.astral.sh/uv/concepts/configuration-files/
12. uv indexes, https://docs.astral.sh/uv/concepts/indexes/
13. uv tools, https://docs.astral.sh/uv/concepts/tools/
14. uv installation, https://docs.astral.sh/uv/getting-started/installation/
15. uv platform policy, https://docs.astral.sh/uv/reference/policies/platforms/
16. uv releases, https://github.com/astral-sh/uv/releases/latest
17. uv Python versions, https://docs.astral.sh/uv/concepts/python-versions/
