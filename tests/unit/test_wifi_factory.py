import pytest

from mlsc.wifi import MockWifiManager
from mlsc.wifi.factory import BACKEND_ENV_VAR, create_wifi_manager
from mlsc.wifi.nmcli import NmcliWifiManager

pytestmark = pytest.mark.unit


class FakeHost:
    def __init__(self, nmcli_path) -> None:
        self.nmcli_path = nmcli_path

    def which(self, command):
        return self.nmcli_path if command == "nmcli" else None

    def run(self, command, timeout=None):  # ruff: ignore[no-self-use, unused-method-argument]
        return 0, ""


def test_auto_uses_nmcli_on_linux_when_it_is_installed():
    assert isinstance(create_wifi_manager("auto", FakeHost("/usr/bin/nmcli"), platform="linux"), NmcliWifiManager)


@pytest.mark.parametrize(("nmcli_path", "platform"), [(None, "linux"), ("C:/nmcli.exe", "win32")])
def test_auto_is_an_unsupported_manager_without_networkmanager(nmcli_path, platform):
    manager = create_wifi_manager("auto", FakeHost(nmcli_path), platform=platform)

    assert isinstance(manager, MockWifiManager)
    assert manager.capabilities().supported is False


def test_mock_is_selectable_for_ui_development():
    manager = create_wifi_manager("mock", FakeHost(None), platform="win32")

    assert manager.capabilities().supported is True
    assert manager.scan()


def test_the_backend_defaults_to_the_environment(monkeypatch):
    monkeypatch.setenv(BACKEND_ENV_VAR, "mock")

    assert create_wifi_manager(host=FakeHost(None), platform="win32").capabilities().supported is True
