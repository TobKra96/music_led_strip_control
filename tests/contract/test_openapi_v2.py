import json
import os
from pathlib import Path

import pytest

from mlsc.api.v2 import register_api_v2
from mlsc.app import create_app

pytestmark = pytest.mark.contract

SNAPSHOT = Path(__file__).parent / "openapi_v2.json"
UPDATE_ENV = "UPDATE_OPENAPI_SNAPSHOT"


def fetch_spec():
    app = create_app()
    register_api_v2(app)
    return app.test_client().get("/api/v2/openapi.json").get_json()


GUARDED_SCHEMAS = {
    "Problem": "error contract",
    "LoginBody": "auth contract",
    "SessionOut": "auth contract",
    "PinSettings": "auth contract",
}


def describe_drift(actual, expected):
    lines = []
    actual_paths, expected_paths = set(actual["paths"]), set(expected["paths"])
    lines += [f"  added path: {path}" for path in sorted(actual_paths - expected_paths)]
    lines += [f"  removed path: {path}" for path in sorted(expected_paths - actual_paths)]
    lines += [f"  changed path: {path}" for path in sorted(actual_paths & expected_paths) if actual["paths"][path] != expected["paths"][path]]

    actual_schemas, expected_schemas = actual["components"]["schemas"], expected["components"]["schemas"]
    for name in sorted(set(actual_schemas) | set(expected_schemas)):
        if actual_schemas.get(name) != expected_schemas.get(name):
            note = f" ({GUARDED_SCHEMAS[name]})" if name in GUARDED_SCHEMAS else ""
            lines.append(f"  changed schema: {name}{note}")

    detail = "\n".join(lines) or "  (only non-path, non-schema parts changed)"
    command = f"{UPDATE_ENV}=1 uv run pytest tests/contract/test_openapi_v2.py"
    return f"The v2 API changed:\n{detail}\nIf intended, regenerate the snapshot with:\n  {command}"


def guard_against_regeneration_in_ci():
    if os.environ.get("CI") and os.environ.get(UPDATE_ENV):
        pytest.fail(f"{UPDATE_ENV} must not be set in CI: it would overwrite the snapshot instead of checking it.")


def test_v2_spec_matches_the_committed_snapshot():
    guard_against_regeneration_in_ci()
    spec = fetch_spec()

    if os.environ.get(UPDATE_ENV):
        SNAPSHOT.write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    expected = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert spec == expected, describe_drift(spec, expected)


def test_v2_spec_only_documents_v2_paths_and_problem_errors():
    spec = fetch_spec()

    assert spec["paths"]
    assert all(path.startswith("/api/v2/") for path in spec["paths"])
    assert "Problem" in spec["components"]["schemas"]
    assert "401" in spec["paths"]["/api/v2/devices"]["get"]["responses"]


def test_v2_spec_does_not_depend_on_the_python_version():
    spec = fetch_spec()
    descriptions = {response["description"] for item in spec["paths"].values() for op in item.values() for response in op["responses"].values()}

    assert "Unprocessable Content" in descriptions
    assert "Unprocessable Entity" not in descriptions


def test_v2_validation_errors_are_documented_as_problems():
    spec = fetch_spec()
    login = spec["paths"]["/api/v2/auth/session"]["get"]["responses"]["422"]

    assert login["content"]["application/json"]["schema"] == {"$ref": "#/components/schemas/Problem"}
    assert "ValidationErrorModel" not in spec["components"]["schemas"]


def test_v2_spec_documents_the_payload_of_every_event():
    spec = fetch_spec()
    events = spec["paths"]["/api/v2/events"]["get"]["x-events"]

    assert set(events) == {"device.status", "diagnosis", "mic.level", "wifi.state", "system.stats", "operation"}
    assert events["mic.level"]["schema"] == {"$ref": "#/components/schemas/MicLevelEvent"}
    assert events["mic.level"]["replayable"] is False
    assert events["device.status"]["replayable"] is True
    assert spec["components"]["schemas"]["MicLevelEvent"]["properties"]["level"]["maximum"] == 1


def test_v2_problem_schema_lists_every_code_of_the_messages_module():
    from mlsc.webserver.messages import error_codes

    code = fetch_spec()["components"]["schemas"]["Problem"]["properties"]["code"]

    assert code["enum"] == error_codes()
    assert {"InvalidPin", "TooManyAttempts", "TooManyStreams", "ValidationError", "NotFound", "MethodNotAllowed"} <= set(code["enum"])


def test_drift_message_names_the_regeneration_command_and_what_changed():
    expected = {"paths": {"/api/v2/a": {}, "/api/v2/gone": {}}, "components": {"schemas": {"Problem": {"x": 1}, "LoginBody": {"x": 1}, "Other": {}}}}
    actual = {"paths": {"/api/v2/a": {}, "/api/v2/new": {}}, "components": {"schemas": {"Problem": {"x": 2}, "LoginBody": {"x": 2}, "Other": {}}}}

    message = describe_drift(actual, expected)

    assert f"{UPDATE_ENV}=1 uv run pytest tests/contract/test_openapi_v2.py" in message
    assert "added path: /api/v2/new" in message
    assert "removed path: /api/v2/gone" in message
    assert "changed schema: Problem (error contract)" in message
    assert "changed schema: LoginBody (auth contract)" in message
    assert "Other" not in message


def test_snapshot_is_never_regenerated_in_ci(monkeypatch):
    monkeypatch.setenv("CI", "true")
    monkeypatch.setenv(UPDATE_ENV, "1")

    with pytest.raises(pytest.fail.Exception, match="CI"):
        guard_against_regeneration_in_ci()
