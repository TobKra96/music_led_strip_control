import pytest

from mlsc import __version__, cli, paths

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv(paths.CONFIG_DIR_ENV, raising=False)


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


def test_config_dir_flag_sets_the_override(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "run_server", lambda: 0)

    cli.main(["--config-dir", str(tmp_path), "run"])

    assert paths.config_dir() == tmp_path.resolve()
    monkeypatch.delenv(paths.CONFIG_DIR_ENV)


def test_config_path_prints_the_config_file(capsys, tmp_path, monkeypatch):
    assert cli.main(["--config-dir", str(tmp_path), "config", "path"]) == 0

    assert capsys.readouterr().out.strip() == str(tmp_path.resolve() / "config.json")
    monkeypatch.delenv(paths.CONFIG_DIR_ENV)


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
