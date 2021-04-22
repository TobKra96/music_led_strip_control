from libs.config_converter.config_converter_v2 import ConfigConverterV2  # pylint: disable=E0611, E0401

import logging

class ConfigConverterService():
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def upgrade(self, old_config):
        config_converter_v2 = ConfigConverterV2()

        # Convert to the newer config version.
        if "version" not in old_config:
            old_config = config_converter_v2.upgrade(old_config)

        if old_config["version"] < 2:
            old_config = config_converter_v2.upgrade(old_config)

        return old_config