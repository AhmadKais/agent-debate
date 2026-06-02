"""API Gatekeeper — central gateway for all external API calls.

Every call to the Anthropic API must go through Gatekeeper.execute().
This enforces token budget and RPM rate limits, logs every call, and
provides a single audit point for cost tracking — API gateway pattern (§5.1).
Rate limiting uses a sliding-window deque keyed off rate_limits.json (§5.3).
"""

from __future__ import annotations

import time
from collections import deque
from typing import Any


class BudgetExceededError(Exception):
    """Raised when cumulative token usage reaches the configured ceiling."""


class RateLimitExceededError(Exception):
    """Raised when the requests-per-minute limit is hit and cannot recover."""


class Gatekeeper:
    """Centralized API call manager: enforces token budget, RPM rate limit, logs all calls.

    All external API calls must be routed through execute() — never call
    the Anthropic client directly from agent code.
    """

    def __init__(self, token_budget: int, requests_per_minute: int = 0) -> None:
        """Initialize with a hard token ceiling and optional RPM limit (0 = unlimited)."""
        self.token_budget = token_budget
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self._call_count = 0
        self._rpm_limit = requests_per_minute
        self._rpm_window: deque[float] = deque()

    @property
    def total_tokens(self) -> int:
        """Combined input + output tokens used so far."""
        return self.total_input_tokens + self.total_output_tokens

    def _enforce_rate_limit(self) -> None:
        """Block until the RPM sliding window has capacity.

        Evicts timestamps older than 60 s, then sleeps if at limit.
        Uses monotonic time to avoid wall-clock drift issues.
        """
        if not self._rpm_limit:
            return
        now = time.monotonic()
        while self._rpm_window and now - self._rpm_window[0] >= 60.0:
            self._rpm_window.popleft()
        if len(self._rpm_window) >= self._rpm_limit:
            sleep_for = 60.0 - (now - self._rpm_window[0])
            if sleep_for > 0:
                time.sleep(sleep_for)
            now = time.monotonic()
            while self._rpm_window and now - self._rpm_window[0] >= 60.0:
                self._rpm_window.popleft()
        self._rpm_window.append(time.monotonic())

    def execute(self, api_call: Any, *args: Any, **kwargs: Any) -> Any:
        """Execute an API call through the gateway.

        Enforces RPM rate limit and budget before execution, records tokens after.
        All Anthropic API calls must go through this method.
        """
        self._enforce_rate_limit()
        self.check_budget()
        result = api_call(*args, **kwargs)
        self.record(result.usage.input_tokens, result.usage.output_tokens)
        self._call_count += 1
        return result

    def check_budget(self) -> None:
        """Raise BudgetExceededError if the token ceiling has been reached."""
        if self.total_tokens >= self.token_budget:
            raise BudgetExceededError(
                f"Token budget of {self.token_budget:,} exceeded "
                f"(used: {self.total_tokens:,})"
            )

    def record(self, input_tokens: int, output_tokens: int) -> None:
        """Accumulate token counts from a completed API response.

        Also checks budget after recording — two-phase enforcement:
        execute() checks before the call, record() checks after.
        """
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.check_budget()

    def status(self) -> dict:
        """Return a snapshot of current usage, budget, and rate-limit state."""
        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "budget": self.token_budget,
            "remaining": self.token_budget - self.total_tokens,
            "api_calls": self._call_count,
            "rpm_limit": self._rpm_limit,
            "rpm_used": len(self._rpm_window),
        }
