"""API Gatekeeper — central gateway for all external API calls.

Every call to the Anthropic API must go through Gatekeeper.execute().
This enforces budget limits, logs every call, and provides a single
audit point for cost tracking — the API gateway pattern (§5.1).
"""

from __future__ import annotations

from typing import Any


class BudgetExceededError(Exception):
    """Raised when cumulative token usage reaches the configured ceiling."""


class Gatekeeper:
    """Centralized API call manager: enforces token budget and logs all calls.

    All external API calls must be routed through execute() — never call
    the Anthropic client directly from agent code.
    """

    def __init__(self, token_budget: int) -> None:
        """Initialize with a hard token ceiling in tokens."""
        self.token_budget = token_budget
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self._call_count = 0

    @property
    def total_tokens(self) -> int:
        """Combined input + output tokens used so far."""
        return self.total_input_tokens + self.total_output_tokens

    def execute(self, api_call: Any, *args: Any, **kwargs: Any) -> Any:
        """Execute an API call through the gateway.

        Checks budget before execution, records tokens after.
        All Anthropic API calls must go through this method.
        """
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
        """Return a snapshot of current usage vs budget."""
        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "budget": self.token_budget,
            "remaining": self.token_budget - self.total_tokens,
            "api_calls": self._call_count,
        }
