from libs.outputs.output import Output # pylint: disable=E0611, E0401

import numpy as np

class OutputRaspi(Output):
    def __init__(self, device):

        # Call the constructor of the base class.
        super(OutputRaspi, self).__init__(device)

        import _rpi_ws281x as ws # pylint: disable=import-error

        output_id = "output_raspi"

        # LED strip configuration:
        self._led_count       = int(self._device_config["LED_Count"])      # Number of LED pixels.
        self._led_pin         = int(self._device_config["output"][output_id]["LED_Pin"])        # GPIO pin connected to the pixels (18 uses PWM!).
        self._led_freq_hz     = int(self._device_config["output"][output_id]["LED_Freq_Hz"])    # LED signal frequency in hertz (usually 800khz)
        self._led_dma         = int(self._device_config["output"][output_id]["LED_Dma"])        # DMA channel to use for generating signal (try 10)
        self._led_brightness  = int(self._device_config["output"][output_id]["LED_Brightness"]) # Set to 0 for darkest and 100 for brightest
        self._led_invert      = int(self._device_config["output"][output_id]["LED_Invert"])     # True to invert the signal (when using NPN transistor level shift)
        self._led_channel     = int(self._device_config["output"][output_id]["LED_Channel"])    # set to '1' for GPIOs 13, 19, 41, 45 or 53

        
        self._led_brightness_translated = int(255 * (self._led_brightness / 100))

        print("LED Brightness: " + str(self._led_brightness))
        print("LED Brightness Translated: " + str(self._led_brightness_translated))

        self._leds = ws.new_ws2811_t()

        self.channel = ws.ws2811_channel_get(self._leds, 0)

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
	        raise RuntimeError('ws2811_init failed with code {0} ({1})'.format(resp, message))

    def show(self, output_array):
        import _rpi_ws281x as ws # pylint: disable=import-error

        # Typecast the array to int
        output_array = output_array.clip(0, 255).astype(int)

        # sort the colors. grb
        g = np.left_shift(output_array[1][:].astype(int), 16) # pylint: disable=assignment-from-no-return
        r = np.left_shift(output_array[0][:].astype(int), 8) # pylint: disable=assignment-from-no-return    
        b = output_array[2][:].astype(int)
        rgb = np.bitwise_or(np.bitwise_or(r, g), b).astype(int)

        # You can only use ws2811_leds_set with the custom version.
        #ws.ws2811_leds_set(self.channel, rgb)
        for i in range(self._led_count):
            ws.ws2811_led_set(self.channel, i, rgb[i].item())


        resp = ws.ws2811_render(self._leds)

        if resp != ws.WS2811_SUCCESS:
            message = ws.ws2811_get_return_t_str(resp)
            raise RuntimeError('ws2811_render failed with code {0} ({1})'.format(resp, message))