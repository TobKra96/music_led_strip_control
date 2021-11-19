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
      - description: ID of `device` to return settings from
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
          Specific `setting_key` to return from device\n\n
          Return all settings if not specified
        in: query
        name: setting_key
        required: false
        schema:
          type: string
          enum:
            - device_groups
            - device_name
            - effects
            - fps
            - led_brightness
            - led_count
            - led_mid
            - led_strip
            - output
            - output_type
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
                  setting_key: str
                  setting_value: str/int/array/bool/num
                summary: With specified setting_key
              example2:
                value:
                  device: str
                  settings: object
                summary: Without specified setting_key
      "403":
        description: Input data are wrong
      "422":
        description: Unprocessable Entity
    """
    if len(request.args) == 2:  # Get one specific device setting of one device.
        data_in = request.args.to_dict()

        if not Executer.instance.device_settings_executer.validate_data_in(data_in, ("device", "setting_key",)):
            return "Input data are wrong.", 403

        result = Executer.instance.device_settings_executer.get_device_setting(data_in["device"], data_in["setting_key"])

        if result is None:
            return "Unprocessable Entity", 422

        data_out = copy.deepcopy(data_in)
        data_out["setting_value"] = result
        return jsonify(data_out)

    elif len(request.args) == 1:  # Get all device settings of a specific device.
        data_in = request.args.to_dict()

        if not Executer.instance.device_settings_executer.validate_data_in(data_in, ("device",)):
            return "Input data are wrong.", 403

        result = Executer.instance.device_settings_executer.get_device_settings(data_in["device"])

        if result is None:
            return "Unprocessable Entity.", 422

        data_out = copy.deepcopy(data_in)
        data_out["settings"] = result
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
    requestBody:
      content:
        application/json:
          schema:
            type: string
          examples:
            example1:
              value:
                device: device_0
                settings:
                  device_name: Default Device
                  fps: 60
                  led_brightness: 100
                  led_count: 124
                  led_mid: 64
                  led_strip: ws2812_strip
                  output_type: output_raspi
              summary: Default device settings
      description: The `settings` which to set for the specified `device`
      required: true
    responses:
      "200":
        description: OK
        content:
          application/json:
            schema:
              example:
                device: str
                settings:
                  device_name: str
                  fps: int
                  led_brightness: str
                  led_count: int
                  led_mid: int
                  led_strip: str
                  output_type: str
              type: object
      "403":
        description: Input data are wrong
      "422":
        description: Unprocessable Entity
    """
    data_in = request.get_json()

    if not Executer.instance.device_settings_executer.validate_data_in(data_in, ("device", "settings", )):
        return "Input data are wrong.", 403

    result = Executer.instance.device_settings_executer.set_device_setting(data_in["device"], data_in["settings"])

    if result is None:
        return "Unprocessable Entity.", 422

    data_out = copy.deepcopy(data_in)
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
      - description: The device ID
        in: query
        name: device
        required: true
        schema:
          type: string
        examples:
          example1:
            value: device_0
            summary: device ID
      - description: The output type ID
        in: query
        name: output_type_key
        required: true
        schema:
          type: string
          enum:
            - output_raspi
            - output_udp
      - description:
          "The `setting_key` for a specified `device` to get the value from\n\n
          If `output_type_key` is output_raspi, the following `setting_key` keys are allowed:\n\n
          led_channel, led_dma, led_freq_hz, led_invert, led_pin\n\n
          If `output_type_key` is output_udp, the following `setting_key` keys are allowed:\n\n
          udp_client_ip, udp_client_port"
        in: query
        name: setting_key
        required: true
        schema:
          type: string
          enum:
            - led_channel
            - led_dma
            - led_freq_hz
            - led_invert
            - led_pin
            - udp_client_ip
            - udp_client_port
    responses:
      "200":
        description: OK
        content:
          application/json:
            schema:
              example:
                device: str,
                output_type_key: str,
                setting_key: str,
                setting_value: str/int/array/bool/num
              type: object
      "403":
        description: Input data are wrong
      "422":
        description: Unprocessable Entity
    """
    data_in = request.args.to_dict()

    if not Executer.instance.device_settings_executer.validate_data_in(data_in, ("device", "output_type_key", "setting_key",)):
        return "Input data are wrong.", 403

    result = Executer.instance.device_settings_executer.get_output_type_device_setting(data_in["device"], data_in["output_type_key"], data_in["setting_key"])

    if result is None:
        return "Unprocessable Entity.", 422

    data_out = copy.deepcopy(data_in)
    data_out["setting_value"] = result
    return jsonify(data_out)


@device_settings_api.post('/api/settings/device/output-type')
@login_required
def set_output_type_device_settings():  # pylint: disable=E0211
    """
    Set a specific output-type setting for a device
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
                output_type_key: output_raspi
                settings:
                  led_channel: 0
                  led_dma: 10
                  led_freq_hz: 800000
                  led_invert: false
                  led_pin: 18
              summary: Default output_raspi settings
            example2:
              value:
                device: device_0
                output_type_key: output_udp
                settings:
                  udp_client_ip: 127.0.0.1
                  udp_client_port: 7777
              summary: Default output_udp settings
      description:
        "The output-type `settings` which to set for the specified `device`\n\n
        Available `output_type_key` keys: output_raspi, output_udp\n\n
        If `output_type_key` is output_raspi, the following `setting_key` keys are allowed:\n\n
        led_channel, led_dma, led_freq_hz, led_invert, led_pin\n\n
        If `output_type_key` is output_udp, the following `setting_key` keys are allowed:\n\n
        udp_client_ip, udp_client_port\n\n
        __Note:__ It is not required to include all above keys inside `settings`"
      required: true
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
                  output_type_key: str
                  settings:
                    led_channel: int
                    led_dma: int
                    led_freq_hz: int
                    led_invert: bool
                    led_pin: int
                summary: With output_raspi settings
              example2:
                value:
                  device: str
                  output_type_key: str
                  settings:
                    udp_client_ip: str
                    udp_client_port: str/int
                summary: With output_udp settings
      "403":
        description: Input data are wrong
      "422":
        description: Unprocessable Entity
    """
    data_in = request.get_json()

    if not Executer.instance.device_settings_executer.validate_data_in(data_in, ("device", "output_type_key", "settings", )):
        return "Input data are wrong.", 403

    result = Executer.instance.device_settings_executer.set_output_type_device_setting(data_in["device"], data_in["output_type_key"], data_in["settings"])

    if result is None:
        return "Unprocessable Entity.", 422

    data_out = copy.deepcopy(data_in)
    return jsonify(data_out)
