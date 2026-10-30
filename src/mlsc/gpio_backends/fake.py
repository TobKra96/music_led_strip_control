import numpy as np

from mlsc.diagnosis import Diagnosis
from mlsc.gpio_backends import GpioBackend, GpioBackendError, GpioStrip
from mlsc.host import Host


class FakeGpioBackend(GpioBackend):
    """Records the frames instead of driving a strip, so tests never import the real driver."""

    name = "fake"
    valid_pins = frozenset(range(2, 28))

    def __init__(self, init_error: GpioBackendError | None = None) -> None:
        self.init_error = init_error
        self.strip: GpioStrip | None = None
        self.frames: list[np.ndarray] = []
        self.closed = False

    def init(self, strip: GpioStrip) -> None:
        if self.init_error:
            raise self.init_error
        self.strip = strip
        self.closed = False

    def show(self, frame: np.ndarray) -> None:
        self.frames.append(np.array(frame, copy=True))

    def close(self) -> None:
        self.closed = True

    @classmethod
    def diagnose(cls, device_config: dict, host: Host) -> Diagnosis:  # ruff: ignore[unused-method-argument]
        return Diagnosis.ok("Fake GPIO Backend: no hardware is driven.")
