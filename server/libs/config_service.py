#
#   Contains all configuration for the server.
#   Load and save the config after every change.
#

from shutil import copyfile
from pathlib import Path
import json
import os


class ConfigService():
    def __init__(self, config_lock):
        config_file = "/config.json"
        config_path = "/share/.mlsc"
        src = os.path.dirname(__file__) + config_file  # Default config.json from the repository.
        if not os.path.exists(src):
            raise Exception(f'Could not find the config file: "{src}"')  # Raise exception, if no config.json found in repository.
        if not os.path.exists(config_path + config_file):
            Path(config_path).mkdir(exist_ok=True)  # Create config directory, ignore if already exists.
            copyfile(src, config_path + config_file)  # Copy config.json from repository to config directory.
        self._path = config_path + config_file

        self.config_lock = config_lock

        self.load_config()

    def load_config(self):
        """Load the configuration file inside the self.config variable."""
        self.config_lock.acquire()

        with open(self._path, "r") as read_file:
            self.config = json.load(read_file)

        self.config_lock.release()

        print("Settings loaded from config.")

    def save_config(self, config=None):
        """Save the config file. Use the current self.config"""
        print("Saving settings...")

        self.config_lock.acquire()

        if config is not None:
            self.config = config

        with open(self._path, "w") as write_file:
            json.dump(self.config, write_file, indent=4, sort_keys=True)

        self.config_lock.release()

    def reset_config(self):
        """Reset the config."""
        print("Resetting config...")

        self.config_lock.acquire()

        backup_config = self.load_backup()
        if backup_config is not None:
            self.config = backup_config

        self.config_lock.release()

        # Save the config again.
        self.save_config()

    def load_backup(self):
        backup_config = None

        path = os.path.dirname(__file__) + "/config.json.bak"
        if not os.path.exists(path):
            raise Exception(f'Could not find the backup config file: "{path}"')

        # Read the Backup Config.
        with open(path, "r") as read_file:
            backup_config = json.load(read_file)

        return backup_config
        

    def check_compatibility(self):
        loaded_config = self.config
        template_config = self.load_backup()

        # Loop through the root
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
