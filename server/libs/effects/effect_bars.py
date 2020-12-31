from libs.effects.effect import Effect # pylint: disable=E0611, E0401

import numpy as np

class EffectBars(Effect):
    def run(self):
        effect_config = self._device.device_config["effects"]["effect_bars"]
        led_count = self._device.device_config["LED_Count"]
        led_mid = self._device.device_config["LED_Mid"]

        audio_data = self.get_audio_data()
        y = self.get_mel(audio_data)

        if y is None:
            return

         # Bit of fiddling with the y values
        y = np.copy(self._math_service.interpolate(y, led_count // 2))
        self._dsp.common_mode.update(y)
        self.prev_spectrum = np.copy(y)
        # Color channel mappings
        r = self._dsp.r_filt.update(y - self._dsp.common_mode.value)
        r = np.array([j for i in zip(r,r) for j in i])
        # Split y into [resulution] chunks and calculate the average of each
        max_values = np.array([max(i) for i in np.array_split(r, effect_config["resolution"])])
        max_values = np.clip(max_values, 0, 1)
        color_sets = []
        for i in range(effect_config["resolution"]):
            # [r,g,b] values from a multicolour gradient array at [resulution] equally spaced intervals
            color_sets.append([self._color_service.full_gradients[effect_config["color_mode"]]\
                              [j][i*(led_count//effect_config["resolution"])] for j in range(3)])
        output = np.zeros((3,led_count))
        chunks = np.array_split(output[0], effect_config["resolution"])
        n = 0
        # Assign blocks with heights corresponding to max_values and colours from color_sets
        for i in range(len(chunks)):
            m = len(chunks[i])
            for j in range(3):
                output[j][n:n+m] = color_sets[i][j]*max_values[i]
            n += m

        # Calculate how many steps the array will roll
        steps = self.get_roll_steps(effect_config["roll_speed"])
        
        self._color_service.full_gradients[effect_config["color_mode"]] = np.roll(
                    self._color_service.full_gradients[effect_config["color_mode"]],
                    steps*(-1 if effect_config["reverse_roll"] else 1),
                    axis=1)
        if effect_config["flip_lr"]:
            output = np.fliplr(output)

        if effect_config["mirror"]:
            # calculate the real mid
            real_mid = led_count / 2
            # add some tolerance for the real mid
            if (real_mid >= led_mid - 2) and (real_mid <= led_mid + 2):
                # Use the option with shrinking the array
                output = np.concatenate((output[:, ::-2], output[:, ::2]), axis=1)
            else:
                # Mirror the whole array. After this the array has the double size than led_count
                big_mirrored_array = np.concatenate((output[:, ::-1], output[:, ::1]), axis=1)
                start_of_array = led_count - led_mid
                end_of_array = start_of_array + led_count
                output = big_mirrored_array[:, start_of_array:end_of_array]
       
        self.queue_output_array_noneblocking(output)
        
        