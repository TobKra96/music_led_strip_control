from libs.webserver.executer import Executer

from flask import Blueprint, request, jsonify
from flask_login import login_required


microphone_settings_api = Blueprint('microphone_settings_api', __name__)


@microphone_settings_api.get('/api/settings/microphone/volume')
@login_required
def microphone_get_volume():  # pylint: disable=E0211
    """
    Return microphone volume
    ---
    tags:
        - Settings
    deprecated: true
    responses:
        200:
            description: OK
            schema:
                type: object
                example:
                    {
                        error: str,
                        level: int,
                        output: str,
                        returncode: int
                    }
        403:
            description: Could not find settings value
    """
    data_out = Executer.instance.microphone_settings_executer.microphone_get_volume()

    if data_out is None:
        return "Could not find settings value.", 403

    return jsonify(data_out)


@microphone_settings_api.post('/api/settings/microphone/volume')
@login_required
def microphone_set_volume():  # pylint: disable=E0211
    """
    Set microphone volume
    ---
    tags:
        - Settings
    deprecated: true
    parameters:
        - name: group
          in: body
          type: string
          required: true
          description: Volume level to set
          schema:
                type: object
                example:
                    {
                        level: int
                    }
    responses:
        200:
            description: OK
            schema:
                type: object
                example:
                    {
                        error: str,
                        output: str,
                        returncode: int
                    }
        403:
            description: Input data are wrong
    """
    data_in = request.get_json()

    if not Executer.instance.effect_executer.validate_data_in(data_in, ("level",)):
        return "Input data are wrong.", 403

    data_out = Executer.instance.microphone_settings_executer.microphone_set_volume(data_in["level"])

    if data_out is None:
        return "Could not find settings value.", 403

    return jsonify(data_out)
