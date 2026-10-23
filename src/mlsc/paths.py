"""Locations of the config and data directories.

The config directory is resolved from `MLSC_CONFIG_DIR` (set by `--config-dir`) and falls back to the platform default.
It is passed through the environment so that spawned child processes resolve the same directory.
"""
from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_config_path, user_data_path

APP_NAME = "mlsc"
CONFIG_DIR_ENV = "MLSC_CONFIG_DIR"


def config_dir() -> Path:
    """Return the directory holding config.json, its backup and security.ini."""
    override = os.environ.get(CONFIG_DIR_ENV)
    if override:
        return Path(override).expanduser().resolve()
    return user_config_path(APP_NAME)


def data_dir() -> Path:
    """Return the directory for logs and the instance lock.

    An explicit config directory keeps everything together in one place.
    """
    if os.environ.get(CONFIG_DIR_ENV):
        return config_dir()
    return user_data_path(APP_NAME)


def set_config_dir(path: str | os.PathLike) -> None:
    os.environ[CONFIG_DIR_ENV] = str(Path(path).expanduser().resolve())
