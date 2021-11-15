from libs.webserver.executer import Executer

from flask import Blueprint, request, jsonify
from flask_login import login_required
import copy

device_settings_api = Blueprint('device_settings_api', __name__)


@device_settings_api.get('/api/settings/device')
@login_required
def get_device_setting():  # pylint: disable=E0211
    """
    Return device settings
    ---
    tags:
        - Settings
    parameters:
        - name: device
          in: query
          type: string
          required: true
          description: ID of `device` to return settings from
        - name: setting_key
          in: query
          type: string
          required: false
          enum: ['device_name', 'effects', 'fps', 'led_brightness', 'led_count',
                 'led_mid', 'led_strip', 'output', 'output_type']
          description: Specific `setting_key` to return from device
    responses:
        200:
            description: OK
            schema:
                type: object,
                example:
                    {
                        device: str,
                        setting_key: str,
                        setting_value: str
                    }
        403:
            description: Input data are wrong
    """
    if len(request.args) == 2:  # Get one specific device setting of one device.
        data_in = request.args.to_dict()
        data_out = copy.deepcopy(data_in)

        if not Executer.instance.device_settings_executer.validate_data_in(data_in, ("device", "setting_key",)):
            return "Input data are wrong.", 403

        setting_value = Executer.instance.device_settings_executer.get_device_setting(data_in["device"], data_in["setting_key"])
        data_out["setting_value"] = setting_value

        if setting_value is None:
            return "Could not find settings value: ", 403
        else:
            return jsonify(data_out)

    elif len(request.args) == 1:  # Get all device settings of a specific device.
        data_in = request.args.to_dict()
        data_out = copy.deepcopy(data_in)

        if not Executer.instance.device_settings_executer.validate_data_in(data_in, ("device",)):
            return "test.", 403

        setting_values = Executer.instance.device_settings_executer.get_device_settings(data_in["device"])
        data_out["settings"] = setting_values

        if setting_values is None:
            return "Could not find settings value: ", 403
        else:
            return jsonify(data_out)

    return "Input data are wrong.", 403


@device_settings_api.post('/api/settings/device')
@login_required
def set_device_settings():  # pylint: disable=E0211
    """
    Set device settings
    ---
    tags:
        - Settings
    parameters:
        - name: data
          in: body
          type: string
          required: true
          description: The `settings` which to set for the specified `device`
          schema:
                type: object,
                example:
                    {
                        device: str,
                        settings: {
                            device_name: str,
                            fps: int,
                            led_brightness: str,
                            led_count: int,
                            led_mid: int,
                            led_strip: str,
                            output_type: str
                        }
                    }
    responses:
        200:
            description: OK
            schema:
                type: object,
                example:
                    {
                        device: str,
                        settings: {
                            device_name: str,
                            fps: int,
                            led_brightness: str,
                            led_count: int,
                            led_mid: int,
                            led_strip: str,
                            output_type: str
                        }
                    }
        403:
            description: Input data are wrong
    """
    data_in = request.get_json()
    data_out = copy.deepcopy(data_in)

    if not Executer.instance.device_settings_executer.validate_data_in(data_in, ("device", "settings", )):
        return "Input data are wrong.", 403

    Executer.instance.device_settings_executer.set_device_setting(data_in["device"], data_in["settings"])

    return jsonify(data_out)


@device_settings_api.get('/api/settings/device/output-type')
@login_required
def get_output_type_device_settings():  # pylint: disable=E0211
    """
    Return a specific output-type setting for a device
    ---
    tags:
        - Settings
    parameters:
        - name: device
          in: query
          type: string
          required: true
          description: The device ID
        - name: output_type_key
          in: query
          type: string
          required: true
          enum: ['output_raspi', 'output_udp']
          description: The output type ID
        - name: setting_key
          in: query
          type: string
          required: true
          description: The `setting_key` for a specified `device` to get the value from
    responses:
        200:
            description: OK
            schema:
                type: object,
                example:
                    {
                        device: str,
                        output_type_key: str,
                        setting_key: str,
                        setting_value: str
                    }
        403:
            description: Input data are wrong
    """
    data_in = request.args.to_dict()
    data_out = copy.deepcopy(data_in)

    if not Executer.instance.device_settings_executer.validate_data_in(data_in, ("device", "output_type_key", "setting_key",)):
        return "Input data are wrong.", 403

    setting_value = Executer.instance.device_settings_executer.get_output_type_device_setting(data_in["device"], data_in["output_type_key"], data_in["setting_key"])
    data_out["setting_value"] = setting_value

    if setting_value is None:
        return "Could not find settings value: ", 403
    else:
        return jsonify(data_out)


@device_settings_api.post('/api/settings/device/output-type')
@login_required
def set_output_type_device_settings():  # pylint: disable=E0211
    """
    Set a specific output-type setting for a device
    ---
    tags:
        - Settings
    parameters:
        - name: data
          in: body
          type: string
          required: true
          description: The output-type `settings` which to set for the specified `device`\n\n
                       Available `output_type_key` keys - output_raspi, output_udp\n\n
                       If `output_type_key` is output_raspi, the following keys are\n
                       allowed inside `settings` - led_channel, led_dma, led_freq_hz, led_invert, led_pin\n\n
                       If `output_type_key` is output_udp, the following keys are\n
                       allowed inside `settings` - udp_client_ip, udp_client_port\n\n
                       It is not required to include all above keys inside `settings`

          schema:
                type: object,
                example:
                    {
                        device: str,
                        output_type_key: str,
                        settings: {
                            led_channel: int,
                            led_dma: int,
                            led_freq_hz: int,
                            led_invert: bool,
                            led_pin: int
                        }
                    }
    responses:
        200:
            description: OK
            schema:
                type: object,
                example:
                    {
                        device: str,
                        output_type_key: str,
                        settings: {
                            led_channel: int,
                            led_dma: int,
                            led_freq_hz: int,
                            led_invert: bool,
                            led_pin: int
                        }
                    }
        403:
            description: Input data are wrong
    """
    data_in = request.get_json()
    data_out = copy.deepcopy(data_in)

    if not Executer.instance.device_settings_executer.validate_data_in(data_in, ("device", "output_type_key", "settings", )):
        return "Input data are wrong.", 403

    Executer.instance.device_settings_executer.set_output_type_device_setting(data_in["device"], data_in["output_type_key"], data_in["settings"])

    return jsonify(data_out)
