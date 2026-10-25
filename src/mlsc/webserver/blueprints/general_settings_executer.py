from __future__ import annotations

import copy
from typing import TYPE_CHECKING

from loguru import logger

from mlsc.config_migration import ConfigMigrationError, migrate_data
from mlsc.webserver.executer_base import ExecuterBase, merge, update

if TYPE_CHECKING:
    from mlsc.webserver.messages import BadRequest, NotFound


class GeneralSettingsExecuter(ExecuterBase):

    def get_general_setting(self, setting_key: str) -> dict | NotFound:
        """Return a specific general setting."""
        return {
            "setting_key": setting_key,
            "setting_value": self._config["general_settings"][setting_key]
        }

    def get_general_settings(self) -> dict[str, dict]:
        """Return all general settings."""
        return {
            "setting_value": self._config["general_settings"]
        }

    def get_audio_settings(self) -> dict:
        """Return the audio section."""
        return self._config["audio"]

    def set_general_setting(self, settings: dict, audio: dict | None = None) -> dict | NotFound | BadRequest:
        """Set multiple general settings, and optionally some audio settings, with one save and refresh."""
        update(self._config["general_settings"], settings)
        update(self._config["audio"], audio or {})

        self.save_config()
        self.refresh_device(self.all_devices_id)

        return {
            "settings": settings
        }

    def get_webserver_port(self) -> int:
        """Return the webserver port, 8080 by default."""
        if "webserver_port" in self._config["general_settings"]:
            return self._config["general_settings"]["webserver_port"]
        return 8080

    def get_https_port(self) -> int | None:
        """Return the port of the opt-in HTTPS server, or `None` when it is off."""
        return self._config["general_settings"].get("https_port")

    def reset_general_settings(self) -> None:
        """Reset the general settings to their defaults. Device groups, devices and the audio section stay as they are."""
        defaults = copy.deepcopy(self._config_instance.load_template()["general_settings"])
        defaults["device_groups"] = self._config["general_settings"].get("device_groups", {})
        self._config["general_settings"] = defaults

        self.save_config()
        self.refresh_device(self.all_devices_id)

    def reset_settings(self) -> dict:
        """Reset the whole configuration to default, devices and groups included."""
        self._reset_config()
        self.refresh_device(self.all_devices_id)
        return {}

    def _reset_config(self) -> None:
        """Reset the config to default. Internal method."""
        self._config_instance.reset_config()
        self._config = self._config_instance.config

    def import_config(self, imported_config: dict) -> bool:
        """Import a new config and load it. The live config is only replaced once the new one is valid and complete."""
        if imported_config is None:
            logger.error("Could not import Config. Config is None.")
            return False

        logger.debug(f"Type of imported config: {type(imported_config)}")
        if isinstance(imported_config, dict):
            try:
                self.replace_config(imported_config)
            except ConfigMigrationError as e:
                logger.error(f"Could not import Config: {e}")
                return False
            return True
        logger.error("Unknown Type.")
        return False

    def patch_config(self, patch: dict) -> dict:
        """Merge a partial config into the live one, all or nothing. Raises ConfigMigrationError and changes nothing on failure."""
        return copy.deepcopy(self.replace_config(merge(copy.deepcopy(self._config), patch)))

    def replace_config(self, candidate: dict) -> dict:
        """Migrate and complete `candidate`, then swap it in and save. Raises ConfigMigrationError and changes nothing on failure."""
        try:
            config, _ = migrate_data(candidate)
            config = self._config_instance.make_compatible(config)
        except (KeyError, TypeError, ValueError, AttributeError) as e:
            msg = f"The config is incomplete or malformed: {e!r}"
            raise ConfigMigrationError(msg) from e
        self._config = config
        self._config_instance.check_compatibility()
        self.refresh_device(self.all_devices_id)
        return self._config
