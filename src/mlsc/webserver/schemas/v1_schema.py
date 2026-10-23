"""Request schemas of the frozen v1 API: the current schemas with the v1 keys `led_strip` and `device_id` instead of their v4 successors."""
from copy import deepcopy

from mlsc.webserver.schemas import device_settings_api_schema as device_schemas
from mlsc.webserver.schemas import general_settings_api_schema as general_schemas
from mlsc.webserver.v1_adapter import LED_STRIP_NAMES, V4_ONLY_DEVICE_KEYS

_LED_STRIP = {"enum": list(LED_STRIP_NAMES)}
_DEVICE_ID = {"type": "integer", "minimum": -1, "maximum": 100}


def _with_enum_value(schema: dict, key: str, value: str) -> dict:
    schema = deepcopy(schema)
    schema["properties"][key]["enum"].append(value)
    schema["properties"][key]["enum"].sort()
    return schema


ONE_DEVICE_SETTING_SCHEMA = _with_enum_value(device_schemas.ONE_DEVICE_SETTING_SCHEMA, "setting_key", "led_strip")
DEVICE_SETTINGS_WITH_EXCL_SCHEMA = _with_enum_value(device_schemas.DEVICE_SETTINGS_WITH_EXCL_SCHEMA, "excluded_key", "led_strip")

SET_DEVICE_SETTINGS_SCHEMA = deepcopy(device_schemas.SET_DEVICE_SETTINGS_SCHEMA)
_device_properties = SET_DEVICE_SETTINGS_SCHEMA["properties"]["settings"]["properties"]
for _key in V4_ONLY_DEVICE_KEYS:
    del _device_properties[_key]
_device_properties["led_strip"] = _LED_STRIP

ONE_GENERAL_SETTING_SCHEMA = _with_enum_value(general_schemas.ONE_GENERAL_SETTING_SCHEMA, "setting_key", "device_id")

SET_GENERAL_SETTINGS_SCHEMA = deepcopy(general_schemas.SET_GENERAL_SETTINGS_SCHEMA)
SET_GENERAL_SETTINGS_SCHEMA["properties"]["settings"]["properties"]["device_id"] = _DEVICE_ID
