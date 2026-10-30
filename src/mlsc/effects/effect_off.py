import numpy as np

from mlsc.effects.effect import Effect


class EffectOff(Effect):
    def run(self):
        # Build an empty array.
        output_array = np.zeros((3, self._device_config["led_count"]))

        return output_array
