import json
import threading
from pathlib import Path
from queue import Queue

import pytest

from mlsc.api.v2 import register_api_v2
from mlsc.api.v2.errors import ProblemError
from mlsc.app import create_app
from mlsc.color_registry import registry
from mlsc.config_service import ConfigService
from mlsc.notification_enum import NotificationEnum
from mlsc.notification_item import NotificationItem
from mlsc.webserver.executer import Executer
from mlsc.webserver.messages import RefreshFailed

pytestmark = pytest.mark.integration

PROBLEM_JSON = "application/problem+json"
GRADIENT_EFFECT, GRADIENT_SETTING = next(
    (effect, setting) for effect, settings in registry().items() for setting, kind in settings.items() if kind == "gradient")
STOPS = [[255, 0, 0], [0, 0, 255]]


class _OutQueue:
    """Plays the NotificationService: records each refresh request and answers it."""

    def __init__(self, inbox, reply) -> None:
        self.inbox = inbox
        self.reply = reply
        self.requested = []

    def put(self, item):
        self.requested.append(item.device_id)
        self.inbox.put(NotificationItem(self.reply, item.device_id))


@pytest.fixture
def executer(config_dir, monkeypatch):  # ruff: ignore[unused-function-argument]
    monkeypatch.delattr(ConfigService, "current_instance", raising=False)
    inbox = Queue()
    instance = Executer(threading.Lock(), inbox, Queue(), Queue(), "fake")
    instance.entry_executer.notification_queue_out = _OutQueue(inbox, NotificationEnum.config_refresh_finished)
    monkeypatch.setattr(Executer, "instance", instance, raising=False)
    return instance


@pytest.fixture
def client(executer):  # ruff: ignore[unused-function-argument]
    app = create_app()
    app.config["AUTH_ENABLED"] = False
    app.secret_key = "test"  # ruff: ignore[hardcoded-password-string]
    register_api_v2(app)
    return app.test_client()


@pytest.fixture
def restarted(executer):
    return executer.entry_executer.notification_queue_out.requested


def use_gradient(client, executer, name, device_count=2):
    """Create `device_count` devices; the first and the last one use the gradient. Return the ids."""
    ids = [client.post("/api/v2/devices", json={}).get_json()["id"] for _ in range(device_count)]
    configs = executer.entry_executer._config["device_configs"]  # ruff: ignore[private-member-access]
    for device_id in (ids[0], ids[-1]):
        configs[device_id]["effects"][GRADIENT_EFFECT][GRADIENT_SETTING] = name
    return ids


def assert_problem(response, status, code):
    assert response.status_code == status
    assert response.mimetype == PROBLEM_JSON
    body = response.get_json()
    assert body["code"] == code
    return body


def test_the_list_holds_predefined_and_custom_entries_with_their_data(client):
    client.post("/api/v2/gradients", json={"name": "mine", "stops": STOPS})

    entries = {entry["name"]: entry for entry in client.get("/api/v2/gradients").get_json()}

    assert entries["mine"] == {"name": "mine", "stops": STOPS, "predefined": False}
    assert entries["spectral"]["predefined"] is True
    colours = {entry["name"]: entry for entry in client.get("/api/v2/colors").get_json()}
    assert colours["red"] == {"name": "red", "rgb": [255, 0, 0], "predefined": True}


def test_an_entry_is_created_read_and_deleted_by_name_ignoring_case_and_url_encoding(client):
    created = client.post("/api/v2/colors", json={"name": "Sea Foam", "rgb": [1, 2, 3]})

    assert created.status_code == 201
    assert created.get_json() == {"name": "Sea Foam", "rgb": [1, 2, 3], "predefined": False}
    assert client.get("/api/v2/colors/sea%20FOAM").get_json()["name"] == "Sea Foam"
    assert client.delete("/api/v2/colors/sea%20foam").status_code == 204
    assert_problem(client.get("/api/v2/colors/Sea%20Foam"), 404, "EntryNotFound")


def test_a_name_that_exists_in_any_case_is_a_conflict_but_a_colour_and_a_gradient_may_share_it(client):
    assert client.post("/api/v2/gradients", json={"name": "mine", "stops": STOPS}).status_code == 201

    assert_problem(client.post("/api/v2/gradients", json={"name": "MINE", "stops": STOPS}), 409, "AlreadyExists")
    assert_problem(client.post("/api/v2/gradients", json={"name": "Spectral", "stops": STOPS}), 409, "AlreadyExists")
    assert client.post("/api/v2/colors", json={"name": "mine", "rgb": [1, 1, 1]}).status_code == 201


@pytest.mark.parametrize("name", ["", "   ", "x" * 33, "bad/name", " padded", "dot."])
def test_a_bad_name_is_a_field_error(client, name):
    body = assert_problem(client.post("/api/v2/colors", json={"name": name, "rgb": [1, 2, 3]}), 422, "ValidationError")

    assert body["errors"][0]["field"] == "name"


@pytest.mark.parametrize("rgb", [[256, 0, 0], [-1, 0, 0], [1, 2], [1, 2, 3, 4]])
def test_a_bad_colour_is_a_field_error(client, rgb):
    body = assert_problem(client.post("/api/v2/colors", json={"name": "mine", "rgb": rgb}), 422, "ValidationError")

    assert body["errors"][0]["field"] == "rgb"


@pytest.mark.parametrize("stops", [[[1, 2, 3]], [[1, 2, 3]] * 17, [[1, 2, 3], [1, 2, 300]]])
def test_bad_stops_are_a_field_error(client, stops):
    body = assert_problem(client.post("/api/v2/gradients", json={"name": "mine", "stops": stops}), 422, "ValidationError")

    assert body["errors"][0]["field"] == "stops"


def test_patch_changes_only_the_sent_fields(client):
    client.post("/api/v2/gradients", json={"name": "mine", "stops": STOPS})
    three = [[1, 1, 1], [2, 2, 2], [3, 3, 3]]

    assert client.patch("/api/v2/gradients/mine", json={"stops": three}).get_json() == {"name": "mine", "stops": three, "predefined": False}
    assert_problem(client.patch("/api/v2/gradients/mine", json={}), 422, "ValidationError")


def test_patch_to_the_name_of_another_entry_is_a_conflict_but_a_case_change_of_its_own_name_is_fine(client):
    client.post("/api/v2/colors", json={"name": "one", "rgb": [1, 1, 1]})
    client.post("/api/v2/colors", json={"name": "two", "rgb": [2, 2, 2]})

    assert_problem(client.patch("/api/v2/colors/one", json={"name": "TWO"}), 409, "AlreadyExists")
    assert client.patch("/api/v2/colors/one", json={"name": "ONE"}).get_json()["name"] == "ONE"


def test_rename_rewrites_the_usages_and_restarts_exactly_the_using_devices(client, executer, restarted):
    client.post("/api/v2/gradients", json={"name": "mine", "stops": STOPS})
    ids = use_gradient(client, executer, "mine", device_count=3)

    renamed = client.patch("/api/v2/gradients/mine", json={"name": "yours"})

    assert renamed.get_json()["name"] == "yours"
    assert client.get("/api/v2/gradients/mine").status_code == 404
    usages = client.get("/api/v2/gradients/yours/usages").get_json()
    assert sorted(usage["target"] for usage in usages) == sorted([ids[0], ids[-1]])
    assert restarted == [ids[0], ids[-1]]
    stored = executer.entry_executer._config["device_configs"][ids[0]]["effects"][GRADIENT_EFFECT][GRADIENT_SETTING]  # ruff: ignore[private-member-access]
    assert stored == "yours"


def test_editing_an_unused_entry_restarts_nothing(client, restarted):
    client.post("/api/v2/gradients", json={"name": "mine", "stops": STOPS})
    client.patch("/api/v2/gradients/mine", json={"stops": STOPS[::-1]})

    assert restarted == []


def test_editing_a_used_entry_restarts_only_the_using_devices(client, executer, restarted):
    client.post("/api/v2/gradients", json={"name": "mine", "stops": STOPS})
    ids = use_gradient(client, executer, "mine", device_count=3)

    client.patch("/api/v2/gradients/mine", json={"stops": STOPS[::-1]})

    assert restarted == [ids[0], ids[-1]]


def test_the_config_is_saved_before_the_refresh(client, executer, monkeypatch):
    saved = []
    path = Path(executer.entry_executer.export_config_path)
    monkeypatch.setattr(
        executer.entry_executer, "refresh_devices_using", lambda *_: saved.append(json.loads(path.read_text(encoding="utf-8"))["colors"].get("mine")))

    client.post("/api/v2/colors", json={"name": "mine", "rgb": [1, 2, 3]})

    assert saved == [[1, 2, 3]]


def test_a_failed_refresh_is_reported_but_the_entry_stays_saved(client, executer, monkeypatch):
    def fail(*_):
        raise ProblemError(RefreshFailed)

    monkeypatch.setattr(executer.entry_executer, "refresh_devices_using", fail)

    assert_problem(client.post("/api/v2/colors", json={"name": "mine", "rgb": [1, 2, 3]}), 500, "RefreshFailed")
    assert client.get("/api/v2/colors/mine").get_json()["rgb"] == [1, 2, 3]


@pytest.mark.parametrize("method", ["patch", "delete"])
def test_predefined_entries_are_read_only(client, method):
    options = {"json": {"name": "other"}} if method == "patch" else {}

    assert_problem(getattr(client, method)("/api/v2/colors/RED", **options), 409, "PredefinedEntryReadOnly")
    assert client.get("/api/v2/colors/red").status_code == 200


def test_deleting_a_used_entry_is_blocked_and_names_the_usages(client, executer):
    client.post("/api/v2/gradients", json={"name": "mine", "stops": STOPS})
    ids = use_gradient(client, executer, "mine")

    body = assert_problem(client.delete("/api/v2/gradients/mine"), 409, "EntryInUse")

    assert {usage["target"] for usage in body["usages"]} == set(ids)
    assert body["usages"][0].keys() == {"target", "effect", "setting"}
    assert client.get("/api/v2/gradients/mine").status_code == 200


def test_usages_of_an_unused_entry_are_empty(client):
    client.post("/api/v2/gradients", json={"name": "mine", "stops": STOPS})

    assert client.get("/api/v2/gradients/mine/usages").get_json() == []
    assert_problem(client.get("/api/v2/gradients/none/usages"), 404, "EntryNotFound")


def test_duplicate_picks_the_next_free_copy_name_within_32_characters(client):
    first = client.post("/api/v2/gradients/spectral/duplicate", json={})
    second = client.post("/api/v2/gradients/spectral/duplicate", json={})

    assert first.status_code == 201
    assert first.get_json()["name"] == "spectral (copy)"
    assert first.get_json()["predefined"] is False
    assert second.get_json()["name"] == "spectral (copy 2)"
    client.post("/api/v2/colors", json={"name": "n" * 32, "rgb": [1, 2, 3]})
    assert client.post(f"/api/v2/colors/{'n' * 32}/duplicate", json={}).get_json()["name"] == "n" * 25 + " (copy)"


def test_a_copy_can_be_edited_and_renamed_like_any_custom_entry(client):
    copy_name = client.post("/api/v2/colors/red/duplicate", json={}).get_json()["name"]

    assert client.patch(f"/api/v2/colors/{copy_name}", json={"rgb": [9, 9, 9]}).get_json()["rgb"] == [9, 9, 9]
    assert client.patch(f"/api/v2/colors/{copy_name}", json={"name": "Dark Red"}).get_json()["name"] == "Dark Red"


def test_an_effect_setting_accepts_a_custom_gradient_and_rejects_an_unknown_name(client):
    device_id = client.post("/api/v2/devices", json={}).get_json()["id"]
    client.post("/api/v2/gradients", json={"name": "mine", "stops": STOPS})
    path = f"/api/v2/devices/{device_id}/effects/{GRADIENT_EFFECT}/settings"

    assert client.patch(path, json={GRADIENT_SETTING: "mine"}).status_code == 200
    assert client.get(path).get_json()[GRADIENT_SETTING] == "mine"
    assert client.patch(path, json={GRADIENT_SETTING: "nonexistent"}).status_code == 422
