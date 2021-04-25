from libs.webserver.executer import Executer

from flask import Blueprint, request, jsonify
from flask_login import login_required
import copy

device_settings_api = Blueprint('device_settings_api', __name__)


#################################################################
# Get one specific device setting of one device
# /GetDeviceSetting
# in
# {
# "device" = <deviceID>
# "setting_key" = <setting_key>
# }
#
# return
# {
# "device" = <deviceID>
# "setting_key" = <setting_key>
# "setting_value" = <setting_value>
# }
@device_settings_api.route('/GetDeviceSetting', methods=['GET'])
@login_required
def get_device_setting():  # pylint: disable=E0211
    if request.method == 'GET':
        data_in = request.args.to_dict()
        data_out = copy.deepcopy(data_in)

        if not Executer.instance.device_settings_executer.validate_data_in(data_in, ("device", "setting_key",)):
            return "Input data are wrong.", 403

        setting_value = Executer.instance.device_settings_executer.get_device_setting(data_in["device"], data_in["setting_key"])
        data_out["setting_value"] = setting_value

        if setting_value is None:
            return "Could not find settings value: ", 403
        else:
            return jsonify(data_out)


# Get all device settings of a specific device
# /GetDeviceSettings
# in
# {
# "device" = <deviceID>
# }
#
# return
# {
# "device" = <deviceID>
# "settings" = {
#   "<settings_key>" = <setting_value>
# }
#
@device_settings_api.route('/GetDeviceSettings', methods=['GET'])
@login_required
def get_device_settings():  # pylint: disable=E0211
    if request.method == 'GET':
        data_in = request.args.to_dict()
        data_out = copy.deepcopy(data_in)

        if not Executer.instance.device_settings_executer.validate_data_in(data_in, ("device",)):
            return "Input data are wrong.", 403

        setting_values = Executer.instance.device_settings_executer.get_device_settings(data_in["device"])
        data_out["settings"] = setting_values

        if setting_values is None:
            return "Could not find settings value: ", 403
        else:
            return jsonify(data_out)


# /SetDeviceSetting
# {
# "device" = <deviceID>
# "settings" = {
#   "<settings_key>" = <setting_value>
# }
# }
@device_settings_api.route('/SetDeviceSetting', methods=['POST'])
@login_required
def set_device_setting():  # pylint: disable=E0211
    if request.method == 'POST':
        data_in = request.get_json()
        data_out = copy.deepcopy(data_in)

        if not Executer.instance.device_settings_executer.validate_data_in(data_in, ("device", "settings", )):
            return "Input data are wrong.", 403

        Executer.instance.device_settings_executer.set_device_setting(data_in["device"], data_in["settings"])

        return jsonify(data_out)


# /GetOutputTypeDeviceSetting
# in
# {
# "device" = <deviceID>
# "output_type_key" = <output_type_key>
# "setting_key" = <setting_key>
# }
#
# return
# {
# "device" = <deviceID>
# "output_type_key" = <output_type_key>
# "setting_key" = <setting_key>
# "setting_value" = <setting_value>
# }
@device_settings_api.route('/GetOutputTypeDeviceSetting', methods=['GET'])
@login_required
def get_output_type_device_setting():  # pylint: disable=E0211
    if request.method == 'GET':
        data_in = request.args.to_dict()
        data_out = copy.deepcopy(data_in)

        if not Executer.instance.device_settings_executer.validate_data_in(data_in, ("device", "output_type_key", "setting_key",)):
            return "Input data are wrong.", 403

        setting_value = Executer.instance.device_settings_executer.get_output_type_device_setting(data_in["device"], data_in["output_type_key"], data_in["setting_key"])
        data_out["setting_value"] = setting_value

        if setting_value is None:
            return "Could not find settings value: ", 403
        else:
            return jsonify(data_out)


# /SetOutputTypeDeviceSetting
# {
# "device" = <deviceID>
# "output_type_key" = <output_type_key>
# "settings" = {
#   "<settings_key>" = <setting_value>
# }
# }
@device_settings_api.route('/SetOutputTypeDeviceSetting', methods=['POST'])
@login_required
def set_output_type_device_setting():  # pylint: disable=E0211
    if request.method == 'POST':
        data_in = request.get_json()
        data_out = copy.deepcopy(data_in)

        if not Executer.instance.device_settings_executer.validate_data_in(data_in, ("device", "output_type_key", "settings", )):
            return "Input data are wrong.", 403

        Executer.instance.device_settings_executer.set_output_type_device_setting(data_in["device"], data_in["output_type_key"], data_in["settings"])

        return jsonify(data_out)
