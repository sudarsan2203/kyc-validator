"""Sliding-window rate limiter.

For each client we keep a queue of the times of its recent requests.
On a new request:

1. Drop times from the front of the queue that are older than the window.
2. If the queue still holds `max_requests` entries, reject the request.
3. Otherwise record the time and allow it.

A deque is used because removing from the front is O(1).

This limiter lives in the memory of one process. If the API ran as several
processes, the counts would need to move to a shared store such as Redis.
"""

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable


class SlidingWindowRateLimiter:
    def __init__(
        self,
        max_requests: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._clock = clock
        self._requests: dict[object, deque[float]] = defaultdict(deque)
        # FastAPI handles requests on several threads, so guard the shared dict.
        self._lock = threading.Lock()

    def _drop_expired(self, timestamps: deque[float], now: float) -> None:
        while timestamps and now - timestamps[0] >= self.window_seconds:
            timestamps.popleft()

    def allow(self, client: object) -> bool:
        """Record a request for `client`. Return False if it is over the limit."""
        now = self._clock()
        with self._lock:
            timestamps = self._requests[client]
            self._drop_expired(timestamps, now)
            if len(timestamps) >= self.max_requests:
                return False
            timestamps.append(now)
            return True

    def retry_after(self, client: object) -> float:
        """Seconds until `client` can make another request (0 if it can now)."""
        now = self._clock()
        with self._lock:
            timestamps = self._requests[client]
            self._drop_expired(timestamps, now)
            if len(timestamps) < self.max_requests:
                return 0.0
            return self.window_seconds - (now - timestamps[0])

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()
