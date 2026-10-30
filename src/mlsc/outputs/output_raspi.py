from loguru import logger

from mlsc.diagnosis import Diagnosis
from mlsc.gpio_backends import GpioBackend, GpioBackendError, GpioStrip, select_backend
from mlsc.host import Host
from mlsc.outputs.output import Output
from mlsc.strip import has_white_channel


class OutputRaspi(Output):
    def __init__(self, device, backend: GpioBackend | None = None) -> None:
        # Call the constructor of the base class.
        super().__init__(device)

        settings = self._device_config["output"]["output_raspi"]
        strip = GpioStrip(
            chip_family=self._device_config["chip_family"],
            colour_order=self._device_config["colour_order"],
            white_channel=has_white_channel(self._device_config),
            led_count=int(self._device_config["led_count"]),
            pin=int(settings["led_pin"]),
            brightness=int(self._device_config["led_brightness"]),
            advanced={
                "led_freq_hz": int(settings["led_freq_hz"]),
                "led_dma": int(settings["led_dma"]),
                "led_channel": int(settings["led_channel"]),
                "led_invert": int(settings["led_invert"]),
            },
        )
        try:
            self._backend = backend or select_backend()()
            self._backend.init(strip)
        except GpioBackendError as e:
            logger.error(f"{e} {e.suggested_fix or ''}")
            raise

    def show(self, output_array):
        self._backend.show(output_array)

    def close(self):
        self._backend.close()

    @classmethod
    def diagnose(cls, device_config: dict, host: Host | None = None) -> Diagnosis:
        host = host or Host()
        try:
            backend = select_backend(host)
        except GpioBackendError as e:
            return e.to_diagnosis()
        return backend.diagnose(device_config, host)
