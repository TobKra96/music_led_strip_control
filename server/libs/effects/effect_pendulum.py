from libs.effects.effect import Effect # pylint: disable=E0611, E0401

import numpy as np

class EffectPendulum(Effect):

    def __init__(self, config, config_lock, output_queue, output_queue_lock, audio_queue, audio_queue_lock):

        # Call the constructor of the base class.
        super(EffectPendulum, self).__init__(config, config_lock, output_queue, output_queue_lock, audio_queue, audio_queue_lock)

        # Pendulum Variables
        self.current_direction = True
        self.current_position = 0
        self.current_color = [0,0,0]
        self.current_color_index = 0


    def run(self):
        # Get the config of the current effect
        effect_config = self._device.device_config["effects"]["effect_pendulum"]
        led_count = self._device.device_config["LED_Count"]

        if (self.current_position == 0) or (self.current_position == led_count - 1):
            if effect_config["change_color"]:
                gradient = self._config["gradients"][effect_config["gradient"]]
                count_colors_in_gradient = len(gradient)

                self.current_color_index = self.current_color_index + 1
                if self.current_color_index > count_colors_in_gradient - 1:
                    self.current_color_index = 0
                
                self.current_color = gradient[self.current_color_index]

            else:
                self.current_color = self._color_service.colour(effect_config["color"])

        # Build an empty array
        output_array = np.zeros((3, self._device.device_config["LED_Count"]))

        # Calculate how many steps the array will roll
        steps = self.get_roll_steps(effect_config["speed"])

        if self.current_direction:
            # start                                                       end
            # |-----------------------------------------------------------|
            #               ----> Direction

            # Fix the direction swap
            if self.current_position == 0:
                self.current_position = effect_config["pendulum_length"]

            self.current_position = self.current_position + steps

            if self.current_position > led_count - 1:
                self.current_position = led_count - 1
                self.current_direction = False
            
            start_position = self.current_position
            end_position = start_position - effect_config["pendulum_length"]
            if end_position < 0:
                end_position = 0

            output_array[0, end_position:start_position] = self.current_color[0]
            output_array[1, end_position:start_position] = self.current_color[1]
            output_array[2, end_position:start_position] = self.current_color[2]

        else:
            # end                                                       start
            # |-----------------------------------------------------------|
            #               <---- Direction

            # Fix the direction swap
            if self.current_position == led_count - 1:
                self.current_position = (led_count - 1) - effect_config["pendulum_length"]

            self.current_position = self.current_position - steps

            if self.current_position < 0:
                self.current_position = 0
                self.current_direction = True
            
            start_position = self.current_position
            end_position = start_position + effect_config["pendulum_length"]
            if end_position > led_count - 1:
                end_position = led_count - 1

            output_array[0, start_position:end_position] = self.current_color[0]
            output_array[1, start_position:end_position] = self.current_color[1]
            output_array[2, start_position:end_position] = self.current_color[2]


        # Add the output array to the queue
        self._output_queue_lock.acquire()
        self._output_queue.put(output_array)
        self._output_queue_lock.release()