"""Golden wire-format tests for the UDP client protocol, over a real loopback socket (no internet).

One datagram per frame: the channels are interleaved per pixel ("F" order), one byte each, in the strip's
channel order, after scaling by ``led_brightness``. The ESP clients rely on exactly this layout.
"""
import socket
from types import SimpleNamespace

import numpy as np
import pytest
from conftest import FakeDevice

from mlsc.config_converter.config_converter_v4 import LED_STRIP_MAPPING
from mlsc.outputs.output_udp import OutputUDP

pytestmark = pytest.mark.contract

# Pixel 0 is (R, G, B) = (10, 20, 30), pixel 1 is (40, 50, 60), pixel 2 is (70, 80, 90).
RGB_FRAME = np.array([[10, 40, 70], [20, 50, 80], [30, 60, 90]], dtype=float)
RGBW_FRAME = np.vstack([RGB_FRAME, [[1, 2, 3]]])

LED_STRIPS = {name: mapping[:3] for name, mapping in LED_STRIP_MAPPING.items()}


@pytest.fixture
def receiver():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    sock.settimeout(2)
    yield sock
    sock.close()


def make_output(receiver, led_strip="ws2811_strip_rgb", brightness=100):
    chip_family, colour_order, white_channel = LED_STRIPS[led_strip]
    config = {
        "chip_family": chip_family,
        "colour_order": colour_order,
        "white_channel": white_channel,
        "led_brightness": brightness,
        "output": {"output_udp": {"udp_client_ip": "127.0.0.1", "udp_client_port": str(receiver.getsockname()[1])}},
    }
    return OutputUDP(FakeDevice(config))


def send(receiver, frame, **kwargs):
    make_output(receiver, **kwargs).show(frame)
    return receiver.recvfrom(4096)[0]


def test_rgb_frame_is_interleaved_per_pixel(receiver):
    assert send(receiver, RGB_FRAME) == bytes([10, 20, 30, 40, 50, 60, 70, 80, 90])


@pytest.mark.parametrize(
    ("led_strip", "expected_first_pixel"),
    [
        ("ws2811_strip_rgb", (10, 20, 30)),
        ("ws2811_strip_rbg", (10, 30, 20)),
        ("ws2811_strip_grb", (20, 10, 30)),
        ("ws2811_strip_gbr", (20, 30, 10)),
        ("ws2811_strip_brg", (30, 10, 20)),
        ("ws2811_strip_bgr", (30, 20, 10)),
    ],
)
def test_colour_order_of_three_channel_strips(receiver, led_strip, expected_first_pixel):
    payload = send(receiver, RGB_FRAME, led_strip=led_strip)

    assert tuple(payload[:3]) == expected_first_pixel
    assert len(payload) == 9


@pytest.mark.parametrize(
    ("led_strip", "expected_first_pixel"),
    [
        ("sk6812_strip_rgbw", (10, 20, 30, 1)),
        ("sk6812_strip_rbgw", (10, 30, 20, 1)),
        ("sk6812_strip_grbw", (20, 10, 30, 1)),
        ("sk6812_strip_gbrw", (20, 30, 10, 1)),
        ("sk6812_strip_brgw", (30, 10, 20, 1)),
        ("sk6812_strip_bgrw", (30, 20, 10, 1)),
    ],
)
def test_four_channel_frame_ends_each_pixel_with_white(receiver, led_strip, expected_first_pixel):
    payload = send(receiver, RGBW_FRAME, led_strip=led_strip)

    assert tuple(payload[:4]) == expected_first_pixel
    assert len(payload) == 12


def test_sk6812_strip_receiving_three_channels_keeps_them_in_order(receiver):
    assert send(receiver, RGB_FRAME, led_strip="sk6812_strip_grbw")[:3] == bytes([20, 10, 30])


def test_brightness_scales_values_and_truncates(receiver):
    assert send(receiver, RGB_FRAME, brightness=50) == bytes([5, 10, 15, 20, 25, 30, 35, 40, 45])


def test_values_are_clipped_to_a_byte(receiver):
    frame = np.array([[-5, 300], [0, 255], [256, 0]], dtype=float)

    assert send(receiver, frame) == bytes([0, 0, 255, 255, 255, 0])


def test_one_datagram_per_frame(receiver):
    output = make_output(receiver)
    output.show(RGB_FRAME)
    output.show(RGB_FRAME * 2)

    assert receiver.recvfrom(4096)[0] == bytes([10, 20, 30, 40, 50, 60, 70, 80, 90])
    assert receiver.recvfrom(4096)[0] == bytes([20, 40, 60, 80, 100, 120, 140, 160, 180])


def test_send_failure_is_swallowed_and_the_socket_recreated(receiver):
    output = make_output(receiver)

    def boom(*_args):
        msg = "unreachable"
        raise OSError(msg)

    output._sock = SimpleNamespace(sendto=boom)

    output.show(RGB_FRAME)

    assert isinstance(output._sock, socket.socket)
    output.show(RGB_FRAME)
    assert receiver.recvfrom(4096)[0] == bytes([10, 20, 30, 40, 50, 60, 70, 80, 90])


def test_udp_config_keys_are_read_with_string_port(receiver):
    output = make_output(receiver)

    assert output._udp_client_ip == "127.0.0.1"
    assert output._udp_client_port == receiver.getsockname()[1]
