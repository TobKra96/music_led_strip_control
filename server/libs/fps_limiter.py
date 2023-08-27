from time import sleep, time


class FPSLimiter:

    def __init__(self, fps) -> None:
        self._fps = fps

        # Init FPS Limiter.
        self.fps_limiter_start = time()
        self.max_fps = self._fps
        self.min_waiting_time = 1 / self.max_fps

    def fps_limiter(self):
        self.fps_limiter_end = time()
        time_between_last_cycle = self.fps_limiter_end - self.fps_limiter_start
        if time_between_last_cycle < self.min_waiting_time:
            time_diff = self.min_waiting_time - time_between_last_cycle
            if time_diff > 0.001:
                sleep(time_diff)

        self.fps_limiter_start = time()
