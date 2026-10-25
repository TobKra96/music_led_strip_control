from __future__ import annotations

from abc import ABCMeta, abstractmethod
from http import HTTPStatus
from typing import Literal

from flask import Response, jsonify


class _MessageMeta(ABCMeta):
    """Metaclass for `_Message` class to access its attributes."""

    @property
    def message(cls: type[_Message]) -> str:
        return cls._message

    @property
    def code(cls: type[_Message]) -> int:
        return cls._code

    def __bool__(cls: type[_Message]) -> Literal[False]:
        return False

    def __repr__(cls: type[_Message]) -> str:
        return f'<{cls.__name__}>(message="{cls.message}", code={cls.code})'


class _Message(metaclass=_MessageMeta):
    """Base class for messages.

    Classes that inherit from this class should implement the following `private` attributes:
    ```
    _message: str
    _code: int
    ```
    Otherwise, the default values will be used.
    """

    _message: str = "Generic message."
    _code: int = 400

    @abstractmethod
    def __init__(self: _Message) -> None:
        pass

    @classmethod
    def as_dict(cls: _Message) -> dict:
        """Return the message as a dict.

        Example:
        -------
        ```json
        {"code": 400, "message": "Generic message.", "message_id": "_Message"}
        ```

        """
        return {
            "code": cls.code,
            "message": cls.message,
            "message_id": cls.__name__
        }

    @classmethod
    def as_response(cls: _Message) -> tuple[Response, int]:
        """Return the message as a `Flask` response with the status code."""
        return jsonify(cls.as_dict()), cls.code


# Messages are Sentinel values that can be returned by the API.

class OK(_Message):
    _message = "OK"
    _code = HTTPStatus.OK.value


class ConfigFileImported(OK):
    _message = "Config file imported."


class NotFound(_Message):
    _message = "Resource does not exist."
    _code = HTTPStatus.NOT_FOUND.value


class DeviceNotFound(NotFound):
    _message = "Device does not exist."


class GroupNotFound(NotFound):
    _message = "Group does not exist."


class OperationNotFound(NotFound):
    _message = "Operation does not exist."


class MigrationReportNotFound(NotFound):
    _message = "There is no migration report to show."


class MixerNotFound(NotFound):
    _message = "The microphone has no hardware gain."


class RecordingNotFound(NotFound):
    _message = "There is no recording of the microphone test."


class SettingNotFound(NotFound):
    _message = "Setting does not exist."


class EffectNotFound(NotFound):
    _message = "Effect does not exist."


class ConfigFileNotFound(NotFound):
    _message = "No config file selected."


class LimitReached(_Message):
    _message = "Resource limit reached."
    _code = HTTPStatus.CONFLICT.value


class DeviceLimitReached(LimitReached):
    _message = "Device limit reached. Maximum amount of devices is 100."


class GroupLimitReached(LimitReached):
    _message = "Group limit reached. Maximum amount of groups is 100."


class AlreadyExists(_Message):
    _message = "Resource already exists."
    _code = HTTPStatus.CONFLICT.value


class DeviceAlreadyExists(AlreadyExists):
    _message = "Device with this name already exists."


class GroupAlreadyExists(AlreadyExists):
    _message = "Group with this name already exists."


class BrowserStreamBusy(AlreadyExists):
    _message = "Another browser is already streaming its microphone."


class TestInProgress(AlreadyExists):
    _message = "A microphone test is already running."


class BrowserMicrophoneNotSelected(AlreadyExists):
    _message = "The Browser Microphone is not the selected audio source."


class DuplicateItem(AlreadyExists):
    _message = "Same item used more than once."
    _code = HTTPStatus.CONFLICT.value


class BadRequest(_Message):
    _message = "Bad request. Check the request data provided."
    _code = HTTPStatus.BAD_REQUEST.value


class InvalidConfigFile(BadRequest):
    _message = "Invalid config file."


class UnprocessableEntity(_Message):
    _message = "Unprocessable entity. Check the request body."
    _code = HTTPStatus.UNPROCESSABLE_ENTITY.value


class ValidationError(UnprocessableEntity):
    _message = "Request validation failed."


class HttpError(_Message):
    _message = "The request was rejected."


class MethodNotAllowed(_Message):
    _message = "Method not allowed for this resource."
    _code = HTTPStatus.METHOD_NOT_ALLOWED.value


class Unauthorized(_Message):
    _message = "Unauthorized."
    _code = HTTPStatus.UNAUTHORIZED.value


class UnsupportedMediaType(_Message):
    _message = "Unsupported media type."
    _code = HTTPStatus.UNSUPPORTED_MEDIA_TYPE.value


class StreamGone(_Message):
    _message = "The stream is not open or has expired."
    _code = HTTPStatus.GONE.value


class InvalidChunk(_Message):
    _message = "The audio chunk is invalid."
    _code = HTTPStatus.BAD_REQUEST.value


class InvalidPin(Unauthorized):
    _message = "Invalid PIN."


class TooManyAttempts(_Message):
    _message = "Too many failed attempts. Try again later."
    _code = HTTPStatus.TOO_MANY_REQUESTS.value


class ServerError(_Message):
    _message = "Internal server error."
    _code = HTTPStatus.INTERNAL_SERVER_ERROR.value


class TooManyStreams(_Message):
    _message = "Too many event streams."
    _code = HTTPStatus.SERVICE_UNAVAILABLE.value


def _subclasses(cls: type[_Message]) -> list[type[_Message]]:
    return [cls, *(sub for child in cls.__subclasses__() for sub in _subclasses(child))]


def error_codes() -> list[str]:
    """Return the `code` of every error message, sorted. This is the full vocabulary of the v2 API."""
    return sorted({m.__name__ for m in _subclasses(_Message)[1:] if m.code >= HTTPStatus.BAD_REQUEST})


_BUILTIN_HTTP_ERRORS = {
    m.code: m for m in (BadRequest, Unauthorized, NotFound, MethodNotAllowed, UnsupportedMediaType, UnprocessableEntity, ServerError)
}


def message_for_status(status: int) -> type[_Message] | None:
    """Return the message that names a built-in HTTP error, e.g. `NotFound` for 404."""
    return _BUILTIN_HTTP_ERRORS.get(status)
