import numpy as np
from loguru import logger

from mlsc.diagnosis import Diagnosis, worst
from mlsc.host import Host
from mlsc.outputs.output import Output
from mlsc.strip import has_white_channel, rpi_ws281x_strip_type

# GPIOs that rpi_ws281x drives with the PWM hardware, which the Pi's analog audio also uses.
PWM_PINS = frozenset({12, 13, 18, 19})


class OutputRaspi(Output):
    def __init__(self, device) -> None:
        # Call the constructor of the base class.
        super().__init__(device)

        try:
            import _rpi_ws281x as ws  # ruff: ignore[import-outside-top-level]
        except (ImportError, ModuleNotFoundError):
            return
            from rpi_ws281x import ws  # ruff: ignore[import-outside-top-level]

        output_id = "output_raspi"

        # LED strip configuration:
        self._led_count = int(self._device_config["led_count"])                                 # Number of LED pixels.
        self._led_pin = int(self._device_config["output"][output_id]["led_pin"])                # GPIO pin connected to the pixels (18 uses PWM!).
        self._led_freq_hz = int(self._device_config["output"][output_id]["led_freq_hz"])        # LED signal frequency in hertz (usually 800khz).
        self._led_dma = int(self._device_config["output"][output_id]["led_dma"])                # DMA channel to use for generating signal (try 10).
        self._led_brightness = int(self._device_config["led_brightness"])  # Set to '0' for darkest and 100 for brightest.
        self._led_invert = int(self._device_config["output"][output_id]["led_invert"])          # Set to 'True' to invert the signal (when using NPN transistor level shift).
        self._led_channel = int(self._device_config["output"][output_id]["led_channel"])        # set to '1' for GPIOs 13, 19, 41, 45 or 53.
        self._white_channel = has_white_channel(self._device_config)

        # Set Fallback Strip
        self._led_strip_translated = ws.WS2811_STRIP_RGB

        try:
            strip_type = rpi_ws281x_strip_type(self._device_config["chip_family"], self._device_config["colour_order"], self._white_channel)
            self._led_strip_translated = getattr(ws, strip_type)
            logger.debug(f"Found Led Strip {strip_type}")
        except Exception as e:
            logger.exception(f"Could not find LED Strip Type. Exception: {e}")

        self._led_brightness_translated = int(255 * (self._led_brightness / 100))

        logger.debug(f"LED Brightness: {self._led_brightness}")
        logger.debug(f"LED Brightness converted: {self._led_brightness_translated}")

        self._leds = ws.new_ws2811_t()

        self.channel = ws.ws2811_channel_get(self._leds, self._led_channel)

        ws.ws2811_channel_t_strip_type_set(self.channel, self._led_strip_translated)
        ws.ws2811_channel_t_count_set(self.channel, self._led_count)
        ws.ws2811_channel_t_gpionum_set(self.channel, self._led_pin)
        ws.ws2811_channel_t_invert_set(self.channel, self._led_invert)
        ws.ws2811_channel_t_brightness_set(self.channel, self._led_brightness_translated)

        ws.ws2811_t_freq_set(self._leds, self._led_freq_hz)
        ws.ws2811_t_dmanum_set(self._leds, self._led_dma)

        # Initialize library with LED configuration.
        resp = ws.ws2811_init(self._leds)
        if resp != ws.WS2811_SUCCESS:
            message = ws.ws2811_get_return_t_str(resp)
            error_msg = f"ws2811_init failed with code {resp} ({message})"
            raise RuntimeError(error_msg)

    def show(self, output_array):
        try:
            import _rpi_ws281x as ws  # ruff: ignore[import-outside-top-level]
        except (ImportError, ModuleNotFoundError):
            from rpi_ws281x import ws  # ruff: ignore[import-outside-top-level]

        # Typecast the array to int.
        output_array = output_array.clip(0, 255).astype(int)

        # Check if we have a white channel or not.
        if len(output_array[:]) == 4 and self._white_channel:
            # Sort the colors as RGB type.
            g = np.left_shift(output_array[1][:].astype(int), 24)
            r = np.left_shift(output_array[0][:].astype(int), 16)
            b = np.left_shift(output_array[2][:].astype(int), 8)
            w = output_array[3][:].astype(int)
            grbw = np.bitwise_or(np.bitwise_or(np.bitwise_or(r, g), b), w).astype(int)

            # You can only use ws2811_leds_set with the custom version.
            for i in range(self._led_count):
                ws.ws2811_led_set(self.channel, i, int(grbw[i].item()))
        else:
            # Sort the colors as RGB type.
            g = np.left_shift(output_array[1][:].astype(int), 16)
            r = np.left_shift(output_array[0][:].astype(int), 8)
            b = output_array[2][:].astype(int)
            grb = np.bitwise_or(np.bitwise_or(r, g), b).astype(int)

            # You can only use ws2811_leds_set with the custom version.
            for i in range(self._led_count):
                ws.ws2811_led_set(self.channel, i, grb[i].item())

        resp = ws.ws2811_render(self._leds)

        if resp != ws.WS2811_SUCCESS:
            message = ws.ws2811_get_return_t_str(resp)
            error_msg = f"ws2811_render failed with code {resp} ({message})"
            raise RuntimeError(error_msg)

    @classmethod
    def diagnose(cls, device_config: dict, host: Host | None = None) -> Diagnosis:
        host = host or Host()
        pin = device_config["output"]["output_raspi"]["led_pin"]
        problems = []
        if not host.has_ws281x():
            problems.append(Diagnosis.error("The rpi_ws281x library is not installed.", "Install it with: pip install 'mlsc[pi]'"))
        if not host.can_use_gpio_memory():
            problems.append(
                Diagnosis.error("Permission denied for the GPIO memory (/dev/mem).", "Run MLSC as root, for example through the systemd service.")
            )
        model = host.pi_model()
        if model and "Pi 5" in model:
            problems.append(
                Diagnosis.warning(
                    "The Pi 5 is not supported by rpi_ws281x (experimental/unsupported driver).",
                    "Use a Pi 4 or older, or send the frames to a UDP client.",
                )
            )
        if pin in PWM_PINS and host.analog_audio_enabled():
            problems.append(
                Diagnosis.warning(
                    f"GPIO {pin} is used by the Pi's analog audio (PWM).",
                    "Set dtparam=audio=off in /boot/firmware/config.txt and reboot, or use another pin such as GPIO 10 (SPI).",
                )
            )
        return worst(problems) if problems else Diagnosis.ok(f"GPIO {pin} is ready.")
