

from libs.color_service_global import ColorServiceGlobal
from libs.device import Device
from libs.unit_tests.testfixtures.helper_functions import load_config_template


class DemoDevice(Device):
    def __init__(self) -> None:
        config = load_config_template()
        config["device_configs"]["test_device"] = config["default_device"]
        device_config = config["device_configs"]["test_device"]
        color_service_global = ColorServiceGlobal(config)

        super().__init__(config, device_config, color_service_global)
