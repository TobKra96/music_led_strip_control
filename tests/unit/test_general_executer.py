import pytest
from loguru import logger

from mlsc.audio_capture import AudioCaptureError
from mlsc.audio_capture.fake import FakeCapture
from mlsc.webserver.blueprints import general_executer
from mlsc.webserver.blueprints.general_executer import GeneralExecuter

pytestmark = pytest.mark.unit


def make_executer(backend="fake"):
    executer = GeneralExecuter.__new__(GeneralExecuter)
    executer._audio_backend = backend  # ruff: ignore[private-member-access]
    return executer


def test_the_device_list_uses_the_chosen_backend_and_closes_the_capture(monkeypatch):
    capture = FakeCapture()
    closed = []
    capture.close = lambda: closed.append(True)
    requested = []
    monkeypatch.setattr(general_executer, "create_capture", lambda backend: requested.append(backend) or capture)

    assert make_executer("miniaudio").get_audio_devices() == {0: "0 - Fake Mic - 44100 Hz", 1: "1 - Fake Monitor - 48000 Hz"}
    assert requested == ["miniaudio"]
    assert closed == [True]


def test_an_unavailable_backend_is_logged_as_a_warning_and_lists_nothing(monkeypatch):
    def unavailable(_backend):
        message = "no backend"
        raise AudioCaptureError(message)

    monkeypatch.setattr(general_executer, "create_capture", unavailable)
    messages = []
    sink = logger.add(messages.append, level="WARNING")
    try:
        assert make_executer().get_audio_devices() == {}
    finally:
        logger.remove(sink)

    assert "no backend" in str(messages[0])
