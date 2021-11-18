from libs.webserver.executer import Executer

from flask import Blueprint, request, jsonify
from flask_login import login_required
import copy

device_api = Blueprint('device_api', __name__)


@device_api.get('/api/system/devices')
@login_required
def get_devices():  # pylint: disable=E0211
    """
    Devices
    ---
    tags:
        - System
    responses:
        200:
            description: OK
            schema:
                type: object
                example:
                    [
                        {
                            "groups": [
                                str,
                                ...
                            ],
                            id: str,
                            name: str
                        },
                        ...
                    ]
        403:
            description: Could not find devices
        422:
            description: Unprocessable Entity
    """
    data_out = Executer.instance.device_executer.get_devices()

    if data_out is None:
        return "Unprocessable Entity.", 422

    if not data_out:
        return "Could not find devices.", 403

    return jsonify(data_out)


@device_api.post('/api/system/devices')
@login_required
def create_device():  # pylint: disable=E0211
    """
    Add new device
    ---
    tags:
        - System
    responses:
        200:
            description: OK
            schema:
                type: object
                example:
                    {
                        index: int
                    }
        422:
            description: Unprocessable Entity
    """
    result = Executer.instance.device_executer.create_new_device()

    if result is None:
        return "Unprocessable Entity.", 422

    data_out = {
        "index": result
    }

    return jsonify(data_out)


@device_api.delete('/api/system/devices')
@login_required
def delete_device():  # pylint: disable=E0211
    """
    Delete device
    ---
    tags:
        - System
    parameters:
        - name: device
          in: body
          type: string
          required: true
          description: ID of `device` to delete
          schema:
                type: object
                example:
                    {
                        device: str
                    }
    responses:
        200:
            description: OK
            schema:
                type: object
                example:
                    {
                        device: str
                    }
        403:
            description: Input data are wrong
        422:
            description: Unprocessable Entity
    """
    data_in = request.get_json()

    if not Executer.instance.device_executer.validate_data_in(data_in, ("device",)):
        return "Input data are wrong.", 403

    result = Executer.instance.device_executer.delete_device(data_in["device"])

    if result is None:
        return "Unprocessable Entity.", 422

    data_out = copy.deepcopy(data_in)
    return jsonify(data_out)


@device_api.get('/api/system/groups')
@login_required
def get_groups():  # pylint: disable=E0211
    """
    Groups
    ---
    tags:
        - System
    responses:
        200:
            description: OK
            schema:
                type: object
                example:
                    "groups": [
                        str,
                        ...
                    ]
        403:
            description: Could not find groups
        422:
            description: Unprocessable Entity
    """
    data_out = Executer.instance.device_executer.get_groups()

    if data_out is None:
        return "Unprocessable Entity.", 422

    if not data_out["groups"]:
        return "Could not find groups.", 403
    else:
        return jsonify(data_out)


@device_api.post('/api/system/groups')
@login_required
def create_group():  # pylint: disable=E0211
    """
    Add new group
    ---
    tags:
        - System
    parameters:
        - name: group
          in: body
          type: string
          required: true
          description: Name of `group` to create
          schema:
                type: object
                example:
                    {
                        group: str
                    }
    responses:
        200:
            description: OK
            schema:
                type: object
                example:
                    "groups": [
                        str,
                        ...
                    ]
        403:
            description: Input data are wrong
        422:
            description: Unprocessable Entity
    """
    data_in = request.get_json()

    if not Executer.instance.device_executer.validate_data_in(data_in, ("group",)):
        return "Input data are wrong.", 403

    data_out = Executer.instance.device_executer.create_new_group(data_in["group"])

    if data_out is None:
        return "Unprocessable Entity.", 422

    return jsonify(data_out)


@device_api.delete('/api/system/groups')
@login_required
def delete_group():  # pylint: disable=E0211
    """
    Delete group
    ---
    tags:
        - System
    parameters:
        - name: group
          in: body
          type: string
          required: true
          description: Name of `group` to delete
          schema:
                type: object
                example:
                    {
                        group: str
                    }
    responses:
        200:
            description: OK
            schema:
                type: object
                example:
                    "groups": [
                        str,
                        ...
                    ]
        403:
            description: Input data are wrong
        422:
            description: Unprocessable Entity
    """
    data_in = request.get_json()

    if not Executer.instance.device_executer.validate_data_in(data_in, ("group",)):
        return "Input data are wrong.", 403

    data_out = Executer.instance.device_executer.delete_group(data_in["group"])

    if data_out is None:
        return "Unprocessable Entity.", 422

    return jsonify(data_out)


@device_api.patch('/api/system/groups')
@login_required
def remove_invalid_device_groups():  # pylint: disable=E0211
    """
    Remove invalid device groups
    ---
    tags:
        - System
    responses:
        200:
            description: OK
            schema:
                type: object
                example:
                    "removed_groups": [
                        str,
                        ...
                    ]
        202:
            description: No invalid groups found
    """
    data_out = Executer.instance.device_executer.remove_invalid_device_groups()

    if data_out is None:
        return "Unprocessable Entity.", 422

    if not data_out["removed_groups"]:
        return "No invalid groups found.", 202

    return jsonify(data_out)
