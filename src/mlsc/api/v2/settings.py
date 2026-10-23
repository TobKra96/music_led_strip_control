from flask import send_file
from flask_openapi3 import APIBlueprint, Tag
from pydantic import RootModel

from mlsc.api.v2.devices import SettingsOut, SettingsPatch
from mlsc.api.v2.errors import Problem, ProblemError, ValidationError
from mlsc.api.v2.lookup import check_schema
from mlsc.api.v2.security import api_login_required
from mlsc.webserver.executer import Executer
from mlsc.webserver.messages import InvalidConfigFile
from mlsc.webserver.schemas.general_settings_api_schema import SET_GENERAL_SETTINGS_SCHEMA

tag = Tag(name="Settings", description="Global settings and the configuration file")
settings_api = APIBlueprint("settings_api_v2", __name__, url_prefix="/api/v2", abp_tags=[tag])

# Groups have their own resource.
_GENERAL_SETTINGS = SET_GENERAL_SETTINGS_SCHEMA["properties"]["settings"]
GENERAL_PROPERTIES = {
    **_GENERAL_SETTINGS,
    "properties": {key: schema for key, schema in _GENERAL_SETTINGS["properties"].items() if key != "device_groups"},
}
WRITE_ERRORS = {"401": Problem, "415": Problem, "422": Problem}


class ConfigDocument(RootModel[dict]):
    """The whole configuration as stored in `config.json`."""


def _settings() -> dict:
    settings = dict(Executer.instance.general_settings_executer.get_general_settings()["setting_value"])
    settings.pop("device_groups", None)
    return settings


@settings_api.get("/settings", summary="Get the global settings", responses={"200": SettingsOut, "401": Problem})
@api_login_required
def get_settings():
    return _settings()


@settings_api.patch("/settings", summary="Update some global settings", responses={"200": SettingsOut, **WRITE_ERRORS})
@api_login_required
def patch_settings(body: SettingsPatch):
    if not body.root:
        raise ProblemError(ValidationError, errors=[{"field": "(body)", "detail": "Send at least one setting."}])
    check_schema(body.root, GENERAL_PROPERTIES)
    Executer.instance.general_settings_executer.set_general_setting(body.root)
    return _settings()


@settings_api.delete("/settings", summary="Reset the whole configuration to the defaults", responses={"200": SettingsOut, "401": Problem})
@api_login_required
def reset_settings():
    """Reset everything, not only the global settings: devices and groups are removed too."""
    Executer.instance.general_settings_executer.reset_settings()
    return _settings()


@settings_api.get("/config", summary="Export the configuration", responses={"200": ConfigDocument, "401": Problem})
@api_login_required
def export_config():
    return send_file(Executer.instance.general_settings_executer.export_config_path, mimetype="application/json", max_age=-1)


@settings_api.put("/config", summary="Import a configuration", responses={"204": None, "400": Problem, **WRITE_ERRORS})
@api_login_required
def import_config(body: ConfigDocument):
    """Older configuration versions are migrated. An unusable document changes nothing."""
    if not Executer.instance.general_settings_executer.import_config(body.root):
        raise ProblemError(InvalidConfigFile)
    return "", 204
