"""Public SDK facade — the single entry point for all debate logic.

External consumers (CLI, tests, REST) must use this class only.
All inter-agent communication is routed child→JudgeAgent→child and
serialized as typed Message objects (JSON IPC).
"""

from __future__ import annotations

import json
from pathlib import Path

from src.agents.debater_agent import ConAgent, ProAgent
from src.agents.judge_agent import JudgeAgent
from src.constants import DEFAULT_CONFIG_PATH, DEFAULT_LOG_DIR, TRANSCRIPT_FILENAME
from src.core.config import load_config
from src.core.gatekeeper import BudgetExceededError, Gatekeeper
from src.core.logger import FIFOLogger
from src.core.watchdog import Watchdog
from src.data_types.message import Message


class DebateSDK:
    """Orchestrates a full Pro-vs-Con debate supervised by a Judge agent."""

    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH) -> None:
        self.cfg = load_config(config_path)

    def run(
        self,
        topic: str | None = None,
        max_pings: int | None = None,
        on_argument: object = None,
    ) -> dict:
        """Run a full debate and return {"topic", "transcript", "verdict", "token_usage"}.

        All arguments flow child→Judge→child. The Judge routes every message
        and declares the winner. on_argument(side, name, argument, ping, tokens).
        """
        topic = topic or self.cfg["debate_topic"]
        max_pings = max_pings or self.cfg["max_pings"]

        logger, gatekeeper, watchdog = self._build_infrastructure()
        pro = ProAgent(gatekeeper, watchdog, logger)
        con = ConAgent(gatekeeper, watchdog, logger)
        judge = JudgeAgent(gatekeeper, watchdog, logger)
        transcript: list[dict] = []

        try:
            pro_arg = self._open_debate(pro, judge, topic, transcript, gatekeeper, on_argument)
            self._run_rounds(pro, con, judge, pro_arg, max_pings, transcript, gatekeeper, on_argument)
            verdict = judge.declare_winner()
        except BudgetExceededError as exc:
            verdict = {"winner": "Pro", "reason": f"Budget exceeded: {exc}", "score_pro": 0, "score_con": 0}

        self._save_transcript(transcript, verdict, topic)
        return {"topic": topic, "transcript": transcript, "verdict": verdict, "token_usage": gatekeeper.status()}

    def _build_infrastructure(self) -> tuple[FIFOLogger, Gatekeeper, Watchdog]:
        """Instantiate shared infrastructure: logger, gatekeeper, watchdog."""
        logger = FIFOLogger(
            log_dir=self.cfg.get("log_dir", DEFAULT_LOG_DIR),
            max_files=self.cfg["log_max_files"],
            max_lines=self.cfg["log_max_lines"],
        )
        gatekeeper = Gatekeeper(token_budget=self.cfg["token_budget"])
        watchdog = Watchdog(timeout_seconds=self.cfg["timeout_seconds"], max_retries=self.cfg["max_retries"], logger=logger)
        return logger, gatekeeper, watchdog

    def _parse_argument(self, raw: str) -> tuple[str, list[str]]:
        """Extract argument text and references from agent JSON response.

        Uses json.JSONDecoder to find the first valid JSON object in the string,
        which is more robust than rfind('}') when the argument text contains braces.
        Falls back to returning the raw string if no valid JSON is found.
        """
        decoder = json.JSONDecoder()
        for start in range(len(raw)):
            if raw[start] == "{":
                try:
                    data, _ = decoder.raw_decode(raw, start)
                    return data.get("argument", raw), data.get("references_used", [])
                except json.JSONDecodeError:
                    continue
        return raw, []

    def _open_debate(self, pro, judge, topic, transcript, gatekeeper, on_argument) -> str:
        """Pro agent opens the debate; Judge routes to Con (child→papa→child)."""
        opening = (
            f'The debate topic is: "{topic}"\n'
            "You are arguing the PRO side. Open with your strongest argument. "
            "Use web_search to cite real evidence."
        )
        pro_raw = pro.generate_response(opening)
        pro_arg, refs = self._parse_argument(pro_raw)
        next_speaker = judge.observe("Pro", pro_arg)  # judge routes: Pro→Judge→Con
        msg = Message(round=1, sender="pro", recipient=next_speaker.lower(), content=pro_arg, references=refs)
        transcript.append(msg.to_ipc_dict())
        if on_argument:
            on_argument("Pro", pro.name, pro_arg, 1, gatekeeper.status()["total_tokens"])
        return pro_arg

    def _run_rounds(self, pro, con, judge, pro_arg, max_pings, transcript, gatekeeper, on_argument):
        """Execute debate rounds; judge routes every message, reserves budget for verdict."""
        verdict_reserve = 60_000
        for ping in range(1, max_pings + 1):
            try:
                if gatekeeper.status()["remaining"] < verdict_reserve:
                    break
                con_arg = self._con_turn(con, judge, pro_arg, ping, transcript, gatekeeper, on_argument)
                if ping == max_pings:
                    break
                if gatekeeper.status()["remaining"] < verdict_reserve:
                    break
                pro_arg = self._pro_turn(pro, judge, con_arg, ping, transcript, gatekeeper, on_argument)
            except BudgetExceededError:
                break

    def _con_turn(self, con, judge, pro_arg, ping, transcript, gatekeeper, on_argument) -> str:
        """Con argues; Judge evaluates and routes back to Pro (child→papa→child)."""
        raw = con.generate_response(f'Ping {ping}: Pro argued:\n"{pro_arg}"\n\nTear it apart for CON.')
        arg, refs = self._parse_argument(raw)
        next_speaker = judge.observe("Con", arg)  # judge routes: Con→Judge→Pro
        msg = Message(round=ping, sender="con", recipient=next_speaker.lower(), content=arg, references=refs)
        transcript.append(msg.to_ipc_dict())
        if on_argument:
            on_argument("Con", con.name, arg, ping, gatekeeper.status()["total_tokens"])
        return arg

    def _pro_turn(self, pro, judge, con_arg, ping, transcript, gatekeeper, on_argument) -> str:
        """Pro argues; Judge evaluates and routes back to Con (child→papa→child)."""
        raw = pro.generate_response(f'Ping {ping}: Con argued:\n"{con_arg}"\n\nRefute it for PRO.')
        arg, refs = self._parse_argument(raw)
        next_speaker = judge.observe("Pro", arg)  # judge routes: Pro→Judge→Con
        msg = Message(round=ping + 1, sender="pro", recipient=next_speaker.lower(), content=arg, references=refs)
        transcript.append(msg.to_ipc_dict())
        if on_argument:
            on_argument("Pro", pro.name, arg, ping + 1, gatekeeper.status()["total_tokens"])
        return arg

    def _save_transcript(self, transcript: list, verdict: dict, topic: str) -> None:
        """Persist transcript and verdict to JSONL log directory."""
        log_dir = Path(self.cfg.get("log_dir", DEFAULT_LOG_DIR))
        log_dir.mkdir(exist_ok=True)
        with open(log_dir / TRANSCRIPT_FILENAME, "w") as f:
            json.dump({"topic": topic, "transcript": transcript, "verdict": verdict}, f, indent=2)
