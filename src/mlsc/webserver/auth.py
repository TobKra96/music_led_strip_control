from collections.abc import Callable
from functools import wraps

from flask import current_app, redirect, request, session, url_for

SESSION_KEY = "authenticated"
EPOCH_KEY = "auth_epoch"


def is_auth_enabled() -> bool:
    """Whether the shared login is enforced. Secure by default when the app does not say otherwise."""
    return current_app.config.get("AUTH_ENABLED", True)


def _epoch() -> int:
    return current_app.config.get("AUTH_EPOCH", 0)


def bump_epoch() -> None:
    """Log out every session that was started before now. Used when the PIN lock is enabled or the PIN changes."""
    current_app.config["AUTH_EPOCH"] = _epoch() + 1


def is_authenticated() -> bool:
    return bool(session.get(SESSION_KEY)) and session.get(EPOCH_KEY) == _epoch()


def session_check() -> Callable[[], bool]:
    """Capture the current login session; the returned check turns false once it has been invalidated.

    Safe to call after the request ended. A session cookie the client deleted cannot be seen from here, only server-side invalidation (epoch bump or auth turned off).
    """
    app = current_app._get_current_object()
    authenticated = is_authenticated()
    epoch = session.get(EPOCH_KEY)
    return lambda: not app.config.get("AUTH_ENABLED", True) or (authenticated and epoch == app.config.get("AUTH_EPOCH", 0))


def login_user() -> None:
    session[SESSION_KEY] = True
    session[EPOCH_KEY] = _epoch()


def logout_user() -> None:
    session.pop(SESSION_KEY, None)
    session.pop(EPOCH_KEY, None)


def login_required(func):
    """Send visitors without a login session to the login page. A no-op while auth is disabled in the config."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not is_auth_enabled() or is_authenticated():
            return func(*args, **kwargs)
        if request.method == "GET" and not request.path.startswith("/api/"):
            session["next"] = request.path
        return redirect(url_for("authentication_api.show_login_page", next=request.path))
    return wrapper
