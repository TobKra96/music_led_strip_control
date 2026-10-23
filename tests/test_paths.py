from pathlib import Path

import pytest

from mlsc import paths

pytestmark = pytest.mark.unit


def test_env_override_wins(monkeypatch, tmp_path):
    monkeypatch.setenv(paths.CONFIG_DIR_ENV, str(tmp_path))

    assert paths.config_dir() == tmp_path.resolve()
    assert paths.data_dir() == tmp_path.resolve()


def test_default_uses_platform_dirs(monkeypatch):
    monkeypatch.delenv(paths.CONFIG_DIR_ENV, raising=False)

    assert paths.config_dir().name == paths.APP_NAME
    assert paths.data_dir().name == paths.APP_NAME


def test_set_config_dir_is_visible_to_children(monkeypatch, tmp_path):
    monkeypatch.delenv(paths.CONFIG_DIR_ENV, raising=False)

    paths.set_config_dir(tmp_path / "cfg")

    assert Path(paths.config_dir()) == (tmp_path / "cfg").resolve()
    monkeypatch.delenv(paths.CONFIG_DIR_ENV)
