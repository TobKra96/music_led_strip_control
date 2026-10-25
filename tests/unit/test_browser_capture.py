import queue

import numpy as np
import pytest

from mlsc.audio_capture.browser import STALL_SECONDS, BrowserCapture, JitterBuffer, LinearResampler

pytestmark = pytest.mark.unit

RATE = 16000
# 40 ms chunks, and the 512-frame buffers (32 ms) the effects take.
CHUNK = RATE * 40 // 1000
FRAMES = 512


def chunk(value=1000, frames=CHUNK):
    return np.full(frames, value, dtype=np.int16)


@pytest.fixture
def jitter(fake_clock):
    return JitterBuffer(RATE, fake_clock.time)


def fill(jitter, chunks=3, first=0):
    for sequence in range(first, first + chunks):
        jitter.push(sequence, RATE, chunk())


def test_silence_until_the_buffer_holds_the_target_then_audio(jitter):
    fill(jitter, chunks=2)
    assert not jitter.pull(FRAMES).any()

    fill(jitter, chunks=1, first=2)

    assert (jitter.pull(FRAMES) == 1000).all()


def test_running_dry_fills_silence_counts_an_underrun_and_refills_before_resuming(jitter):
    fill(jitter, chunks=3)
    while jitter.buffered_seconds * RATE >= FRAMES:
        jitter.pull(FRAMES)

    assert not jitter.pull(FRAMES).any()
    assert jitter.underruns == 1
    # Waiting for the buffer to refill is one underrun, however long it takes.
    jitter.pull(FRAMES)
    assert jitter.underruns == 1

    fill(jitter, chunks=3, first=3)
    assert (jitter.pull(FRAMES) == 1000).all()


def test_a_missing_chunk_is_filled_with_silence_and_counted(jitter):
    jitter.push(0, RATE, chunk())
    jitter.push(2, RATE, chunk())

    assert jitter.underruns == 1
    assert jitter.buffered_seconds == pytest.approx(0.12)


def test_late_and_repeated_chunks_are_dropped(jitter):
    fill(jitter, chunks=3)
    before = jitter.buffered_seconds

    jitter.push(1, RATE, chunk())
    jitter.push(2, RATE, chunk())

    assert jitter.buffered_seconds == before


def test_overflow_drops_the_oldest_audio(jitter):
    for sequence in range(10):
        jitter.push(sequence, RATE, chunk((sequence + 1) * 1000))

    assert jitter.buffered_seconds <= 0.25
    pulled = jitter.pull(FRAMES)
    assert pulled[0] >= 5000


def test_a_new_stream_starts_its_numbering_over(jitter):
    fill(jitter, chunks=3)
    jitter.reset()

    jitter.push(0, RATE, chunk())

    assert jitter.buffered_seconds == pytest.approx(0.04)
    assert jitter.underruns == 0


def test_streaming_ends_when_chunks_stop(jitter, fake_clock):
    assert not jitter.streaming
    jitter.push(0, RATE, chunk())
    assert jitter.streaming

    fake_clock.advance(STALL_SECONDS)

    assert not jitter.streaming


def test_a_stopped_stream_is_silence_not_an_underrun(jitter, fake_clock):
    fill(jitter, chunks=3)
    fake_clock.advance(STALL_SECONDS)
    for _ in range(10):
        jitter.pull(FRAMES)

    assert jitter.underruns == 0


def test_resampling_keeps_the_pitch_and_the_length_across_chunks():
    resampler = LinearResampler()
    source_rate, target_rate = 48000, 44100
    t = np.arange(source_rate) / source_rate
    signal = (10000 * np.sin(2 * np.pi * 440 * t)).astype(np.int16)

    out = np.concatenate([resampler.process(signal[i:i + 1920], source_rate, target_rate) for i in range(0, source_rate, 1920)])

    assert abs(len(out) - target_rate) <= 1
    expected = 10000 * np.sin(2 * np.pi * 440 * np.arange(len(out)) / target_rate)
    assert np.abs(out - expected).max() < 100


def test_the_same_rate_passes_through():
    samples = chunk()
    assert LinearResampler().process(samples, RATE, RATE) is samples


@pytest.fixture
def capture(fake_clock):
    return BrowserCapture(None, fake_clock.time)


def open_capture(capture):
    delivered = []
    capture.open(capture.device(RATE), RATE, FRAMES, on_data=delivered.append)
    return delivered


def send(capture, sequence, value=1000):
    capture.ingest(("chunk", sequence, RATE, chunk(value).tobytes()))


def test_delivers_one_buffer_per_tick_silence_until_audio_arrives(capture):
    delivered = open_capture(capture)
    capture.tick()
    for sequence in range(3):
        send(capture, sequence)
    capture.tick()

    assert [np.frombuffer(b, dtype=np.int16).any() for b in delivered] == [False, True]
    assert all(len(b) == FRAMES * 2 for b in delivered)


def test_reports_streaming_and_unstable(capture, fake_clock):
    open_capture(capture)
    assert not capture.streaming

    for sequence in (0, 2, 4, 6):
        send(capture, sequence)

    assert capture.streaming
    assert capture.underruns == 3
    assert capture.unstable

    fake_clock.advance(11)
    assert not capture.unstable


def test_a_reset_message_starts_a_new_stream(capture):
    open_capture(capture)
    for sequence in range(3):
        send(capture, sequence)

    capture.ingest(("reset",))
    send(capture, 0)

    assert capture.underruns == 0


def test_messages_before_open_are_ignored(capture):
    send(capture, 0)
    capture.tick()

    assert capture.underruns == 0
    assert not capture.streaming


def test_the_thread_feeds_the_queue_into_buffers():
    source = queue.Queue()
    capture = BrowserCapture(source)
    delivered = []
    capture.open(capture.device(RATE), RATE, 160, on_data=delivered.append)
    try:
        for sequence in range(5):
            source.put(("chunk", sequence, RATE, chunk(1000).tobytes()))
        for _ in range(100):
            if any(np.frombuffer(b, dtype=np.int16).any() for b in delivered):
                break
            capture.read(timeout=0.05)
    finally:
        capture.close()

    assert any(np.frombuffer(b, dtype=np.int16).any() for b in delivered)


def test_a_buffer_larger_than_the_usual_target_is_still_served(fake_clock):
    capture = BrowserCapture(None, fake_clock.time)
    delivered = []
    capture.open(capture.device(8000), 8000, 4096, on_data=delivered.append)
    for sequence in range(14):
        capture.ingest(("chunk", sequence, 8000, np.full(320, 1000, dtype=np.int16).tobytes()))

    capture.tick()

    assert np.frombuffer(delivered[0], dtype=np.int16).all()


def test_opening_discards_chunks_left_in_the_queue():
    source = queue.Queue()
    source.put(("chunk", 0, RATE, chunk().tobytes()))
    capture = BrowserCapture(source)

    capture.open(capture.device(RATE), RATE, FRAMES)
    capture.close()

    assert source.empty()
