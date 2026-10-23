from functools import wraps

from mlsc.api.v2.errors import ProblemError
from mlsc.webserver import auth
from mlsc.webserver.messages import Unauthorized


def api_login_required(func):
    """Answer callers without a login session with a JSON 401. A no-op while the PIN lock is off."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if auth.is_auth_enabled() and not auth.is_authenticated():
            raise ProblemError(Unauthorized, "Log in with POST /api/v2/auth/login first.")
        return func(*args, **kwargs)
    return wrapper
