import pytest

from mlsc.strip import has_white_channel, rpi_ws281x_strip_type, udp_channel_order

pytestmark = pytest.mark.unit


def test_white_channel_is_read_from_the_device_config():
    assert has_white_channel({"white_channel": True}) is True
    assert has_white_channel({"white_channel": False}) is False


@pytest.mark.parametrize(("chip_family", "colour_order", "white", "expected"), [
    ("ws2812", "grb", False, "WS2812_STRIP"),
    ("sk6812", "grb", False, "SK6812_STRIP"),
    ("ws2811", "rgb", False, "WS2811_STRIP_RGB"),
    ("ws2811", "bgr", False, "WS2811_STRIP_BGR"),
    ("ws2812", "brg", False, "WS2811_STRIP_BRG"),
    ("sk6812", "rgb", False, "WS2811_STRIP_RGB"),
    ("sk6812", "grb", True, "SK6812_STRIP_GRBW"),
    ("sk6812", "bgr", True, "SK6812_STRIP_BGRW"),
    ("ws2811", "rgb", True, "WS2811_STRIP_RGB"),
])
def test_rpi_ws281x_strip_type_name(chip_family, colour_order, white, expected):
    assert rpi_ws281x_strip_type(chip_family, colour_order, white) == expected


@pytest.mark.parametrize(("chip_family", "colour_order", "expected"), [
    ("ws2811", "rgb", (0, 1, 2)),
    ("ws2811", "bgr", (2, 1, 0)),
    ("ws2811", "grb", (1, 0, 2)),
    ("sk6812", "rbg", (0, 2, 1)),
    ("sk6812", "brg", (2, 0, 1)),
    ("sk6812", "gbr", (1, 2, 0)),
    ("ws2812", "grb", (0, 1, 2)),  # ws2812_strip never reordered on the wire; the client's library does it
])
def test_udp_channel_order(chip_family, colour_order, expected):
    assert udp_channel_order(chip_family, colour_order) == expected
