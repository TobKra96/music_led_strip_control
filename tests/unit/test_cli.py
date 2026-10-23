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


@pytest.mark.parametrize(
    "argv",
    [
        ["service", "install"],
        ["service", "uninstall"],
        ["service", "status"],
        ["service", "restart"],
        ["doctor"],
        ["config", "migrate"],
    ],
)
def test_stub_subcommands_report_not_implemented(argv, capsys):
    assert cli.main(argv) == 1
    assert "not implemented" in capsys.readouterr().err


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])

    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out
