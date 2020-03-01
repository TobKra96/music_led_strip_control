from libs.effects.effect import Effect # pylint: disable=E0611, E0401

import numpy as np

class EffectVuMeter(Effect):
    def __init__(self, config, config_lock, output_queue, output_queue_lock, audio_queue, audio_queue_lock):

        # Call the constructor of the base class.
        super(EffectVuMeter, self).__init__(config, config_lock, output_queue, output_queue_lock, audio_queue, audio_queue_lock)

        # Setup for "VU Meter" (don't change these)
        self.max_vol = 0
        self.vol_history = np.zeros(100)

    def run(self):
        effect_config = self._device.device_config["effects"]["effect_vu_meter"]
        led_count = self._device.device_config["LED_Count"]

        audio_data = self.get_audio_data()
        vol = self.get_vol(audio_data)

        if vol is None:
            return

        self.set_vol_history(vol)
        normalized_vol = self.get_normalized_vol(vol)

        # Build an empty array
        output = np.zeros((3,led_count))

        """Effect that lights up more leds when volume gets higher"""
        output[0][: int(normalized_vol*led_count)]=self._color_service.colour(effect_config["color"])[0]
        output[1][: int(normalized_vol*led_count)]=self._color_service.colour(effect_config["color"])[1]
        output[2][: int(normalized_vol*led_count)]=self._color_service.colour(effect_config["color"])[2]
        
        
        if normalized_vol > self.max_vol:
            self.max_vol = normalized_vol

        """Effect that shows the max. volume"""
        output[0][int(self.max_vol*led_count)-effect_config["bar_length"] : int(self.max_vol*led_count)]=self._color_service.colour(effect_config["max_vol_color"])[0]
        output[1][int(self.max_vol*led_count)-effect_config["bar_length"] : int(self.max_vol*led_count)]=self._color_service.colour(effect_config["max_vol_color"])[1]
        output[2][int(self.max_vol*led_count)-effect_config["bar_length"] : int(self.max_vol*led_count)]=self._color_service.colour(effect_config["max_vol_color"])[2]

        self.max_vol -= effect_config["speed"]/10000

        #print("vol: " + str(y))

        self._output_queue_lock.acquire()
        if self._output_queue.full():
            prev_output_array = self._output_queue.get()
            del prev_output_array
        self._output_queue.put(output)
        self._output_queue_lock.release()

        self.prev_output = output

    def set_vol_history(self, currentVol):
        #roll the history for one.
        self.vol_history = np.roll(self.vol_history,1,axis = 0)
        #add the new value
        self.vol_history[0] = currentVol

    def get_normalized_vol(self, currentVol):
        normalized_vol = (currentVol-np.min(self.vol_history)) / (np.max(self.vol_history)-np.min(self.vol_history))
        return normalized_vol
