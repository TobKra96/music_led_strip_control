from libs.color_service import ColorService # pylint: disable=E0611, E0401

import numpy as np
import time


class ColorServiceGlobal():
    def __init__(self, config):
        self._config = config
        device_config = {}
        if len(self._config["device_configs"].keys()) > 0:
            device_key = list(self._config["device_configs"].keys())[0]
            device_config = self._config["device_configs"][device_key]
        else:
            device_config = self._config["default_device"]

        self._device_config = device_config
        self.full_gradients = {}
        self.full_fadegradients = {}
        self.full_slide = {}
        self.full_bubble = {}

        self.build_gradients()
        self.current_fade_color = {}
        self.current_fade_color[0] = 0
        self.current_fade_color[1] = 0
        self.current_fade_color[2] = 0
        self.last_fade_change_time = int(round(time.time() * 1000))

    def build_gradients(self):
        #print("Enter build_gradients() in ColorServiceGlobal")
        led_count = 1000

        self.full_gradients = {}

        for key in self._config["gradients"].keys():
            not_mirrored_gradient = self._easing_gradient_generator(
                self._config["gradients"][key], # All colors of the current gradient
                led_count
            )

            # Mirror the gradient to get seemsles transition from start to the end
            # [1,2,3,4]
            # -> [1,2,3,4,4,3,2,1]
            self.full_gradients[key] = np.concatenate(
                (not_mirrored_gradient[:, ::-1], not_mirrored_gradient), 
                axis = 1
                )
        #print("Leave build_gradients() in ColorServiceGlobal")

    def _easing_gradient_generator(self, colors, length):
        """
        returns np.array of given length that eases between specified colours

        parameters:
        colors - list, colours must be in self.config.colour_manager["colours"]
            eg. ["Red", "Orange", "Blue", "Purple"]
        length - int, length of array to return. should be from self.config.settings
            eg. self.config.settings["devices"]["my strip"]["configuration"]["N_PIXELS"]
        """
        def _easing_func(x, length, slope=2.5):
            # returns a nice eased curve with defined length and curve
            xa = (x/length)**slope
            return xa / (xa + (1 - (x/length))**slope)
        colors = colors[::-1] # needs to be reversed, makes it easier to deal with
        n_transitions = len(colors) - 1
        ease_length = length // n_transitions
        pad = length - (n_transitions * ease_length)
        output = np.zeros((3, length))
        ease = np.array([_easing_func(i, ease_length, slope=2.5) for i in range(ease_length)])
        # for r,g,b
        for i in range(3):
            # for each transition
            for j in range(n_transitions):
                # Starting ease value
                start_value = colors[j][i]
                # Ending ease value
                end_value = colors[j+1][i]
                # Difference between start and end
                diff = end_value - start_value
                # Make array of all start value
                base = np.empty(ease_length)
                base.fill(start_value)
                # Make array of the difference between start and end
                diffs = np.empty(ease_length)
                diffs.fill(diff)
                # run diffs through easing function to make smooth curve
                eased_diffs = diffs * ease
                # add transition to base values to produce curve from start to end value
                base += eased_diffs
                # append this to the output array
                output[i, j*ease_length:(j+1)*ease_length] = base
        # cast to int
        output = np.asarray(output, dtype=int)
        # pad out the ends (bit messy but it works and looks good)
        if pad:
            for i in range(3):
                output[i, -pad:] = output[i, -pad-1]
        return output

    def colour(self, colour):
        # returns the values of a given colour. use this function to get colour values.
        if colour in self._config["colours"]:
            return self._config["colours"][colour]
        else:
            print("colour {} has not been defined".format(colour))
            return (0,0,0)


    def get_global_fade_color(self, fade_speed, fade_gradient, fade_reverse):
        current_time = int(round(time.time() * 1000))
        time_diff = current_time - self.last_fade_change_time
        
        rolling_steps = int((fade_speed * time_diff) / 500)
        
        if rolling_steps >= 1:
            if fade_reverse:
                current_reverse_translated = -1
            else:
                current_reverse_translated = 1


            self.full_gradients[fade_gradient] = np.roll(
            self.full_gradients[fade_gradient],
            rolling_steps*current_reverse_translated,
            axis = 1)

            self.last_fade_change_time = int(round(time.time() * 1000))
        

        self.current_fade_color[0] = self.full_gradients[fade_gradient][0][0]
        self.current_fade_color[1] = self.full_gradients[fade_gradient][1][0]
        self.current_fade_color[2] = self.full_gradients[fade_gradient][2][0]

        return self.current_fade_color



