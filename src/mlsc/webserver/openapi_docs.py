from copy import deepcopy
from functools import lru_cache
from pathlib import Path

import yaml
from flask_openapi3 import Tag

DOCS_DIR = Path(__file__).parent / "blueprints" / "docs"

TAG_DESCRIPTIONS = {
    "Auth": "Authentication and PIN management",
    "Effect": "Current effect controls",
    "Resources": "Static configuration data",
    "Settings": "Configuration management",
    "System": "Device and system information",
}


def doc(name: str) -> dict:
    """Route keyword arguments for the OpenAPI operation described in `blueprints/docs/<name>`.

    Each file is a title line, `---`, then the operation as OpenAPI YAML. The docs only feed the generated spec;
    requests are still validated by the JSON schemas in `mlsc/webserver/schemas`.
    """
    return deepcopy(_load(name))


@lru_cache
def _load(name: str) -> dict:
    text = (DOCS_DIR / name).read_text(encoding="utf-8").replace("\r\n", "\n")
    title, _, body = text.partition("\n---\n")
    operation = yaml.safe_load(body) or {}

    kwargs = {
        "summary": title.strip(),
        "tags": [Tag(name=tag, description=TAG_DESCRIPTIONS.get(tag)) for tag in operation.get("tags", [])],
        "responses": {str(status): response for status, response in operation.get("responses", {}).items()},
        "openapi_extensions": {key: operation[key] for key in ("parameters", "requestBody") if key in operation},
    }
    if "description" in operation:
        kwargs["description"] = operation["description"]
    if "deprecated" in operation:
        kwargs["deprecated"] = operation["deprecated"]
    return kwargs
