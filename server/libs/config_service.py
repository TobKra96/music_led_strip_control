#
#   Contains all configuration for the server.
#   Load and save the config after every change.
#

from shutil import copyfile, copy
from pathlib import Path
import json
import os


class ConfigService():
    def __init__(self, config_lock):
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

        print("Config Files")
        print(f"Config: {self._config_path}")
        print(f"Backup: {self._backup_path}")
        print(f"Template: {self._template_path}")

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

    def load_config(self):
        """Load the configuration file inside the self.config variable."""
        self.config_lock.acquire()

        with open(self._config_path, "r") as read_file:
            self.config = json.load(read_file)

        self.config_lock.release()

        print("Settings loaded from config.")

    def save_config(self, config=None):
        """Save the config file. Use the current self.config"""
        print("Saving settings...")

        self.config_lock.acquire()

        self.save_backup()

        if config is not None:
            self.config = config

        with open(self._config_path, "w") as write_file:
            json.dump(self.config, write_file, indent=4, sort_keys=True)

        self.config_lock.release()

    def save_backup(self):
        copy(self._config_path, self._backup_path)

    def reset_config(self):
        """Reset the config."""
        print("Resetting config...")

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

        # Loop through the root.
        for key, value in template_config.items():
            if key == "device_configs":
                continue

            if key not in loaded_config:
                loaded_config[key] = template_config[key]
                continue

            self.check_leaf(loaded_config[key], template_config[key])

        self.check_devices(loaded_config["device_configs"], template_config["default_device"])

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

    @staticmethod
    def instance(config_lock, imported_instance=None):
        """
        Returns the current instance of the Config_Service.
        Use this method and not the current_instance variable directly.
        This method will create the config if it's null.
        """
        if imported_instance is not None:
            print("Importing config instance...")
            ConfigService.current_instance = imported_instance

        if not hasattr(ConfigService, 'current_instance'):
            ConfigService.current_instance = ConfigService(config_lock)

        return ConfigService.current_instance
