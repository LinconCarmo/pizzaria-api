import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from src.core.exceptions import TooManyRequestsError

_SWEEP_THRESHOLD = 10_000


@dataclass(frozen=True, slots=True)
class RateLimitPolicy:
    max_attempts: int
    window_seconds: float


@dataclass(slots=True)
class _Window:
    expires_at: float
    count: int


class RateLimiterProtocol(Protocol):
    def check(self, key: str, policy: RateLimitPolicy) -> None: ...

    def record(self, key: str, policy: RateLimitPolicy) -> None: ...

    def reset(self, key: str) -> None: ...


class InMemoryRateLimiter:
    """Janela fixa por chave, guardada na memória do processo.

    Cada worker do uvicorn tem o próprio contador. Com mais de um worker ou de uma
    réplica, o limite efetivo se multiplica; nesse cenário a implementação precisa
    de um armazenamento compartilhado (ex.: Redis) atrás do mesmo Protocol.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._windows: dict[str, _Window] = {}

    def check(self, key: str, policy: RateLimitPolicy) -> None:
        window = self._active_window(key)
        if window is not None and window.count >= policy.max_attempts:
            retry_after = math.ceil(window.expires_at - self._clock())
            raise TooManyRequestsError(retry_after_seconds=max(retry_after, 1))

    def record(self, key: str, policy: RateLimitPolicy) -> None:
        window = self._active_window(key)
        if window is None:
            if len(self._windows) >= _SWEEP_THRESHOLD:
                self._sweep_expired()
            self._windows[key] = _Window(
                expires_at=self._clock() + policy.window_seconds,
                count=1,
            )
            return
        window.count += 1

    def reset(self, key: str) -> None:
        self._windows.pop(key, None)

    def clear(self) -> None:
        self._windows.clear()

    def _active_window(self, key: str) -> _Window | None:
        window = self._windows.get(key)
        if window is not None and window.expires_at <= self._clock():
            del self._windows[key]
            return None
        return window

    def _sweep_expired(self) -> None:
        now = self._clock()
        expired = [key for key, window in self._windows.items() if window.expires_at <= now]
        for key in expired:
            del self._windows[key]


rate_limiter = InMemoryRateLimiter()


def get_rate_limiter() -> RateLimiterProtocol:
    return rate_limiter
