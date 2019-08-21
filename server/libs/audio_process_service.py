from libs.color_service import ColorService # pylint: disable=E0611, E0401
from libs.config_service import ConfigService # pylint: disable=E0611, E0401
from libs.dsp import DSP # pylint: disable=E0611, E0401

import numpy as np
import pyaudio
import sys
import time
from time import sleep

class AudioProcessService:
       
    def start(self, config_lock, notification_queue_in, notification_queue_out, audio_queue, audio_queue_lock ):

        self._config_lock = config_lock
        self._notification_queue_in = notification_queue_in
        self._notification_queue_out = notification_queue_out
        self._audio_queue = audio_queue
        self._audio_queue_lock = audio_queue_lock

        # Initial config load.
        self._config = ConfigService.instance(self._config_lock).config

        #Init FPS Limiter
        self.fps_limiter_start = time.time()
        self.max_fps = 120
        self.min_waiting_time = 1 / self.max_fps

        # Init pyaudio
        self._py_audio = pyaudio.PyAudio()

        self._numdevices = self._py_audio.get_device_count()
        self._default_device_id = self._py_audio.get_default_input_device_info()['index']
        self._devices = []

        print("Found the following audio sources:")

        #for each audio device, add to list of devices
        for i in range(0,self._numdevices):
            try:
                device_info = self._py_audio.get_device_info_by_host_api_device_index(0,i)

                if device_info["maxInputChannels"] >= 1:
                    self._devices.append(device_info)
                    print(str(device_info["index"]) + " - " + str(device_info["name"])  + " - " + str(device_info["defaultSampleRate"]))
            except Exception as e:
                print("Could not get device infos.")
                print("Unexpected error in AudioProcessService :" + str(e))
            
        # to test the audio, use 0
        selected_device_list_index = 2
        
        for device in self._devices:
            if device["index"] == selected_device_list_index:
                print("Use " + str(device["index"]) + " - " + str(device["name"])  + " - " + str(device["defaultSampleRate"]))
                self._device_id = device["index"]
                self._device_name = device["name"]
                self._device_rate = int(device["defaultSampleRate"])
                self._config["audio_config"]["DEFAULT_SAMPLE_RATE"] = self._device_rate
                self._frames_per_buffer = self._config["audio_config"]["FRAMES_PER_BUFFER"]

        
        self.start_time = time.time()
        self.ten_seconds_counter = time.time()

        self._dsp = DSP(config_lock)

        print("Start open Audio stream")
        self.stream = self._py_audio.open(format = pyaudio.paInt16,
                                    channels = 1,
                                    rate = self._device_rate,
                                    input = True,
                                    input_device_index = self._device_id,
                                    frames_per_buffer = self._frames_per_buffer)

        while True:
            self.audio_service_routine()
                
    def audio_service_routine(self):
        try:
            # Limit the fps to decrease laggs caused by 100 percent cpu
            self.fps_limiter()

            raw_data_from_stream = self.stream.read(self._frames_per_buffer, exception_on_overflow = False)

            # Convert the raw string audio stream to an array.
            y = np.fromstring(raw_data_from_stream, dtype=np.int16)
            # Use the type float32
            y = y.astype(np.float32)

            # Process the audio stream
            audio_datas = self._dsp.update(y)

            # Send the new audio data to the effect process.
            
            if self._audio_queue.full():
                pre_audio_data = self._audio_queue.get()
            self._audio_queue.put(audio_datas["mel"])

            self.end_time = time.time()
                    
            if time.time() - self.ten_seconds_counter > 10:
                self.ten_seconds_counter = time.time()
                self.time_dif = self.end_time - self.start_time
                self.fps = 1 / self.time_dif
                print("Audio Service | FPS: " + str(self.fps))

            self.start_time = time.time()
            

        except IOError:
            print("IOError during reading the Microphone Stream.")
            pass


    def fps_limiter(self):

        self.fps_limiter_end = time.time()
        time_between_last_cycle = self.fps_limiter_end - self.fps_limiter_start
        if time_between_last_cycle < self.min_waiting_time:
            sleep(self.min_waiting_time - time_between_last_cycle)

        self.fps_limiter_start = time.time() 

       
           

       
        