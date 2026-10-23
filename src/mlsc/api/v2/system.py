from flask_openapi3 import APIBlueprint, Tag
from pydantic import BaseModel

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
