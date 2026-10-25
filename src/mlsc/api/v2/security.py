from functools import wraps

from flask import Response, request
from werkzeug.exceptions import BadRequest as MalformedJson

from mlsc.api.v2.errors import ProblemError, handle_problem_error, is_v2_request
from mlsc.webserver import auth
from mlsc.webserver.messages import BadRequest, Unauthorized, UnsupportedMediaType

WRITE_METHODS = frozenset({"POST", "PUT", "PATCH"})
# Writes that take no body. Without a Content-Type they cannot be sent by a cross-site form, which always sets one.
BODYLESS_WRITES = frozenset({"auth_api_v2.logout"})
# Writes that carry raw audio. A cross-site form cannot send this Content-Type without a preflight either.
BINARY_WRITES = frozenset({"microphone_api_v2.post_browser_chunk"})
BINARY_MIMETYPE = "application/octet-stream"


def api_login_required(func):
    """Answer callers without a login session with a JSON 401. A no-op while the PIN lock is off."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if auth.is_auth_enabled() and not auth.is_authenticated():
            raise ProblemError(Unauthorized, "Log in with POST /api/v2/auth/login first.")
        return func(*args, **kwargs)
    return wrapper


def _is_bodyless(endpoint: str | None) -> bool:
    return endpoint in BODYLESS_WRITES and not request.content_type and not request.get_data()


def require_json_writes() -> Response | None:
    """Require `Content-Type: application/json` on writes, which a cross-site form cannot send without a preflight."""
    if not is_v2_request():
        return None
    if request.endpoint in BINARY_WRITES:
        if request.mimetype != BINARY_MIMETYPE:
            return handle_problem_error(ProblemError(UnsupportedMediaType, f"Send the request body as {BINARY_MIMETYPE}."))
        return None
    if request.method in WRITE_METHODS and request.mimetype != "application/json" and not _is_bodyless(request.endpoint):
        return handle_problem_error(ProblemError(UnsupportedMediaType, "Send the request body as application/json."))
    try:
        if request.is_json and request.get_data():
            request.get_json()
    except MalformedJson:
        return handle_problem_error(ProblemError(BadRequest, "The request body is not valid JSON."))
    return None
