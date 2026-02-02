from multiprocessing import current_process  # DEBUG

from libs.webserver.schemas.config_validator_service import device_schema, remove_required_keys
from libs.webserver.schemas.custom_types import valid_device_id_type


def debug_print(text: str) -> None:  # DEBUG
    if current_process().name == "MainProcess":
        print(text)  # noqa: T201


_DEVICE_SCHEMA_PARSED = remove_required_keys(device_schema)
""" Parsed device schema. Using schema from config validator service to avoid duplication. """


ALL_DEVICE_SETTINGS_SCHEMA = {
    "type": "object",
    "required": ["device"],
    "properties": {
        "device": valid_device_id_type,
    },
}
""" Schema for `GET /api/settings/device` with `device` as a query parameter. """


ONE_DEVICE_SETTING_SCHEMA = {
    "type": "object",
    "required": ["device", "setting_key"],
    "properties": {
        "device": valid_device_id_type,
        "setting_key": {
            "enum": [
                "device_groups",
                "device_name",
                "effects",
                "fps",
                "led_brightness",
                "led_count",
                "led_mid",
                "led_strip",
                "output",
                "output_type",
            ],
        },
    },
}
""" Schema for `GET /api/settings/device` with `device` and `setting_key` as query parameters. """


DEVICE_SETTINGS_WITH_EXCL_SCHEMA = {
    "type": "object",
    "required": ["device", "excluded_key"],
    "properties": {
        "device": valid_device_id_type,
        "excluded_key": {
            "enum": [
                "device_groups",
                "device_name",
                "effects",
                "fps",
                "led_brightness",
                "led_count",
                "led_mid",
                "led_strip",
                "output",
                "output_type",
            ],
        },
    },
}
""" Schema for `GET /api/settings/device` with `device` and `excluded_key` as query parameters. """


_DEVICE_PROPS = _DEVICE_SCHEMA_PARSED["properties"]
SET_DEVICE_SETTINGS_SCHEMA = {
    "type": "object",
    "required": ["device", "settings"],
    "properties": {
        "device": valid_device_id_type,
        "settings": {
            "type": "object",
            "properties": _DEVICE_PROPS,
            "additionalProperties": False,
        },
    },
}
""" Schema for `POST /api/settings/device`. """


GET_ALL_OUTPUT_SETTINGS_SCHEMA = {
    "type": "object",
    "required": ["device"],
    "properties": {
        "device": valid_device_id_type,
    },
}
""" Schema for `GET /api/settings/device/output-type` with `device` as a query parameter. """


GET_OUTPUT_SETTING_SCHEMA = {
    "type": "object",
    "required": ["device", "output_type_key", "setting_key"],
    "properties": {
        "device": valid_device_id_type,
        "output_type_key": {
            "enum": [
                "output_mqtt",
                "output_raspi",
                "output_udp",
            ],
        },
        "setting_key": {
            "enum": [
                "mqtt_broker",
                "mqtt_path",
                "led_channel",
                "led_dma",
                "led_freq_hz",
                "led_invert",
                "led_pin",
                "udp_client_ip",
                "udp_client_port",
            ],
        },
    },
}
""" Schema for `GET /api/settings/device/output-type` with `device`, `output_type_key` and `setting_key` as query parameters. """


_OUTPUT_PROPS = _DEVICE_SCHEMA_PARSED["properties"]["output"]["properties"]
_OUTPUT_SETTINGS_PROPS = {k: v for output_type in _OUTPUT_PROPS for k, v in _OUTPUT_PROPS[output_type]["properties"].items()}
SET_OUTPUT_SETTINGS_SCHEMA = {
    "type": "object",
    "required": ["device", "output_type_key", "settings"],
    "properties": {
        "device": valid_device_id_type,
        "output_type_key": {
            "enum": [
                "output_mqtt",
                "output_raspi",
                "output_udp",
            ],
        },
        "settings": {
            "type": "object",
            "properties": _OUTPUT_SETTINGS_PROPS,
            "additionalProperties": False,
        },
    },
}
""" Schema for `POST /api/settings/device/output-type`. """
