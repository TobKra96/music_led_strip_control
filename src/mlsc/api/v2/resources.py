from flask_openapi3 import APIBlueprint, Tag
from pydantic import RootModel

from mlsc.api.v2.errors import Problem
from mlsc.api.v2.security import api_login_required
from mlsc.webserver.executer import Executer

tag = Tag(name="Resources", description="Lists of the values that settings can take")
resources_api = APIBlueprint("resources_api_v2", __name__, url_prefix="/api/v2/resources", abp_tags=[tag])


class ResourceOut(RootModel[dict]):
    """Id to display name."""


@resources_api.get("/colors", summary="List the colours", responses={"200": ResourceOut, "401": Problem})
@api_login_required
def colors():
    return Executer.instance.general_executer.get_colors()


@resources_api.get("/gradients", summary="List the gradients", responses={"200": ResourceOut, "401": Problem})
@api_login_required
def gradients():
    return Executer.instance.general_executer.get_gradients()


@resources_api.get("/logging-levels", summary="List the logging levels", responses={"200": ResourceOut, "401": Problem})
@api_login_required
def logging_levels():
    return Executer.instance.general_executer.get_logging_levels()


@resources_api.get("/audio-devices", summary="List the audio input devices", responses={"200": ResourceOut, "401": Problem})
@api_login_required
def audio_devices():
    return Executer.instance.general_executer.get_audio_devices()


@resources_api.get("/output-types", summary="List the output types", responses={"200": ResourceOut, "401": Problem})
@api_login_required
def output_types():
    return Executer.instance.general_executer.get_output_types()


@resources_api.get("/effects", summary="List the effects by kind", responses={"200": ResourceOut, "401": Problem})
@api_login_required
def effects():
    """List the effect ids as `non_music`, `music` and `special`, plus their display `order`."""
    return Executer.instance.general_executer.get_effects()
