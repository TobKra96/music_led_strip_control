from libs.webserver.executer import Executer

from flask import Blueprint, request, jsonify
from flask_login import login_required
import copy

effect_settings_api = Blueprint('effect_settings_api', __name__)


@effect_settings_api.get('/api/settings/effect')
@login_required
def get_effect_settings():  # pylint: disable=E0211
    """
    Return effect settings
    ---
    tags:
        - Settings
    parameters:
        - name: device
          in: query
          type: string
          required: true
          description: Device for which to get the effect settings from
        - name: effect
          in: query
          type: string
          required: true
          description: Specific effect for a selected device
        - name: setting_key
          in: query
          type: string
          required: false
          description: Specific `setting_key` to return from selected effect\n
                       Return all settings if not specified
    responses:
        200:
            description: OK
            schema:
                type: object,
                example:
                    {
                        device: str,
                        effect: str,
                        setting_key: str,
                        setting_value: str
                    }
        403:
            description: Input data are wrong
    """
    if len(request.args) == 3:
        # Retrieve a specific setting for one effect from config.
        data_in = request.args.to_dict()
        data_out = copy.deepcopy(data_in)

        if not Executer.instance.effect_settings_executer.validate_data_in(data_in, ("device", "effect", "setting_key",)):
            return "Input data are wrong.", 403

        setting_value = Executer.instance.effect_settings_executer.get_effect_setting(data_in["device"], data_in["effect"], data_in["setting_key"])
        data_out["setting_value"] = setting_value

        if setting_value is None:
            return "Could not find settings value: ", 403
        else:
            return jsonify(data_out)

    elif len(request.args) == 2:
        # Retrieve all settings for a specific effect from config.
        data_in = request.args.to_dict()
        data_out = copy.deepcopy(data_in)

        if not Executer.instance.effect_settings_executer.validate_data_in(data_in, ("device", "effect",)):
            return "Input data are wrong.", 403

        settings = Executer.instance.effect_settings_executer.get_effect_settings(data_in["device"], data_in["effect"])
        data_out["settings"] = settings

        if settings is None:
            return "Could not find settings value: ", 403
        else:
            return jsonify(data_out)

    return "Input data are wrong.", 403


@effect_settings_api.post('/api/settings/effect')
@login_required
def set_effect_settings():  # pylint: disable=E0211
    """
    Set effect settings
    ---
    tags:
        - Settings
    parameters:
        - name: data
          in: body
          type: string
          required: true
          description: The effect settings which to set\n
          schema:
                type: object,
                example:
                    {
                        device: str,
                        effect: str,
                        settings: object
                    }
    responses:
        200:
            description: OK
            schema:
                type: object,
                example:
                    {
                        device: str,
                        effect: str,
                        settings: object
                    }
        403:
            description: Input data are wrong
    """
    data_in = request.get_json()
    if all(key in data_in for key in ("device", "effect", "settings")):
        # Save a specific setting for one effect to config.
        data_out = copy.deepcopy(data_in)

        if not Executer.instance.effect_settings_executer.validate_data_in(data_in, ("device", "effect", "settings", )):
            return "Input data are wrong.", 403

        Executer.instance.effect_settings_executer.set_effect_setting(data_in["device"], data_in["effect"], data_in["settings"])

        return jsonify(data_out)

    elif all(key in data_in for key in ("effect", "settings")):
        # Save all settings for a specific effect to config.
        data_out = copy.deepcopy(data_in)

        if not Executer.instance.effect_settings_executer.validate_data_in(data_in, ("effect", "settings", )):
            return "Input data are wrong.", 403

        Executer.instance.effect_settings_executer.set_effect_setting_for_all(data_in["effect"], data_in["settings"])

        return jsonify(data_out)

    return "Input data are wrong.", 403
