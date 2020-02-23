from libs.effects.effect import Effect # pylint: disable=E0611, E0401

import numpy as np
from scipy.ndimage.filters import gaussian_filter1d

class EffectScroll(Effect):

    def __init__(self, config, config_lock, output_queue, output_queue_lock, audio_queue, audio_queue_lock):

        # Call the constructor of the base class.
        super(EffectScroll, self).__init__(config, config_lock, output_queue, output_queue_lock, audio_queue, audio_queue_lock)

        # Scroll Variables
        self.output_scroll_high = np.array([[0 for i in range(self.led_count)] for i in range(3)])
        self.output_scroll_mid = np.array([[0 for i in range(self.led_count)] for i in range(3)])
        self.output_scroll_low = np.array([[0 for i in range(self.led_count)] for i in range(3)])


    def run(self):
        effect_config = self._config["effects"]["effect_scroll"]
        led_count = self._config["device_config"]["LED_Count"]
        led_mid = self._config["device_config"]["LED_Mid"]

        audio_data = self.get_audio_data()
        y = self.get_mel(audio_data)

        if y is None:
            return

        # Effect that scrolls colours corresponding to frequencies across the strip 
        y = y**4.0
        n_pixels = led_count
        y = np.copy(self._math_service.interpolate(y, (n_pixels // 2)))
        self._dsp.common_mode.update(y)
        self.prev_spectrum = np.copy(y)

        y = np.clip(y, 0, 1)
        lows = y[:len(y) // 6]
        mids = y[len(y) // 6: 2 * len(y) // 5]
        high = y[2 * len(y) // 5:]
        # max values
        lows_max = float(np.max(lows)) * effect_config["lows_multiplier"]
        mids_max = float(np.max(mids)) * effect_config["mids_multiplier"]
        high_max = float(np.max(high)) * effect_config["high_multiplier"]
        # indexes of max values
        # map to colour gradient
        lows_val = (np.array(self._color_service.colour(effect_config["lows_color"])) * lows_max).astype(int)
        mids_val = (np.array(self._color_service.colour(effect_config["mids_color"])) * mids_max).astype(int)
        high_val = (np.array(self._color_service.colour(effect_config["high_color"])) * high_max).astype(int)
        # Scrolling effect window

        # Calculate how many steps the array will roll
        high_steps = effect_config["high_speed"]
        mid_steps = effect_config["mid_speed"]
        low_steps = effect_config["low_speed"]

        if(high_steps > 0):
            self.output_scroll_high[:, high_steps:] = self.output_scroll_high[:, :-high_steps]
        
            # Create new color originating at the center
            self.output_scroll_high[0, :high_steps] = high_val[0]
            self.output_scroll_high[1, :high_steps] = high_val[1]
            self.output_scroll_high[2, :high_steps] = high_val[2]
        
        if(mid_steps > 0):
            self.output_scroll_mid[:, mid_steps:] = self.output_scroll_mid[:, :-mid_steps]

            # Create new color originating at the center
            self.output_scroll_mid[0, :mid_steps] = mids_val[0]
            self.output_scroll_mid[1, :mid_steps] = mids_val[1]
            self.output_scroll_mid[2, :mid_steps] = mids_val[2]

        if(low_steps > 0):
            self.output_scroll_low[:, low_steps:] = self.output_scroll_low[:, :-low_steps]

             # Create new color originating at the center
            self.output_scroll_low[0, :low_steps] = lows_val[0]
            self.output_scroll_low[1, :low_steps] = lows_val[1]
            self.output_scroll_low[2, :low_steps] = lows_val[2]

        self.output[0] = self.output_scroll_high[0] + self.output_scroll_mid[0] + self.output_scroll_low[0]
        self.output[1] = self.output_scroll_high[1] + self.output_scroll_mid[1] + self.output_scroll_low[1]
        self.output[2] = self.output_scroll_high[2] + self.output_scroll_mid[2] + self.output_scroll_low[2]

        self.output = (self.output * effect_config["decay"]).astype(int)
        self.output = gaussian_filter1d(self.output, sigma=effect_config["blur"])

        if effect_config["mirror"]:
            # calculate the real mid
            real_mid = led_count / 2
            # add some tolerance for the real mid
            if (real_mid >= led_mid - 2) and (real_mid <= led_mid + 2):
                # Use the option with shrinking the array
                output_array = np.concatenate((self.output[:, ::-2], self.output[:, ::2]), axis=1)
            else:
                # Mirror the whole array. After this the array has the double size than led_count
                big_mirrored_array = np.concatenate((self.output[:, ::-1], self.output[:, ::1]), axis=1)
                start_of_array = led_count - led_mid
                end_of_array = start_of_array + led_count
                output_array = big_mirrored_array[:, start_of_array:end_of_array]
        else:
            output_array = self.output

        self._output_queue_lock.acquire()
        if self._output_queue.full():
            prev_output_array = self._output_queue.get()
            del prev_output_array
        self._output_queue.put(output_array)
        self._output_queue_lock.release()