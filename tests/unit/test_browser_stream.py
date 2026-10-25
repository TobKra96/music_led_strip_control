import queue

import pytest

from mlsc.browser_stream import IDLE_SECONDS, BrowserStream, BrowserStreamError

pytestmark = pytest.mark.unit

PCM = bytes(1280)


@pytest.fixture
def sink():
    return queue.Queue()


@pytest.fixture
def stream(sink, fake_clock):
    return BrowserStream(sink, fake_clock.time)


def kind_of(call, *args):
    with pytest.raises(BrowserStreamError) as error:
        call(*args)
    return error.value.kind


def test_opening_tells_the_audio_process_to_start_a_new_stream(stream, sink):
    stream_id = stream.open()

    assert stream_id
    assert sink.get_nowait() == ("reset",)


def test_chunks_of_the_open_stream_reach_the_audio_process(stream, sink):
    stream_id = stream.open()
    sink.get_nowait()

    stream.chunk(stream_id, 7, 48000, PCM)

    assert sink.get_nowait() == ("chunk", 7, 48000, PCM)


def test_a_second_streamer_is_refused(stream):
    stream.open()

    assert kind_of(stream.open) == "busy"


def test_a_chunk_needs_the_id_of_the_open_stream(stream):
    stream.open()

    assert kind_of(stream.chunk, "guess", 0, 48000, PCM) == "unknown_stream"


def test_five_seconds_without_chunks_release_the_claim(stream, fake_clock):
    old = stream.open()
    fake_clock.advance(IDLE_SECONDS)

    assert kind_of(stream.chunk, old, 0, 48000, PCM) == "unknown_stream"
    new = stream.open()
    assert new != old


def test_chunks_keep_the_claim_alive(stream, fake_clock):
    stream_id = stream.open()
    for sequence in range(4):
        fake_clock.advance(IDLE_SECONDS - 1)
        stream.chunk(stream_id, sequence, 48000, PCM)

    assert stream.active


def test_closing_releases_the_claim_at_once(stream):
    stream_id = stream.open()

    stream.close(stream_id)

    assert not stream.active
    stream.open()


def test_closing_with_another_id_keeps_the_claim(stream):
    stream.open()

    stream.close("other")

    assert stream.active


@pytest.mark.parametrize(("rate", "pcm"), [
    pytest.param(100, PCM, id="rate-too-low"),
    pytest.param(10_000_000, PCM, id="rate-too-high"),
    pytest.param(48000, b"", id="empty"),
    pytest.param(48000, bytes(3), id="odd-length"),
    pytest.param(48000, bytes(48000 * 2 + 2), id="over-a-second"),
])
def test_invalid_chunks_are_rejected(stream, sink, rate, pcm):
    stream_id = stream.open()
    sink.get_nowait()

    assert kind_of(stream.chunk, stream_id, 0, rate, pcm) == "invalid_chunk"
    assert sink.empty()


def test_a_full_queue_drops_the_chunk_instead_of_blocking(fake_clock):
    sink = queue.Queue(1)
    stream = BrowserStream(sink, fake_clock.time)
    stream_id = stream.open()

    stream.chunk(stream_id, 0, 48000, PCM)

    assert sink.qsize() == 1


def test_opening_clears_the_old_streams_chunks_so_the_reset_is_not_lost(fake_clock):
    sink = queue.Queue(1)
    stream = BrowserStream(sink, fake_clock.time)
    old = stream.open()
    stream.chunk(old, 0, 48000, PCM)
    stream.close(old)

    stream.open()

    assert sink.get_nowait() == ("reset",)


def test_a_non_ascii_stream_id_is_unknown_not_an_error(stream):
    stream.open()

    assert kind_of(stream.chunk, "straße", 0, 48000, PCM) == "unknown_stream"
