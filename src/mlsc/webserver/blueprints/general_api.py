from flask import jsonify
from flask_openapi3 import APIBlueprint

from mlsc.webserver.auth import login_required
from mlsc.webserver.executer import Executer
from mlsc.webserver.openapi_docs import doc
from mlsc.webserver.v1_adapter import LED_STRIP_NAMES

general_api = APIBlueprint("general_api", __name__)


@general_api.get("/api/resources/colors", **doc("general_api/colors.yml"))
@login_required
def colors():
    data_out = Executer.instance.general_executer.get_colors()

    return jsonify(data_out)


@general_api.get("/api/resources/gradients", **doc("general_api/gradients.yml"))
@login_required
def gradients():
    data_out = Executer.instance.general_executer.get_gradients()

    return jsonify(data_out)


@general_api.get("/api/resources/led-strips", **doc("general_api/led_strips.yml"))
@login_required
def led_strips():
    return jsonify(LED_STRIP_NAMES)


@general_api.get("/api/resources/logging-levels", **doc("general_api/logging_levels.yml"))
@login_required
def logging_levels():
    data_out = Executer.instance.general_executer.get_logging_levels()

    return jsonify(data_out)


@general_api.get("/api/resources/audio-devices", **doc("general_api/audio_devices.yml"))
@login_required
def audio_devices():
    data_out = Executer.instance.general_executer.get_audio_devices()

    return jsonify(data_out)


@general_api.get("/api/resources/output-types", **doc("general_api/output_types.yml"))
@login_required
def output_types():
    data_out = Executer.instance.general_executer.get_output_types()

    return jsonify(data_out)


@general_api.get("/api/resources/effects", **doc("general_api/effects.yml"))
@login_required
def effects():
    data_out = Executer.instance.general_executer.get_effects()

    return jsonify(data_out)
