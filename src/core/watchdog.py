import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Any, Callable

from src.core.logger import FIFOLogger


class WatchdogTimeoutError(Exception):
    pass


class Watchdog:
    """Wraps callable with timeout + retry. Logs each attempt."""

    def __init__(self, timeout_seconds: int, max_retries: int, logger: FIFOLogger):
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.logger = logger

    def run(self, fn: Callable, *args, source: str = "watchdog", **kwargs) -> Any:
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
