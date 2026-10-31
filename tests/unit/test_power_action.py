import pytest

from mlsc import host as host_module
from mlsc.host import Host

pytestmark = pytest.mark.unit


class SystemdHost(Host):
    def __init__(self, systemctl=True) -> None:
        super().__init__(boot_configs=())
        self.systemctl = systemctl

    def which(self, command):
        return f"/usr/bin/{command}" if self.systemctl else None


@pytest.fixture
def linux_root(monkeypatch):
    monkeypatch.setattr(host_module.sys, "platform", "linux")
    monkeypatch.setattr(host_module.os, "geteuid", lambda: 0, raising=False)


@pytest.mark.usefixtures("linux_root")
@pytest.mark.parametrize("action", ["reboot", "shutdown"])
def test_power_action_is_runnable_as_root_on_linux_with_systemctl(action):
    assert SystemdHost().power_action_block(action) is None


@pytest.mark.usefixtures("linux_root")
def test_power_action_is_blocked_off_linux(monkeypatch):
    monkeypatch.setattr(host_module.sys, "platform", "win32")

    assert SystemdHost().power_action_block("reboot") == "Rebooting and shutting down are only possible on Linux."


@pytest.mark.usefixtures("linux_root")
def test_power_action_is_blocked_without_systemctl():
    assert SystemdHost(systemctl=False).power_action_block("shutdown") == "`systemctl` was not found on this system."


@pytest.mark.usefixtures("linux_root")
def test_power_action_is_blocked_when_not_root(monkeypatch):
    monkeypatch.setattr(host_module.os, "geteuid", lambda: 1000, raising=False)

    assert SystemdHost().power_action_block("reboot") == "MLSC must run as root to reboot or shut down the machine."
