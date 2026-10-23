"""Reads a Device's strip settings: Chip Family, Colour Order and white channel."""

_RGB_INDEX = {"r": 0, "g": 1, "b": 2}


def has_white_channel(device_config: dict) -> bool:
    return bool(device_config["white_channel"])


def rpi_ws281x_strip_type(chip_family: str, colour_order: str, white_channel: bool) -> str:
    """Name of the `rpi_ws281x` strip type constant for a strip."""
    if white_channel and chip_family == "sk6812":
        return f"SK6812_STRIP_{colour_order.upper()}W"
    if colour_order == "grb":
        if chip_family == "ws2812":
            return "WS2812_STRIP"
        if chip_family == "sk6812":
            return "SK6812_STRIP"
    return f"WS2811_STRIP_{colour_order.upper()}"


def udp_channel_order(chip_family: str, colour_order: str) -> tuple[int, int, int]:
    """Indices into an RGB frame in the order the UDP client expects the colour channels.

    A ws2812 strip is sent as plain RGB, because the client's library applies its GRB order itself.
    """
    if chip_family == "ws2812":
        return 0, 1, 2
    return tuple(_RGB_INDEX[channel] for channel in colour_order)
