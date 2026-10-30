# ruff: file-ignore[private-member-access]
import queue
from typing import ClassVar

import pytest

from mlsc import effect_service
from mlsc.diagnosis import Status
from mlsc.effect_item import EffectItem
from mlsc.effect_service import FALLBACK_AFTER_FAILURES, LOG_INTERVAL_SECONDS, WARNING_REPEAT_SECONDS, EffectService
from mlsc.effects_enum import EffectsEnum
from mlsc.fps_limiter import FPSLimiter
from mlsc.strip_preview import PreviewChannel, PreviewHub, PreviewSink

pytestmark = pytest.mark.unit


class Queue:
    def __init__(self) -> None:
        self._items = queue.SimpleQueue()

    def put_blocking(self, item):
        self._items.put(item)

    def get_blocking(self):
        return self._items.get()

    def empty(self):
        return self._items.empty()


class StubDevice:
    device_config: ClassVar[dict] = {"device_name": "Desk", "fps": 1000}

    def __init__(self) -> None:
        self.device_notification_queue_in = Queue()
        self.device_notification_queue_out = Queue()
        self.effect_queue = Queue()


class Preview:
    def __init__(self) -> None:
        self.diagnoses = []

    def diagnosis(self, diagnosis):
        self.diagnoses.append(diagnosis)


class Broken:
    runs = 0

    def __init__(self, _device) -> None:
        pass

    def run(self):  # ruff: ignore[no-self-use]
        Broken.runs += 1
        msg = "boom"
        raise ValueError(msg)


class Healthy:
    runs = 0

    def __init__(self, _device) -> None:
        pass

    def run(self):  # ruff: ignore[no-self-use]
        Healthy.runs += 1


class Off:
    runs = 0

    def __init__(self, _device) -> None:
        pass

    def run(self):  # ruff: ignore[no-self-use]
        Off.runs += 1


@pytest.fixture
def setup(monkeypatch):
    Broken.runs = Healthy.runs = Off.runs = 0
    clock = [100.0]
    monkeypatch.setattr(effect_service, "time", lambda: clock[0])
    errors = []
    monkeypatch.setattr(effect_service.logger, "error", lambda message, *_a, **_k: errors.append(message))
    device = StubDevice()
    service = EffectService()
    service._device = device
    service._fps_limiter = FPSLimiter(1000)
    service._preview = Preview()
    service._available_effects = {EffectsEnum.effect_off: Off, EffectsEnum.effect_single: Broken, EffectsEnum.effect_fade: Healthy}
    service._initialized_effects = {}
    service._current_effect = EffectsEnum.effect_single
    service._skip_effect = False
    service._failures = 0
    service._last_logged = float("-inf")
    service._suppressed = 0
    service._warning = None
    service._warned_at = float("-inf")
    service.ten_seconds_counter = service.start_time = clock[0]
    return service, device, clock, errors


def test_a_failing_frame_is_skipped_and_the_next_frame_runs(setup):
    service, _device, _clock, _errors = setup

    service.effect_routine()
    service.effect_routine()

    assert Broken.runs == 2
    assert service._current_effect is EffectsEnum.effect_single


def test_failures_are_logged_at_most_once_per_interval(setup):
    service, _device, clock, errors = setup

    for _ in range(5):
        service.effect_routine()
    assert len(errors) == 1

    clock[0] += LOG_INTERVAL_SECONDS + 1
    service.effect_routine()
    assert len(errors) == 2
    assert "4 similar" in errors[1]


def test_a_success_resets_the_failure_count(setup):
    service, device, _clock, _errors = setup

    for _ in range(FALLBACK_AFTER_FAILURES - 1):
        service.effect_routine()
    device.effect_queue.put_blocking(EffectItem(EffectsEnum.effect_fade, "device_0"))
    service.effect_routine()
    device.effect_queue.put_blocking(EffectItem(EffectsEnum.effect_single, "device_0"))
    for _ in range(FALLBACK_AFTER_FAILURES - 1):
        service.effect_routine()

    assert service._current_effect is EffectsEnum.effect_single
    assert service._preview.diagnoses == []


def test_consecutive_failures_fall_back_to_effect_off_with_a_warning(setup):
    service, _device, _clock, _errors = setup

    for _ in range(FALLBACK_AFTER_FAILURES):
        service.effect_routine()

    assert service._current_effect is EffectsEnum.effect_off
    [diagnosis] = service._preview.diagnoses
    assert diagnosis.status is Status.WARNING
    assert "single" in diagnosis.message.lower()

    service.effect_routine()
    assert Off.runs == 1
    assert Broken.runs == FALLBACK_AFTER_FAILURES


def test_an_unknown_effect_is_isolated(setup):
    service, _device, _clock, errors = setup
    service._current_effect = EffectsEnum.effect_bars

    service.effect_routine()

    assert len(errors) >= 1


def test_the_warning_is_repeated_while_the_fallback_lasts(setup):
    service, _device, clock, _errors = setup
    for _ in range(FALLBACK_AFTER_FAILURES):
        service.effect_routine()

    service.effect_routine()
    assert len(service._preview.diagnoses) == 1

    clock[0] += WARNING_REPEAT_SECONDS
    service.effect_routine()
    assert [d.status for d in service._preview.diagnoses] == [Status.WARNING, Status.WARNING]


def test_choosing_another_effect_clears_the_warning(setup):
    service, device, clock, _errors = setup
    for _ in range(FALLBACK_AFTER_FAILURES):
        service.effect_routine()

    device.effect_queue.put_blocking(EffectItem(EffectsEnum.effect_fade, "device_0"))
    service.effect_routine()
    clock[0] += WARNING_REPEAT_SECONDS
    service.effect_routine()

    assert [d.status for d in service._preview.diagnoses] == [Status.WARNING, Status.OK]


def test_the_warning_reaches_the_diagnosis_event_through_the_preview_hub(setup):
    service, _device, _clock, _errors = setup
    channel = PreviewChannel()
    service._preview = PreviewSink(channel, "device_0")
    published = []
    hub = PreviewHub(channel, lambda event, data: published.append((event, data)))

    for _ in range(FALLBACK_AFTER_FAILURES):
        service.effect_routine()
    hub.drain(timeout=1)

    [(event, payload)] = published
    assert event == "diagnosis"
    assert payload["device_id"] == "device_0"
    assert payload["status"] == "warning"
    assert hub.latest("device_0")[1] == payload
