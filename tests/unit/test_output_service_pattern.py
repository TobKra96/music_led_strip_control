# ruff: file-ignore[private-member-access]
import queue
from typing import ClassVar

import numpy as np
import pytest

from mlsc.fps_limiter import FPSLimiter
from mlsc.gpio_backends.fake import FakeGpioBackend
from mlsc.output_service import OutputService
from mlsc.outputs.output_raspi import OutputRaspi
from mlsc.strip_pattern import Pattern, PatternChannel, PatternPlayer

pytestmark = pytest.mark.unit

LED_COUNT = 6


class Clock:
    def __init__(self) -> None:
        self.now = 10.0

    def __call__(self) -> float:
        return self.now


class Queue:
    def __init__(self) -> None:
        self._items = queue.SimpleQueue()

    def put_blocking(self, item):
        self._items.put(item)

    def get_blocking(self):
        return self._items.get()

    def empty(self):
        return self._items.empty()


class StubDevice:
    device_id = "device_0"
    device_config: ClassVar[dict] = {
        "device_name": "Desk", "output_type": "output_raspi", "led_count": LED_COUNT, "led_mid": 3, "fps": 60, "chip_family": "ws2812",
        "colour_order": "grb", "white_channel": False, "led_brightness": 100,
        "output": {"output_raspi": {"led_pin": 18, "led_freq_hz": 800000, "led_dma": 10, "led_channel": 0, "led_invert": 0}},
    }

    def __init__(self) -> None:
        self.output_queue = Queue()
        self.device_notification_queue_in = Queue()


class NoPreview:
    def frame(self, frame):
        pass


@pytest.fixture
def setup():
    clock = Clock()
    channel = PatternChannel(clock)
    device = StubDevice()
    backend = FakeGpioBackend()
    service = OutputService()
    service._device = device
    service._output_queue = device.output_queue
    service._device_notification_queue_in = device.device_notification_queue_in
    service._white_channel = False
    service._skip_output = False
    service._fps_limiter = FPSLimiter(1000)
    service._current_output = OutputRaspi(device, backend)
    service._preview = NoPreview()
    service._pattern = PatternPlayer(channel, "device_0", LED_COUNT, 3, False)
    service.ten_seconds_counter = service.start_time = 0
    return service, channel, clock, device, backend


def effect_frame(value):
    return np.full((3, LED_COUNT), value)


def test_the_effect_is_shown_while_no_pattern_runs(setup):
    service, _, _, device, backend = setup
    device.output_queue.put_blocking(effect_frame(7))

    service.output_routine()

    assert [frame.tolist() for frame in backend.frames] == [effect_frame(7).tolist()]


def test_a_pattern_replaces_the_effect_and_the_strip_is_restored_after_the_timeout(setup):
    service, channel, clock, device, backend = setup
    channel.start("device_0", Pattern.power, 5)

    device.output_queue.put_blocking(effect_frame(7))
    service.output_routine()
    assert backend.frames[-1].tolist() == np.full((3, LED_COUNT), 255).tolist()
    assert device.output_queue.empty()

    clock.now += 6
    device.output_queue.put_blocking(effect_frame(9))
    service.output_routine()
    assert backend.frames[-1].tolist() == effect_frame(9).tolist()


def test_a_pattern_is_shown_even_when_the_effect_sends_no_frame(setup):
    service, channel, _, _, backend = setup
    channel.start("device_0", Pattern.markers, 5)

    service.output_routine()

    assert len(backend.frames) == 1
