
from libs.config_service import ConfigService # pylint: disable=E0611, E0401
from libs.effects_enum import EffectsEnum # pylint: disable=E0611, E0401
from libs.notification_enum import NotificationEnum # pylint: disable=E0611, E0401
from libs.effect_item import EffectItem # pylint: disable=E0611, E0401
from libs.notification_item import NotificationItem # pylint: disable=E0611, E0401

from flask import Flask, render_template, request, jsonify
from time import sleep

server = Flask(__name__)

class Webserver():
    def start(self, config_lock, notification_queue_in, notification_queue_out, effects_queue, effects_queue_lock):
        self._config_lock = config_lock
        self.notification_queue_in = notification_queue_in
        self.notification_queue_out = notification_queue_out
        self.effects_queue = effects_queue
        self.effects_queue_lock = effects_queue_lock

        # Initial config load.
        self._config_instance = ConfigService.instance(self._config_lock)
        self._config = self._config_instance.config

        Webserver.instance = self

        server.config["TEMPLATES_AUTO_RELOAD"] = True
        server.run(host='0.0.0.0', port=80)

        while True:
            sleep(10)

    def save_config(self):
        self._config_instance.save_config(self._config)

    def reset_config(self):
        self._config_instance.reset_config()
        self._config = self._config_instance.config

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
    @server.route('/setActiveEffect', methods=['POST'])
    def SetActiveEffect(): # pylint: disable=E0211
        # set the effect
        if request.method == 'POST':
            if request.get_json() is not None:
                # Get the data in json format.
                data = request.get_json()
                print("Set effect to: " + data["activeEffect"])
                
                if data["device"] == "all_devices":
                    for key, value in data["settings"]["device_configs"].items():
                        Webserver.instance.PutIntoEffectQueue(data["activeEffect"], key)
                else:
                    Webserver.instance.PutIntoEffectQueue(data["activeEffect"], data["device"])
                

                # Save the new active effect inside the config, to remember the last effect after a restart.
                Webserver.instance._config = data["settings"]
                Webserver.instance.save_config()
                # TODO: Put the new effect inside the effect queue
                # Handle the all_devices action.

                return "active_effect was set.", 200
            return "Could not find active effect. All I got: ", 403
        return "Invalid request. (Custom Response)", 403

    def PutIntoEffectQueue(self, effect, device):
        print("Prepare new EnumItem")
        effect_item = EffectItem(EffectsEnum[effect], device)
        print("EnumItem prepared: " + str(effect_item.effect_enum) + " " + effect_item.device_id)
        Webserver.instance.effects_queue_lock.acquire()
        Webserver.instance.effects_queue.put(effect_item)
        Webserver.instance.effects_queue_lock.release()
        print("EnumItem put into queue.")
        print("Effect queue id Webserver " + str(id(Webserver.instance.effects_queue)))

    def PutIntoNotificationQueue(self, notificication, device):
        print("Prepare new Notification")
        notification_item = NotificationItem(notificication, device)
        print("Notification Item prepared: " + str(notification_item.notification_enum) + " " + notification_item.device_id)
        #TODO Add lock
        Webserver.instance.notification_queue_out.put(notification_item)
        print("Notification Item put into queue.")

    def RefreshDevice(self, deviceId):
        self.PutIntoNotificationQueue(NotificationEnum.config_refresh, deviceId)


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
        
    @server.route('/effects/effect_beat_slide', methods=['GET', 'POST'])
    def effect_beat_slide(): # pylint: disable=E0211
        # Render the effect_beat_slide page
        return render_template('effects/effect_beat_slide.html')

    @server.route('/effects/effect_wiggle', methods=['GET', 'POST'])
    def effect_wiggle(): # pylint: disable=E0211
        # Render the effect_wiggle page
        return render_template('effects/effect_wiggle.html')

    @server.route('/effects/effect_vu_meter', methods=['GET', 'POST'])
    def effect_vu_meter(): # pylint: disable=E0211
        # Render the effect_vu_meter page
        return render_template('effects/effect_vu_meter.html')

    @server.route('/effects/effect_spectrum_analyzer', methods=['GET', 'POST'])
    def effect_spectrum_analyzer(): # pylint: disable=E0211
        # Render the effect_spectrum_analyzer page
        return render_template('effects/effect_spectrum_analyzer.html')

    #####################################################################
    #   Settings Ajax                                                   #
    #####################################################################

    # Endpoint for Ajax
    @server.route('/getSettings', methods=['GET'])
    def GetSettings(): # pylint: disable=E0211
        if request.method == 'GET':
            # Return the configuration. Not the safest way, but the esiest.
            # TODO: Increase security.
            return jsonify(Webserver.instance._config)

    #Endpoint for Ajax
    @server.route('/setSettings', methods=['POST'])
    def SetSettings(): # pylint: disable=E0211
        if request.method == 'POST':
            if request.get_json() is not None:
                # Get the data in json format.
                data = request.get_json()
                #print("Get new settings: " + str(data['settings']))

                Webserver.instance._config = data['settings']
                print("New general settings set.")
                Webserver.instance.save_config()
                Webserver.instance.RefreshDevice(data['device'])
                
                return "Settings set.", 200


    #####################################################################
    #   Helper                                                          #
    #####################################################################

