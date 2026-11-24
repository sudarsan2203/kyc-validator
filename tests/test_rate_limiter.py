"""Unit tests for the rate limiter, using a fake clock so nothing has to sleep."""

from app.rate_limiter import SlidingWindowRateLimiter


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def make_limiter(max_requests=3, window_seconds=60):
    clock = FakeClock()
    return SlidingWindowRateLimiter(max_requests, window_seconds, clock=clock), clock


def test_allows_requests_up_to_the_limit():
    limiter, _ = make_limiter(max_requests=3)
    assert [limiter.allow("a") for _ in range(3)] == [True, True, True]


def test_blocks_requests_over_the_limit():
    limiter, _ = make_limiter(max_requests=3)
    for _ in range(3):
        limiter.allow("a")
    assert limiter.allow("a") is False


def test_allows_again_after_the_window_passes():
    limiter, clock = make_limiter(max_requests=1, window_seconds=60)
    assert limiter.allow("a")
    assert not limiter.allow("a")
    clock.now = 60
    assert limiter.allow("a")


def test_window_slides_instead_of_resetting():
    limiter, clock = make_limiter(max_requests=2, window_seconds=60)
    limiter.allow("a")  # at t=0
    clock.now = 30
    limiter.allow("a")  # at t=30
    clock.now = 61  # the t=0 request has expired, the t=30 one has not
    assert limiter.allow("a")
    assert not limiter.allow("a")


def test_clients_are_counted_separately():
    limiter, _ = make_limiter(max_requests=1)
    assert limiter.allow("a")
    assert limiter.allow("b")
    assert not limiter.allow("a")


def test_blocked_requests_are_not_counted():
    limiter, clock = make_limiter(max_requests=1, window_seconds=60)
    limiter.allow("a")
    clock.now = 59
    limiter.allow("a")  # blocked, so it must not extend the wait
    clock.now = 60
    assert limiter.allow("a")


def test_retry_after():
    limiter, clock = make_limiter(max_requests=1, window_seconds=60)
    assert limiter.retry_after("a") == 0
    limiter.allow("a")
    clock.now = 20
    assert limiter.retry_after("a") == 40
