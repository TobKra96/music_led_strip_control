from libs.webserver.executer import Executer

from flask import Blueprint, request, jsonify
from flask_login import login_required

general_api = Blueprint('general_api', __name__)


@general_api.get('/api/resources/colors')
@login_required
def colors():  # pylint: disable=E0211
    """
    Return colors
    ---
    tags:
        - Resources
    responses:
        200:
            description: OK
            schema:
                type: object,
                example:
                    {
                        black: str,
                        blue: str,
                        cyan: str,
                        green: str,
                        orange: str,
                        pink: str,
                        purple: str,
                        red: str,
                        white: str,
                        yellow: str
                    }
        403:
            description: Could not find colors
        422:
            description: Unprocessable Entity
    """
    data_out = Executer.instance.general_executer.get_colors()

    if data_out is None:
        return "Unprocessable Entity.", 422

    if data_out is None:
        return "Could not find colors.", 403

    return jsonify(data_out)


@general_api.get('/api/resources/gradients')
@login_required
def gradients():  # pylint: disable=E0211
    """
    Return gradients
    ---
    tags:
        - Resources
    responses:
        200:
            description: OK
            schema:
                type: object,
                example:
                    {
                        dancefloor: str,
                        fruity: str,
                        jamaica: str,
                        jungle: str,
                        jupiter: str,
                        ocean: str,
                        peach: str,
                        rust: str,
                        safari: str,
                        spectral: str,
                        sunny: str,
                        sunset: str
                    }
        403:
            description: Could not find gradients
    """
    data_out = dict()

    gradients = Executer.instance.general_executer.get_gradients()
    data_out = gradients

    if data_out is None:
        return "Could not find gradients.", 403
    else:
        return jsonify(data_out)


@general_api.get('/api/resources/led-strips')
@login_required
def led_strips():  # pylint: disable=E0211
    """
    Return LED strips
    ---
    tags:
        - Resources
    responses:
        200:
            description: OK
            schema:
                type: object,
                example:
                    {
                        sk6812_shift_wmask: str,
                        sk6812_strip: str,
                        sk6812_strip_BGRW: str,
                        sk6812_strip_BRGW: str,
                        sk6812_strip_GBRW: str,
                        sk6812_strip_GRBW: str,
                        sk6812_strip_RBGW: str,
                        sk6812_strip_RGBW: str,
                        sk6812_strip_bgrw: str,
                        sk6812_strip_brgw: str,
                        sk6812_strip_gbrw: str,
                        sk6812_strip_grbw: str,
                        sk6812_strip_rbgw: str,
                        sk6812_strip_rgbw: str,
                        sk6812w_strip: str,
                        ws2811_strip_bgr: str,
                        ws2811_strip_brg: str,
                        ws2811_strip_gbr: str,
                        ws2811_strip_grb: str,
                        ws2811_strip_rbg: str,
                        ws2811_strip_rgb: str,
                        ws2812_strip: str
                    }
        403:
            description: Could not find led_strips
    """
    data_out = dict()

    led_strips = Executer.instance.general_executer.get_led_strips()
    data_out = led_strips

    if data_out is None:
        return "Could not find led_strips.", 403
    else:
        return jsonify(data_out)


@general_api.get('/api/resources/logging-levels')
@login_required
def logging_levels():  # pylint: disable=E0211
    """
    Return logging levels
    ---
    tags:
        - Resources
    responses:
        200:
            description: OK
            schema:
                type: object,
                example:
                    {
                        critical: str,
                        debug: str,
                        error: str,
                        info: str,
                        notset: str,
                        warning: str
                    }
        403:
            description: Could not find logging_levels
    """
    data_out = dict()

    logging_levels = Executer.instance.general_executer.get_logging_levels()
    data_out = logging_levels

    if data_out is None:
        return "Could not find logging_levels.", 403
    else:
        return jsonify(data_out)


@general_api.get('/api/resources/audio-devices')
@login_required
def audio_devices():  # pylint: disable=E0211
    """
    Return audio devices
    ---
    tags:
        - Resources
    responses:
        200:
            description: OK
            schema:
                type: object,
                example:
                    {
                        1: str,
                        2: str
                    }
        403:
            description: Could not find audio_devices
    """
    data_out = dict()

    audio_devices = Executer.instance.general_executer.get_audio_devices()
    data_out = audio_devices

    if data_out is None:
        return "Could not find audio_devices.", 403
    else:
        return jsonify(data_out)


@general_api.get('/api/resources/output-types')
@login_required
def output_types():  # pylint: disable=E0211
    """
    Return output types
    ---
    tags:
        - Resources
    responses:
        200:
            description: OK
            schema:
                type: object,
                example:
                    {
                        output_raspi: str,
                        output_udp: str
                    }
        403:
            description: Could not find output_types
    """
    data_out = dict()

    output_types = Executer.instance.general_executer.get_output_types()
    data_out = output_types

    if data_out is None:
        return "Could not find output_types.", 403
    else:
        return jsonify(data_out)


@general_api.get('/api/resources/effects')
@login_required
def effects():  # pylint: disable=E0211
    """
    Return effects and their order
    ---
    tags:
        - Resources
    responses:
        200:
            description: OK
            schema:
                type: object,
                example:
                    {
                        music: {
                            effect_name: str,
                        },
                        non_music: {
                            effect_name: str,
                        },
                        order: {
                            effect_name: int,
                        },
                        special: {
                            effect_name: str,
                        }
                    }
        403:
            description: Could not find effects
    """
    data_out = dict()

    effects = Executer.instance.general_executer.get_effects()
    data_out = effects

    if data_out is None:
        return "Could not find effects.", 403
    else:
        return jsonify(data_out)
