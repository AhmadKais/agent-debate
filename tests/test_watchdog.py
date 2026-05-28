import tempfile
import time

import pytest

from src.core.logger import FIFOLogger
from src.core.watchdog import Watchdog, WatchdogTimeoutError


def make_watchdog(timeout=2, retries=2):
    with tempfile.TemporaryDirectory() as tmp:
        logger = FIFOLogger(log_dir=tmp, max_files=5, max_lines=100)
        return Watchdog(timeout_seconds=timeout, max_retries=retries, logger=logger)


def test_returns_result_on_success():
    with tempfile.TemporaryDirectory() as tmp:
        logger = FIFOLogger(log_dir=tmp)
        wd = Watchdog(timeout_seconds=5, max_retries=3, logger=logger)
        result = wd.run(lambda: 42)
        assert result == 42


def test_raises_on_timeout():
    with tempfile.TemporaryDirectory() as tmp:
        logger = FIFOLogger(log_dir=tmp)
        wd = Watchdog(timeout_seconds=1, max_retries=1, logger=logger)

        def slow():
            time.sleep(5)

        with pytest.raises(WatchdogTimeoutError):
            wd.run(slow)


def test_retries_on_exception():
    with tempfile.TemporaryDirectory() as tmp:
        logger = FIFOLogger(log_dir=tmp)
        wd = Watchdog(timeout_seconds=5, max_retries=3, logger=logger)
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                raise ValueError("fail")
            return "ok"

        result = wd.run(flaky)
        assert result == "ok"
        assert calls["n"] == 3
