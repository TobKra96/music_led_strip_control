import pytest

from mlsc import fps_limiter
from mlsc.fps_limiter import FPSLimiter

pytestmark = pytest.mark.unit


def test_fake_clock_sleep_advances_time_without_waiting(fake_clock):
    fake_clock.sleep(45)

    assert fake_clock.time() == pytest.approx(1_045.0)
    assert fake_clock.sleeps == [45]


def test_fake_clock_drives_the_fps_limiter(fake_clock, monkeypatch):
    fake_clock.patch(monkeypatch, fps_limiter)
    limiter = FPSLimiter(fps=10)

    limiter.fps_limiter()

    assert fake_clock.sleeps == [pytest.approx(0.1)]


def test_mock_output_records_frames(mock_output):
    mock_output.show([1, 2, 3])
    mock_output.show([4, 5, 6])

    assert mock_output.frames == [[1, 2, 3], [4, 5, 6]]
