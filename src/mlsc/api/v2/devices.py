from flask import Response, request, stream_with_context
from flask_openapi3 import APIBlueprint, Tag
from pydantic import BaseModel, Field, RootModel

from mlsc.api.v2.errors import READ_ERRORS, WRITE_ERRORS, Problem, ProblemError
from mlsc.api.v2.lookup import device_settings, effect_settings, require_device, require_devices, require_patch, unwrap
from mlsc.api.v2.security import api_login_required
from mlsc.api.v2.settings_models import DeviceSettingsPatch, EffectSettingsPatches
from mlsc.webserver import auth
from mlsc.webserver.executer import Executer
from mlsc import strip_preview
from mlsc.webserver.messages import EffectNotFound, TooManyStreams

tag = Tag(name="Devices", description="Configured LED strip devices")
devices_api = APIBlueprint("devices_api_v2", __name__, url_prefix="/api/v2/devices", abp_tags=[tag])


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


@devices_api.get("", summary="List devices", responses={"200": DeviceListOut, "401": Problem})
@api_login_required
def list_devices():
    return Executer.instance.device_executer.get_devices()


@devices_api.post("", summary="Create a device with default settings", responses={"201": DeviceOut, "401": Problem, "409": Problem, "415": Problem})
@api_login_required
def create_device():
    created = unwrap(Executer.instance.device_executer.create_new_device())
    return require_device(created["device_id"]), 201


@devices_api.get("/<device_id>", summary="Get a device", responses={"200": DeviceOut, **READ_ERRORS})
@api_login_required
def get_device(path: DevicePath):
    return require_device(path.device_id)


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
def patch_device_settings(path: DevicePath, body: DeviceSettingsPatch):
    """Only the given settings change, nested objects are merged. Output settings are updated the same way, nested under `output`."""
    patch = require_patch(body.model_dump(exclude_unset=True))
    require_devices([path.device_id])
    unwrap(Executer.instance.device_settings_executer.set_device_settings(path.device_id, patch))
    return device_settings(path.device_id)


@devices_api.get("/<device_id>/effects/<effect>/settings", summary="Get the settings of one effect of a device",
                 responses={"200": SettingsOut, **READ_ERRORS})
@api_login_required
def get_effect_settings(path: EffectSettingsPath):
    return effect_settings(path.device_id, path.effect)


@devices_api.patch("/<device_id>/effects/<effect>/settings", doc_ui=False)
@api_login_required
def patch_unknown_effect_settings(path: EffectSettingsPath):
    """Every known effect has a route of its own with its own body; this one only answers for the others."""
    effect_settings(path.device_id, path.effect)
    raise ProblemError(EffectNotFound, f"Effect {path.effect} does not exist.")


def _add_effect_settings_route(effect: str, patch_model: type[BaseModel]) -> None:
    def patch_effect_settings(path: DevicePath, body: patch_model):
        patch = require_patch(body.model_dump(exclude_unset=True))
        effect_settings(path.device_id, effect)
        unwrap(Executer.instance.effect_settings_executer.set_effect_settings(path.device_id, effect, patch))
        return effect_settings(path.device_id, effect)

    patch_effect_settings.__name__ = f"patch_{effect}_settings"
    patch_effect_settings.__doc__ = "Only the given settings change."
    devices_api.patch(f"/<device_id>/effects/{effect}/settings", summary=f"Update some settings of {effect} of a device",
                      responses={"200": SettingsOut, **WRITE_ERRORS})(api_login_required(patch_effect_settings))


for _effect, _patch_model in EffectSettingsPatches.items():
    _add_effect_settings_route(_effect, _patch_model)


@devices_api.get("/<device_id>/preview", summary="Stream the frames of a device (Strip Preview)",
                 responses={"200": None, **READ_ERRORS, "503": Problem})
@api_login_required
def preview(path: DevicePath):
    """A `text/event-stream` of `preview` events, one per frame, at most 30 a second: the pixels as base64 red, green, blue per LED.

    Works for every output type. Frames only flow while a stream is open.
    """
    require_device(path.device_id)
    hub = strip_preview.hub
    broker = hub.broker(path.device_id) if hub else None
    subscriber = broker.subscribe() if broker else None
    if subscriber is None:
        raise ProblemError(TooManyStreams)
    return Response(
        stream_with_context(broker.stream(
            subscriber, is_valid=auth.session_check(), client_gone=request.environ.get("waitress.client_disconnected"))),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )
