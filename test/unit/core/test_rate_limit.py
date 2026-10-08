import pytest

from src.core.exceptions import TooManyRequestsError
from src.core.rate_limit import InMemoryRateLimiter, RateLimitPolicy

KEY = "login:ip:127.0.0.1"
OTHER_KEY = "login:ip:10.0.0.1"
POLICY = RateLimitPolicy(max_attempts=2, window_seconds=60)


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def limiter(clock: FakeClock) -> InMemoryRateLimiter:
    return InMemoryRateLimiter(clock=clock)


def _record_times(limiter: InMemoryRateLimiter, times: int, key: str = KEY) -> None:
    for _ in range(times):
        limiter.record(key, POLICY)


def test_check_allows_when_below_limit(limiter: InMemoryRateLimiter) -> None:
    _record_times(limiter, 1)

    limiter.check(KEY, POLICY)


def test_check_raises_429_with_retry_after_when_limit_reached(
    limiter: InMemoryRateLimiter, clock: FakeClock
) -> None:
    _record_times(limiter, 2)
    clock.now += 15

    with pytest.raises(TooManyRequestsError) as exc_info:
        limiter.check(KEY, POLICY)

    assert exc_info.value.status_code == 429
    assert exc_info.value.headers == {"Retry-After": "45"}


def test_check_allows_again_when_window_expires(
    limiter: InMemoryRateLimiter, clock: FakeClock
) -> None:
    _record_times(limiter, 2)
    clock.now += 60

    limiter.check(KEY, POLICY)


def test_limit_is_tracked_per_key(limiter: InMemoryRateLimiter) -> None:
    _record_times(limiter, 2)

    limiter.check(OTHER_KEY, POLICY)


def test_reset_clears_the_key(limiter: InMemoryRateLimiter) -> None:
    _record_times(limiter, 2)

    limiter.reset(KEY)

    limiter.check(KEY, POLICY)


def test_clear_removes_every_key(limiter: InMemoryRateLimiter) -> None:
    _record_times(limiter, 2)
    _record_times(limiter, 2, key=OTHER_KEY)

    limiter.clear()

    limiter.check(KEY, POLICY)
    limiter.check(OTHER_KEY, POLICY)
