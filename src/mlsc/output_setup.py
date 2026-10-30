"""What the Setup Wizard needs to know about an Output: the valid choices for this host, the checks, and the Power Limit maths."""
from mlsc.gpio_backends import GpioBackendError, select_backend
from mlsc.host import Host
from mlsc.output_enum import OutputsEnum
from mlsc.outputs.output import Output
from mlsc.outputs.output_mock import OutputMock
from mlsc.outputs.output_raspi import OutputRaspi
from mlsc.outputs.output_udp import OutputUDP

LOCAL_GPIO = OutputsEnum.output_raspi.name
OUTPUTS: dict[str, type[Output]] = {
    OutputsEnum.output_dummy.name: OutputMock,
    LOCAL_GPIO: OutputRaspi,
    OutputsEnum.output_udp.name: OutputUDP,
}
DEFAULT_VOLTS = 5.0
DMA_CHANNELS = range(15)
FREQUENCY_HZ = range(400_000, 1_200_001)
# The wire time of a pixel sets the frame rate: about 25,600 divided by the LED count.
FPS_NUMERATOR = 25_600
SPLIT_FROM_LEDS = 600


def _error(field: str, detail: str) -> dict:
    return {"field": field, "detail": detail}


def _backend(host: Host):
    """The GPIO Backend of this host, or None when it has none (a Pi 5)."""
    try:
        return select_backend(host)
    except GpioBackendError:
        return None


def validate_output(device_config: dict, host: Host | None = None) -> list[dict]:
    """A field error for each setting of `device_config` that the hardware cannot use."""
    host = host or Host()
    errors = []
    led_count, led_mid = device_config["led_count"], device_config["led_mid"]
    if led_count < 1:
        errors.append(_error("led_count", "Must be at least 1."))
    if not 0 <= led_mid < max(led_count, 1):
        errors.append(_error("led_mid", f"Must be a pixel of the strip, from 0 to {max(led_count - 1, 0)}."))
    if device_config["white_channel"] and device_config["chip_family"] != "sk6812":
        errors.append(_error("white_channel", "Only the SK6812 has a white channel."))
    if device_config["output_type"] != LOCAL_GPIO:
        return errors

    settings = device_config["output"][LOCAL_GPIO]
    backend = _backend(host)
    if backend is not None and settings["led_pin"] not in backend.valid_pins:
        pins = ", ".join(map(str, sorted(backend.valid_pins)))
        errors.append(_error(f"output.{LOCAL_GPIO}.led_pin", f"GPIO {settings['led_pin']} cannot drive the strip. Use one of {pins}."))
    if settings["led_dma"] not in DMA_CHANNELS:
        errors.append(_error(f"output.{LOCAL_GPIO}.led_dma", f"Must be a DMA channel from {DMA_CHANNELS[0]} to {DMA_CHANNELS[-1]}."))
    if settings["led_freq_hz"] not in FREQUENCY_HZ:
        errors.append(_error(f"output.{LOCAL_GPIO}.led_freq_hz", f"Must be from {FREQUENCY_HZ[0]} to {FREQUENCY_HZ[-1]} Hz."))
    return errors


def estimate_power(device_config: dict) -> dict:
    """The draw at full white and the configured brightness, with a warning when it is above the supply and the Power Limit is on."""
    limit = device_config["power_limit"]
    amps = device_config["led_count"] * limit["ma_per_led"] / 1000 * device_config["led_brightness"] / 100
    warning = None
    if limit["enabled"] and amps > limit["supply_amps"]:
        warning = (f"The strip can draw {amps:.1f} A at full white, more than the {limit['supply_amps']:.1f} A supply. "
                   "Lower the brightness, use a bigger supply or split the strip.")
    return {"amps": amps, "watts": amps * limit.get("supply_volts", DEFAULT_VOLTS), "warning": warning}


def max_fps(led_count: int) -> int | None:
    """The frame rate the strip can reach, which falls as the strip gets longer. None without pixels."""
    return FPS_NUMERATOR // led_count if led_count > 0 else None


def split_suggestion(led_count: int) -> str | None:
    if led_count < SPLIT_FROM_LEDS:
        return None
    return (f"{led_count} LEDs limit the strip to about {max_fps(led_count)} fps. "
            "Split it into several Devices on separate pins for a higher frame rate.")


def setup_options(device_config: dict, host: Host | None = None) -> dict:
    """Everything the Setup Wizard offers for this Device on this host."""
    host = host or Host()
    backend = _backend(host)
    try:
        select_backend(host)
        experimental = None
    except GpioBackendError as e:
        experimental = str(e)
    return {
        "pi_model": host.pi_model(),
        "backend": backend.name if backend else None,
        "pin_channels": {str(pin): channel for pin, channel in sorted(backend.pin_channels.items())} if backend else {},
        "experimental": experimental,
        "power": estimate_power(device_config),
        "max_fps": max_fps(device_config["led_count"]),
        "split_suggestion": split_suggestion(device_config["led_count"]),
        "diagnosis": _diagnose(device_config, host),
    }


def _diagnose(device_config: dict, host: Host) -> dict:
    output = OUTPUTS[device_config["output_type"]]
    diagnosis = output.diagnose(device_config, host)
    return {"status": diagnosis.status.value, "message": diagnosis.message, "suggested_fix": diagnosis.suggested_fix}
