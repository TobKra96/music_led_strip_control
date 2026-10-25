import json
import queue
import threading
import time
from collections import deque
from collections.abc import Callable, Iterator

# Waitress serves each open stream from one of its worker threads, so the cap must stay well below the thread count.
MAX_SUBSCRIBERS = 4
KEEPALIVE_SECONDS = 15
# How often an open stream re-checks that its login session is still valid.
SESSION_RECHECK_SECONDS = 15
SUBSCRIBER_BACKLOG = 64
# How often an open stream checks that its client is still there, so a closed page frees its slot even when no events flow.
DISCONNECT_CHECK_SECONDS = 0.1

# Events that are rare and must not be missed get an id and are replayed to a client that reconnects with `Last-Event-ID`.
# The rest (meters, stats) are continuous: a reconnecting client just waits for the next one.
REPLAYABLE_EVENTS = frozenset({"device.status", "diagnosis", "wifi.state", "operation", "audio.status"})
REPLAY_BUFFER = 32


def format_event(event: str, data, event_id: int | None = None) -> str:
    id_line = f"id: {event_id}\n" if event_id is not None else ""
    return f"{id_line}event: {event}\ndata: {json.dumps(data)}\n\n"


class EventBroker:
    """Fan-out of server events to the connected SSE clients."""

    def __init__(self, max_subscribers: int = MAX_SUBSCRIBERS) -> None:
        self._max_subscribers = max_subscribers
        self._subscribers: set[queue.Queue] = set()
        self._lock = threading.Lock()
        self._next_id = 1
        self._replay: deque[tuple[int, str]] = deque(maxlen=REPLAY_BUFFER)

    def subscribe(self, last_event_id: int | None = None) -> queue.Queue | None:
        """Register a client, or return None when all stream slots are taken.

        A client that passes the id of the last event it saw first gets the replayable events it missed.
        """
        with self._lock:
            if len(self._subscribers) >= self._max_subscribers:
                return None
            subscriber = queue.Queue(maxsize=SUBSCRIBER_BACKLOG)
            if last_event_id is not None:
                for event_id, message in self._replay:
                    if event_id > last_event_id:
                        subscriber.put_nowait(message)
            self._subscribers.add(subscriber)
            return subscriber

    def has_subscribers(self) -> bool:
        with self._lock:
            return bool(self._subscribers)

    def unsubscribe(self, subscriber: queue.Queue) -> None:
        with self._lock:
            self._subscribers.discard(subscriber)

    def publish(self, event: str, data) -> None:
        """Queue an event for every client. A client that stopped reading drops events instead of blocking the publisher."""
        with self._lock:
            if event in REPLAYABLE_EVENTS:
                event_id = self._next_id
                self._next_id += 1
                message = format_event(event, data, event_id)
                self._replay.append((event_id, message))
            else:
                message = format_event(event, data)
            subscribers = list(self._subscribers)
        for subscriber in subscribers:
            try:
                subscriber.put_nowait(message)
            except queue.Full:
                continue

    def stream(
        self,
        subscriber: queue.Queue,
        keepalive: float | None = None,
        is_valid: Callable[[], bool] | None = None,
        recheck_seconds: float | None = None,
        client_gone: Callable[[], bool] | None = None,
    ) -> Iterator[str]:
        """Yield events until the client leaves or `is_valid` turns false, which ends the stream so the client reconnects and is refused.

        Without `client_gone` a departed client is only noticed when writing to it fails, so its slot stays taken while no events flow.
        """
        keepalive = KEEPALIVE_SECONDS if keepalive is None else keepalive
        recheck_seconds = SESSION_RECHECK_SECONDS if recheck_seconds is None else recheck_seconds
        wait = min(keepalive, DISCONNECT_CHECK_SECONDS) if client_gone is not None else keepalive
        last_check = last_sent = time.monotonic()
        try:
            yield format_event("ready", {})
            while True:
                if client_gone is not None and client_gone():
                    return
                if is_valid is not None and time.monotonic() - last_check >= recheck_seconds:
                    if not is_valid():
                        return
                    last_check = time.monotonic()
                try:
                    message = subscriber.get(timeout=wait)
                except queue.Empty:
                    if time.monotonic() - last_sent < keepalive:
                        continue
                    message = ": keepalive\n\n"
                last_sent = time.monotonic()
                yield message
        finally:
            self.unsubscribe(subscriber)


broker = EventBroker()
