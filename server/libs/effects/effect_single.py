from libs.effects.effect import Effect  # pylint: disable=E0611, E0401

import numpy as np


class EffectSingle(Effect):
    def run(self):
        """
        Show one single color.
        """
        # Get the config of the current effect.
        effect_config = self.get_effect_config("effect_single")
        self._led_strip = self._device.device_config["LED_Strip"]
        # Set Fallback Strip
        # self._led_strip_translated = ws.WS2811_STRIP_RGB

        # Build an empty array.
        if "SK6812" in self._led_strip:
            output_array = np.zeros((4, self._device.device_config["LED_Count"]))
        else:
            output_array = np.zeros((3, self._device.device_config["LED_Count"]))

        if effect_config["use_custom_color"]:
            output_array[0][:] = effect_config["custom_color"][0]
            output_array[1][:] = effect_config["custom_color"][1]
            output_array[2][:] = effect_config["custom_color"][2]
        else:
            # Fill the array with the selected color.
            output_array[0][:] = self._config_colours[effect_config["color"]][0]
            output_array[1][:] = self._config_colours[effect_config["color"]][1]
            output_array[2][:] = self._config_colours[effect_config["color"]][2]

        if "SK6812" in self._led_strip:
            output_array[3][:] = effect_config["white"]

        # Add the output array to the queue.
        self.queue_output_array_blocking(output_array)
