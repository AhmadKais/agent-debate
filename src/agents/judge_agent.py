"""Judge (Papa) agent — routes all messages and declares the debate winner.

Architecture: every argument flows child → JudgeAgent → child.
The Judge evaluates each exchange, decides who speaks next,
and delivers the final verdict with no ties allowed.
"""

import json

from src.agents.base_agent import BaseAgent
from src.core.gatekeeper import Gatekeeper
from src.core.logger import FIFOLogger
from src.core.watchdog import Watchdog

JUDGE_SYSTEM_PROMPT = """You are THE ARBITER, an impartial and authoritative debate judge.
Your role is to evaluate arguments on PERSUASIVENESS, LOGIC, and RHETORICAL IMPACT — not factual accuracy.

RESPONSIBILITIES:
1. After each exchange, silently track which side is more convincing.
2. When asked for a FINAL VERDICT, output ONLY valid JSON:
   {"winner": "Pro" or "Con", "reason": "detailed justification", "score_pro": <integer 0-100>, "score_con": <integer 0-100>, "summary": "brief debate summary"}
3. ABSOLUTE RULE: You CANNOT declare a tie. One side must win. Even if scores are close, pick the winner.
4. For routing during the debate, output ONLY: {"route_to": "Con"} or {"route_to": "Pro"}.
5. Be fair but decisive. Your verdict is final and cannot be appealed.
6. Language: English only."""


class JudgeAgent(BaseAgent):
    """Supervises the debate: routes every message and declares the winner."""

    def __init__(self, gatekeeper: Gatekeeper, watchdog: Watchdog, logger: FIFOLogger):
        super().__init__(
            name="THE ARBITER (Judge)",
            system_prompt=JUDGE_SYSTEM_PROMPT,
            gatekeeper=gatekeeper,
            watchdog=watchdog,
            logger=logger,
        )
        self.debate_transcript: list[dict] = []

    def observe(self, side: str, argument: str) -> str:
        """Receive argument from a debater and route to the next speaker.

        Implements child→papa→child: every argument passes through the Judge
        before the next debater is allowed to respond.

        Returns: next speaker — 'Pro' or 'Con' (judge's decision).
        """
        self.debate_transcript.append({"side": side, "argument": argument})
        raw = self.generate_response(
            f"Debate exchange received:\n[{side}]: {argument}\n\n"
            "Evaluate this argument, then decide who speaks next. "
            'Respond ONLY with routing JSON: {"route_to": "Con"} or {"route_to": "Pro"}'
        )
        fallback = "Con" if side == "Pro" else "Pro"
        return self._parse_route(raw, fallback)

    def declare_winner(self) -> dict:
        """Evaluate the full debate transcript and return verdict JSON.

        Returns a dict with: winner, reason, score_pro, score_con, summary.
        No ties allowed — winner is always 'Pro' or 'Con'.
        """
        self.logger.info(self.name, "Declaring final winner")
        transcript_text = "\n\n".join(
            f"[{e['side']}]: {e['argument']}" for e in self.debate_transcript
        )
        prompt = (
            "The debate is now over. Here is the complete transcript:\n\n"
            f"{transcript_text}\n\n"
            "Deliver your FINAL VERDICT in the exact JSON format. "
            "Keep reason under 200 words and summary under 80 words. NO ties."
        )
        self.max_tokens = 2048
        raw = self.generate_response(prompt)
        self.max_tokens = 500
        return self._parse_verdict(raw)

    def _parse_route(self, raw: str, fallback: str) -> str:
        """Extract route_to value from judge's routing JSON response."""
        try:
            start, end = raw.find("{"), raw.rfind("}") + 1
            return json.loads(raw[start:end]).get("route_to", fallback)
        except (ValueError, json.JSONDecodeError):
            self.logger.warning(self.name, f"Could not parse route from: {raw[:80]}")
            return fallback

    def _parse_verdict(self, raw: str) -> dict:
        """Extract structured verdict from judge's final JSON response."""
        try:
            start, end = raw.find("{"), raw.rfind("}") + 1
            return json.loads(raw[start:end])
        except (ValueError, json.JSONDecodeError):
            self.logger.error(self.name, f"Failed to parse verdict JSON: {raw[:200]}")
            return {
                "winner": "Pro",
                "reason": "Could not parse judge verdict.",
                "score_pro": 50,
                "score_con": 49,
                "summary": raw[:300],
            }
