"""Read the Server Logs: what MLSC wrote to the systemd journal during the current boot."""
from __future__ import annotations

import json
import re
from datetime import UTC, datetime

JOURNAL_ENTRY_LIMIT = 2000
LEVELS = ("trace", "debug", "info", "success", "warning", "error", "critical")
LEVEL_RANK = {level: rank for rank, level in enumerate(LEVELS)}

ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
# `2026-11-01 12:00:00.123 | INFO     | mlsc.main:run:42 - message`
LOGURU_LINE = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+) \| (\w+)\s*\| (\S+) - (.*)$", re.DOTALL)


def journal_command(unit: str = "mlsc") -> list[str]:
    return ["journalctl", "-u", unit, "-b", "-o", "json", "-n", str(JOURNAL_ENTRY_LIMIT), "--no-pager"]


def _message_text(value: object) -> str:
    """`MESSAGE` is a string, `null`, or an array of byte values when the journal holds non-UTF-8 or binary data."""
    if value is None:
        return ""
    if isinstance(value, list):
        return bytes(b for b in value if isinstance(b, int) and 0 <= b < 256).decode("utf-8", errors="replace")
    return str(value)


def _iso_time(entry: dict) -> str | None:
    try:
        return datetime.fromtimestamp(int(entry["__REALTIME_TIMESTAMP"]) / 1_000_000, tz=UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    except (KeyError, ValueError, TypeError, OverflowError, OSError):
        return None


def parse_entries(journal_output: str) -> list[dict]:
    """Turn `journalctl -o json` output into entries, oldest first. Lines that are not Loguru lines inherit the previous level."""
    entries: list[dict] = []
    previous_level: str | None = None
    for raw in journal_output.splitlines():
        try:
            record = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(record, dict):
            continue
        text = ANSI.sub("", _message_text(record.get("MESSAGE"))).rstrip("\r\n")
        match = LOGURU_LINE.match(text)
        if match:
            level, source, message = match.group(2).lower(), match.group(3), match.group(4)
        else:
            level, source, message = previous_level, None, text
        previous_level = level
        entries.append({"time": _iso_time(record), "level": level, "source": source, "message": message})
    return entries


def filter_entries(entries: list[dict], lines: int, level: str | None = None, query: str | None = None) -> list[dict]:
    """The last `lines` entries at or above `level` whose message contains `query`, oldest first."""
    minimum = LEVEL_RANK[level] if level else None
    needle = query.casefold() if query else None
    matches = []
    for entry in entries:
        if minimum is not None and LEVEL_RANK.get(entry["level"], -1) < minimum:
            continue
        if needle is not None and needle not in entry["message"].casefold():
            continue
        matches.append(entry)
    return matches[-lines:]
