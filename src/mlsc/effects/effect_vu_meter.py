import numpy as np

from mlsc.effects.effect import Effect


class EffectVuMeter(Effect):
    needs_audio = True

    def __init__(self, config, device_config, color_service_global=None) -> None:

        # Call the constructor of the base class.
        super().__init__(config, device_config, color_service_global)

        # Setup for "VU Meter" (don't change these).
        self.max_vol = 0
        self.vol_history = np.zeros(300)

    def run(self, audio_data):
        """Effect that lights up more leds when volume gets higher."""
        effect_config = self.get_effect_config("effect_vu_meter")
        led_count = self._device_config["led_count"]

        vol = self.get_vol(audio_data)

        if vol is None or not np.isfinite(vol):
            return None

        self.set_vol_history(vol)
        normalized_vol = self.get_normalized_vol(vol)

        # Build an empty array.
        output = np.zeros((3, led_count))

        use_gradient = effect_config["use_gradient"]
        current_gradient = effect_config["gradient"]

        leds_on = int(normalized_vol * led_count)

        if use_gradient:
            full_gradient_ref = self._color_service.full_gradients

            output[0][: leds_on] = full_gradient_ref[current_gradient][0][:leds_on]
            output[1][: leds_on] = full_gradient_ref[current_gradient][1][:leds_on]
            output[2][: leds_on] = full_gradient_ref[current_gradient][2][:leds_on]
        else:

            output[0][: leds_on] = self._color_service.colour(effect_config["color"])[0]
            output[1][: leds_on] = self._color_service.colour(effect_config["color"])[1]
            output[2][: leds_on] = self._color_service.colour(effect_config["color"])[2]

        self.max_vol = max(normalized_vol, self.max_vol)

        # Show the max. volume
        max_vol_end = int(np.clip(self.max_vol * led_count, 0, led_count))
        max_vol_start = max(max_vol_end - effect_config["bar_length"], 0)
        output[0][max_vol_start: max_vol_end] = self._color_service.colour(effect_config["max_vol_color"])[0]
        output[1][max_vol_start: max_vol_end] = self._color_service.colour(effect_config["max_vol_color"])[1]
        output[2][max_vol_start: max_vol_end] = self._color_service.colour(effect_config["max_vol_color"])[2]

        self.max_vol -= effect_config["speed"] / 10000

        self.prev_output = output

        return output

    def set_vol_history(self, current_vol):
        # Roll the history for one.
        self.vol_history = np.roll(self.vol_history, 1, axis=0)
        # Add the new value.
        self.vol_history[0] = current_vol

    def get_normalized_vol(self, current_vol):
        vol_range = np.max(self.vol_history) - np.min(self.vol_history)
        if vol_range == 0:
            return 0.0

        return float(np.clip((current_vol - np.min(self.vol_history)) / vol_range, 0, 1))
