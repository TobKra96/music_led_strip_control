from functools import wraps

from flask import current_app, redirect, request, session, url_for

SESSION_KEY = "authenticated"


def is_auth_enabled() -> bool:
    """Whether the shared login is enforced. Secure by default when the app does not say otherwise."""
    return current_app.config.get("AUTH_ENABLED", True)


def is_authenticated() -> bool:
    return bool(session.get(SESSION_KEY))


def login_user() -> None:
    session[SESSION_KEY] = True


def logout_user() -> None:
    session.pop(SESSION_KEY, None)


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
