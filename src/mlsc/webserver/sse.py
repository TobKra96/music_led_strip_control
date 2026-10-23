import json
import queue
import threading
from collections.abc import Iterator

from flask import Response, stream_with_context
from flask_openapi3 import APIBlueprint

from mlsc.webserver.auth import login_required

# Waitress serves each open stream from one of its worker threads, so the cap must stay well below the thread count.
MAX_SUBSCRIBERS = 4
KEEPALIVE_SECONDS = 15
SUBSCRIBER_BACKLOG = 64

events_api = APIBlueprint("events_api", __name__)


def format_event(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


class EventBroker:
    """Fan-out of server events to the connected SSE clients."""

    def __init__(self, max_subscribers: int = MAX_SUBSCRIBERS) -> None:
        self._max_subscribers = max_subscribers
        self._subscribers: set[queue.Queue] = set()
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue | None:
        """Register a client, or return None when all stream slots are taken."""
        with self._lock:
            if len(self._subscribers) >= self._max_subscribers:
                return None
            subscriber = queue.Queue(maxsize=SUBSCRIBER_BACKLOG)
            self._subscribers.add(subscriber)
            return subscriber

    def unsubscribe(self, subscriber: queue.Queue) -> None:
        with self._lock:
            self._subscribers.discard(subscriber)

    def publish(self, event: str, data) -> None:
        """Queue an event for every client. A client that stopped reading drops events instead of blocking the publisher."""
        message = format_event(event, data)
        with self._lock:
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


@events_api.get("/api/v2/events")
@login_required
def events():
    """Server-sent events stream."""
    subscriber = broker.subscribe()
    if subscriber is None:
        return Response("Too many event streams.", status=503)

    # no-transform and X-Accel-Buffering keep proxies from holding events back.
    return Response(
        stream_with_context(broker.stream(subscriber)),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )
