"""Helpers that turn the sentinel results of the executers into problem documents."""
from mlsc.api.v2.errors import ProblemError
from mlsc.webserver.executer import Executer
from mlsc.webserver.messages import DeviceNotFound, EffectNotFound, GroupNotFound, ValidationError, _Message


def unwrap(result):
    """Return the result of an executer, or raise it if it is one of the sentinel messages."""
    if isinstance(result, type) and issubclass(result, _Message):
        raise ProblemError(result)
    return result


def device_ids() -> list[str]:
    return [device["id"] for device in Executer.instance.device_executer.get_devices()]


def require_devices(ids: list[str]) -> None:
    """Raise a 404 that names the first unknown id."""
    known = set(device_ids())
    for device_id in ids:
        if device_id not in known:
            raise ProblemError(DeviceNotFound, f"Device {device_id} does not exist.")


def require_device(device_id: str) -> dict:
    """Return a device, or raise a 404."""
    device = Executer.instance.device_executer.get_device(device_id)
    if device is DeviceNotFound:
        raise ProblemError(DeviceNotFound, f"Device {device_id} does not exist.")
    return device


def require_group(group_id: str) -> str:
    """Return the name of a group, or raise a 404."""
    groups = Executer.instance.device_executer.get_groups()["groups"]
    if group_id not in groups:
        raise ProblemError(GroupNotFound, f"Group {group_id} does not exist.")
    return groups[group_id]


def device_settings(device_id: str) -> dict:
    """Return the live settings of a device."""
    require_devices([device_id])
    return Executer.instance.device_settings_executer.get_device_settings(device_id)["settings"]


def effect_settings(device_id: str, effect: str) -> dict:
    """Return the live settings of one effect of a device."""
    effects = device_settings(device_id)["effects"]
    if effect not in effects or not isinstance(effects[effect], dict):
        raise ProblemError(EffectNotFound, f"Effect {effect} does not exist.")
    return effects[effect]


def require_patch(patch: dict) -> dict:
    """Return a partial update, or raise a 422 if it changes nothing."""
    if not patch:
        raise ProblemError(ValidationError, errors=[{"field": "(body)", "detail": "Send at least one setting."}])
    return patch


def unique_ids(ids: list[str]) -> list[str]:
    """Return `ids`, or raise a ValueError that names the ids listed more than once."""
    repeated = sorted({i for i in ids if ids.count(i) > 1})
    if repeated:
        msg = f"Each id may be listed only once: {', '.join(repeated)}."
        raise ValueError(msg)
    return ids
