from flask import jsonify, request
from flask_openapi3 import APIBlueprint

from mlsc.webserver.auth import login_required
from mlsc.webserver.executer import Executer
from mlsc.webserver.openapi_docs import doc

microphone_settings_api = APIBlueprint("microphone_settings_api", __name__)


@microphone_settings_api.get("/api/settings/microphone/volume", **doc("microphone_settings_api/microphone_get_volume.yml"))
@login_required
def microphone_get_volume():
    """Return microphone volume."""
    data_out = Executer.instance.microphone_settings_executer.microphone_get_volume()

    return jsonify(data_out)


@microphone_settings_api.post("/api/settings/microphone/volume", **doc("microphone_settings_api/microphone_set_volume.yml"))
@login_required
def microphone_set_volume():
    """Set microphone volume."""
    data_in = request.get_json()

    if not Executer.instance.effect_executer.validate_data_in(data_in, ("level",)):
        return jsonify("Unprocessable Entity."), 422

    data_out = Executer.instance.microphone_settings_executer.microphone_set_volume(data_in["level"])

    return jsonify(data_out)
