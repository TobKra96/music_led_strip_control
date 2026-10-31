from types import SimpleNamespace

import pytest

from mlsc.api.v2 import register_api_v2
from mlsc.app import create_app
from mlsc.webserver.executer import Executer

pytestmark = pytest.mark.integration

BLOCK = "MLSC must run as root to reboot or shut down the machine."


class FakeHost:
    def __init__(self, block=None, result=(0, "")) -> None:
        self.block = block
        self.result = result
        self.commands = []

    def power_action_block(self, action):  # ruff: ignore[unused-method-argument]
        return self.block

    def run(self, command, timeout=None):  # ruff: ignore[unused-method-argument]
        self.commands.append(command)
        return self.result


def make_client(host, monkeypatch, *, auth_enabled=False):
    monkeypatch.setattr(Executer, "instance", SimpleNamespace(host=host), raising=False)
    app = create_app()
    app.config["AUTH_ENABLED"] = auth_enabled
    app.secret_key = "test"  # ruff: ignore[hardcoded-password-string]
    register_api_v2(app)
    return app.test_client()


def test_power_reports_each_action_as_available_when_nothing_blocks_it(monkeypatch):
    client = make_client(FakeHost(), monkeypatch)

    assert client.get("/api/v2/system/power").get_json() == {
        "reboot": {"available": True, "reason": None}, "shutdown": {"available": True, "reason": None},
    }


def test_power_reports_the_reason_when_blocked(monkeypatch):
    client = make_client(FakeHost(block=BLOCK), monkeypatch)

    assert client.get("/api/v2/system/power").get_json()["reboot"] == {"available": False, "reason": BLOCK}


@pytest.mark.parametrize(("action", "verb"), [("reboot", "reboot"), ("shutdown", "poweroff")])
def test_action_runs_systemctl_without_blocking_and_is_accepted(monkeypatch, action, verb):
    host = FakeHost()
    client = make_client(host, monkeypatch)

    response = client.post(f"/api/v2/system/{action}", json={})

    assert response.status_code == 202
    assert response.get_json() == {"action": action, "status": "accepted"}
    assert host.commands == [["systemctl", verb, "--no-block"]]


def test_blocked_action_is_a_conflict_and_runs_nothing(monkeypatch):
    host = FakeHost(block=BLOCK)
    client = make_client(host, monkeypatch)

    response = client.post("/api/v2/system/reboot", json={})

    assert response.status_code == 409
    assert response.mimetype == "application/problem+json"
    assert response.get_json()["code"] == "PowerActionBlocked"
    assert response.get_json()["detail"] == BLOCK
    assert host.commands == []


def test_failing_command_is_a_server_error_with_its_output(monkeypatch):
    client = make_client(FakeHost(result=(1, "Failed to connect to bus")), monkeypatch)

    response = client.post("/api/v2/system/shutdown", json={})

    assert response.status_code == 500
    assert response.get_json()["code"] == "ServerError"
    assert response.get_json()["detail"] == "Failed to connect to bus"


@pytest.mark.parametrize(("method", "path"), [("get", "power"), ("post", "reboot"), ("post", "shutdown")])
def test_power_endpoints_require_login(monkeypatch, method, path):
    host = FakeHost()
    client = make_client(host, monkeypatch, auth_enabled=True)

    response = getattr(client, method)(f"/api/v2/system/{path}", **({"json": {}} if method == "post" else {}))

    assert response.status_code == 401
    assert host.commands == []
