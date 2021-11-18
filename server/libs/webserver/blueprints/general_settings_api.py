from libs.webserver.executer import Executer

from flask import Blueprint, request, jsonify, send_file, flash
from flask_login import login_required
import copy
import json

general_settings_api = Blueprint('general_settings_api', __name__)


@general_settings_api.get('/api/settings/general')
@login_required
def get_general_settings():  # pylint: disable=E0211
    """
    Return general settings
    ---
    tags:
        - Settings
    parameters:
        - name: setting_key
          in: query
          type: string
          required: false
          enum: ['default_sample_rate', 'device_id', 'frames_per_buffer', 'log_file_enabled', 'log_level_console', 'log_level_file',
                 'max_frequency', 'min_frequency', 'min_volume_threshold', 'n_fft_bins', 'n_rolling_history', webserver_port]
          description: Specific `setting_key` to return from general settings\n
                       Return all settings if not specified
    responses:
        200:
            description: OK
            schema:
                type: object
                example:
                    {
                        setting_key: str,
                        setting_value: str
                    }
        403:
            description: Input data are wrong
        422:
            description: Unprocessable Entity
    """
    if len(request.args) == 1:
        data_in = request.args.to_dict()

        if not Executer.instance.general_settings_executer.validate_data_in(data_in, ("setting_key",)):
            return "Input data are wrong.", 403

        result = Executer.instance.general_settings_executer.get_general_setting(data_in["setting_key"])

        if result is None:
            return "Unprocessable Entity.", 422

        data_out = copy.deepcopy(data_in)
        data_out["setting_value"] = result
        return jsonify(data_out)

    elif len(request.args) == 0:
        # If no queries passed, return all settings.
        result = Executer.instance.general_settings_executer.get_general_settings()

        if result is None:
            return "Unprocessable Entity.", 422

        data_out = dict()
        data_out["setting_value"] = result
        return jsonify(data_out)

    return "Input data are wrong.", 403


@general_settings_api.post('/api/settings/general')
@login_required
def set_general_settings():  # pylint: disable=E0211
    """
    Set general settings
    ---
    tags:
        - Settings
    parameters:
        - name: data
          in: body
          type: string
          required: true
          description: The general settings which to set\n
          schema:
                type: object
                example:
                    {
                        settings: {
                            default_sample_rate: int,
                            device_id: str,
                            frames_per_buffer: int,
                            log_file_enabled: bool,
                            log_level_console: str,
                            log_level_file: str,
                            max_frequency: int,
                            min_frequency: int,
                            min_volume_threshold: float,
                            n_fft_bins: int,
                            n_rolling_history: int,
                            webserver_port: int
                        }
                    }
    responses:
        200:
            description: OK
            schema:
                type: object
                example:
                    {
                        settings: {
                            default_sample_rate: int,
                            device_id: str,
                            frames_per_buffer: int,
                            log_file_enabled: bool,
                            log_level_console: str,
                            log_level_file: str,
                            max_frequency: int,
                            min_frequency: int,
                            min_volume_threshold: float,
                            n_fft_bins: int,
                            n_rolling_history: int,
                            webserver_port: int
                        }
                    }
        403:
            description: Input data are wrong
        422:
            description: Unprocessable Entity
    """
    data_in = request.get_json()

    if not Executer.instance.general_settings_executer.validate_data_in(data_in, ("settings", )):
        return "Input data are wrong.", 403

    result = Executer.instance.general_settings_executer.set_general_setting(data_in["settings"])

    if result is None:
        return "Unprocessable Entity.", 422

    data_out = copy.deepcopy(data_in)
    return jsonify(data_out)


@general_settings_api.delete('/api/settings/general')
@login_required
def reset_general_settings():  # pylint: disable=E0211
    """
    Reset general settings
    ---
    tags:
        - Settings
    responses:
        200:
            description: OK
            schema:
                type: object
                example:
                    {}
        403:
            description: Input data are wrong
    """
    Executer.instance.general_settings_executer.reset_settings()

    data_out = dict()
    return jsonify(data_out)


@general_settings_api.get('/api/settings/configuration/file')
@login_required
def export_config():  # pylint: disable=E0211
    """
    Export configuration file
    ---
    tags:
        - Settings
    responses:
        200:
            description: OK
    """
    Executer.instance.logger.debug(f"Send file: {Executer.instance.general_settings_executer.export_config_path}")
    return send_file(Executer.instance.general_settings_executer.export_config_path, as_attachment=True, cache_timeout=-1, mimetype="text/html")


@general_settings_api.post('/api/settings/configuration/file')
@login_required
def import_config():  # pylint: disable=E0211
    """
    Import configuration file
    ---
    tags:
        - Settings
    consumes:
        - multipart/form-data
    parameters:
        - name: imported_config
          in: formData
          type: file
          required: true
          description: Upload config file.
    responses:
        200:
            description: OK
        400:
            description: Could not import file
        404:
            description: No config file selected
        415:
            description: Unsupported media type
    """
    Executer.instance.logger.debug("Import Config Request received.")
    if 'imported_config' not in request.files:
        Executer.instance.logger.error("Could not find the file key.")
        flash('No config file selected', 'error')
        return "No config file selected.", 404
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
            return "Unsupported media type.", 415
    else:
        flash('No config file selected', 'error')
        return "No config file selected.", 404
