from libs.webserver_executer import WebserverExecuter  # pylint: disable=E0611, E0401
from libs.config_service import ConfigService  # pylint: disable=E0611, E0401

from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user, login_required
from flask import render_template, request, jsonify, send_file, redirect, url_for, session, flash
from configparser import ConfigParser, ParsingError, MissingSectionHeaderError
from urllib.parse import urlparse, urljoin
from libs.app import create_app
from waitress import serve
from time import sleep
from os import chmod
import logging
import copy
import json
import re


default_values = {
    "DEFAULT_PIN": "",
    "USE_PIN_LOCK": False
}

pin_config = ConfigParser()
pin_file = '../security.ini'
DEFAULT_PIN = default_values["DEFAULT_PIN"]
USE_PIN_LOCK = default_values["USE_PIN_LOCK"]


def save_pin_file():
    with open(pin_file, 'w') as configfile:
        pin_config.write(configfile)
        chmod(pin_file, 775)


def reset_pin_file():
    for section in pin_config.sections():
        pin_config.remove_section(section)
    pin_config["SECURITY"] = default_values
    save_pin_file()


# Check if .ini file exists and if security options are valid.
try:
    dataset = pin_config.read(pin_file)
except (ParsingError, MissingSectionHeaderError):
    reset_pin_file()
    dataset = pin_config.read(pin_file)
if pin_file in dataset:
    try:
        DEFAULT_PIN = pin_config['SECURITY'].get('DEFAULT_PIN')
        USE_PIN_LOCK = pin_config['SECURITY'].getboolean('USE_PIN_LOCK')
    except (ValueError, KeyError):
        reset_pin_file()
else:
    reset_pin_file()


def validate_pin(pin):
    return bool(re.fullmatch(r"\d{4,8}", pin))


if not validate_pin(DEFAULT_PIN) and USE_PIN_LOCK:
    raise ValueError("PIN must be from 4 to 8 digits.")


# Flask DEBUG switch.
DEBUG = False


server = create_app()

login_manager = LoginManager()
server.secret_key = 'secretkey'
if not USE_PIN_LOCK:
    server.config['LOGIN_DISABLED'] = True
login_manager.init_app(server)


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


class User(UserMixin):
    id = 1001


@login_manager.user_loader
def user_loader(user_id):
    if not USE_PIN_LOCK:
        return
    user = User()
    user.id = user_id
    return user


@login_manager.unauthorized_handler
def unauthorized():
    session['next'] = request.path
    return redirect(url_for('login', next=session['next']))


@server.before_first_request
def first():
    if USE_PIN_LOCK:
        logout_user()


@server.route('/login', methods=['GET', 'POST'])
def login():
    if not USE_PIN_LOCK:
        return redirect("/")
    if request.method == 'POST':
        pin = request.form.get('pin')
        if 'next' in request.args:
            session['next'] = request.args['next']
        else:
            session['next'] = None
        if not pin:
            flash('PIN is required')
            return redirect(url_for('login', next=session['next']))
        if not pin.isdigit():
            flash('PIN must only contain digits')
            return redirect(url_for('login', next=session['next']))
        if not validate_pin(pin):
            flash('PIN must be at least 4 digits long')
            return redirect(url_for('login', next=session['next']))
        if pin != DEFAULT_PIN:
            flash('Invalid PIN')
            return redirect(url_for('login', next=session['next']))
        elif pin == DEFAULT_PIN:
            user = User()
            login_user(user)
            if session['next'] is not None:
                if is_safe_url(session['next']):
                    return redirect(session['next'])
            return redirect("/")
    return render_template('login.html')


@server.route('/logout')
def logout():
    if current_user.is_authenticated:
        logout_user()
    return redirect(url_for('login'))


class Webserver():
    def start(self, config_lock, notification_queue_in, notification_queue_out, effects_queue):
        self.logger = logging.getLogger(__name__)

        self._config_lock = config_lock
        self.notification_queue_in = notification_queue_in
        self.notification_queue_out = notification_queue_out
        self.effects_queue = effects_queue

        self.webserver_executer = WebserverExecuter(config_lock, notification_queue_in, notification_queue_out, effects_queue)
        Webserver.instance = self

        config_instance = ConfigService.instance(self._config_lock)
        self.export_config_path = config_instance.get_config_path()

        server.config["TEMPLATES_AUTO_RELOAD"] = True
        webserver_port = self.webserver_executer.GetWebserverPort()

        if DEBUG:
            server.run(host='0.0.0.0', port=webserver_port, load_dotenv=False, debug=True)
        else:
            serve(server, host='0.0.0.0', port=webserver_port, threads=8)

        while True:
            sleep(10)

    @server.route('/export_config')
    @login_required
    def export_config():  # pylint: disable=E0211
        Webserver.instance.logger.debug(f"Send file: {Webserver.instance.export_config_path}")
        return send_file(Webserver.instance.export_config_path, as_attachment=True, cache_timeout=-1, mimetype="text/html")

    @server.route('/import_config', methods=['POST'])
    @login_required
    def import_config():  # pylint: disable=E0211
        Webserver.instance.logger.debug("Import Config Request received.")
        if 'imported_config' not in request.files:
            Webserver.instance.logger.error("Could not find the file key.")
            return "Could not import file.", 404
        imported_config = request.files['imported_config']
        content = imported_config.read()
        if content:
            try:
                Webserver.instance.logger.debug(f"File Received: {json.dumps(json.loads(content), indent=4)}")
                if Webserver.instance.webserver_executer.ImportConfig(json.loads(content, encoding='utf-8')):
                    return "File imported.", 200
                else:
                    return "Could not import file.", 400
            except (json.decoder.JSONDecodeError, UnicodeDecodeError):
                return "File is not valid JSON.", 400
        else:
            return "No config file selected.", 400

    #####################################################################
    #   Ajax Endpoints                                                  #
    #####################################################################

    # /GetDevices
    # in
    # {
    # }

    # return
    # {
    # "<device_id1>" = <device_name1>
    # "<device_id2>" = <device_name2>
    # "<device_id3>" = <device_name3>
    # ...
    # }

    @server.route('/GetDevices', methods=['GET'])
    @login_required
    def GetDevices():  # pylint: disable=E0211
        if request.method == 'GET':
            data_out = dict()

            devices = Webserver.instance.webserver_executer.GetDevices()
            data_out = devices

            if devices is None:
                return "Could not find devices: ", 403
            else:
                return jsonify(data_out)

    #################################################################

    # /GetActiveEffect
    # in
    # {
    # "device" = <deviceID>
    # }

    # return
    # {
    # "device" = <deviceID>
    # "effect" = <effectID>
    # }
    @server.route('/GetActiveEffect', methods=['GET'])
    @login_required
    def GetActiveEffect():  # pylint: disable=E0211
        if request.method == 'GET':
            data_in = request.args.to_dict()
            data_out = copy.deepcopy(data_in)

            if not Webserver.instance.webserver_executer.ValidateDataIn(data_in, ("device",)):
                return "Input data are wrong.", 403

            active_effect = Webserver.instance.webserver_executer.GetActiveEffect(data_in["device"])
            data_out["effect"] = active_effect

            if active_effect is None:
                return "Could not find active effect: ", 403
            else:
                return jsonify(data_out)

    # /SetActiveEffect
    # {
    # "device" = <deviceID>
    # "effect" = <effectID>
    # }
    @server.route('/SetActiveEffect', methods=['POST'])
    @login_required
    def SetActiveEffect():  # pylint: disable=E0211
        if request.method == 'POST':
            data_in = request.get_json()
            data_out = copy.deepcopy(data_in)

            if not Webserver.instance.webserver_executer.ValidateDataIn(data_in, ("device", "effect",)):
                return "Input data are wrong.", 403

            Webserver.instance.webserver_executer.SetActiveEffect(data_in["device"], data_in["effect"])

            return jsonify(data_out)

    # SetActiveEffectForAll
    # {
    # "effect" = <effectID>
    # }
    @server.route('/SetActiveEffectForAll', methods=['POST'])
    @login_required
    def SetActiveEffectForAll():  # pylint: disable=E0211
        if request.method == 'POST':
            data_in = request.get_json()
            data_out = copy.deepcopy(data_in)

            if not Webserver.instance.webserver_executer.ValidateDataIn(data_in, ("effect",)):
                return "Input data is wrong.", 403

            Webserver.instance.webserver_executer.SetActiveEffectForAll(data_in["effect"])

            return jsonify(data_out)

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
    @server.route('/GetEffectSetting', methods=['GET'])
    @login_required
    def GetEffectSetting():  # pylint: disable=E0211
        if request.method == 'GET':
            data_in = request.args.to_dict()
            data_out = copy.deepcopy(data_in)

            if not Webserver.instance.webserver_executer.ValidateDataIn(data_in, ("device", "effect", "setting_key",)):
                return "Input data are wrong.", 403

            setting_value = Webserver.instance.webserver_executer.GetEffectSetting(data_in["device"], data_in["effect"], data_in["setting_key"])
            data_out["setting_value"] = setting_value

            if setting_value is None:
                return "Could not find settings value: ", 403
            else:
                return jsonify(data_out)

    # /GetColors
    #
    # return
    # {
    # "<colorID1>" = <colorName1>
    # "<colorID2>" = <colorName2>
    # "<colorID3>" = <colorName3>
    # ...
    # }
    @server.route('/GetColors', methods=['GET'])
    @login_required
    def GetColors():  # pylint: disable=E0211
        if request.method == 'GET':
            data_out = dict()

            colors = Webserver.instance.webserver_executer.GetColors()
            data_out = colors

            if data_out is None:
                return "Could not find colors.", 403
            else:
                return jsonify(data_out)

    # /GetGradients
    #
    # return
    # {
    # "<gradientID1>" = <gradientName1>
    # "<gradientID2>" = <gradientName2>
    # "<gradientID3>" = <gradientName3>
    # ...
    # }
    @server.route('/GetGradients', methods=['GET'])
    @login_required
    def GetGradients():  # pylint: disable=E0211
        if request.method == 'GET':
            data_out = dict()

            gradients = Webserver.instance.webserver_executer.GetGradients()
            data_out = gradients

            if data_out is None:
                return "Could not find gradients.", 403
            else:
                return jsonify(data_out)

    # /GetLEDStrips
    #
    # return
    # {
    # "<LEDStripID1>" = <LEDStripName1>
    # "<LEDStripID2>" = <LEDStripName2>
    # "<LEDStripID3>" = <LEDStripName3>
    # ...
    # }
    @server.route('/GetLEDStrips', methods=['GET'])
    @login_required
    def GetLEDStrips():  # pylint: disable=E0211
        if request.method == 'GET':
            data_out = dict()

            led_strips = Webserver.instance.webserver_executer.GetLEDStrips()
            data_out = led_strips

            if data_out is None:
                return "Could not find led_strips.", 403
            else:
                return jsonify(data_out)

    # /GetLoggingLevels
    #
    # return
    # {
    # "<GetLoggingLevelID1>" = <LoggingLevelName1>
    # "<GetLoggingLevelID2>" = <LoggingLevelName2>
    # "<GetLoggingLevelID3>" = <LoggingLevelName3>
    # ...
    # }
    @server.route('/GetLoggingLevels', methods=['GET'])
    @login_required
    def GetLoggingLevels():  # pylint: disable=E0211
        if request.method == 'GET':
            data_out = dict()

            logging_levels = Webserver.instance.webserver_executer.GetLoggingLevels()
            data_out = logging_levels

            if data_out is None:
                return "Could not find logging_levels.", 403
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
    @server.route('/SetEffectSetting', methods=['POST'])
    @login_required
    def SetEffectSetting():  # pylint: disable=E0211
        if request.method == 'POST':
            data_in = request.get_json()
            data_out = copy.deepcopy(data_in)

            if not Webserver.instance.webserver_executer.ValidateDataIn(data_in, ("device", "effect", "settings", )):
                return "Input data are wrong.", 403

            Webserver.instance.webserver_executer.SetEffectSetting(data_in["device"], data_in["effect"], data_in["settings"])

            return jsonify(data_out)

    # /SetEffectSettingForAll
    # {
    # "effect" = <effectID>
    # "settings" = {
    #   "<settings_key>" = <setting_value>
    # }
    # }
    @server.route('/SetEffectSettingForAll', methods=['POST'])
    @login_required
    def SetEffectSettingForAll():  # pylint: disable=E0211
        if request.method == 'POST':
            data_in = request.get_json()
            data_out = copy.deepcopy(data_in)

            if not Webserver.instance.webserver_executer.ValidateDataIn(data_in, ("effect", "settings", )):
                return "Input data are wrong.", 403

            Webserver.instance.webserver_executer.SetEffectSettingForAll(data_in["effect"], data_in["settings"])

            return jsonify(data_out)

    #################################################################

    # /GetGeneralSetting
    # in
    # {
    # "setting_key" = <setting_key>
    # }
    #
    # return
    # {
    # "setting_key" = <setting_key>
    # "setting_value" = <setting_value>
    # }
    @server.route('/GetGeneralSetting', methods=['GET'])
    @login_required
    def GetGeneralSetting():  # pylint: disable=E0211
        if request.method == 'GET':
            data_in = request.args.to_dict()
            data_out = copy.deepcopy(data_in)

            if not Webserver.instance.webserver_executer.ValidateDataIn(data_in, ("setting_key",)):
                return "Input data are wrong.", 403

            setting_value = Webserver.instance.webserver_executer.GetGeneralSetting(data_in["setting_key"])
            data_out["setting_value"] = setting_value

            if setting_value is None:
                return "Could not find settings value: ", 403
            else:
                return jsonify(data_out)

    @server.route('/GetPinSetting', methods=['GET'])
    @login_required
    def GetPinSetting():  # pylint: disable=E0211
        data = {
            "DEFAULT_PIN": DEFAULT_PIN,
            "USE_PIN_LOCK": USE_PIN_LOCK
        }
        return jsonify(data)

    # /SetGeneralSetting
    # {
    # "settings" = {
    #   "<settings_key>" = <setting_value>
    # }
    # }
    @server.route('/SetGeneralSetting', methods=['POST'])
    @login_required
    def SetGeneralSetting():  # pylint: disable=E0211
        if request.method == 'POST':
            data_in = request.get_json()
            data_out = copy.deepcopy(data_in)

            if not Webserver.instance.webserver_executer.ValidateDataIn(data_in, ("settings", )):
                return "Input data are wrong.", 403

            Webserver.instance.webserver_executer.SetGeneralSetting(data_in["settings"])

            return jsonify(data_out)

    @server.route('/SetPinSetting', methods=['POST'])
    @login_required
    def SetPinSetting():  # pylint: disable=E0211
        data = request.get_json()
        new_pin = data["DEFAULT_PIN"]
        use_pin_lock = data["USE_PIN_LOCK"]

        new_values = {
            "DEFAULT_PIN": new_pin,
            "USE_PIN_LOCK": use_pin_lock
        }
        pin_config["SECURITY"] = new_values
        save_pin_file()
        return jsonify(data)

    #################################################################

    # /GetDeviceSetting
    # in
    # {
    # "device" = <deviceID>
    # "setting_key" = <setting_key>
    # }
    #
    # return
    # {
    # "device" = <deviceID>
    # "setting_key" = <setting_key>
    # "setting_value" = <setting_value>
    # }
    @server.route('/GetDeviceSetting', methods=['GET'])
    @login_required
    def GetDeviceSetting():  # pylint: disable=E0211
        if request.method == 'GET':
            data_in = request.args.to_dict()
            data_out = copy.deepcopy(data_in)

            if not Webserver.instance.webserver_executer.ValidateDataIn(data_in, ("device", "setting_key",)):
                return "Input data are wrong.", 403

            setting_value = Webserver.instance.webserver_executer.GetDeviceSetting(data_in["device"], data_in["setting_key"])
            data_out["setting_value"] = setting_value

            if setting_value is None:
                return "Could not find settings value: ", 403
            else:
                return jsonify(data_out)

    # /SetDeviceSetting
    # {
    # "device" = <deviceID>
    # "settings" = {
    #   "<settings_key>" = <setting_value>
    # }
    # }
    @server.route('/SetDeviceSetting', methods=['POST'])
    @login_required
    def SetDeviceSetting():  # pylint: disable=E0211
        if request.method == 'POST':
            data_in = request.get_json()
            data_out = copy.deepcopy(data_in)

            if not Webserver.instance.webserver_executer.ValidateDataIn(data_in, ("device", "settings", )):
                return "Input data are wrong.", 403

            Webserver.instance.webserver_executer.SetDeviceSetting(data_in["device"], data_in["settings"])

            return jsonify(data_out)

    # /GetOutputTypes
    #
    # return
    # {
    # "<outputTypeID1>" = <outputTypeName1>
    # "<outputTypeID2>" = <outputTypeName2>
    # "<outputTypeID3>" = <outputTypeName3>
    # ...
    # }
    @server.route('/GetOutputTypes', methods=['GET'])
    @login_required
    def GetOutputTypes():  # pylint: disable=E0211
        if request.method == 'GET':
            data_out = dict()

            output_types = Webserver.instance.webserver_executer.GetOutputTypes()
            data_out = output_types

            if data_out is None:
                return "Could not find output_types.", 403
            else:
                return jsonify(data_out)

    # /GetOutputTypeDeviceSetting
    # in
    # {
    # "device" = <deviceID>
    # "output_type_key" = <output_type_key>
    # "setting_key" = <setting_key>
    # }
    #
    # return
    # {
    # "device" = <deviceID>
    # "output_type_key" = <output_type_key>
    # "setting_key" = <setting_key>
    # "setting_value" = <setting_value>
    # }
    @server.route('/GetOutputTypeDeviceSetting', methods=['GET'])
    @login_required
    def GetOutputTypeDeviceSetting():  # pylint: disable=E0211
        if request.method == 'GET':
            data_in = request.args.to_dict()
            data_out = copy.deepcopy(data_in)

            if not Webserver.instance.webserver_executer.ValidateDataIn(data_in, ("device", "output_type_key", "setting_key",)):
                return "Input data are wrong.", 403

            setting_value = Webserver.instance.webserver_executer.GetOutputTypeDeviceSetting(data_in["device"], data_in["output_type_key"], data_in["setting_key"])
            data_out["setting_value"] = setting_value

            if setting_value is None:
                return "Could not find settings value: ", 403
            else:
                return jsonify(data_out)

    # /SetOutputTypeDeviceSetting
    # {
    # "device" = <deviceID>
    # "output_type_key" = <output_type_key>
    # "settings" = {
    #   "<settings_key>" = <setting_value>
    # }
    # }
    @server.route('/SetOutputTypeDeviceSetting', methods=['POST'])
    @login_required
    def SetOutputTypeDeviceSetting():  # pylint: disable=E0211
        if request.method == 'POST':
            data_in = request.get_json()
            data_out = copy.deepcopy(data_in)

            if not Webserver.instance.webserver_executer.ValidateDataIn(data_in, ("device", "output_type_key", "settings", )):
                return "Input data are wrong.", 403

            Webserver.instance.webserver_executer.SetOutputTypeDeviceSetting(data_in["device"], data_in["output_type_key"], data_in["settings"])

            return jsonify(data_out)

    # /CreateNewDevice
    # {
    # }
    @server.route('/CreateNewDevice', methods=['POST'])
    @login_required
    def CreateNewDevice():  # pylint: disable=E0211
        if request.method == 'POST':

            data_out = dict()

            Webserver.instance.webserver_executer.CreateNewDevice()

            return jsonify(data_out)

    # /DeleteDevice
    # {
    # "device" = <deviceID>
    # }
    @server.route('/DeleteDevice', methods=['POST'])
    @login_required
    def DeleteDevice():  # pylint: disable=E0211
        if request.method == 'POST':
            data_in = request.get_json()
            data_out = copy.deepcopy(data_in)

            if not Webserver.instance.webserver_executer.ValidateDataIn(data_in, ("device",)):
                return "Input data are wrong.", 403

            Webserver.instance.webserver_executer.DeleteDevice(data_in["device"])

            return jsonify(data_out)

    # /ResetSettings
    # {
    # }
    @server.route('/ResetSettings', methods=['POST'])
    @login_required
    def ResetSettings():  # pylint: disable=E0211
        if request.method == 'POST':

            data_out = dict()

            Webserver.instance.webserver_executer.ResetSettings()

            return jsonify(data_out)
