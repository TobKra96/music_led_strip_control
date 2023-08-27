from libs.webserver.schemas.config_validator_service import definitions, effect_enum, effect_schema, remove_required_keys
from libs.webserver.schemas.custom_types import valid_device_id_type

_ALL_CUSTOMIZABLE_EFFECTS = [*effect_enum, "effect_random_cycle"]
""" List of all customizable effects. """


_EFFECT_SCHEMA_PARSED = remove_required_keys(list(effect_schema["properties"].values()))
""" Parsed effect schema. Using schema from config validator service to avoid duplication. """


GET_EFFECT_SETTING_SCHEMA = {
    "type": "object",
    "required": ["device", "effect", "setting_key"],
    "properties": {
        "device": valid_device_id_type,
        "effect": {
            "type": "string",
            "enum": _ALL_CUSTOMIZABLE_EFFECTS,
        },
        "setting_key": {
            "type": "string",
        },
    },
}
""" Schema for `GET /api/settings/effect` with `device`, `effect` and `setting_key` as query parameters. """


GET_EFFECT_SETTINGS_SCHEMA = {
    "type": "object",
    "required": ["device", "effect"],
    "properties": {
        "device": valid_device_id_type,
        "effect": {
            "type": "string",
            "enum": _ALL_CUSTOMIZABLE_EFFECTS,
        },
    },
}
""" Schema for `GET /api/settings/effect` with `device` and `effect` as query parameters. """


SET_EFFECT_SETTINGS_SCHEMA = {
    "type": "object",
    "required": ["device", "effect", "settings"],
    "properties": {
        "device": valid_device_id_type,
        "effect": {
            "type": "string",
            "enum": _ALL_CUSTOMIZABLE_EFFECTS,
        },
        "settings": {  # oneOf can't be used because some partial updates are identical in multiple effects.
            "anyOf": _EFFECT_SCHEMA_PARSED
        },
    },
    "$defs": definitions,  # Required for the `#/defs/rgb` in this schema.
}
""" Schema for `POST /api/settings/effect` with `device`, `effect` and `settings` as request body keys. """


SET_EFFECT_SETTINGS_ALL_SCHEMA = {
    "type": "object",
    "required": ["effect", "settings"],
    "properties": {
        "effect": {
            "type": "string",
            "enum": _ALL_CUSTOMIZABLE_EFFECTS,
        },
        "settings": {  # oneOf can't be used because some partial updates are identical in multiple effects.
            "anyOf": _EFFECT_SCHEMA_PARSED
        },
    },
    "$defs": definitions,  # Required for the `#/defs/rgb` in this schema.
}
""" Schema for `POST /api/settings/effect` with `effect` and `settings` as request body keys. """
