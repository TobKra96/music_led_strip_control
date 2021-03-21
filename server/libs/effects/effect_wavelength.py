from libs.effects.effect import Effect  # pylint: disable=E0611, E0401

import numpy as np
from scipy.ndimage.filters import gaussian_filter1d


class EffectWavelength(Effect):
    def run(self):
        effect_config = self._device.device_config["effects"]["effect_wavelength"]
        led_count = self._device.device_config["LED_Count"]
        led_mid = self._device.device_config["LED_Mid"]

        audio_data = self.get_audio_data()
        y = self.get_mel(audio_data)

        if y is None:
            return

        y = np.copy(self._math_service.interpolate(y, led_count // 2))
        self._dsp.common_mode.update(y)
        diff = y - self.prev_spectrum
        self.prev_spectrum = np.copy(y)
        # Color channel mappings.
        r = self._dsp.r_filt.update(y - self._dsp.common_mode.value)
        g = np.abs(diff)
        b = self._dsp.b_filt.update(np.copy(y))
        r = np.array([j for i in zip(r, r) for j in i])
        r_len_before_resize = len(r)
        missing_values = led_count - r_len_before_resize
        r = np.pad(r, (0,missing_values), 'edge')
        output = np.array(
            [
                self._color_service.full_gradients[effect_config["color_mode"]][0]
                [
                    (led_count if effect_config["reverse_grad"] else 0):
                    (None if effect_config["reverse_grad"] else led_count):
                ] * r,
                self._color_service.full_gradients[effect_config["color_mode"]][1]
                [
                    (led_count if effect_config["reverse_grad"] else 0):
                    (None if effect_config["reverse_grad"] else led_count):
                ] * r,
                self._color_service.full_gradients[effect_config["color_mode"]][2]
                [
                    (led_count if effect_config["reverse_grad"] else 0):
                    (None if effect_config["reverse_grad"] else led_count):
                ] * r
            ]
        )

        # Calculate how many steps the array will roll.
        steps = self.get_roll_steps(effect_config["roll_speed"])

        self._color_service.full_gradients[effect_config["color_mode"]] = np.roll(
            self._color_service.full_gradients[effect_config["color_mode"]],
            steps * (-1 if effect_config["reverse_roll"] else 1),
            axis=1
        )
        output[0] = gaussian_filter1d(output[0], sigma=effect_config["blur"])
        output[1] = gaussian_filter1d(output[1], sigma=effect_config["blur"])
        output[2] = gaussian_filter1d(output[2], sigma=effect_config["blur"])
        if effect_config["flip_lr"]:
            output = np.fliplr(output)

        if effect_config["mirror"]:
            # Calculate the real mid.
            real_mid = led_count / 2
            # Add some tolerance for the real mid.
            if (real_mid >= led_mid - 2) and (real_mid <= led_mid + 2):
                # Use the option with shrinking the array.
                output = np.concatenate((output[:, ::-2], output[:, ::2]), axis=1)
            else:
                # Mirror the whole array. After this the array has a two times bigger size than led_count.
                big_mirrored_array = np.concatenate((output[:, ::-1], output[:, ::1]), axis=1)
                start_of_array = led_count - led_mid
                end_of_array = start_of_array + led_count
                output = big_mirrored_array[:, start_of_array:end_of_array]

        self.queue_output_array_noneblocking(output)
