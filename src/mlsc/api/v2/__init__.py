"""REST API v2: one blueprint per resource, RFC 9457 problem+json errors, session-cookie JSON auth."""
import copy
import time
from collections.abc import Callable

from flask_openapi3 import OpenAPI

from mlsc.api.v2.auth import auth_api
from mlsc.api.v2.devices import devices_api
from mlsc.api.v2.effects import effects_api
from mlsc.api.v2.errors import API_V2_PREFIX, register_error_handlers
from mlsc.api.v2.events import events_api
from mlsc.api.v2.groups import groups_api
from mlsc.api.v2.resources import resources_api
from mlsc.api.v2.security import require_json_writes
from mlsc.api.v2.settings import settings_api
from mlsc.api.v2.system import system_api
from mlsc.api.v2.throttle import LoginLimiter

SPEC_PATH = f"{API_V2_PREFIX}openapi.json"
API_V2_BLUEPRINTS = (auth_api, devices_api, groups_api, effects_api, resources_api, settings_api, system_api, events_api)


# Fixed response descriptions: the stdlib phrases differ between Python versions (422 is "Unprocessable Entity" before 3.13).
STATUS_DESCRIPTIONS = {
    "200": "OK",
    "204": "No Content",
    "400": "Bad Request",
    "401": "Unauthorized",
    "404": "Not Found",
    "415": "Unsupported Media Type",
    "422": "Unprocessable Content",
    "429": "Too Many Requests",
    "503": "Service Unavailable",
}
FRAMEWORK_VALIDATION_SCHEMA = "ValidationErrorModel"


def v2_spec(app: OpenAPI) -> dict:
    """Return the OpenAPI document restricted to the v2 paths, with the same text on every Python version.

    flask-openapi3 documents its own 422 body; v2 answers validation errors with `Problem`, so that response is replaced.
    """
    spec = copy.deepcopy(app.api_doc)
    spec["paths"] = {path: item for path, item in spec["paths"].items() if path.startswith(API_V2_PREFIX) and path != SPEC_PATH}
    problem_ref = {"$ref": "#/components/schemas/Problem"}
    for item in spec["paths"].values():
        for operation in item.values():
            for status, response in operation["responses"].items():
                response["description"] = STATUS_DESCRIPTIONS.get(status, response["description"])
                if status == "422":
                    response["content"] = {"application/json": {"schema": problem_ref}}
    spec["components"]["schemas"].pop(FRAMEWORK_VALIDATION_SCHEMA, None)
    return spec


def register_api_v2(app: OpenAPI, clock: Callable[[], float] = time.monotonic) -> None:
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.extensions["mlsc_login_limiter"] = LoginLimiter(clock)
    register_error_handlers(app)
    app.before_request(require_json_writes)
    for blueprint in API_V2_BLUEPRINTS:
        app.register_api(blueprint)

    @app.get(SPEC_PATH)
    def openapi_v2_spec() -> dict:
        return v2_spec(app)
