from libs.webserver.executer import Executer

from flask import Blueprint, request, jsonify
from flask_login import login_required
import copy

group_api = Blueprint('group_api', __name__)


@group_api.get('/api/system/groups')
@login_required
def get_groups():  # pylint: disable=E0211
    """
    Device groups
    ---
    tags:
        - System
    parameters:
        - name: group
          in: query
          type: string
          required: false
          description: ID of `group` to return\n
                       Return all groups if not specified
    responses:
        200:
            description: OK
            schema:
                type: object,
                example:
                    [
                        {
                            id: str,
                            name: str,
                            devices: [str, ...]
                        },
                        ...
                    ]
        403:
            description: Could not find group
    """
    executer = Executer.instance.group_executer

    if "group" in request.args:
        group = executer.get_group(request.args["group"])
        if group is None:
            return "Could not find group.", 403
        return jsonify(group)

    return jsonify(executer.get_groups())


@group_api.post('/api/system/groups')
@login_required
def create_group():  # pylint: disable=E0211
    """
    Add new device group
    ---
    tags:
        - System
    parameters:
        - name: data
          in: body
          type: string
          required: false
          description: Optional `group_name` and list of member `devices` for the new group
          schema:
                type: object,
                example:
                    {
                        group_name: str,
                        devices: [str, ...]
                    }
    responses:
        200:
            description: OK
            schema:
                type: object,
                example:
                    {
                        group: str
                    }
        403:
            description: Input data are wrong
    """
    executer = Executer.instance.group_executer
    data_in = request.get_json(silent=True) or {}

    devices = data_in.get("devices")
    if devices is not None and not executer.validate_devices(devices):
        return "Input data are wrong.", 403

    group = executer.create_new_group(data_in.get("group_name"), devices)

    return jsonify({"group": group})


@group_api.put('/api/system/groups')
@login_required
def update_group():  # pylint: disable=E0211
    """
    Rename a device group or change its members
    ---
    tags:
        - System
    parameters:
        - name: data
          in: body
          type: string
          required: true
          description: The `group` to update. `group_name` and `devices` are optional.
          schema:
                type: object,
                example:
                    {
                        group: str,
                        group_name: str,
                        devices: [str, ...]
                    }
    responses:
        200:
            description: OK
            schema:
                type: object,
                example:
                    {
                        group: str,
                        group_name: str,
                        devices: [str, ...]
                    }
        403:
            description: Input data are wrong
    """
    executer = Executer.instance.group_executer
    data_in = request.get_json()
    data_out = copy.deepcopy(data_in)

    if not executer.validate_data_in(data_in, ("group",)) or not executer.is_group(data_in["group"]):
        return "Input data are wrong.", 403

    devices = data_in.get("devices")
    if devices is not None and not executer.validate_devices(devices):
        return "Input data are wrong.", 403

    executer.update_group(data_in["group"], data_in.get("group_name"), devices)

    return jsonify(data_out)


@group_api.delete('/api/system/groups')
@login_required
def delete_group():  # pylint: disable=E0211
    """
    Delete device group
    ---
    tags:
        - System
    parameters:
        - name: group
          in: body
          type: string
          required: true
          description: ID of `group` to delete. Member devices are not deleted.
          schema:
                type: object,
                example:
                    {
                        group: str
                    }
    responses:
        200:
            description: OK
            schema:
                type: object,
                example:
                    {
                        group: str
                    }
        403:
            description: Input data are wrong
    """
    executer = Executer.instance.group_executer
    data_in = request.get_json()
    data_out = copy.deepcopy(data_in)

    if not executer.validate_data_in(data_in, ("group",)) or not executer.is_group(data_in["group"]):
        return "Input data are wrong.", 403

    executer.delete_group(data_in["group"])

    return jsonify(data_out)


@group_api.get('/api/settings/group')
@login_required
def get_group_settings():  # pylint: disable=E0211
    """
    Return group settings
    ---
    tags:
        - Settings
    parameters:
        - name: group
          in: query
          type: string
          required: true
          description: ID of `group` to return settings from
    responses:
        200:
            description: OK
            schema:
                type: object,
                example:
                    {
                        group: str,
                        settings: {
                            fps: int,
                            led_brightness: int
                        }
                    }
        403:
            description: Input data are wrong
    """
    executer = Executer.instance.group_executer
    data_in = request.args.to_dict()
    data_out = copy.deepcopy(data_in)

    if not executer.validate_data_in(data_in, ("group",)) or not executer.is_group(data_in["group"]):
        return "Input data are wrong.", 403

    data_out["settings"] = executer.get_group_settings(data_in["group"])

    return jsonify(data_out)


@group_api.post('/api/settings/group')
@login_required
def set_group_settings():  # pylint: disable=E0211
    """
    Set group settings
    ---
    tags:
        - Settings
    parameters:
        - name: data
          in: body
          type: string
          required: true
          description: The `settings` which to apply to every device of the specified `group`\n\n
                       Allowed keys inside `settings` - fps, led_brightness\n\n
                       It is not required to include all above keys inside `settings`
          schema:
                type: object,
                example:
                    {
                        group: str,
                        settings: {
                            fps: int,
                            led_brightness: int
                        }
                    }
    responses:
        200:
            description: OK
            schema:
                type: object,
                example:
                    {
                        group: str,
                        settings: {
                            fps: int,
                            led_brightness: int
                        }
                    }
        403:
            description: Input data are wrong
    """
    executer = Executer.instance.group_executer
    data_in = request.get_json()
    data_out = copy.deepcopy(data_in)

    if not executer.validate_data_in(data_in, ("group", "settings",)) or not executer.is_group(data_in["group"]):
        return "Input data are wrong.", 403

    settings = data_in["settings"]
    if type(settings) is not dict or not all(key in executer.GROUP_DEVICE_SETTINGS for key in settings):
        return "Input data are wrong.", 403

    executer.set_group_settings(data_in["group"], settings)

    return jsonify(data_out)
