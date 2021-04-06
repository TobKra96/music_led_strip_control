from libs.effects.effect import Effect  # pylint: disable=E0611, E0401

from random import randint
import numpy as np


class EffectFireplace(Effect):
    def run(self):
        # Get the config of the current effect.
        effect_config = self.get_effect_config("effect_fireplace")
        # Build an empty array.
        output_array = np.zeros((3, self._device.device_config["LED_Count"]))

        led_count = self._device.device_config["LED_Count"]

        steps = self.get_roll_steps(5)

        if effect_config["use_custom_color"]:
            for i in range(led_count):
                rand = randint(50, 150)
                output_array[0][i:i + 1] = effect_config["custom_color"][0] - rand
                output_array[1][i:i + 1] = effect_config["custom_color"][1] - rand
                output_array[2][i:i + 1] = effect_config["custom_color"][2] - rand
                output_array = np.roll(
                    output_array,
                    steps,
                    axis=1
                )
        else:
            for i in range(led_count):
                rand = randint(50, 200)
                output_array[0][i:i + 1] = self._config_colours[effect_config["color"]][0] - rand
                output_array[1][i:i + 1] = self._config_colours[effect_config["color"]][1] - rand
                output_array[2][i:i + 1] = self._config_colours[effect_config["color"]][2] - rand
                output_array = np.roll(
                    output_array,
                    steps,
                    axis=1
                )

        # Add the output array to the queue.
        self.queue_output_array_blocking(output_array)
