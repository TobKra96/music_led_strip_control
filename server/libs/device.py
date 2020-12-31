from multiprocessing import Process, Queue, Manager, Lock

from libs.effect_service import EffectService
from libs.output_service import OutputService

class Device:

    def __init__(self, config, device_config):
        self.__config = config
        self.__device_config = device_config
        
        self.__device_notification_queue_in = Queue(2)
        self.__device_notification_queue_in_lock = Lock()

        self.__device_notification_queue_out = Queue(2)
        self.__device_notification_queue_out_lock = Lock()

        self.__effect_queue = Queue(2)
        self.__effect_queue_lock = Lock()

        self.__audio_queue = Queue(2)
        self.__audio_queue_lock = Lock()

        self.__output_queue = Queue(2)
        self.__output_queue_lock = Lock()

        self.create_processes()

    def start_device(self):
        print("Start device: " + self.__device_config["DEVICE_NAME"])
        self.__output_process.start()
        self.__effect_process.start()

    def stop_device(self):
        print("Stop device: " + self.__device_config["DEVICE_NAME"])
        self.__effect_process.terminate()
        self.__output_process.terminate()

    def create_processes(self):
        self.__output_service = OutputService()
        self.__output_process = Process(
            target=self.__output_service.start, 
            args=(self,))

        self.__effect_service = EffectService()
        self.__effect_process = Process(
            target=self.__effect_service.start, 
            args=(self,))

    def refresh_config(self, config, device_config):
        print("Refresh config of device: " + self.__device_config["DEVICE_NAME"])

        self.stop_device()

        self.__config = config
        self.__device_config = device_config

        self.create_processes()

        self.__output_service = OutputService()
        self.__output_process = Process(
            target=self.__output_service.start, 
            args=(self,))

        self.__effect_service = EffectService()
        self.__effect_process = Process(
            target=self.__effect_service.start, 
            args=(self,))

        self.start_device()

        
    def get_config(self):
        return self.__config

    def get_device_config(self):
        return self.__device_config

    def get_device_notification_queue_in(self):
        return self.__device_notification_queue_in

    def get_device_notification_queue_in_lock(self):
        return self.__device_notification_queue_in_lock

    def get_device_notification_queue_out(self):
        return self.__device_notification_queue_out

    def get_device_notification_queue_out_lock(self):
        return self.__device_notification_queue_out_lock
    
    def get_effect_queue(self):
        return self.__effect_queue

    def get_effect_queue_lock(self):
        return self.__effect_queue_lock

    def get_audio_queue(self):
        return self.__audio_queue

    def get_audio_queue_lock(self):
        return self.__audio_queue_lock

    def get_output_queue(self):
        return self.__output_queue

    def get_output_queue_lock(self):
        return self.__output_queue_lock

    config = property(get_config)
    device_config = property(get_device_config)

    device_notification_queue_in = property(get_device_notification_queue_in)
    device_notification_queue_in_lock = property(get_device_notification_queue_in_lock)

    device_notification_queue_out = property(get_device_notification_queue_out)
    device_notification_queue_out_lock = property(get_device_notification_queue_out_lock)

    effect_queue = property(get_effect_queue)
    effect_queue_lock = property(get_effect_queue_lock)

    audio_queue = property(get_audio_queue)
    audio_queue_lock = property(get_audio_queue_lock)

    output_queue = property(get_output_queue)
    output_queue_lock = property(get_output_queue_lock)

