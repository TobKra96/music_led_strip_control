# ruff: file-ignore[unused-method-argument, no-self-use]
import sys

import numpy as np
import pytest

from mlsc.config_migration import load_template
from mlsc.diagnosis import Status
from mlsc.gpio_backends import GpioBackendError, GpioStrip, select_backend
from mlsc.gpio_backends.fake import FakeGpioBackend
from mlsc.gpio_backends.ws281x_backend import Ws281xBackend
from mlsc.host import Host
from mlsc.outputs.output_raspi import OutputRaspi

pytestmark = pytest.mark.unit

ADVANCED = {"led_freq_hz": 800000, "led_dma": 10, "led_channel": 0, "led_invert": 0}


class FakeWs:
    WS2811_SUCCESS = 0
    WS2811_STRIP_RGB = "rgb"
    WS2812_STRIP = "ws2812"
    SK6812_STRIP_GRBW = "grbw"

    def __init__(self, init_code=0, render_code=0, init_message=None) -> None:
        self.init_code = init_code
        self.render_code = render_code
        self.init_message = init_message
        self.leds = {}
        self.calls = []
        self.finalised = False

    def new_ws2811_t(self):
        return object()

    def ws2811_channel_get(self, leds, channel):
        self.calls.append(("channel", channel))
        return "channel"

    def ws2811_channel_t_strip_type_set(self, channel, value):
        self.calls.append(("strip_type", value))

    def ws2811_channel_t_count_set(self, channel, value):
        self.calls.append(("count", value))

    def ws2811_channel_t_gpionum_set(self, channel, value):
        self.calls.append(("pin", value))

    def ws2811_channel_t_invert_set(self, channel, value):
        self.calls.append(("invert", value))

    def ws2811_channel_t_brightness_set(self, channel, value):
        self.calls.append(("brightness", value))

    def ws2811_t_freq_set(self, leds, value):
        self.calls.append(("freq", value))

    def ws2811_t_dmanum_set(self, leds, value):
        self.calls.append(("dma", value))

    def ws2811_init(self, leds):
        return self.init_code

    def ws2811_get_return_t_str(self, code):
        return self.init_message or f"error {code}"

    def ws2811_led_set(self, channel, index, value):
        self.leds[index] = value

    def ws2811_render(self, leds):
        return self.render_code

    def ws2811_fini(self, leds):
        self.finalised = True


class PiHost(Host):
    def __init__(self, model=None) -> None:
        self.model = model

    def pi_model(self):
        return self.model


def strip(**overrides):
    values = {"chip_family": "ws2812", "colour_order": "grb", "white_channel": False, "led_count": 3, "pin": 18, "brightness": 50,
              "advanced": ADVANCED, **overrides}
    return GpioStrip(**values)


def started(ws=None, **overrides):
    ws = ws or FakeWs()
    backend = Ws281xBackend(ws)
    backend.init(strip(**overrides))
    return backend, ws


def test_init_configures_the_library_from_the_strip():
    _, ws = started()

    assert ("strip_type", "ws2812") in ws.calls
    assert ("pin", 18) in ws.calls
    assert ("count", 3) in ws.calls
    assert ("brightness", 127) in ws.calls
    assert ("freq", 800000) in ws.calls
    assert ("dma", 10) in ws.calls


def test_init_failure_raises_a_backend_error_with_a_fix():
    with pytest.raises(GpioBackendError, match="ws2811_init failed with code 3") as e:
        started(FakeWs(init_code=3))

    assert e.value.suggested_fix


def test_init_failure_about_permissions_suggests_root():
    with pytest.raises(GpioBackendError) as e:
        started(FakeWs(init_code=1, init_message="mmap() failed"))

    assert "root" in e.value.suggested_fix


def test_init_rejects_a_pin_the_library_cannot_drive():
    with pytest.raises(GpioBackendError, match="GPIO 5"):
        started(pin=5)


def test_init_rejects_a_strip_type_the_library_lacks():
    with pytest.raises(GpioBackendError, match="no strip type"):
        started(chip_family="ws2811", colour_order="bgr")


def test_a_missing_library_is_a_backend_error_not_a_silent_return(monkeypatch):
    monkeypatch.setitem(sys.modules, "_rpi_ws281x", None)
    monkeypatch.setitem(sys.modules, "rpi_ws281x", None)

    with pytest.raises(GpioBackendError, match="not installed") as e:
        Ws281xBackend().init(strip())

    assert "mlsc[pi]" in e.value.suggested_fix


def test_show_packs_rgb_pixels():
    backend, ws = started()

    backend.show(np.array([[255, 0, 300], [0, 255, -5], [0, 0, 255]]))

    assert ws.leds == {0: 0xFF00, 1: 0xFF0000, 2: 0xFF00 | 0xFF}


def test_show_packs_the_white_channel():
    backend, ws = started(chip_family="sk6812", colour_order="grb", white_channel=True)

    backend.show(np.array([[1], [2], [3], [4]]).repeat(3, axis=1))

    assert ws.leds[0] == (2 << 24) | (1 << 16) | (3 << 8) | 4


def test_show_reports_a_render_failure():
    backend, _ = started(FakeWs(render_code=2))

    with pytest.raises(GpioBackendError, match="ws2811_render failed"):
        backend.show(np.zeros((3, 3)))


def test_show_before_init_fails():
    with pytest.raises(GpioBackendError, match="not initialised"):
        Ws281xBackend(FakeWs()).show(np.zeros((3, 3)))


def test_close_releases_the_library_once():
    backend, ws = started()

    backend.close()
    assert ws.finalised
    ws.finalised = False
    backend.close()

    assert ws.finalised is False


@pytest.mark.parametrize("model", ["Raspberry Pi 3 Model B", "Raspberry Pi 4 Model B", "Raspberry Pi Zero 2 W Rev 1.0", None])
def test_pi_3_pi_4_zero_2_w_and_other_hosts_use_rpi_ws281x(model):
    assert select_backend(PiHost(model)) is Ws281xBackend


def test_pi_5_has_no_backend():
    with pytest.raises(GpioBackendError, match="No Pi 5 driver installed") as e:
        select_backend(PiHost("Raspberry Pi 5 Model B Rev 1.0"))

    assert e.value.to_diagnosis().status is Status.ERROR


def test_the_fake_backend_records_frames():
    fake = FakeGpioBackend()
    fake.init(strip())
    frame = np.ones((3, 3))

    fake.show(frame)
    frame[:] = 0
    fake.close()

    assert fake.strip.pin == 18
    assert fake.frames[0].sum() == 9
    assert fake.closed
    assert fake.diagnose({}, PiHost()).status is Status.OK


class Device:
    def __init__(self) -> None:
        self.device_config = {**load_template()["default_device"], "led_count": 3}


def test_output_raspi_hands_the_strip_and_frames_to_the_backend():
    backend = FakeGpioBackend()
    output = OutputRaspi(Device(), backend)

    output.show(np.ones((3, 3)))
    output.close()

    assert backend.strip.led_count == 3
    assert backend.strip.advanced["led_dma"] == 10
    assert len(backend.frames) == 1
    assert backend.closed


def test_output_raspi_raises_the_backend_error_instead_of_a_bare_runtime_error():
    error = GpioBackendError("ws2811_init failed", "Run as root.")

    with pytest.raises(GpioBackendError) as e:
        OutputRaspi(Device(), FakeGpioBackend(init_error=error))

    assert e.value is error
