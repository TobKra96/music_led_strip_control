from __future__ import annotations

from time import sleep

from flask_openapi3 import OpenAPI
from waitress import serve

from mlsc import operations
from mlsc.api.v2 import register_api_v2
from mlsc.app import create_app
from mlsc.webserver.blueprints.authentication_api import authentication_api
from mlsc.webserver.blueprints.device_api import device_api
from mlsc.webserver.blueprints.device_settings_api import device_settings_api
from mlsc.webserver.blueprints.effect_api import effect_api
from mlsc.webserver.blueprints.effect_settings_api import effect_settings_api
from mlsc.webserver.blueprints.general_api import general_api
from mlsc.webserver.blueprints.general_settings_api import general_settings_api
from mlsc.webserver.blueprints.microphone_settings_api import microphone_settings_api
from mlsc.webserver.blueprints.system_info_api import system_info_api
from mlsc.webserver.deprecation import register_v1_deprecation
from mlsc.webserver.executer import Executer
from mlsc.webserver.mic_level_publisher import MIC_LEVEL_POLL_SECONDS
from mlsc.webserver.mic_level_publisher import create_mic_level_publisher
from mlsc.webserver.status_publisher import create_status_publisher, start_status_publisher

API_BLUEPRINTS = (
    authentication_api, device_api, device_settings_api, effect_api, effect_settings_api,
    general_api, general_settings_api, system_info_api, microphone_settings_api
)


def register_api_blueprints(server: OpenAPI) -> None:
    for blueprint in API_BLUEPRINTS:
        server.register_api(blueprint)
    register_v1_deprecation(server)
    register_api_v2(server)


# Flask DEBUG switch.
DEBUG = False


class Webserver:
    def start(self: Webserver, config_lock, notification_queue_in, notification_queue_out, effects_queue, audio_backend, mic_level=None) -> None:
        self._config_lock = config_lock
        self.notification_queue_in = notification_queue_in
        self.notification_queue_out = notification_queue_out
        self.effects_queue = effects_queue
        self._audio_backend = audio_backend

        self.webserver_executer = Executer(
            config_lock, notification_queue_in, notification_queue_out, effects_queue, audio_backend)
        Webserver.instance = self

        self.server = create_app()

        self.server = Executer.instance.authentication_executer.add_server_authentication(self.server)

        self.server.config["TEMPLATES_AUTO_RELOAD"] = True
        webserver_port = Executer.instance.general_settings_executer.get_webserver_port()

        register_api_blueprints(self.server)
        operations.start_ticker(operations.registry)
        publishers = [start_status_publisher(create_status_publisher(Executer.instance.system_info_executer))]
        if mic_level is not None:
            publishers.append(start_status_publisher(create_mic_level_publisher(mic_level), MIC_LEVEL_POLL_SECONDS))

        if DEBUG:
            self.server.run(host="0.0.0.0", port=webserver_port, load_dotenv=False, debug=True)  # ruff: ignore[hardcoded-bind-all-interfaces]
        else:
            try:
                serve(self.server, host="0.0.0.0", port=webserver_port, threads=8, clear_untrusted_proxy_headers=False)  # ruff: ignore[hardcoded-bind-all-interfaces]
            finally:
                for publisher in publishers:
                    publisher.stop()
        while True:
            sleep(10)
