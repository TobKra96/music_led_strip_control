import numpy as np

class ColorService():
    def __init__(self, config):

        self._config = config
        self.full_gradients = {}

    def build_gradients(self):

        self.full_gradients = {}

        for gradient in self._config["gradients"]:
            not_mirrored_gradient = self._easing_gradient_generator(
                self._config["gradients"][gradient], # All colors of the current gradient
                self._config["device_config"]["LED_Count"]
            )

            # Mirror the gradient to get seemsles transition from start to the end
            # [1,2,3,4]
            # -> [1,2,3,4,4,3,2,1]
            self.full_gradients[gradient] = np.concatenate(
                (not_mirrored_gradient[:, ::-1], not_mirrored_gradient), 
                axis = 1
                )
                   


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