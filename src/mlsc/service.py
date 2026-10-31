"""`mlsc service`: installs MLSC as a systemd service that starts at boot."""
from __future__ import annotations

import os
import shlex
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from mlsc import paths
from mlsc.host import Host

SERVICE_NAME = "mlsc.service"
UNIT_PATH = Path("/etc/systemd/system") / SERVICE_NAME
MANAGED_MARKER = "# Managed by `mlsc service install`."
SYSTEMCTL_TIMEOUT_SECONDS = 60


class ServiceError(Exception):
    """A service action cannot be carried out; the message tells the user what to do."""


def installing_user_config_dir(env: dict[str, str] | None = None) -> Path:
    """The config dir of the user who ran the install, also when they used `sudo`, so the service reads the config they created."""
    env = os.environ if env is None else env
    sudo_user = env.get("SUDO_USER")
    if env.get(paths.CONFIG_DIR_ENV) or not sudo_user or sudo_user == "root":
        return paths.config_dir()
    import pwd  # ruff: ignore[import-outside-top-level] POSIX only, and only needed when installing through sudo.

    home = Path(pwd.getpwnam(sudo_user).pw_dir)
    return Path(env.get("XDG_CONFIG_HOME") or home / ".config") / paths.APP_NAME


def running_as_root() -> bool:
    return sys.platform == "linux" and os.geteuid() == 0


def render_unit(exec_start: list[str], config_dir: Path) -> str:
    """The unit file. `User=root` because `rpi_ws281x` needs `/dev/mem`; the hardening keeps the rest of the system out of reach."""
    return f"""{MANAGED_MARKER}
[Unit]
Description=Music LED Strip Control
After=network.target sound.target

[Service]
Type=simple
User=root
Environment={paths.CONFIG_DIR_ENV}={config_dir}
ExecStart={shlex.join(exec_start)}
Restart=on-abnormal
RestartSec=10
KillMode=control-group
ProtectHome=read-only
ReadWritePaths={config_dir}
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
"""


@dataclass
class ServiceManager:
    host: Host
    unit_path: Path = UNIT_PATH
    config_dir: Callable[[], Path] = installing_user_config_dir
    exec_start: list[str] | None = None
    is_root: Callable[[], bool] = field(default=lambda: running_as_root())  # looked up late so tests can substitute it

    def _systemctl(self, *args: str) -> tuple[int, str]:
        return self.host.run(["systemctl", *args], timeout=SYSTEMCTL_TIMEOUT_SECONDS)

    def _require_systemd(self) -> None:
        if self.host.which("systemctl") is None:
            raise ServiceError("systemd was not found. The service commands only work on Linux with systemd.")

    def _require_root(self, action: str) -> None:
        if not self.is_root():
            raise ServiceError(f"`mlsc service {action}` needs root. Run it with sudo, for example: sudo \"$(command -v mlsc)\" service {action}")

    def _check(self, *args: str) -> str:
        code, output = self._systemctl(*args)
        if code != 0:
            raise ServiceError(f"systemctl {' '.join(args)} failed ({code}): {output}")
        return output

    def install(self) -> list[str]:
        """Write the unit, enable it and (re)start it. An existing unit, such as the one from 2.x, is replaced. Returns the lines to show."""
        self._require_systemd()
        self._require_root("install")
        config_dir = self.config_dir()
        exec_start = self.exec_start or [sys.executable, "-m", "mlsc", "run"]
        lines = []
        previous = self.unit_path.read_text(encoding="utf-8", errors="replace") if self.unit_path.is_file() else None
        if previous is not None:
            lines.append(f"Replacing the existing {SERVICE_NAME}{'' if MANAGED_MARKER in previous else ' (from MLSC 2.x)'}.")
            self._systemctl("stop", SERVICE_NAME)
        config_dir.mkdir(parents=True, exist_ok=True)
        self._own_like_user(config_dir)
        self.unit_path.write_text(render_unit(exec_start, config_dir), encoding="utf-8")
        self._check("daemon-reload")
        self._check("enable", SERVICE_NAME)
        self._check("restart", SERVICE_NAME)
        lines.append(f"Installed {self.unit_path}, enabled it and started it. Config directory: {config_dir}")
        return lines

    def uninstall(self) -> list[str]:
        """Stop and remove the unit. The config and data stay where they are."""
        self._require_systemd()
        self._require_root("uninstall")
        if not self.unit_path.is_file():
            return [f"{SERVICE_NAME} is not installed."]
        self._systemctl("stop", SERVICE_NAME)
        self._systemctl("disable", SERVICE_NAME)
        self.unit_path.unlink()
        self._check("daemon-reload")
        return [f"Removed {self.unit_path}. The config was left untouched."]

    def status(self) -> tuple[int, str]:
        """The `systemctl status` output and its exit code (0 running, 3 stopped, 4 not installed)."""
        self._require_systemd()
        return self._systemctl("status", SERVICE_NAME, "--no-pager")

    def restart(self) -> list[str]:
        self._require_systemd()
        self._require_root("restart")
        self._check("restart", SERVICE_NAME)
        return [f"Restarted {SERVICE_NAME}."]

    def _own_like_user(self, directory: Path) -> None:
        """Give a directory that root just created to the user who ran sudo, so they can still edit the config."""
        sudo_user = os.environ.get("SUDO_USER")
        if not sudo_user or sudo_user == "root" or sys.platform == "win32":
            return
        import pwd  # ruff: ignore[import-outside-top-level] POSIX only.

        entry = pwd.getpwnam(sudo_user)
        os.chown(directory, entry.pw_uid, entry.pw_gid)
