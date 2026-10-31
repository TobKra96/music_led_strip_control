#!/usr/bin/env bash
set -euo pipefail

# Thin bootstrapper for MLSC: installs the system packages and uv, installs the package and calls `mlsc service install`.
# https://github.com/TobKra96/music_led_strip_control

if [[ $EUID -eq 0 ]]; then
    echo "Do not run this script as root. It asks for sudo where needed." >&2
    exit 1
fi

PACKAGE="music-led-strip-control[pi]"
UV_BIN="$HOME/.local/bin/uv"

function usage {
    echo "Usage: bash $0 [options]"
    echo
    echo "OPTIONS"
    echo "  -s, --source SPEC   package to install (default: $PACKAGE), for example 'git+https://github.com/TobKra96/music_led_strip_control@dev_3.0'"
    echo "  -h, --help          show this list of command-line options"
    exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do case $1 in
    -s|--source) PACKAGE="${2:?--source needs a value}"; shift 2;;
    -h|--help) usage;;
    *) echo "Unknown argument passed: $1" >&2; usage 1;;
esac; done

echo "[1/3] Installing the system packages..."
# libportaudio2: audio input. build-essential, python3-dev: build rpi_ws281x. git: for --source git+https URLs.
sudo apt-get update -qq
sudo apt-get -y --no-install-recommends install git python3-dev libportaudio2 build-essential curl

echo "[2/3] Installing MLSC..."
if [[ -x "$UV_BIN" ]]; then
    "$UV_BIN" self update
else
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi
"$UV_BIN" tool install --force "$PACKAGE"
MLSC_BIN="$("$UV_BIN" tool dir --bin)/mlsc"

echo "[3/3] Installing the service..."
sudo "$MLSC_BIN" service install

echo
echo "MLSC is installed and running. Open http://$(hostname).local:8080 and check 'mlsc service status'."
echo "Upgrading from 2.x? Run 'mlsc config migrate' first. Your 2.x clone and config are left untouched."
