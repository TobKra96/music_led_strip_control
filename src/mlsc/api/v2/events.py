from flask import Response, request, stream_with_context
from flask_openapi3 import APIBlueprint, Tag

from mlsc.api.v2.errors import Problem, ProblemError
from mlsc.api.v2.security import api_login_required
from mlsc.webserver import auth, sse
from mlsc.webserver.messages import TooManyStreams

tag = Tag(name="Events", description="Server-sent event stream")
events_api = APIBlueprint("events_api_v2", __name__, url_prefix="/api/v2/events", abp_tags=[tag])


@events_api.get("", summary="Subscribe to server events", responses={"200": None, "401": Problem, "503": Problem})
@api_login_required
def events():
    """One multiplexed `text/event-stream` with `device.status`, `diagnosis`, `mic.level`, `audio.status`, `wifi.state`, `system.stats` and `operation`.

    Notifications only. The low-rate events carry an `id`; reconnect with `Last-Event-ID` to receive the ones missed.
    """
    last_event_id = request.headers.get("Last-Event-ID", type=int)
    subscriber = sse.broker.subscribe(last_event_id)
    if subscriber is None:
        raise ProblemError(TooManyStreams)

    # no-transform and X-Accel-Buffering keep proxies from holding events back.
    return Response(
        # Set by waitress (with `channel_request_lookahead`), so a closed page frees its slot without waiting for the next event.
        stream_with_context(sse.broker.stream(
            subscriber, is_valid=auth.session_check(), client_gone=request.environ.get("waitress.client_disconnected"))),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )
