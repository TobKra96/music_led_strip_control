import pytest

from mlsc import paths
from mlsc.outputs.output_mock import OutputMock


@pytest.fixture
def clean_config_env(monkeypatch):
    """Start without a config dir override and restore the environment afterwards, even if the test sets it directly."""
    # setenv first so monkeypatch records the original state and removes any value the test sets.
    monkeypatch.setenv(paths.CONFIG_DIR_ENV, "")
    monkeypatch.delenv(paths.CONFIG_DIR_ENV)


@pytest.fixture
def config_dir(clean_config_env, tmp_path):  # ruff: ignore[unused-function-argument]
    """Point MLSC at a temporary config dir."""
    paths.set_config_dir(tmp_path)
    return tmp_path.resolve()


class FakeClock:
    """Deterministic stand-in for ``time.time``/``time.sleep``: sleeping advances the clock instead of waiting."""

    def __init__(self, start=1_000.0) -> None:
        self.now = start
        self.sleeps = []

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.advance(seconds)

    def advance(self, seconds):
        self.now += seconds

    def patch(self, monkeypatch, module):
        """Replace ``time``/``sleep`` imported by name into ``module``; fails if the module does not have them."""
        for name in ("time", "sleep"):
            monkeypatch.setattr(module, name, getattr(self, name))


@pytest.fixture
def fake_clock():
    """Injectable clock so timer tests (rollbacks, fallbacks) never sleep for real."""
    return FakeClock()


class FakeDevice:
    """Minimal device exposing what ``Output`` reads from the real ``Device``."""

    def __init__(self, device_config=None) -> None:
        self.device_config = device_config if device_config is not None else {}


@pytest.fixture
def fake_device():
    return FakeDevice()


class RecordingOutput(OutputMock):
    """Mock Output that records every frame it is asked to show."""

    def __init__(self, device) -> None:
        super().__init__(device)
        self.frames = []

    def show(self, output_array):
        self.frames.append(output_array)


@pytest.fixture
def mock_output(fake_device):
    """Provide a Mock Output on a fake device; ``mock_output.frames`` holds the shown frames."""
    return RecordingOutput(fake_device)


def pytest_collection_modifyitems(items):
    """Mark tests by the directory they live in, so ``-m unit`` and ``-m integration`` select layers."""
    for item in items:
        for layer in ("unit", "integration", "contract"):
            if f"/tests/{layer}/" in item.path.as_posix():
                item.add_marker(layer)
