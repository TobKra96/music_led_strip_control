from libs.webserver.schemas.config_validator_service import effect_enum
from libs.webserver.schemas.custom_types import valid_device_id_type, valid_group_id_type

_ALL_EFFECTS = [*effect_enum, "effect_off", "effect_random_cycle", "effect_random_music", "effect_random_non_music"]
""" List of all possible effects. """


DEVICE_ACTIVE_EFFECT_SCHEMA = {
    "type": "object",
    "required": ["device"],
    "properties": {
        "device": valid_device_id_type,
    },
}
""" Schema for `GET /api/effect/active`. """


SET_ACTIVE_EFFECT_SCHEMA = {
    "type": "object",
    "required": ["device", "effect"],
    "properties": {
        "device": valid_device_id_type,
        "effect": {
            "type": "string",
            "enum": _ALL_EFFECTS,
        },
    },
}
""" Schema for `POST /api/effect/active` with `device` and `effect` as request body keys. """


SET_ACTIVE_EFFECT_MULT_SCHEMA = {
    "type": "object",
    "required": ["devices"],
    "properties": {
        "devices": {
            "type": "array",
            "uniqueItems": True,
            "maxItems": 100,
            "items": {
                "type": "object",
                "required": ["device", "effect"],
                "properties": {
                    "device": valid_device_id_type,
                    "effect": {
                        "type": "string",
                        "enum": _ALL_EFFECTS,
                    },
                },
            },
        },
    },
}
""" Schema for `POST /api/effect/active` with `devices` as a request body key. """


SET_ACTIVE_EFFECT_ALL_SCHEMA = {
    "type": "object",
    "required": ["effect"],
    "properties": {
        "effect": {
            "type": "string",
            "enum": _ALL_EFFECTS,
        },
    },
}
""" Schema for `POST /api/effect/active` with `effect` as a request body key. """


DEVICE_CYCLE_STATUS_SCHEMA = {
    "type": "object",
    "required": ["device"],
    "oneOf": [
        {
            "properties": {
                "device": valid_device_id_type,
            }
        },
        {
            "properties": {
                "device": valid_group_id_type,
            }
        },
        {
            "properties": {
                "device": {
                    "type": "string",
                    "enum": ["all_devices"],
                },
            }
        },
    ],
}
""" Schema for `GET /api/effect/cycle-status`. """
