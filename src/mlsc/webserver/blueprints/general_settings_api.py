from json import JSONDecodeError, dumps, loads

from flask import jsonify, request, send_file
from flask_openapi3 import APIBlueprint
from loguru import logger

from mlsc.webserver.auth import login_required
from mlsc.webserver.executer import Executer
from mlsc.webserver.executer_base import validate_schema
from mlsc.webserver.messages import ConfigFileImported, ConfigFileNotFound, InvalidConfigFile, UnprocessableEntity, UnsupportedMediaType
from mlsc.webserver.openapi_docs import doc
from mlsc.webserver.schemas.v1_schema import ONE_GENERAL_SETTING_SCHEMA, SET_GENERAL_SETTINGS_SCHEMA
from mlsc.webserver.v1_adapter import general_settings_from_v1, general_settings_to_v1

general_settings_api = APIBlueprint("general_settings_api", __name__)


def v1_general_settings() -> dict:
    """Return the general settings with the v1 microphone keys."""
    audio = Executer.instance.general_settings_executer.get_audio_settings()
    audio_devices = Executer.instance.general_executer.list_audio_devices() if audio["device_name"] is not None else []
    general = Executer.instance.general_settings_executer.get_general_settings()["setting_value"]
    return general_settings_to_v1(general, audio, audio_devices)


@general_settings_api.get("/api/settings/general", **doc("general_settings_api/get_general_settings.yml"))
@login_required
def get_general_settings():
    data_in = request.args.to_dict()

    if set(data_in) == {"setting_key"}:  # Get one specific general setting.

        if not validate_schema(data_in, ONE_GENERAL_SETTING_SCHEMA):
            return UnprocessableEntity.as_response()

        return jsonify({"setting_key": data_in["setting_key"], "setting_value": v1_general_settings()[data_in["setting_key"]]})

    if not set(data_in):  # Get all general settings.

        return jsonify({"setting_value": v1_general_settings()})

    return UnprocessableEntity.as_response()


@general_settings_api.post("/api/settings/general", **doc("general_settings_api/set_general_settings.yml"))
@login_required
def set_general_settings():
    data_in = request.get_json()

    if not validate_schema(data_in, SET_GENERAL_SETTINGS_SCHEMA):
        return UnprocessableEntity.as_response()

    audio_devices = Executer.instance.general_executer.list_audio_devices() if "device_id" in data_in["settings"] else []
    general, audio = general_settings_from_v1(data_in["settings"], audio_devices)
    Executer.instance.general_settings_executer.set_general_setting(general, audio)

    return jsonify({"settings": data_in["settings"]})


@general_settings_api.delete("/api/settings/general", **doc("general_settings_api/reset_general_settings.yml"))
@login_required
def reset_general_settings():
    data_out = Executer.instance.general_settings_executer.reset_settings()

    return jsonify(data_out)


@general_settings_api.get("/api/settings/configuration/file", **doc("general_settings_api/export_config.yml"))
@login_required
def export_config():
    logger.debug(f"Send file: {Executer.instance.general_settings_executer.export_config_path}")
    return send_file(
        Executer.instance.general_settings_executer.export_config_path,
        as_attachment=True,
        max_age=-1,
        mimetype="application/json"
    )


@general_settings_api.post("/api/settings/configuration/file", **doc("general_settings_api/import_config.yml"))
@login_required
def import_config():
    logger.debug("Import Config Request received.")

    if "imported_config" not in request.files:
        logger.error("Could not find the file key.")
        return ConfigFileNotFound.as_response()

    imported_config = request.files["imported_config"]
    content = imported_config.read()
    if content:
        try:
            logger.debug(f"File Received: {dumps(loads(content), indent=4)}")
            if Executer.instance.general_settings_executer.import_config(loads(content)):
                return ConfigFileImported.as_response()
            return InvalidConfigFile.as_response()

        except (JSONDecodeError, UnicodeDecodeError):
            return UnsupportedMediaType.as_response()

    return ConfigFileNotFound.as_response()
