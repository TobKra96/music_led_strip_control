"""Deprecation of the v1 `/api/*` paths: its own OpenAPI document and `Deprecation` response headers."""
import copy

from flask import Response, request
from flask_openapi3 import OpenAPI

from mlsc.api.v2.errors import API_V2_PREFIX

V1_PREFIX = "/api/"
DOCS_PATH = "/api/"
DEPRECATED_SINCE = "@1792800000"  # RFC 9745 date: 2026-10-24, the day v1 was frozen. There is no removal date in 3.x.
V1_DEPRECATION_NOTE = "**Deprecated.** These paths are frozen and kept for existing clients. Use `/api/v2/` (spec at `/api/v2/openapi.json`)."


def is_v1_path(path: str) -> bool:
    return path.startswith(V1_PREFIX) and not path.startswith(API_V2_PREFIX) and path != DOCS_PATH


def add_deprecation_headers(response: Response) -> Response:
    """Mark the response of a v1 route as deprecated. Unknown paths and everything outside v1 are left alone."""
    if request.url_rule is not None and is_v1_path(request.path):
        response.headers["Deprecation"] = DEPRECATED_SINCE
        response.headers.add("Link", f'<{API_V2_PREFIX}openapi.json>; rel="successor-version"')
        response.headers.add("Link", f'<{DOCS_PATH}>; rel="deprecation"; type="text/html"')
    return response


def register_v1_deprecation(app: OpenAPI) -> None:
    app.after_request(add_deprecation_headers)


def v1_spec(app: OpenAPI) -> dict:
    """Return the OpenAPI document restricted to the v1 paths, every operation marked deprecated."""
    spec = copy.deepcopy(app.api_doc)
    spec["paths"] = {path: item for path, item in spec["paths"].items() if is_v1_path(path)}
    for item in spec["paths"].values():
        for operation in item.values():
            operation["deprecated"] = True
    spec["info"]["description"] = f"{spec['info'].get('description', '')} {V1_DEPRECATION_NOTE}".strip()
    schemas = spec.get("components", {}).get("schemas", {})
    used = _referenced_schemas(spec["paths"], schemas)
    for name in set(schemas) - used:
        del schemas[name]
    return spec


def _referenced_schemas(node, schemas: dict) -> set[str]:
    """Return the names of the component schemas that `node` refers to, directly or through other schemas."""
    found: set[str] = set()
    pending = [node]
    while pending:
        current = pending.pop()
        if isinstance(current, dict):
            ref = current.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref.rsplit("/", 1)[1]
                if name not in found:
                    found.add(name)
                    pending.append(schemas.get(name, {}))
            pending.extend(current.values())
        elif isinstance(current, list):
            pending.extend(current)
    return found
