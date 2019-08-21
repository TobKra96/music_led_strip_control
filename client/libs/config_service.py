#
#   Contains all configuration for the server
#   Load and save the config after every change
#
#
import json
import os

class ConfigService():

    def __init__(self, config_lock):
        path = os.path.dirname(__file__) + "/config.json"
        if os.path.exists(path):
            self._path = path
        else:
            raise Exception("Could not find the config file.", path)

        self.config_lock = config_lock

        self.load_config()

    def load_config(self):
        """Load the configuration file inside the self.config variable"""
        self.config_lock.acquire()

        with open (self._path, "r") as read_file:
            self.config = json.load(read_file)

        self.config_lock.release()

        #print("Settings loaded: " + str(self.config))
        print("Settings loaded")

    def save_config(self, config = None):
        """Save the config file. Use the current self.config"""
        #print("Save settings: " + str(self.config))
        print("Save settings")

        self.config_lock.acquire()

        if config is not None:
            self.config = config

        with open(self._path, "w") as write_file:
            json.dump(self.config, write_file, indent=4, sort_keys=True)

        self.config_lock.release()

    def reset_config(self):
        """Reset the config"""
        print("Reset config")

        self.config_lock.acquire()

        path = os.path.dirname(__file__) + "\\config.json.bak"
        if not os.path.exists(path):
            raise Exception("Could not find the backup config file.", path)

        # Read the Backup Config
        with open (path, "r") as read_file:
            self.config = json.load(read_file)

        self.config_lock.release()

        # Save the config again.
        self.save_config()

    @staticmethod
    def instance(config_lock, imported_instance=None):
        """ Returns the current instance of the Config_Service
        Use this method and not the current_instance variable directly. This method will create the config if it's null
        """        
        if imported_instance is not None:
            print("Import config instance")
            ConfigService.current_instance = imported_instance

        if not hasattr(ConfigService, 'current_instance'):            
            ConfigService.current_instance = ConfigService(config_lock) 
        
        return ConfigService.current_instance
            