from flask_openapi3 import APIBlueprint, Tag
from pydantic import BaseModel, Field, RootModel

from mlsc.api.v2.errors import Problem, ProblemError
from mlsc.api.v2.security import api_login_required
from mlsc.webserver.executer import Executer
from mlsc.webserver.messages import DeviceNotFound

tag = Tag(name="Devices", description="Configured LED strip devices")
devices_api = APIBlueprint("devices_api_v2", __name__, url_prefix="/api/v2/devices", abp_tags=[tag])


class DevicePath(BaseModel):
    device_id: str = Field(description="Stable device id, e.g. `device_0`.")


class DeviceOut(BaseModel):
    id: str
    name: str
    assigned_to: dict = Field(description="Groups the device belongs to.")


class DeviceListOut(RootModel[list[DeviceOut]]):
    pass


@devices_api.get("", summary="List devices", responses={"200": DeviceListOut, "401": Problem})
@api_login_required
def list_devices():
    return Executer.instance.device_executer.get_devices()


@devices_api.get("/<device_id>", summary="Get a device", responses={"200": DeviceOut, "401": Problem, "404": Problem})
@api_login_required
def get_device(path: DevicePath):
    for device in Executer.instance.device_executer.get_devices():
        if device["id"] == path.device_id:
            return device
    raise ProblemError(DeviceNotFound)
