from importlib import import_module

from flask import Flask, render_template, request
from werkzeug.exceptions import HTTPException

from libs.webserver.messages import BadRequest, MethodNotAllowed, NotFound, ServerError


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


def register_blueprints(app: Flask) -> None:
    for module_name in ["home"]:
        module = import_module(f"libs.app.{module_name}.routes")
        app.register_blueprint(module.blueprint)


def register_errors(app: Flask) -> None:
    app.register_error_handler(400, bad_request)
    app.register_error_handler(404, not_found)
    app.register_error_handler(405, method_not_allowed)
    app.register_error_handler(500, server_error)


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static")
    register_blueprints(app)
    register_errors(app)
    return app
