from typing import Literal

from flask_openapi3 import APIBlueprint, Tag
from pydantic import BaseModel, Field

from mlsc import strip_pattern
from mlsc.api.v2.errors import READ_ERRORS, WRITE_ERRORS, ProblemError
from mlsc.api.v2.lookup import require_device
from mlsc.api.v2.security import api_login_required
from mlsc.strip_pattern import DEFAULT_SECONDS, MAX_SECONDS, Pattern
from mlsc.webserver.messages import ServerError

tag = Tag(name="Test Patterns", description="Temporary patterns that take over a strip to check its setup")
test_patterns_api = APIBlueprint("test_patterns_api_v2", __name__, url_prefix="/api/v2/devices", abp_tags=[tag])


class DevicePath(BaseModel):
    device_id: str = Field(description="Stable device id, e.g. `device_0`.")


class TestPatternBody(BaseModel):
    __test__ = False

    pattern: Literal[tuple(pattern.name for pattern in Pattern)] = Field(
        description="`colour_order`: the whole strip in red, green, blue and white, one after the other. "
                    "`markers`: the first pixel red, the middle one green, the last one blue. "
                    "`chase`: one pixel that runs along the strip. `power`: every pixel and colour at full brightness."
    )
    duration_seconds: int = Field(DEFAULT_SECONDS, ge=1, le=MAX_SECONDS, description="After this time the strip returns to its effect.")


class TestPatternOut(BaseModel):
    __test__ = False

    pattern: str
    duration_seconds: int


def _channel() -> strip_pattern.PatternChannel:
    if strip_pattern.channel is None:
        raise ProblemError(ServerError, "Test patterns are not available.")
    return strip_pattern.channel


@test_patterns_api.post("/<device_id>/test-pattern", summary="Show a Test Pattern on a device",
                        responses={"200": TestPatternOut, **WRITE_ERRORS})
@api_login_required
def start_test_pattern(path: DevicePath, body: TestPatternBody):
    """Takes over the strip of the device and returns it to its effect after `duration_seconds`. A running pattern is replaced."""
    require_device(path.device_id)
    _channel().start(path.device_id, Pattern[body.pattern], body.duration_seconds)
    return TestPatternOut(pattern=body.pattern, duration_seconds=body.duration_seconds).model_dump()


@test_patterns_api.delete("/<device_id>/test-pattern", summary="Stop the Test Pattern of a device",
                          responses={"204": None, **READ_ERRORS})
@api_login_required
def stop_test_pattern(path: DevicePath):
    """Returns the strip to its effect at once. Does nothing when no pattern runs."""
    require_device(path.device_id)
    _channel().stop(path.device_id)
    return "", 204
