
from libs.config_service import ConfigService # pylint: disable=E0611, E0401
from libs.effects_enum import EffectsEnum # pylint: disable=E0611, E0401
from libs.notification_enum import NotificationEnum # pylint: disable=E0611, E0401

from flask import Flask, render_template, request, jsonify
from time import sleep

server = Flask(__name__)

class Webserver():
    def start(self, config_lock, notification_queue_in, notification_queue_out, effects_queue):
        self._config_lock = config_lock
        self._notification_queue_in = notification_queue_in
        self._notification_queue_out = notification_queue_out
        self._effects_queue = effects_queue

        # Initial config load.
        self._config_instance = ConfigService.instance(self._config_lock)
        self._config = self._config_instance.config
        self._current_effect = self._config["effects"]["last_effect"]

        Webserver.instance = self

        server.config["TEMPLATES_AUTO_RELOAD"] = True
        server.run(host='0.0.0.0', port=80)

        while True:
            sleep(10)

    def save_config(self):
        self._config_instance.save_config(self._config)
        self._notification_queue_out.put(NotificationEnum.config_refresh)

    def reset_config(self):
        self._config_instance.reset_config()
        self._config = self._config_instance.config
        self._notification_queue_out.put(NotificationEnum.config_refresh)

    @server.route('/', methods=['GET'])
    @server.route('/index', methods=['GET'])
    @server.route('/dashboard', methods=['GET'])
    def index(): # pylint: disable=E0211
        # First hanle with normal get and render the template
        return render_template('dashboard.html')

    #####################################################################
    #   Dashboard                                                       #
    #####################################################################

    # Endpoint for Ajax
    @server.route('/getActiveEffect', methods=['GET'])
    def getActiveEffect(): # pylint: disable=E0211
        # return the current effect if the request is valid.
        if request.method == 'GET':
            if request.args.get('active_effect') is not None:
                return jsonify(active_effect = Webserver.instance._current_effect)

    # Endpoint for Ajax
    @server.route('/setActiveEffect', methods=['POST'])
    def setActiveEffect(): # pylint: disable=E0211
        # set the effect
        if request.method == 'POST':
            if request.get_json() is not None:
                # Get the data in json format.
                data = request.get_json()
                print("Set effect to: " + data)
                
                # Save the new active effect inside the config, to remember the last effect after a restart.
                Webserver.instance._current_effect = data
                Webserver.instance._config["effects"]["last_effect"] = data
                Webserver.instance.save_config()

                # Now send the new effect via effects queue to the effects process.
                Webserver.instance._effects_queue.put(EffectsEnum[data])

                return "active_effect was set.", 200
            return "Could not find active effect. All I got: ", 403
        return "Invalid request. (Custom Response)", 403

    #####################################################################
    #   General Settings                                                #
    #####################################################################
    @server.route('/device_settings', methods=['GET', 'POST'])
    def device_settings(): # pylint: disable=E0211
        # Render the general settings page
        return render_template('/general_settings/device_settings.html')

    @server.route('/audio_settings', methods=['GET', 'POST'])
    def audio_settings(): # pylint: disable=E0211
        # Render the audio settings page
        return render_template('/general_settings/audio_settings.html')

    @server.route('/reset_settings', methods=['GET', 'POST'])
    def reset_settings(): # pylint: disable=E0211
        # Render the reset settings page
        return render_template('/general_settings/reset_settings.html')

    @server.route('/reset_settings/reset', methods=['POST'])
    def reset_settings_command(): # pylint: disable=E0211
        Webserver.instance.reset_config()
        return "Settings resetted.", 200

    #####################################################################
    #   Effects                                                         #
    #####################################################################
    @server.route('/effects/effect_single', methods=['GET', 'POST'])
    def effect_single(): # pylint: disable=E0211
        # Render the effect_single page
        return render_template('effects/effect_single.html')

    @server.route('/effects/effect_gradient', methods=['GET', 'POST'])
    def effect_gradient(): # pylint: disable=E0211
        # Render the effect_gradient page
        return render_template('effects/effect_gradient.html')

    @server.route('/effects/effect_fade', methods=['GET', 'POST'])
    def effect_fade(): # pylint: disable=E0211
        # Render the effect_fade page
        return render_template('effects/effect_fade.html')

    @server.route('/effects/effect_scroll', methods=['GET', 'POST'])
    def effect_scroll(): # pylint: disable=E0211
        # Render the effect_scroll page
        return render_template('effects/effect_scroll.html')

    @server.route('/effects/effect_energy', methods=['GET', 'POST'])
    def effect_energy(): # pylint: disable=E0211
        # Render the effect_energy page
        return render_template('effects/effect_energy.html')

    @server.route('/effects/effect_wavelength', methods=['GET', 'POST'])
    def effect_wavelength(): # pylint: disable=E0211
        # Render the effect_wavelength page
        return render_template('effects/effect_wavelength.html')

    @server.route('/effects/effect_bars', methods=['GET', 'POST'])
    def effect_bars(): # pylint: disable=E0211
        # Render the effect_bars page
        return render_template('effects/effect_bars.html')

    @server.route('/effects/effect_power', methods=['GET', 'POST'])
    def effect_power(): # pylint: disable=E0211
        # Render the effect_power page
        return render_template('effects/effect_power.html')

    @server.route('/effects/effect_beat', methods=['GET', 'POST'])
    def effect_beat(): # pylint: disable=E0211
        # Render the effect_beat page
        return render_template('effects/effect_beat.html')

    @server.route('/effects/effect_wave', methods=['GET', 'POST'])
    def effect_wave(): # pylint: disable=E0211
        # Render the effect_wave page
        return render_template('effects/effect_wave.html')

    @server.route('/effects/effect_slide', methods=['GET', 'POST'])
    def effect_slide(): # pylint: disable=E0211
        # Render the effect_slide page
        return render_template('effects/effect_slide.html')

    @server.route('/effects/effect_bubble', methods=['GET', 'POST'])
    def effect_bubble(): # pylint: disable=E0211
        # Render the effect_bubble page
        return render_template('effects/effect_bubble.html')

    @server.route('/effects/effect_twinkle', methods=['GET', 'POST'])
    def effect_twinkle(): # pylint: disable=E0211
        # Render the effect_twinkle page
        return render_template('effects/effect_twinkle.html') 
        
    @server.route('/effects/effect_pendulum', methods=['GET', 'POST'])
    def effect_pendulum(): # pylint: disable=E0211
        # Render the effect_pendulum page
        return render_template('effects/effect_pendulum.html')
            
    @server.route('/effects/effect_rods', methods=['GET', 'POST'])
    def effect_rods(): # pylint: disable=E0211
        # Render the effect_rods page
        return render_template('effects/effect_rods.html')

    #####################################################################
    #   Settings Ajax                                                   #
    #####################################################################

    # Endpoint for Ajax
    @server.route('/getSettings', methods=['GET'])
    def getSettings(): # pylint: disable=E0211
        if request.method == 'GET':
            # Return the configuration. Not the safest way, but the esiest.
            # TODO: Increase security.
            return jsonify(Webserver.instance._config)

    #Endpoint for Ajax
    @server.route('/setSettings', methods=['POST'])
    def setSettings(): # pylint: disable=E0211
        if request.method == 'POST':
            if request.get_json() is not None:
                # Get the data in json format.
                data = request.get_json()
                #print("Get new settings: " + str(data['settings']))

                Webserver.instance._config = data['settings']
                print("New general settings set.")
                Webserver.instance.save_config()
                
                return "Settings set.", 200


