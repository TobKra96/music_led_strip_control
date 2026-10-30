import numpy as np
from loguru import logger

from mlsc.diagnosis import Diagnosis, worst
from mlsc.gpio_backends import GpioBackend, GpioBackendError, GpioStrip
from mlsc.host import Host
from mlsc.strip import rpi_ws281x_strip_type

# GPIOs that rpi_ws281x drives with the PWM hardware, which the Pi's analog audio also uses.
PWM_PINS = frozenset({12, 13, 18, 19})
INSTALL_FIX = "Install it with: pip install 'mlsc[pi]'"
ROOT_FIX = "Run MLSC as root, for example through the systemd service."


def _load_ws():
    try:
        import _rpi_ws281x as ws  # ruff: ignore[import-outside-top-level]
    except ImportError:
        try:
            from rpi_ws281x import ws  # ruff: ignore[import-outside-top-level]
        except ImportError as e:
            raise GpioBackendError("The rpi_ws281x library is not installed.", INSTALL_FIX) from e
    return ws


class Ws281xBackend(GpioBackend):
    """Drives the strip through the `rpi_ws281x` library (PWM, PCM or SPI).

    Advanced settings: `led_dma`, `led_channel`, `led_freq_hz` and `led_invert`.
    """

    name = "rpi_ws281x"
    valid_pins = frozenset({10, 12, 13, 18, 19, 21})

    def __init__(self, ws=None) -> None:
        self._ws = ws
        self._leds = None
        self._channel = None
        self._strip: GpioStrip | None = None

    def init(self, strip: GpioStrip) -> None:
        if strip.pin not in self.valid_pins:
            raise GpioBackendError(f"GPIO {strip.pin} cannot be driven by rpi_ws281x.", f"Use one of the GPIOs {sorted(self.valid_pins)}.")
        ws = self._ws or _load_ws()
        advanced = strip.advanced

        strip_type = rpi_ws281x_strip_type(strip.chip_family, strip.colour_order, strip.white_channel)
        try:
            strip_type_constant = getattr(ws, strip_type)
        except AttributeError as e:
            raise GpioBackendError(f"rpi_ws281x has no strip type {strip_type}.", "Choose another chip family or colour order.") from e
        logger.debug(f"Found Led Strip {strip_type}")

        brightness = int(255 * (strip.brightness / 100))
        logger.debug(f"LED Brightness: {strip.brightness}, converted: {brightness}")

        leds = ws.new_ws2811_t()
        channel = ws.ws2811_channel_get(leds, int(advanced["led_channel"]))
        ws.ws2811_channel_t_strip_type_set(channel, strip_type_constant)
        ws.ws2811_channel_t_count_set(channel, strip.led_count)
        ws.ws2811_channel_t_gpionum_set(channel, strip.pin)
        ws.ws2811_channel_t_invert_set(channel, int(advanced["led_invert"]))
        ws.ws2811_channel_t_brightness_set(channel, brightness)
        ws.ws2811_t_freq_set(leds, int(advanced["led_freq_hz"]))
        ws.ws2811_t_dmanum_set(leds, int(advanced["led_dma"]))

        resp = ws.ws2811_init(leds)
        if resp != ws.WS2811_SUCCESS:
            message = ws.ws2811_get_return_t_str(resp)
            raise GpioBackendError(f"ws2811_init failed with code {resp} ({message}).", _init_fix(message))

        self._ws, self._leds, self._channel, self._strip = ws, leds, channel, strip

    def show(self, frame: np.ndarray) -> None:
        ws, strip = self._ws, self._strip
        if strip is None:
            msg = "The backend is not initialised."
            raise GpioBackendError(msg)

        frame = frame.clip(0, 255).astype(int)
        if len(frame) == 4 and strip.white_channel:
            g = np.left_shift(frame[1], 24)
            r = np.left_shift(frame[0], 16)
            b = np.left_shift(frame[2], 8)
            packed = np.bitwise_or(np.bitwise_or(np.bitwise_or(r, g), b), frame[3])
        else:
            g = np.left_shift(frame[1], 16)
            r = np.left_shift(frame[0], 8)
            packed = np.bitwise_or(np.bitwise_or(r, g), frame[2])

        # You can only use ws2811_led_set with the custom version.
        for i in range(strip.led_count):
            ws.ws2811_led_set(self._channel, i, int(packed[i].item()))

        resp = ws.ws2811_render(self._leds)
        if resp != ws.WS2811_SUCCESS:
            message = ws.ws2811_get_return_t_str(resp)
            raise GpioBackendError(f"ws2811_render failed with code {resp} ({message}).")

    def close(self) -> None:
        if self._leds is not None:
            self._ws.ws2811_fini(self._leds)
            self._leds = self._channel = self._strip = None

    @classmethod
    def diagnose(cls, device_config: dict, host: Host) -> Diagnosis:
        pin = device_config["output"]["output_raspi"]["led_pin"]
        problems = []
        if not host.has_ws281x():
            problems.append(Diagnosis.error("The rpi_ws281x library is not installed.", INSTALL_FIX))
        if not host.can_use_gpio_memory():
            problems.append(Diagnosis.error("Permission denied for the GPIO memory (/dev/mem).", ROOT_FIX))
        if pin not in cls.valid_pins:
            problems.append(Diagnosis.error(f"GPIO {pin} cannot be driven by rpi_ws281x.", f"Use one of the GPIOs {sorted(cls.valid_pins)}."))
        if pin in PWM_PINS and host.analog_audio_enabled():
            problems.append(
                Diagnosis.warning(
                    f"GPIO {pin} is used by the Pi's analog audio (PWM).",
                    "Set dtparam=audio=off in /boot/firmware/config.txt and reboot, or use another pin such as GPIO 10 (SPI).",
                )
            )
        return worst(problems) if problems else Diagnosis.ok(f"GPIO {pin} is ready.")


def _init_fix(message: str) -> str:
    if "mmap" in message.lower() or "permission" in message.lower():
        return ROOT_FIX
    return "Check the GPIO, DMA channel and PWM channel in the advanced output settings."
