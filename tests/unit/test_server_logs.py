import json

import pytest

from mlsc import host as host_module
from mlsc.host import Host
from mlsc.server_logs import filter_entries, parse_entries

pytestmark = pytest.mark.unit

GREEN = "\x1b[32m"
RESET = "\x1b[0m"


def journal(*messages, base=1_798_804_800_000_000):
    return "\n".join(json.dumps({"__REALTIME_TIMESTAMP": str(base + i * 1_000_000), "MESSAGE": m}) for i, m in enumerate(messages))


def line(level, message, source="mlsc.main:run:42"):
    return f"2026-11-01 12:00:00.123 | {level: <8} | {source} - {message}"


def test_parses_a_loguru_line_into_its_parts():
    [entry] = parse_entries(journal(line("INFO", "Started")))

    assert entry == {"time": "2027-01-01T12:00:00.000Z", "level": "info", "source": "mlsc.main:run:42", "message": "Started"}


def test_strips_ansi_colour_codes():
    source = f"{GREEN}mlsc.a{RESET}:{GREEN}f{RESET}:{GREEN}1{RESET}"
    colored = f"{GREEN}2026-11-01 12:00:00.123{RESET} | \x1b[1mWARNING \x1b[0m | {source} - \x1b[1mCareful{RESET}"

    [entry] = parse_entries(journal(colored))

    assert (entry["level"], entry["source"], entry["message"]) == ("warning", "mlsc.a:f:1", "Careful")


def test_message_as_byte_array_is_decoded():
    [entry] = parse_entries(journal(list(line("ERROR", "Bröken").encode())))

    assert (entry["level"], entry["message"]) == ("error", "Bröken")


def test_null_message_is_an_empty_line():
    [entry] = parse_entries(journal(None))

    assert not entry["message"]
    assert entry["level"] is None


def test_continuation_lines_inherit_the_previous_level():
    entries = parse_entries(journal(line("ERROR", "Boom"), "Traceback (most recent call last):", '  File "x.py", line 1', "ValueError: no"))

    assert [e["level"] for e in entries] == ["error"] * 4
    assert [e["source"] for e in entries[1:]] == [None] * 3


def test_non_loguru_line_without_a_predecessor_has_no_level():
    [entry] = parse_entries(journal("print() from a library"))

    assert (entry["level"], entry["source"], entry["message"]) == (None, None, "print() from a library")


def test_ignores_lines_that_are_not_json():
    entries = parse_entries("-- No entries --\n" + journal(line("INFO", "ok")))

    assert len(entries) == 1


def entries_of(*pairs):
    return [{"time": None, "level": lvl, "source": None, "message": msg} for lvl, msg in pairs]


def test_level_is_a_minimum_severity():
    entries = entries_of(("debug", "a"), ("info", "b"), ("warning", "c"), ("error", "d"))

    assert [e["message"] for e in filter_entries(entries, 10, level="warning")] == ["c", "d"]


def test_null_level_entries_are_excluded_when_a_level_is_set():
    entries = entries_of((None, "stray"), ("info", "b"))

    assert [e["message"] for e in filter_entries(entries, 10, level="info")] == ["b"]
    assert len(filter_entries(entries, 10)) == 2


def test_text_filter_is_a_case_insensitive_substring_on_the_message():
    entries = entries_of(("info", "Wi-Fi connected"), ("info", "audio started"))

    assert [e["message"] for e in filter_entries(entries, 10, query="WI-fi")] == ["Wi-Fi connected"]


def test_lines_keeps_the_newest_matches_oldest_first():
    entries = entries_of(*[("info", str(i)) for i in range(10)])

    assert [e["message"] for e in filter_entries(entries, 3)] == ["7", "8", "9"]


class JournalHost(Host):
    def __init__(self, journalctl=True) -> None:
        super().__init__(boot_configs=())
        self.journalctl = journalctl

    def which(self, command):
        return f"/usr/bin/{command}" if self.journalctl else None


@pytest.fixture
def service_as_root(monkeypatch):
    monkeypatch.setattr(host_module.sys, "platform", "linux")
    monkeypatch.setattr(host_module.os, "geteuid", lambda: 0, raising=False)
    monkeypatch.setenv("INVOCATION_ID", "abc")
    monkeypatch.delenv("JOURNAL_STREAM", raising=False)


@pytest.mark.usefixtures("service_as_root")
def test_logs_are_available_as_the_root_service_on_linux():
    assert JournalHost().server_logs_unavailable() is None


@pytest.mark.usefixtures("service_as_root")
def test_logs_are_unavailable_off_linux(monkeypatch):
    monkeypatch.setattr(host_module.sys, "platform", "win32")

    assert "Linux" in JournalHost().server_logs_unavailable()


@pytest.mark.usefixtures("service_as_root")
def test_logs_are_unavailable_without_journalctl():
    assert "journalctl" in JournalHost(journalctl=False).server_logs_unavailable()


@pytest.mark.usefixtures("service_as_root")
def test_logs_are_unavailable_outside_the_service(monkeypatch):
    monkeypatch.delenv("INVOCATION_ID")

    assert "service" in JournalHost().server_logs_unavailable()


@pytest.mark.usefixtures("service_as_root")
def test_journal_stream_alone_counts_as_the_service(monkeypatch):
    monkeypatch.delenv("INVOCATION_ID")
    monkeypatch.setenv("JOURNAL_STREAM", "8:1")

    assert JournalHost().server_logs_unavailable() is None


@pytest.mark.usefixtures("service_as_root")
def test_logs_are_unavailable_when_not_root(monkeypatch):
    monkeypatch.setattr(host_module.os, "geteuid", lambda: 1000, raising=False)

    assert "root" in JournalHost().server_logs_unavailable()


def test_journal_is_persistent_when_its_directory_exists(monkeypatch, tmp_path):
    monkeypatch.setattr(host_module, "JOURNAL_DIR", tmp_path)
    assert Host().journal_is_persistent() is True

    monkeypatch.setattr(host_module, "JOURNAL_DIR", tmp_path / "missing")
    assert Host().journal_is_persistent() is False
