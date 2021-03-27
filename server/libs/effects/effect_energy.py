from libs.effects.effect import Effect  # pylint: disable=E0611, E0401

from scipy.ndimage.filters import gaussian_filter1d
import numpy as np


class EffectEnergy(Effect):
    def run(self):
        effect_config = self.get_effect_config("effect_energy")
        led_count = self._device.device_config["LED_Count"]
        led_mid = self._device.device_config["LED_Mid"]

        audio_data = self.get_audio_data()
        y = self.get_mel(audio_data)

        if y is None:
            return

        y = np.copy(y)
        self._dsp.gain.update(y)
        y /= self._dsp.gain.value
        scale = effect_config["scale"]
        # Scale by the width of the LED strip.
        y *= float((led_count * scale) - 1)
        y = np.copy(self._math_service.interpolate(y, led_count // 2))
        # Map color channels according to energy in the different freq bands.
        self.prev_spectrum = np.copy(y)
        spectrum = np.copy(self.prev_spectrum)
        spectrum = np.array([j for i in zip(spectrum, spectrum) for j in i])
        # Color channel mappings.
        r = int(np.mean(spectrum[:len(spectrum) // 3]**scale) * effect_config["r_multiplier"])
        g = int(np.mean(spectrum[len(spectrum) // 3: 2 * len(spectrum) // 3]**scale) * effect_config["g_multiplier"])
        b = int(np.mean(spectrum[2 * len(spectrum) // 3:]**scale) * effect_config["b_multiplier"])
        # Assign color to different frequency regions.
        self.output[0, :r] = 255
        self.output[0, r:] = 0
        self.output[1, :g] = 255
        self.output[1, g:] = 0
        self.output[2, :b] = 255
        self.output[2, b:] = 0
        # Apply blur to smooth the edges.
        blur_amount = effect_config["blur"]
        if blur_amount > 0:
            self.output[0, :] = gaussian_filter1d(self.output[0, :], sigma=blur_amount)
            self.output[1, :] = gaussian_filter1d(self.output[1, :], sigma=blur_amount)
            self.output[2, :] = gaussian_filter1d(self.output[2, :], sigma=blur_amount)

        if effect_config["mirror"]:
            # Calculate the real mid.
            real_mid = led_count / 2
            # Add some tolerance for the real mid.
            if (real_mid >= led_mid - 2) and (real_mid <= led_mid + 2):
                # Use the option with shrinking the array.
                output_array = np.concatenate((self.output[:, ::-2], self.output[:, ::2]), axis=1)
            else:
                # Mirror the whole array. After this the array has a two times bigger size than led_count.
                big_mirrored_array = np.concatenate((self.output[:, ::-1], self.output[:, ::1]), axis=1)
                start_of_array = led_count - led_mid
                end_of_array = start_of_array + led_count
                output_array = big_mirrored_array[:, start_of_array:end_of_array]
        else:
            output_array = self.output

        self.queue_output_array_noneblocking(output_array)
