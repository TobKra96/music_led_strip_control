#
#   Contains all configuration for the server.
#   Load and save the config after every change.
#
from libs.config_converter.config_converter_service import ConfigConverterService  # pylint: disable=E0611, E0401

from logging.handlers import RotatingFileHandler
from shutil import copyfile, copy
from pathlib import Path
import coloredlogs
import fileinput
import logging
import json
import sys
import os


class ConfigService():
    def __init__(self, config_lock):
        self.config = None

        # Start with the default logging settings, because the config was not loaded.
        self.setup_logging()

        self.logger = logging.getLogger(__name__)

        config_file = "config.json"
        config_backup_file = "config_backup.json"
        config_template_file = "config_template.json"

        rel_config_path = "../../.mlsc/"
        # Convert relative path to abs path.
        config_folder = os.path.abspath(rel_config_path) + "/"
        lib_folder = os.path.dirname(__file__) + "/"

        self._config_path = config_folder + config_file
        self._backup_path = config_folder + config_backup_file
        self._template_path = lib_folder + config_template_file

        self.logger.debug("Config Files")
        self.logger.debug(f"Config: {self._config_path}")
        self.logger.debug(f"Backup: {self._backup_path}")
        self.logger.debug(f"Template: {self._template_path}")

        if not os.path.exists(self._config_path):
            if not os.path.exists(self._backup_path):
                # Use the template as config.
                Path(config_folder).mkdir(exist_ok=True)  # Create config directory, ignore if already exists.
                copyfile(self._template_path, self._config_path)  # Copy config.json from repository to config directory.
            else:
                # Use the backup as template.
                Path(config_folder).mkdir(exist_ok=True)  # Create config directory, ignore if already exists.
                copyfile(self._backup_path, self._config_path)  # Copy config.json from repository to config directory.

        self.config_lock = config_lock

        self.load_config()

        # Now the config was loaded, so we can reinit the logging with the set logging levels.
        self.setup_logging()

    def load_config(self):
        """Load the configuration file inside the self.config variable."""
        self.config_lock.acquire()

        with open(self._config_path, "r") as read_file:
            self.config = json.load(read_file)

        self.config_lock.release()

        self.logger.debug("Settings loaded from config.")

    def save_config(self, config=None):
        """Save the config file. Use the current self.config"""
        self.logger.debug("Saving settings...")

        self.config_lock.acquire()

        self.save_backup()

        if config is not None:
            self.config = config

        with open(self._config_path, "w") as write_file:
            json.dump(self.config, write_file, indent=4, sort_keys=True)

        # Maybe the logging updated
        self.setup_logging()
        self.config_lock.release()

    def save_backup(self):
        copy(self._config_path, self._backup_path)

    def reset_config(self):
        """Reset the config."""
        self.logger.debug("Resetting config...")

        self.config_lock.acquire()

        config_template = self.load_template()
        if config_template is not None:
            self.config = config_template

        self.config_lock.release()

        # Save the config again.
        self.save_config()

    def load_template(self):
        config_template = None

        if not os.path.exists(self._template_path):
            raise Exception(f'Could not find the template config file: "{self._template_path}"')

        # Read the Backup Config.
        with open(self._template_path, "r") as read_file:
            config_template = json.load(read_file)

        return config_template

    def check_compatibility(self):
        loaded_config = self.config
        template_config = self.load_template()

        config_converter_service = ConfigConverterService()
        loaded_config = config_converter_service.upgrade(loaded_config)

        # Loop through the root.
        for key, value in template_config.items():
            if key == "device_configs":
                continue

            if key not in loaded_config:
                loaded_config[key] = template_config[key]
                continue

            self.check_leaf(loaded_config[key], template_config[key])

        self.check_devices(loaded_config["device_configs"], template_config["default_device"])

        self.config = loaded_config
        self.save_config()

    def check_leaf(self, loaded_config_leaf, template_config_leaf):
        if type(template_config_leaf) is dict:
            for key, value in template_config_leaf.items():
                if key not in loaded_config_leaf:
                    loaded_config_leaf[key] = template_config_leaf[key]
                    continue

                self.check_leaf(loaded_config_leaf[key], template_config_leaf[key])

    def check_devices(self, loaded_config_devices, template_config_device):
        for key, value in loaded_config_devices.items():
            self.check_leaf(loaded_config_devices[key], template_config_device)

    def get_config_path(self):
        return self._config_path

    def setup_logging(self):
        logging_path = "../../.mlsc/"
        logging_file = "mlsc.log"

        format_string_file = "%(asctime)s - %(levelname)-8s - %(name)-30s - %(message)s"
        format_string_console = "%(levelname)-8s - %(name)-30s - %(message)s"

        logging_level_root = logging.NOTSET
        logging_level_console = logging.INFO
        logging_level_file = logging.INFO
        logging_file_enabled = False

        logging_level_map = {
            "notset": logging.NOTSET,
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL
        }

        if self.config is not None:
            try:
                logging_level_console = logging_level_map[self.config["general_settings"]["log_level_console"]]
                logging_level_file = logging_level_map[self.config["general_settings"]["log_level_file"]]
                logging_file_enabled = self.config["general_settings"]["log_file_enabled"]
            except Exception as e:
                print(f"Could not load logging settings. Exception {e}")
                pass

        if not os.path.exists(logging_path):
            Path(logging_path).mkdir(exist_ok=True)

        root_logger = logging.getLogger()

        # Reset Handlers
        root_logger.handlers = []
        root_logger.setLevel(logging_level_root)

        if logging_file_enabled:
            file_formatter = logging.Formatter(format_string_file)
            rotating_file_handler = RotatingFileHandler(logging_path + logging_file, mode='a', maxBytes=5 * 1024 * 1024, backupCount=5, encoding='utf-8')
            rotating_file_handler.setLevel(logging_level_file)
            rotating_file_handler.setFormatter(file_formatter)
            root_logger.addHandler(rotating_file_handler)

        console_formatter = coloredlogs.ColoredFormatter(fmt=format_string_console)
        stream_handler = logging.StreamHandler(stream=sys.stderr)
        stream_handler.setFormatter(console_formatter)
        stream_handler.setLevel(logging_level_console)
        root_logger.addHandler(stream_handler)

    @staticmethod
    def instance(config_lock, imported_instance=None):
        """
        Returns the current instance of the Config_Service.
        Use this method and not the current_instance variable directly.
        This method will create the config if it's null.
        """
        if imported_instance is not None:
            ConfigService.current_instance = imported_instance

        if not hasattr(ConfigService, 'current_instance'):
            ConfigService.current_instance = ConfigService(config_lock)

        return ConfigService.current_instance
