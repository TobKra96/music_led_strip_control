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
      - description: Device for which to get the effect settings from
        in: query
        name: device
        required: true
        schema:
          type: string
        examples:
          example1:
            value: device_0
            summary: device ID
      - description:
          "Specific effect for a selected device\n\n
          __Note:__ `effect_random_cycle` can only be retrieved using `all_devices` device ID."
        in: query
        name: effect
        required: true
        schema:
          type: string
          enum:
            - effect_single
            - effect_gradient
            - effect_fade
            - effect_sync_fade
            - effect_slide
            - effect_bubble
            - effect_twinkle
            - effect_pendulum
            - effect_rods
            - effect_segment_color
            - effect_fireplace
            - effect_scroll
            - effect_advanced_scroll
            - effect_energy
            - effect_wavelength
            - effect_bars
            - effect_power
            - effect_beat
            - effect_beat_twinkle
            - effect_beat_slide
            - effect_wave
            - effect_wiggle
            - effect_vu_meter
            - effect_spectrum_analyzer
            - effect_direction_changer
            - effect_border
            - effect_random_cycle
      - description:
          Specific `setting_key` to return from selected effect\n\n
          Return all settings if not specified
        in: query
        name: setting_key
        required: false
        schema:
          type: string
        examples:
          example1:
            value: color
            summary: color Setting Key
          example2:
            value: gradient
            summary: gradient Setting Key
    responses:
      "200":
        description: OK
        content:
          application/json:
            schema:
              type: object
            examples:
              example1:
                value:
                  device: str
                  effect: str
                  setting_key: str
                  setting_value: str/int/array/bool/num
                summary: With specified setting_key
              example2:
                value:
                  device: str
                  effect: str
                  settings: object
                summary: Without specified setting_key
      "403":
        description: Input data are wrong
      "422":
        description: Unprocessable Entity
    """
    if len(request.args) == 3:
        # Retrieve a specific setting for one effect from config.
        data_in = request.args.to_dict()

        if not Executer.instance.effect_settings_executer.validate_data_in(data_in, ("device", "effect", "setting_key",)):
            return "Input data are wrong.", 403

        result = Executer.instance.effect_settings_executer.get_effect_setting(
            data_in["device"], data_in["effect"], data_in["setting_key"])

        if result is None:
            return "Unprocessable Entity.", 422

        if result is None:
            return "Could not find settings value: ", 403

        data_out = copy.deepcopy(data_in)
        data_out["setting_value"] = result
        return jsonify(data_out)

    if len(request.args) == 2:
        # Retrieve all settings for a specific effect from config.
        data_in = request.args.to_dict()

        if not Executer.instance.effect_settings_executer.validate_data_in(data_in, ("device", "effect",)):
            return "Input data are wrong.", 403

        result = Executer.instance.effect_settings_executer.get_effect_settings(
            data_in["device"], data_in["effect"])

        if result is None:
            return "Unprocessable Entity.", 422

        if result is None:
            return "Could not find settings value: ", 403

        data_out = copy.deepcopy(data_in)
        data_out["settings"] = result
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
    requestBody:
      content:
        application/json:
          schema:
            type: string
          examples:
            example1:
              value:
                device: device_0
                effect: effect_single
                settings:
                  color: blue
                  custom_color:
                    - 0
                    - 0
                    - 255
                  use_custom_color: false
                  white: 0
              summary: Default effect_single settings
      description: The effect settings which to set
      required: true
    responses:
      "200":
        description: OK
        content:
          application/json:
            schema:
              example:
                device: str
                effect: str
                settings: object
              type: object
      "403":
        description: Input data are wrong
      "422":
        description: Unprocessable Entity
    """
    data_in = request.get_json()
    if all(key in data_in for key in ("device", "effect", "settings")):
        # Save a specific setting for one effect to config.
        if not Executer.instance.effect_settings_executer.validate_data_in(data_in, ("device", "effect", "settings", )):
            return "Input data are wrong.", 403

        result = Executer.instance.effect_settings_executer.set_effect_setting(
            data_in["device"], data_in["effect"], data_in["settings"])

        if result is None:
            return "Unprocessable Entity.", 422

        data_out = copy.deepcopy(data_in)
        return jsonify(data_out)

    if all(key in data_in for key in ("effect", "settings")):
        # Save all settings for a specific effect to config.
        if not Executer.instance.effect_settings_executer.validate_data_in(data_in, ("effect", "settings", )):
            return "Input data are wrong.", 403

        result = Executer.instance.effect_settings_executer.set_effect_setting_for_all(
            data_in["effect"], data_in["settings"])

        if result is None:
            return "Unprocessable Entity.", 422

        data_out = copy.deepcopy(data_in)
        return jsonify(data_out)

    return "Input data are wrong.", 403
