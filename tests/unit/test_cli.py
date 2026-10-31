import pytest

from mlsc import __version__, cli, paths

pytestmark = [pytest.mark.unit, pytest.mark.usefixtures("clean_config_env")]


def test_no_arguments_runs_the_server(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "run_server", lambda: calls.append("run") or 0)

    assert cli.main([]) == 0
    assert calls == ["run"]


def test_run_subcommand_runs_the_server(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "run_server", lambda: calls.append("run") or 0)

    assert cli.main(["run"]) == 0
    assert calls == ["run"]


@pytest.mark.parametrize("position", ["before", "after"])
def test_config_dir_flag_works_before_and_after_the_subcommand(monkeypatch, tmp_path, position):
    monkeypatch.setattr(cli, "run_server", lambda: 0)
    flag = ["--config-dir", str(tmp_path)]

    cli.main([*flag, "run"] if position == "before" else ["run", *flag])

    assert paths.config_dir() == tmp_path.resolve()


def test_config_dir_flag_works_after_a_nested_subcommand(tmp_path):
    assert cli.main(["config", "path", "--config-dir", str(tmp_path)]) == 0

    assert paths.config_dir() == tmp_path.resolve()


def test_config_path_prints_the_config_file(capsys, tmp_path):
    assert cli.main(["--config-dir", str(tmp_path), "config", "path"]) == 0

    assert capsys.readouterr().out.strip() == str(tmp_path.resolve() / "config.json")


def test_service_subcommand_reports_errors_without_systemd(capsys, monkeypatch):
    monkeypatch.setattr("mlsc.host.Host.which", lambda *_: None)

    assert cli.main(["service", "restart"]) == 1
    assert "systemd was not found" in capsys.readouterr().err


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])

    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_service_status_prints_systemctl_output_and_its_exit_code(capsys, monkeypatch):
    monkeypatch.setattr("mlsc.host.Host.which", lambda *_: "/usr/bin/systemctl")
    monkeypatch.setattr("mlsc.host.Host.run", lambda *_, **__: (3, "inactive"))

    assert cli.main(["service", "status"]) == 3
    assert capsys.readouterr().out.strip() == "inactive"


def test_service_restart_reports_success(capsys, monkeypatch):
    monkeypatch.setattr("mlsc.host.Host.which", lambda *_: "/usr/bin/systemctl")
    monkeypatch.setattr("mlsc.host.Host.run", lambda *_, **__: (0, ""))
    monkeypatch.setattr("mlsc.service.running_as_root", lambda: True)

    assert cli.main(["service", "restart"]) == 0
    assert "Restarted" in capsys.readouterr().out
