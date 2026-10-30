import numpy as np

from mlsc.effects.effect import Effect


class EffectBeatSlide(Effect):
    needs_audio = True

    def __init__(self, config, device_config, color_service_global=None) -> None:
        # Call the constructor of the base class.
        super().__init__(config, device_config, color_service_global)
        self.current_position = 0

    def run(self, audio_data):
        effect_config = self.get_effect_config("effect_beat_slide")
        led_count = self._device_config["led_count"]

        y = self.get_mel(audio_data)

        if y is None:
            return None

        self.update_freq_channels(y)
        self.detect_freqs()

        self.current_color = self._color_service.colour(effect_config["color"])

        # Build an empty array.
        output = np.zeros((3, led_count))

        # Calculate how many steps the array will roll.
        steps = self.get_roll_steps(effect_config["speed"])

        self.current_position += steps
        if self.current_position > led_count:
            self.current_position = 0

        start_position = self.current_position
        end_position = start_position - effect_config["bar_length"]
        end_position = max(end_position, 0)

        output = (self.prev_output * effect_config["decay"]).astype(int)

        if self.current_freq_detects["beat"]:
            start_position += effect_config["slider_length"]
            start_position = min(led_count, start_position)

            self.current_position = start_position

        output[0][end_position:start_position] = self.current_color[0]
        output[1][end_position:start_position] = self.current_color[1]
        output[2][end_position:start_position] = self.current_color[2]

        self.prev_output = output
        return output
