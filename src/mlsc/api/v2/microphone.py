from flask import Response, request
from flask_openapi3 import APIBlueprint, Tag
from pydantic import BaseModel, Field

from mlsc.api.v2.errors import BODY_ERRORS, WRITE_ERRORS, Problem, ProblemError
from mlsc.api.v2.lookup import require_patch
from mlsc.api.v2.operations import OperationOut, accepted
from mlsc.api.v2.security import api_login_required
from mlsc.api.v2.settings_models import MicrophonePatch
from mlsc.browser_stream import BrowserStreamError
from mlsc.mixer import MixerError
from mlsc.webserver.blueprints.microphone_settings_executer import FRAMES_PER_BUFFER_CHOICES
from mlsc.webserver.executer import Executer
from mlsc.webserver.messages import (
    BrowserMicrophoneNotSelected,
    BrowserStreamBusy,
    InvalidChunk,
    MixerNotFound,
    ServerError,
    StreamGone,
    ValidationError,
)

tag = Tag(name="Microphone", description="The audio input: device, gain, level test and hardware gain")
microphone_api = APIBlueprint("microphone_api_v2", __name__, url_prefix="/api/v2/microphone", abp_tags=[tag])


def _executer():
    return Executer.instance.microphone_settings_executer


class MicrophoneOut(BaseModel):
    source: str = Field(description="`device`, or `browser` for the Browser Microphone, which streams from a browser.")
    device_name: str | None = Field(description="Stored device name; `null` is the system default.")
    host_api: str | None = Field(description="Host API of the stored device; `null` matches any.")
    gain: float = Field(description="Software gain, applied to the samples before the effects.")
    sample_rate: int | None = Field(description="`null` is the native rate of the device.")
    frames_per_buffer: int
    min_frequency: float
    max_frequency: float
    min_volume_threshold: float


class AudioStatusOut(BaseModel):
    """Status of the audio stream. Also pushed as the `audio.status` event."""

    state: str | None = Field(
        default=None,
        description="`starting`, `ok`, `waiting` (for the Browser Microphone to stream) or `error`; missing before the audio process has started.",
    )
    device: str | None = Field(default=None, description="The device in use.")
    host_api: str | None = None
    sample_rate: int | None = None
    fallback: bool = Field(default=False, description="Whether the stored device was not found and the system default is used.")
    message: str | None = Field(default=None, description="What went wrong, or why the system default is used.")
    kind: str | None = Field(
        default=None,
        description="`no_device`, `permission_denied` or `open_failed` while `state` is `error`, `waiting_for_browser` while it is `waiting`.",
    )
    retry_in: float | None = Field(default=None, description="Seconds until the next try to open the device.")
    restarts: int = 0
    unstable: bool = Field(default=False, description="Whether the Browser Microphone connection keeps running dry, so audio drops out.")
    underruns: int = Field(default=0, description="How often the Browser Microphone ran dry when the status last changed.")


class AudioDeviceOut(BaseModel):
    source: str = Field(description="`device`, or `browser` for the Browser Microphone entry, which is always listed.")
    name: str
    host_api: str
    default_sample_rate: int = Field(description="The native rate.")
    sample_rates: list[int] = Field(description="Rates the device reports as supported.")
    monitor: bool = Field(description="Whether it is a Monitor Device, which carries played or remote audio.")
    default: bool = Field(description="Whether it is the system default.")


class AudioDevicesOut(BaseModel):
    devices: list[AudioDeviceOut]
    frames_per_buffer: list[int] = Field(description="The valid choices for `frames_per_buffer`.")


class MicrophoneTestOut(BaseModel):
    result: str = Field(description="`ok`, `silence`, `no_device`, `permission_denied`, `waiting_for_browser` or `error`.")
    message: str
    hint: str | None = Field(description="How to fix the problem.")
    peak: float = Field(description="Highest input level seen, 0 to 1.")
    device: str | None


class MixerOut(BaseModel):
    available: bool = Field(description="Whether the device has a hardware capture gain. Without one, use the software `gain`.")
    card: str | None
    control: str | None
    level: int | None = Field(description="Hardware capture level in percent.")


class MixerIn(BaseModel):
    level: int = Field(ge=0, le=100)


@microphone_api.get("", summary="Get the microphone settings", responses={"200": MicrophoneOut, "401": Problem})
@api_login_required
def get_microphone():
    return _executer().get_settings()


@microphone_api.patch("", summary="Change the microphone settings", responses={"202": OperationOut, **BODY_ERRORS})
@api_login_required
def patch_microphone(body: MicrophonePatch):
    """Run as an Operation: the audio stream restarts with the new settings and rolls back to the last working ones when no audio arrives.

    A `sample_rate` must be one the device supports, `frames_per_buffer` one of the listed choices.
    """
    patch = require_patch(body.model_dump(exclude_unset=True))
    errors = _executer().validate(patch)
    if errors:
        raise ProblemError(ValidationError, errors=errors)
    return accepted(_executer().apply(patch))


@microphone_api.get("/status", summary="Get the status of the audio stream", responses={"200": AudioStatusOut, "401": Problem})
@api_login_required
def get_status():
    return _executer().get_status()


@microphone_api.get("/devices", summary="List the audio input devices", responses={"200": AudioDevicesOut, "401": Problem})
@api_login_required
def get_devices():
    return {"devices": _executer().list_devices(), "frames_per_buffer": list(FRAMES_PER_BUFFER_CHOICES)}


@microphone_api.post("/test", summary="Test the microphone", responses={"200": MicrophoneTestOut, "401": Problem, "415": Problem})
@api_login_required
def test_microphone():
    """Watches the live input for two seconds and reports silence, no device or permission denied, with a hint to fix it."""
    return _executer().test()


@microphone_api.get("/mixer", summary="Get the hardware gain", responses={"200": MixerOut, "401": Problem})
@api_login_required
def get_mixer():
    try:
        return _executer().get_mixer()
    except MixerError as e:
        raise ProblemError(ServerError, str(e)) from e


@microphone_api.put("/mixer", summary="Set the hardware gain", responses={"200": MixerOut, **WRITE_ERRORS})
@api_login_required
def put_mixer(body: MixerIn):
    """`404` when the device has no hardware gain; use the software `gain` instead. Takes effect at once, without an Operation."""
    try:
        mixer = _executer().set_mixer(body.level)
    except MixerError as e:
        raise ProblemError(ServerError, str(e)) from e
    if mixer is None:
        raise ProblemError(MixerNotFound)
    return mixer


class BrowserStreamOut(BaseModel):
    stream_id: str = Field(description="Send with every chunk. Valid until the stream is closed or sends nothing for 5 seconds.")


class BrowserChunkQuery(BaseModel):
    sequence: int = Field(ge=0, description="Number of the chunk, counted from 0 for each stream. A gap is filled with silence.")
    sample_rate: int = Field(description="Sample rate of the chunk in Hz, the browser's own. The server resamples.")


class BrowserStreamPath(BaseModel):
    stream_id: str


STREAM_ERRORS = {"401": Problem, "409": Problem}


def _stream_error(e: BrowserStreamError) -> ProblemError:
    messages = {
        "busy": BrowserStreamBusy, "not_selected": BrowserMicrophoneNotSelected, "unknown_stream": StreamGone, "invalid_chunk": InvalidChunk,
    }
    return ProblemError(messages[e.kind], e.detail)


@microphone_api.post("/browser/stream", summary="Start streaming the Browser Microphone", responses={"201": BrowserStreamOut, **STREAM_ERRORS})
@api_login_required
def open_browser_stream():
    """Claims the single stream and returns its id. `409` while another browser streams or when the source is not `browser`.

    Then send about 40 ms of 16-bit little-endian mono PCM per request to the chunks endpoint.
    A stream that sends nothing for about 5 seconds is released. Nothing resumes by itself: open a new stream.
    """
    try:
        return {"stream_id": _executer().open_browser_stream()}, 201
    except BrowserStreamError as e:
        raise _stream_error(e) from e


@microphone_api.post(
    "/browser/stream/<stream_id>/chunks", summary="Send a chunk of the Browser Microphone",
    responses={"204": None, "400": Problem, "401": Problem, "410": Problem, "415": Problem},
)
@api_login_required
def post_browser_chunk(path: BrowserStreamPath, query: BrowserChunkQuery):
    """The body is raw 16-bit little-endian mono PCM, sent as `application/octet-stream`. `410` when the stream expired."""
    try:
        _executer().send_browser_chunk(path.stream_id, query.sequence, query.sample_rate, request.get_data())
    except BrowserStreamError as e:
        raise _stream_error(e) from e
    return Response(status=204)


@microphone_api.delete("/browser/stream/<stream_id>", summary="Stop streaming the Browser Microphone", responses={"204": None, "401": Problem})
@api_login_required
def close_browser_stream(path: BrowserStreamPath):
    """Releases the claim. Closing a stream that is already gone is not an error."""
    _executer().close_browser_stream(path.stream_id)
    return Response(status=204)
