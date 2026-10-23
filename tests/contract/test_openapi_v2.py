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


def test_v2_spec_matches_the_committed_snapshot():
    spec = fetch_spec()

    if os.environ.get(UPDATE_ENV):
        SNAPSHOT.write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    expected = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert spec == expected, f"The v2 API changed. If intended, regenerate the snapshot with {UPDATE_ENV}=1."


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
