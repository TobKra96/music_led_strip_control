from flask_openapi3 import APIBlueprint, Tag
from pydantic import BaseModel, Field, RootModel, field_validator

from mlsc.api.v2.devices import DevicePath
from mlsc.api.v2.errors import READ_ERRORS, WRITE_ERRORS, Problem
from mlsc.api.v2.lookup import device_ids, require_devices
from mlsc.api.v2.security import api_login_required
from mlsc.effects_enum import EffectsEnum
from mlsc.webserver.executer import Executer

tag = Tag(name="Effects", description="The effect shown on each device")
effects_api = APIBlueprint("effects_api_v2", __name__, url_prefix="/api/v2", abp_tags=[tag])

EFFECT_IDS = frozenset(EffectsEnum.__members__)


class EffectBody(BaseModel):
    effect: str = Field(description="Effect id, or a special effect such as `effect_off` and `effect_random_cycle`.")

    @field_validator("effect")
    @classmethod
    def known_effect(cls, effect: str) -> str:
        if effect not in EFFECT_IDS:
            msg = f"Unknown effect {effect}."
            raise ValueError(msg)
        return effect


class BulkEffectBody(EffectBody):
    device_ids: list[str] | None = Field(default=None, min_length=1, description="The devices to change. Omit to change all devices.")

    @field_validator("device_ids")
    @classmethod
    def no_duplicates(cls, ids: list[str] | None) -> list[str] | None:
        if ids is not None and len(set(ids)) != len(ids):
            msg = "Each device may be listed only once."
            raise ValueError(msg)
        return ids


class ActiveEffectOut(BaseModel):
    device_id: str
    effect: str


class ActiveEffectListOut(RootModel[list[ActiveEffectOut]]):
    pass


class DeviceEffectOut(ActiveEffectOut):
    random_cycle_active: bool


def _active_effects() -> list[dict]:
    return [{"device_id": item["device"], "effect": item["effect"]}
            for item in Executer.instance.effect_executer.get_active_effects()["devices"]]


def _device_effect(device_id: str) -> dict:
    executer = Executer.instance.effect_executer
    return {
        "device_id": device_id,
        "effect": executer.get_active_effect(device_id)["effect"],
        "random_cycle_active": executer.is_cycle_job_running(device_id)["random_cycle_active"],
    }


@effects_api.get("/effect", summary="Get the active effect of every device", responses={"200": ActiveEffectListOut, "401": Problem})
@api_login_required
def get_active_effects():
    return _active_effects()


@effects_api.put("/effect", summary="Set the effect of several devices at once", responses={"200": ActiveEffectListOut, **WRITE_ERRORS})
@api_login_required
def set_active_effects(body: BulkEffectBody):
    """All-or-nothing: every target is checked first, and the 404 names the unknown device."""
    executer = Executer.instance.effect_executer
    if body.device_ids is None:
        executer.set_active_effect_for_all(body.effect)
        targets = device_ids()
    else:
        require_devices(body.device_ids)
        targets = [d for d in device_ids() if d in body.device_ids]
        executer.set_active_effect_for_multiple([{"device": d, "effect": body.effect} for d in targets])
    return [item for item in _active_effects() if item["device_id"] in targets]


@effects_api.get("/devices/<device_id>/effect", summary="Get the active effect of a device", responses={"200": DeviceEffectOut, **READ_ERRORS})
@api_login_required
def get_device_effect(path: DevicePath):
    require_devices([path.device_id])
    return _device_effect(path.device_id)


@effects_api.put("/devices/<device_id>/effect", summary="Set the effect of a device", responses={"200": DeviceEffectOut, **WRITE_ERRORS})
@api_login_required
def set_device_effect(path: DevicePath, body: EffectBody):
    require_devices([path.device_id])
    Executer.instance.effect_executer.set_active_effect(path.device_id, body.effect)
    return _device_effect(path.device_id)
