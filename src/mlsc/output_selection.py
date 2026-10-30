"""Chooses the Output of a Device: the configured one, or the Mock Output when that one cannot work here."""
from collections.abc import Mapping

from loguru import logger

from mlsc.diagnosis import Diagnosis
from mlsc.gpio_backends import GpioBackendError
from mlsc.host import Host
from mlsc.output_enum import OutputsEnum
from mlsc.outputs.output import Output
from mlsc.outputs.output_mock import OutputMock

LOCAL_GPIO = OutputsEnum.output_raspi.name
SUFFIX = "Using the Mock Output instead."


def build_output(device, available: Mapping[str, type[Output]], host: Host | None = None) -> tuple[Output, Diagnosis | None]:
    """Create the Output of `device`.

    Returns the Output and, when it is the Mock Output only because the configured one could not be used, the Diagnosis that says why.
    The web UI stays reachable and the Strip Preview keeps working either way.
    """
    output_type = device.device_config["output_type"]
    if output_type == LOCAL_GPIO and not (host or Host()).can_drive_gpio():
        message = "Local GPIO output needs Linux and the rpi_ws281x library, so the Mock Output is used."
        return OutputMock(device), Diagnosis.warning(message, "Install rpi_ws281x on a Raspberry Pi, or choose the UDP output.")
    try:
        return available[output_type](device), None
    except GpioBackendError as e:
        logger.error(f"{e} {e.suggested_fix or ''}")
        return OutputMock(device), Diagnosis.warning(f"{e} {SUFFIX}", e.suggested_fix)
    except Exception as e:
        logger.exception(f"Could not start the {output_type} output.")
        return OutputMock(device), Diagnosis.warning(f"The {output_type} output could not be started ({e}). {SUFFIX}")
