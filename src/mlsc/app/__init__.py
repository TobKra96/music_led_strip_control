from importlib import import_module

from flask import render_template, request
from flask_openapi3 import Info, OpenAPI
from werkzeug.exceptions import HTTPException

from mlsc.api.v2.errors import v2_aware
from mlsc.webserver import auth
from mlsc.webserver.deprecation import v1_spec
from mlsc.webserver.messages import BadRequest, MethodNotAllowed, NotFound, ServerError

API_INFO = Info(
    title="MLSC API",
    description="API for communicating with the MLSC server. The API is based on the OpenAPI 3.1 specification.",
    version="2.3.0",
    license={"name": "MIT", "url": "https://github.com/TobKra96/music_led_strip_control/blob/master/LICENSE"},
)


def bad_request(_: HTTPException) -> tuple:
    return BadRequest.as_response()


def not_found(e: HTTPException) -> tuple:
    if request.path.startswith("/api/"):
        return NotFound.as_response()
    return render_template("home/error.html", code=e.code, message="Page not found"), e.code


def method_not_allowed(e: HTTPException) -> tuple:
    if request.path.startswith("/api/"):
        return MethodNotAllowed.as_response()
    return render_template("home/error.html", code=e.code, message="Method not allowed"), e.code


def server_error(e: HTTPException) -> tuple:
    if request.path.startswith("/api/"):
        return ServerError.as_response()
    return render_template("home/error.html", code=e.code, message="Server error"), e.code


def register_blueprints(app: OpenAPI) -> None:
    for module_name in ["home"]:
        module = import_module(f"mlsc.app.{module_name}.routes")
        app.register_blueprint(module.blueprint)


def register_api_docs(app: OpenAPI) -> None:
    @app.get("/openapi.json")
    def openapi_spec() -> dict:
        return v1_spec(app)

    @app.get("/api/")
    def api_docs() -> str:
        return render_template("swagger.html")


def register_errors(app: OpenAPI) -> None:
    app.register_error_handler(400, v2_aware(bad_request))
    app.register_error_handler(404, v2_aware(not_found))
    app.register_error_handler(405, v2_aware(method_not_allowed))
    app.register_error_handler(500, v2_aware(server_error))


def create_app() -> OpenAPI:
    # The interactive docs are served by `register_api_docs` from bundled assets, not by flask-openapi3's CDN-based UI.
    app = OpenAPI(__name__, static_folder="static", info=API_INFO, doc_ui=False)
    register_blueprints(app)
    register_api_docs(app)
    app.context_processor(lambda: {"is_authenticated": auth.is_authenticated})
    register_errors(app)
    return app
