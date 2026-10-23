"""Operations: tracked changes that can take time or fail, applied with verify and rollback."""
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

from mlsc.webserver import sse


class OperationState(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass(frozen=True)
class RetryPolicy:
    """How often apply and verify are tried, and how the wait between tries grows."""

    attempts: int = 3
    delay: float = 1.0
    factor: float = 2.0


@dataclass
class Operation:
    id: str
    kind: str
    state: OperationState = OperationState.PENDING
    attempts: int = 0
    error: str | None = None
    deadline: float | None = field(default=None, repr=False)
    rollback: Callable[[], None] | None = field(default=None, repr=False)

    def as_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind, "state": self.state.value, "attempts": self.attempts, "error": self.error}


MAX_FINISHED = 100
DEFAULT_POLICY = RetryPolicy()


def _spawn_thread(target: Callable[[], None]) -> None:
    threading.Thread(target=target, daemon=True).start()


class OperationRegistry:
    """Runs safe applies and keeps their Operations. Time, sleeping, publishing and threading are injectable for tests."""

    def __init__(self, clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep,
                 publish: Callable[[str, dict], None] | None = None, spawn: Callable[[Callable[[], None]], None] = _spawn_thread) -> None:
        self._clock = clock
        self._sleep = sleep
        self._publish = publish if publish is not None else lambda event, data: sse.broker.publish(event, data)
        self._spawn = spawn
        self._operations: dict[str, Operation] = {}
        self._lock = threading.Lock()

    def get(self, operation_id: str) -> Operation | None:
        self.tick()
        return self._operations.get(operation_id)

    def run(self, kind: str, apply: Callable[[], None], verify: Callable[[], bool], rollback: Callable[[], None],
            policy: RetryPolicy = DEFAULT_POLICY, confirm_within: float | None = None) -> Operation:
        """Apply, verify and roll back on failure, in the calling thread.

        A failed verify applies again on the next attempt without rolling back in between, so `apply` must be safe to repeat.
        """
        operation = self._create(kind)
        self._execute(operation, apply, verify, rollback, policy, confirm_within)
        return operation

    def start(self, kind: str, apply: Callable[[], None], verify: Callable[[], bool], rollback: Callable[[], None],
              policy: RetryPolicy = DEFAULT_POLICY, confirm_within: float | None = None) -> Operation:
        """Like `run`, but return the pending Operation at once and do the work in the background."""
        operation = self._create(kind)
        self._spawn(lambda: self._execute(operation, apply, verify, rollback, policy, confirm_within))
        return operation

    def confirm(self, operation_id: str) -> Operation:
        """Keep a change that is waiting for its confirmation. Raises KeyError for an unknown id."""
        self.tick()
        operation = self._operations[operation_id]
        with self._lock:
            if operation.state is OperationState.PENDING and operation.deadline is not None:
                operation.deadline = None
                operation.rollback = None
                self._set_state(operation, OperationState.CONFIRMED)
        return operation

    def tick(self) -> None:
        """Roll back every change whose confirmation deadline has passed."""
        now = self._clock()
        with self._lock:
            overdue = [o for o in self._operations.values() if o.state is OperationState.PENDING and o.deadline is not None and now >= o.deadline]
            for operation in overdue:
                operation.deadline = None
                self._roll_back(operation, "Not confirmed in time.")

    def _create(self, kind: str) -> Operation:
        operation = Operation(id=uuid.uuid4().hex, kind=kind)
        with self._lock:
            self._operations[operation.id] = operation
            self._evict_finished()
            self._publish("operation", operation.as_dict())
        return operation

    def _evict_finished(self) -> None:
        """Forget the oldest finished Operations beyond `MAX_FINISHED`, so the registry does not grow without bound."""
        finished = [o.id for o in self._operations.values() if o.state is not OperationState.PENDING]
        for operation_id in finished[:-MAX_FINISHED] if len(finished) > MAX_FINISHED else []:
            del self._operations[operation_id]

    def _set_state(self, operation: Operation, state: OperationState, error: str | None = None) -> None:
        operation.state = state
        operation.error = error
        self._publish("operation", operation.as_dict())

    def _roll_back(self, operation: Operation, reason: str) -> None:
        try:
            if operation.rollback is not None:
                operation.rollback()
        except Exception as e:
            self._set_state(operation, OperationState.FAILED, f"{reason} Rollback failed: {e}")
        else:
            self._set_state(operation, OperationState.ROLLED_BACK, reason)
        operation.rollback = None

    def _execute(self, operation: Operation, apply: Callable[[], None], verify: Callable[[], bool], rollback: Callable[[], None],
                 policy: RetryPolicy, confirm_within: float | None) -> None:
        reason = "Verification failed."
        delay = policy.delay
        for attempt in range(1, max(policy.attempts, 1) + 1):
            if attempt > 1:
                self._sleep(delay)
                delay *= policy.factor
            operation.attempts = attempt
            try:
                apply()
                if verify():
                    break
            except Exception as e:
                reason = str(e) or type(e).__name__
        else:
            with self._lock:
                operation.rollback = rollback
                self._roll_back(operation, reason)
            return
        with self._lock:
            if confirm_within is None:
                self._set_state(operation, OperationState.CONFIRMED)
            else:
                operation.rollback = rollback
                operation.deadline = self._clock() + confirm_within
                self._set_state(operation, OperationState.PENDING)


TICK_SECONDS = 1.0


def run_ticker(operations: OperationRegistry, wait: Callable[[float], bool], interval: float = TICK_SECONDS) -> None:
    """Tick the registry every `interval` until `wait` reports a stop, so deadlines pass without anyone polling."""
    while not wait(interval):
        operations.tick()


@dataclass
class Ticker:
    thread: threading.Thread
    _stopped: threading.Event

    def stop(self) -> None:
        self._stopped.set()
        self.thread.join()


def start_ticker(operations: OperationRegistry, interval: float = TICK_SECONDS) -> Ticker:
    """Run `run_ticker` in a daemon thread."""
    stopped = threading.Event()
    thread = threading.Thread(target=run_ticker, args=(operations, stopped.wait, interval), daemon=True)
    thread.start()
    return Ticker(thread, stopped)


registry = OperationRegistry()
