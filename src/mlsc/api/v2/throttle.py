import math
import threading
import time
from collections.abc import Callable

FREE_ATTEMPTS = 5
BASE_DELAY_SECONDS = 1
MAX_DELAY_SECONDS = 300
MAX_TRACKED_CLIENTS = 1024


class LoginLimiter:
    """Locks a client out after repeated failed logins, doubling the lockout with every further failure."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._failures: dict[str, int] = {}
        self._blocked_until: dict[str, float] = {}

    def retry_after(self, client: str) -> int:
        """Seconds the client still has to wait, 0 when it may try."""
        with self._lock:
            remaining = self._blocked_until.get(client, 0) - self._clock()
        return max(0, math.ceil(remaining))

    def record_failure(self, client: str) -> None:
        with self._lock:
            if client not in self._failures and len(self._failures) >= MAX_TRACKED_CLIENTS:
                self._forget_oldest()
            failures = self._failures.get(client, 0) + 1
            self._failures[client] = failures
            if failures >= FREE_ATTEMPTS:
                delay = min(BASE_DELAY_SECONDS * 2 ** (failures - FREE_ATTEMPTS), MAX_DELAY_SECONDS)
                self._blocked_until[client] = self._clock() + delay

    def record_success(self, client: str) -> None:
        with self._lock:
            self._failures.pop(client, None)
            self._blocked_until.pop(client, None)

    def _forget_oldest(self) -> None:
        oldest = next(iter(self._failures))
        self._failures.pop(oldest)
        self._blocked_until.pop(oldest, None)
