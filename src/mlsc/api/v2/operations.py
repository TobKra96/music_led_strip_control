from flask import Response, jsonify
from flask_openapi3 import APIBlueprint, Tag
from pydantic import BaseModel, Field

from mlsc import operations
from mlsc.api.v2.errors import API_V2_PREFIX, READ_ERRORS, ProblemError
from mlsc.api.v2.security import api_login_required
from mlsc.operations import Operation, OperationState
from mlsc.webserver.messages import OperationNotFound

tag = Tag(name="Operations", description="Tracked changes that can take time or fail")
operations_api = APIBlueprint("operations_api_v2", __name__, url_prefix="/api/v2/operations", abp_tags=[tag])


class OperationPath(BaseModel):
    operation_id: str = Field(description="Id from the `202` response or the `operation` event.")


class OperationOut(BaseModel):
    id: str
    kind: str = Field(description="What is being changed, e.g. `output`.")
    state: OperationState
    attempts: int = Field(description="How many times the change was applied so far.")
    error: str | None = Field(description="Why the change was rolled back or failed.")


def accepted(operation: Operation) -> tuple[Response, int, dict]:
    """Return the `202` answer, with the Location of the Operation, for an endpoint whose change runs as an Operation."""
    return jsonify(operation.as_dict()), 202, {"Location": f"{API_V2_PREFIX}operations/{operation.id}"}


@operations_api.get("/<operation_id>", summary="Get an operation", responses={"200": OperationOut, **READ_ERRORS})
@api_login_required
def get_operation(path: OperationPath):
    """Poll the state of a change: `pending`, `confirmed`, `rolled_back` or `failed`. The same objects are pushed as `operation` events."""
    operation = operations.registry.get(path.operation_id)
    if operation is None:
        raise ProblemError(OperationNotFound, f"Operation {path.operation_id} does not exist.")
    return operation.as_dict()
