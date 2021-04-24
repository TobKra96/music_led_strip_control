from flask import Blueprint, request, jsonify, send_file, flash
from libs.webserver.executer import Executer
from flask_login import login_required

import copy
import json

system_info_api = Blueprint('system_info_api', __name__)


#################################################################

# /GetSystemInfoPerformance
# in
# {
# }
#
# return
# {
# "data" = {
#   "<system_info_key1>" = <system_info_value1>,
#   "<system_info_key2>" = <system_info_value2>,
#   "<system_info_key3>" = <system_info_value3>
# }
@system_info_api.route('/GetSystemInfoPerformance', methods=['GET'])
@login_required
def get_system_info_performance():  # pylint: disable=E0211
    if request.method == 'GET':
        data_out = dict()

        data = Executer.instance.system_info_executer.get_system_info_performance()
        data_out["system"] = data

        if data is None:
            return "Could not find data value: data", 403
        else:
            return jsonify(data_out)


#################################################################

# /GetSystemInfoTemperature
# in
# {
# }
#
# return
# {
# "data" = {
#   "<system_info_key1>" = <system_info_value1>,
#   "<system_info_key2>" = <system_info_value2>,
#   "<system_info_key3>" = <system_info_value3>
# }
@system_info_api.route('/GetSystemInfoTemperature', methods=['GET'])
@login_required
def get_system_info_temperature():  # pylint: disable=E0211
    if request.method == 'GET':
        data_out = dict()

        data = Executer.instance.system_info_executer.get_system_info_temperature()
        data_out["system"] = data

        if data is None:
            return "Could not find data value: data", 403
        else:
            return jsonify(data_out)


#################################################################

# /GetSystemInfoServices
# in
# {
# }
#
# return
# {
# "data" = {
#   "<system_info_key1>" = <system_info_value1>,
#   "<system_info_key2>" = <system_info_value2>,
#   "<system_info_key3>" = <system_info_value3>
# }
@system_info_api.route('/GetSystemInfoServices', methods=['GET'])
@login_required
def get_system_info_services():  # pylint: disable=E0211
    if request.method == 'GET':
        data_out = dict()

        data = Executer.instance.system_info_executer.get_system_info_services()
        data_out["system"] = data

        if data is None:
            return "Could not find data value: data", 403
        else:
            return jsonify(data_out)
