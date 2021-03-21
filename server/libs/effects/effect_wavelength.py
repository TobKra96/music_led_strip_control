from libs.effects.effect import Effect  # pylint: disable=E0611, E0401

from scipy.ndimage.filters import gaussian_filter1d
import numpy as np


class EffectWavelength(Effect):
    def run(self):
        effect_config = self._device.device_config["effects"]["effect_wavelength"]
        led_count = self._device.device_config["LED_Count"]
        led_mid = self._device.device_config["LED_Mid"]

        audio_data = self.get_audio_data()
        y = self.get_mel(audio_data)

        if y is None:
            return

        # Interpolate y to get a array, which is as half long as the led strip
        y = np.copy(self._math_service.interpolate(y, led_count // 2))
        self._dsp.common_mode.update(y)

        # Color channel mappings.
        r = self._dsp.r_filt.update(y - self._dsp.common_mode.value)

        # Expand the array to the twice sice and mirror the values
        # [0,1,2,3]
        # --> [0,1,2,3,3,2,1,0]
        r = np.array([j for i in zip(r, r) for j in i])

        # If the r array is smaller than the led_count, the r array will b filled with the lats value.
        r_len_before_resize = len(r)
        missing_values = led_count - r_len_before_resize
        r = np.pad(r, (0,missing_values), 'edge')
               
        start_gradient_index = (led_count if effect_config["reverse_grad"] else 0)
        end_gradient_index = (None if effect_config["reverse_grad"] else led_count)

        self.output = np.array(
            [
                self._color_service.full_gradients[effect_config["color_mode"]][0][start_gradient_index:end_gradient_index:] * r,
                self._color_service.full_gradients[effect_config["color_mode"]][1][start_gradient_index:end_gradient_index:] * r,
                self._color_service.full_gradients[effect_config["color_mode"]][2][start_gradient_index:end_gradient_index:] * r
            ]
        )

        # Calculate how many steps the array will roll.
        steps = self.get_roll_steps(effect_config["roll_speed"])

        self._color_service.full_gradients[effect_config["color_mode"]] = np.roll(
            self._color_service.full_gradients[effect_config["color_mode"]],
            steps * (-1 if effect_config["reverse_roll"] else 1),
            axis=1
        )
        blur_amount = effect_config["blur"]
        if blur_amount > 0:
            self.output[0] = gaussian_filter1d(self.output[0], sigma=blur_amount)
            self.output[1] = gaussian_filter1d(self.output[1], sigma=blur_amount)
            self.output[2] = gaussian_filter1d(self.output[2], sigma=blur_amount)

        if effect_config["flip_lr"]:
            self.output = np.fliplr(self.output)

        if effect_config["mirror"]:
            # Calculate the real mid.
            real_mid = led_count / 2
            # Add some tolerance for the real mid.
            if (real_mid >= led_mid - 2) and (real_mid <= led_mid + 2):
                # Use the option with shrinking the array.
                self.output = np.concatenate((self.output[:, ::-2], self.output[:, ::2]), axis=1)
            else:
                # Mirror the whole array. After this the array has a two times bigger size than led_count.
                big_mirrored_array = np.concatenate((self.output[:, ::-1], self.output[:, ::1]), axis=1)
                start_of_array = led_count - led_mid
                end_of_array = start_of_array + led_count
                self.output = big_mirrored_array[:, start_of_array:end_of_array]

        self.queue_output_array_noneblocking(self.output)
