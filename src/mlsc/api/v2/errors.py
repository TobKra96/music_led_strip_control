from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

from flask import Response, jsonify, request
from pydantic import BaseModel, Field
from werkzeug.exceptions import HTTPException

from mlsc.webserver.messages import HttpError, ServerError, ValidationError, _Message, error_codes, message_for_status

if TYPE_CHECKING:
    from collections.abc import Callable

    from pydantic import ValidationError as PydanticValidationError

API_V2_PREFIX = "/api/v2/"
PROBLEM_MIMETYPE = "application/problem+json"
PROBLEM_TYPE_PREFIX = "urn:mlsc:problem:"
GENERIC_HTTP_CODE = HttpError.__name__


class FieldError(BaseModel):
    field: str = Field(description="Dotted path of the offending field.")
    detail: str


class Problem(BaseModel):
    """RFC 9457 problem details."""

    type: str = Field(description="URI that identifies the problem type.")
    title: str
    status: int
    detail: str | None = None
    code: str = Field(description="Stable error code; the v1 `message_id` where one exists.", json_schema_extra=lambda schema: schema.update(enum=error_codes()))
    errors: list[FieldError] | None = Field(default=None, description="Per-field validation errors.")


READ_ERRORS = {"401": Problem, "404": Problem}
BODY_ERRORS = {"401": Problem, "415": Problem, "422": Problem}
WRITE_ERRORS = {**READ_ERRORS, **BODY_ERRORS}


class ProblemError(Exception):
    """Raised by v2 code to answer with a problem document. `message` is one of the sentinel classes in `messages.py`."""

    def __init__(self, message: type[_Message], detail: str | None = None, errors: list[dict] | None = None, headers: dict | None = None) -> None:
        super().__init__(message.message)
        self.message = message
        self.detail = detail if detail is not None else message.message
        self.errors = errors
        self.headers = headers or {}


def is_v2_request() -> bool:
    return request.path.startswith(API_V2_PREFIX)


def problem_response(status: int, title: str, code: str, detail: str | None = None, errors: list[dict] | None = None,
                     headers: dict | None = None) -> Response:
    body = {"type": f"{PROBLEM_TYPE_PREFIX}{code}", "title": title, "status": status, "code": code}
    if detail is not None:
        body["detail"] = detail
    if errors is not None:
        body["errors"] = errors
    response = jsonify(body)
    response.status_code = status
    response.mimetype = PROBLEM_MIMETYPE
    for name, value in (headers or {}).items():
        response.headers[name] = value
    return response


def handle_problem_error(e: ProblemError) -> Response:
    return problem_response(e.message.code, e.message.message, e.message.__name__, e.detail, e.errors, e.headers)


def handle_http_exception(e: HTTPException) -> Response:
    """Problem for the built-in HTTP errors (404, 405, 400 ...) of a v2 request."""
    status = e.code or ServerError.code
    if status >= HTTPStatus.INTERNAL_SERVER_ERROR:
        return handle_problem_error(ProblemError(ServerError))
    message = message_for_status(status)
    return problem_response(status, e.name, message.__name__ if message is not None else GENERIC_HTTP_CODE, e.description)


def handle_validation_error(e: PydanticValidationError) -> Response:
    errors = [{"field": ".".join(str(part) for part in error["loc"]), "detail": error["msg"]} for error in e.errors()]
    return handle_problem_error(ProblemError(ValidationError, errors=errors))


def v2_aware(v1_handler: Callable) -> Callable:
    """Wrap an error handler of the v1 API and the HTML pages so that v2 requests get a problem document instead."""
    def handler(e):
        return handle_http_exception(e) if is_v2_request() else v1_handler(e)
    return handler


def register_error_handlers(app) -> None:
    app.register_error_handler(ProblemError, handle_problem_error)
    app.register_error_handler(HTTPException, v2_aware(lambda e: e))
    app.validation_error_callback = _v2_validation_callback(app.validation_error_callback)


def _v2_validation_callback(default_callback: Callable) -> Callable:
    def callback(e):
        return handle_validation_error(e) if is_v2_request() else default_callback(e)
    return callback
