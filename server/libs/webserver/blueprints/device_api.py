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
                type: object,
                example:
                    [
                        {
                            id: str,
                            name: str
                        },
                        ...
                    ]
        403:
            description: Could not find devices
    """
    data_out = dict()

    devices = Executer.instance.device_executer.get_devices()
    data_out = devices

    if devices is None:
        return "Could not find devices: ", 403
    else:
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
                type: object,
                example:
                    {
                        index: int
                    }
    """
    index = Executer.instance.device_executer.create_new_device()

    data_out = {
        "index": index
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
                type: object,
                example:
                    {
                        device: str
                    }
    responses:
        200:
            description: OK
            schema:
                type: object,
                example:
                    {
                        device: str
                    }
        403:
            description: Input data are wrong
    """
    data_in = request.get_json()
    data_out = copy.deepcopy(data_in)

    if not Executer.instance.device_executer.validate_data_in(data_in, ("device",)):
        return "Input data are wrong.", 403

    Executer.instance.device_executer.delete_device(data_in["device"])

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
                type: object,
                example:
                    [
                        {
                            id: str,
                            name: str
                        },
                        ...
                    ]
        403:
            description: Could not find groups
    """
    data_out = dict()

    groups = Executer.instance.device_executer.get_groups()
    data_out = groups

    if groups is None:
        return "Could not find devices: ", 403
    else:
        return jsonify(data_out)
