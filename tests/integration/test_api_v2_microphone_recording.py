import wave
from io import BytesIO
from types import SimpleNamespace

import numpy as np
import pytest

from mlsc.api.v2 import register_api_v2
from mlsc.app import create_app
from mlsc.audio_capture.fake import FakeCapture, sine_sweep
from mlsc.mic_level import MicLevel
from mlsc.mic_recording import MicRecording
from mlsc.webserver import auth
from mlsc.webserver.blueprints.microphone_settings_executer import MicrophoneSettingsExecuter
from mlsc.webserver.executer import Executer

pytestmark = pytest.mark.integration

RATE = 44100
TEST = "/api/v2/microphone/test"
RECORDING = "/api/v2/microphone/recording"


class Rig:
    """The microphone test against a fake capture that feeds the level and the recording like the audio process does."""

    def __init__(self, executer, fake_clock, monkeypatch) -> None:
        self.executer = executer
        self.level = MicLevel()
        self.recording = MicRecording()
        self.state = "ok"
        self.rate = RATE
        self.on_tick = None
        self.capture = FakeCapture(sine_sweep(440, 440))
        self.feeding = True
        self.silent = False
        self.capture.open(self.capture.default_device(), RATE, 4096, on_data=self._receive)
        executer.connect_audio(self.level, None, mic_recording=self.recording)
        monkeypatch.setattr(executer, "_clock", fake_clock.time)
        monkeypatch.setattr(executer, "_sleep", self._sleep)
        monkeypatch.setattr(executer, "get_status", lambda: {"state": self.state, "device": "Fake", "kind": "no_device"})
        self.fake_clock = fake_clock

    def _receive(self, data):
        if self.silent:
            data = bytes(len(data))
        self.level.update(data)
        self.recording.write(data, self.rate)

    def _sleep(self, seconds):
        if self.feeding:
            self.capture.feed()
        if self.on_tick:
            self.on_tick()
        self.fake_clock.sleep(seconds)


@pytest.fixture
def executer(monkeypatch):
    executer = object.__new__(MicrophoneSettingsExecuter)
    executer._config_instance = SimpleNamespace(config={"audio": {"source": "device"}})
    monkeypatch.setattr(Executer, "instance", SimpleNamespace(microphone_settings_executer=executer), raising=False)
    return executer


@pytest.fixture
def rig(executer, fake_clock, monkeypatch):
    return Rig(executer, fake_clock, monkeypatch)


@pytest.fixture
def client(executer):  # ruff: ignore[unused-function-argument]
    app = create_app()
    app.config["AUTH_ENABLED"] = False
    app.secret_key = "test"  # ruff: ignore[hardcoded-password-string]
    register_api_v2(app)
    return app.test_client()


def test_a_working_microphone_leaves_a_clip_that_the_endpoint_serves_as_wav(rig, client):  # ruff: ignore[unused-function-argument]
    result = client.post(TEST, json={}).get_json()
    response = client.get(RECORDING)

    assert result["result"] == "ok"
    assert result["recording"] is True
    assert (response.status_code, response.mimetype, response.headers["Cache-Control"]) == (200, "audio/wav", "no-store")
    with wave.open(BytesIO(response.data)) as clip:
        assert (clip.getframerate(), clip.getnchannels(), clip.getsampwidth()) == (RATE, 1, 2)
        assert clip.getnframes() > 0.5 * RATE
        assert np.abs(np.frombuffer(clip.readframes(clip.getnframes()), dtype=np.int16)).max() > 0


def test_every_kept_clip_gets_a_new_recording_id(rig, client):  # ruff: ignore[unused-function-argument]
    first = client.post(TEST, json={}).get_json()["recording_id"]
    second = client.post(TEST, json={}).get_json()["recording_id"]

    assert second > first


@pytest.mark.parametrize("state", ["error", "waiting", "starting"])
def test_a_failed_test_clears_the_old_clip(rig, client, state):
    client.post(TEST, json={})
    rig.state = state

    result = client.post(TEST, json={}).get_json()

    assert result["recording"] is False
    assert client.get(RECORDING).status_code == 404


def test_a_silent_test_clears_the_old_clip_and_keeps_the_hint(rig, client):
    client.post(TEST, json={})
    rig.silent = True
    rig.capture.feed()  # the live capture has long delivered silence when the next test starts

    result = client.post(TEST, json={}).get_json()

    assert (result["result"], result["recording"]) == ("silence", False)
    assert result["hint"]
    assert client.get(RECORDING).status_code == 404


def test_there_is_no_clip_before_any_test(rig, client):  # ruff: ignore[unused-function-argument]
    response = client.get(RECORDING)

    assert response.status_code == 404
    assert response.get_json()["code"] == "RecordingNotFound"


def test_a_rate_change_during_the_test_keeps_only_the_new_rate(rig, client):
    switched = []

    def switch():
        if rig.fake_clock.now > 1_000.0 + 1.0 and not switched:
            rig.rate = 48000
            switched.append(True)

    rig.on_tick = switch
    client.post(TEST, json={})

    with wave.open(BytesIO(client.get(RECORDING).data)) as clip:
        assert clip.getframerate() == 48000


def test_a_clip_that_is_too_short_is_not_kept(rig, client):
    rig.feeding = False

    result = client.post(TEST, json={}).get_json()

    assert result["recording"] is False


def test_a_second_test_while_one_runs_is_a_conflict_and_there_is_no_clip_meanwhile(rig, client):
    seen = []

    def during():
        if not seen:
            seen.append((client.post(TEST, json={}), client.get(RECORDING)))

    rig.on_tick = during
    client.post(TEST, json={})

    conflict, clip = seen[0]
    assert (conflict.status_code, conflict.get_json()["code"]) == (409, "TestInProgress")
    assert clip.status_code == 404


def test_the_recording_needs_a_login(rig, client, monkeypatch):  # ruff: ignore[unused-function-argument]
    client.application.config["AUTH_ENABLED"] = True
    monkeypatch.setattr(auth, "is_auth_enabled", lambda: True)
    monkeypatch.setattr(auth, "is_authenticated", lambda: False)

    response = client.get(RECORDING)

    assert (response.status_code, response.get_json()["code"]) == (401, "Unauthorized")
