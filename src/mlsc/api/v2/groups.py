from flask_openapi3 import APIBlueprint, Tag
from pydantic import BaseModel, Field, RootModel, field_validator

from mlsc.api.v2.effects import ActiveEffectOut, EffectBody, active_effects
from mlsc.api.v2.errors import READ_ERRORS, WRITE_ERRORS, Problem
from mlsc.api.v2.lookup import device_ids, require_devices, require_group, unique_ids, unwrap
from mlsc.api.v2.security import api_login_required
from mlsc.webserver.executer import Executer
from mlsc.webserver.schemas.custom_types import valid_name

tag = Tag(name="Groups", description="Named sets of devices")
groups_api = APIBlueprint("groups_api_v2", __name__, url_prefix="/api/v2/groups", abp_tags=[tag])


class GroupPath(BaseModel):
    group_id: str = Field(description="Stable group id, e.g. `group_0`.")


class GroupCreate(BaseModel):
    name: str = Field(pattern=valid_name, min_length=1, max_length=75)


class GroupRename(GroupCreate):
    pass


class GroupMembers(BaseModel):
    device_ids: list[str] = Field(description="Exactly these devices are members afterwards.")

    _unique = field_validator("device_ids")(unique_ids)


class GroupOut(BaseModel):
    id: str
    name: str
    device_ids: list[str]


class GroupEffectOut(BaseModel):
    group_id: str
    effect: str | None = Field(description="The effect all members show, or null if they differ or the group has no members.")
    devices: list[ActiveEffectOut]


class GroupListOut(RootModel[list[GroupOut]]):
    pass


def _group(group_id: str) -> dict:
    name = require_group(group_id)
    members = [device["id"] for device in Executer.instance.device_executer.get_devices() if group_id in device["assigned_to"]]
    return {"id": group_id, "name": name, "device_ids": members}


@groups_api.get("", summary="List groups", responses={"200": GroupListOut, "401": Problem})
@api_login_required
def list_groups():
    return [_group(group_id) for group_id in Executer.instance.device_executer.get_groups()["groups"]]


@groups_api.post("", summary="Create a group", responses={"201": GroupOut, "401": Problem, "409": Problem, "415": Problem, "422": Problem})
@api_login_required
def create_group(body: GroupCreate):
    groups = unwrap(Executer.instance.device_executer.create_new_group(body.name))["groups"]
    group_id = next(group_id for group_id, name in groups.items() if name == body.name)
    return _group(group_id), 201


@groups_api.get("/<group_id>", summary="Get a group", responses={"200": GroupOut, **READ_ERRORS})
@api_login_required
def get_group(path: GroupPath):
    return _group(path.group_id)


@groups_api.patch("/<group_id>", summary="Rename a group", responses={"200": GroupOut, **WRITE_ERRORS})
@api_login_required
def rename_group(path: GroupPath, body: GroupRename):
    require_group(path.group_id)
    unwrap(Executer.instance.device_executer.rename_group(path.group_id, body.name))
    return _group(path.group_id)


@groups_api.delete("/<group_id>", summary="Delete a group", responses={"204": None, **READ_ERRORS})
@api_login_required
def delete_group(path: GroupPath):
    unwrap(Executer.instance.device_executer.delete_group(path.group_id))
    return "", 204


@groups_api.put("/<group_id>/devices", summary="Replace the members of a group", responses={"200": GroupOut, **WRITE_ERRORS})
@api_login_required
def set_group_devices(path: GroupPath, body: GroupMembers):
    """All-or-nothing: if any id is unknown, the 404 names it and no membership changes."""
    require_group(path.group_id)
    require_devices(body.device_ids)
    Executer.instance.device_executer.set_group_devices(path.group_id, [d for d in device_ids() if d in body.device_ids])
    return _group(path.group_id)


def _group_effect(group_id: str) -> dict:
    members = _group(group_id)["device_ids"]
    devices = [item for item in active_effects() if item["device_id"] in members]
    effects = {item["effect"] for item in devices}
    return {"group_id": group_id, "effect": effects.pop() if len(effects) == 1 else None, "devices": devices}


@groups_api.get("/<group_id>/effect", summary="Get the active effect of a group", responses={"200": GroupEffectOut, **READ_ERRORS})
@api_login_required
def get_group_effect(path: GroupPath):
    return _group_effect(path.group_id)


@groups_api.put("/<group_id>/effect", summary="Set the effect of every device in a group", responses={"200": GroupEffectOut, **WRITE_ERRORS})
@api_login_required
def set_group_effect(path: GroupPath, body: EffectBody):
    members = _group(path.group_id)["device_ids"]
    Executer.instance.effect_executer.set_active_effect_for_multiple([{"device": d, "effect": body.effect} for d in members])
    return _group_effect(path.group_id)
