import pytest

from mlsc import host as host_module
from mlsc.host import Host

pytestmark = pytest.mark.unit


class SystemdHost(Host):
    def __init__(self, result=(0, "enabled"), systemctl=True) -> None:
        super().__init__(boot_configs=())
        self.result = result
        self.systemctl = systemctl
        self.commands = []

    def which(self, command):
        return f"/usr/bin/{command}" if self.systemctl else None

    def run(self, command, timeout=None):  # ruff: ignore[unused-method-argument]
        self.commands.append(command)
        return self.result


@pytest.fixture(autouse=True)
def linux(monkeypatch):
    monkeypatch.setattr(host_module.sys, "platform", "linux")


def test_an_enabled_service_has_no_warning():
    host = SystemdHost()

    assert host.autostart_warning() is None
    assert host.commands == [["systemctl", "is-enabled", "mlsc.service"]]


@pytest.mark.parametrize("result", [(1, "disabled"), (1, "masked"), (0, "enabled-runtime"), (1, "")])
def test_a_service_that_is_not_enabled_warns(result):
    warning = SystemdHost(result).autostart_warning()

    assert "not enabled" in warning
    assert "systemctl enable mlsc.service" in warning


@pytest.mark.parametrize("result", [(4, "Failed to get unit file state for mlsc.service: No such file or directory"), (1, "not-found")])
def test_a_missing_service_warns_that_it_is_not_installed(result):
    warning = SystemdHost(result).autostart_warning()

    assert "not installed" in warning
    assert "mlsc service install" in warning


def test_no_warning_where_there_is_no_systemd(monkeypatch):
    assert SystemdHost(systemctl=False).autostart_warning() is None
    monkeypatch.setattr(host_module.sys, "platform", "win32")
    assert SystemdHost().autostart_warning() is None


def test_no_warning_when_systemctl_cannot_answer():
    assert SystemdHost((124, "systemctl timed out")).autostart_warning() is None
