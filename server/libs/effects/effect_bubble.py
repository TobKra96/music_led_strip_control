from libs.effects.effect import Effect  # pylint: disable=E0611, E0401

import numpy as np


class EffectBubble(Effect):
    def run(self):
        # Get the config of the current effect.
        effect_config = self.get_effect_config("effect_bubble")
        led_count = self._device.device_config["led_count"]
        led_mid = self._device.device_config["led_mid"]

        # Translate the true and false to a number, for the function use.
        current_reverse_translated = 0
        if effect_config["reverse"]:
            current_reverse_translated = -1
        else:
            current_reverse_translated = 1

        full_bubble_ref = self._color_service.full_bubble

        # Build an array with the currently selected gradient.
        # Cut the slide to the led count length.
        output_array = np.array(
            [
                full_bubble_ref[effect_config["gradient"]][0][:led_count],
                full_bubble_ref[effect_config["gradient"]][1][:led_count],
                full_bubble_ref[effect_config["gradient"]][2][:led_count]
            ]
        )

        # Calculate how many steps the array will roll.
        steps = self.get_roll_steps(effect_config["speed"])

        # We got the current output array. Now we prepare the next step. We "roll" the array with the specified speed.
        full_bubble_ref[effect_config["gradient"]] = np.roll(
            full_bubble_ref[effect_config["gradient"]],
            steps * current_reverse_translated,
            axis=1
        )

        if effect_config["mirror"]:
            # Calculate the real mid.
            real_mid = led_count / 2
            # Add some tolerance for the real mid.
            if (real_mid >= led_mid - 2) and (real_mid <= led_mid + 2):
                # Use the option with shrinking the array.
                output_array = np.concatenate((output_array[:, ::-2], output_array[:, ::2]), axis=1)
            else:
                # Mirror the whole array. After this the array has a two times bigger size than led_count.
                big_mirrored_array = np.concatenate((output_array[:, ::-1], output_array[:, ::1]), axis=1)
                start_of_array = led_count - led_mid
                end_of_array = start_of_array + led_count
                output_array = big_mirrored_array[:, start_of_array:end_of_array]

        # Add the output array to the queue.
        self.queue_output_array_blocking(output_array)
