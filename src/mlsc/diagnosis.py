"""Diagnosis: the structured result of an Output's health check, shared by the backends, the UI banner and `mlsc doctor`."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum


class Status(StrEnum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


_SEVERITY = {Status.OK: 0, Status.WARNING: 1, Status.ERROR: 2}


@dataclass(frozen=True)
class Diagnosis:
    status: Status
    message: str
    suggested_fix: str | None = None

    @classmethod
    def ok(cls, message: str) -> Diagnosis:
        return cls(Status.OK, message)

    @classmethod
    def warning(cls, message: str, suggested_fix: str | None = None) -> Diagnosis:
        return cls(Status.WARNING, message, suggested_fix)

    @classmethod
    def error(cls, message: str, suggested_fix: str | None = None) -> Diagnosis:
        return cls(Status.ERROR, message, suggested_fix)

    def to_event(self, device_id: str) -> dict:
        """The payload of the `diagnosis` event on `GET /api/v2/events`."""
        return {"device_id": device_id, "status": self.status.value, "message": self.message, "suggested_fix": self.suggested_fix}


def worst(diagnoses: Iterable[Diagnosis]) -> Diagnosis:
    """The most severe Diagnosis, the first of its severity. Healthy when there are none."""
    result = Diagnosis.ok("No problems found.")
    for diagnosis in diagnoses:
        if _SEVERITY[diagnosis.status] > _SEVERITY[result.status]:
            result = diagnosis
    return result
