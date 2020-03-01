from libs.effects.effect import Effect # pylint: disable=E0611, E0401

import numpy as np

class EffectWiggle(Effect):
    def __init__(self, config, config_lock, output_queue, output_queue_lock, audio_queue, audio_queue_lock):

        # Call the constructor of the base class.
        super(EffectWiggle, self).__init__(config, config_lock, output_queue, output_queue_lock, audio_queue, audio_queue_lock)

        # Setup for "Wiggle" (don't change these)
        self.bool_lr = 0


    def run(self):
        effect_config = self._device.device_config["effects"]["effect_wiggle"]
        led_count = self._device.device_config["LED_Count"]

        audio_data = self.get_audio_data()
        y = self.get_mel(audio_data)

        if y is None:
            return

        self.update_freq_channels(y)
        self.detect_freqs()


        self.current_color = self._color_service.colour(effect_config["color"])

        # Build an empty array
        output = np.zeros((3,led_count))

        max_bar_count = led_count//effect_config["bar_length"]

        #myIterator = cycle(range(2))

        
        """Effect that flashes to the beat"""
        if self.current_freq_detects["beat"]:
            output = np.zeros((3,led_count))
            output[0][:]=self._color_service.colour(effect_config["beat_color"])[0]
            output[1][:]=self._color_service.colour(effect_config["beat_color"])[1]
            output[2][:]=self._color_service.colour(effect_config["beat_color"])[2]
        elif self.current_freq_detects["low"] or self.current_freq_detects["mid"] or self.current_freq_detects["high"]:
            if self.bool_lr == 0:
                for bar_count in range (max_bar_count):
                    if (bar_count % 2) == 0:
                        output[0, bar_count*effect_config["bar_length"] : (bar_count*effect_config["bar_length"] + effect_config["bar_length"])] = self.current_color[0]
                        output[1, bar_count*effect_config["bar_length"] : (bar_count*effect_config["bar_length"] + effect_config["bar_length"])] = self.current_color[1]
                        output[2, bar_count*effect_config["bar_length"] : (bar_count*effect_config["bar_length"] + effect_config["bar_length"])] = self.current_color[2]
                self.bool_lr = 1
            else:
                for bar_count in range (max_bar_count):
                    if (bar_count % 2) == 1:
                        output[0, bar_count*effect_config["bar_length"] : (bar_count*effect_config["bar_length"] + effect_config["bar_length"])] = self.current_color[0]
                        output[1, bar_count*effect_config["bar_length"] : (bar_count*effect_config["bar_length"] + effect_config["bar_length"])] = self.current_color[1]
                        output[2, bar_count*effect_config["bar_length"] : (bar_count*effect_config["bar_length"] + effect_config["bar_length"])] = self.current_color[2]
                self.bool_lr = 0
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