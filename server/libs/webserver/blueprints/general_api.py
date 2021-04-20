from flask import Blueprint, request, jsonify
from flask_login import login_required
from libs.webserver.executer import Executer

import copy
import json

general_api = Blueprint('general_api', __name__)


# /GetColors
#
# return
# {
# "<colorID1>" = <colorName1>
# "<colorID2>" = <colorName2>
# "<colorID3>" = <colorName3>
# ...
# }
@general_api.route('/GetColors', methods=['GET'])
@login_required
def get_colors():  # pylint: disable=E0211
    if request.method == 'GET':
        data_out = dict()

        colors = Executer.instance.general_executer.get_colors()
        data_out = colors

        if data_out is None:
            return "Could not find colors.", 403
        else:
            return jsonify(data_out)


# /GetGradients
#
# return
# {
# "<gradientID1>" = <gradientName1>
# "<gradientID2>" = <gradientName2>
# "<gradientID3>" = <gradientName3>
# ...
# }
@general_api.route('/GetGradients', methods=['GET'])
@login_required
def get_gradients():  # pylint: disable=E0211
    if request.method == 'GET':
        data_out = dict()

        gradients = Executer.instance.general_executer.get_gradients()
        data_out = gradients

        if data_out is None:
            return "Could not find gradients.", 403
        else:
            return jsonify(data_out)


# /GetLEDStrips
#
# return
# {
# "<LEDStripID1>" = <LEDStripName1>
# "<LEDStripID2>" = <LEDStripName2>
# "<LEDStripID3>" = <LEDStripName3>
# ...
# }
@general_api.route('/GetLEDStrips', methods=['GET'])
@login_required
def get_led_strips():  # pylint: disable=E0211
    if request.method == 'GET':
        data_out = dict()

        led_strips = Executer.instance.general_executer.get_led_strips()
        data_out = led_strips

        if data_out is None:
            return "Could not find led_strips.", 403
        else:
            return jsonify(data_out)


# /GetLoggingLevels
#
# return
# {
# "<GetLoggingLevelID1>" = <LoggingLevelName1>
# "<GetLoggingLevelID2>" = <LoggingLevelName2>
# "<GetLoggingLevelID3>" = <LoggingLevelName3>
# ...
# }
@general_api.route('/GetLoggingLevels', methods=['GET'])
@login_required
def get_logging_levels():  # pylint: disable=E0211
    if request.method == 'GET':
        data_out = dict()

        logging_levels = Executer.instance.general_executer.get_logging_levels()
        data_out = logging_levels

        if data_out is None:
            return "Could not find logging_levels.", 403
        else:
            return jsonify(data_out)


# /get_audio_devices
#
# return
# {
# "<AudioDeviceID1>" = <AudioDeviceIDDescription1>
# "<AudioDeviceID2>" = <AudioDeviceIDDescription2>
# "<AudioDeviceID3>" = <AudioDeviceIDDescription3>
# ...
# }
@general_api.route('/GetAudioDevices', methods=['GET'])
@login_required
def get_audio_devices():  # pylint: disable=E0211
    if request.method == 'GET':
        data_out = dict()

        audio_devices = Executer.instance.general_executer.get_audio_devices()
        data_out = audio_devices

        if data_out is None:
            return "Could not find audio_devices.", 403
        else:
            return jsonify(data_out)


# /GetOutputTypes
#
# return
# {
# "<outputTypeID1>" = <outputTypeName1>
# "<outputTypeID2>" = <outputTypeName2>
# "<outputTypeID3>" = <outputTypeName3>
# ...
# }
@general_api.route('/GetOutputTypes', methods=['GET'])
@login_required
def get_output_types():  # pylint: disable=E0211
    if request.method == 'GET':
        data_out = dict()

        output_types = Executer.instance.general_executer.get_output_types()
        data_out = output_types

        if data_out is None:
            return "Could not find output_types.", 403
        else:
            return jsonify(data_out)
