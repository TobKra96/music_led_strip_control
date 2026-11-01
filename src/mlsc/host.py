"""What the checks need to know about the machine MLSC runs on. Tests substitute a fake."""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEVICE_TREE_MODEL = Path("/proc/device-tree/model")
BOOT_CONFIGS = (Path("/boot/firmware/config.txt"), Path("/boot/config.txt"))
GPIO_MEMORY = "/dev/mem"
BOOT_DIRS = (Path("/boot/firmware"), Path("/boot"))
NET_CLASS = Path("/sys/class/net")
WIFI_INTERFACE_PREFIXES = ("wl",)
COMMAND_TIMEOUT_SECONDS = 5
JOURNAL_DIR = Path("/var/log/journal")
SERVICE_NAME = "mlsc.service"


class Host:
    def __init__(self, device_tree_model: Path = DEVICE_TREE_MODEL, boot_configs: tuple[Path, ...] | list[Path] = BOOT_CONFIGS) -> None:
        self._device_tree_model = device_tree_model
        self._boot_configs = boot_configs

    def has_ws281x(self) -> bool:
        return any(importlib.util.find_spec(name) is not None for name in ("_rpi_ws281x", "rpi_ws281x"))

    def can_drive_gpio(self) -> bool:
        """Whether local GPIO output can work here at all: on Linux with `rpi_ws281x` installed. Windows and macOS use the Mock Output."""
        return sys.platform == "linux" and self.has_ws281x()

    def pi_model(self) -> str | None:
        """The Raspberry Pi model string, or None when this is not a Pi."""
        try:
            return self._device_tree_model.read_bytes().rstrip(b"\x00").decode(errors="replace")
        except OSError:
            return None

    def can_use_gpio_memory(self) -> bool:
        """Whether the process may map GPIO memory, which `rpi_ws281x` needs. Only Linux restricts it."""
        if sys.platform != "linux":
            return True
        return os.geteuid() == 0 or os.access(GPIO_MEMORY, os.R_OK | os.W_OK)

    def analog_audio_enabled(self) -> bool:
        """Whether the Pi's analog audio (which uses the PWM hardware) is switched on in the boot config."""
        for path in self._boot_configs:
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            # The last dtparam=audio setting wins, as in the firmware.
            enabled = False
            for line in lines:
                for param in line.strip().replace(" ", "").removeprefix("dtparam=").split(",") if line.strip().replace(" ", "").startswith("dtparam=") else []:
                    if param.startswith("audio="):
                        enabled = param == "audio=on"
            return enabled
        return False

    def boot_dir(self) -> Path | None:
        """The boot partition, where the user can leave files for MLSC. None where there is none."""
        return next((path for path in BOOT_DIRS if path.is_dir()), None)

    def mac_address(self) -> str | None:
        """The MAC address of the first Wi-Fi interface, or None."""
        for interface in sorted(NET_CLASS.glob("wl*")):
            try:
                return (interface / "address").read_text().strip()
            except OSError:
                continue
        return None

    def ethernet_up(self) -> bool:
        """Whether a wired interface has a link."""
        try:
            interfaces = sorted(NET_CLASS.iterdir())
        except OSError:
            return False
        for interface in interfaces:
            if interface.name == "lo" or interface.name.startswith(WIFI_INTERFACE_PREFIXES) or not (interface / "device").exists():
                continue
            try:
                if (interface / "operstate").read_text().strip() == "up":
                    return True
            except OSError:
                continue
        return False

    def power_action_block(self, action: str) -> str | None:  # ruff: ignore[unused-method-argument]
        """Why a Power Action cannot run here, or None when it can. Needs Linux, `systemctl` and root."""
        if sys.platform != "linux":
            return "Rebooting and shutting down are only possible on Linux."
        if self.which("systemctl") is None:
            return "`systemctl` was not found on this system."
        if os.geteuid() != 0:
            return "MLSC must run as root to reboot or shut down the machine."
        return None

    def autostart_warning(self) -> str | None:
        """Why MLSC would not be running again after a reboot, or None when it would (or when this host has no systemd to ask)."""
        if sys.platform != "linux" or self.which("systemctl") is None:
            return None
        code, output = self.run(["systemctl", "is-enabled", SERVICE_NAME])
        state = output.splitlines()[0].strip() if output else ""
        if code == 0 and state == "enabled":
            return None
        if code == 127 or code == 124:
            return None
        if state == "not-found" or "No such file" in output or "does not exist" in output:
            return f"{SERVICE_NAME} is not installed, so MLSC will not start again after a reboot. Run `sudo mlsc service install`."
        return f"{SERVICE_NAME} is not enabled, so MLSC will not start again after a reboot. Run `sudo systemctl enable {SERVICE_NAME}`."

    def server_logs_unavailable(self) -> str | None:
        """Why the Server Logs cannot be read here, or None when they can. Needs Linux, `journalctl`, the systemd service and root."""
        if sys.platform != "linux":
            return "Server logs are only available on Linux."
        if self.which("journalctl") is None:
            return "`journalctl` was not found on this system."
        if not (os.environ.get("INVOCATION_ID") or os.environ.get("JOURNAL_STREAM")):
            return "MLSC is not running as a systemd service, so its logs are not in the journal."
        if os.geteuid() != 0:
            return "MLSC must run as root to read the system journal."
        return None

    def journal_is_persistent(self) -> bool:
        """Whether the journal survives a reboot: `/var/log/journal` exists. Otherwise it lives in memory."""
        return JOURNAL_DIR.is_dir()

    def which(self, command: str) -> str | None:
        return shutil.which(command)

    def run(self, command: list[str], timeout: float = COMMAND_TIMEOUT_SECONDS) -> tuple[int, str]:
        """Run `command` and return its exit code and combined output. 127 when the command does not exist."""
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        except FileNotFoundError:
            return 127, f"{command[0]}: command not found"
        except subprocess.TimeoutExpired:
            return 124, f"{command[0]} timed out"
        return result.returncode, (result.stdout + result.stderr).strip()
