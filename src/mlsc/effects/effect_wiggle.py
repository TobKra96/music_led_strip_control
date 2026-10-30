import numpy as np

from mlsc.effects.effect import Effect


class EffectWiggle(Effect):
    needs_audio = True

    def __init__(self, config, device_config, color_service_global=None) -> None:

        # Call the constructor of the base class.
        super().__init__(config, device_config, color_service_global)

        # Setup for "Wiggle" (don't change this).
        self.bool_lr = 0

    def run(self, audio_data):
        effect_config = self.get_effect_config("effect_wiggle")
        led_count = self._device_config["led_count"]

        y = self.get_mel(audio_data)

        if y is None:
            return None

        self.update_freq_channels(y)
        self.detect_freqs()

        self.current_color = self._color_service.colour(effect_config["color"])

        # Build an empty array.
        output = np.zeros((3, led_count))

        max_bar_count = led_count // effect_config["bar_length"]

        if self.current_freq_detects["beat"]:
            output = np.zeros((3, led_count))
            output[0][:] = self._color_service.colour(effect_config["beat_color"])[0]
            output[1][:] = self._color_service.colour(effect_config["beat_color"])[1]
            output[2][:] = self._color_service.colour(effect_config["beat_color"])[2]
        elif self.current_freq_detects["low"] or self.current_freq_detects["mid"] or self.current_freq_detects["high"]:
            if self.bool_lr == 0:
                for bar_count in range(max_bar_count):
                    if (bar_count % 2) == 0:
                        output[0, bar_count * effect_config["bar_length"]: (bar_count * effect_config["bar_length"] + effect_config["bar_length"])] = self.current_color[0]
                        output[1, bar_count * effect_config["bar_length"]: (bar_count * effect_config["bar_length"] + effect_config["bar_length"])] = self.current_color[1]
                        output[2, bar_count * effect_config["bar_length"]: (bar_count * effect_config["bar_length"] + effect_config["bar_length"])] = self.current_color[2]
                self.bool_lr = 1
            else:
                for bar_count in range(max_bar_count):
                    if (bar_count % 2) == 1:
                        output[0, bar_count * effect_config["bar_length"]: (bar_count * effect_config["bar_length"] + effect_config["bar_length"])] = self.current_color[0]
                        output[1, bar_count * effect_config["bar_length"]: (bar_count * effect_config["bar_length"] + effect_config["bar_length"])] = self.current_color[1]
                        output[2, bar_count * effect_config["bar_length"]: (bar_count * effect_config["bar_length"] + effect_config["bar_length"])] = self.current_color[2]
                self.bool_lr = 0
        else:
            output = np.copy(self.prev_output)
            output = np.multiply(self.prev_output, effect_config["decay"])

        self.prev_output = output
        return output
