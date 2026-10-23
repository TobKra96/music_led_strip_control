"""Input level of the audio capture, shared between the audio process and the webserver process."""
import multiprocessing

import numpy as np

FULL_SCALE = float(np.iinfo(np.int16).max)


class MicLevel:
    """Peak level of the latest capture buffer, from 0.0 (silence) to 1.0 (full scale).

    The audio process calls `update` from its capture callback, the webserver process calls `read`.
    The object is created before the processes start and passed to both as an argument.
    """

    def __init__(self) -> None:
        self._level = multiprocessing.RawValue("d", 0.0)

    def update(self, buffer: bytes) -> None:
        """Take the peak of a buffer of mono int16 samples."""
        samples = np.frombuffer(buffer, dtype=np.int16)
        peak = float(np.max(np.abs(samples.astype(np.int32)))) if samples.size else 0.0
        self._level.value = min(peak / FULL_SCALE, 1.0)

    def read(self) -> float:
        return self._level.value
