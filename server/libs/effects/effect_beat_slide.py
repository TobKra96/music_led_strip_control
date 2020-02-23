from libs.effects.effect import Effect # pylint: disable=E0611, E0401

import numpy as np

class EffectBeatSlide(Effect):
    def __init__(self, config, config_lock, output_queue, output_queue_lock, audio_queue, audio_queue_lock):

        # Call the constructor of the base class.
        super(EffectBeatSlide, self).__init__(config, config_lock, output_queue, output_queue_lock, audio_queue, audio_queue_lock)

        self.current_position = 0


    def run(self):
        effect_config = self._config["effects"]["effect_beat_slide"]
        led_count = self._config["device_config"]["LED_Count"]

        audio_data = self.get_audio_data()
        y = self.get_mel(audio_data)
        
        if y is None:
            return

        self.update_freq_channels(y)
        self.detect_freqs()


        self.current_color = self._color_service.colour(effect_config["color"])

        # Build an empty array
        output = np.zeros((3,led_count))

        # Calculate how many steps the array will roll
        steps = self.get_roll_steps(effect_config["speed"])

        
        if self.current_position == 0:
            self.current_position = effect_config["slider_length"]

        self.current_position = self.current_position + steps

        if self.current_position > led_count - 1:
            self.current_position = 0
            #self.current_direction = False
        
        start_position = self.current_position
        end_position = start_position - effect_config["slider_length"]
        if end_position < 0:
            end_position = 0
        """
        output[0, end_position:start_position] = self.current_color[0]
        output[1, end_position:start_position] = self.current_color[1]
        output[2, end_position:start_position] = self.current_color[2]
        """

        """Effect that creates a bar to the beat, where the Slider ends"""
        if self.current_freq_detects["beat"]:
            #output = np.zeros((3,led_count))
            #evtl Zeilenende mit self.current_color[0] ersetzen
            #time.sleep(0.5)
            output[0][self.current_position:(self.current_position+effect_config["bar_length"])]=self._color_service.colour(effect_config["color"])[0]
            output[1][self.current_position:(self.current_position+effect_config["bar_length"])]=self._color_service.colour(effect_config["color"])[1]
            output[2][self.current_position:(self.current_position+effect_config["bar_length"])]=self._color_service.colour(effect_config["color"])[2]
           
            self.current_position = self.current_position+effect_config["bar_length"]
            
        else:
            #output = np.copy(self.prev_output)
            #output = np.multiply(self.prev_output,effect_config["decay"])
            """Creates the Slider"""
            output[0, end_position:start_position] = self.current_color[0]
            output[1, end_position:start_position] = self.current_color[1]
            output[2, end_position:start_position] = self.current_color[2]
       
        self._output_queue_lock.acquire()
        if self._output_queue.full():
            prev_output_array = self._output_queue.get()
            del prev_output_array
        self._output_queue.put(output)
        self._output_queue_lock.release()

        self.prev_output = output