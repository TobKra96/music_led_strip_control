from flask import Blueprint, request, jsonify
from flask_login import login_required
from libs.webserver.executer import Executer

import copy
import json

device_api = Blueprint('device_api', __name__)


# /GetDevices
# in
# {
# }

# return
# {
# "<device_id1>" = <device_name1>
# "<device_id2>" = <device_name2>
# "<device_id3>" = <device_name3>
# ...
# }
@device_api.route('/GetDevices', methods=['GET'])
@login_required
def GetDevices():  # pylint: disable=E0211
    if request.method == 'GET':
        data_out = dict()

        devices = Executer.instance.device_executer.GetDevices()
        data_out = devices

        if devices is None:
            return "Could not find devices: ", 403
        else:
            return jsonify(data_out)


# /CreateNewDevice
# {
# }
@device_api.route('/CreateNewDevice', methods=['POST'])
@login_required
def CreateNewDevice():  # pylint: disable=E0211
    if request.method == 'POST':

        index = Executer.instance.device_executer.CreateNewDevice()

        data_out = {
            "index": index
        }

        return jsonify(data_out)


# /DeleteDevice
# {
# "device" = <deviceID>
# }
@device_api.route('/DeleteDevice', methods=['POST'])
@login_required
def DeleteDevice():  # pylint: disable=E0211
    if request.method == 'POST':
        data_in = request.get_json()
        data_out = copy.deepcopy(data_in)

        if not Executer.instance.device_executer.ValidateDataIn(data_in, ("device",)):
            return "Input data are wrong.", 403

        Executer.instance.device_executer.DeleteDevice(data_in["device"])

        return jsonify(data_out)
