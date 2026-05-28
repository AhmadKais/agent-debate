class BudgetExceededError(Exception):
    pass


class Gatekeeper:
    """Tracks token usage and enforces a hard budget ceiling."""

    def __init__(self, token_budget: int):
        self.token_budget = token_budget
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    def check_budget(self) -> None:
        if self.total_tokens >= self.token_budget:
            raise BudgetExceededError(
                f"Token budget of {self.token_budget} exceeded "
                f"(used: {self.total_tokens})"
            )

    def record(self, input_tokens: int, output_tokens: int) -> None:
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.check_budget()

    def status(self) -> dict:
        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "budget": self.token_budget,
            "remaining": self.token_budget - self.total_tokens,
        }
