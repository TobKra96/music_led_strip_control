import json
from types import SimpleNamespace

import pytest

from mlsc.api.v2 import register_api_v2
from mlsc.app import create_app
from mlsc.webserver.executer import Executer

pytestmark = pytest.mark.integration


def journal_line(level, message, n=0):
    text = f"2026-11-01 12:00:00.123 | {level: <8} | mlsc.main:run:42 - {message}"
    return json.dumps({"__REALTIME_TIMESTAMP": str(1_798_804_800_000_000 + n), "MESSAGE": text})


class FakeHost:
    def __init__(self, unavailable=None, persistent=True, result=(0, "")) -> None:
        self.unavailable = unavailable
        self.persistent = persistent
        self.result = result
        self.commands = []

    def server_logs_unavailable(self):
        return self.unavailable

    def journal_is_persistent(self):
        return self.persistent

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


def test_returns_parsed_entries_from_the_journal(monkeypatch):
    host = FakeHost(result=(0, journal_line("INFO", "Started")))
    client = make_client(host, monkeypatch)

    body = client.get("/api/v2/system/logs").get_json()

    assert body == {"unavailable": None, "persistent": True, "entries": [
        {"time": "2027-01-01T12:00:00.000Z", "level": "info", "source": "mlsc.main:run:42", "message": "Started"}]}
    assert host.commands[0][:2] == ["journalctl", "-u"]


def test_applies_level_text_and_lines(monkeypatch):
    output = "\n".join(journal_line(lvl, msg, i) for i, (lvl, msg) in enumerate(
        [("DEBUG", "noise"), ("INFO", "Wifi up"), ("WARNING", "Wifi slow"), ("ERROR", "Wifi down"), ("ERROR", "other")]))
    client = make_client(FakeHost(result=(0, output)), monkeypatch)

    body = client.get("/api/v2/system/logs?level=warning&q=WIFI&lines=1").get_json()

    assert [e["message"] for e in body["entries"]] == ["Wifi down"]


def test_unavailable_is_a_200_with_no_entries(monkeypatch):
    host = FakeHost(unavailable="Server logs are only available on Linux.")
    client = make_client(host, monkeypatch)

    response = client.get("/api/v2/system/logs")

    assert response.status_code == 200
    assert response.get_json() == {"unavailable": "Server logs are only available on Linux.", "persistent": None, "entries": []}
    assert host.commands == []


def test_reports_a_volatile_journal(monkeypatch):
    client = make_client(FakeHost(persistent=False), monkeypatch)

    assert client.get("/api/v2/system/logs").get_json()["persistent"] is False


@pytest.mark.parametrize("query", ["lines=0", "lines=1001", "lines=x", "level=loud", "level=INFO", "q=" + "a" * 201])
def test_rejects_invalid_parameters(monkeypatch, query):
    client = make_client(FakeHost(), monkeypatch)

    assert client.get(f"/api/v2/system/logs?{query}").status_code == 422


def test_journalctl_failure_is_a_server_error(monkeypatch):
    client = make_client(FakeHost(result=(1, "Failed to open journal")), monkeypatch)

    response = client.get("/api/v2/system/logs")

    assert response.status_code == 500
    assert "Failed to open journal" in response.get_data(as_text=True)


def test_timeout_is_a_server_error(monkeypatch):
    client = make_client(FakeHost(result=(124, "journalctl timed out")), monkeypatch)

    assert client.get("/api/v2/system/logs").status_code == 500


def test_requires_login_when_auth_is_enabled(monkeypatch):
    client = make_client(FakeHost(), monkeypatch, auth_enabled=True)

    assert client.get("/api/v2/system/logs").status_code == 401
