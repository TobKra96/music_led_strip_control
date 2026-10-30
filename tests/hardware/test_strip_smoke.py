"""Hardware smoke test: plays the rpi_ws281x strandtest animations once on a real strip. Run manually on a Pi with ``pytest -m hardware``.

Originally ``test/raspi_led_test.py`` (Tony DiCola's rpi_ws281x strandtest example).
"""
import time

import pytest

rpi_ws281x = pytest.importorskip("rpi_ws281x", reason="needs the rpi_ws281x library on a Raspberry Pi")

# LED strip configuration:
LED_COUNT = 16        # Number of LED pixels.
LED_PIN = 18          # GPIO pin connected to the pixels (18 uses PWM!).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10          # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False    # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53


def color_wipe(strip, color, wait_ms=50):
    """Wipe color across display a pixel at a time."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        strip.show()
        time.sleep(wait_ms / 1000.0)


def theater_chase(strip, color, wait_ms=50, iterations=10):
    """Movie theater light style chaser animation."""
    for _ in range(iterations):
        for q in range(3):
            for i in range(0, strip.numPixels(), 3):
                if i + q < strip.numPixels():
                    strip.setPixelColor(i + q, color)
            strip.show()
            time.sleep(wait_ms / 1000.0)
            for i in range(0, strip.numPixels(), 3):
                if i + q < strip.numPixels():
                    strip.setPixelColor(i + q, 0)


def wheel(pos):
    """Generate rainbow colors across 0-255 positions."""
    if pos < 85:
        return rpi_ws281x.Color(pos * 3, 255 - pos * 3, 0)
    if pos < 170:
        pos -= 85
        return rpi_ws281x.Color(255 - pos * 3, 0, pos * 3)
    pos -= 170
    return rpi_ws281x.Color(0, pos * 3, 255 - pos * 3)


def rainbow(strip, wait_ms=20, iterations=1):
    """Draw rainbow that fades across all pixels at once."""
    for j in range(256 * iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, wheel((i + j) & 255))
        strip.show()
        time.sleep(wait_ms / 1000.0)


def rainbow_cycle(strip, wait_ms=20, iterations=1):
    """Draw rainbow that uniformly distributes itself across all pixels."""
    for j in range(256 * iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, wheel((int(i * 256 / strip.numPixels()) + j) & 255))
        strip.show()
        time.sleep(wait_ms / 1000.0)


def theater_chase_rainbow(strip, wait_ms=50):
    """Rainbow movie theater light style chaser animation."""
    for j in range(256):
        for q in range(3):
            for i in range(0, strip.numPixels(), 3):
                if i + q < strip.numPixels():
                    strip.setPixelColor(i + q, wheel((i + j) % 255))
            strip.show()
            time.sleep(wait_ms / 1000.0)
            for i in range(0, strip.numPixels(), 3):
                if i + q < strip.numPixels():
                    strip.setPixelColor(i + q, 0)


@pytest.fixture
def strip():
    if "mock" in rpi_ws281x.Adafruit_NeoPixel.__module__:
        pytest.skip("rpi_ws281x is its mock here, not a real strip")
    strip = rpi_ws281x.Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    strip.begin()
    yield strip
    color_wipe(strip, rpi_ws281x.Color(0, 0, 0), 10)


def test_color_wipe(strip):
    for color in (rpi_ws281x.Color(255, 0, 0), rpi_ws281x.Color(0, 255, 0), rpi_ws281x.Color(0, 0, 255)):
        color_wipe(strip, color)


def test_theater_chase(strip):
    for color in (rpi_ws281x.Color(127, 127, 127), rpi_ws281x.Color(127, 0, 0), rpi_ws281x.Color(0, 0, 127)):
        theater_chase(strip, color)


def test_rainbow(strip):
    rainbow(strip)
    rainbow_cycle(strip)
    theater_chase_rainbow(strip)
