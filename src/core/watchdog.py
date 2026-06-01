"""Watchdog — timeout and exponential back-off retry wrapper.

Every autonomous agent project must have a Watchdog (§8.6).
Wraps any callable with a configurable timeout and retry logic.
If a process stalls, Watchdog kills it and retries with back-off.
"""

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Any

from src.core.logger import FIFOLogger


class WatchdogTimeoutError(Exception):
    """Raised when all retry attempts are exhausted due to timeouts."""


class Watchdog:
    """Wraps any callable with timeout + exponential back-off retry.

    Designed for autonomous agent environments where API calls may stall.
    Each failed attempt is logged. After max_retries the last exception
    is re-raised so the caller can handle it (e.g. skip the round).
    """

    def __init__(self, timeout_seconds: int, max_retries: int, logger: FIFOLogger):
        """Configure the watchdog with timeout and retry limits."""
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.logger = logger

    def run(self, fn: Callable, *args: Any, source: str = "watchdog", **kwargs: Any) -> Any:
        """Execute fn(*args, **kwargs) with timeout and retry on failure.

        Uses ThreadPoolExecutor so the timeout is enforced even on blocking calls.
        Back-off: sleeps 2^attempt seconds between retries (2s, 4s, 8s…).
        """
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(fn, *args, **kwargs)
                    return future.result(timeout=self.timeout_seconds)
            except FuturesTimeoutError:
                last_exc = WatchdogTimeoutError(
                    f"Timed out after {self.timeout_seconds}s (attempt {attempt}/{self.max_retries})"
                )
                self.logger.warning(source, str(last_exc))
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
            except Exception as exc:
                last_exc = exc
                self.logger.error(source, f"Attempt {attempt} failed: {exc}")
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
        raise last_exc
