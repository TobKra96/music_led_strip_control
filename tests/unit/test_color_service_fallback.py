import json
from importlib import resources

import numpy as np
import pytest
from loguru import logger

from mlsc.color_service import ColorService
from mlsc.color_service_global import ColorServiceGlobal

pytestmark = pytest.mark.unit


@pytest.fixture
def config():
    config = json.loads((resources.files("mlsc") / "config_template.json").read_text())
    config["gradients"]["mine"] = [[0, 0, 0], [255, 255, 255]]
    return config


@pytest.fixture
def service(config):
    service = ColorService(config, config["default_device"])
    service.build_gradients()
    service.build_fadegradients()
    service.build_slidearrays()
    return service


@pytest.fixture
def warnings():
    messages = []
    handler = logger.add(lambda message: messages.append(message.record["message"]), level="WARNING")
    yield messages
    logger.remove(handler)


def test_known_colour_is_returned(config, service):
    assert service.colour("blue") == config["colors"]["blue"]


def test_missing_colour_falls_back_to_red_and_warns(config, service, warnings):
    assert service.colour("ghost") == config["colors"]["red"]
    assert any("ghost" in message for message in warnings)


def test_missing_colour_warns_once_per_name(service, warnings):
    for _ in range(5):
        service.colour("ghost")

    assert len([message for message in warnings if "ghost" in message]) == 1


@pytest.mark.parametrize("table", ["full_gradients", "full_fadegradients", "full_slide"])
def test_missing_gradient_falls_back_to_spectral_and_warns(service, warnings, table):
    entries = getattr(service, table)

    np.testing.assert_array_equal(entries["ghost"], entries["spectral"])
    assert any("ghost" in message for message in warnings)


def test_missing_gradient_keeps_its_own_roll_state(service):
    service.full_gradients["ghost"] = np.roll(service.full_gradients["ghost"], 3, axis=1)

    np.testing.assert_array_equal(service.full_gradients["ghost"], np.roll(service.full_gradients["spectral"], 3, axis=1))
    np.testing.assert_array_equal(service.full_gradients["spectral"], service.full_gradients["spectral"])


def test_stored_value_is_left_untouched(config, service):
    config["device_configs"] = {"device_0": config["default_device"]}
    config["default_device"]["effects"]["effect_gradient"]["gradient"] = "ghost"

    service.full_gradients["ghost"]

    assert config["default_device"]["effects"]["effect_gradient"]["gradient"] == "ghost"


def test_global_service_falls_back_the_same_way(config, warnings):
    service = ColorServiceGlobal(config)

    assert service.colour("ghost") == config["colors"]["red"]
    np.testing.assert_array_equal(service.full_gradients["ghost"], service.full_gradients["spectral"])
    assert any("ghost" in message for message in warnings)
