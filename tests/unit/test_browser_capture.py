import math
import queue
import threading

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


def test_running_dry_plays_silence_counts_an_underrun_and_resumes_with_the_next_full_buffer(jitter):
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


def test_a_short_pull_keeps_the_queued_audio_and_resumes_before_the_whole_target_is_back(jitter):
    fill(jitter, chunks=3)
    while jitter.buffered_seconds * RATE >= FRAMES:
        jitter.pull(FRAMES)
    left = jitter.buffered_seconds

    assert not jitter.pull(FRAMES).any()
    assert jitter.buffered_seconds == left

    # Resumes with 20 ms chunks coming in, before the whole 100 ms target is back.
    sequence = 3
    while not jitter.pull(FRAMES).any():
        jitter.push(sequence, RATE, chunk(1000, CHUNK // 2))
        sequence += 1
    assert jitter.buffered_seconds < 0.1


def test_a_missing_chunk_is_filled_with_silence_and_counted(jitter):
    jitter.push(0, RATE, chunk())
    jitter.push(2, RATE, chunk())

    assert jitter.underruns == 1
    # The lost chunk is bridged by 20 ms, not by a full 40 ms of silence.
    assert jitter.buffered_seconds == pytest.approx(0.10)


def test_a_missing_chunk_is_bridged_with_a_fade_out_from_the_last_sample(jitter):
    jitter.push(0, RATE, chunk())
    jitter.push(2, RATE, chunk(2000))

    bridge = jitter._buffer[CHUNK:CHUNK + RATE // 50]  # ruff: ignore[private-member-access]
    assert bridge[0] == 1000
    assert (np.diff(bridge.astype(int)) <= 0).all()
    assert abs(int(bridge[-1])) < 100


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
    assert pulled[-1] >= 5000


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


def test_a_stream_that_stopped_starts_over_with_the_full_target(jitter, fake_clock):
    fill(jitter, chunks=3)
    fake_clock.advance(STALL_SECONDS)
    for _ in range(10):
        jitter.pull(FRAMES)

    jitter.push(3, RATE, chunk())

    assert not jitter.pull(FRAMES).any()


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


def test_cutting_the_buffer_at_the_maximum_is_counted(jitter):
    for sequence in range(10):
        jitter.push(sequence, RATE, chunk())

    assert jitter.trims == 2


def test_cutting_the_buffer_keeps_most_of_it_and_does_not_click(jitter):
    wave = (8000 * np.sin(2 * np.pi * 200 * np.arange(CHUNK * 10) / RATE)).astype(np.int16)
    for sequence in range(10):
        jitter.push(sequence, RATE, wave[sequence * CHUNK:(sequence + 1) * CHUNK])

    assert 0.15 < jitter.buffered_seconds <= 0.25
    audio = jitter._buffer  # ruff: ignore[private-member-access]
    # A 200 Hz tone at this amplitude moves about 630 per sample; a bare splice would jump by thousands.
    assert np.abs(np.diff(audio.astype(int))).max() < 1500


def uneven(jitter, arrivals, frames=FRAMES, seconds=2.4, clock=None):
    """Feed 40 ms chunks of a sine at the given arrival times and pull a buffer every 32 ms; return the audio played."""
    wave = (8000 * np.sin(2 * np.pi * 200 * np.arange(int(RATE * (seconds + 1))) / RATE)).astype(np.int16)
    played, pending = [], sorted(arrivals)
    step = frames / RATE
    for tick in range(int(seconds / step)):
        now = tick * step
        clock.now = now
        while pending and pending[0][0] <= now:
            _, sequence = pending.pop(0)
            jitter.push(sequence, RATE, wave[sequence * CHUNK:(sequence + 1) * CHUNK])
        played.append(jitter.pull(frames))
    return np.concatenate(played)


def bursts():
    """Chunks every 40 ms, but every fourth one is held back 50 ms and the next arrives right behind it, in order."""
    arrivals, previous = [], 0.0
    for sequence in range(70):
        previous = max(previous, sequence * 0.04 + (0.05 if sequence % 4 == 3 else 0))
        arrivals.append((previous, sequence))
    return arrivals


def test_bursts_and_short_delays_play_smoothly(jitter, fake_clock):
    fake_clock.now = 0.0
    audio = uneven(jitter, bursts(), clock=fake_clock)

    started = np.flatnonzero(audio)[0]
    assert jitter.underruns <= 1
    assert jitter.trims == 0
    # Once audio plays, the only gaps are the first silence and at most the one underrun.
    zeros = np.flatnonzero(audio[started:] == 0)
    assert len(zeros) < 2 * FRAMES + 40
    # Nothing jumps further than the tone itself moves between two samples.
    assert np.abs(np.diff(audio[started:].astype(int))).max() < 8000


def test_the_buffer_survives_a_late_chunk_without_waiting_for_the_target_again(jitter, fake_clock):
    fake_clock.now = 0.0
    arrivals = [(sequence * 0.04, sequence) for sequence in range(60)]
    arrivals[30] = (30 * 0.04 + 0.12, 30)
    audio = uneven(jitter, arrivals, clock=fake_clock)

    silent = (audio == 0).sum() / RATE
    # Start-up wait (about the target) plus one short stretch, not a second wait of 100 ms.
    assert silent < 0.1 + 0.07 + 0.05
    assert jitter.underruns <= 1


def test_the_longest_wait_between_chunks_is_kept(jitter, fake_clock):
    jitter.push(0, RATE, chunk())
    fake_clock.advance(0.04)
    jitter.push(1, RATE, chunk())
    fake_clock.advance(0.3)
    jitter.push(2, RATE, chunk())
    fake_clock.advance(0.04)
    jitter.push(3, RATE, chunk())

    assert jitter.longest_gap == pytest.approx(0.3)


class TimerSource:
    """A chunk source on a fake clock whose waits end on a timer tick, like `queue.get(timeout=...)` on Windows (about 15.6 ms)."""

    def __init__(self, clock, rate, seconds, granularity=0.0, chunk_seconds=0.04, stall=None) -> None:
        self.clock, self.seconds, self.granularity = clock, seconds, granularity
        self.rate, self.chunk_seconds, self.stall = rate, chunk_seconds, stall
        self.sent = 0
        self.stop = threading.Event()

    def arrival(self, sequence):
        """When chunk `sequence` reaches the audio process: on time, or all held back by `stall` = (start, length)."""
        due = sequence * self.chunk_seconds
        if self.stall and self.stall[0] <= due < self.stall[0] + self.stall[1]:
            return self.stall[0] + self.stall[1]
        return due

    def get(self, timeout):
        wake = self.clock.now + (math.ceil(timeout / self.granularity) * self.granularity if self.granularity else timeout)
        arrives = self.arrival(self.sent)
        if arrives <= wake:
            self.clock.now = max(self.clock.now, arrives)
            message = ("chunk", self.sent, self.rate, chunk(1000, int(self.rate * self.chunk_seconds)).tobytes())
            self.sent += 1
            return message
        self.clock.now = wake
        if wake >= self.seconds:
            self.stop.set()
        raise queue.Empty

    @staticmethod
    def get_nowait():
        raise queue.Empty


def run_real_time(fake_clock, source, rate, frames):
    """Run the capture's own loop against `source` and return it with the audio it delivered, in seconds."""
    capture = BrowserCapture(None, fake_clock.time)
    delivered = []
    capture.open(capture.device(rate), rate, frames, on_data=delivered.append)
    capture._source = source  # ruff: ignore[private-member-access]
    capture._run(source.stop, frames / rate)  # ruff: ignore[private-member-access]
    return capture, delivered


@pytest.fixture
def clock_at_start(fake_clock):
    fake_clock.now = 0.0
    return fake_clock


def test_a_timer_that_wakes_on_time_delivers_audio_in_real_time_and_counts_nothing_lost(clock_at_start):
    source = TimerSource(clock_at_start, 44100, seconds=10)

    capture, delivered = run_real_time(clock_at_start, source, 44100, 512)

    assert len(delivered) * 512 / 44100 == pytest.approx(10, rel=0.01)
    assert capture.lost_seconds == pytest.approx(0, abs=0.02)
    assert capture.trims == 0


def test_ticks_that_fall_behind_are_counted_as_lost_time(clock_at_start):
    source = TimerSource(clock_at_start, 44100, seconds=10, granularity=0.015625)

    capture, _ = run_real_time(clock_at_start, source, 44100, 256)

    assert capture.lost_seconds > 1


@pytest.mark.xfail(strict=True, reason="#302: on a coarse timer (Windows, about 15.6 ms) the 5.8 ms ticks are late and never made up, "
                   "so less audio is played than arrives and the buffer is cut at its maximum again and again")
def test_small_buffers_are_played_in_real_time_on_a_coarse_timer(clock_at_start):
    source = TimerSource(clock_at_start, 44100, seconds=20, granularity=0.015625)

    capture, delivered = run_real_time(clock_at_start, source, 44100, 256)

    assert len(delivered) * 256 / 44100 >= 0.98 * 20
    assert capture.trims == 0


def test_a_stall_the_buffer_can_absorb_is_not_heard(clock_at_start):
    rate, frames = 44100, 512
    source = TimerSource(clock_at_start, rate, seconds=6, stall=(3.0, 0.06))

    capture, _ = run_real_time(clock_at_start, source, rate, frames)

    assert capture.underruns == 0
    assert capture.trims == 0


def test_a_stall_longer_than_the_buffer_runs_it_dry_once_and_the_catch_up_is_cut(clock_at_start):
    rate, frames = 44100, 512
    source = TimerSource(clock_at_start, rate, seconds=6, stall=(3.0, 0.25))

    capture, _ = run_real_time(clock_at_start, source, rate, frames)

    assert capture.underruns == 1
    assert capture.trims == 1
    assert capture.longest_gap >= 0.25
