import pytest

from mlsc import paths

pytestmark = [pytest.mark.unit, pytest.mark.usefixtures("clean_config_env")]


def test_env_override_wins(monkeypatch, tmp_path):
    monkeypatch.setenv(paths.CONFIG_DIR_ENV, str(tmp_path))

    assert paths.config_dir() == tmp_path.resolve()
    assert paths.data_dir() == tmp_path.resolve()


def test_default_uses_platform_dirs():
    assert paths.config_dir().name == paths.APP_NAME
    assert paths.data_dir().name == paths.APP_NAME


def test_set_config_dir_is_visible_through_the_environment(tmp_path):
    paths.set_config_dir(tmp_path / "cfg")

    assert paths.config_dir() == (tmp_path / "cfg").resolve()
