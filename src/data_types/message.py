"""Typed inter-agent message passed as JSON over IPC (child → papa → child)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

AgentRole = Literal["pro", "con", "judge"]


class Message(BaseModel):
    """Represents one argument in the debate, serializable as JSON for IPC.

    Every message flows: sender → Judge → recipient.
    The Judge observes, routes, and logs each Message before forwarding.
    `sender` and `recipient` are validated against the three agent roles.
    """

    round: int
    sender: AgentRole       # "pro" | "con" | "judge"
    recipient: AgentRole    # "pro" | "con" | "judge"
    content: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    references: list[str] = Field(default_factory=list)

    def to_ipc_dict(self) -> dict:
        """Serialize to JSON-safe dict for inter-process communication."""
        return self.model_dump()

    @classmethod
    def from_ipc_dict(cls, data: dict) -> Message:
        """Deserialize from IPC dict back to a typed Message."""
        return cls(**data)

    def summary(self) -> str:
        """One-line representation for logging."""
        return f"[Round {self.round}] {self.sender}→{self.recipient}: {self.content[:60]}..."
