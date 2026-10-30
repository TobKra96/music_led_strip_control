import numpy as np

from mlsc.effects.effect import Effect


class EffectBorder(Effect):
    needs_audio = True

    def run(self, audio_data):
        effect_config = self.get_effect_config("effect_border")
        led_count = self._device_config["led_count"]
        led_mid = self._device_config["led_mid"]

        bar_count = effect_config["bar_count"]

        y = self.get_mel(audio_data)

        if y is None:
            return None

        self.update_freq_channels(y)

        # Build an empty array.
        output = np.zeros((3, led_count))

        y = np.clip(y, 0, 1)

        spec_array = y[0: len(y) // 2]
        bass_output = float(np.max(spec_array))

        if effect_config["manually_resize_bars"]:
            bar_count = 4

        for i in range(bar_count):
            if effect_config["manually_resize_bars"]:
                start = effect_config[f"segment_0{i + 1}_start"]
                start = max(start, 0)
                end = start + int(bass_output * (effect_config[f"segment_0{i + 1}_end"] - start))
                end = min(end, led_count)
            else:
                start = i * (led_count // bar_count)
                end = start + int(bass_output * (led_count // bar_count))

            for led in range(3):
                if effect_config["use_gradient"]:
                    gradient = self._color_service.full_gradients[effect_config["gradient"]][led][start: end]
                    output[led][start: end] = np.vstack([gradient])
                else:
                    output[led][start: end] = self._color_service.colour(effect_config["color"])[led]

        # Calculate how many steps the array will roll.
        steps = self.get_roll_steps(effect_config["roll_speed"])

        self._color_service.full_gradients[effect_config["gradient"]] = np.roll(
            self._color_service.full_gradients[effect_config["gradient"]],
            steps * (-1 if effect_config["reverse_roll"] else 1),
            axis=1
        )

        if effect_config["mirror"]:
            output = self.mirror_array(output, led_mid, led_count)

        self.prev_output = output

        return output
