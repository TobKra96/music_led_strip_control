import hmac

from flask import current_app, request
from flask_openapi3 import APIBlueprint, Tag
from pydantic import BaseModel, Field

from mlsc.api.v2.errors import Problem, ProblemError
from mlsc.api.v2.security import api_login_required
from mlsc.webserver import auth
from mlsc.webserver.executer import Executer
from mlsc.webserver.messages import InvalidPin, TooManyAttempts, ValidationError

tag = Tag(name="Auth", description="Session login and PIN management")
auth_api = APIBlueprint("auth_api_v2", __name__, url_prefix="/api/v2/auth", abp_tags=[tag])

PIN_PATTERN = r"^\d{4,8}$"
WRITE_ERRORS = {"401": Problem, "415": Problem, "422": Problem}


class LoginBody(BaseModel):
    pin: str | None = Field(default=None, description="The PIN configured in the security settings. Not needed while the PIN lock is off.")


class SessionOut(BaseModel):
    authenticated: bool
    pin_required: bool


class PinSettings(BaseModel):
    default_pin: str = Field(pattern=PIN_PATTERN, description="4 to 8 digits.")
    use_pin_lock: bool


def _session() -> dict:
    return {"authenticated": auth.is_authenticated(), "pin_required": auth.is_auth_enabled()}


def _pin_out(pin_config: dict) -> dict:
    return {"default_pin": pin_config["DEFAULT_PIN"], "use_pin_lock": pin_config["USE_PIN_LOCK"]}


@auth_api.get("/session", summary="Show the login state", responses={"200": SessionOut})
def get_session():
    return _session()


@auth_api.post("/login", summary="Log in with the PIN", responses={"200": SessionOut, "429": Problem, **WRITE_ERRORS})
def login(body: LoginBody):
    """Start a session. Repeated failures lock the client out with a growing delay (`Retry-After`)."""
    limiter = current_app.extensions["mlsc_login_limiter"]
    client = request.remote_addr or "unknown"

    wait = limiter.retry_after(client)
    if wait:
        raise ProblemError(TooManyAttempts, headers={"Retry-After": str(wait)})

    executer = Executer.instance.authentication_executer
    if auth.is_auth_enabled():
        if body.pin is None:
            raise ProblemError(ValidationError, errors=[{"field": "pin", "detail": "Field required"}])
        if not hmac.compare_digest(body.pin.encode(), executer.USER_PIN.encode()):
            limiter.record_failure(client)
            raise ProblemError(InvalidPin)
        limiter.record_success(client)
    executer.login()
    return _session()


@auth_api.post("/logout", summary="End the session", responses={"204": None, "415": Problem})
def logout():
    auth.logout_user()
    return "", 204


@auth_api.get("/pin", summary="Get the PIN settings", responses={"200": PinSettings, "401": Problem})
@api_login_required
def get_pin():
    return _pin_out(Executer.instance.authentication_executer.get_pin_setting())


@auth_api.put("/pin", summary="Replace the PIN settings", responses={"200": PinSettings, **WRITE_ERRORS})
@api_login_required
def set_pin(body: PinSettings):
    executer = Executer.instance.authentication_executer
    executer.set_pin_setting({"DEFAULT_PIN": body.default_pin, "USE_PIN_LOCK": body.use_pin_lock})
    return _pin_out(executer.get_pin_setting())


@auth_api.delete("/pin", summary="Reset the PIN settings", responses={"200": PinSettings, "401": Problem})
@api_login_required
def reset_pin():
    return _pin_out(Executer.instance.authentication_executer.reset_pin_settings())
