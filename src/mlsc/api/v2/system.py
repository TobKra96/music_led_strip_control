import json

from flask_openapi3 import APIBlueprint, Tag
from pydantic import BaseModel, Field, RootModel

from mlsc import paths
from mlsc.api.v2.errors import READ_ERRORS, Problem, ProblemError
from mlsc.api.v2.security import api_login_required
from mlsc.config_migration import REPORT_FILE
from mlsc.webserver.executer import Executer
from mlsc.webserver.messages import MigrationReportNotFound

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
