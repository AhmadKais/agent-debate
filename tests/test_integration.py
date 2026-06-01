"""
Integration tests: full debate orchestration and token tracking.
Uses mocked Anthropic API — no real API key required.
"""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.agents.debater_agent import ConAgent, ProAgent
from src.agents.judge_agent import JudgeAgent
from src.core.gatekeeper import Gatekeeper
from src.core.logger import FIFOLogger
from src.core.watchdog import Watchdog
from tests.mock_data import CON_RESPONSES, JUDGE_ROUTE_RESPONSE, JUDGE_VERDICT, PRO_RESPONSES


def _fake_msg(text: str, input_tokens: int = 50, output_tokens: int = 80):
    block = SimpleNamespace(type="text", text=text)
    usage = SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens)
    return SimpleNamespace(content=[block], usage=usage, stop_reason="end_turn")


@pytest.fixture
def infra(tmp_path):
    log_dir = str(tmp_path / "logs")
    logger = FIFOLogger(log_dir=log_dir, max_files=20, max_lines=500)
    gatekeeper = Gatekeeper(token_budget=150_000)
    watchdog = Watchdog(timeout_seconds=30, max_retries=3, logger=logger)
    return logger, gatekeeper, watchdog, tmp_path


def _build_agents(mock_cls, infra):
    logger, gatekeeper, watchdog, _ = infra
    pro_client, con_client, judge_client = MagicMock(), MagicMock(), MagicMock()
    pro_iter = iter(PRO_RESPONSES)
    con_iter = iter(CON_RESPONSES)
    judge_n = {"n": 0}

    def judge_side(**kw):
        judge_n["n"] += 1
        return _fake_msg(JUDGE_VERDICT if judge_n["n"] > 10 else JUDGE_ROUTE_RESPONSE)

    pro_client.messages.create.side_effect = lambda **kw: _fake_msg(next(pro_iter, PRO_RESPONSES[-1]))
    con_client.messages.create.side_effect = lambda **kw: _fake_msg(next(con_iter, CON_RESPONSES[-1]))
    judge_client.messages.create.side_effect = judge_side
    clients = iter([pro_client, con_client, judge_client])
    mock_cls.side_effect = lambda **kw: next(clients)
    pro = ProAgent(gatekeeper, watchdog, logger)
    con = ConAgent(gatekeeper, watchdog, logger)
    judge = JudgeAgent(gatekeeper, watchdog, logger)
    return pro, con, judge


@patch("anthropic.Anthropic")
def test_full_debate_runs_5_pings(mock_cls, infra):
    logger, gatekeeper, watchdog, tmp_path = infra
    pro, con, judge = _build_agents(mock_cls, infra)
    transcript = []
    max_pings = 5
    pro_raw = pro.generate_response('Topic: "Linux vs Windows". Argue PRO.')
    pro_arg = json.loads(pro_raw)["argument"]
    judge.observe("Pro", pro_arg)
    transcript.append({"ping": 1, "side": "Pro", "argument": pro_arg})

    for ping in range(1, max_pings + 1):
        con_raw = con.generate_response(f'Ping {ping}: Pro argued: "{pro_arg}". Refute.')
        con_arg = json.loads(con_raw)["argument"]
        judge.observe("Con", con_arg)
        transcript.append({"ping": ping, "side": "Con", "argument": con_arg})
        if ping == max_pings:
            break
        pro_raw = pro.generate_response(f'Ping {ping}: Con argued: "{con_arg}". Counter.')
        pro_arg = json.loads(pro_raw)["argument"]
        judge.observe("Pro", pro_arg)
        transcript.append({"ping": ping + 1, "side": "Pro", "argument": pro_arg})

    verdict = judge.declare_winner()
    out = tmp_path / "transcript.json"
    with open(out, "w") as f:
        json.dump({"transcript": transcript, "verdict": verdict}, f)

    assert len(transcript) == 10, f"Expected 10 exchanges, got {len(transcript)}"
    assert verdict["winner"] in ("Pro", "Con")
    assert verdict["winner"] != "Tie"
    assert out.exists()


@patch("anthropic.Anthropic")
def test_gatekeeper_tracks_tokens_across_agents(mock_cls, infra):
    logger, gatekeeper, watchdog, _ = infra
    client = MagicMock()
    client.messages.create.return_value = _fake_msg(PRO_RESPONSES[0], input_tokens=100, output_tokens=200)
    mock_cls.return_value = client
    pro = ProAgent(gatekeeper, watchdog, logger)
    pro.generate_response("Argue PRO.")
    pro.generate_response("Refute CON.")
    assert gatekeeper.total_input_tokens == 200
    assert gatekeeper.total_output_tokens == 400


@patch("anthropic.Anthropic")
def test_logger_creates_structured_jsonl(mock_cls, infra):
    logger, gatekeeper, watchdog, tmp_path = infra
    client = MagicMock()
    client.messages.create.return_value = _fake_msg(PRO_RESPONSES[0])
    mock_cls.return_value = client
    pro = ProAgent(gatekeeper, watchdog, logger)
    pro.generate_response("Open argument.")
    log_files = list(Path(tmp_path / "logs").glob("debate_*.log"))
    assert len(log_files) >= 1
    with open(log_files[0]) as f:
        for line in f:
            entry = json.loads(line)
            assert {"ts", "level", "source", "msg"} <= entry.keys()
