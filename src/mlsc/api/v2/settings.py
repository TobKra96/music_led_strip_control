from flask import send_file
from flask_openapi3 import APIBlueprint, Tag
from pydantic import RootModel

from mlsc.api.v2.devices import SettingsOut
from mlsc.api.v2.errors import BODY_ERRORS, Problem, ProblemError
from mlsc.api.v2.lookup import require_patch
from mlsc.api.v2.security import api_login_required
from mlsc.api.v2.settings_models import GeneralSettingsPatch
from mlsc.config_migration import ConfigMigrationError
from mlsc.webserver.executer import Executer
from mlsc.webserver.messages import InvalidConfigFile

tag = Tag(name="Settings", description="Global settings and the configuration file")
settings_api = APIBlueprint("settings_api_v2", __name__, url_prefix="/api/v2", abp_tags=[tag])


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


@settings_api.patch("/settings", summary="Update some global settings", responses={"200": SettingsOut, **BODY_ERRORS})
@api_login_required
def patch_settings(body: GeneralSettingsPatch):
    patch = require_patch(body.model_dump(exclude_unset=True))
    Executer.instance.general_settings_executer.set_general_setting(patch)
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


@settings_api.put("/config", summary="Import a configuration", responses={"204": None, "400": Problem, **BODY_ERRORS})
@api_login_required
def import_config(body: ConfigDocument):
    """Older configuration versions are migrated. An unusable document changes nothing and is a `400` that says why."""
    try:
        Executer.instance.general_settings_executer.replace_config(body.root)
    except ConfigMigrationError as e:
        raise ProblemError(InvalidConfigFile, str(e)) from e
    return "", 204


@settings_api.patch("/config", summary="Update part of the configuration", responses={"200": ConfigDocument, "400": Problem, **BODY_ERRORS})
@api_login_required
def patch_config(body: ConfigDocument):
    """Send only the sections to change; objects are merged, anything else is replaced.

    A result that is not a usable configuration changes nothing and is a `400` that says why.
    """
    patch = require_patch(body.root)
    try:
        return Executer.instance.general_settings_executer.patch_config(patch)
    except ConfigMigrationError as e:
        raise ProblemError(InvalidConfigFile, str(e)) from e
