"""Payload models of the events on `GET /api/v2/events`, documented in the OpenAPI spec.

The producers of `diagnosis`, `wifi.state` and `operation` live with the Output, Wi-Fi and Operations slices and must publish these shapes.
"""
from pydantic import BaseModel, Field

from mlsc.api.v2.microphone import AudioStatusOut
from mlsc.api.v2.operations import OperationOut
from mlsc.webserver.sse import REPLAYABLE_EVENTS


class DeviceStatusEntry(BaseModel):
    id: str
    name: str
    connected: bool = Field(description="Whether the Device is reachable. A local Output is always reachable.")
    output_type: str = Field(description="The Output of the Device, so an Output change is a new event.")


class DeviceStatusEvent(BaseModel):
    """Sent when a Device goes up or down or its Output changes, and to a client that just connected."""

    devices: list[DeviceStatusEntry]


class SystemStatsEvent(BaseModel):
    """CPU, memory and temperature as reported by the host, sent every few seconds."""

    system: dict


class MicLevelEvent(BaseModel):
    """Peak input level of the audio capture, sent only when it changed."""

    level: float = Field(ge=0, le=1, description="0 is silence, 1 is full scale.")


class DiagnosisEvent(BaseModel):
    """The Diagnosis of an Output's health check."""

    device_id: str
    status: str
    message: str = Field(description="Human readable result.")
    suggested_fix: str | None


class WifiStateEvent(BaseModel):
    """The current Wi-Fi mode and connection."""

    mode: str = Field(description="`client` or `hotspot`.")
    connected: bool
    fallback: bool = Field(description="Whether a Setup Fallback hotspot is up.")


EVENT_PAYLOADS: dict[str, type[BaseModel]] = {
    "device.status": DeviceStatusEvent,
    "diagnosis": DiagnosisEvent,
    "mic.level": MicLevelEvent,
    "audio.status": AudioStatusOut,
    "wifi.state": WifiStateEvent,
    "system.stats": SystemStatsEvent,
    "operation": OperationOut,
}


def document_events(spec: dict) -> None:
    """Add the payload schemas to `spec` and list them on the events operation as `x-events`."""
    schemas = spec["components"]["schemas"]
    events = {}
    for name, model in EVENT_PAYLOADS.items():
        schema = model.model_json_schema(ref_template="#/components/schemas/{model}")
        schemas.update(schema.pop("$defs", {}))
        schemas[model.__name__] = schema
        events[name] = {"schema": {"$ref": f"#/components/schemas/{model.__name__}"}, "replayable": name in REPLAYABLE_EVENTS}
    spec["paths"]["/api/v2/events"]["get"]["x-events"] = events
