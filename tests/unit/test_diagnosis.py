import socket

import pytest

from mlsc.diagnosis import Diagnosis, Status, worst
from mlsc.host import Host
from mlsc.outputs.output import Output
from mlsc.outputs.output_dummy import OutputDummy
from mlsc.outputs.output_raspi import OutputRaspi
from mlsc.outputs.output_udp import OutputUDP

pytestmark = pytest.mark.unit


class FakeHost(Host):
    def __init__(self, **overrides) -> None:
        pi_4 = "Raspberry Pi 4 Model B Rev 1.4"
        self.values = {"has_ws281x": True, "pi_model": pi_4, "can_use_gpio_memory": True, "analog_audio_enabled": False, **overrides}

    def has_ws281x(self):
        return self.values["has_ws281x"]

    def pi_model(self):
        return self.values["pi_model"]

    def can_use_gpio_memory(self):
        return self.values["can_use_gpio_memory"]

    def analog_audio_enabled(self):
        return self.values["analog_audio_enabled"]


def raspi_config(pin=18):
    return {"output": {"output_raspi": {"led_pin": pin}}}


def udp_config(ip="127.0.0.1", port=7777):
    return {"output": {"output_udp": {"udp_client_ip": ip, "udp_client_port": port}}}


def test_diagnosis_event_carries_the_device_id():
    diagnosis = Diagnosis(Status.ERROR, "It broke.", "Fix it.")

    assert diagnosis.to_event("device_0") == {"device_id": "device_0", "status": "error", "message": "It broke.", "suggested_fix": "Fix it."}


def test_diagnosis_without_a_fix_has_a_null_suggested_fix():
    assert Diagnosis.ok("Fine.").to_event("d")["suggested_fix"] is None


def test_worst_picks_the_most_severe_and_the_first_of_a_kind():
    first = Diagnosis.warning("a")
    second = Diagnosis.warning("b")
    error = Diagnosis.error("c")

    assert worst([Diagnosis.ok("x"), first, second]) is first
    assert worst([first, error, second]) is error
    assert worst([]).status is Status.OK


def test_base_output_is_healthy_by_default():
    assert Output.diagnose({}).status is Status.OK


def test_mock_output_is_healthy():
    assert OutputDummy.diagnose({}).status is Status.OK


def test_raspi_is_healthy_on_a_pi_4_with_the_library():
    assert OutputRaspi.diagnose(raspi_config(), FakeHost()).status is Status.OK


def test_raspi_reports_a_missing_library():
    diagnosis = OutputRaspi.diagnose(raspi_config(), FakeHost(has_ws281x=False))

    assert diagnosis.status is Status.ERROR
    assert "rpi_ws281x" in diagnosis.message
    assert "pip install" in diagnosis.suggested_fix


def test_raspi_reports_permission_denied():
    diagnosis = OutputRaspi.diagnose(raspi_config(), FakeHost(can_use_gpio_memory=False))

    assert diagnosis.status is Status.ERROR
    assert "permission" in diagnosis.message.lower()
    assert "root" in diagnosis.suggested_fix


def test_raspi_warns_when_gpio_18_is_used_by_analog_audio():
    diagnosis = OutputRaspi.diagnose(raspi_config(18), FakeHost(analog_audio_enabled=True))

    assert diagnosis.status is Status.WARNING
    assert "GPIO 18" in diagnosis.message
    assert "dtparam=audio=off" in diagnosis.suggested_fix


def test_raspi_does_not_warn_about_audio_for_a_pin_without_pwm():
    assert OutputRaspi.diagnose(raspi_config(10), FakeHost(analog_audio_enabled=True)).status is Status.OK


def test_raspi_reports_that_no_pi_5_driver_is_installed():
    diagnosis = OutputRaspi.diagnose(raspi_config(), FakeHost(pi_model="Raspberry Pi 5 Model B Rev 1.0"))

    assert diagnosis.status is Status.ERROR
    assert "No Pi 5 driver installed" in diagnosis.message
    assert diagnosis.suggested_fix


def test_raspi_rejects_a_pin_the_backend_cannot_drive():
    diagnosis = OutputRaspi.diagnose(raspi_config(5), FakeHost())

    assert diagnosis.status is Status.ERROR
    assert "GPIO 5" in diagnosis.message


def test_raspi_error_wins_over_warning():
    host = FakeHost(pi_model="Raspberry Pi 5 Model B", has_ws281x=False)

    assert OutputRaspi.diagnose(raspi_config(), host).status is Status.ERROR


def test_udp_is_healthy_for_a_resolvable_host():
    assert OutputUDP.diagnose(udp_config()).status is Status.OK


def test_udp_reports_an_unresolvable_host(monkeypatch):
    def fail(*_args, **_kwargs):
        message = "nope"
        raise socket.gaierror(message)

    monkeypatch.setattr(socket, "getaddrinfo", fail)

    diagnosis = OutputUDP.diagnose(udp_config("no.such.host"))

    assert diagnosis.status is Status.ERROR
    assert "no.such.host" in diagnosis.message


@pytest.mark.parametrize("port", [0, 65536, -1])
def test_udp_reports_a_port_out_of_range(port):
    diagnosis = OutputUDP.diagnose(udp_config(port=port))

    assert diagnosis.status is Status.ERROR
    assert "port" in diagnosis.message.lower()


def test_udp_rejects_a_boolean_port_and_a_non_string_host():
    assert OutputUDP.diagnose(udp_config(port=True)).status is Status.ERROR
    assert OutputUDP.diagnose(udp_config(ip=123)).status is Status.ERROR


def test_udp_reports_an_empty_host():
    assert OutputUDP.diagnose(udp_config(ip="")).status is Status.ERROR
