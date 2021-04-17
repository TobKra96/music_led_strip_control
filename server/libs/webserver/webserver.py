from libs.webserver.executer import Executer  # pylint: disable=E0611, E0401
from libs.config_service import ConfigService  # pylint: disable=E0611, E0401

from libs.webserver.blueprints.authentication_api import authentication_api
from libs.webserver.blueprints.device_api import device_api
from libs.webserver.blueprints.device_settings_api import device_settings_api
from libs.webserver.blueprints.effect_api import effect_api
from libs.webserver.blueprints.effect_settings_api import effect_settings_api
from libs.webserver.blueprints.general_api import general_api
from libs.webserver.blueprints.general_settings_api import general_settings_api

from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user, login_required
from flask import render_template, request, jsonify, send_file, redirect, url_for, session, flash

from libs.app import create_app
from waitress import serve
from time import sleep

import logging
import copy
import json



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

        self.webserver_executer = Executer(config_lock, notification_queue_in, notification_queue_out, effects_queue, py_audio)
        Webserver.instance = self

        self.server = create_app()
        
        self.server = Executer.instance.authentication_executer.add_server_authentication(self.server)

        self.server.config["TEMPLATES_AUTO_RELOAD"] = True
        webserver_port = Executer.instance.general_settings_executer.GetWebserverPort()

        self.server.register_blueprint(authentication_api)
        self.server.register_blueprint(device_api)
        self.server.register_blueprint(device_settings_api)
        self.server.register_blueprint(effect_api)
        self.server.register_blueprint(effect_settings_api)
        self.server.register_blueprint(general_api)
        self.server.register_blueprint(general_settings_api)


        if DEBUG:
            self.server.run(host='0.0.0.0', port=webserver_port, load_dotenv=False, debug=True)
        else:
            serve(self.server, host='0.0.0.0', port=webserver_port, threads=8)

        while True:
            sleep(10)

    


