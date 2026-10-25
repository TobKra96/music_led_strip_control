import numpy as np
import pytest

from mlsc.audio_capture.browser import STALL_SECONDS, BrowserCapture
from mlsc.audio_capture.fake import FULL_SCALE, FakeCapture, clipping, sine_sweep
from mlsc.audio_device import AudioDevice
from mlsc.mic_supervisor import MicSupervisor

pytestmark = pytest.mark.unit

BUILT_IN = AudioDevice(0, "Built-in Mic", 44100, "ALSA")
USB = AudioDevice(3, "USB Mic", 48000, "ALSA")


def audio(**overrides):
    return {"device_name": "USB Mic", "host_api": "ALSA", "sample_rate": None, "frames_per_buffer": 512, "gain": 1.0, **overrides}


@pytest.fixture
def capture():
    return FakeCapture(devices=[BUILT_IN, USB])


@pytest.fixture
def received():
    return []


@pytest.fixture
def reports():
    return []


@pytest.fixture
def supervisor(capture, received, reports, fake_clock):
    return MicSupervisor(capture, on_buffer=received.append, report=reports.append, clock=fake_clock.time)


def test_opens_the_stored_device_at_its_native_rate_and_is_ok_once_audio_arrives(supervisor, capture):
    supervisor.start(audio())
    assert supervisor.status["state"] == "starting"

    capture.feed()

    assert {key: supervisor.status[key] for key in ("state", "device", "host_api", "sample_rate", "fallback")} == {
        "state": "ok", "device": "USB Mic", "host_api": "ALSA", "sample_rate": 48000, "fallback": False}


@pytest.mark.parametrize("stored", [{"device_name": "Unplugged Mic"}, {"host_api": "JACK"}])
def test_a_missing_device_falls_back_to_the_system_default_with_a_warning(supervisor, capture, stored):
    supervisor.start(audio(**stored))
    capture.feed()

    assert (supervisor.status["state"], supervisor.status["device"], supervisor.status["fallback"]) == ("ok", "Built-in Mic", True)
    assert "not found" in supervisor.status["message"]


def test_no_stored_device_uses_the_system_default_without_a_warning(supervisor, capture):
    supervisor.start(audio(device_name=None, host_api=None))
    capture.feed()

    assert (supervisor.status["device"], supervisor.status["fallback"], supervisor.status["message"]) == ("Built-in Mic", False, None)


def test_software_gain_scales_the_samples_and_clips_at_full_scale(received, fake_clock):
    quiet = FakeCapture(source=sine_sweep(100, 2000, amplitude=0.25), devices=[USB])
    loud = FakeCapture(source=clipping(), devices=[USB])
    for capture in (quiet, loud):
        MicSupervisor(capture, on_buffer=received.append, clock=fake_clock.time).start(audio(gain=3.0))
        capture.feed()

    raw = FakeCapture(source=sine_sweep(100, 2000, amplitude=0.25), devices=[USB])
    raw.open(USB, 48000, 512)
    raw.feed()
    expected = np.frombuffer(raw.read(timeout=0), dtype=np.int16).astype(np.int32) * 3

    np.testing.assert_array_equal(np.frombuffer(received[0], dtype=np.int16), expected)
    assert np.abs(np.frombuffer(received[1], dtype=np.int16).astype(np.int32)).max() == FULL_SCALE


@pytest.mark.parametrize(("error", "kind"), [
    (PermissionError("[Errno 13] Permission denied"), "permission_denied"),
    (OSError("Error opening InputStream: Device unavailable [PaErrorCode -9985]"), "no_device"),
    (OSError("Invalid sample rate [PaErrorCode -9997]"), "open_failed"),
])
def test_a_failed_open_is_reported_with_its_kind_and_a_retry(supervisor, capture, reports, error, kind):
    capture.open_error = error

    supervisor.start(audio())

    assert {key: reports[-1][key] for key in ("state", "kind", "retry_in")} == {"state": "error", "kind": kind, "retry_in": 1.0}
    assert str(error) in reports[-1]["message"]


def test_retries_with_growing_backoff_until_the_device_opens(supervisor, capture, reports, fake_clock):
    capture.open_error = OSError("Device unavailable")
    supervisor.start(audio())

    retries = []
    for _ in range(7):
        fake_clock.advance(reports[-1]["retry_in"] - 0.01)
        supervisor.poll()
        assert reports[-1]["state"] == "error", "retried before the backoff passed"
        fake_clock.advance(0.01)
        supervisor.poll()
        retries.append(reports[-1]["retry_in"])

    assert retries == [2.0, 4.0, 8.0, 16.0, 30.0, 30.0, 30.0]

    capture.open_error = None
    fake_clock.advance(30)
    supervisor.poll()
    capture.feed()

    assert (reports[-1]["state"], reports[-1]["kind"], reports[-1]["retry_in"]) == ("ok", None, None)


def test_a_stream_that_stops_delivering_is_reported_as_gone_and_reopened(supervisor, capture, reports, fake_clock):
    supervisor.start(audio())
    capture.feed()
    fake_clock.advance(1.9)
    supervisor.poll()
    assert reports[-1]["state"] == "ok"

    capture.devices = [BUILT_IN]
    fake_clock.advance(0.2)
    supervisor.poll()

    assert (reports[-1]["state"], reports[-1]["kind"], reports[-1]["retry_in"]) == ("error", "no_device", 1.0)

    capture.devices = [BUILT_IN, USB]
    fake_clock.advance(1.0)
    supervisor.poll()
    capture.feed()

    assert (reports[-1]["state"], reports[-1]["device"], capture.opened[0]) == ("ok", "USB Mic", USB)


def test_a_device_that_opens_but_never_delivers_is_reported(supervisor, reports, fake_clock):
    supervisor.start(audio())
    fake_clock.advance(2.1)
    supervisor.poll()

    assert (reports[-1]["state"], reports[-1]["kind"]) == ("error", "no_device")


def test_the_status_counts_applied_configs_but_not_retries(supervisor, capture, reports, fake_clock):
    supervisor.start(audio())
    capture.open_error = OSError("Device unavailable")
    supervisor.start(audio(gain=2.0))
    fake_clock.advance(1.0)
    supervisor.poll()

    assert [report["restarts"] for report in reports] == [1, 2, 2, 2, 2]


def test_no_input_device_at_all_is_reported_as_no_device(received, reports, fake_clock):
    MicSupervisor(FakeCapture(devices=[]), on_buffer=received.append, report=reports.append, clock=fake_clock.time).start(audio())

    assert reports[-1] == {
        "state": "error", "device": None, "host_api": None, "sample_rate": None, "fallback": False,
        "message": "There is no input device.", "kind": "no_device", "retry_in": 1.0, "restarts": 1,
    }


# Browser Microphone

def browser_audio(**overrides):
    return audio(source="browser", device_name=None, host_api=None, sample_rate=16000, frames_per_buffer=512, **overrides)


@pytest.fixture
def browser(fake_clock):
    return BrowserCapture(None, fake_clock.time)


@pytest.fixture
def browser_supervisor(capture, browser, received, reports, fake_clock):
    return MicSupervisor(capture, on_buffer=received.append, report=reports.append, clock=fake_clock.time, browser=browser)


def stream_chunks(browser, sequences):
    for sequence in sequences:
        browser.ingest(("chunk", sequence, 16000, np.full(640, 1000, dtype=np.int16).tobytes()))


def test_the_browser_source_waits_for_the_browser_and_opens_no_device(browser_supervisor, capture):
    browser_supervisor.start(browser_audio())

    assert capture.opened is None
    assert {key: browser_supervisor.status[key] for key in ("state", "kind", "message", "device", "sample_rate")} == {
        "state": "waiting", "kind": "waiting_for_browser", "message": "Waiting for browser", "device": "Browser Microphone",
        "sample_rate": 16000}


def test_the_status_is_ok_while_the_browser_streams_and_waiting_again_when_it_stops(browser_supervisor, browser, fake_clock):
    browser_supervisor.start(browser_audio())

    stream_chunks(browser, [0])
    browser_supervisor.poll()
    assert browser_supervisor.status["state"] == "ok"
    assert browser_supervisor.status["message"] is None

    fake_clock.advance(STALL_SECONDS)
    browser_supervisor.poll()
    assert (browser_supervisor.status["state"], browser_supervisor.status["kind"]) == ("waiting", "waiting_for_browser")


def test_silence_still_reaches_the_effects_while_waiting_and_gain_applies(browser_supervisor, browser, received):
    browser_supervisor.start(browser_audio(gain=2.0))

    browser.tick()
    stream_chunks(browser, [0, 1, 2])
    browser.tick()

    assert not np.frombuffer(received[0], dtype=np.int16).any()
    assert (np.frombuffer(received[1], dtype=np.int16) == 2000).all()


def test_a_connection_that_keeps_running_dry_is_reported_as_unstable(browser_supervisor, browser):
    browser_supervisor.start(browser_audio())

    stream_chunks(browser, [0, 2, 4, 6])
    browser_supervisor.poll()

    assert browser_supervisor.status["unstable"] is True
    assert browser_supervisor.status["underruns"] == 3


def test_switching_back_to_a_device_closes_the_browser_and_opens_the_device(browser_supervisor, browser, capture):
    browser_supervisor.start(browser_audio())

    browser_supervisor.start(audio())
    capture.feed()

    assert browser_supervisor.status["device"] == "USB Mic"
    assert browser_supervisor.status["state"] == "ok"
    assert not browser.streaming


def test_without_a_browser_capture_the_device_stays_in_use(supervisor, capture):
    supervisor.start(browser_audio())
    capture.feed()

    assert supervisor.status["state"] == "ok"
