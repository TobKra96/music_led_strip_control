from types import SimpleNamespace

import pytest

from mlsc.webserver.blueprints.device_executer import DeviceExecuter
from mlsc.webserver.messages import DeviceNotFound

pytestmark = pytest.mark.unit


def make_executer():
    executer = DeviceExecuter.__new__(DeviceExecuter)
    config = {"device_configs": {"device_0": {"device_name": "Desk", "device_groups": {"group_0": "Room"}}}}
    executer._config_instance = SimpleNamespace(config=config)  # ruff: ignore[private-member-access]
    return executer


def test_get_device_returns_the_same_view_as_the_device_list():
    executer = make_executer()

    assert executer.get_device("device_0") == {"name": "Desk", "id": "device_0", "assigned_to": {"group_0": "Room"}}
    assert executer.get_devices() == [executer.get_device("device_0")]


def test_get_device_reports_an_unknown_id_as_device_not_found():
    assert make_executer().get_device("device_9") is DeviceNotFound
