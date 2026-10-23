from flask_openapi3 import APIBlueprint, Tag
from pydantic import BaseModel, RootModel

from mlsc.api.v2.errors import Problem
from mlsc.api.v2.security import api_login_required
from mlsc.webserver.executer import Executer

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


def _info(method: str):
    return getattr(Executer.instance.system_info_executer, method)()


@system_api.get("/performance", summary="Get CPU, memory, disk and network usage", responses={"200": InfoOut, "401": Problem})
@api_login_required
def get_performance():
    return _info("get_system_info_performance")


@system_api.get("/temperature", summary="Get the CPU temperature", responses={"200": InfoOut, "401": Problem})
@api_login_required
def get_temperature():
    return _info("get_system_info_temperature")


@system_api.get("/services", summary="Get the status of the system services", responses={"200": InfoOut, "401": Problem})
@api_login_required
def get_services():
    return _info("get_system_info_services")


@system_api.get("/device-status", summary="Check whether each device is reachable", responses={"200": InfoOut, "401": Problem})
@api_login_required
def get_device_status():
    return _info("get_system_info_device_status")
