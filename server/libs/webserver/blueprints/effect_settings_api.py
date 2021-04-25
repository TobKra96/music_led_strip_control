from libs.webserver.executer import Executer

from flask import Blueprint, request, jsonify
from flask_login import login_required
import copy

effect_settings_api = Blueprint('effect_settings_api', __name__)


# /GetEffectSetting
# in
# {
# "device" = <deviceID>
# "effect" = <effectID>
# "setting_key" = <setting_key>
# }
#
# return
# {
# "device" = <deviceID>
# "effect" = <effectID>
# "setting_key" = <setting_key>
# "setting_value" = <setting_value>
# }
@effect_settings_api.route('/GetEffectSetting', methods=['GET'])
@login_required
def get_effect_setting():  # pylint: disable=E0211
    if request.method == 'GET':
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


# /GetEffectSettings
# in
# {
# "device" = <deviceID>
# "effect" = <effectID>
# }
#
# return
# {
# "device" = <deviceID>
# "effect" = <effectID>
# "settings" = {
#   "<settings_key>" = <setting_value>
# }
# }
@effect_settings_api.route('/GetEffectSettings', methods=['GET'])
@login_required
def get_effect_settings():  # pylint: disable=E0211
    if request.method == 'GET':
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


# /SetEffectSetting
# {
# "device" = <deviceID>
# "effect" = <effectID>
# "settings" = {
#   "<settings_key>" = <setting_value>
# }
# }
@effect_settings_api.route('/SetEffectSetting', methods=['POST'])
@login_required
def set_effect_setting():  # pylint: disable=E0211
    if request.method == 'POST':
        data_in = request.get_json()
        data_out = copy.deepcopy(data_in)

        if not Executer.instance.effect_settings_executer.validate_data_in(data_in, ("device", "effect", "settings", )):
            return "Input data are wrong.", 403

        Executer.instance.effect_settings_executer.set_effect_setting(data_in["device"], data_in["effect"], data_in["settings"])

        return jsonify(data_out)


# /SetEffectSettingForAll
# {
# "effect" = <effectID>
# "settings" = {
#   "<settings_key>" = <setting_value>
# }
# }
@effect_settings_api.route('/SetEffectSettingForAll', methods=['POST'])
@login_required
def set_effect_setting_for_all():  # pylint: disable=E0211
    if request.method == 'POST':
        data_in = request.get_json()
        data_out = copy.deepcopy(data_in)

        if not Executer.instance.effect_settings_executer.validate_data_in(data_in, ("effect", "settings", )):
            return "Input data are wrong.", 403

        Executer.instance.effect_settings_executer.set_effect_setting_for_all(data_in["effect"], data_in["settings"])

        return jsonify(data_out)
