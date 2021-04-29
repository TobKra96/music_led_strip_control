from libs.webserver.executer import Executer

from flask import Blueprint, request, jsonify
from flask_login import login_required
import copy

effect_api = Blueprint('effect_api', __name__)


@effect_api.route('/api/effect/active', methods=['GET', 'POST'])
@login_required
def active_effect():  # pylint: disable=E0211
    if request.method == 'GET':
        if len(request.args) == 1:
            # Retrieve the active effect for specific device.
            data_in = request.args.to_dict()
            data_out = copy.deepcopy(data_in)

            if not Executer.instance.effect_executer.validate_data_in(data_in, ("device",)):
                return "Input data are wrong.", 403

            active_effect = Executer.instance.effect_executer.get_active_effect(data_in["device"])
            data_out["effect"] = active_effect

            if active_effect is None:
                return "Could not find active effect: ", 403
            else:
                return jsonify(data_out)

        return "Input data are wrong.", 403

    elif request.method == 'POST':
        data_in = request.get_json()
        if all(key in data_in for key in ("device", "effect")):
            # Save the active effect for specific device.
            data_out = copy.deepcopy(data_in)

            if not Executer.instance.effect_executer.validate_data_in(data_in, ("device", "effect",)):
                return "Input data are wrong.", 403

            Executer.instance.effect_executer.set_active_effect(data_in["device"], data_in["effect"])

            return jsonify(data_out)

        elif all(key in data_in for key in ("effect")):
            # Save the active effect for all devices.
            data_out = copy.deepcopy(data_in)

            if not Executer.instance.effect_executer.validate_data_in(data_in, ("effect",)):
                return "Input data is wrong.", 403

            Executer.instance.effect_executer.set_active_effect_for_all(data_in["effect"])

            return jsonify(data_out)

        return "Input data are wrong.", 403
