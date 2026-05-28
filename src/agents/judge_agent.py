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
   {{"winner": "Pro" or "Con", "reason": "detailed justification", "score_pro": <integer 0-100>, "score_con": <integer 0-100>, "summary": "brief debate summary"}}
3. ABSOLUTE RULE: You CANNOT declare a tie. One side must win. Even if scores are close (e.g., 71 vs 70), pick the winner and justify it.
4. For routing during the debate, output ONLY: {{"route_to": "Con"}} or {{"route_to": "Pro"}}, plus optional {{"comment": "brief note"}}.
5. Be fair but decisive. Your verdict is final and cannot be appealed.
6. Language: English only."""


class JudgeAgent(BaseAgent):
    def __init__(self, gatekeeper: Gatekeeper, watchdog: Watchdog, logger: FIFOLogger):
        super().__init__(
            name="THE ARBITER (Judge)",
            system_prompt=JUDGE_SYSTEM_PROMPT,
            gatekeeper=gatekeeper,
            watchdog=watchdog,
            logger=logger,
        )
        self.debate_transcript: list[dict] = []

    def observe(self, side: str, argument: str) -> None:
        self.debate_transcript.append({"side": side, "argument": argument})
        summary = f"[{side}]: {argument[:120]}..."
        self.generate_response(
            f"Debate exchange received — observe and track:\n{summary}\n"
            f"Respond only with a routing JSON: {{\"route_to\": \"Pro\" or \"Con\"}}"
        )

    def declare_winner(self) -> dict:
        self.logger.info(self.name, "Declaring final winner")
        transcript_text = "\n\n".join(
            f"[{e['side']}]: {e['argument']}" for e in self.debate_transcript
        )
        prompt = (
            "The debate is now over. Here is the complete transcript:\n\n"
            f"{transcript_text}\n\n"
            "Now deliver your FINAL VERDICT in the exact JSON format specified in your instructions. "
            "Remember: NO ties allowed."
        )
        raw = self.generate_response(prompt)
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            return json.loads(raw[start:end])
        except (ValueError, json.JSONDecodeError):
            self.logger.error(self.name, f"Failed to parse verdict JSON: {raw}")
            return {
                "winner": "Pro",
                "reason": "Could not parse judge verdict.",
                "score_pro": 50,
                "score_con": 49,
                "summary": raw,
            }
