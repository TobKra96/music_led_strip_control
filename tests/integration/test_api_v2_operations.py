import pytest

from mlsc import operations
from mlsc.api.v2 import register_api_v2
from mlsc.api.v2.operations import accepted
from mlsc.app import create_app
from mlsc.operations import OperationRegistry, RetryPolicy

pytestmark = pytest.mark.integration


@pytest.fixture
def registry(fake_clock, monkeypatch):
    registry = OperationRegistry(clock=fake_clock.time, sleep=fake_clock.sleep, publish=lambda *_: None, spawn=lambda target: target())
    monkeypatch.setattr(operations, "registry", registry)
    return registry


@pytest.fixture
def app(registry):  # ruff: ignore[unused-function-argument]
    app = create_app()
    app.config["AUTH_ENABLED"] = False
    app.secret_key = "test"  # ruff: ignore[hardcoded-password-string]
    register_api_v2(app)

    @app.post("/api/v2/_test/apply")
    def apply():
        return accepted(operations.registry.start("output", lambda: None, lambda: True, lambda: None, RetryPolicy(attempts=1)))

    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_a_slow_apply_answers_202_with_the_operation_to_poll(client):
    response = client.post("/api/v2/_test/apply", json={})

    body = response.get_json()
    assert response.status_code == 202
    assert response.headers["Location"] == f"/api/v2/operations/{body['id']}"

    polled = client.get(response.headers["Location"])
    assert polled.status_code == 200
    assert polled.get_json() == {"id": body["id"], "kind": "output", "state": "confirmed", "attempts": 1, "error": None}


def test_a_rolled_back_operation_reports_why(client, registry):
    operation = registry.run("output", lambda: None, lambda: False, lambda: None, RetryPolicy(attempts=1))

    body = client.get(f"/api/v2/operations/{operation.id}").get_json()

    assert body["state"] == "rolled_back"
    assert body["error"] == "Verification failed."


def test_polling_rolls_back_a_change_that_missed_its_deadline(client, registry, fake_clock):
    operation = registry.run("wifi", lambda: None, lambda: True, lambda: None, confirm_within=45)
    fake_clock.advance(46)

    assert client.get(f"/api/v2/operations/{operation.id}").get_json()["state"] == "rolled_back"


def test_an_unknown_operation_is_a_problem_document(client):
    response = client.get("/api/v2/operations/nope")

    assert response.status_code == 404
    assert response.mimetype == "application/problem+json"
    assert response.get_json()["code"] == "OperationNotFound"
