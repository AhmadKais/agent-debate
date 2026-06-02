"""Standalone debate simulation (no API key needed).

Loads mock_responses.json and runs the full orchestration loop, printing
to stdout exactly as the live terminal UI would show it.
"""

import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-mock-key-for-simulation")

from src.agents.debater_agent import ConAgent, ProAgent  # noqa: E402
from src.agents.judge_agent import JudgeAgent  # noqa: E402
from src.core.gatekeeper import Gatekeeper  # noqa: E402
from src.core.logger import FIFOLogger  # noqa: E402
from src.core.watchdog import Watchdog  # noqa: E402

_DATA = json.loads((Path(__file__).parent / "mock_responses.json").read_text())
TOPIC = _DATA["topic"]
PRO_RESPONSES = [json.dumps(r) for r in _DATA["pro_responses"]]
CON_RESPONSES = [json.dumps(r) for r in _DATA["con_responses"]]
JUDGE_ROUTE = json.dumps(_DATA["judge_route"])
JUDGE_VERDICT = json.dumps(_DATA["judge_verdict"])

WIDTH = 66


def separator(label: str = "") -> None:
    if label:
        pad = (WIDTH - len(label) - 2) // 2
        print(f"\n{'─' * pad} {label} {'─' * (WIDTH - len(label) - 2 - pad)}\n")
    else:
        print("─" * WIDTH)


def _wrap(text: str, width: int) -> list[str]:
    words, lines, current = text.split(), [], []
    for w in words:
        if sum(len(x) + 1 for x in current) + len(w) > width:
            lines.append(" ".join(current))
            current = [w]
        else:
            current.append(w)
    if current:
        lines.append(" ".join(current))
    return lines


def show_argument(name: str, raw: str, ping: int, tokens_used: int, budget: int) -> str:
    try:
        data = json.loads(raw)
        arg = data.get("argument", raw)
        refs = data.get("references_used", [])
    except (ValueError, json.JSONDecodeError):
        arg = raw
        refs = []
    separator(f"Ping {ping} — {name}")
    for line in _wrap(arg, 62):
        print(f"  {line}")
    print()
    if refs:
        print("  References:")
        for r in refs:
            print(f"    • {r}")
    print(f"\n  [Tokens used: {tokens_used:,} / {budget:,}]")
    return arg


def _fake_message(text: str, in_tok: int = 120, out_tok: int = 180) -> SimpleNamespace:
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=in_tok, output_tokens=out_tok),
        stop_reason="end_turn",
    )


def run_debate() -> tuple[list, dict]:
    """Run a fully mocked debate and print results to stdout."""
    print("\n" + "═" * WIDTH)
    print("  AI AGENT DEBATE SYSTEM  v1.0".center(WIDTH))
    print("  Pro vs Con  |  Judged by THE ARBITER".center(WIDTH))
    print("═" * WIDTH)
    separator("DEBATE TOPIC")
    print(f"  {TOPIC}\n")
    print("  Rounds (pings per side): 5   |   Token budget: 150,000")
    separator()

    with tempfile.TemporaryDirectory() as tmp:
        logger = FIFOLogger(log_dir=tmp, max_files=20, max_lines=500)
        gatekeeper = Gatekeeper(token_budget=150_000)
        watchdog = Watchdog(timeout_seconds=30, max_retries=3, logger=logger)

        pro_iter, con_iter = iter(PRO_RESPONSES), iter(CON_RESPONSES)
        judge_calls: dict[str, int] = {"n": 0}

        def judge_side_effect(**kwargs: object) -> SimpleNamespace:
            judge_calls["n"] += 1
            if judge_calls["n"] > 10:
                return _fake_message(JUDGE_VERDICT, 400, 300)
            return _fake_message(JUDGE_ROUTE)

        pro_client, con_client, judge_client = MagicMock(), MagicMock(), MagicMock()
        pro_client.messages.create.side_effect = lambda **kw: _fake_message(next(pro_iter, PRO_RESPONSES[-1]))
        con_client.messages.create.side_effect = lambda **kw: _fake_message(next(con_iter, CON_RESPONSES[-1]))
        judge_client.messages.create.side_effect = judge_side_effect

        clients = iter([pro_client, con_client, judge_client])
        with patch("anthropic.Anthropic", side_effect=lambda **kw: next(clients)):
            pro = ProAgent(gatekeeper, watchdog, logger)
            con = ConAgent(gatekeeper, watchdog, logger)
            judge = JudgeAgent(gatekeeper, watchdog, logger)

    transcript: list[dict] = []
    max_pings = 5
    pro_raw = pro.generate_response(f'Topic: "{TOPIC}"\nYou are PRO. Open with your strongest argument.')
    pro_arg = show_argument(pro.name, pro_raw, 1, gatekeeper.total_tokens, 150_000)
    judge.observe("Pro", pro_arg)
    transcript.append({"ping": 1, "side": "Pro", "argument": pro_arg})

    for ping in range(1, max_pings + 1):
        con_raw = con.generate_response(f'Ping {ping}: Pro argued:\n"{pro_arg}"\n\nTear it apart.')
        con_arg = show_argument(con.name, con_raw, ping, gatekeeper.total_tokens, 150_000)
        judge.observe("Con", con_arg)
        transcript.append({"ping": ping, "side": "Con", "argument": con_arg})
        if ping == max_pings:
            break
        pro_raw = pro.generate_response(f'Ping {ping}: Con argued:\n"{con_arg}"\n\nRefute it.')
        pro_arg = show_argument(pro.name, pro_raw, ping + 1, gatekeeper.total_tokens, 150_000)
        judge.observe("Pro", pro_arg)
        transcript.append({"ping": ping + 1, "side": "Pro", "argument": pro_arg})

    verdict = judge.declare_winner()
    separator("FINAL VERDICT")
    print(f"  WINNER : {verdict.get('winner', '?').upper()}")
    print(f"  Score  — Pro: {verdict.get('score_pro', '?')}  |  Con: {verdict.get('score_con', '?')}\n")
    for line in _wrap(verdict.get("reason", ""), 62):
        print(f"    {line}")
    separator()
    print(f"  Tokens: {gatekeeper.total_tokens:,} / 150,000  |  Entries: {len(transcript)}")
    separator()
    return transcript, verdict


if __name__ == "__main__":
    run_debate()
