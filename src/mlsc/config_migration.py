"""Config Migration: the explicit, backed-up conversion of an older config to the current format.

The converter chain is pure. This module owns the files around it: it migrates in memory, validates, and only then writes
atomically, so a failure leaves the original untouched.
"""
from __future__ import annotations

import copy
import json
import os
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from loguru import logger

from mlsc.config_converter.config_converter_service import ConfigConverterService
from mlsc.config_converter.config_converter_v4 import MigrationReport
from mlsc.webserver.schemas.config_validator_service import ConfigValidatorService

CURRENT_VERSION = 4
CONFIG_FILE = "config.json"
ROLLING_BACKUP_FILE = "config_backup.json"
REPORT_FILE = "migration-report.json"
SHARE_LEGACY_DIR = Path("/share/.mlsc")  # Where setup.sh put the 2.x config.

HELP_HINT = "Run 'mlsc config reset' to start over with the default config, or 'mlsc doctor' to check the setup."


class ConfigMigrationError(Exception):
    """The config could not be loaded, migrated or validated. The message is meant for the user."""


@dataclass
class MigrationResult:
    config: dict
    report: MigrationReport
    source: Path
    target: Path
    backup: Path | None = None
    written: bool = False


def backup_name(version: int) -> str:
    return f"config.v{version}.bak.json"


def read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise ConfigMigrationError(f"Could not read {path}: {e}") from e
    except json.JSONDecodeError as e:
        raise ConfigMigrationError(f"{path} is not valid JSON: {e}") from e
    if not isinstance(data, dict):
        raise ConfigMigrationError(f"{path} does not contain a config object.")
    return data


def write_json_atomic(path: Path, data: dict) -> None:
    """Write via a temp file in the same directory and rename, so readers never see a partial file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f"{path.name}.tmp")
    try:
        with temp.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def load_template() -> dict:
    return json.loads((resources.files("mlsc") / "config_template.json").read_text(encoding="utf-8"))


def fill_defaults(config: dict, template: dict) -> None:
    """Add every key the template has and the config lacks. Existing values and unknown keys stay."""
    for key, default in template.items():
        if key == "device_configs":
            continue
        if key not in config:
            config[key] = copy.deepcopy(default)
        elif isinstance(default, dict) and isinstance(config[key], dict):
            fill_defaults(config[key], default)

    for device in config.get("device_configs", {}).values():
        if isinstance(device, dict):
            fill_defaults(device, template["default_device"])


# 1.x stored these effect settings as the strings "true"/"false".
STRING_BOOLEAN_SETTINGS = (("effect_single", "use_custom_color"), ("effect_vu_meter", "use_gradient"))


def coerce_string_booleans(config: dict, report: MigrationReport) -> None:
    devices = {"default_device": config.get("default_device"), **config.get("device_configs", {})}
    for device_id, device in devices.items():
        effects = device.get("effects", {}) if isinstance(device, dict) else {}
        for effect, setting in STRING_BOOLEAN_SETTINGS:
            value = effects.get(effect, {}).get(setting)
            if value in ("true", "false"):
                effects[effect][setting] = value == "true"
                path = f"{'device_configs.' if device_id != 'default_device' else ''}{device_id}.effects.{effect}.{setting}"
                report.add("info", "string_boolean", path, f"Converted {value!r} to a boolean.", value)


def list_audio_devices() -> list[dict] | None:
    """Return the input devices as `{"index", "name", "host_api"}`, or None when audio cannot be queried."""
    try:
        # Imported here as it is optional at migration time and slow to import.
        from mlsc.audio_capture import create_capture  # ruff: ignore[import-outside-top-level]

        return [{"index": device.device_id, "name": device.name, "host_api": None} for device in create_capture().list_devices()]
    except Exception:
        logger.warning("Could not query audio devices for the config migration.")
        return None


def migrate_data(data: dict, audio_devices: list[dict] | None = None) -> tuple[dict, MigrationReport]:
    """Migrate, fill template defaults and validate, all in memory. Used for startup, `mlsc config migrate` and import."""
    version = data.get("version", 1)
    if not isinstance(version, int) or isinstance(version, bool):
        raise ConfigMigrationError(f"The config has an invalid version {version!r}.")
    if version > CURRENT_VERSION:
        raise ConfigMigrationError(
            f"The config is version {version}, but this MLSC only supports up to version {CURRENT_VERSION}. "
            "It was left unchanged. Upgrade MLSC to open it."
        )

    try:
        config, report = ConfigConverterService.migrate(copy.deepcopy(data), audio_devices=audio_devices)
        fill_defaults(config, load_template())
        coerce_string_booleans(config, report)
    except Exception as e:
        raise ConfigMigrationError(f"The config could not be migrated: {e!r}") from e

    # Unknown keys are preserved, so only the known part of the config is checked.
    errors = ConfigValidatorService().errors(config, allow_unknown_keys=True)
    if errors:
        shown = "\n  ".join(error[:200] for error in errors[:5])
        more = f"\n  ... and {len(errors) - 5} more" if len(errors) > 5 else ""
        raise ConfigMigrationError(f"The migrated config is not valid:\n  {shown}{more}")

    return config, report


def migrate_file(source: Path, config_dir: Path, *, dry_run: bool = False, audio_devices: list[dict] | None = None) -> MigrationResult:
    """Migrate `source` into `config_dir/config.json`.

    `source` may be the target itself (in-place) or a legacy file, which is only read. The original is copied once to
    `config.v<old>.bak.json` and never overwritten. The rolling backup follows only after the new config validated.
    """
    source = Path(source)
    target = config_dir / CONFIG_FILE
    data = read_json(source)
    from_version = data.get("version", 1)
    config, report = migrate_data(data, audio_devices)
    result = MigrationResult(config=config, report=report, source=source, target=target)
    if dry_run:
        return result

    if target.exists() and not _same_file(source, target):
        raise ConfigMigrationError(f"{target} already exists and would be replaced. Run 'mlsc config reset' first, which keeps a copy.")

    config_dir.mkdir(parents=True, exist_ok=True)
    backup = config_dir / backup_name(from_version)
    if not backup.exists():
        shutil.copyfile(source, backup)
    result.backup = backup

    write_json_atomic(target, config)
    write_json_atomic(config_dir / REPORT_FILE, report.to_dict())
    shutil.copyfile(target, config_dir / ROLLING_BACKUP_FILE)
    result.written = True
    return result


def _same_file(a: Path, b: Path) -> bool:
    return a.exists() and b.exists() and a.samefile(b)


def find_legacy_config(from_path: str | os.PathLike | None = None, cwd: Path | None = None) -> Path | None:
    """Locate a pre-3.0 config. `from_path` may be the file, or a directory holding config.json."""
    if from_path is not None:
        path = Path(from_path).expanduser()
        path = path / CONFIG_FILE if path.is_dir() else path
        if not path.is_file():
            raise ConfigMigrationError(f"No config found at {path}.")
        return path

    for legacy_dir in ((cwd or Path.cwd()) / ".mlsc", SHARE_LEGACY_DIR):
        candidate = legacy_dir / CONFIG_FILE
        if candidate.is_file():
            return candidate
    return None


def prepare_config(
    config_dir: Path,
    *,
    from_path: str | os.PathLike | None = None,
    audio_devices: Callable[[], list[dict] | None] | None = None,
) -> MigrationResult | None:
    """Make `config_dir/config.json` a valid current config before anything reads it. Returns the migration, if one ran.

    A missing config is copy-migrated from a legacy location, restored from the rolling backup, or created from the template.
    A corrupt current config is left for the runtime fallback to the last-good backup.
    `audio_devices` is called only when a migration runs, so a current config never touches the audio system.
    """
    audio_devices = audio_devices or list_audio_devices
    config_dir.mkdir(parents=True, exist_ok=True)
    target = config_dir / CONFIG_FILE

    if target.exists():
        try:
            version = json.loads(target.read_text(encoding="utf-8")).get("version", 1)
        except (OSError, ValueError, AttributeError):
            return None
        if version == CURRENT_VERSION:
            return None
        return _migrate_or_refuse(target, config_dir, audio_devices)

    legacy = find_legacy_config(from_path)
    if legacy is not None:
        logger.info(f"Found a legacy config at {legacy}. Migrating a copy into {config_dir}.")
        return _migrate_or_refuse(legacy, config_dir, audio_devices)

    backup = config_dir / ROLLING_BACKUP_FILE
    if backup.exists():
        shutil.copyfile(backup, target)
    else:
        write_json_atomic(target, load_template())
    return None


def _migrate_or_refuse(source: Path, config_dir: Path, audio_devices: Callable[[], list[dict] | None]) -> MigrationResult:
    try:
        return migrate_file(source, config_dir, audio_devices=audio_devices())
    except ConfigMigrationError as e:
        hint = f"\nThe original is untouched. Backups: {config_dir}. {HELP_HINT}"
        raise ConfigMigrationError(f"{e}{hint}") from e


def reset_config(config_dir: Path) -> Path | None:
    """Replace the config with the template. The replaced file is kept as `config.pre-reset.bak.json`; returns that path."""
    target = config_dir / CONFIG_FILE
    kept = None
    if target.exists():
        kept = config_dir / "config.pre-reset.bak.json"
        shutil.copyfile(target, kept)
    write_json_atomic(target, load_template())
    return kept
