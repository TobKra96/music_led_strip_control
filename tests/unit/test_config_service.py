import json
import threading
from importlib import resources

import pytest

from mlsc.config_service import ConfigService

pytestmark = pytest.mark.unit

TEMPLATE = resources.files("mlsc") / "config_template.json"


def test_first_start_copies_the_template_into_the_config_dir(config_dir):
    service = ConfigService(threading.Lock())

    assert service.get_config_path() == config_dir / "config.json"
    assert json.loads((config_dir / "config.json").read_text()) == json.loads(TEMPLATE.read_text())


def test_missing_config_is_restored_from_the_backup(config_dir):
    (config_dir / "config_backup.json").write_text(json.dumps({"from": "backup"}))

    service = ConfigService(threading.Lock())

    assert service.config == {"from": "backup"}


def test_save_config_writes_inside_the_config_dir(config_dir):
    service = ConfigService(threading.Lock())

    service.save_config({"saved": True})

    assert json.loads((config_dir / "config.json").read_text()) == {"saved": True}
    assert (config_dir / "config_backup.json").exists()


def test_missing_config_dir_is_created(config_dir, monkeypatch):
    nested = config_dir / "a" / "b"
    monkeypatch.setenv("MLSC_CONFIG_DIR", str(nested))

    ConfigService(threading.Lock())

    assert (nested / "config.json").exists()
