# This class will represent the output.
# It get its output information from a queue, to be non blocking.
#
#

import numpy as np
from numpy import asarray
from libs.config_service import ConfigService # pylint: disable=E0611, E0401
from libs.notification_enum import NotificationEnum # pylint: disable=E0611, E0401
from ctypes import c_uint8

import time
from time import sleep
import cProfile
import pprint
import array

class Output:

    def manual_init(self):
        import _rpi_ws281x as ws # pylint: disable=import-error

        device_config = self._config["device_config"] 
        # LED strip configuration:
        self._led_count       = int(device_config["LED_Count"])      # Number of LED pixels.
        self._led_pin         = int(device_config["LED_Pin"])        # GPIO pin connected to the pixels (18 uses PWM!).
        self._led_freq_hz     = int(device_config["LED_Freq_Hz"])    # LED signal frequency in hertz (usually 800khz)
        self._led_dma         = int(device_config["LED_Dma"])        # DMA channel to use for generating signal (try 10)
        self._led_brightness  = int(device_config["LED_Brightness"]) # Set to 0 for darkest and 100 for brightest
        self._led_invert      = int(device_config["LED_Invert"])     # True to invert the signal (when using NPN transistor level shift)
        self._led_channel     = int(device_config["LED_Channel"])    # set to '1' for GPIOs 13, 19, 41, 45 or 53

        
        self._led_brightness_translated = int(255 * (self._led_brightness / 100))
        #self._led_brightness_translated = 255

        print("LED Brightness: " + str(self._led_brightness))
        print("LED Brightness Translated: " + str(self._led_brightness_translated))

        self._leds = ws.new_ws2811_t()

        self.channel = ws.ws2811_channel_get(self._leds, 0)

        ws.ws2811_channel_t_count_set(self.channel, self._led_count)
        ws.ws2811_channel_t_gpionum_set(self.channel, self._led_pin)
        ws.ws2811_channel_t_invert_set(self.channel, self._led_invert)
        ws.ws2811_channel_t_brightness_set(self.channel, self._led_brightness_translated)
       
        ws.ws2811_t_freq_set(self._leds, self._led_freq_hz)
        ws.ws2811_t_dmanum_set(self._leds, self._led_dma)

        # Initialize library with LED configuration.
        resp = ws.ws2811_init(self._leds)
        if resp != ws.WS2811_SUCCESS:
	        message = ws.ws2811_get_return_t_str(resp)
	        raise RuntimeError('ws2811_init failed with code {0} ({1})'.format(resp, message))


    def start(self, config_lock, notification_queue_in, notification_queue_out, output_queue, output_queue_lock):
        print("Starting Output component..")
        self._config_lock = config_lock
        self._output_queue = output_queue
        self._output_queue_lock = output_queue_lock
        self._notification_queue_in = notification_queue_in
        self._notification_queue_out = notification_queue_out
        
        self.ten_seconds_counter = time.time()
        self.sec_ten_seconds_counter = time.time()
        self.start_time = time.time()

        # Initial config load.
        self._config = ConfigService.instance(self._config_lock).config
        
        #Init FPS Limiter
        self.fps_limiter_start = time.time()
        self.max_fps = 120
        self.min_waiting_time = 1 / self.max_fps

        # Init all nessessarry components
        self.manual_init()

        self._skip_output = False
        self._cancel_token = False
        print("Output component started.")
        while not self._cancel_token:
            self.output_routine()
           

    def output_routine(self):
        # Limit the fps to decrease laggs caused by 100 percent cpu
        self.fps_limiter()

        # Check the nofitication queue
        if not self._notification_queue_in.empty():
            self._current_notification_in = self._notification_queue_in.get()

        if hasattr(self, "_current_notification_in"):
            if self._current_notification_in is NotificationEnum.config_refresh:
                self.refresh()
            elif self._current_notification_in is NotificationEnum.process_continue:
                self._skip_output = False
            elif self._current_notification_in is NotificationEnum.process_pause:
                self._skip_output = True
            elif self._current_notification_in is NotificationEnum.process_stop:
                self.stop() 

        # Reset the current in notification, to do it only one time.
        self._current_notification_in = None

        # Skip the output sequence, for example to "pause" the process.
        if self._skip_output:
            if not self._output_queue.empty():
                skip_output_queue = self._output_queue.get()
            return

        # Check if the queue is empty and stop if its empty.
        if not self._output_queue.empty():
            current_output_array = self._output_queue.get()
            self.show(current_output_array)
            #cProfile.runctx('self.show(current_output_array)', globals(), locals())


        self.end_time = time.time()
                    
        if time.time() - self.ten_seconds_counter > 10:
            self.ten_seconds_counter = time.time()
            self.time_dif = self.end_time - self.start_time
            self.fps = 1 / self.time_dif
            print("Output Service | FPS: " + str(self.fps))

        self.start_time = time.time()

    def stop(self):
        self._cancel_token = True
        self.clear()

    def refresh(self):
        print("Refresh Output...")

        # Refresh the config
        ConfigService.instance(self._config_lock).load_config()
        self._config = ConfigService.instance(self._config_lock).config

        # Init the led components with the new config again
        self.manual_init()

        # Notifiy the master component, that I'm finished.
        self._notification_queue_out.put(NotificationEnum.config_refresh_finished)

        print("Output refreshed.")

    def show(self, output_array):
        

        import _rpi_ws281x as ws # pylint: disable=import-error

        # Typecast the array to int
        output_array = output_array.clip(0, 255).astype(int)

        # sort the colors. grb
        g = np.left_shift(output_array[1][:].astype(int), 16) # pylint: disable=assignment-from-no-return
        r = np.left_shift(output_array[0][:].astype(int), 8) # pylint: disable=assignment-from-no-return    
        b = output_array[2][:].astype(int)
        rgb = np.bitwise_or(np.bitwise_or(r, g), b).astype(int)

        # You can only use ws2811_leds_set with the custom version.
        #ws.ws2811_leds_set(self.channel, rgb)
        for i in range(self._led_count):
            ws.ws2811_led_set(self.channel, i, rgb[i].item())


        resp = ws.ws2811_render(self._leds)

        if resp != ws.WS2811_SUCCESS:
            message = ws.ws2811_get_return_t_str(resp)
            raise RuntimeError('ws2811_render failed with code {0} ({1})'.format(resp, message))
        

    def clear(self):
        # Create a Array with only 0
        pixels = np.array([[0 for i in range(900)] for i in range(3)]).astype(int)
        self.show(pixels)

    def fps_limiter(self):

        self.fps_limiter_end = time.time()
        time_between_last_cycle = self.fps_limiter_end - self.fps_limiter_start
        if time_between_last_cycle < self.min_waiting_time:
            sleep(self.min_waiting_time - time_between_last_cycle)

        self.fps_limiter_start = time.time() 
       
    def start_dummy(self, config_lock, notification_queue_in, notification_queue_out, output_queue, output_queue_lock):
        print("Starting Output component..")
        self._config_lock = config_lock
        self._output_queue = output_queue
        self._output_queue_lock = output_queue_lock
        self._notification_queue_in = notification_queue_in
        self._notification_queue_out = notification_queue_out

        self._skip_output = False
        self._cancel_token = False
        print("Output component started.")
        while not self._cancel_token:
            sleep(0.2)
            # Check the nofitication queue
            if not self._notification_queue_in.empty():
                self._current_notification_in = self._notification_queue_in.get()

            if hasattr(self, "_current_notification_in"):
                if self._current_notification_in is NotificationEnum.config_refresh:
                    self.refresh_dummy()
                elif self._current_notification_in is NotificationEnum.process_continue:
                    self._skip_output = False
                elif self._current_notification_in is NotificationEnum.process_pause:
                    self._skip_output = True
                elif self._current_notification_in is NotificationEnum.process_stop:
                    print("dummy stop")
                    break

            # Reset the current in notification, to do it only one time.
            self._current_notification_in = None

            # Skip the output sequence, for example to "pause" the process.
            if self._skip_output:
                self._output_queue_lock.acquire()
                if not self._output_queue.empty():
                    self._output_queue.get()
                self._output_queue_lock.release()
                continue

            # Check if the queue is empty and stop if its empty.
            self._output_queue_lock.acquire()
            if not self._output_queue.empty():
                self._output_queue.get()
            self._output_queue_lock.release()


    def refresh_dummy(self):
        print("Refresh Output...")

        # Refresh the config
        ConfigService.instance(self._config_lock).load_config()
        self._config = ConfigService.instance(self._config_lock).config

        # Notifiy the master component, that I'm finished.
        self._notification_queue_out.put(NotificationEnum.config_refresh_finished)

        print("Output refreshed.")