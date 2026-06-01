"""Judge (Papa) agent — routes all messages and declares the debate winner.

Architecture: every argument flows child → JudgeAgent → child.
The Judge actively evaluates each exchange before routing:
  - checks for rule violations (profanity, off-topic, personal attacks)
  - issues warnings and deducts credibility from violating side
  - decides who speaks next
  - delivers the final non-tie verdict
"""

import json

from src.agents.base_agent import BaseAgent
from src.core.gatekeeper import Gatekeeper
from src.core.logger import FIFOLogger
from src.core.watchdog import Watchdog

JUDGE_SYSTEM_PROMPT = """You are THE ARBITER, an impartial and authoritative debate judge.
Your role is to evaluate arguments on PERSUASIVENESS, LOGIC, and RHETORICAL IMPACT — not factual accuracy.

RESPONSIBILITIES:
1. Before routing each argument, CHECK FOR VIOLATIONS:
   - Profanity or foul language → flag as "violation: profanity", penalize that side
   - Personal attacks on the opponent (not their argument) → flag as "violation: ad_hominem"
   - Completely off-topic content → flag as "violation: off_topic"
   - If a violation is found: warn the side, reduce their credibility score, still route.
2. After each exchange, silently track which side is more convincing.
3. For routing, output ONLY valid JSON:
   {"route_to": "Con" or "Pro", "violation": null or "profanity|ad_hominem|off_topic", "warning": null or "warning text"}
4. When asked for FINAL VERDICT, output ONLY:
   {"winner": "Pro" or "Con", "reason": "detailed justification", "score_pro": <0-100>, "score_con": <0-100>, "summary": "brief summary"}
5. ABSOLUTE RULE: NO TIE. Always pick a winner. Violations count against a side.
6. Language: English only."""


class RuleViolationError(Exception):
    """Raised when a debater's argument violates debate rules."""

    def __init__(self, side: str, violation_type: str, warning: str) -> None:
        self.side = side
        self.violation_type = violation_type
        self.warning = warning
        super().__init__(f"[{side}] violation: {violation_type} — {warning}")


class JudgeAgent(BaseAgent):
    """Supervises the debate: checks rules, routes every message, declares the winner."""

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
        """Receive argument, check rules, log any violations, route to next speaker.

        Implements child→papa→child with active moderation:
        the Judge reads every argument before forwarding it.
        If a violation is detected, it is logged and penalizes the offending side.

        Returns: next speaker — 'Pro' or 'Con' (judge's decision).
        """
        self.debate_transcript.append({"side": side, "argument": argument})
        raw = self.generate_response(
            f"Debate exchange received:\n[{side}]: {argument}\n\n"
            "1. Check for rule violations (profanity, personal attacks, off-topic).\n"
            "2. Decide who speaks next.\n"
            'Respond ONLY with: {"route_to": "Con" or "Pro", '
            '"violation": null or "profanity|ad_hominem|off_topic", '
            '"warning": null or "brief warning text"}'
        )
        fallback = "Con" if side == "Pro" else "Pro"
        return self._parse_route_and_check(raw, side, fallback)

    def declare_winner(self) -> dict:
        """Evaluate the full debate transcript and return verdict JSON.

        Violations accumulated during the debate are factored into the final scores.
        No ties allowed — winner is always 'Pro' or 'Con'.
        """
        self.logger.info(self.name, "Declaring final winner")
        transcript_text = "\n\n".join(
            f"[{e['side']}]: {e['argument']}" for e in self.debate_transcript
        )
        violation_summary = ""
        if self.violations:
            violation_summary = "\n\nVIOLATIONS RECORDED:\n" + "\n".join(
                f"  [{v['side']}] {v['type']}: {v['warning']}" for v in self.violations
            )
        prompt = (
            "The debate is now over. Here is the complete transcript:\n\n"
            f"{transcript_text}{violation_summary}\n\n"
            "Deliver your FINAL VERDICT. Violations count against the offending side. "
            "Keep reason under 200 words and summary under 80 words. NO ties."
        )
        self.max_tokens = 2048
        raw = self.generate_response(prompt)
        self.max_tokens = 500
        return self._parse_verdict(raw)

    def _parse_route_and_check(self, raw: str, side: str, fallback: str) -> str:
        """Parse routing JSON, log any rule violations found by the judge."""
        try:
            start, end = raw.find("{"), raw.rfind("}") + 1
            data = json.loads(raw[start:end])
            violation = data.get("violation")
            warning = data.get("warning")
            if violation and violation != "null":
                record = {"side": side, "type": violation, "warning": warning or ""}
                self.violations.append(record)
                self.logger.warning(
                    self.name,
                    f"RULE VIOLATION by {side}: {violation} — {warning}",
                )
            return data.get("route_to", fallback)
        except (ValueError, json.JSONDecodeError):
            self.logger.warning(self.name, f"Could not parse route from: {raw[:80]}")
            return fallback

    def _parse_verdict(self, raw: str) -> dict:
        """Extract structured verdict from judge's final JSON response."""
        try:
            start, end = raw.find("{"), raw.rfind("}") + 1
            verdict = json.loads(raw[start:end])
            verdict["violations"] = self.violations
            return verdict
        except (ValueError, json.JSONDecodeError):
            self.logger.error(self.name, f"Failed to parse verdict JSON: {raw[:200]}")
            return {
                "winner": "Pro",
                "reason": "Could not parse judge verdict.",
                "score_pro": 50,
                "score_con": 49,
                "summary": raw[:300],
                "violations": self.violations,
            }
