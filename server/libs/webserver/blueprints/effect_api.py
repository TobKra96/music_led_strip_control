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
      - description:
          ID of `device` to return active effect from\n\n
          Return active effects for all devices if not specified
        name: device
        in: query
        required: false
        schema:
          type: string
        examples:
          example1:
            value: device_0
            summary: device ID
    responses:
      "200":
        description: OK
        content:
          application/json:
            schema:
              example:
                devices:
                  - device: str
                    effect: str
              type: object
            examples:
              example1:
                value:
                  device: str
                  effect: str
                summary: With specified device
              example2:
                value:
                  devices:
                    - device: str
                      effect: str
                summary: Without specified device
      "403":
        description: Input data are wrong
      "422":
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

    if not request.args:
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
    requestBody:
      description:
        The `effect` which to set for the specified `device`\n\n
        Remove `device` to apply effect to all devices
      content:
        application/json:
          schema:
            type: string
          examples:
            example1:
              value:
                device: device_0
                effect: effect_off
              summary: Set for one device
            example2:
              value:
                devices:
                  - device: device_0
                    effect: effect_off
              summary: Set for multiple devices
            example3:
              value:
                effect: effect_off
              summary: Set for all devices
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
              type: object
            examples:
              example1:
                value:
                  device: str
                  effect: str
                summary: With one device
              example2:
                value:
                  devices:
                    - device: str
                      effect: str
                summary: With multiple devices
              example3:
                value:
                  effect: str
                summary: With all devices
      "403":
        description: Input data are wrong
      "422":
        description: Unprocessable Entity
    """
    data_in = request.get_json()
    data_out = None
    if data_in:
        effect_dict = Executer.instance.general_executer.get_effects()
        # Set effect for 1 device.
        if all(key in data_in for key in ("device", "effect")):
            if not Executer.instance.effect_executer.validate_data_in(data_in, ("device", "effect",)):
                return "Input data are wrong.", 403

            data_out = Executer.instance.effect_executer.set_active_effect(data_in["device"], data_in["effect"], effect_dict)

        # Set effect for multiple devices.
        elif "devices" in data_in:
            if not Executer.instance.effect_executer.validate_data_in(data_in, ("devices",)):
                return "Input data are wrong.", 403

            data_out = Executer.instance.effect_executer.set_active_effect_for_multiple(data_in["devices"], effect_dict)

        # Set effect for all devices.
        elif "effect" in data_in:
            if not Executer.instance.effect_executer.validate_data_in(data_in, ("effect",)):
                return "Input data is wrong.", 403

            data_out = Executer.instance.effect_executer.set_active_effect_for_all(data_in["effect"], effect_dict)

        if data_out is None:
            return "Unprocessable Entity.", 422

        return jsonify(data_out)

    return "Input data are wrong.", 403


@effect_api.get('/api/effect/cycle-status')
@login_required
def get_cycle_status():  # pylint: disable=E0211
    """
    Return Random Cycle effect status
    ---
    tags:
      - Effect
    parameters:
      - description:
          ID of `device` to return Random Cycle effect status from
        name: device
        in: query
        required: true
        schema:
          type: string
        examples:
          example1:
            value: device_0
            summary: device ID
    responses:
      "200":
        description: OK
        content:
          application/json:
            schema:
              example:
                devices:
                  - device: str
                    random_cycle_active: bool
              type: object
      "403":
        description: Input data are wrong
      "422":
        description: Unprocessable Entity
    """
    data_in = request.args.to_dict()

    if not Executer.instance.effect_executer.validate_data_in(data_in, ("device",)):
        return "Input data are wrong.", 403

    result = Executer.instance.effect_executer.is_cycle_job_running(data_in["device"])

    if result is None:
        return "Unprocessable Entity.", 422

    data_out = copy.deepcopy(data_in)
    data_out["random_cycle_active"] = result
    return jsonify(data_out)
