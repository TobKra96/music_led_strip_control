import numpy as np
import pytest

from mlsc.strip_pattern import (
    CHASE_PIXELS_PER_SECOND,
    COLOUR_STEP_SECONDS,
    MAX_SECONDS,
    Pattern,
    PatternChannel,
    PatternPlayer,
    render,
)

pytestmark = pytest.mark.unit

RED, GREEN, BLUE, WHITE, DARK = (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255), (0, 0, 0)


def pixel(frame, index):
    return tuple(int(value) for value in frame[:3, index])


def lit(frame):
    return [index for index in range(frame.shape[1]) if any(frame[:, index])]


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def test_the_colour_order_check_cycles_red_green_blue_white():
    colours = [pixel(render(Pattern.colour_order, 10, 5, step * COLOUR_STEP_SECONDS), 3) for step in range(5)]

    assert colours == [RED, GREEN, BLUE, WHITE, RED]


def test_the_colour_order_check_lights_the_whole_strip():
    frame = render(Pattern.colour_order, 10, 5, 0)

    assert frame.shape == (3, 10)
    assert lit(frame) == list(range(10))


def test_the_white_step_uses_the_white_channel_of_an_rgbw_strip():
    frame = render(Pattern.colour_order, 10, 5, 3 * COLOUR_STEP_SECONDS, white_channel=True)

    assert frame.shape == (4, 10)
    assert frame[:, 0].tolist() == [0, 0, 0, 255]


def test_the_markers_show_the_first_the_middle_and_the_last_pixel():
    frame = render(Pattern.markers, 10, 4, 0)

    assert lit(frame) == [0, 4, 9]
    assert (pixel(frame, 0), pixel(frame, 4), pixel(frame, 9)) == (RED, GREEN, BLUE)


def test_a_middle_outside_the_strip_is_clamped_onto_it():
    assert lit(render(Pattern.markers, 10, 99, 0)) == [0, 9]


def test_the_chase_moves_one_pixel_along_the_strip_and_wraps():
    positions = [lit(render(Pattern.chase, 10, 5, (step + 0.5) / CHASE_PIXELS_PER_SECOND)) for step in (0, 1, 2, 10)]

    assert positions == [[0], [1], [2], [0]]


def test_the_power_test_lights_every_pixel_white():
    frame = render(Pattern.power, 6, 3, 0, white_channel=True)

    assert frame[:, 2].tolist() == [255, 255, 255, 255]
    assert lit(frame) == list(range(6))


def test_a_strip_without_pixels_gives_an_empty_frame():
    assert render(Pattern.markers, 0, 0, 0).shape == (3, 0)


def make_player(channel, _clock, device_id="device_0", led_count=10, white_channel=False):
    return PatternPlayer(channel, device_id, led_count, 5, white_channel)


def test_there_is_no_frame_while_no_pattern_runs():
    clock = Clock()

    assert make_player(PatternChannel(clock), clock).frame() is None


def test_a_started_pattern_takes_over_the_strip():
    clock = Clock()
    channel = PatternChannel(clock)
    player = make_player(channel, clock)

    channel.start("device_0", Pattern.markers, 10)

    assert lit(player.frame()) == [0, 5, 9]


def test_the_pattern_animates_from_the_moment_it_started():
    clock = Clock()
    channel = PatternChannel(clock)
    player = make_player(channel, clock)

    clock.now += 50
    channel.start("device_0", Pattern.chase, 10)
    clock.now += 2.5 / CHASE_PIXELS_PER_SECOND

    assert lit(player.frame()) == [2]


def test_the_strip_is_restored_after_the_timeout():
    clock = Clock()
    channel = PatternChannel(clock)
    player = make_player(channel, clock)
    channel.start("device_0", Pattern.power, 5)

    clock.now += 4.9
    assert player.frame() is not None
    clock.now += 0.2
    assert player.frame() is None


def test_stopping_restores_the_strip_at_once():
    clock = Clock()
    channel = PatternChannel(clock)
    player = make_player(channel, clock)
    channel.start("device_0", Pattern.power, 30)

    channel.stop("device_0")

    assert player.frame() is None


def test_a_pattern_only_takes_over_its_own_device():
    clock = Clock()
    channel = PatternChannel(clock)
    channel.start("device_1", Pattern.power, 10)

    assert make_player(channel, clock, "device_0").frame() is None
    assert make_player(channel, clock, "device_1").frame() is not None


def test_starting_another_pattern_replaces_the_running_one():
    clock = Clock()
    channel = PatternChannel(clock)
    player = make_player(channel, clock)
    channel.start("device_0", Pattern.power, 10)

    channel.start("device_0", Pattern.markers, 10)

    assert lit(player.frame()) == [0, 5, 9]


def test_the_player_without_a_channel_never_takes_over():
    assert PatternPlayer(None, "device_0", 10, 5, False).frame() is None


def test_the_timeout_is_limited():
    clock = Clock()
    channel = PatternChannel(clock)
    player = make_player(channel, clock)

    channel.start("device_0", Pattern.power, 10_000)
    clock.now += MAX_SECONDS + 1

    assert player.frame() is None


def test_the_channel_runs_out_of_slots_only_for_new_devices():
    channel = PatternChannel(Clock())
    for index in range(PatternChannel.SLOTS):
        channel.start(f"device_{index}", Pattern.power, 10)

    channel.start("device_0", Pattern.markers, 10)
    with pytest.raises(RuntimeError, match="Too many"):
        channel.start("one_more", Pattern.power, 10)


def test_the_frame_is_an_array_of_the_strip_size():
    clock = Clock()
    channel = PatternChannel(clock)
    channel.start("device_0", Pattern.power, 10)

    frame = make_player(channel, clock, led_count=7).frame()

    assert isinstance(frame, np.ndarray)
    assert frame.shape == (3, 7)


def test_stopping_a_device_without_a_pattern_does_nothing():
    clock = Clock()
    channel = PatternChannel(clock)

    channel.stop("device_0")

    assert make_player(channel, clock).frame() is None
