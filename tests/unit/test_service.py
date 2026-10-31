from pathlib import Path

import pytest

from mlsc import paths, service
from mlsc.service import ServiceError, ServiceManager, render_unit

pytestmark = pytest.mark.unit


class FakeHost:
    def __init__(self, systemd=True, fail=()) -> None:
        self.systemd = systemd
        self.fail = fail
        self.commands = []

    def which(self, command):
        return f"/usr/bin/{command}" if self.systemd else None

    def run(self, command, timeout=5):  # ruff: ignore[unused-method-argument] Matches Host.run.
        self.commands.append(command[1:])
        return (1, "boom") if command[1] in self.fail else (0, "ok")


@pytest.fixture
def manager(tmp_path):
    host = FakeHost()
    return ServiceManager(
        host,
        unit_path=tmp_path / "mlsc.service",
        config_dir=lambda: tmp_path / "cfg",
        exec_start=["/venv/bin/python", "-m", "mlsc", "run"],
        is_root=lambda: True,
    )


def test_unit_hardens_and_pins_the_config_dir():
    config_dir = Path("/home/pi/.config/mlsc")
    unit = render_unit(["/opt/my venv/bin/python", "-m", "mlsc", "run"], config_dir)

    assert "User=root" in unit
    assert "ProtectHome=read-only" in unit
    assert "NoNewPrivileges=true" in unit
    assert f"ReadWritePaths={config_dir}" in unit
    assert f"Environment={paths.CONFIG_DIR_ENV}={config_dir}" in unit
    assert "ExecStart='/opt/my venv/bin/python' -m mlsc run" in unit


def test_install_writes_the_unit_and_starts_the_service(manager, tmp_path):
    lines = manager.install()

    assert "ExecStart=/venv/bin/python -m mlsc run" in manager.unit_path.read_text()
    assert (tmp_path / "cfg").is_dir()
    assert manager.host.commands == [["daemon-reload"], ["enable", "mlsc.service"], ["restart", "mlsc.service"]]
    assert "Installed" in lines[-1]


def test_install_replaces_an_old_2x_unit(manager):
    manager.unit_path.write_text("[Service]\nExecStart=/share/.venv/bin/python run.py\n")

    lines = manager.install()

    assert "from MLSC 2.x" in lines[0]
    assert ["stop", "mlsc.service"] in manager.host.commands
    assert service.MANAGED_MARKER in manager.unit_path.read_text()


def test_reinstall_does_not_call_the_unit_a_2x_one(manager):
    manager.install()

    assert "2.x" not in manager.install()[0]


def test_install_needs_root(manager):
    manager.is_root = lambda: False

    with pytest.raises(ServiceError, match="needs root"):
        manager.install()
    assert not manager.unit_path.exists()


def test_actions_need_systemd(manager):
    manager.host = FakeHost(systemd=False)

    with pytest.raises(ServiceError, match="systemd was not found"):
        manager.status()


def test_install_reports_a_failing_systemctl(manager):
    manager.host = FakeHost(fail=("enable",))

    with pytest.raises(ServiceError, match="enable"):
        manager.install()


def test_uninstall_removes_the_unit_but_not_the_config(manager, tmp_path):
    manager.install()

    manager.uninstall()

    assert not manager.unit_path.exists()
    assert (tmp_path / "cfg").is_dir()
    assert ["disable", "mlsc.service"] in manager.host.commands


def test_uninstall_without_unit_is_a_noop(manager):
    assert "not installed" in manager.uninstall()[0]
    assert manager.host.commands == []


def test_restart_and_status(manager):
    manager.restart()
    code, output = manager.status()

    assert manager.host.commands == [["restart", "mlsc.service"], ["status", "mlsc.service", "--no-pager"]]
    assert (code, output) == (0, "ok")


def test_config_dir_follows_the_override(monkeypatch, tmp_path):
    monkeypatch.setenv(paths.CONFIG_DIR_ENV, str(tmp_path))

    assert service.installing_user_config_dir({paths.CONFIG_DIR_ENV: str(tmp_path), "SUDO_USER": "pi"}) == tmp_path.resolve()


def test_config_dir_of_the_sudo_user(monkeypatch):
    pwd = pytest.importorskip("pwd")
    monkeypatch.setattr(pwd, "getpwnam", lambda name: type("E", (), {"pw_dir": f"/home/{name}"})())

    assert service.installing_user_config_dir({"SUDO_USER": "pi"}) == Path("/home/pi/.config/mlsc")
    assert service.installing_user_config_dir({"SUDO_USER": "pi", "XDG_CONFIG_HOME": "/x"}) == Path("/x/mlsc")
