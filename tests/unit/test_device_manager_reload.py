import json
from importlib import resources

import pytest

from mlsc import device_manager as device_manager_module
from mlsc.color_service_global import ColorServiceGlobal
from mlsc.device_manager import DeviceManager

pytestmark = pytest.mark.unit


class _ConfigService:
    def __init__(self, config) -> None:
        self.config = config
        self.loaded = None

    def load_config(self):
        self.config = self.loaded


@pytest.fixture
def template():
    return json.loads((resources.files("mlsc") / "config_template.json").read_text())


@pytest.fixture
def manager(monkeypatch, template):
    service = _ConfigService(template)
    monkeypatch.setattr(device_manager_module.ConfigService, "instance", staticmethod(lambda _lock: service))
    manager = DeviceManager()
    manager._config_lock = None  # ruff: ignore[private-member-access]
    manager._config = template  # ruff: ignore[private-member-access]
    manager._color_service_global = ColorServiceGlobal(template)  # ruff: ignore[private-member-access]
    manager.service = service
    return manager


def test_reload_config_rebuilds_the_global_colours_and_gradients(manager, template):
    edited = json.loads(json.dumps(template))
    edited["colors"]["mine"] = [1, 2, 3]
    edited["gradients"]["mine"] = [[0, 0, 0], [255, 255, 255]]
    manager.service.loaded = edited

    manager.reload_config()

    assert manager._color_service_global.colour("mine") == [1, 2, 3]  # ruff: ignore[private-member-access]
    assert "mine" in manager._color_service_global.full_gradients  # ruff: ignore[private-member-access]
