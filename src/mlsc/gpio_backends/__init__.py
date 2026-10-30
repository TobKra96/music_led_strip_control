"""GPIO Backend: the library or driver a local GPIO Output uses to push pixel frames to the strip on a given Pi model."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from mlsc.diagnosis import Diagnosis
from mlsc.host import Host

if TYPE_CHECKING:
    from collections.abc import Mapping

    import numpy as np


class GpioBackendError(RuntimeError):
    """A GPIO Backend cannot be used. Carries the fix, so the caller can show it as a Diagnosis."""

    def __init__(self, message: str, suggested_fix: str | None = None) -> None:
        super().__init__(message)
        self.suggested_fix = suggested_fix

    def to_diagnosis(self) -> Diagnosis:
        return Diagnosis.error(str(self), self.suggested_fix)


@dataclass(frozen=True)
class GpioStrip:
    """What every GPIO Backend needs to know about the strip, plus the settings only the chosen backend understands."""

    chip_family: str
    colour_order: str
    white_channel: bool
    led_count: int
    pin: int
    brightness: int = 100  # 0-100
    advanced: Mapping[str, int | bool] = field(default_factory=dict)


class GpioBackend(ABC):
    name: str
    valid_pins: frozenset[int]

    @abstractmethod
    def init(self, strip: GpioStrip) -> None:
        """Claim the pin and prepare the strip. Raises GpioBackendError when that is not possible."""

    @abstractmethod
    def show(self, frame: np.ndarray) -> None:
        """Display `frame`: rows of red, green, blue (and white on a white channel strip), one column per pixel, values 0-255."""

    @abstractmethod
    def close(self) -> None:
        """Release the pin."""

    @classmethod
    @abstractmethod
    def diagnose(cls, device_config: dict, host: Host) -> Diagnosis:
        """Check that this backend can drive the strip described by the output `device_config`, without initialising it."""


def select_backend(host: Host | None = None) -> type[GpioBackend]:
    """The backend for this Pi model: `rpi_ws281x` on a Pi 3, Pi 4 and Zero 2 W (and on any host that is not a Pi 5)."""
    model = (host or Host()).pi_model()
    if model and "Pi 5" in model:
        raise GpioBackendError(
            "No Pi 5 driver installed: the Pi 5 is experimental and MLSC ships no GPIO Backend for it.",
            "Use a Pi 4 or older, send the frames to a UDP client, or see the docs for the Pi 5 driver options.",
        )
    from mlsc.gpio_backends.ws281x_backend import Ws281xBackend  # ruff: ignore[import-outside-top-level]

    return Ws281xBackend
