"""Pydantic models for the settings bodies of the v2 API.

The rules (types, ranges, enums) are written once, in the config validator schemas, which also guard the configuration file.
The models are derived from them at import time, so the OpenAPI document spells out every setting and pydantic produces the field errors.
Every model is a partial update: all fields are optional and unknown fields are rejected.
"""
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, create_model

from mlsc.webserver.schemas.config_validator_service import audio_schema, definitions, device_schema, general_settings_schema

_IPV4 = r"^((25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(25[0-5]|2[0-4]\d|1?\d?\d)$"
_SCALARS = {"integer": int, "number": int | float, "string": str, "boolean": bool}
_CONSTRAINTS = {
    "minimum": "ge", "maximum": "le", "exclusiveMinimum": "gt", "multipleOf": "multiple_of",
    "minLength": "min_length", "maxLength": "max_length", "pattern": "pattern", "minItems": "min_length", "maxItems": "max_length",
}


def _pascal(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("_"))


def _drop_defaults(schema: dict[str, Any]) -> None:
    """Fields are optional because they have no value, not because their default is `null`."""
    for field in schema.get("properties", {}).values():
        field.pop("default", None)


def _constraints(schema: dict[str, Any]) -> dict[str, Any]:
    constraints = {_CONSTRAINTS[key]: value for key, value in schema.items() if key in _CONSTRAINTS}
    if schema.get("format") == "ipv4":
        constraints["pattern"] = _IPV4
    return constraints


def _resolve(schema: dict[str, Any]) -> dict[str, Any]:
    if "$ref" not in schema:
        return schema
    return definitions[schema["$ref"].rsplit("/", 1)[-1]]


def _annotation(name: str, schema: dict[str, Any]) -> Any:  # ruff: ignore[any-type]
    """Return the type that accepts the same values as the JSON schema `schema`."""
    schema = _resolve(schema)
    if "enum" in schema:
        return Literal[tuple(schema["enum"])]
    if "const" in schema:
        return Literal[schema["const"]]
    for union_key in ("anyOf", "oneOf"):
        if union_key in schema:
            return Union[tuple(_annotation(name, option) for option in schema[union_key])]
    kind = schema["type"]
    if isinstance(kind, list):
        return Union[tuple(type(None) if option == "null" else _annotation(name, {**schema, "type": option}) for option in kind)]
    if kind == "object":
        if "patternProperties" in schema:
            (pattern, value), = schema["patternProperties"].items()
            return dict[Annotated[str, StringConstraints(pattern=pattern)], _annotation(name, value)]
        return _model(name, schema)
    if kind == "array":
        return Annotated[list[_annotation(name, schema["items"])], Field(**_constraints(schema))]
    return Annotated[_SCALARS[kind], Field(**_constraints(schema))]


def _model(name: str, schema: dict[str, Any]) -> type[BaseModel]:
    fields = {key: (_annotation(f"{name}{_pascal(key)}", prop), Field(default=None)) for key, prop in schema["properties"].items()}
    return create_model(
        name, __config__=ConfigDict(extra="forbid", strict=True, json_schema_extra=_drop_defaults), **fields,
    )


GeneralSettingsPatch = _model("GeneralSettingsPatch", {
    **general_settings_schema,
    # Groups have their own resource.
    "properties": {key: value for key, value in general_settings_schema["properties"].items() if key != "device_groups"},
})
DeviceSettingsPatch = _model("DeviceSettingsPatch", device_schema)
MicrophonePatch = _model("MicrophonePatch", audio_schema)
# What the Setup Wizard changes: the strip, its power and the Output.
OUTPUT_KEYS = (
    "led_count", "led_mid", "led_brightness", "output_type", "chip_family", "colour_order", "white_channel", "gpio_backend", "power_limit",
    "output",
)
OutputPatch = _model("OutputPatch", {**device_schema, "properties": {key: device_schema["properties"][key] for key in OUTPUT_KEYS}})

EFFECT_SCHEMAS = {
    effect: schema
    for effect, schema in device_schema["properties"]["effects"]["properties"].items()
    if schema.get("type") == "object"
}
EffectSettingsPatches: dict[str, type[BaseModel]] = {
    effect: _model(f"{_pascal(effect)}SettingsPatch", schema) for effect, schema in EFFECT_SCHEMAS.items()
}
