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
      - description:
          Specific `setting_key` to return from general settings\n\n
          Return all settings if not specified
        in: query
        name: setting_key
        required: false
        schema:
          type: string
          enum:
            - default_sample_rate
            - device_groups
            - device_id
            - frames_per_buffer
            - log_file_enabled
            - log_level_console
            - log_level_file
            - max_frequency
            - min_frequency
            - min_volume_threshold
            - n_fft_bins
            - n_rolling_history
            - webserver_port
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
                  setting_key: str
                  setting_value: str/num/int/array/bool
                summary: With specified setting_key
              example2:
                value:
                  setting_value:
                    default_sample_rate: int
                    device_groups: array
                    device_id: int
                    frames_per_buffer: int
                    log_file_enabled: bool
                    log_level_console: str
                    log_level_file: str
                    max_frequency: int
                    min_frequency: int
                    min_volume_threshold: num
                    n_fft_bins: int
                    n_rolling_history: int
                    webserver_port: int
                summary: Without specified setting_key
      "403":
        description: Input data are wrong
      "422":
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

    if len(request.args) == 0:
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
    requestBody:
      content:
        application/json:
          schema:
            type: object
          examples:
            example1:
              value:
                settings:
                  default_sample_rate: 48000
                  device_groups: []
                  device_id: -1
                  frames_per_buffer: 512
                  log_file_enabled: false
                  log_level_console: info
                  log_level_file: info
                  max_frequency: 16000
                  min_frequency: 50
                  min_volume_threshold: 0.001
                  n_fft_bins: 24
                  n_rolling_history: 4
                  webserver_port: 8080
              summary: Default general settings
      description: The general settings which to set
      required: true
    responses:
      "200":
        description: OK
        content:
          application/json:
            schema:
              example:
                settings:
                  default_sample_rate: int
                  device_id: str
                  frames_per_buffer: int
                  log_file_enabled: bool
                  log_level_console: str
                  log_level_file: str
                  max_frequency: int
                  min_frequency: int
                  min_volume_threshold: num
                  n_fft_bins: int
                  n_rolling_history: int
                  webserver_port: int
              type: object
      "403":
        description: Input data are wrong
      "422":
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
      "200":
        description: OK
        content:
          application/json:
            schema:
              type: object
      "403":
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
        "200":
          description: OK
          content:
            multipart/form-data:
              schema:
                type: string
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
    requestBody:
      content:
        multipart/form-data:
          schema:
            type: object
            properties:
              imported_config:
                description: Upload config file.
                type: string
                format: binary
            required:
              - imported_config
    responses:
      "200":
        description: OK
        content:
          application/json:
            schema:
              type: string
      "400":
        description: Could not import file
      "404":
        description: No config file selected
      "415":
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
            if Executer.instance.general_settings_executer.import_config(json.loads(content)):
                flash('Config file imported', 'success')
                return "File imported.", 200
            flash('Could not import config file', 'error')
            return "Could not import file.", 400
        except (json.decoder.JSONDecodeError, UnicodeDecodeError):
            flash('Not a valid config file', 'error')
            return "Unsupported media type.", 415
    else:
        flash('No config file selected', 'error')
        return "No config file selected.", 404
