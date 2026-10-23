import numpy as np

from mlsc.effects.effect import Effect
from mlsc.strip import has_white_channel


class EffectSingle(Effect):
    def run(self):
        """Show one single color."""
        # Get the config of the current effect.
        effect_config = self.get_effect_config("effect_single")
        white_channel = has_white_channel(self._device.device_config)
        # Set Fallback Strip
        # self._led_strip_translated = ws.WS2811_STRIP_RGB

        # Build an empty array.
        if white_channel:
            output_array = np.zeros((4, self._device.device_config["led_count"]))
        else:
            output_array = np.zeros((3, self._device.device_config["led_count"]))

        if effect_config["use_custom_color"]:
            output_array[0][:] = effect_config["custom_color"][0]
            output_array[1][:] = effect_config["custom_color"][1]
            output_array[2][:] = effect_config["custom_color"][2]
        else:
            # Fill the array with the selected color.
            output_array[0][:] = self._config_colours[effect_config["color"]][0]
            output_array[1][:] = self._config_colours[effect_config["color"]][1]
            output_array[2][:] = self._config_colours[effect_config["color"]][2]

        if white_channel:
            output_array[3][:] = effect_config["white"]

        # Add the output array to the queue.
        self.queue_output_array_blocking(output_array)
