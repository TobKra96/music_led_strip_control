from libs.outputs.output import Output  # pylint: disable=E0611, E0401

import numpy as np


class OutputRaspi(Output):
    def __init__(self, device):
        # Call the constructor of the base class.
        super(OutputRaspi, self).__init__(device)

        import _rpi_ws281x as ws  # pylint: disable=import-error

        output_id = "output_raspi"

        # LED strip configuration:
        self._led_count = int(self._device_config["LED_Count"])                                 # Number of LED pixels.
        self._led_pin = int(self._device_config["output"][output_id]["LED_Pin"])                # GPIO pin connected to the pixels (18 uses PWM!).
        self._led_freq_hz = int(self._device_config["output"][output_id]["LED_Freq_Hz"])        # LED signal frequency in hertz (usually 800khz).
        self._led_dma = int(self._device_config["output"][output_id]["LED_Dma"])                # DMA channel to use for generating signal (try 10).
        self._led_brightness = int(self._device_config["output"][output_id]["LED_Brightness"])  # Set to '0' for darkest and 100 for brightest.
        self._led_invert = int(self._device_config["output"][output_id]["LED_Invert"])          # Set to 'True' to invert the signal (when using NPN transistor level shift).
        self._led_channel = int(self._device_config["output"][output_id]["LED_Channel"])        # set to '1' for GPIOs 13, 19, 41, 45 or 53.
        self._led_strip = self._device_config["output"][output_id]["LED_Strip"]

        # Set Fallback Strip
        self._led_strip_translated = ws.WS2811_STRIP_RGB

        self._led_strip_mapper = {
            "SK6812_STRIP_RGBW": ws.SK6812_STRIP_RGBW,
            "SK6812_STRIP_RBGW": ws.SK6812_STRIP_RBGW,
            "SK6812_STRIP_GRBW": ws.SK6812_STRIP_GRBW,
            "SK6812_STRIP_GBRW": ws.SK6812_STRIP_GBRW,
            "SK6812_STRIP_BRGW": ws.SK6812_STRIP_BRGW,
            "SK6812_STRIP_BGRW": ws.SK6812_STRIP_BGRW,
            "SK6812_SHIFT_WMASK": ws.SK6812_SHIFT_WMASK,
            "WS2811_STRIP_RGB": ws.WS2811_STRIP_RGB,
            "WS2811_STRIP_RBG": ws.WS2811_STRIP_RBG,
            "WS2811_STRIP_GRB": ws.WS2811_STRIP_GRB,
            "WS2811_STRIP_GBR": ws.WS2811_STRIP_GBR,
            "WS2811_STRIP_BRG": ws.WS2811_STRIP_BRG,
            "WS2811_STRIP_BGR": ws.WS2811_STRIP_BGR,
            "WS2812_STRIP": ws.WS2812_STRIP,
            "SK6812_STRIP": ws.SK6812_STRIP,
            "SK6812W_STRIP": ws.SK6812W_STRIP
        }


        try:
            led_strip = self._led_strip_mapper[self._led_strip]
            if led_strip is not None:
                self._led_strip_translated = led_strip
                print(f"Found Led Strip {self._led_strip}")
        except Exception as e:
            print(f"Could not find LED Strip Type. Exception: {str(e)}")
            pass

        self._led_brightness_translated = int(255 * (self._led_brightness / 100))

        print(f"LED Brightness: {self._led_brightness}")
        print(f"LED Brightness converted: {self._led_brightness_translated}")

        self._leds = ws.new_ws2811_t()

        self.channel = ws.ws2811_channel_get(self._leds, 0)

        ws.ws2811_channel_t_strip_type_set(self.channel, self._led_strip_translated)
        ws.ws2811_channel_t_count_set(self.channel, self._led_count)
        ws.ws2811_channel_t_gpionum_set(self.channel, self._led_pin)
        ws.ws2811_channel_t_invert_set(self.channel, self._led_invert)
        ws.ws2811_channel_t_brightness_set(self.channel, self._led_brightness_translated)

        ws.ws2811_t_freq_set(self._leds, self._led_freq_hz)
        ws.ws2811_t_dmanum_set(self._leds, self._led_dma)

        # Initialize library with LED configuration.
        resp = ws.ws2811_init(self._leds)
        if resp != ws.WS2811_SUCCESS:
            message = ws.ws2811_get_return_t_str(resp)
            raise RuntimeError(f'ws2811_init failed with code {resp} ({message})')

    def show(self, output_array):
        import _rpi_ws281x as ws  # pylint: disable=import-error

        # Typecast the array to int.
        output_array = output_array.clip(0, 255).astype(int)

        # Sort the colors as RGB type.
        r = np.left_shift(output_array[0][:].astype(int), 16)  # pylint: disable=assignment-from-no-return
        g = np.left_shift(output_array[1][:].astype(int), 8)  # pylint: disable=assignment-from-no-return
        b = output_array[2][:].astype(int)
        rgb = np.bitwise_or(np.bitwise_or(r, g), b).astype(int)

        # You can only use ws2811_leds_set with the custom version.
        # ws.ws2811_leds_set(self.channel, rgb)
        for i in range(self._led_count):
            ws.ws2811_led_set(self.channel, i, rgb[i].item())

        resp = ws.ws2811_render(self._leds)

        if resp != ws.WS2811_SUCCESS:
            message = ws.ws2811_get_return_t_str(resp)
            raise RuntimeError(f'ws2811_render failed with code {resp} ({message})')
