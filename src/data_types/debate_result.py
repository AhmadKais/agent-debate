"""Typed result returned by the Judge at the end of the debate."""

from __future__ import annotations

from pydantic import BaseModel, field_validator


class DebateResult(BaseModel):
    """Structured verdict produced by the Judge agent.

    winner must always be 'Pro' or 'Con' — ties are forbidden by the assignment.
    """

    topic: str
    winner: str       # "Pro" or "Con" — never a tie
    score_pro: int
    score_con: int
    reason: str
    summary: str = ""
    total_tokens: int = 0
    rounds_completed: int = 0

    @field_validator("winner")
    @classmethod
    def winner_must_not_be_tie(cls, v: str) -> str:
        """Enforce the no-tie rule at the data layer."""
        if v not in ("Pro", "Con"):
            raise ValueError(f"winner must be 'Pro' or 'Con', got: {v!r}")
        return v

    @field_validator("score_pro", "score_con")
    @classmethod
    def scores_in_range(cls, v: int) -> int:
        """Scores must be 0–100."""
        if not 0 <= v <= 100:
            raise ValueError(f"Score must be 0–100, got {v}")
        return v

    def to_dict(self) -> dict:
        """Serialize for SDK return value."""
        return self.model_dump()
