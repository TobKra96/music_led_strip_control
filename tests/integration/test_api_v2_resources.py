import io
import json
import threading
from queue import Queue

import pytest

from mlsc.api.v2 import register_api_v2
from mlsc.app import create_app
from mlsc.config_service import ConfigService
from mlsc.webserver.executer import Executer
from mlsc.webserver.webserver import register_api_blueprints

pytestmark = pytest.mark.integration

PROBLEM_JSON = "application/problem+json"


@pytest.fixture
def executer(config_dir, monkeypatch):  # ruff: ignore[unused-function-argument]
    """Real executers over a config in a temporary dir; the queues collect what would reach the effect and device processes."""
    monkeypatch.delattr(ConfigService, "current_instance", raising=False)
    instance = Executer(threading.Lock(), Queue(), Queue(), Queue(), "fake")
    monkeypatch.setattr(Executer, "instance", instance, raising=False)
    return instance


@pytest.fixture
def client(executer):  # ruff: ignore[unused-function-argument]
    app = create_app()
    app.config["AUTH_ENABLED"] = False
    app.secret_key = "test"  # ruff: ignore[hardcoded-password-string]
    register_api_v2(app)
    return app.test_client()


def assert_problem(response, status, code):
    assert response.status_code == status
    assert response.mimetype == PROBLEM_JSON
    body = response.get_json()
    assert body["code"] == code
    return body


def test_devices_can_be_created_listed_and_deleted_by_id(client):
    created = client.post("/api/v2/devices", json={})

    assert created.status_code == 201
    device_id = created.get_json()["id"]
    assert [d["id"] for d in client.get("/api/v2/devices").get_json()] == [device_id]

    assert client.delete(f"/api/v2/devices/{device_id}").status_code == 204
    assert client.get("/api/v2/devices").get_json() == []
    assert_problem(client.delete(f"/api/v2/devices/{device_id}"), 404, "DeviceNotFound")


@pytest.fixture
def device_id(client):
    return client.post("/api/v2/devices", json={}).get_json()["id"]


def test_device_settings_are_patched_partially(client, device_id):
    before = client.get(f"/api/v2/devices/{device_id}/settings").get_json()

    patch = {"device_name": "Desk", "output": {"output_udp": {"udp_client_port": 9000}}}
    response = client.patch(f"/api/v2/devices/{device_id}/settings", json=patch)

    after = response.get_json()
    assert response.status_code == 200
    assert after["device_name"] == "Desk"
    assert after["output"]["output_udp"]["udp_client_port"] == 9000
    assert after["output"]["output_udp"]["udp_client_ip"] == before["output"]["output_udp"]["udp_client_ip"]
    assert after["led_count"] == before["led_count"]
    assert client.get(f"/api/v2/devices/{device_id}").get_json()["name"] == "Desk"


@pytest.mark.parametrize("patch", [{"led_count": "many"}, {"no_such_setting": 1}, {}])
def test_invalid_device_settings_change_nothing(client, device_id, patch):
    before = client.get(f"/api/v2/devices/{device_id}/settings").get_json()

    response = client.patch(f"/api/v2/devices/{device_id}/settings", json=patch)

    assert_problem(response, 422, "ValidationError")
    assert client.get(f"/api/v2/devices/{device_id}/settings").get_json() == before


def test_settings_of_an_unknown_device_are_a_404(client):
    assert_problem(client.get("/api/v2/devices/device_9/settings"), 404, "DeviceNotFound")
    assert_problem(client.patch("/api/v2/devices/device_9/settings", json={"fps": 30}), 404, "DeviceNotFound")


def test_effect_settings_are_patched_partially(client, device_id):
    url = f"/api/v2/devices/{device_id}/effects/effect_single/settings"
    before = client.get(url).get_json()

    response = client.patch(url, json={"color": "red"})

    assert response.get_json() == {**before, "color": "red"}


def test_effect_settings_reject_unknown_effects_settings_and_values(client, device_id):
    url = f"/api/v2/devices/{device_id}/effects/effect_single/settings"

    assert_problem(client.get(f"/api/v2/devices/{device_id}/effects/effect_nope/settings"), 404, "EffectNotFound")
    body = assert_problem(client.patch(url, json={"nope": 1}), 422, "ValidationError")
    assert body["errors"][0]["field"] == "nope"
    assert_problem(client.patch(url, json={"color": "not a colour"}), 422, "ValidationError")


def test_groups_hold_lists_of_device_ids(client, device_id):
    created = client.post("/api/v2/groups", json={"name": "Living room"})
    group_id = created.get_json()["id"]

    assert created.status_code == 201
    assert created.get_json() == {"id": group_id, "name": "Living room", "device_ids": []}

    members = client.put(f"/api/v2/groups/{group_id}/devices", json={"device_ids": [device_id]})

    assert members.get_json() == {"id": group_id, "name": "Living room", "device_ids": [device_id]}
    assert client.get("/api/v2/groups").get_json() == [members.get_json()]
    assert group_id in client.get(f"/api/v2/devices/{device_id}").get_json()["assigned_to"]

    assert client.put(f"/api/v2/groups/{group_id}/devices", json={"device_ids": []}).get_json()["device_ids"] == []


def test_group_membership_is_all_or_nothing(client, device_id):
    group_id = client.post("/api/v2/groups", json={"name": "A"}).get_json()["id"]

    body = assert_problem(client.put(f"/api/v2/groups/{group_id}/devices", json={"device_ids": [device_id, "device_9"]}), 404, "DeviceNotFound")

    assert "device_9" in body["detail"]
    assert client.get(f"/api/v2/groups/{group_id}").get_json()["device_ids"] == []


def test_groups_reject_duplicates_bad_names_and_unknown_ids(client):
    client.post("/api/v2/groups", json={"name": "A"})

    assert_problem(client.post("/api/v2/groups", json={"name": "A"}), 409, "GroupAlreadyExists")
    assert_problem(client.post("/api/v2/groups", json={"name": "bad/name"}), 422, "ValidationError")
    assert_problem(client.get("/api/v2/groups/group_9"), 404, "GroupNotFound")
    assert_problem(client.delete("/api/v2/groups/group_9"), 404, "GroupNotFound")


def test_deleting_a_group_removes_it_from_its_devices(client, device_id):
    group_id = client.post("/api/v2/groups", json={"name": "A"}).get_json()["id"]
    client.put(f"/api/v2/groups/{group_id}/devices", json={"device_ids": [device_id]})

    assert client.delete(f"/api/v2/groups/{group_id}").status_code == 204

    assert client.get("/api/v2/groups").get_json() == []
    assert client.get(f"/api/v2/devices/{device_id}").get_json()["assigned_to"] == {}


def test_a_device_has_an_active_effect_that_can_be_set(client, device_id, executer):
    url = f"/api/v2/devices/{device_id}/effect"
    response = client.put(url, json={"effect": "effect_single"})

    assert response.get_json() == {"device_id": device_id, "effect": "effect_single", "random_cycle_active": False}
    assert client.get(url).get_json()["effect"] == "effect_single"
    assert executer.effect_executer.effects_queue.get_nowait().effect_enum.name == "effect_single"


def test_setting_an_unknown_effect_is_a_validation_problem(client, device_id):
    assert_problem(client.put(f"/api/v2/devices/{device_id}/effect", json={"effect": "effect_nope"}), 422, "ValidationError")
    assert_problem(client.put("/api/v2/devices/device_9/effect", json={"effect": "effect_single"}), 404, "DeviceNotFound")


def test_the_bulk_effect_call_sets_the_given_devices_or_all(client):
    first, second, third = (client.post("/api/v2/devices", json={}).get_json()["id"] for _ in range(3))

    some = client.put("/api/v2/effect", json={"effect": "effect_fade", "device_ids": [first, second]})
    assert some.get_json() == [{"device_id": first, "effect": "effect_fade"}, {"device_id": second, "effect": "effect_fade"}]
    assert client.get(f"/api/v2/devices/{third}/effect").get_json()["effect"] != "effect_fade"

    everything = client.put("/api/v2/effect", json={"effect": "effect_bars"})
    assert {item["effect"] for item in everything.get_json()} == {"effect_bars"}
    assert len(everything.get_json()) == 3
    assert client.get("/api/v2/effect").get_json() == everything.get_json()


def test_the_bulk_effect_call_names_the_offending_device_and_applies_nothing(client, device_id):
    before = client.get("/api/v2/effect").get_json()

    body = assert_problem(client.put("/api/v2/effect", json={"effect": "effect_fade", "device_ids": [device_id, "device_9"]}), 404, "DeviceNotFound")

    assert "device_9" in body["detail"]
    assert client.get("/api/v2/effect").get_json() == before

    repeated = {"effect": "effect_fade", "device_ids": [device_id, device_id]}
    duplicate = assert_problem(client.put("/api/v2/effect", json=repeated), 422, "ValidationError")
    assert device_id in duplicate["errors"][0]["detail"]


def test_group_members_must_be_unique(client, device_id):
    group_id = client.post("/api/v2/groups", json={"name": "A"}).get_json()["id"]

    body = assert_problem(client.put(f"/api/v2/groups/{group_id}/devices", json={"device_ids": [device_id, device_id]}), 422, "ValidationError")

    assert device_id in body["errors"][0]["detail"]
    assert client.get(f"/api/v2/groups/{group_id}").get_json()["device_ids"] == []


@pytest.mark.parametrize("name", ["colors", "gradients", "logging-levels", "output-types", "effects", "audio-devices"])
def test_resource_lists_are_served(client, name):
    response = client.get(f"/api/v2/resources/{name}")

    assert response.status_code == 200
    assert isinstance(response.get_json(), dict)


def test_resource_lists_hold_the_known_values(client):
    assert "red" in client.get("/api/v2/resources/colors").get_json()
    assert set(client.get("/api/v2/resources/output-types").get_json()) == {"output_raspi", "output_udp"}
    assert "effect_single" in client.get("/api/v2/resources/effects").get_json()["non_music"]


def test_general_settings_are_patched_partially_and_validated(client):
    before = client.get("/api/v2/settings").get_json()

    response = client.patch("/api/v2/settings", json={"min_frequency": 60})

    assert response.get_json() == {**before, "min_frequency": 60}
    assert_problem(client.patch("/api/v2/settings", json={"min_frequency": "low"}), 422, "ValidationError")
    assert_problem(client.patch("/api/v2/settings", json={}), 422, "ValidationError")
    assert client.get("/api/v2/settings").get_json()["min_frequency"] == 60


@pytest.mark.usefixtures("device_id")
def test_deleting_the_settings_resets_the_configuration(client):
    client.patch("/api/v2/settings", json={"min_frequency": 60})

    response = client.delete("/api/v2/settings")

    assert response.get_json()["min_frequency"] == 50
    assert client.get("/api/v2/devices").get_json() == []


def test_config_can_be_exported_and_imported(client, device_id):
    exported = client.get("/api/v2/config")
    assert exported.status_code == 200
    document = exported.get_json()
    assert device_id in document["device_configs"]

    client.delete(f"/api/v2/devices/{device_id}")
    assert client.get("/api/v2/devices").get_json() == []

    assert client.put("/api/v2/config", json=document).status_code == 204
    assert [d["id"] for d in client.get("/api/v2/devices").get_json()] == [device_id]


def test_importing_an_invalid_config_is_a_400_and_changes_nothing(client, device_id):
    assert_problem(client.put("/api/v2/config", json={"nonsense": True}), 400, "InvalidConfigFile")

    assert [d["id"] for d in client.get("/api/v2/devices").get_json()] == [device_id]


@pytest.mark.parametrize("name", ["performance", "temperature", "services", "device-status", "version"])
@pytest.mark.usefixtures("device_id")
def test_system_information_is_served(client, name):
    response = client.get(f"/api/v2/system/{name}")

    assert response.status_code == 200
    assert response.get_json()


def test_system_device_status_lists_the_devices(client, device_id, monkeypatch, executer):
    monkeypatch.setattr(executer.system_info_executer, "check_device_status", lambda _address: True)

    assert [d["id"] for d in client.get("/api/v2/system/device-status").get_json()["devices"]] == [device_id]


def test_a_v1_config_import_is_seen_by_every_executer(client, executer, device_id):
    """The v1 import replaces the config; the device and effect executers must not keep serving the old one."""
    document = client.get("/api/v2/config").get_json()
    client.delete(f"/api/v2/devices/{device_id}")
    app = create_app()
    app.config["AUTH_ENABLED"] = False
    register_api_blueprints(app)
    v1 = app.test_client()

    imported = v1.post("/api/settings/configuration/file", data={"imported_config": (io.BytesIO(json.dumps(document).encode()), "config.json")})

    assert imported.status_code == 200
    assert [d["id"] for d in v1.get("/api/system/devices").get_json()] == [device_id]
    assert v1.get(f"/api/effect/active?device={device_id}").get_json()["device"] == device_id
    assert executer.effect_executer.get_active_effect(device_id)["device"] == device_id


@pytest.fixture
def group_of_two(client):
    first, second = (client.post("/api/v2/devices", json={}).get_json()["id"] for _ in range(2))
    group_id = client.post("/api/v2/groups", json={"name": "Desk"}).get_json()["id"]
    client.put(f"/api/v2/groups/{group_id}/devices", json={"device_ids": [first, second]})
    return group_id, [first, second]


def test_a_group_can_be_renamed_and_its_devices_follow(client, group_of_two):
    group_id, members = group_of_two

    response = client.patch(f"/api/v2/groups/{group_id}", json={"name": "Shelf"})

    assert response.status_code == 200
    assert response.get_json() == {"id": group_id, "name": "Shelf", "device_ids": members}
    assert client.get(f"/api/v2/devices/{members[0]}").get_json()["assigned_to"] == {group_id: "Shelf"}
    assert client.patch(f"/api/v2/groups/{group_id}", json={"name": "Shelf"}).status_code == 200


def test_renaming_a_group_rejects_taken_bad_and_unknown(client, group_of_two):
    group_id, _ = group_of_two
    other = client.post("/api/v2/groups", json={"name": "Other"}).get_json()["id"]

    assert_problem(client.patch(f"/api/v2/groups/{group_id}", json={"name": "Other"}), 409, "GroupAlreadyExists")
    assert_problem(client.patch(f"/api/v2/groups/{group_id}", json={"name": "bad/name"}), 422, "ValidationError")
    assert_problem(client.patch("/api/v2/groups/group_9", json={"name": "X"}), 404, "GroupNotFound")
    assert client.get(f"/api/v2/groups/{group_id}").get_json()["name"] == "Desk"
    assert client.get(f"/api/v2/groups/{other}").get_json()["name"] == "Other"


def test_setting_the_effect_of_a_group_changes_exactly_its_members(client, group_of_two):
    group_id, members = group_of_two
    outsider = client.post("/api/v2/devices", json={}).get_json()["id"]
    before = client.get(f"/api/v2/devices/{outsider}/effect").get_json()["effect"]

    response = client.put(f"/api/v2/groups/{group_id}/effect", json={"effect": "effect_fade"})

    expected = [{"device_id": d, "effect": "effect_fade"} for d in members]
    assert response.get_json() == {"group_id": group_id, "effect": "effect_fade", "devices": expected}
    assert client.get(f"/api/v2/groups/{group_id}/effect").get_json() == response.get_json()
    assert client.get(f"/api/v2/devices/{outsider}/effect").get_json()["effect"] == before


def test_the_group_effect_is_null_when_members_differ_or_there_are_none(client, group_of_two):
    group_id, members = group_of_two
    client.put(f"/api/v2/devices/{members[0]}/effect", json={"effect": "effect_fade"})
    client.put(f"/api/v2/devices/{members[1]}/effect", json={"effect": "effect_bars"})
    empty = client.post("/api/v2/groups", json={"name": "Empty"}).get_json()["id"]

    assert client.get(f"/api/v2/groups/{group_id}/effect").get_json()["effect"] is None
    assert client.get(f"/api/v2/groups/{empty}/effect").get_json() == {"group_id": empty, "effect": None, "devices": []}
    assert client.put(f"/api/v2/groups/{empty}/effect", json={"effect": "effect_fade"}).get_json()["devices"] == []


def test_the_group_effect_rejects_unknown_groups_and_effects(client, group_of_two):
    group_id, _ = group_of_two

    assert_problem(client.get("/api/v2/groups/group_9/effect"), 404, "GroupNotFound")
    assert_problem(client.put("/api/v2/groups/group_9/effect", json={"effect": "effect_fade"}), 404, "GroupNotFound")
    assert_problem(client.put(f"/api/v2/groups/{group_id}/effect", json={"effect": "effect_nope"}), 422, "ValidationError")


def test_importing_a_partial_config_is_refused_and_changes_nothing(client, device_id):
    body = assert_problem(client.put("/api/v2/config", json={"version": 4}), 400, "InvalidConfigFile")

    assert body["detail"]
    assert [d["id"] for d in client.get("/api/v2/devices").get_json()] == [device_id]
    assert client.get("/api/v2/settings").status_code == 200


def test_a_failing_import_leaves_the_live_config_and_the_file_untouched(client, executer, device_id, monkeypatch):
    def fail(_config):
        key = "device_configs"
        raise KeyError(key)

    monkeypatch.setattr(executer.general_settings_executer._config_instance, "make_compatible", fail)  # ruff: ignore[private-member-access]
    before = client.get("/api/v2/config").get_json()

    assert_problem(client.put("/api/v2/config", json={"version": 4}), 400, "InvalidConfigFile")

    assert client.get("/api/v2/config").get_json() == before
    assert [d["id"] for d in client.get("/api/v2/devices").get_json()] == [device_id]


def test_importing_an_unusable_config_names_the_reason(client):
    body = assert_problem(client.put("/api/v2/config", json={"version": 999}), 400, "InvalidConfigFile")

    assert "999" in body["detail"]


def test_config_can_be_patched_partially(client, device_id):
    response = client.patch("/api/v2/config", json={"general_settings": {"min_frequency": 60}})

    assert response.status_code == 200
    document = response.get_json()
    assert document["general_settings"]["min_frequency"] == 60
    assert device_id in document["device_configs"]
    assert client.get("/api/v2/settings").get_json()["min_frequency"] == 60
    assert client.get("/api/v2/config").get_json() == document


def test_an_invalid_config_patch_is_a_400_and_changes_nothing(client):
    before = client.get("/api/v2/config").get_json()

    assert_problem(client.patch("/api/v2/config", json={"version": 999}), 400, "InvalidConfigFile")

    assert client.get("/api/v2/config").get_json() == before


def test_an_empty_config_patch_is_a_422(client):
    assert_problem(client.patch("/api/v2/config", json={}), 422, "ValidationError")
