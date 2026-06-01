"""Judge (Papa) agent — routes all messages and declares the debate winner.

Every argument flows child → JudgeAgent → child.
The Judge enforces 8 debate rules before routing each message,
accumulates violations, and weighs them in the final verdict.
"""

import json

from src.agents.base_agent import BaseAgent
from src.agents.prompts import JUDGE_SYSTEM_PROMPT
from src.core.gatekeeper import Gatekeeper
from src.core.logger import FIFOLogger
from src.core.watchdog import Watchdog


class RuleViolationError(Exception):
    """Raised when a debater commits a critical rule violation."""

    def __init__(self, side: str, violations: list[str]) -> None:
        self.side = side
        self.violations = violations
        super().__init__(f"[{side}] violations: {', '.join(violations)}")


class JudgeAgent(BaseAgent):
    """Supervises the debate: checks all 8 rules, routes messages, declares winner."""

    def __init__(self, gatekeeper: Gatekeeper, watchdog: Watchdog, logger: FIFOLogger):
        super().__init__(
            name="THE ARBITER (Judge)",
            system_prompt=JUDGE_SYSTEM_PROMPT,
            gatekeeper=gatekeeper,
            watchdog=watchdog,
            logger=logger,
        )
        self.debate_transcript: list[dict] = []
        self.violations: list[dict] = []

    def observe(self, side: str, argument: str) -> str:
        """Receive argument, run all 8 rule checks, log violations, route to next speaker.

        Implements child→papa→child with full active moderation:
        profanity, ad hominem, off-topic, empty, no-rebuttal,
        concession, no-evidence, and repetition are all checked.

        Returns: next speaker — 'Pro' or 'Con' (judge's decision).
        """
        previous = self._last_opponent_argument(side)
        self.debate_transcript.append({"side": side, "argument": argument})

        prompt = f"Debate exchange received:\n[{side}]: {argument}\n\n"
        if previous:
            prompt += f"Opponent's last argument:\n{previous}\n\n"
        else:
            prompt += "Opening argument — Rule 2 (rebuttal) does not apply.\n\n"
        prompt += 'Apply ALL 8 rules. Respond ONLY with: {"route_to": "...", "violations": [...], "warnings": [...]}'

        raw = self.generate_response(prompt)
        fallback = "Con" if side == "Pro" else "Pro"
        return self._parse_route_and_check(raw, side, fallback)

    def declare_winner(self) -> dict:
        """Evaluate full transcript + all violations and return final verdict.

        Violations are shown to the judge so the offending side is penalised.
        No ties allowed — always returns winner 'Pro' or 'Con'.
        """
        self.logger.info(self.name, "Declaring final winner")
        transcript_text = "\n\n".join(
            f"[{e['side']}]: {e['argument']}" for e in self.debate_transcript
        )
        violation_summary = ""
        if self.violations:
            violation_summary = "\n\nVIOLATIONS (penalise offending side):\n" + "\n".join(
                f"  [{v['side']}] {v['type']}: {v['warning']}" for v in self.violations
            )
        prompt = (
            f"Debate over. Transcript:\n\n{transcript_text}{violation_summary}\n\n"
            "FINAL VERDICT — reason ≤200 words, summary ≤80 words. NO ties."
        )
        self.max_tokens = 2048
        raw = self.generate_response(prompt)
        self.max_tokens = 500
        return self._parse_verdict(raw)

    def _last_opponent_argument(self, side: str) -> str | None:
        """Return the most recent argument from the opposing side, or None."""
        opponent = "Con" if side == "Pro" else "Pro"
        for entry in reversed(self.debate_transcript):
            if entry["side"] == opponent:
                return entry["argument"]
        return None

    def _parse_route_and_check(self, raw: str, side: str, fallback: str) -> str:
        """Parse routing JSON and record all violations flagged by the judge."""
        try:
            start, end = raw.find("{"), raw.rfind("}") + 1
            data = json.loads(raw[start:end])
            violations = data.get("violations") or []
            warnings = data.get("warnings") or []
            for v_type, warning in zip(violations, warnings, strict=False):
                if v_type and v_type != "null":
                    self.violations.append({"side": side, "type": v_type, "warning": warning})
                    self.logger.warning(self.name, f"VIOLATION [{side}] {v_type}: {warning}")
            return data.get("route_to", fallback)
        except (ValueError, json.JSONDecodeError):
            self.logger.warning(self.name, f"Could not parse route: {raw[:80]}")
            return fallback

    def _parse_verdict(self, raw: str) -> dict:
        """Extract structured verdict JSON and attach the full violation log."""
        try:
            start, end = raw.find("{"), raw.rfind("}") + 1
            verdict = json.loads(raw[start:end])
            verdict["violations"] = self.violations
            return verdict
        except (ValueError, json.JSONDecodeError):
            self.logger.error(self.name, f"Failed to parse verdict: {raw[:200]}")
            return {
                "winner": "Pro", "reason": "Could not parse verdict.",
                "score_pro": 50, "score_con": 49,
                "summary": raw[:300], "violations": self.violations,
            }
