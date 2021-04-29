from libs.webserver.executer import Executer

from flask import Blueprint, request, jsonify
from flask_login import login_required

general_api = Blueprint('general_api', __name__)


@general_api.route('/api/resources/colors', methods=['GET'])
@login_required
def colors():  # pylint: disable=E0211
    if request.method == 'GET':
        data_out = dict()

        colors = Executer.instance.general_executer.get_colors()
        data_out = colors

        if data_out is None:
            return "Could not find colors.", 403
        else:
            return jsonify(data_out)


@general_api.route('/api/resources/gradients', methods=['GET'])
@login_required
def gradients():  # pylint: disable=E0211
    if request.method == 'GET':
        data_out = dict()

        gradients = Executer.instance.general_executer.get_gradients()
        data_out = gradients

        if data_out is None:
            return "Could not find gradients.", 403
        else:
            return jsonify(data_out)


@general_api.route('/api/resources/led-strips', methods=['GET'])
@login_required
def led_strips():  # pylint: disable=E0211
    if request.method == 'GET':
        data_out = dict()

        led_strips = Executer.instance.general_executer.get_led_strips()
        data_out = led_strips

        if data_out is None:
            return "Could not find led_strips.", 403
        else:
            return jsonify(data_out)


@general_api.route('/api/resources/logging-levels', methods=['GET'])
@login_required
def logging_levels():  # pylint: disable=E0211
    if request.method == 'GET':
        data_out = dict()

        logging_levels = Executer.instance.general_executer.get_logging_levels()
        data_out = logging_levels

        if data_out is None:
            return "Could not find logging_levels.", 403
        else:
            return jsonify(data_out)


@general_api.route('/api/resources/audio-devices', methods=['GET'])
@login_required
def audio_devices():  # pylint: disable=E0211
    if request.method == 'GET':
        data_out = dict()

        audio_devices = Executer.instance.general_executer.get_audio_devices()
        data_out = audio_devices

        if data_out is None:
            return "Could not find audio_devices.", 403
        else:
            return jsonify(data_out)


@general_api.route('/api/resources/output-types', methods=['GET'])
@login_required
def output_types():  # pylint: disable=E0211
    if request.method == 'GET':
        data_out = dict()

        output_types = Executer.instance.general_executer.get_output_types()
        data_out = output_types

        if data_out is None:
            return "Could not find output_types.", 403
        else:
            return jsonify(data_out)
