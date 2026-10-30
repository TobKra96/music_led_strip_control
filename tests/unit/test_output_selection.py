# ruff: file-ignore[unused-method-argument, raise-vanilla-args, raw-string-in-exception]
import pytest

from mlsc.diagnosis import Diagnosis, Status
from mlsc.gpio_backends import GpioBackendError
from mlsc.host import Host
from mlsc.output_selection import build_output
from mlsc.outputs.output import Output
from mlsc.outputs.output_mock import OutputMock

pytestmark = pytest.mark.unit


class FakeHost(Host):
    def __init__(self, gpio=True) -> None:
        self.gpio = gpio

    def can_drive_gpio(self):
        return self.gpio


class StubDevice:
    def __init__(self, output_type) -> None:
        self.device_config = {"output_type": output_type, "device_name": "Desk"}


class WorkingRaspi(Output):
    pass


class BrokenRaspi(Output):
    def __init__(self, device) -> None:
        raise GpioBackendError("ws2811_init failed with code 3.", "Run MLSC as root.")


class CrashingRaspi(Output):
    def __init__(self, device) -> None:
        raise OSError("boom")


class WorkingUdp(Output):
    pass


def outputs(raspi):
    return {"output_dummy": OutputMock, "output_raspi": raspi, "output_udp": WorkingUdp}


def test_the_configured_output_is_used_when_it_works():
    output, diagnosis = build_output(StubDevice("output_raspi"), outputs(WorkingRaspi), FakeHost())

    assert type(output) is WorkingRaspi
    assert diagnosis is None


def test_local_gpio_without_the_driver_is_the_mock_output_by_default():
    output, diagnosis = build_output(StubDevice("output_raspi"), outputs(WorkingRaspi), FakeHost(gpio=False))

    assert type(output) is OutputMock
    assert diagnosis.status is Status.WARNING


def test_the_mock_output_is_not_a_fallback_when_it_is_configured():
    output, diagnosis = build_output(StubDevice("output_dummy"), outputs(WorkingRaspi), FakeHost(gpio=False))

    assert type(output) is OutputMock
    assert diagnosis is None


def test_a_hardware_failure_falls_back_to_the_mock_output_with_the_fix():
    output, diagnosis = build_output(StubDevice("output_raspi"), outputs(BrokenRaspi), FakeHost())

    assert type(output) is OutputMock
    assert diagnosis == Diagnosis.warning("ws2811_init failed with code 3. Using the Mock Output instead.", "Run MLSC as root.")


def test_an_unexpected_failure_falls_back_too():
    output, diagnosis = build_output(StubDevice("output_raspi"), outputs(CrashingRaspi), FakeHost())

    assert type(output) is OutputMock
    assert "boom" in diagnosis.message


def test_a_unix_without_a_gpio_driver_does_not_affect_udp():
    output, diagnosis = build_output(StubDevice("output_udp"), outputs(WorkingRaspi), FakeHost(gpio=False))

    assert type(output) is WorkingUdp
    assert diagnosis is None
