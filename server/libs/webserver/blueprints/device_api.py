from libs.webserver.executer import Executer

from flask import Blueprint, request, jsonify
from flask_login import login_required
import copy

device_api = Blueprint('device_api', __name__)


@device_api.route('/api/system/devices', methods=['GET', 'POST', 'DELETE'])
@login_required
def devices():  # pylint: disable=E0211
    if request.method == 'GET':
        data_out = dict()

        devices = Executer.instance.device_executer.get_devices()
        data_out = devices

        if devices is None:
            return "Could not find devices: ", 403
        else:
            return jsonify(data_out)

    elif request.method == 'POST':
        index = Executer.instance.device_executer.create_new_device()

        data_out = {
            "index": index
        }

        return jsonify(data_out)

    elif request.method == 'DELETE':
        data_in = request.get_json()
        data_out = copy.deepcopy(data_in)

        if not Executer.instance.device_executer.validate_data_in(data_in, ("device",)):
            return "Input data are wrong.", 403

        Executer.instance.device_executer.delete_device(data_in["device"])

        return jsonify(data_out)
