from flask_openapi3 import APIBlueprint, Tag
from pydantic import BaseModel, Field

from mlsc.api.v2.errors import READ_ERRORS, WRITE_ERRORS, Problem, ProblemError
from mlsc.api.v2.lookup import device_settings, require_device, require_patch, unwrap
from mlsc.api.v2.operations import OperationOut, accepted
from mlsc.api.v2.security import api_login_required
from mlsc.api.v2.settings_models import OutputPatch
from mlsc.output_setup import setup_options
from mlsc.webserver.executer import Executer
from mlsc.webserver.messages import ValidationError

tag = Tag(name="Output", description="Setup Wizard support: the choices for a strip and its Output, and applying them safely")
output_api = APIBlueprint("output_api_v2", __name__, url_prefix="/api/v2/devices", abp_tags=[tag])


class DevicePath(BaseModel):
    device_id: str = Field(description="Stable device id, e.g. `device_0`.")


class PowerOut(BaseModel):
    amps: float = Field(description="Draw at full white and the configured brightness.")
    watts: float
    warning: str | None = Field(description="Set when the Power Limit is enabled and the draw is above the supply. Advisory: nothing is dimmed.")


class DiagnosisOut(BaseModel):
    status: str = Field(description="`ok`, `warning` or `error`.")
    message: str
    suggested_fix: str | None


class OutputSetupOut(BaseModel):
    pi_model: str | None = Field(description="The Raspberry Pi model, `null` when MLSC does not run on a Pi.")
    backend: str | None = Field(description="The GPIO Backend of this host, `null` when there is none.")
    pin_channels: dict[str, int] = Field(description="The valid GPIO pins for this host, each with the channel that is derived from it.")
    experimental: str | None = Field(description="Notice shown instead of pins on a Pi 5, which has no supported driver.")
    power: PowerOut
    max_fps: int | None = Field(description="About 25,600 divided by the LED count.")
    split_suggestion: str | None = Field(description="Advice to split a long strip into several Devices.")
    diagnosis: DiagnosisOut = Field(description="The Diagnosis of the stored Output config, as `mlsc doctor` reports it.")


@output_api.get("/<device_id>/output/setup", summary="Get the choices of the Setup Wizard", responses={"200": OutputSetupOut, **READ_ERRORS})
@api_login_required
def get_output_setup(path: DevicePath):
    """Only valid pins are listed for the detected Pi model, and the channel follows from the pin."""
    return setup_options(device_settings(path.device_id))


@output_api.patch("/<device_id>/output", summary="Apply the strip and Output settings of a device",
                  responses={"202": OperationOut, **WRITE_ERRORS})
@api_login_required
def patch_output(path: DevicePath, body: OutputPatch):
    """Run as an Operation: the device restarts with the new settings, the Output is verified with `diagnose()` and a test frame on the strip.

    When that fails the previous config comes back, including the file, and the Device falls back to the Mock Output with a banner.
    The `channel` is derived from the pin. Values the hardware cannot use are `422`.
    """
    patch = require_patch(body.model_dump(exclude_unset=True))
    require_device(path.device_id)
    executer = Executer.instance.device_settings_executer
    errors = unwrap(executer.validate_output(path.device_id, patch))
    if errors:
        raise ProblemError(ValidationError, errors=errors)
    return accepted(unwrap(executer.apply_output(path.device_id, patch)))


@output_api.post("/<device_id>/output/retry", summary="Start the Output of a device again",
                 responses={"202": OperationOut, "401": Problem, "404": Problem, "415": Problem})
@api_login_required
def retry_output(path: DevicePath):
    """For the banner after a fallback to the Mock Output: applies the stored config again, retrying with a growing wait."""
    require_device(path.device_id)
    return accepted(unwrap(Executer.instance.device_settings_executer.retry_output(path.device_id)))
