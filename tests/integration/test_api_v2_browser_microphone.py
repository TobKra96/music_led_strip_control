import queue
from types import SimpleNamespace

import numpy as np
import pytest

from mlsc.api.v2 import register_api_v2
from mlsc.app import create_app
from mlsc.webserver import auth
from mlsc.webserver.blueprints.microphone_settings_executer import MicrophoneSettingsExecuter
from mlsc.webserver.executer import Executer

pytestmark = pytest.mark.integration

STREAM = "/api/v2/microphone/browser/stream"
OCTET = {"Content-Type": "application/octet-stream"}
PCM = np.full(1920, 1000, dtype=np.int16).tobytes()


@pytest.fixture
def audio_queue():
    return queue.Queue()


@pytest.fixture
def executer(audio_queue, monkeypatch):
    executer = object.__new__(MicrophoneSettingsExecuter)
    executer._config_instance = SimpleNamespace(config={"audio": {"source": "browser"}})
    executer.connect_audio(None, None, audio_queue)
    monkeypatch.setattr(Executer, "instance", SimpleNamespace(microphone_settings_executer=executer), raising=False)
    return executer


@pytest.fixture
def client(executer):  # ruff: ignore[unused-function-argument]
    app = create_app()
    app.config["AUTH_ENABLED"] = False
    app.secret_key = "test"  # ruff: ignore[hardcoded-password-string]
    register_api_v2(app)
    return app.test_client()


def open_stream(client):
    return client.post(STREAM, json={})


def send(client, stream_id, sequence=0, rate=48000, body=PCM, headers=OCTET):
    return client.post(f"{STREAM}/{stream_id}/chunks?sequence={sequence}&sample_rate={rate}", data=body, headers=headers)


def test_opening_returns_a_stream_id_and_chunks_reach_the_audio_process(client, audio_queue):
    response = open_stream(client)
    stream_id = response.get_json()["stream_id"]

    sent = send(client, stream_id, sequence=3)

    assert (response.status_code, sent.status_code) == (201, 204)
    assert audio_queue.get_nowait() == ("reset",)
    assert audio_queue.get_nowait() == ("chunk", 3, 48000, PCM)


def test_a_second_streamer_gets_a_conflict(client):
    open_stream(client)

    response = open_stream(client)

    assert response.status_code == 409
    assert response.get_json()["code"] == "BrowserStreamBusy"


def test_opening_needs_the_browser_microphone_to_be_selected(client, executer):
    executer._config["audio"]["source"] = "device"

    response = open_stream(client)

    assert response.status_code == 409
    assert response.get_json()["code"] == "BrowserMicrophoneNotSelected"


def test_a_chunk_with_an_unknown_stream_id_is_gone(client):
    response = send(client, "unknown")

    assert response.status_code == 410
    assert response.get_json()["code"] == "StreamGone"


@pytest.mark.parametrize(("rate", "body"), [
    pytest.param(100, PCM, id="rate-too-low"), pytest.param(48000, bytes(3), id="odd-length"), pytest.param(48000, b"", id="empty"),
])
def test_invalid_chunks_are_rejected(client, rate, body):
    stream_id = open_stream(client).get_json()["stream_id"]

    response = send(client, stream_id, rate=rate, body=body)

    assert response.status_code == 400
    assert response.get_json()["code"] == "InvalidChunk"


def test_chunks_must_be_sent_as_octet_stream(client):
    stream_id = open_stream(client).get_json()["stream_id"]

    response = send(client, stream_id, headers={"Content-Type": "text/plain"})

    assert response.status_code == 415


def test_closing_frees_the_claim_and_is_idempotent(client):
    stream_id = open_stream(client).get_json()["stream_id"]

    first = client.delete(f"{STREAM}/{stream_id}")
    second = client.delete(f"{STREAM}/{stream_id}")

    assert (first.status_code, second.status_code) == (204, 204)
    assert open_stream(client).status_code == 201


def test_streaming_needs_a_login_when_the_pin_lock_is_on(executer, monkeypatch):  # ruff: ignore[unused-function-argument]
    monkeypatch.setattr(auth, "is_auth_enabled", lambda: True)
    monkeypatch.setattr(auth, "is_authenticated", lambda: False)
    app = create_app()
    app.secret_key = "test"  # ruff: ignore[hardcoded-password-string]
    register_api_v2(app)
    client = app.test_client()

    assert open_stream(client).status_code == 401
    assert send(client, "any").status_code == 401


def test_the_device_list_always_contains_the_browser_microphone(executer, monkeypatch):
    monkeypatch.setattr(executer, "_audio_backend", "fake", raising=False)
    devices = executer.list_devices()

    browser = [d for d in devices if d["source"] == "browser"]
    assert [d["name"] for d in browser] == ["Browser Microphone"]
    assert all(d["source"] == "device" for d in devices if d not in browser)


def test_selecting_the_browser_source_needs_no_device_checks(executer, monkeypatch):
    executer._config["audio"] = {
        "source": "device", "device_name": "Gone", "host_api": None, "gain": 1.0, "sample_rate": 12345,
        "frames_per_buffer": 512, "min_frequency": 20, "max_frequency": 20000, "min_volume_threshold": 0.0}
    monkeypatch.setattr(executer, "_audio_backend", "fake", raising=False)

    assert executer.validate({"source": "browser"}) == []
    # Back to a device, the stored rate has to suit it again.
    assert [e["field"] for e in executer.validate({"source": "device", "device_name": None})] == ["sample_rate"]


def test_the_microphone_test_says_when_no_browser_streams(executer, fake_clock, monkeypatch):
    monkeypatch.setattr(executer, "_clock", fake_clock.time)
    monkeypatch.setattr(executer, "_sleep", fake_clock.sleep)
    monkeypatch.setattr(executer, "get_status", lambda: {"state": "waiting", "device": "Browser Microphone"})

    result = executer.test()

    assert result["result"] == "waiting_for_browser"
    assert "Stream from this browser" in result["hint"]
