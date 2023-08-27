from flask import Blueprint, jsonify
from flask_login import login_required
from flask_openapi import swag_from
from libs.webserver.executer import Executer

general_api = Blueprint("general_api", __name__)


@general_api.get("/api/resources/colors")
@login_required
@swag_from("docs/general_api/colors.yml")
def colors():  # pylint: disable=E0211
    data_out = Executer.instance.general_executer.get_colors()

    return jsonify(data_out)


@general_api.get("/api/resources/gradients")
@login_required
@swag_from("docs/general_api/gradients.yml")
def gradients():  # pylint: disable=E0211
    data_out = Executer.instance.general_executer.get_gradients()

    return jsonify(data_out)


@general_api.get("/api/resources/led-strips")
@login_required
@swag_from("docs/general_api/led_strips.yml")
def led_strips():  # pylint: disable=E0211
    data_out = Executer.instance.general_executer.get_led_strips()

    return jsonify(data_out)


@general_api.get("/api/resources/logging-levels")
@login_required
@swag_from("docs/general_api/logging_levels.yml")
def logging_levels():  # pylint: disable=E0211
    data_out = Executer.instance.general_executer.get_logging_levels()

    return jsonify(data_out)


@general_api.get("/api/resources/audio-devices")
@login_required
@swag_from("docs/general_api/audio_devices.yml")
def audio_devices():  # pylint: disable=E0211
    data_out = Executer.instance.general_executer.get_audio_devices()

    return jsonify(data_out)


@general_api.get("/api/resources/output-types")
@login_required
@swag_from("docs/general_api/output_types.yml")
def output_types():  # pylint: disable=E0211
    data_out = Executer.instance.general_executer.get_output_types()

    return jsonify(data_out)


@general_api.get("/api/resources/effects")
@login_required
@swag_from("docs/general_api/effects.yml")
def effects():  # pylint: disable=E0211
    data_out = Executer.instance.general_executer.get_effects()

    return jsonify(data_out)
