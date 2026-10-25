import multiprocessing
from typing import ClassVar

import pytest

from mlsc.audio_capture import AudioCapture, create_capture
from mlsc.audio_process_service import AudioProcessService

pytestmark = pytest.mark.unit

FRAMES = 4


def capture_in_child(backend, results):
    """Run in the spawned child: only the backend name arrives, the capture is built here."""
    capture = create_capture(backend)
    capture.open(capture.default_device(), 44100, FRAMES)
    capture.feed()
    results.put((type(capture).__name__, capture.read(timeout=5)))
    capture.close()


def test_a_spawned_process_builds_its_own_capture_from_the_backend_name():
    context = multiprocessing.get_context("spawn")
    results = context.Queue()
    process = context.Process(target=capture_in_child, args=("fake", results))
    process.start()
    try:
        name, buffer = results.get(timeout=60)
    finally:
        process.join(timeout=60)

    assert name == "FakeCapture"
    assert buffer == bytes(FRAMES * 2)
    assert process.exitcode == 0


def test_only_plain_data_crosses_the_process_boundary(monkeypatch):
    from mlsc import main

    captured = {}

    class RecordingProcess:
        def __init__(self, target, args) -> None:
            captured[getattr(target, "__qualname__", repr(target))] = args

        def start(self):
            pass

        def terminate(self):
            pass

    monkeypatch.setenv("MLSC_AUDIO_BACKEND", "fake")
    monkeypatch.setattr(main, "Process", RecordingProcess)
    monkeypatch.setattr(main, "sleep", lambda _: (_ for _ in ()).throw(KeyboardInterrupt()))
    for service in ("ConfigService", "DeviceManager", "NotificationService", "Webserver"):
        monkeypatch.setattr(main, service, type(service, (), {"instance": staticmethod(lambda _lock: _Config()), "start": lambda *_: None}))

    main.Main().start()

    args = captured[AudioProcessService.start.__qualname__]
    assert "fake" in args
    assert not any(isinstance(arg, AudioCapture) for arg in args)


class _Config:
    config: ClassVar[dict] = {}

    @staticmethod
    def check_compatibility():
        pass
