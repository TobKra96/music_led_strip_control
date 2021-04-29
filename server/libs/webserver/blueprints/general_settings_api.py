from libs.webserver.executer import Executer

from flask import Blueprint, request, jsonify, send_file, flash
from flask_login import login_required
import copy
import json

general_settings_api = Blueprint('general_settings_api', __name__)


@general_settings_api.route('/api/settings/general', methods=['GET', 'POST', 'DELETE'])
@login_required
def general_settings():  # pylint: disable=E0211
    if request.method == 'GET':
        # Retrieve settings from config.
        if len(request.args) == 1:
            data_in = request.args.to_dict()
            data_out = copy.deepcopy(data_in)

            if not Executer.instance.general_settings_executer.validate_data_in(data_in, ("setting_key",)):
                return "Input data are wrong.", 403

            setting_value = Executer.instance.general_settings_executer.get_general_setting(data_in["setting_key"])
            data_out["setting_value"] = setting_value

            if setting_value is None:
                return "Could not find settings value: ", 403
            else:
                return jsonify(data_out)

        elif len(request.args) == 0:
            # If no queries passed, return all settings.
            data_out = dict()

            settings = Executer.instance.general_settings_executer.get_general_settings()
            data_out["setting_value"] = settings

            if settings is None:
                return "Could not find settings value: ", 403
            else:
                return jsonify(data_out)

        return "Input data are wrong.", 403

    elif request.method == 'POST':
        # Save new settings to config.
        data_in = request.get_json()
        data_out = copy.deepcopy(data_in)

        if not Executer.instance.general_settings_executer.validate_data_in(data_in, ("settings", )):
            return "Input data are wrong.", 403

        Executer.instance.general_settings_executer.set_general_setting(data_in["settings"])

        return jsonify(data_out)

    elif request.method == 'DELETE':
        # Reset settings in config to default.
        data_out = dict()

        Executer.instance.general_settings_executer.reset_settings()

        return jsonify(data_out)


@general_settings_api.route('/api/settings/export')
@login_required
def export_config():  # pylint: disable=E0211
    Executer.instance.logger.debug(f"Send file: {Executer.instance.general_settings_executer.export_config_path}")
    return send_file(Executer.instance.general_settings_executer.export_config_path, as_attachment=True, cache_timeout=-1, mimetype="text/html")


@general_settings_api.route('/api/settings/import', methods=['POST'])
@login_required
def import_config():  # pylint: disable=E0211
    Executer.instance.logger.debug("Import Config Request received.")
    if 'imported_config' not in request.files:
        Executer.instance.logger.error("Could not find the file key.")
        flash('No config file selected', 'error')
        return "Could not import file.", 404
    imported_config = request.files['imported_config']
    content = imported_config.read()
    if content:
        try:
            Executer.instance.logger.debug(f"File Received: {json.dumps(json.loads(content), indent=4)}")
            if Executer.instance.general_settings_executer.import_config(json.loads(content, encoding='utf-8')):
                flash('Config file imported', 'success')
                return "File imported.", 200
            else:
                flash('Could not import config file', 'error')
                return "Could not import file.", 400
        except (json.decoder.JSONDecodeError, UnicodeDecodeError):
            flash('Not a valid config file', 'error')
            return "File is not valid JSON.", 400
    else:
        flash('No config file selected', 'error')
        return "No config file selected.", 400
