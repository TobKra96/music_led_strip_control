from libs.webserver.blueprints.authentication_api import authentication_api
from libs.webserver.blueprints.device_api import device_api
from libs.webserver.blueprints.device_settings_api import device_settings_api
from libs.webserver.blueprints.effect_api import effect_api
from libs.webserver.blueprints.effect_settings_api import effect_settings_api
from libs.webserver.blueprints.general_api import general_api
from libs.webserver.blueprints.general_settings_api import general_settings_api
from libs.webserver.blueprints.system_info_api import system_info_api
from libs.webserver.blueprints.microphone_settings_api import microphone_settings_api
from libs.webserver.executer import Executer  # pylint: disable=E0611, E0401
from libs.app import create_app

from flasgger import Swagger
from waitress import serve
from time import sleep
import logging

# Flask DEBUG switch.
DEBUG = False


class Webserver():
    def start(self, config_lock, notification_queue_in, notification_queue_out, effects_queue, py_audio):
        self.logger = logging.getLogger(__name__)

        self._config_lock = config_lock
        self.notification_queue_in = notification_queue_in
        self.notification_queue_out = notification_queue_out
        self.effects_queue = effects_queue
        self._py_audio = py_audio

        self.webserver_executer = Executer(
            config_lock, notification_queue_in, notification_queue_out, effects_queue, py_audio)
        Webserver.instance = self

        self.server = create_app()

        self.server = Executer.instance.authentication_executer.add_server_authentication(
            self.server)

        self.server.config["TEMPLATES_AUTO_RELOAD"] = True
        webserver_port = Executer.instance.general_settings_executer.get_webserver_port()

        api_blueprints = (
            authentication_api, device_api, device_settings_api, effect_api, effect_settings_api,
            general_api, general_settings_api, system_info_api, microphone_settings_api
        )

        for blueprint in api_blueprints:
            self.server.register_blueprint(blueprint)

        self.server.config['SWAGGER'] = {
            "specs": [
                {
                    "endpoint": 'openapi',
                    "route": '/openapi.json'
                }
            ],
            "specs_route": "/api/",
            'openapi': '3.0.3'
        }

        swagger_template = {
            "info": {
                "title": "MLSC API",
                "description": "API for communicating with the MLSC server.",
                "version": "2.3.0",
                "license": {
                    "name": 'MIT',
                    "url": 'https://github.com/TobKra96/music_led_strip_control/blob/master/LICENSE'
                }
            }
        }

        Swagger(self.server, template=swagger_template)

        if DEBUG:
            self.server.run(host='0.0.0.0', port=webserver_port,
                            load_dotenv=False, debug=True)
        else:
            serve(self.server, host='0.0.0.0', port=webserver_port, threads=8)

        while True:
            sleep(10)
