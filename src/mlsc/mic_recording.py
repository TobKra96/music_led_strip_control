"""Short clip of the audio capture, shared between the audio process and the webserver process. Kept in RAM only."""
import io
import multiprocessing
import wave

import numpy as np

# Length of the microphone test, and so of the clip.
TEST_SECONDS = 2.0
MAX_SAMPLE_RATE = 192_000
# A shorter clip is too short to judge by ear.
MIN_SECONDS = 0.5


class MicRecording:
    """The samples the capture delivered while the microphone test ran, as a mono int16 clip at the rate of the stream.

    The audio process calls `write` from its capture callback, the webserver process arms and disarms it and reads `wav`.
    The object is created before the processes start and passed to both as an argument.
    """

    def __init__(self, seconds: float = TEST_SECONDS) -> None:
        self._seconds = seconds
        self._capacity = int(seconds * MAX_SAMPLE_RATE)
        self._armed = multiprocessing.RawValue("b", 0)
        self._rate = multiprocessing.RawValue("i", 0)
        self._frames_written = multiprocessing.RawValue("l", 0)
        self._samples = multiprocessing.RawArray("h", self._capacity)

    def arm(self) -> None:
        """Drop the old clip and start keeping what the capture delivers."""
        self.clear()
        self._armed.value = 1

    def disarm(self) -> None:
        self._armed.value = 0

    def clear(self) -> None:
        self._frames_written.value = 0

    def write(self, buffer: bytes, rate: int) -> None:
        """Append a buffer of mono int16 samples captured at `rate`. A different rate than before starts the clip over."""
        if not self._armed.value:
            return
        if rate != self._rate.value:
            self._frames_written.value = 0
            self._rate.value = rate
        samples = np.frombuffer(buffer, dtype=np.int16)
        start = self._frames_written.value
        limit = min(self._capacity, int(self._seconds * rate))
        count = min(samples.size, limit - start)
        if count <= 0:
            return
        np.frombuffer(self._samples, dtype=np.int16)[start:start + count] = samples[:count]
        # Last, so a reader never sees frames that are not written yet.
        self._frames_written.value = start + count

    def wav(self) -> bytes | None:
        """Return the clip as a WAV file, or None when there is none or it is too short."""
        rate, frames = self._rate.value, self._frames_written.value
        if rate <= 0 or frames < MIN_SECONDS * rate:
            return None
        out = io.BytesIO()
        with wave.open(out, "wb") as file:
            file.setnchannels(1)
            file.setsampwidth(2)
            file.setframerate(rate)
            file.writeframes(np.frombuffer(self._samples, dtype=np.int16)[:frames].tobytes())
        return out.getvalue()
