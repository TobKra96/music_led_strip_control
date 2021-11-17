from libs.webserver.executer import Executer

from flask import Blueprint, request, jsonify
from flask_login import login_required
import copy

effect_api = Blueprint('effect_api', __name__)


@effect_api.get('/api/effect/active')
@login_required
def get_active_effect():  # pylint: disable=E0211
    """
    Return active effect
    ---
    tags:
        - Effect
    parameters:
        - name: device
          in: query
          type: string
          required: false
          description: ID of `device` to return active effect from\n
                       Return active effects for all devices if not specified
    responses:
        200:
            description: OK
            schema:
                type: object,
                example:
                    {
                        devices: [
                            {
                                device: str,
                                effect: str
                            },
                            ...
                        ]
                    }
        403:
            description: Input data are wrong
        422:
            description: Unprocessable Entity
    """
    if len(request.args) == 1:
        # Retrieve the active effect for specific device.
        data_in = request.args.to_dict()

        if not Executer.instance.effect_executer.validate_data_in(data_in, ("device",)):
            return "Input data are wrong.", 403

        result = Executer.instance.effect_executer.get_active_effect(data_in["device"])

        if result is None:
            return "Unprocessable Entity.", 422

        data_out = copy.deepcopy(data_in)
        data_out["effect"] = result
        return jsonify(data_out)

    elif not request.args:
        # Retrieve the active effect for all devices.
        result = Executer.instance.effect_executer.get_active_effects()

        if result is None:
            return "Unprocessable Entity.", 422

        data_out = dict()
        data_out["devices"] = result
        return jsonify(data_out)

    return "Input data are wrong.", 403


@effect_api.post('/api/effect/active')
@login_required
def set_active_effect():  # pylint: disable=E0211
    """
    Set active effect
    ---
    tags:
        - Effect
    parameters:
        - name: data
          in: body
          type: string
          required: true
          description: The `effect` which to set for the specified `device`\n
                    Remove `device` to apply effect to all devices (Not implemented yet)
          schema:
            type: object,
            example:
                {
                    device: str,
                    effect: str
                }
    responses:
        200:
            description: OK
            schema:
                type: object,
                example:
                    {
                        device: str,
                        effect: str
                    }
        403:
            description: Input data are wrong
        422:
            description: Unprocessable Entity
    """
    # TODO: Support multiple devices at once.
    data_in = request.get_json()
    if data_in and all(key in data_in for key in ("device", "effect")):
        # Save the active effect for specific device.
        if not Executer.instance.effect_executer.validate_data_in(data_in, ("device", "effect",)):
            return "Input data are wrong.", 403

        effect_dict = Executer.instance.general_executer.get_effects()
        if data_in["effect"] in effect_dict["special"]:
            data_in["effect"] = Executer.instance.effect_executer.parse_special_effects(data_in["effect"], effect_dict, data_in["device"])

        data_out = Executer.instance.effect_executer.set_active_effect(data_in["device"], data_in["effect"])

        if data_out is None:
            return "Unprocessable Entity.", 422

        return jsonify(data_out)

    elif data_in and "effect" in data_in:
        # Save the active effect for all devices.
        if not Executer.instance.effect_executer.validate_data_in(data_in, ("effect",)):
            return "Input data is wrong.", 403

        effect_dict = Executer.instance.general_executer.get_effects()
        if data_in["effect"] in effect_dict["special"]:
            data_in["effect"] = Executer.instance.effect_executer.parse_special_effects(data_in["effect"], effect_dict)

        data_out = Executer.instance.effect_executer.set_active_effect_for_all(data_in["effect"])

        if data_out is None:
            return "Unprocessable Entity.", 422

        return jsonify(data_out)

    return "Input data are wrong.", 403
