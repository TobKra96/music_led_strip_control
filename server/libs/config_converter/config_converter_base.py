import logging


class ConfigConverterBase():
    def __init__(self):
        self.logger = logging.getLogger(__name__)

        self.from_version = 0
        self.to_version = 0

    from_version = 0
    to_version = 0

    def upgrade(self, old_config):
        return old_config
