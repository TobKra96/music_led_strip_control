
from libs.config_service import ConfigService  # pylint: disable=E0611, E0401
from libs.webserver_executer import WebserverExecuter  # pylint: disable=E0611, E0401

from flask import Flask, render_template, request, jsonify, send_file
from time import sleep

from os.path import join, dirname, realpath
import copy
import json


server = Flask(__name__)


class Webserver():
    def start(self, config_lock, notification_queue_in, notification_queue_out, effects_queue):
        self._config_lock = config_lock
        self.notification_queue_in = notification_queue_in
        self.notification_queue_out = notification_queue_out
        self.effects_queue = effects_queue

        self.webserver_executer = WebserverExecuter(config_lock, notification_queue_in, notification_queue_out, effects_queue)
        Webserver.instance = self

        self.export_config_path = join(dirname(realpath(__file__)), 'config.json')

        server.config["TEMPLATES_AUTO_RELOAD"] = True
        webserver_port = self.webserver_executer.GetWebserverPort()
        server.run(host='0.0.0.0', port=webserver_port)

        while True:
            sleep(10)

    #####################################################################
    #   Dashboard                                                       #
    #####################################################################

    @server.route('/', methods=['GET'])
    @server.route('/index', methods=['GET'])
    @server.route('/dashboard', methods=['GET'])
    def index():  # pylint: disable=E0211
        # First handle with normal GET and render the template.
        return render_template('dashboard.html')

    #####################################################################
    #   General Settings                                                #
    #####################################################################
    @server.route('/general_settings', methods=['GET', 'POST'])
    def general_settings():  # pylint: disable=E0211
        # Render the general_settings page.
        return render_template('/general_settings/general_settings.html')

    @server.route('/export_config')
    def export_config():  # pylint: disable=E0211
        print("Send file " + Webserver.instance.export_config_path)
        return send_file(Webserver.instance.export_config_path, as_attachment=True, cache_timeout=-1)

    @server.route('/import_config', methods=['POST'])
    def import_config():  # pylint: disable=E0211
        print("Import Config Request received.")
        if 'imported_config' not in request.files:
            print("Could not find the file key.")
            return "Could not import file.", 404
        imported_config = request.files['imported_config']
        content = imported_config.read()
        print("File Received: " + str(content))
        if Webserver.instance.webserver_executer.ImportConfig(json.loads(content, encoding='utf-8')):
            return "File imported.", 200
        else:
            return "Could not import file.", 400

    #####################################################################
    #   Device Settings                                                 #
    #####################################################################
    @server.route('/device_settings', methods=['GET', 'POST'])
    def device_settings():  # pylint: disable=E0211
        # Render the device_settings page.
        return render_template('/general_settings/device_settings.html')

    #####################################################################
    #   Effects                                                         #
    #####################################################################
    @server.route('/effects/effect_single', methods=['GET', 'POST'])
    def effect_single():  # pylint: disable=E0211
        # Render the effect_single page.
        return render_template('effects/effect_single.html')

    @server.route('/effects/effect_gradient', methods=['GET', 'POST'])
    def effect_gradient():  # pylint: disable=E0211
        # Render the effect_gradient page.
        return render_template('effects/effect_gradient.html')

    @server.route('/effects/effect_fade', methods=['GET', 'POST'])
    def effect_fade():  # pylint: disable=E0211
        # Render the effect_fade page.
        return render_template('effects/effect_fade.html')

    @server.route('/effects/effect_sync_fade', methods=['GET', 'POST'])
    def effect_sync_fade():  # pylint: disable=E0211
        # Render the effect_fade page.
        return render_template('effects/effect_sync_fade.html')

    @server.route('/effects/effect_scroll', methods=['GET', 'POST'])
    def effect_scroll():  # pylint: disable=E0211
        # Render the effect_scroll page.
        return render_template('effects/effect_scroll.html')

    @server.route('/effects/effect_energy', methods=['GET', 'POST'])
    def effect_energy():  # pylint: disable=E0211
        # Render the effect_energy page.
        return render_template('effects/effect_energy.html')

    @server.route('/effects/effect_advanced_scroll', methods=['GET', 'POST'])
    def effect_advanced_scroll():  # pylint: disable=E0211
        # Render the effect_advanced_scroll page.
        return render_template('effects/effect_advanced_scroll.html')

    @server.route('/effects/effect_wavelength', methods=['GET', 'POST'])
    def effect_wavelength():  # pylint: disable=E0211
        # Render the effect_wavelength page.
        return render_template('effects/effect_wavelength.html')

    @server.route('/effects/effect_bars', methods=['GET', 'POST'])
    def effect_bars():  # pylint: disable=E0211
        # Render the effect_bars page.
        return render_template('effects/effect_bars.html')

    @server.route('/effects/effect_power', methods=['GET', 'POST'])
    def effect_power():  # pylint: disable=E0211
        # Render the effect_power page.
        return render_template('effects/effect_power.html')

    @server.route('/effects/effect_beat', methods=['GET', 'POST'])
    def effect_beat():  # pylint: disable=E0211
        # Render the effect_beat page.
        return render_template('effects/effect_beat.html')

    @server.route('/effects/effect_beat_twinkle', methods=['GET', 'POST'])
    def effect_beat_twinkle():  # pylint: disable=E0211
        # Render the effect_beat_twinkle page.
        return render_template('effects/effect_beat_twinkle.html')

    @server.route('/effects/effect_wave', methods=['GET', 'POST'])
    def effect_wave():  # pylint: disable=E0211
        # Render the effect_wave page.
        return render_template('effects/effect_wave.html')

    @server.route('/effects/effect_slide', methods=['GET', 'POST'])
    def effect_slide():  # pylint: disable=E0211
        # Render the effect_slide page.
        return render_template('effects/effect_slide.html')

    @server.route('/effects/effect_bubble', methods=['GET', 'POST'])
    def effect_bubble():  # pylint: disable=E0211
        # Render the effect_bubble page.
        return render_template('effects/effect_bubble.html')

    @server.route('/effects/effect_twinkle', methods=['GET', 'POST'])
    def effect_twinkle():  # pylint: disable=E0211
        # Render the effect_twinkle page.
        return render_template('effects/effect_twinkle.html')

    @server.route('/effects/effect_pendulum', methods=['GET', 'POST'])
    def effect_pendulum():  # pylint: disable=E0211
        # Render the effect_pendulum page.
        return render_template('effects/effect_pendulum.html')

    @server.route('/effects/effect_rods', methods=['GET', 'POST'])
    def effect_rods():  # pylint: disable=E0211
        # Render the effect_rods page.
        return render_template('effects/effect_rods.html')

    @server.route('/effects/effect_beat_slide', methods=['GET', 'POST'])
    def effect_beat_slide():  # pylint: disable=E0211
        # Render the effect_beat_slide page.
        return render_template('effects/effect_beat_slide.html')

    @server.route('/effects/effect_wiggle', methods=['GET', 'POST'])
    def effect_wiggle():  # pylint: disable=E0211
        # Render the effect_wiggle page.
        return render_template('effects/effect_wiggle.html')

    @server.route('/effects/effect_vu_meter', methods=['GET', 'POST'])
    def effect_vu_meter():  # pylint: disable=E0211
        # Render the effect_vu_meter page.
        return render_template('effects/effect_vu_meter.html')

    @server.route('/effects/effect_spectrum_analyzer', methods=['GET', 'POST'])
    def effect_spectrum_analyzer():  # pylint: disable=E0211
        # Render the effect_spectrum_analyzer page.
        return render_template('effects/effect_spectrum_analyzer.html')

    @server.route('/effects/effect_direction_changer', methods=['GET', 'POST'])
    def effect_direction_changer():  # pylint: disable=E0211
        # Render the effect_direction_changer page.
        return render_template('effects/effect_direction_changer.html')

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
    def GetGradients():  # pylint: disable=E0211
        if request.method == 'GET':
            data_out = dict()

            gradients = Webserver.instance.webserver_executer.GetGradients()
            data_out = gradients

            if data_out is None:
                return "Could not find gradients.", 403
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

    # /SetGeneralSetting
    # {
    # "settings" = {
    #   "<settings_key>" = <setting_value>
    # }
    # }
    @server.route('/SetGeneralSetting', methods=['POST'])
    def SetGeneralSetting():  # pylint: disable=E0211
        if request.method == 'POST':
            data_in = request.get_json()
            data_out = copy.deepcopy(data_in)

            if not Webserver.instance.webserver_executer.ValidateDataIn(data_in, ("settings", )):
                return "Input data are wrong.", 403

            Webserver.instance.webserver_executer.SetGeneralSetting(data_in["settings"])

            return jsonify(data_out)

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
    def ResetSettings():  # pylint: disable=E0211
        if request.method == 'POST':

            data_out = dict()

            Webserver.instance.webserver_executer.ResetSettings()

            return jsonify(data_out)
