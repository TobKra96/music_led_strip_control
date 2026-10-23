from flask_openapi3 import APIBlueprint, Tag
from pydantic import BaseModel, Field, RootModel

from mlsc.api.v2.errors import READ_ERRORS, WRITE_ERRORS, Problem, ProblemError, ValidationError
from mlsc.api.v2.lookup import check_schema, device_settings, effect_settings, require_devices, require_patch, unwrap
from mlsc.api.v2.security import api_login_required
from mlsc.webserver.executer import Executer
from mlsc.webserver.schemas.device_settings_api_schema import SET_DEVICE_SETTINGS_SCHEMA

tag = Tag(name="Devices", description="Configured LED strip devices")
devices_api = APIBlueprint("devices_api_v2", __name__, url_prefix="/api/v2/devices", abp_tags=[tag])

DEVICE_PROPERTIES = SET_DEVICE_SETTINGS_SCHEMA["properties"]["settings"]

class DevicePath(BaseModel):
    device_id: str = Field(description="Stable device id, e.g. `device_0`.")


class EffectSettingsPath(DevicePath):
    effect: str = Field(description="Effect id, e.g. `effect_single`.")


class DeviceOut(BaseModel):
    id: str
    name: str
    assigned_to: dict = Field(description="Groups the device belongs to.")


class DeviceListOut(RootModel[list[DeviceOut]]):
    pass


class SettingsOut(RootModel[dict]):
    """All settings of the owner, as stored in the configuration."""


class SettingsPatch(RootModel[dict]):
    """A partial update: only the given settings change, nested objects are merged."""


def _device(device_id: str) -> dict:
    require_devices([device_id])
    return next(device for device in Executer.instance.device_executer.get_devices() if device["id"] == device_id)


@devices_api.get("", summary="List devices", responses={"200": DeviceListOut, "401": Problem})
@api_login_required
def list_devices():
    return Executer.instance.device_executer.get_devices()


@devices_api.post("", summary="Create a device with default settings", responses={"201": DeviceOut, "401": Problem, "409": Problem, "415": Problem})
@api_login_required
def create_device():
    created = unwrap(Executer.instance.device_executer.create_new_device())
    return _device(created["device_id"]), 201


@devices_api.get("/<device_id>", summary="Get a device", responses={"200": DeviceOut, **READ_ERRORS})
@api_login_required
def get_device(path: DevicePath):
    return _device(path.device_id)


@devices_api.delete("/<device_id>", summary="Delete a device", responses={"204": None, **READ_ERRORS})
@api_login_required
def delete_device(path: DevicePath):
    unwrap(Executer.instance.device_executer.delete_device(path.device_id))
    return "", 204


@devices_api.get("/<device_id>/settings", summary="Get the settings of a device", responses={"200": SettingsOut, **READ_ERRORS})
@api_login_required
def get_device_settings(path: DevicePath):
    return device_settings(path.device_id)


@devices_api.patch("/<device_id>/settings", summary="Update some settings of a device", responses={"200": SettingsOut, **WRITE_ERRORS})
@api_login_required
def patch_device_settings(path: DevicePath, body: SettingsPatch):
    """Output settings are updated the same way, nested under `output`."""
    patch = require_patch(body.root)
    require_devices([path.device_id])
    check_schema(patch, DEVICE_PROPERTIES)
    unwrap(Executer.instance.device_settings_executer.set_device_settings(path.device_id, patch))
    return device_settings(path.device_id)


@devices_api.get("/<device_id>/effects/<effect>/settings", summary="Get the settings of one effect of a device",
                 responses={"200": SettingsOut, **READ_ERRORS})
@api_login_required
def get_effect_settings(path: EffectSettingsPath):
    return effect_settings(path.device_id, path.effect)


@devices_api.patch("/<device_id>/effects/<effect>/settings", summary="Update some settings of one effect of a device",
                   responses={"200": SettingsOut, **WRITE_ERRORS})
@api_login_required
def patch_effect_settings(path: EffectSettingsPath, body: SettingsPatch):
    patch = require_patch(body.root)
    current = effect_settings(path.device_id, path.effect)
    unknown = [key for key in patch if key not in current]
    if unknown:
        raise ProblemError(ValidationError, errors=[{"field": key, "detail": "Unknown setting."} for key in unknown])
    check_schema({"effects": {path.effect: patch}}, DEVICE_PROPERTIES)
    unwrap(Executer.instance.effect_settings_executer.set_effect_settings(path.device_id, path.effect, patch))
    return effect_settings(path.device_id, path.effect)
