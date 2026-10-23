from mlsc.config_converter.config_converter_v2 import ConfigConverterV2
from mlsc.config_converter.config_converter_v3 import ConfigConverterV3
from mlsc.config_converter.config_converter_v4 import ConfigConverterV4, MigrationReport


class ConfigConverterService:
    def __init__(self) -> None:
        pass

    @staticmethod
    def upgrade(old_config):
        return ConfigConverterService.migrate(old_config)[0]

    @staticmethod
    def migrate(old_config, audio_devices=None) -> tuple[dict, MigrationReport]:
        """Run the converter chain and return the new config with its Migration Report.

        `audio_devices` (`{"index", "name", "host_api"}` dicts) lets the V4 step resolve the old microphone index.
        """
        config_converter_v2 = ConfigConverterV2()
        config_converter_v3 = ConfigConverterV3()
        config_converter_v4 = ConfigConverterV4()

        from_version = old_config.get("version", 1)
        report = MigrationReport(from_version=from_version, to_version=from_version)

        # Convert to the newer config version.
        if "version" not in old_config:
            old_config = config_converter_v2.upgrade(old_config)

        if old_config["version"] < 2:
            old_config = config_converter_v2.upgrade(old_config)

        if old_config["version"] < 3:
            old_config = config_converter_v3.upgrade(old_config)

        if old_config["version"] < 4:
            old_config, step_report = config_converter_v4.upgrade(old_config, audio_devices=audio_devices)
            report.extend(step_report)

        report.to_version = old_config["version"]
        return old_config, report
