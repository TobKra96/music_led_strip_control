from libs.effects.effect import Effect  # pylint: disable=E0611, E0401

import numpy as np
import time


class EffectStrobe(Effect):

    def __init__(self, device):

        # Call the constructor of the base class.
        super(EffectStrobe, self).__init__(device)

        # needed to calculate the time
        self.now = time.time() * 1000
        self.last_time = time.time() * 1000

        # False = OFF, True = ON
        self.current_state = False

    def run(self):
        # Get the config of the current effect.
        effect_config = self.get_effect_config("effect_strobe")
        self._led_strip = self._device.device_config["led_strip"]

        speed = effect_config.get("speed", 1)

        self.now = time.time() * 1000

        if (self.now - self.last_time) > (1000 / speed):
            self.last_time = time.time() * 1000
            self.current_state = not self.current_state

        
        # Build an empty array.
        if "SK6812" in self._led_strip:
            output_array = np.zeros((4, self._device.device_config["led_count"]))
        else:
            output_array = np.zeros((3, self._device.device_config["led_count"]))

        if self.current_state:
            if effect_config.get("use_custom_color"):
                color = effect_config["custom_color"]
            else:
                color = self._config_colours[effect_config["color"]]
        else:
            color = self._config_colours["black"]

        # Fill the array with the selected color.
        output_array[0][:] = color[0]
        output_array[1][:] = color[1]
        output_array[2][:] = color[2]

        if "SK6812" in self._led_strip:
            output_array[3][:] = effect_config["white"]

        # Add the output array to the queue.
        self.queue_output_array_blocking(output_array)

