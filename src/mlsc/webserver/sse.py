import json
import queue
import threading
from collections import deque
from collections.abc import Iterator

# Waitress serves each open stream from one of its worker threads, so the cap must stay well below the thread count.
MAX_SUBSCRIBERS = 4
KEEPALIVE_SECONDS = 15
SUBSCRIBER_BACKLOG = 64

# Events that are rare and must not be missed get an id and are replayed to a client that reconnects with `Last-Event-ID`.
# The rest (meters, stats) are continuous: a reconnecting client just waits for the next one.
REPLAYABLE_EVENTS = frozenset({"device.status", "diagnosis", "wifi.state", "operation"})
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

    def stream(self, subscriber: queue.Queue, keepalive: float = KEEPALIVE_SECONDS) -> Iterator[str]:
        try:
            yield format_event("ready", {})
            while True:
                try:
                    yield subscriber.get(timeout=keepalive)
                except queue.Empty:
                    yield ": keepalive\n\n"
        finally:
            self.unsubscribe(subscriber)


broker = EventBroker()
