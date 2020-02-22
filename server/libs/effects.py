from libs.config_service import ConfigService # pylint: disable=E0611, E0401
from libs.effects_enum import EffectsEnum # pylint: disable=E0611, E0401
from libs.notification_enum import NotificationEnum # pylint: disable=E0611, E0401
from libs.color_service import ColorService # pylint: disable=E0611, E0401
from libs.math_service import MathService # pylint: disable=E0611, E0401
from libs.dsp import DSP # pylint: disable=E0611, E0401

from scipy.ndimage.filters import gaussian_filter1d
import numpy as np
import gc as gc
from time import sleep
import time
import cProfile
import random
from collections import deque
import time
from itertools import cycle

# Output array should look like:
# output = {[r1,r2,r3,r4,r5],[g1,g2,g3,g4,g5],[]}

class Effects():

    def start(self, config_lock, notification_queue_in, notification_queue_out, output_queue, output_queue_lock, effects_queue, server_queue, server_queue_lock, audio_queue, audio_queue_lock ):
        """
        Start the effect process. You can change the effect by add a new effect enum inside the enum_queue.
        """

        print("Start Effects component...")

        self._config_lock = config_lock
        self._notification_queue_in = notification_queue_in
        self._notification_queue_out = notification_queue_out
        self._output_queue = output_queue
        self._output_queue_lock = output_queue_lock
        self._effects_queue = effects_queue
        self._server_queue = server_queue
        self._server_queue_lock = server_queue_lock
        self._audio_queue = audio_queue
        self._audio_queue_lock = audio_queue_lock

        self._lost_arrays_counter = 0
        self.ten_seconds_counter = time.time()
        self.start_time = time.time()

        # Initial config load.
        self._config = ConfigService.instance(self._config_lock).config
        self._config_colours = self._config["colours"]
        self._config_gradients = self._config["gradients"]

        # Initials color service and build gradients
        self._color_service = ColorService(self._config)
        self._color_service.build_gradients()
        self._color_service.build_fadegradients()
        self._color_service.build_slidearrays()
        self._color_service.build_slidearrays()
        self._color_service.build_bubblearrays()

        #Init FPS Limiter
        self.fps_limiter_start = time.time()
        self.max_fps = self._config["audio_config"]["FPS"] + 10
        self.min_waiting_time = 1 / self.max_fps

        # Init math service 
        self._math_service = MathService()

        # Init dsp
        self._dsp = DSP(self._config_lock)

        #Init some variables for the effects
        led_count = self._config["device_config"]["LED_Count"]
        n_fft_bins = self._config["audio_config"]["N_FFT_BINS"]

        self.prev_spectrum = np.array([led_count // 2])
        self.freq_channel_history = 40
        self.beat_count = 0
        self.freq_channels = [deque(maxlen=self.freq_channel_history) for i in range(n_fft_bins)]

        self.output = np.array([[0 for i in range(led_count)] for i in range(3)])
        self.prev_output = np.array([[0 for i in range(led_count)] for i in range(3)])

        self.speed_counter = 0

        # Twinkle Variables
        self.rising_stars = []
        self.descending_stars = []
        self.output_decay = np.array([[0 for i in range(led_count)] for i in range(3)])

        # Pendulum Variables
        self.current_direction = True
        self.current_position = 0
        self.current_color = [0,0,0]
        self.current_color_index = 0

        # Rods Variables
        self.count_since_last_rod = 0

        # Scroll Variables
        self.output_scroll_high = np.array([[0 for i in range(led_count)] for i in range(3)])
        self.output_scroll_mid = np.array([[0 for i in range(led_count)] for i in range(3)])
        self.output_scroll_low = np.array([[0 for i in range(led_count)] for i in range(3)])

        self.current_freq_detects = {"beat":False,
                                     "low":False,
                                     "mid":False,
                                     "high":False}
        self.prev_freq_detects = {"beat":0,
                                  "low":0,
                                  "mid":0,
                                  "high":0}
        self.detection_ranges = {"beat":(0,int(self._config["audio_config"]["N_FFT_BINS"]*0.11)),
                                 "low":(int(self._config["audio_config"]["N_FFT_BINS"]*0.13),
                                        int(self._config["audio_config"]["N_FFT_BINS"]*0.4)),
                                 "mid":(int(self._config["audio_config"]["N_FFT_BINS"]*0.4),
                                        int(self._config["audio_config"]["N_FFT_BINS"]*0.7)),
                                 "high":(int(self._config["audio_config"]["N_FFT_BINS"]*0.8),
                                         int(self._config["audio_config"]["N_FFT_BINS"]))}
        self.min_detect_amplitude = {"beat":0.7,
                                     "low":0.5,
                                     "mid":0.3,
                                     "high":0.3}
        self.min_percent_diff = {"beat":70,
                                 "low":100,
                                 "mid":50,
                                 "high":30}

        # Setup for "Power" (don't change these)
        self.power_indexes = []
        self.power_brightness = 0

        # Setup for "Wave" (don't change these)
        self.wave_wipe_count = 0

        # Setup for "Wiggle" (don't change these)
        self.bool_lr = 0

        # Setup for "VU Meter" (don't change these)
        self.max_vol = 0
        self.vol_history = np.zeros(100)

        try:
            # Get the last effect and set it. 
            last_effect_string = self._config["effects"]["last_effect"]
            last_effect = EffectsEnum[last_effect_string]
            self._current_effect = last_effect

        except Exception:
            print("Could not parse last effect. Set effect to off.")
            self._current_effect = EffectsEnum.effect_off

        
        # A token to cancle the while loop
        self._cancel_token = False
        self._skip_effect = False
        print("Effects component started.")

        while not self._cancel_token:
            try:
                self.effect_routine()
            except Exception as e:
                print("Error in Effect Service. Routine Restarted. Exception: " + str(e))
            
        print("Effects component stopped.")

    def effect_routine(self):
        # Limit the fps to decrease laggs caused by 100 percent cpu
        self.fps_limiter()

        # Check the nofitication queue
        if not self._notification_queue_in.empty():
            self._current_notification_in = self._notification_queue_in.get()

        if hasattr(self, "_current_notification_in"):
            if self._current_notification_in is NotificationEnum.config_refresh:
                self.refresh()
            elif self._current_notification_in is NotificationEnum.process_continue:
                self._skip_effect = False
            elif self._current_notification_in is NotificationEnum.process_pause:
                self._skip_effect = True
            elif self._current_notification_in is NotificationEnum.process_stop:
                self.stop() 

        # Reset the current in notification, to do it only one time.
        self._current_notification_in = None

        #Skip the effect sequence, for example to "pause" the process.
        if self._skip_effect:
            return

        # Check if the effect changed.
        if not self._effects_queue.empty():
            self._current_effect = self._effects_queue.get()
            print("New effect found:", self._current_effect)

        # Something is wrong here, no effect set. So skip until we get a new information.
        if self._current_effect is None:
            print("Effect Service | Could not find effect.")
            return

        if self._current_effect == EffectsEnum.effect_off:
            self.effect_off()
        elif self._current_effect == EffectsEnum.effect_single:
            self.effect_single()
        elif self._current_effect == EffectsEnum.effect_gradient:
            self.effect_gradient()
        elif self._current_effect == EffectsEnum.effect_fade:
            self.effect_fade()
        elif self._current_effect == EffectsEnum.effect_slide:
            self.effect_slide()
        elif self._current_effect == EffectsEnum.effect_bubble:
            self.effect_bubble()
        elif self._current_effect == EffectsEnum.effect_twinkle:
            self.effect_twinkle() 
        elif self._current_effect == EffectsEnum.effect_pendulum:
            self.effect_pendulum()
        elif self._current_effect == EffectsEnum.effect_rods:
            self.effect_rods()
        elif self._current_effect == EffectsEnum.effect_server:
            self.effect_server()
        elif self._current_effect == EffectsEnum.effect_scroll:
            self.effect_scroll()
        elif self._current_effect == EffectsEnum.effect_energy:
            self.effect_energy()
        elif self._current_effect == EffectsEnum.effect_wavelength:
            self.effect_wavelength()
        elif self._current_effect == EffectsEnum.effect_bars:
            self.effect_bars()
        elif self._current_effect == EffectsEnum.effect_power:
            self.effect_power()
        elif self._current_effect == EffectsEnum.effect_beat:
            self.effect_beat()
        elif self._current_effect == EffectsEnum.effect_wave:
            self.effect_wave()
        elif self._current_effect == EffectsEnum.effect_beat_slide:
            self.effect_beat_slide()
        elif self._current_effect == EffectsEnum.effect_wiggle:
            self.effect_wiggle()
        elif self._current_effect == EffectsEnum.effect_vu_meter:
            self.effect_vu_meter()
        elif self._current_effect == EffectsEnum.effect_spectrum_analyzer:
            self.effect_spectrum_analyzer()

        if(self._lost_arrays_counter % 100 == 0 and self._lost_arrays_counter != 0):
            print("Effect Service | Lost Arrays: " + str(self._lost_arrays_counter))

        

        self.end_time = time.time()
                        
        if time.time() - self.ten_seconds_counter > 10:
            self.ten_seconds_counter = time.time()
            self.time_dif = self.end_time - self.start_time
            self.fps = 1 / self.time_dif
            print("Effect Service | FPS: " + str(self.fps))

        self.start_time = time.time()

    def fps_limiter(self):

        self.fps_limiter_end = time.time()
        time_between_last_cycle = self.fps_limiter_end - self.fps_limiter_start
        if time_between_last_cycle < self.min_waiting_time:
            sleep(self.min_waiting_time - time_between_last_cycle)

        self.fps_limiter_start = time.time()

        
    def stop(self):
        
        print("Stopping effect component...")
        self.cancel_token = True

    def refresh(self):
        print("Refresh effects...")
        # Refresh the config
        ConfigService.instance(self._config_lock).load_config()
        self._config = ConfigService.instance(self._config_lock).config

        # Initial config load.
        self._config = ConfigService.instance(self._config_lock).config
        self._config_colours = self._config["colours"]
        self._config_gradients = self._config["gradients"]

        # Initials color service and build gradients
        self._color_service = ColorService(self._config)
        self._color_service.build_gradients()
        self._color_service.build_fadegradients()
        self._color_service.build_slidearrays()
        self._color_service.build_bubblearrays()

         # Init math service 
        self._math_service = MathService()

        # Init dsp
        self._dsp = DSP(self._config_lock)

        #Refresh some variables for the effects
        led_count = self._config["device_config"]["LED_Count"]
        n_fft_bins = self._config["audio_config"]["N_FFT_BINS"]

        self.prev_spectrum = np.array([led_count // 2])
        self.freq_channel_history = 40
        self.beat_count = 0
        self.freq_channels = [deque(maxlen=self.freq_channel_history) for i in range(n_fft_bins)]

        self.output = np.array([[0 for i in range(led_count)] for i in range(3)])
        self.prev_output = np.array([[0 for i in range(led_count)] for i in range(3)])

        # Twinkle Variables
        self.rising_stars = []
        self.descending_stars = []
        self.output_decay = np.array([[0 for i in range(led_count)] for i in range(3)])

        # Pendulum Variables
        self.current_direction = True
        self.current_position = 0
        self.current_color = [0,0,0]
        self.current_color_index = 0

        # Rods Variables
        self.count_since_last_rod = 0

        # Scroll Variables
        self.output_scroll_high = np.array([[0 for i in range(led_count)] for i in range(3)])
        self.output_scroll_mid = np.array([[0 for i in range(led_count)] for i in range(3)])
        self.output_scroll_low = np.array([[0 for i in range(led_count)] for i in range(3)])


        self.current_freq_detects = {"beat":False,
                                     "low":False,
                                     "mid":False,
                                     "high":False}
        self.prev_freq_detects = {"beat":0,
                                  "low":0,
                                  "mid":0,
                                  "high":0}
        self.detection_ranges = {"beat":(0,int(self._config["audio_config"]["N_FFT_BINS"]*0.11)),
                                 "low":(int(self._config["audio_config"]["N_FFT_BINS"]*0.13),
                                        int(self._config["audio_config"]["N_FFT_BINS"]*0.4)),
                                 "mid":(int(self._config["audio_config"]["N_FFT_BINS"]*0.4),
                                        int(self._config["audio_config"]["N_FFT_BINS"]*0.7)),
                                 "high":(int(self._config["audio_config"]["N_FFT_BINS"]*0.8),
                                         int(self._config["audio_config"]["N_FFT_BINS"]))}
        self.min_detect_amplitude = {"beat":0.7,
                                     "low":0.5,
                                     "mid":0.3,
                                     "high":0.3}
        self.min_percent_diff = {"beat":70,
                                 "low":100,
                                 "mid":50,
                                 "high":30}

        # Setup for "Power" (don't change these)
        self.power_indexes = []
        self.power_brightness = 0

        # Setup for "Wave" (don't change these)
        self.wave_wipe_count = 0

        # Setup for "Wiggle" (don't change these)
        self.bool_lr = 0

        # Setup for "VU Meter" (don't change these)
        self.max_vol = 0
        self.vol_history = np.zeros(100)

        # Notifiy the master component, that I'm finished.
        self._notification_queue_out.put(NotificationEnum.config_refresh_finished)
        print("Effects refreshed.")

    def update_freq_channels(self, y):
        for i in range(len(y)):
            self.freq_channels[i].appendleft(y[i])

    def detect_freqs(self):
        """
        Function that updates current_freq_detects. Any visualisation algorithm can check if
        there is currently a beat, low, mid, or high by querying the self.current_freq_detects dict.
        """
        n_fft_bins = self._config["audio_config"]["N_FFT_BINS"]
        channel_avgs = []
        differences = []
        
        for i in range(n_fft_bins):
            channel_avgs.append(sum(self.freq_channels[i])/len(self.freq_channels[i]))
            differences.append(((self.freq_channels[i][0]-channel_avgs[i])*100)//channel_avgs[i])
        for i in ["beat", "low", "mid", "high"]:
            if any(differences[j] >= self.min_percent_diff[i]\
                   and self.freq_channels[j][0] >= self.min_detect_amplitude[i]\
                            for j in range(*self.detection_ranges[i]))\
                        and (time.time() - self.prev_freq_detects[i] > 0.2)\
                        and len(self.freq_channels[0]) == self.freq_channel_history:
                self.prev_freq_detects[i] = time.time()
                self.current_freq_detects[i] = True
            else:
                self.current_freq_detects[i] = False


    def get_roll_steps(self, current_speed):
        """
        Calculate the steps for the rollspeed.
        Up to 1 you can adjust the speed very fine. After this, you need to add decades to increase the speed.
        """
        max_counter = 1
        steps = 0

        self.speed_counter = self.speed_counter + current_speed

        if self.speed_counter > max_counter:
            self.speed_counter = 0

            if (max_counter/current_speed) < 1:

                steps = int(1 / (max_counter/current_speed))
            else:
                steps = 1
        
        else:
            steps = 0

        return steps

    def effect_off(self):
        # Build an empty array
        output_array = np.zeros((3, self._config["device_config"]["LED_Count"]))

        
        self._output_queue.put(output_array)
        

    def effect_single(self):
        """
        Show one single color.
        """
        # Get the config of the current effect
        effect_config = self._config["effects"]["effect_single"]
        # Build an empty array
        output_array = np.zeros((3, self._config["device_config"]["LED_Count"]))
        
        # Fill the array with the selected color
        output_array[0][:]=self._config_colours[effect_config["color"]][0]
        output_array[1][:]=self._config_colours[effect_config["color"]][1]
        output_array[2][:]=self._config_colours[effect_config["color"]][2]

        # Add the output array to the queue
        self._output_queue_lock.acquire()
        self._output_queue.put(output_array)
        self._output_queue_lock.release()

    def effect_gradient(self):
        # Get the config of the current effect
        effect_config = self._config["effects"]["effect_gradient"]

        # Prepare the needed config inside local variables to enhance the looking of the long array functions.
        current_gradient = effect_config["gradient"]
        current_speed = effect_config["speed"]
        current_reverse = effect_config["reverse"]

        led_count = self._config["device_config"]["LED_Count"]
        led_mid = self._config["device_config"]["LED_Mid"]

        # Translate the true and false to a number, for the fuction use.
        current_reverse_translated = 0
        if current_reverse:
            current_reverse_translated = -1
        else:
            current_reverse_translated = 1

        full_gradient_ref = self._color_service.full_gradients
        
        # Build an array with the current selected gradient.
        # Cut the full gradient to the the led count lenght.
        output_array = np.array(
            [   full_gradient_ref[current_gradient][0][:led_count],
                full_gradient_ref[current_gradient][1][:led_count],
                full_gradient_ref[current_gradient][2][:led_count]
            ])
        
        # Calculate how many steps the array will roll
        steps = self.get_roll_steps(current_speed)

        # We got the current output array. Now we prepare the next step. We "roll" the array with the specified speed.
        full_gradient_ref[current_gradient] = np.roll(
            full_gradient_ref[current_gradient],
            steps * current_reverse_translated,
            axis = 1
        )

        if effect_config["mirror"]:
            # calculate the real mid
            real_mid = led_count / 2
            # add some tolerance for the real mid
            if (real_mid >= led_mid - 2) and (real_mid <= led_mid + 2):
                # Use the option with shrinking the array
                output_array = np.concatenate((output_array[:, ::-2], output_array[:, ::2]), axis=1)
            else:
                # Mirror the whole array. After this the array has the double size than led_count
                big_mirrored_array = np.concatenate((output_array[:, ::-1], output_array[:, ::1]), axis=1)
                start_of_array = led_count - led_mid
                end_of_array = start_of_array + led_count
                output_array = big_mirrored_array[:, start_of_array:end_of_array]

        # Add the output array to the queue
        self._output_queue_lock.acquire()
        self._output_queue.put(output_array)
        self._output_queue_lock.release()

    def effect_fade(self):

        # Get the config of the current effect
        effect_config = self._config["effects"]["effect_fade"]

        # Prepare the needed config inside local variables to enhance the looking of the long array functions.
        current_gradient = effect_config["gradient"]
        current_speed = effect_config["speed"]
        current_reverse = effect_config["reverse"]

        led_count = self._config["device_config"]["LED_Count"]

        # Translate the true and false to a number, for the fuction use.
        current_reverse_translated = 0
        if current_reverse:
            current_reverse_translated = -1
        else:
            current_reverse_translated = 1

        full_gradient_ref = self._color_service.full_fadegradients

        # Get the current color we will use for the whole led strip.
        current_color_r = full_gradient_ref[current_gradient][0][0]
        current_color_g = full_gradient_ref[current_gradient][1][0]
        current_color_b = full_gradient_ref[current_gradient][2][0]

        # Fill the whole strip with the color.
        output_array = np.array([
            [current_color_r for i in range(led_count)],
            [current_color_g for i in range(led_count)],
            [current_color_b for i in range(led_count)]
        ])

        # Calculate how many steps the array will roll
        steps = self.get_roll_steps(current_speed)

        # We got the current output array. Now we prepare the next step. We "roll" the array with the specified speed.
        full_gradient_ref[current_gradient] = np.roll(
            full_gradient_ref[current_gradient],
            steps * current_reverse_translated,
            axis = 1
        )

        # Add the output array to the queue
        self._output_queue_lock.acquire()
        self._output_queue.put(output_array)
        self._output_queue_lock.release()

    def effect_slide(self):
        # Get the config of the current effect
        effect_config = self._config["effects"]["effect_slide"]
        led_count = self._config["device_config"]["LED_Count"]
        led_mid = self._config["device_config"]["LED_Mid"]

        # Translate the true and false to a number, for the fuction use.
        current_reverse_translated = 0
        if effect_config["reverse"]:
            current_reverse_translated = -1
        else:
            current_reverse_translated = 1

        full_slide_ref = self._color_service.full_slide

        # Build an array with the current selected gradient.
        # Cut the slide to the the led count lenght.
        output_array = np.array(
            [   full_slide_ref[effect_config["gradient"]][0][:led_count],
                full_slide_ref[effect_config["gradient"]][1][:led_count],
                full_slide_ref[effect_config["gradient"]][2][:led_count]
            ])

        # Calculate how many steps the array will roll
        steps = self.get_roll_steps(effect_config["speed"])

        # We got the current output array. Now we prepare the next step. We "roll" the array with the specified speed.
        full_slide_ref[effect_config["gradient"]] = np.roll(
            full_slide_ref[effect_config["gradient"]],
            steps * current_reverse_translated,
            axis = 1
        )

        if effect_config["mirror"]:
            # calculate the real mid
            real_mid = led_count / 2
            # add some tolerance for the real mid
            if (real_mid >= led_mid - 2) and (real_mid <= led_mid + 2):
                # Use the option with shrinking the array
                output_array = np.concatenate((output_array[:, ::-2], output_array[:, ::2]), axis=1)
            else:
                # Mirror the whole array. After this the array has the double size than led_count
                big_mirrored_array = np.concatenate((output_array[:, ::-1], output_array[:, ::1]), axis=1)
                start_of_array = led_count - led_mid
                end_of_array = start_of_array + led_count
                output_array = big_mirrored_array[:, start_of_array:end_of_array]

        # Add the output array to the queue
        self._output_queue_lock.acquire()
        self._output_queue.put(output_array)
        self._output_queue_lock.release()


    def effect_bubble(self):
        # Get the config of the current effect
        effect_config = self._config["effects"]["effect_bubble"]
        led_count = self._config["device_config"]["LED_Count"]
        led_mid = self._config["device_config"]["LED_Mid"]

        # Translate the true and false to a number, for the fuction use.
        current_reverse_translated = 0
        if effect_config["reverse"]:
            current_reverse_translated = -1
        else:
            current_reverse_translated = 1

        full_bubble_ref = self._color_service.full_bubble

        # Build an array with the current selected gradient.
        # Cut the slide to the the led count lenght.
        output_array = np.array(
            [   full_bubble_ref[effect_config["gradient"]][0][:led_count],
                full_bubble_ref[effect_config["gradient"]][1][:led_count],
                full_bubble_ref[effect_config["gradient"]][2][:led_count]
            ])

        # Calculate how many steps the array will roll
        steps = self.get_roll_steps(effect_config["speed"])

        # We got the current output array. Now we prepare the next step. We "roll" the array with the specified speed.
        full_bubble_ref[effect_config["gradient"]] = np.roll(
            full_bubble_ref[effect_config["gradient"]],
            steps * current_reverse_translated,
            axis = 1
        )

        if effect_config["mirror"]:
            # calculate the real mid
            real_mid = led_count / 2
            # add some tolerance for the real mid
            if (real_mid >= led_mid - 2) and (real_mid <= led_mid + 2):
                # Use the option with shrinking the array
                output_array = np.concatenate((output_array[:, ::-2], output_array[:, ::2]), axis=1)
            else:
                # Mirror the whole array. After this the array has the double size than led_count
                big_mirrored_array = np.concatenate((output_array[:, ::-1], output_array[:, ::1]), axis=1)
                start_of_array = led_count - led_mid
                end_of_array = start_of_array + led_count
                output_array = big_mirrored_array[:, start_of_array:end_of_array]

        # Add the output array to the queue
        self._output_queue_lock.acquire()
        self._output_queue.put(output_array)
        self._output_queue_lock.release()

    def effect_twinkle(self):
        # Get the config of the current effect
        effect_config = self._config["effects"]["effect_twinkle"]
        led_count = self._config["device_config"]["LED_Count"]

        # Rising Star array format: [[r,g,b], [start_position, end_position], percent_brightness]

        # Reset output array
        self.output = np.zeros((3, self._config["device_config"]["LED_Count"]))


        # Random add off the stars, depending on speed settings
        if random.randrange (0, 100, 1) <= effect_config["star_appears_speed"]:
            # add a star only if the list is not full
            if len(self.rising_stars) < effect_config["stars_count"]:
                gradient = self._config["gradients"][effect_config["gradient"]]
                number_of_colors = len(gradient)
                selected_color_index = random.randrange(0, number_of_colors, 1)

                star_start_position = random.randrange(0, led_count, 1)
                star_end_position = star_start_position + effect_config["stars_length"]
                
                # Check if end position still in array
                if star_end_position > led_count - 1:
                    star_end_position = led_count - 1            

                # Add the new rising star with a random color out of the gradient selection.
                self.rising_stars.append([[gradient[selected_color_index][0], gradient[selected_color_index][1], gradient[selected_color_index][2]], [star_start_position, star_end_position], 1])

        remove_stars_rising = []

        # Set the new rising stars value
        for current_star in self.rising_stars:
            current_star[2] = current_star[2] + effect_config["star_rising_speed"]
            # Only allow 100 percent
            if current_star[2] > 100:
                current_star[2] = 100
            
            if current_star[2] == 100:
                self.descending_stars.append(current_star)
                remove_stars_rising.append(current_star)
                # the star will be created in the de
            else:
                self.output[0, current_star[1][0]:current_star[1][1]] = int(current_star[0][0] * (current_star[2]/100))
                self.output[1, current_star[1][0]:current_star[1][1]] = int(current_star[0][1] * (current_star[2]/100))
                self.output[2, current_star[1][0]:current_star[1][1]] = int(current_star[0][2] * (current_star[2]/100))

        # remove the stars from the rising array
        for current_star_to_remove in remove_stars_rising:
            self.rising_stars.remove(current_star_to_remove)

        remove_stars_descending = []

        # Set the new descending stars value
        for current_star in self.descending_stars:
            current_star[2] = current_star[2] - effect_config["star_descending_speed"]
            # Only allow 0 percent
            if current_star[2] < 0:
                current_star[2] = 0
            
            if current_star[2] == 0:
                remove_stars_descending.append(current_star)

            self.output[0, current_star[1][0]:current_star[1][1]] = int(current_star[0][0] * (current_star[2]/100))
            self.output[1, current_star[1][0]:current_star[1][1]] = int(current_star[0][1] * (current_star[2]/100))
            self.output[2, current_star[1][0]:current_star[1][1]] = int(current_star[0][2] * (current_star[2]/100))

        # remove the stars from the descending array
        for current_star_to_remove in remove_stars_descending:
            self.descending_stars.remove(current_star_to_remove)

        self.output = gaussian_filter1d(self.output, sigma=effect_config["blur"])

        # Add the output array to the queue
        self._output_queue_lock.acquire()
        self._output_queue.put(self.output)
        self._output_queue_lock.release()

    def effect_pendulum(self):
        # Get the config of the current effect
        effect_config = self._config["effects"]["effect_pendulum"]
        led_count = self._config["device_config"]["LED_Count"]

        if (self.current_position == 0) or (self.current_position == led_count - 1):
            if effect_config["change_color"]:
                gradient = self._config["gradients"][effect_config["gradient"]]
                count_colors_in_gradient = len(gradient)

                self.current_color_index = self.current_color_index + 1
                if self.current_color_index > count_colors_in_gradient - 1:
                    self.current_color_index = 0
                
                self.current_color = gradient[self.current_color_index]

            else:
                self.current_color = self._color_service.colour(effect_config["color"])

        # Build an empty array
        output_array = np.zeros((3, self._config["device_config"]["LED_Count"]))

        # Calculate how many steps the array will roll
        steps = self.get_roll_steps(effect_config["speed"])

        if self.current_direction:
            # start                                                       end
            # |-----------------------------------------------------------|
            #               ----> Direction

            # Fix the direction swap
            if self.current_position == 0:
                self.current_position = effect_config["pendulum_length"]

            self.current_position = self.current_position + steps

            if self.current_position > led_count - 1:
                self.current_position = led_count - 1
                self.current_direction = False
            
            start_position = self.current_position
            end_position = start_position - effect_config["pendulum_length"]
            if end_position < 0:
                end_position = 0

            output_array[0, end_position:start_position] = self.current_color[0]
            output_array[1, end_position:start_position] = self.current_color[1]
            output_array[2, end_position:start_position] = self.current_color[2]

        else:
            # end                                                       start
            # |-----------------------------------------------------------|
            #               <---- Direction

            # Fix the direction swap
            if self.current_position == led_count - 1:
                self.current_position = (led_count - 1) - effect_config["pendulum_length"]

            self.current_position = self.current_position - steps

            if self.current_position < 0:
                self.current_position = 0
                self.current_direction = True
            
            start_position = self.current_position
            end_position = start_position + effect_config["pendulum_length"]
            if end_position > led_count - 1:
                end_position = led_count - 1

            output_array[0, start_position:end_position] = self.current_color[0]
            output_array[1, start_position:end_position] = self.current_color[1]
            output_array[2, start_position:end_position] = self.current_color[2]


        # Add the output array to the queue
        self._output_queue_lock.acquire()
        self._output_queue.put(output_array)
        self._output_queue_lock.release()

    def effect_rods(self):
        # Get the config of the current effect
        effect_config = self._config["effects"]["effect_rods"]
        led_count = self._config["device_config"]["LED_Count"]
        led_mid = self._config["device_config"]["LED_Mid"]

        self.count_since_last_rod = self.count_since_last_rod + 1

        # Calculate how many steps the array will roll
        steps = self.get_roll_steps(effect_config["speed"])

        # Not reverse
        # start                         end
        # |-------------------------------|
        # Move array ---> this direction for "steps" fields

        # Reverse
        # start                         end
        # |-------------------------------|
        # Move array <--- this direction for "steps" fields

        # Build an empty array
        local_output_array = np.zeros((3, self._config["device_config"]["LED_Count"]))

        if not effect_config["reverse"]:
            self.output = np.roll(self.output,steps,axis = 1)
            self.output[:, :steps] = np.zeros((3, steps))
        else:
            self.output = np.roll(self.output,steps * -1,axis = 1)
            self.output[:, led_count - steps:] = np.zeros((3, steps))

        if (self.count_since_last_rod - effect_config["rods_length"]) > effect_config["rods_distance"]:
            self.count_since_last_rod = 0
            
            # FInd the next color
            if effect_config["change_color"]:
                gradient = self._config["gradients"][effect_config["gradient"]]
                count_colors_in_gradient = len(gradient)

                self.current_color_index = self.current_color_index + 1
                if self.current_color_index > count_colors_in_gradient - 1:
                    self.current_color_index = 0
                
                self.current_color = gradient[self.current_color_index]

            else:
                self.current_color = self._color_service.colour(effect_config["color"])

        if self.count_since_last_rod <= effect_config["rods_length"]:
            if not effect_config["reverse"]:
                self.output[0, :steps] = self.current_color[0]
                self.output[1, :steps] = self.current_color[1]
                self.output[2, :steps] = self.current_color[2]
            else:
                self.output[0, led_count - steps:] = self.current_color[0]
                self.output[1, led_count - steps:] = self.current_color[1]
                self.output[2, led_count - steps:] = self.current_color[2]

        local_output_array = self.output

        if effect_config["mirror"]:
            # calculate the real mid
            real_mid = led_count / 2
            # add some tolerance for the real mid
            if (real_mid >= led_mid - 2) and (real_mid <= led_mid + 2):
                # Use the option with shrinking the array
                local_output_array = np.concatenate((self.output[:, ::-2], self.output[:, ::2]), axis=1)
            else:
                # Mirror the whole array. After this the array has the double size than led_count
                big_mirrored_array = np.concatenate((self.output[:, ::-1], self.output[:, ::1]), axis=1)
                start_of_array = led_count - led_mid
                end_of_array = start_of_array + led_count
                local_output_array = big_mirrored_array[:, start_of_array:end_of_array]

        # Add the output array to the queue
        self._output_queue_lock.acquire()
        self._output_queue.put(local_output_array)
        self._output_queue_lock.release()


    def effect_server(self):
        """
        Show Music stream of the server
        """
        output_array = None
        self._server_queue_lock.acquire()
        if not self._server_queue.empty():
            output_array = self._server_queue.get()
        self._server_queue_lock.release()

        # Output is empty
        if(output_array is None):
            return

        # Add the output array to the queue
        self._output_queue_lock.acquire()
        if self._output_queue.full():
            old_output_array = self._output_queue.get()
            del old_output_array
            self._lost_arrays_counter = self._lost_arrays_counter + 1 
        self._output_queue.put(output_array)
        self._output_queue_lock.release()

    def effect_scroll(self):
        effect_config = self._config["effects"]["effect_scroll"]
        led_count = self._config["device_config"]["LED_Count"]
        led_mid = self._config["device_config"]["LED_Mid"]

        y = None
        
        self._audio_queue_lock.acquire()
        if not self._audio_queue.empty():
            y = self._audio_queue.get()            
        self._audio_queue_lock.release()

        # Audio Data is empty
        if(y is None):
            return

        y = y["mel"]

        # mel is empty
        if(y is None):
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
   
    def effect_energy(self):
        effect_config = self._config["effects"]["effect_energy"]
        led_count = self._config["device_config"]["LED_Count"]
        led_mid = self._config["device_config"]["LED_Mid"]

    
        y = None
        
        self._audio_queue_lock.acquire()
        if not self._audio_queue.empty():
            y = self._audio_queue.get()            
        self._audio_queue_lock.release()

        # Audio Data is empty
        if(y is None):
            return

        y = y["mel"]

        # mel is empty
        if(y is None):
            return

        y = np.copy(y)
        self._dsp.gain.update(y)
        y /= self._dsp.gain.value
        scale = effect_config["scale"]
        # Scale by the width of the LED strip
        y *= float((led_count * scale) - 1)
        y = np.copy(self._math_service.interpolate(y, led_count // 2))
        # Map color channels according to energy in the different freq bands
        self.prev_spectrum = np.copy(y)
        spectrum = np.copy(self.prev_spectrum)
        spectrum = np.array([j for i in zip(spectrum,spectrum) for j in i])
        # Color channel mappings
        r = int(np.mean(spectrum[:len(spectrum) // 3]**scale)*effect_config["r_multiplier"])
        g = int(np.mean(spectrum[len(spectrum) // 3: 2 * len(spectrum) // 3]**scale)*effect_config["g_multiplier"])
        b = int(np.mean(spectrum[2 * len(spectrum) // 3:]**scale)*effect_config["b_multiplier"])
        # Assign color to different frequency regions
        self.output[0, :r] = 255
        self.output[0, r:] = 0
        self.output[1, :g] = 255
        self.output[1, g:] = 0
        self.output[2, :b] = 255
        self.output[2, b:] = 0
        # Apply blur to smooth the edges
        self.output[0, :] = gaussian_filter1d(self.output[0, :], sigma=effect_config["blur"])
        self.output[1, :] = gaussian_filter1d(self.output[1, :], sigma=effect_config["blur"])
        self.output[2, :] = gaussian_filter1d(self.output[2, :], sigma=effect_config["blur"])
        
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

    def effect_wavelength(self):
        effect_config = self._config["effects"]["effect_wavelength"]
        led_count = self._config["device_config"]["LED_Count"]
        led_mid = self._config["device_config"]["LED_Mid"]

        y = None
        
        self._audio_queue_lock.acquire()
        if not self._audio_queue.empty():
            y = self._audio_queue.get()
        self._audio_queue_lock.release()

        # Audio Data is empty
        if(y is None):
            return

        y = y["mel"]

        # mel is empty
        if(y is None):
            return

        y = np.copy(self._math_service.interpolate(y, led_count // 2))
        self._dsp.common_mode.update(y)
        diff = y - self.prev_spectrum
        self.prev_spectrum = np.copy(y)
        # Color channel mappings
        r = self._dsp.r_filt.update(y - self._dsp.common_mode.value)
        g = np.abs(diff)
        b = self._dsp.b_filt.update(np.copy(y))
        r = np.array([j for i in zip(r,r) for j in i])
        output = np.array([self._color_service.full_gradients[effect_config["color_mode"]][0][
                                    (led_count if effect_config["reverse_grad"] else 0):
                                    (None if effect_config["reverse_grad"] else led_count):]*r,
                           self._color_service.full_gradients[effect_config["color_mode"]][1][
                                    (led_count if effect_config["reverse_grad"] else 0):
                                    (None if effect_config["reverse_grad"] else led_count):]*r,
                           self._color_service.full_gradients[effect_config["color_mode"]][2][
                                    (led_count if effect_config["reverse_grad"] else 0):
                                    (None if effect_config["reverse_grad"] else led_count):]*r])
        
        # Calculate how many steps the array will roll
        steps = self.get_roll_steps(effect_config["roll_speed"])

        self._color_service.full_gradients[effect_config["color_mode"]] = np.roll(
                    self._color_service.full_gradients[effect_config["color_mode"]],
                    steps*(-1 if effect_config["reverse_roll"] else 1),
                    axis=1)
        output[0] = gaussian_filter1d(output[0], sigma=effect_config["blur"])
        output[1] = gaussian_filter1d(output[1], sigma=effect_config["blur"])
        output[2] = gaussian_filter1d(output[2], sigma=effect_config["blur"])
        if effect_config["flip_lr"]:
            output = np.fliplr(output)
        
        
        if effect_config["mirror"]:
            # calculate the real mid
            real_mid = led_count / 2
            # add some tolerance for the real mid
            if (real_mid >= led_mid - 2) and (real_mid <= led_mid + 2):
                # Use the option with shrinking the array
                output = np.concatenate((output[:, ::-2], output[:, ::2]), axis=1)
            else:
                # Mirror the whole array. After this the array has the double size than led_count
                big_mirrored_array = np.concatenate((output[:, ::-1], output[:, ::1]), axis=1)
                start_of_array = led_count - led_mid
                end_of_array = start_of_array + led_count
                output = big_mirrored_array[:, start_of_array:end_of_array]

        self._output_queue_lock.acquire()
        if self._output_queue.full():
            prev_output_array = self._output_queue.get()
            del prev_output_array
        self._output_queue.put(output)
        self._output_queue_lock.release()

    def effect_bars(self):
        effect_config = self._config["effects"]["effect_bars"]
        led_count = self._config["device_config"]["LED_Count"]
        led_mid = self._config["device_config"]["LED_Mid"]

        y = None
        
        self._audio_queue_lock.acquire()
        if not self._audio_queue.empty():
            y = self._audio_queue.get()
        self._audio_queue_lock.release()

        # Audio Data is empty
        if(y is None):
            return

        y = y["mel"]

        # mel is empty
        if(y is None):
            return

         # Bit of fiddling with the y values
        y = np.copy(self._math_service.interpolate(y, led_count // 2))
        self._dsp.common_mode.update(y)
        self.prev_spectrum = np.copy(y)
        # Color channel mappings
        r = self._dsp.r_filt.update(y - self._dsp.common_mode.value)
        r = np.array([j for i in zip(r,r) for j in i])
        # Split y into [resulution] chunks and calculate the average of each
        max_values = np.array([max(i) for i in np.array_split(r, effect_config["resolution"])])
        max_values = np.clip(max_values, 0, 1)
        color_sets = []
        for i in range(effect_config["resolution"]):
            # [r,g,b] values from a multicolour gradient array at [resulution] equally spaced intervals
            color_sets.append([self._color_service.full_gradients[effect_config["color_mode"]]\
                              [j][i*(led_count//effect_config["resolution"])] for j in range(3)])
        output = np.zeros((3,led_count))
        chunks = np.array_split(output[0], effect_config["resolution"])
        n = 0
        # Assign blocks with heights corresponding to max_values and colours from color_sets
        for i in range(len(chunks)):
            m = len(chunks[i])
            for j in range(3):
                output[j][n:n+m] = color_sets[i][j]*max_values[i]
            n += m

        # Calculate how many steps the array will roll
        steps = self.get_roll_steps(effect_config["roll_speed"])
        
        self._color_service.full_gradients[effect_config["color_mode"]] = np.roll(
                    self._color_service.full_gradients[effect_config["color_mode"]],
                    steps*(-1 if effect_config["reverse_roll"] else 1),
                    axis=1)
        if effect_config["flip_lr"]:
            output = np.fliplr(output)

        if effect_config["mirror"]:
            # calculate the real mid
            real_mid = led_count / 2
            # add some tolerance for the real mid
            if (real_mid >= led_mid - 2) and (real_mid <= led_mid + 2):
                # Use the option with shrinking the array
                output = np.concatenate((output[:, ::-2], output[:, ::2]), axis=1)
            else:
                # Mirror the whole array. After this the array has the double size than led_count
                big_mirrored_array = np.concatenate((output[:, ::-1], output[:, ::1]), axis=1)
                start_of_array = led_count - led_mid
                end_of_array = start_of_array + led_count
                output = big_mirrored_array[:, start_of_array:end_of_array]
       
        self._output_queue_lock.acquire()
        if self._output_queue.full():
            prev_output_array = self._output_queue.get()
            del prev_output_array
        self._output_queue.put(output)
        self._output_queue_lock.release()

    def effect_power(self):
        effect_config = self._config["effects"]["effect_power"]
        
        led_count = self._config["device_config"]["LED_Count"]
        n_fft_bins = self._config["audio_config"]["N_FFT_BINS"]
        led_mid = self._config["device_config"]["LED_Mid"]

        y = None
        
        self._audio_queue_lock.acquire()
        if not self._audio_queue.empty():
            y = self._audio_queue.get()
        self._audio_queue_lock.release()

        # Audio Data is empty
        if(y is None):
            return

        y = y["mel"]

        # mel is empty
        if(y is None):
            return

        self.update_freq_channels(y)
        self.detect_freqs()

        # Bit of fiddling with the y values
        y = np.copy(self._math_service.interpolate(y, led_count // 2))
        self._dsp.common_mode.update(y)
        self.prev_spectrum = np.copy(y)
        # Color channel mappings
        r = self._dsp.r_filt.update(y - self._dsp.common_mode.value)
        r = np.array([j for i in zip(r,r) for j in i])
        output = np.array([self._color_service.full_gradients[effect_config["color_mode"]][0, :led_count]*r,
                           self._color_service.full_gradients[effect_config["color_mode"]][1, :led_count]*r,
                           self._color_service.full_gradients[effect_config["color_mode"]][2, :led_count]*r])
        # if there's a high (eg clap):
        if self.current_freq_detects["high"]:
            self.power_brightness = 1.0
            # Generate random indexes
            self.power_indexes = random.sample(range(led_count), effect_config["s_count"])
        # Assign colour to the random indexes
        for index in self.power_indexes:
            output[0, index] = int(self._color_service.colour(effect_config["s_color"])[0]*self.power_brightness)
            output[1, index] = int(self._color_service.colour(effect_config["s_color"])[1]*self.power_brightness)
            output[2, index] = int(self._color_service.colour(effect_config["s_color"])[2]*self.power_brightness)
        # Remove some of the indexes for next time
        self.power_indexes = [i for i in self.power_indexes if i not in random.sample(self.power_indexes, len(self.power_indexes)//4)]
        if len(self.power_indexes) <= 4:
            self.power_indexes = []
        # Fade the colour of the sparks out a bit for next time
        if self.power_brightness > 0:
            self.power_brightness -= 0.05
        # Calculate length of bass bar based on max bass frequency volume and length of strip
        strip_len = int((led_count//3)*max(y[:int(n_fft_bins*0.2)]))
        # Add the bass bars into the output. Colour proportional to length
        output[0][:strip_len] = self._color_service.full_gradients[effect_config["color_mode"]][0][strip_len]
        output[1][:strip_len] = self._color_service.full_gradients[effect_config["color_mode"]][1][strip_len]
        output[2][:strip_len] = self._color_service.full_gradients[effect_config["color_mode"]][2][strip_len]
        if effect_config["flip_lr"]:
            output = np.fliplr(output)
        
        if effect_config["mirror"]:
            # calculate the real mid
            real_mid = led_count / 2
            # add some tolerance for the real mid
            if (real_mid >= led_mid - 2) and (real_mid <= led_mid + 2):
                # Use the option with shrinking the array
                output = np.concatenate((output[:, ::-2], output[:, ::2]), axis=1)
            else:
                # Mirror the whole array. After this the array has the double size than led_count
                big_mirrored_array = np.concatenate((output[:, ::-1], output[:, ::1]), axis=1)
                start_of_array = led_count - led_mid
                end_of_array = start_of_array + led_count
                output = big_mirrored_array[:, start_of_array:end_of_array]
       
        self._output_queue_lock.acquire()
        if self._output_queue.full():
            prev_output_array = self._output_queue.get()
            del prev_output_array
        self._output_queue.put(output)
        self._output_queue_lock.release()


    def effect_beat(self):
        effect_config = self._config["effects"]["effect_beat"]
        led_count = self._config["device_config"]["LED_Count"]

        y = None
        
        self._audio_queue_lock.acquire()
        if not self._audio_queue.empty():
            y = self._audio_queue.get()            
        self._audio_queue_lock.release()

        # Audio Data is empty
        if(y is None):
            return

        y = y["mel"]

        # mel is empty
        if(y is None):
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

    def effect_wave(self):
        effect_config = self._config["effects"]["effect_wave"]
        led_count = self._config["device_config"]["LED_Count"]

        y = None
        
        self._audio_queue_lock.acquire()
        if not self._audio_queue.empty():
            y = self._audio_queue.get()
        self._audio_queue_lock.release()

        # Audio Data is empty
        if(y is None):
            return

        y = y["mel"]

        # mel is empty
        if(y is None):
            return

        self.update_freq_channels(y)
        self.detect_freqs()

        """Effect that flashes to the beat with scrolling coloured bits"""
        if self.current_freq_detects["beat"]:
            output = np.zeros((3,led_count))
            output[0][:]=self._color_service.colour(effect_config["color_flash"])[0]
            output[1][:]=self._color_service.colour(effect_config["color_flash"])[1]
            output[2][:]=self._color_service.colour(effect_config["color_flash"])[2]
            self.wave_wipe_count = effect_config["wipe_len"]
        else:
            output = np.copy(self.prev_output)
            #for i in range(len(self.prev_output)):
            #    output[i] = np.hsplit(self.prev_output[i],2)[0]
            output = np.multiply(self.prev_output,effect_config["decay"])
            for i in range(self.wave_wipe_count):
                output[0][i]=self._color_service.colour(effect_config["color_wave"])[0]
                output[0][-i]=self._color_service.colour(effect_config["color_wave"])[0]
                output[1][i]=self._color_service.colour(effect_config["color_wave"])[1]
                output[1][-i]=self._color_service.colour(effect_config["color_wave"])[1]
                output[2][i]=self._color_service.colour(effect_config["color_wave"])[2]
                output[2][-i]=self._color_service.colour(effect_config["color_wave"])[2]
            #output = np.concatenate([output,np.fliplr(output)], axis=1)
            if self.wave_wipe_count > led_count//2:
                self.wave_wipe_count = led_count//2
            
            # Calculate how many steps the array will roll
            steps = self.get_roll_steps(effect_config["wipe_speed"])
            
            self.wave_wipe_count += steps

        self._output_queue_lock.acquire()
        if self._output_queue.full():
            prev_output_array = self._output_queue.get()
            del prev_output_array
        self._output_queue.put(output)
        self._output_queue_lock.release()

        self.prev_output = output

#Eigene Effekte
    def effect_beat_slide(self):
        effect_config = self._config["effects"]["effect_beat_slide"]
        led_count = self._config["device_config"]["LED_Count"]

        y = None
        
        self._audio_queue_lock.acquire()
        if not self._audio_queue.empty():
            y = self._audio_queue.get()
        self._audio_queue_lock.release()

        # Audio Data is empty
        if(y is None):
            return

        y = y["mel"]

        # mel is empty
        if(y is None):
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

        
    def effect_wiggle(self):
        effect_config = self._config["effects"]["effect_wiggle"]
        led_count = self._config["device_config"]["LED_Count"]

        y = None
        
        self._audio_queue_lock.acquire()
        if not self._audio_queue.empty():
            y = self._audio_queue.get()
        self._audio_queue_lock.release()

        # Audio Data is empty
        if(y is None):
            return

        y = y["mel"]

        # mel is empty
        if(y is None):
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

    def effect_vu_meter(self):
        effect_config = self._config["effects"]["effect_vu_meter"]
        led_count = self._config["device_config"]["LED_Count"]

        y = None
        vol = None
        
        self._audio_queue_lock.acquire()
        if not self._audio_queue.empty():
            y = self._audio_queue.get()            
        self._audio_queue_lock.release()

        # Audio Data is empty
        if(y is None):
            return

        vol = y["vol"]

        # vol is empty       
        if(vol is None):
            return

        #roll the history for one.
        self.vol_history = np.roll(self.vol_history,1,axis = 0)
        #add the new value
        self.vol_history[0] = vol
        
        normalized_vol = (vol-np.min(self.vol_history)) / (np.max(self.vol_history)-np.min(self.vol_history))
        

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
        
    def effect_spectrum_analyzer(self):
        effect_config = self._config["effects"]["effect_spectrum_analyzer"]
        led_count = self._config["device_config"]["LED_Count"]

        y = None
        
        self._audio_queue_lock.acquire()
        if not self._audio_queue.empty():
            y = self._audio_queue.get()           
        self._audio_queue_lock.release()

        # Audio Data is empty
        if(y is None):
            return

        y = y["mel"]

        # mel is empty
        if(y is None):
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