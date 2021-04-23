from libs.effects.effect import Effect  # pylint: disable=E0611, E0401

import numpy as np


class EffectOff(Effect):
    def run(self):
        # Build an empty array.
        output_array = np.zeros((3, self._device.device_config["led_count"]))

        self._output_queue.put(output_array)
