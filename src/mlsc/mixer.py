"""Hardware capture gain through ALSA's `amixer`, with the card and control discovered from the selected device."""
from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass

from loguru import logger

AMIXER = "amixer"
# Tried first when a card has several capture controls.
PREFERRED_CONTROLS = ("Mic", "Capture", "Mic Capture", "Digital")

CommandRunner = Callable[[list[str]], subprocess.CompletedProcess]

# PortAudio's ALSA device names end with the card, e.g. "USB PnP Sound Device: Audio (hw:1,0)".
_CARD = re.compile(r"\bhw:(?:CARD=)?(\w+)")
_CONTROL = re.compile(r"^Simple mixer control '(.+)',(\d+)$")
_LEVEL = re.compile(r"\[(\d+)%\]")


def run_command(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, text=True, capture_output=True, check=False, timeout=5)


@dataclass(frozen=True)
class Mixer:
    card: str
    control: str
    run: CommandRunner = run_command

    def get_level(self) -> int:
        """Return the capture level in percent."""
        process = self.run([AMIXER, "-c", self.card, "sget", self.control])
        match = _LEVEL.search(process.stdout)
        if process.returncode != 0 or match is None:
            raise MixerError(process.stderr.strip() or f"Could not read the level of {self.control!r}.")
        return int(match.group(1))

    def set_level(self, level: int) -> None:
        process = self.run([AMIXER, "-c", self.card, "sset", self.control, f"{level}%", "cap"])
        if process.returncode != 0:
            raise MixerError(process.stderr.strip() or f"Could not set the level of {self.control!r}.")


class MixerError(Exception):
    """Raised when amixer fails."""


def card_of(device_name: str | None) -> str | None:
    """Return the ALSA card that a device name refers to, or None when it names none (System default, other host APIs)."""
    match = _CARD.search(device_name or "")
    return match.group(1) if match else None


def capture_controls(scontents: str) -> list[str]:
    """Return the controls in `amixer scontents` output that have a capture volume, in the order listed."""
    controls = []
    current = None
    for line in scontents.splitlines():
        match = _CONTROL.match(line)
        if match:
            current = match.group(1)
        elif current and line.strip().startswith("Capabilities:") and "cvolume" in line.split(":", 1)[1].split():
            controls.append(current)
    return controls


def find_mixer(device_name: str | None, run: CommandRunner = run_command) -> Mixer | None:
    """Return the capture control of the card behind `device_name`, or None when there is no hardware slider for it."""
    card = card_of(device_name)
    if card is None or (run is run_command and shutil.which(AMIXER) is None):
        return None
    try:
        process = run([AMIXER, "-c", card, "scontents"])
    except (OSError, subprocess.SubprocessError) as e:
        logger.debug(f"amixer is not usable: {e}")
        return None
    if process.returncode != 0:
        return None
    controls = capture_controls(process.stdout)
    if not controls:
        return None
    preferred = next((name for name in PREFERRED_CONTROLS if name in controls), controls[0])
    return Mixer(card, preferred, run)
