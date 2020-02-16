from time import sleep
import time

class FPSLimiter:

    def __init__(self, config):
        self._config = config

        #Init FPS Limiter
        self.fps_limiter_start = time.time()
        self.max_fps = self._config["audio_config"]["FPS"] + 10
        self.min_waiting_time = 1 / self.max_fps

    def fps_limiter(self):

        self.fps_limiter_end = time.time()
        time_between_last_cycle = self.fps_limiter_end - self.fps_limiter_start
        if time_between_last_cycle < self.min_waiting_time:
            sleep(self.min_waiting_time - time_between_last_cycle)

        self.fps_limiter_start = time.time()
    