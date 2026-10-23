import json
from types import SimpleNamespace

import pytest

from mlsc.api.v2 import register_api_v2
from mlsc.app import create_app
from mlsc.audio_capture.fake import FakeCapture, clipping, silence
from mlsc.mic_level import MicLevel
from mlsc.webserver import sse
from mlsc.webserver.blueprints.system_info_executer import SystemInfoExecuter
from mlsc.webserver.executer import Executer
from mlsc.webserver.mic_level_publisher import MicLevelPublisher
from mlsc.webserver.sse import EventBroker
from mlsc.webserver.status_publisher import create_status_publisher

pytestmark = pytest.mark.integration


@pytest.fixture
def broker(monkeypatch):
    local = EventBroker()
    monkeypatch.setattr(sse, "broker", local)
    return local


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(Executer, "instance", SimpleNamespace(), raising=False)
    app = create_app()
    app.config["AUTH_ENABLED"] = False
    register_api_v2(app)
    return app.test_client()


def read_events(stream, count):
    return [next(stream).decode() for _ in range(count)]


def parse(chunk):
    fields = dict(line.split(": ", 1) for line in chunk.strip().splitlines())
    return fields["event"], json.loads(fields["data"]), fields.get("id")


def open_capture(source, level):
    capture = FakeCapture(source)
    capture.open(capture.default_device(), 44100, 64, on_data=level.update)
    return capture


def mic_publisher(level):
    return MicLevelPublisher(sse.broker.publish, sse.broker.has_subscribers, level.read)


@pytest.mark.usefixtures("broker")
def test_mic_level_follows_the_captured_audio_on_the_stream(client):
    level = MicLevel()
    capture = open_capture(clipping(), level)
    response = client.get("/api/v2/events")

    capture.feed()
    mic_publisher(level).poll()

    assert parse(read_events(response.response, 2)[1]) == ("mic.level", {"level": 1.0}, None)
    response.close()


def test_mic_level_is_quiet_for_silence_and_is_not_repeated_while_unchanged(client, broker):
    level = MicLevel()
    capture = open_capture(silence(), level)
    publisher = mic_publisher(level)
    response = client.get("/api/v2/events")

    capture.feed()
    publisher.poll()
    publisher.poll()
    broker.publish("wifi.state", {"mode": "hotspot"})

    events = [parse(chunk)[0] for chunk in read_events(response.response, 3)]
    assert events == ["ready", "mic.level", "wifi.state"]
    response.close()


def test_mic_level_is_not_published_while_nobody_listens(broker):
    level = MicLevel()
    open_capture(clipping(), level).feed()
    published = []

    MicLevelPublisher(lambda event, _data: published.append(event), broker.has_subscribers, level.read).poll()

    assert published == []


@pytest.mark.usefixtures("broker")
def test_device_status_is_replayed_after_last_event_id(client):
    states = [{"devices": [{"id": "device_0", "name": "Desk", "connected": True, "output_type": "output_dummy"}]}, {"devices": [{"id": "device_0", "name": "Desk", "connected": True, "output_type": "output_udp"}]}]
    reads = iter(states)
    system_info = SimpleNamespace(
        get_device_status_event=lambda: next(reads),
        get_system_info_performance=lambda: {"system": {"cpu_info": {"percent": 1.0}}},
        get_system_info_temperature=lambda: {"system": {"raspi": {"celsius": 40.0}}},
    )
    publisher = create_status_publisher(system_info)
    first = client.get("/api/v2/events")
    publisher.poll()
    publisher.poll()
    first_chunks = read_events(first.response, 5)
    first.close()
    first_id = parse(first_chunks[1])[2]

    second = client.get("/api/v2/events", headers={"Last-Event-ID": first_id})
    chunks = read_events(second.response, 2)

    assert parse(chunks[1])[:2] == ("device.status", states[1])
    second.close()


@pytest.mark.usefixtures("broker")
def test_system_stats_arrive_on_the_stream(client):
    system_info = SimpleNamespace(
        get_device_status_event=lambda: {"devices": []},
        get_system_info_performance=lambda: {"system": {"cpu_info": {"percent": 3.0}, "memory_info": {"percent": 50.0}}},
        get_system_info_temperature=lambda: {"system": {"raspi": {"celsius": 41.0}}},
    )
    response = client.get("/api/v2/events")

    create_status_publisher(system_info).poll()

    events = {parse(chunk)[0]: parse(chunk)[1] for chunk in read_events(response.response, 3)}
    assert events["system.stats"] == {"system": {"cpu_info": {"percent": 3.0}, "memory_info": {"percent": 50.0}, "raspi": {"celsius": 41.0}}}
    response.close()


def test_device_status_event_names_the_output_of_each_device():
    executer = SystemInfoExecuter.__new__(SystemInfoExecuter)
    executer._config_instance = SimpleNamespace(config={"device_configs": {"device_0": {"device_name": "Desk", "output_type": "output_dummy"}}})

    assert executer.get_device_status_event() == {"devices": [{"name": "Desk", "id": "device_0", "connected": True, "output_type": "output_dummy"}]}


def test_an_output_change_is_a_new_device_status_event(client, broker):
    output = {"type": "output_dummy"}
    executer = SystemInfoExecuter.__new__(SystemInfoExecuter)
    executer._config_instance = SimpleNamespace(config={"device_configs": {"device_0": {"device_name": "Desk", "output_type": output["type"]}}})
    system_info = SimpleNamespace(
        get_device_status_event=executer.get_device_status_event,
        get_system_info_performance=lambda: {"system": {}},
        get_system_info_temperature=lambda: {"system": {}},
    )
    publisher = create_status_publisher(system_info)
    response = client.get("/api/v2/events")

    publisher.poll()
    executer._config_instance.config["device_configs"]["device_0"]["output_type"] = "output_mock"
    publisher.poll()

    statuses = [parse(chunk)[1] for chunk in read_events(response.response, 5) if "event: device.status" in chunk]
    assert [status["devices"][0]["output_type"] for status in statuses] == ["output_dummy", "output_mock"]
    response.close()
