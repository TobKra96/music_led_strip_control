import pytest

from mlsc.operations import MAX_FINISHED, OperationRegistry, OperationState, RetryPolicy

pytestmark = pytest.mark.unit


class Recorder:
    """Stands in for the apply, verify and rollback steps and records the order they ran in."""

    def __init__(self, verify_results=(True,), apply_error=None, rollback_error=None) -> None:
        self.calls = []
        self._verify_results = list(verify_results)
        self._apply_error = apply_error
        self._rollback_error = rollback_error

    def apply(self):
        self.calls.append("apply")
        if self._apply_error:
            raise self._apply_error

    def verify(self):
        self.calls.append("verify")
        return self._verify_results.pop(0) if len(self._verify_results) > 1 else self._verify_results[0]

    def rollback(self):
        self.calls.append("rollback")
        if self._rollback_error:
            raise self._rollback_error


@pytest.fixture
def events():
    return []


@pytest.fixture
def registry(fake_clock, events):
    return OperationRegistry(clock=fake_clock.time, sleep=fake_clock.sleep, publish=lambda name, data: events.append((name, data)))


def test_an_apply_that_verifies_is_confirmed_without_rollback(registry):
    steps = Recorder()

    operation = registry.run("output", steps.apply, steps.verify, steps.rollback)

    assert operation.state is OperationState.CONFIRMED
    assert steps.calls == ["apply", "verify"]
    assert registry.get(operation.id) is operation


def test_a_failing_verify_is_retried_with_growing_backoff_before_it_is_confirmed(registry, fake_clock):
    steps = Recorder(verify_results=[False, False, True])

    operation = registry.run("output", steps.apply, steps.verify, steps.rollback, RetryPolicy(attempts=3, delay=2, factor=3))

    assert operation.state is OperationState.CONFIRMED
    assert operation.attempts == 3
    assert fake_clock.sleeps == [2, 6]
    assert "rollback" not in steps.calls


def test_exhausted_attempts_roll_back(registry):
    steps = Recorder(verify_results=[False])

    operation = registry.run("output", steps.apply, steps.verify, steps.rollback, RetryPolicy(attempts=2, delay=1))

    assert operation.state is OperationState.ROLLED_BACK
    assert steps.calls == ["apply", "verify", "apply", "verify", "rollback"]


def test_an_apply_that_raises_rolls_back_and_keeps_the_reason(registry):
    steps = Recorder(apply_error=RuntimeError("no GPIO"))

    operation = registry.run("output", steps.apply, steps.verify, steps.rollback, RetryPolicy(attempts=1))

    assert operation.state is OperationState.ROLLED_BACK
    assert operation.error == "no GPIO"


def test_a_rollback_that_fails_leaves_the_operation_failed(registry):
    steps = Recorder(verify_results=[False], rollback_error=OSError("disk full"))

    operation = registry.run("output", steps.apply, steps.verify, steps.rollback, RetryPolicy(attempts=1))

    assert operation.state is OperationState.FAILED
    assert "disk full" in operation.error


def test_every_state_change_is_published_as_an_operation_event(registry, events):
    steps = Recorder()

    operation = registry.run("output", steps.apply, steps.verify, steps.rollback)

    assert [name for name, _ in events] == ["operation"] * len(events)
    assert [data["state"] for _, data in events][-1] == "confirmed"
    assert events[0][1]["state"] == "pending"
    assert all(data["id"] == operation.id for _, data in events)


def test_an_unconfirmed_apply_rolls_back_when_its_deadline_passes(registry, fake_clock):
    steps = Recorder()
    operation = registry.run("wifi", steps.apply, steps.verify, steps.rollback, confirm_within=45)
    assert operation.state is OperationState.PENDING

    fake_clock.advance(44)
    registry.tick()
    assert operation.state is OperationState.PENDING

    fake_clock.advance(1)
    registry.tick()
    assert operation.state is OperationState.ROLLED_BACK
    assert steps.calls[-1] == "rollback"


def test_confirming_before_the_deadline_keeps_the_change(registry, fake_clock):
    steps = Recorder()
    operation = registry.run("wifi", steps.apply, steps.verify, steps.rollback, confirm_within=45)

    registry.confirm(operation.id)
    fake_clock.advance(100)
    registry.tick()

    assert operation.state is OperationState.CONFIRMED
    assert "rollback" not in steps.calls


def test_start_returns_a_pending_operation_and_runs_the_steps_in_the_background(fake_clock):
    started = []
    registry = OperationRegistry(clock=fake_clock.time, sleep=fake_clock.sleep, spawn=started.append)
    steps = Recorder()

    operation = registry.start("output", steps.apply, steps.verify, steps.rollback)

    assert operation.state is OperationState.PENDING
    assert steps.calls == []
    started[0]()
    assert operation.state is OperationState.CONFIRMED


def test_unknown_operations_are_not_found(registry):
    assert registry.get("nope") is None
    with pytest.raises(KeyError):
        registry.confirm("nope")


def test_the_default_registry_publishes_to_the_event_stream(fake_clock, monkeypatch):
    from mlsc.webserver import sse

    broker = sse.EventBroker()
    monkeypatch.setattr(sse, "broker", broker)
    subscriber = broker.subscribe()

    OperationRegistry(clock=fake_clock.time, sleep=fake_clock.sleep).run("output", lambda: None, lambda: True, lambda: None)

    messages = []
    while not subscriber.empty():
        messages.append(subscriber.get_nowait())
    assert len(messages) == 2
    assert messages[0].startswith("id: ")
    assert "event: operation" in messages[0]
    assert '"state": "confirmed"' in messages[-1]


def test_confirming_after_the_deadline_is_too_late(registry, fake_clock):
    steps = Recorder()
    operation = registry.run("wifi", steps.apply, steps.verify, steps.rollback, confirm_within=45)

    fake_clock.advance(60)
    registry.confirm(operation.id)

    assert operation.state is OperationState.ROLLED_BACK


def test_only_the_most_recent_finished_operations_are_kept(registry):
    steps = Recorder()
    first = registry.run("output", steps.apply, steps.verify, steps.rollback)
    for _ in range(MAX_FINISHED + 1):
        registry.run("output", steps.apply, steps.verify, steps.rollback)

    assert registry.get(first.id) is None
