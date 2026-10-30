"""`mlsc doctor`: runs the Diagnosis checks for the config, the outputs, audio, Wi-Fi and permissions."""
from __future__ import annotations

import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from mlsc import config_migration, paths
from mlsc.audio_capture import BACKEND_ENV_VAR, create_capture
from mlsc.diagnosis import Diagnosis, Status
from mlsc.host import Host
from mlsc.output_enum import OutputsEnum
from mlsc.outputs.output import Output
from mlsc.outputs.output_dummy import OutputDummy
from mlsc.outputs.output_raspi import OutputRaspi
from mlsc.outputs.output_udp import OutputUDP
from mlsc.webserver.schemas.config_validator_service import ConfigValidatorService

OUTPUTS: dict[str, type[Output]] = {
    OutputsEnum.output_dummy.name: OutputDummy,
    OutputsEnum.output_raspi.name: OutputRaspi,
    OutputsEnum.output_udp.name: OutputUDP,
}


@dataclass(frozen=True)
class Check:
    name: str
    diagnosis: Diagnosis


def run_checks(config_dir: Path, host: Host | None = None, capture_factory: Callable | None = None) -> list[Check]:
    host = host or Host()
    capture_factory = capture_factory or (lambda: create_capture(os.environ.get(BACKEND_ENV_VAR, "auto")))
    config_check, config = _check_config(config_dir)
    checks = [config_check]
    checks.extend(_check_outputs(config, host))
    checks.append(Check("audio", _check_audio(config, capture_factory)))
    checks.append(Check("wifi", _check_wifi(host)))
    checks.append(Check("permissions", _check_permissions(config_dir)))
    return checks


def format_report(checks: list[Check]) -> str:
    lines = []
    for check in checks:
        diagnosis = check.diagnosis
        lines.append(f"[{diagnosis.status.name}] {check.name}: {diagnosis.message}")
        if diagnosis.suggested_fix:
            lines.append(f"  Fix: {diagnosis.suggested_fix}")
    return "\n".join(lines)


def has_errors(checks: list[Check]) -> bool:
    return any(check.diagnosis.status is Status.ERROR for check in checks)


def _check_config(config_dir: Path) -> tuple[Check, dict | None]:
    path = config_dir / config_migration.CONFIG_FILE
    if not path.is_file():
        return Check("config", Diagnosis.warning(f"No config at {path}; the defaults are created on the first start.")), None
    try:
        config = config_migration.read_json(path)
    except config_migration.ConfigMigrationError as e:
        return Check("config", Diagnosis.error(str(e), config_migration.HELP_HINT)), None
    version = config.get("version")
    if version != config_migration.CURRENT_VERSION:
        message = f"The config is version {version}, this MLSC needs {config_migration.CURRENT_VERSION}."
        return Check("config", Diagnosis.error(message, "Run 'mlsc config migrate'.")), None
    errors = ConfigValidatorService().errors(config)
    if errors:
        return Check("config", Diagnosis.error(f"The config is invalid: {errors[0]}", config_migration.HELP_HINT)), None
    return Check("config", Diagnosis.ok(f"{path} is valid.")), config


def _check_outputs(config: dict | None, host: Host) -> list[Check]:
    if config is None:
        return []
    checks = []
    for device_id, device_config in config["device_configs"].items():
        output_type = device_config["output_type"]
        output = OUTPUTS.get(output_type)
        if output is None:
            message = f"The output type {output_type!r} is not supported."
            diagnosis = Diagnosis.error(message, "Choose local GPIO, UDP or mock in the device settings.")
        else:
            try:
                diagnosis = output.diagnose(device_config, host)
            except (KeyError, TypeError) as e:
                diagnosis = Diagnosis.error(f"The output settings are incomplete: {e!r}.", config_migration.HELP_HINT)
        checks.append(Check(f"output {device_id}", diagnosis))
    return checks


def _check_audio(config: dict | None, capture_factory: Callable) -> Diagnosis:
    if config is not None and config["audio"]["source"] == "browser":
        return Diagnosis.ok("Audio comes from the browser microphone; no server device is needed.")
    try:
        devices = capture_factory().list_devices()
    except Exception as e:
        return Diagnosis.error(f"Audio capture is unavailable: {e}", "On Linux install libportaudio2, or set MLSC_AUDIO_BACKEND=miniaudio.")
    if not devices:
        return Diagnosis.error("No audio input devices were found.", "Connect a microphone or a monitor device, or use the browser microphone.")
    return Diagnosis.ok(f"{len(devices)} audio input device(s) found.")


def _check_wifi(host: Host) -> Diagnosis:
    if sys.platform != "linux":
        return Diagnosis.ok("Wi-Fi management is only used on Linux.")
    if host.which("nmcli") is None:
        message = "NetworkManager (nmcli) is not installed, so MLSC cannot manage Wi-Fi."
        return Diagnosis.warning(message, "Install NetworkManager or manage Wi-Fi yourself.")
    code, output = host.run(["nmcli", "-t", "-f", "STATE", "general"])
    if code != 0:
        return Diagnosis.warning(f"NetworkManager did not answer: {output}", "Start it with: sudo systemctl start NetworkManager")
    if not output.strip().startswith("connected"):
        return Diagnosis.warning(f"The network state is {output.strip()!r}.", "Connect to a network or start the Hotspot.")
    return Diagnosis.ok("NetworkManager reports a connection.")


def _check_permissions(config_dir: Path) -> Diagnosis:
    for path in (config_dir, paths.data_dir()):
        reason = _unwritable_reason(path)
        if reason:
            return Diagnosis.error(f"{path} is not writable: {reason}", "Fix the ownership of the directory or use --config-dir.")
    return Diagnosis.ok("The config and data directories are writable.")


def _unwritable_reason(path: Path) -> str | None:
    """Why a file cannot be created in `path`, or None when it can. A missing directory is judged by its nearest existing parent and not created."""
    existing = path
    while not existing.exists() and existing != existing.parent:
        existing = existing.parent
    if not existing.is_dir():
        return f"{existing} is not a directory"
    if not os.access(existing, os.W_OK | os.X_OK):
        return f"no write permission for {existing}"
    return None


def run(config_dir: Path) -> int:
    checks = run_checks(config_dir)
    print(format_report(checks))  # ruff: ignore[print]
    return 1 if has_errors(checks) else 0
