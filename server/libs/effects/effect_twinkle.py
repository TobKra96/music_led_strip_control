from libs.effects.effect import Effect # pylint: disable=E0611, E0401

import numpy as np
import random

class EffectTwinkle(Effect):

    def __init__(self, config, config_lock, output_queue, output_queue_lock, audio_queue, audio_queue_lock):

        # Call the constructor of the base class.
        super(EffectTwinkle, self).__init__(config, config_lock, output_queue, output_queue_lock, audio_queue, audio_queue_lock)

        # Twinkle Variables
        self.rising_stars = []
        self.descending_stars = []
        self.output_decay = np.array([[0 for i in range(led_count)] for i in range(3)])
        

    def run(self):
        # Get the config of the current effect
        effect_config = self._device.device_config["effects"]["effect_twinkle"]
        led_count = self._device.device_config["LED_Count"]

        # Rising Star array format: [[r,g,b], [start_position, end_position], percent_brightness]

        # Reset output array
        self.output = np.zeros((3, self._device.device_config["LED_Count"]))


        # Random add off the stars, depending on speed settings
        if random.randrange (0, 100, 1) <= effect_config["star_appears_speed"]:
            # add a star only if the list is not full
            if len(self.rising_stars) < effect_config["stars_count"]:
                gradient = self._config["gradients"][effect_config["gradient"]]
                number_of_colors = len(gradient)
                selected_color_index = random.randrange(0, number_of_colors, 1)

                star_start_position = random.randrange(0, led_count, 1)
                star_end_position = star_start_position + effect_config["stars_length"]
                
                # Check if end position still in array
                if star_end_position > led_count - 1:
                    star_end_position = led_count - 1            

                # Add the new rising star with a random color out of the gradient selection.
                self.rising_stars.append([[gradient[selected_color_index][0], gradient[selected_color_index][1], gradient[selected_color_index][2]], [star_start_position, star_end_position], 1])

        remove_stars_rising = []

        # Set the new rising stars value
        for current_star in self.rising_stars:
            current_star[2] = current_star[2] + effect_config["star_rising_speed"]
            # Only allow 100 percent
            if current_star[2] > 100:
                current_star[2] = 100
            
            if current_star[2] == 100:
                self.descending_stars.append(current_star)
                remove_stars_rising.append(current_star)
                # the star will be created in the de
            else:
                self.output[0, current_star[1][0]:current_star[1][1]] = int(current_star[0][0] * (current_star[2]/100))
                self.output[1, current_star[1][0]:current_star[1][1]] = int(current_star[0][1] * (current_star[2]/100))
                self.output[2, current_star[1][0]:current_star[1][1]] = int(current_star[0][2] * (current_star[2]/100))

        # remove the stars from the rising array
        for current_star_to_remove in remove_stars_rising:
            self.rising_stars.remove(current_star_to_remove)

        remove_stars_descending = []

        # Set the new descending stars value
        for current_star in self.descending_stars:
            current_star[2] = current_star[2] - effect_config["star_descending_speed"]
            # Only allow 0 percent
            if current_star[2] < 0:
                current_star[2] = 0
            
            if current_star[2] == 0:
                remove_stars_descending.append(current_star)

            self.output[0, current_star[1][0]:current_star[1][1]] = int(current_star[0][0] * (current_star[2]/100))
            self.output[1, current_star[1][0]:current_star[1][1]] = int(current_star[0][1] * (current_star[2]/100))
            self.output[2, current_star[1][0]:current_star[1][1]] = int(current_star[0][2] * (current_star[2]/100))

        # remove the stars from the descending array
        for current_star_to_remove in remove_stars_descending:
            self.descending_stars.remove(current_star_to_remove)

        self.output = gaussian_filter1d(self.output, sigma=effect_config["blur"])

        # Add the output array to the queue
        self._output_queue_lock.acquire()
        self._output_queue.put(self.output)
        self._output_queue_lock.release()