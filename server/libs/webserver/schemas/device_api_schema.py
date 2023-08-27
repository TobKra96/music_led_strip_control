from libs.webserver.schemas.custom_types import valid_device_id_type, valid_group_id_type, valid_name_type

DELETE_DEVICE_SCHEMA = {
    "type": "object",
    "required": ["device"],
    "properties": {
        "device": valid_device_id_type,
    },
}
""" Schema for `DELETE /api/system/devices`. """


CREATE_GROUP_SCHEMA = {
    "type": "object",
    "required": ["group"],
    "properties": {
        "group": valid_name_type,
    },
}
""" Schema for `POST /api/system/groups`. """


DELETE_GROUP_SCHEMA = {
    "type": "object",
    "required": ["group"],
    "properties": {
        "group": valid_group_id_type,
    },
}
""" Schema for `DELETE /api/system/groups`. """
