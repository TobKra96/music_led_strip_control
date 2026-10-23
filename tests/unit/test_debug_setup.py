import json
import re
import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
DEBUGPY_PORT = 5678


def _launch_configurations():
    # launch.json is JSONC; strip whole-line comments before parsing.
    text = (ROOT / ".vscode" / "launch.json").read_text(encoding="utf-8")
    return {c["name"]: c for c in json.loads(re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE))["configurations"]}


def test_launch_config_runs_the_server_under_the_debugger_with_child_processes():
    config = _launch_configurations()["MLSC: run"]

    assert config["module"] == "mlsc"
    assert config["args"] == ["run"]
    assert config["subProcess"] is True


def test_launch_config_can_attach_to_a_server_started_with_debugpy():
    config = _launch_configurations()["MLSC: attach (debugpy)"]

    assert config["request"] == "attach"
    assert config["connect"]["port"] == DEBUGPY_PORT
    assert config["subProcess"] is True


def test_debugpy_is_a_dev_dependency():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert any(dep.startswith("debugpy") for dep in pyproject["dependency-groups"]["dev"])


def test_vscode_launch_config_is_not_git_ignored():
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert "!.vscode/launch.json" in ignored
