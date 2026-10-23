import subprocess

import pytest

from mlsc import main

pytestmark = pytest.mark.unit


class _FakePopen:
    def __init__(self, status) -> None:
        self._status = status

    def communicate(self):
        return (self._status + "\n", None)


@pytest.fixture
def linux(monkeypatch):
    monkeypatch.setattr(main, "platform", "linux")


def test_nothing_happens_off_linux(monkeypatch):
    monkeypatch.setattr(main, "platform", "win32")
    monkeypatch.setattr(main, "instance_already_running", lambda: pytest.fail("must not lock"), raising=False)

    main.exit_if_instance_running()


@pytest.mark.usefixtures("linux")
def test_free_lock_lets_the_server_start(monkeypatch):
    monkeypatch.setattr(main, "instance_already_running", lambda: False)

    main.exit_if_instance_running()


@pytest.mark.usefixtures("linux")
@pytest.mark.parametrize(("status", "expected"), [("active", "as a service"), ("inactive", "directly")])
def test_running_instance_exits_with_a_matching_message(monkeypatch, status, expected):
    monkeypatch.setattr(main, "instance_already_running", lambda: True)
    monkeypatch.setattr(subprocess, "Popen", lambda *_, **__: _FakePopen(status))

    with pytest.raises(SystemExit) as exc:
        main.exit_if_instance_running()

    assert expected in str(exc.value)


def test_run_exits_early_before_starting_the_server(monkeypatch):
    started = []
    monkeypatch.setattr(main, "exit_if_instance_running", lambda: (_ for _ in ()).throw(SystemExit("busy")))
    monkeypatch.setattr(main.Main, "start", lambda _: started.append(True))

    with pytest.raises(SystemExit):
        main.run()

    assert not started


def test_run_starts_the_server(monkeypatch):
    started = []
    monkeypatch.setattr(main, "exit_if_instance_running", lambda: None)
    monkeypatch.setattr(main.Main, "start", lambda _: started.append(True))

    assert main.run() == 0
    assert started == [True]
