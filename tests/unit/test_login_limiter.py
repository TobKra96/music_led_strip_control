import pytest

from mlsc.api.v2.throttle import FREE_ATTEMPTS, MAX_DELAY_SECONDS, MAX_TRACKED_CLIENTS, LoginLimiter

pytestmark = pytest.mark.unit


@pytest.fixture
def limiter(fake_clock):
    return LoginLimiter(fake_clock.time)


def fail(limiter, client, times):
    for _ in range(times):
        limiter.record_failure(client)


def test_clients_may_fail_a_few_times_before_being_locked_out(limiter):
    fail(limiter, "a", FREE_ATTEMPTS - 1)

    assert limiter.retry_after("a") == 0


def test_lockout_doubles_with_every_further_failure(limiter, fake_clock):
    delays = []
    fail(limiter, "a", FREE_ATTEMPTS - 1)
    for _ in range(3):
        limiter.record_failure("a")
        delays.append(limiter.retry_after("a"))
        fake_clock.advance(delays[-1])

    assert delays == [1, 2, 4]


def test_lockout_is_capped(limiter):
    fail(limiter, "a", FREE_ATTEMPTS + 50)

    assert limiter.retry_after("a") == MAX_DELAY_SECONDS


def test_lockout_ends_when_time_passes(limiter, fake_clock):
    fail(limiter, "a", FREE_ATTEMPTS)

    fake_clock.advance(1)

    assert limiter.retry_after("a") == 0


def test_clients_are_tracked_separately(limiter):
    fail(limiter, "a", FREE_ATTEMPTS)

    assert limiter.retry_after("b") == 0


def test_success_clears_the_failures(limiter):
    fail(limiter, "a", FREE_ATTEMPTS)

    limiter.record_success("a")
    fail(limiter, "a", FREE_ATTEMPTS - 1)

    assert limiter.retry_after("a") == 0


def test_memory_is_bounded_by_forgetting_the_oldest_client(limiter):
    for index in range(MAX_TRACKED_CLIENTS + 1):
        limiter.record_failure(f"client-{index}")

    fail(limiter, "client-0", FREE_ATTEMPTS - 1)

    assert limiter.retry_after("client-0") == 0
