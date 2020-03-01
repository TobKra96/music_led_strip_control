from libs.effects.effect import Effect # pylint: disable=E0611, E0401

import numpy as np

class EffectBeat(Effect):
    def run(self):
        effect_config = self._device.device_config["effects"]["effect_beat"]
        led_count = self._device.device_config["LED_Count"]

        audio_data = self.get_audio_data()
        y = self.get_mel(audio_data)

        if y is None:
            return

        self.update_freq_channels(y)
        self.detect_freqs()

        """Effect that flashes to the beat"""
        if self.current_freq_detects["beat"]:
            output = np.zeros((3,led_count))
            output[0][:]=self._color_service.colour(effect_config["color"])[0]
            output[1][:]=self._color_service.colour(effect_config["color"])[1]
            output[2][:]=self._color_service.colour(effect_config["color"])[2]
        else:
            output = np.copy(self.prev_output)
            output = np.multiply(self.prev_output,effect_config["decay"])
       
        self._output_queue_lock.acquire()
        if self._output_queue.full():
            prev_output_array = self._output_queue.get()
            del prev_output_array
        self._output_queue.put(output)
        self._output_queue_lock.release()

        self.prev_output = output