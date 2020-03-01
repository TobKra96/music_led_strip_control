from libs.device import Device # pylint: disable=E0611, E0401
from libs.config_service import ConfigService # pylint: disable=E0611, E0401
import copy


class DeviceManager:
    def start(self, config_lock, notification_queue_in, notification_queue_out, audio_queue, audio_queue_lock):
        
        self.__config_lock = config_lock
        self.__config = ConfigService.instance(self.__config_lock).config

        self.__notification_queue_in = notification_queue_in
        self.__notification_queue_out = notification_queue_out
        self.__audio_queue = audio_queue
        self.__audio_queue_lock = audio_queue_lock
        
        self.__devices = {}
        self.init_devices()
        self.start_devices()

        while True:
            self.routine()

    def routine(self):
        audio_data = self.get_audio_data()
        self.refresh_audio_queues(audio_data)

    def get_audio_data(self):
        audio_data = None
        self.__audio_queue_lock.acquire()
        if not self.__audio_queue.empty():
            audio_data = self.__audio_queue.get()
        self.__audio_queue_lock.release()
        return audio_data
        
    def refresh_audio_queues(self, audio_data):
        if audio_data is None:
            return

        for current_device in self.__devices:    
            current_device.audio_queue_lock.acquire()  
            if current_device.audio_queue.full():
                pre_audio_data = current_device.audio_queue.get()
            current_device.audio_queue.put(copy.deepcopy(audio_data))
            current_device.audio_queue_lock.release()

    def init_devices(self):
        for current_device in self.__config["device_configs"]:
            self.__devices[current_device["DEVICE_ID"]] = Device(self.__config, current_device)

    def start_devices(self):
        for current_device in self.__devices:
            current_device.start()

  
    

    