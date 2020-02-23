from libs.effects.effect import Effect # pylint: disable=E0611, E0401

import numpy as np

class EffectSpectrumAnalyzer(Effect):
    def run(self):
        effect_config = self._config["effects"]["effect_spectrum_analyzer"]
        led_count = self._config["device_config"]["LED_Count"]

        audio_data = self.get_audio_data()
        y = self.get_mel(audio_data)

        if y is None:
            return
        
        self.update_freq_channels(y)
        #self.detect_freqs()


        #self.current_color = self._color_service.colour(effect_config["color"])

        # Build an empty array
        output = np.zeros((3,led_count))

        y = np.clip(y, 0, 1)

        for i in range(effect_config["spectrum_count"]):
            spec_array = y[(len(y)*i) // effect_config["spectrum_count"] : (len(y)*(i+1)) // effect_config["spectrum_count"]]
            pegel_max = float(np.max(spec_array))

            output[0][i*(led_count//effect_config["spectrum_count"]) : i*(led_count//effect_config["spectrum_count"]) + int(pegel_max*(led_count/effect_config["spectrum_count"]))]=self._color_service.colour(effect_config["color"])[0]
            output[1][i*(led_count//effect_config["spectrum_count"]) : i*(led_count//effect_config["spectrum_count"]) + int(pegel_max*(led_count/effect_config["spectrum_count"]))]=self._color_service.colour(effect_config["color"])[1]
            output[2][i*(led_count//effect_config["spectrum_count"]) : i*(led_count//effect_config["spectrum_count"]) + int(pegel_max*(led_count/effect_config["spectrum_count"]))]=self._color_service.colour(effect_config["color"])[2]

       
        self._output_queue_lock.acquire()
        if self._output_queue.full():
            prev_output_array = self._output_queue.get()
            del prev_output_array
        self._output_queue.put(output)
        self._output_queue_lock.release()

        self.prev_output = output