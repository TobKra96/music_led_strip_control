import json
from typing import Literal

from flask_openapi3 import APIBlueprint, Tag
from pydantic import BaseModel, Field, RootModel

from mlsc import paths, server_logs
from mlsc.api.v2.errors import READ_ERRORS, Problem, ProblemError
from mlsc.api.v2.security import api_login_required
from mlsc.config_migration import REPORT_FILE
from mlsc.webserver.executer import Executer
from mlsc.webserver.messages import MigrationReportNotFound, PowerActionBlocked, ServerError

LOGS_TIMEOUT_SECONDS = 15

tag = Tag(name="System", description="Server and host information")
system_api = APIBlueprint("system_api_v2", __name__, url_prefix="/api/v2/system", abp_tags=[tag])


class ComponentVersion(BaseModel):
    name: str
    version: str


class VersionsOut(BaseModel):
    versions: list[ComponentVersion]


@system_api.get("/version", summary="Get component versions", responses={"200": VersionsOut, "401": Problem})
@api_login_required
def get_version():
    return Executer.instance.system_info_executer.get_system_version()


class InfoOut(RootModel[dict]):
    """Information as reported by the host."""


@system_api.get("/performance", summary="Get CPU, memory, disk and network usage", responses={"200": InfoOut, "401": Problem})
@api_login_required
def get_performance():
    return Executer.instance.system_info_executer.get_system_info_performance()


@system_api.get("/temperature", summary="Get the CPU temperature", responses={"200": InfoOut, "401": Problem})
@api_login_required
def get_temperature():
    return Executer.instance.system_info_executer.get_system_info_temperature()


@system_api.get("/services", summary="Get the status of the system services", responses={"200": InfoOut, "401": Problem})
@api_login_required
def get_services():
    return Executer.instance.system_info_executer.get_system_info_services()


@system_api.get("/device-status", summary="Check whether each device is reachable", responses={"200": InfoOut, "401": Problem})
@api_login_required
def get_device_status():
    return Executer.instance.system_info_executer.get_system_info_device_status()


class ReportEntry(BaseModel):
    level: str = Field(description="`info` or `warning`.")
    code: str
    path: str = Field(description="Where in the configuration the change was made.")
    message: str
    original: object | None = Field(description="The value that was replaced, when there was one.")


class MigrationReportOut(BaseModel):
    from_version: int
    to_version: int
    entries: list[ReportEntry]


def _report_path():
    return paths.config_dir() / REPORT_FILE


@system_api.get("/migration-report", summary="Get the report of the last Config Migration", responses={"200": MigrationReportOut, **READ_ERRORS})
@api_login_required
def get_migration_report():
    """The report stays until it is dismissed, so the UI can show it once. `404` when there is nothing to show."""
    try:
        return json.loads(_report_path().read_text(encoding="utf-8"))
    except OSError as e:
        raise ProblemError(MigrationReportNotFound) from e


@system_api.delete("/migration-report", summary="Dismiss the Migration Report", responses={"204": None, **READ_ERRORS})
@api_login_required
def dismiss_migration_report():
    """The report is renamed to `migration-report.dismissed.json`, not deleted."""
    path = _report_path()
    if not path.is_file():
        raise ProblemError(MigrationReportNotFound)
    path.replace(path.with_suffix(".dismissed.json"))
    return "", 204


class PowerActionOut(BaseModel):
    available: bool
    reason: str | None = Field(description="Why the action cannot run on this host. `null` when it can.")


class PowerOut(BaseModel):
    reboot: PowerActionOut
    shutdown: PowerActionOut


class PowerAcceptedOut(BaseModel):
    action: str
    status: str = Field(description="Always `accepted`: the machine goes down shortly after the response.")


POWER_ACTIONS = {"reboot": "reboot", "shutdown": "poweroff"}
POWER_ERRORS = {"401": Problem, "409": Problem, "415": Problem, "500": Problem}


def _power_action_out(action: str) -> dict:
    reason = Executer.instance.host.power_action_block(action)
    return {"available": reason is None, "reason": reason}


@system_api.get("/power", summary="Check whether the machine can be rebooted or shut down", responses={"200": PowerOut, "401": Problem})
@api_login_required
def get_power():
    return {action: _power_action_out(action) for action in POWER_ACTIONS}


def _run_power_action(action: str):
    host = Executer.instance.host
    reason = host.power_action_block(action)
    if reason is not None:
        raise ProblemError(PowerActionBlocked, reason)
    code, output = host.run(["systemctl", POWER_ACTIONS[action], "--no-block"])
    if code != 0:
        raise ProblemError(ServerError, output)
    return {"action": action, "status": "accepted"}, 202


@system_api.post("/reboot", summary="Reboot the machine", responses={"202": PowerAcceptedOut, **POWER_ERRORS})
@api_login_required
def reboot():
    """`409` with `PowerActionBlocked` when the host cannot do it (see `GET /system/power`)."""
    return _run_power_action("reboot")


@system_api.post("/shutdown", summary="Shut the machine down", responses={"202": PowerAcceptedOut, **POWER_ERRORS})
@api_login_required
def shutdown():
    """`409` with `PowerActionBlocked` when the host cannot do it (see `GET /system/power`)."""
    return _run_power_action("shutdown")


class LogsQuery(BaseModel):
    lines: int = Field(200, ge=1, le=1000, description="How many of the newest matching entries to return.")
    level: Literal["trace", "debug", "info", "success", "warning", "error", "critical"] | None = Field(None, description="Minimum severity. All levels when omitted.")
    q: str | None = Field(None, max_length=200, description="Case-insensitive text the message must contain.")


class LogEntryOut(BaseModel):
    time: str | None = Field(description="ISO 8601 UTC time from the journal.")
    level: str | None = Field(description="Lowercase level. Lines that are not Loguru lines inherit the previous entry's level.")
    source: str | None = Field(description="`module:function:line`, or `null` for continuation lines.")
    message: str


class LogsOut(BaseModel):
    unavailable: str | None = Field(description="Why the logs cannot be read on this host. `null` when they can.")
    persistent: bool | None = Field(description="`false` when the journal is kept in memory and cleared on reboot. `null` when unavailable.")
    entries: list[LogEntryOut] = Field(description="Oldest to newest.")


@system_api.get("/logs", summary="Get the Server Logs of the current boot", responses={"200": LogsOut, "401": Problem, "422": Problem, "500": Problem})
@api_login_required
def get_logs(query: LogsQuery):
    """Scans the last 2000 journal entries; older matches are not found. Unavailable is a `200` with no entries; a `journalctl` failure is a `500`."""
    host = Executer.instance.host
    reason = host.server_logs_unavailable()
    if reason is not None:
        return {"unavailable": reason, "persistent": None, "entries": []}
    code, output = host.run(server_logs.journal_command(), timeout=LOGS_TIMEOUT_SECONDS)
    if code != 0:
        raise ProblemError(ServerError, output[-500:])
    entries = server_logs.filter_entries(server_logs.parse_entries(output), query.lines, query.level, query.q)
    return {"unavailable": None, "persistent": host.journal_is_persistent(), "entries": entries}
