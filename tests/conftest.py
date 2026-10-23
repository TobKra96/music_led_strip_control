import pytest

from mlsc import paths


@pytest.fixture
def clean_config_env(monkeypatch):
    """Start without a config dir override and restore the environment afterwards, even if the test sets it directly."""
    # setenv first so monkeypatch records the original state and removes any value the test sets.
    monkeypatch.setenv(paths.CONFIG_DIR_ENV, "")
    monkeypatch.delenv(paths.CONFIG_DIR_ENV)


@pytest.fixture
def config_dir(clean_config_env, tmp_path):  # noqa: ARG001
    """Point MLSC at a temporary config dir."""
    paths.set_config_dir(tmp_path)
    return tmp_path.resolve()
