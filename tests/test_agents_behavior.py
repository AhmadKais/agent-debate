"""
Agent behavior tests: JSON output format, judge no-tie rule, mutual reference.
Uses mocked Anthropic API — no real API key required.
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.agents.debater_agent import ConAgent, ProAgent
from src.agents.judge_agent import JudgeAgent
from src.core.gatekeeper import Gatekeeper
from src.core.logger import FIFOLogger
from src.core.watchdog import Watchdog
from tests.mock_data import CON_RESPONSES, JUDGE_VERDICT, PRO_RESPONSES


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
    return logger, gatekeeper, watchdog


@patch("anthropic.Anthropic")
def test_pro_argument_is_valid_json(mock_cls, infra):
    logger, gatekeeper, watchdog = infra
    client = MagicMock()
    client.messages.create.return_value = _fake_msg(PRO_RESPONSES[0])
    mock_cls.return_value = client
    pro = ProAgent(gatekeeper, watchdog, logger)
    raw = pro.generate_response("Argue PRO on Linux vs Windows.")
    data = json.loads(raw)
    assert "argument" in data
    assert "references_used" in data
    assert isinstance(data["references_used"], list)


@patch("anthropic.Anthropic")
def test_con_argument_is_valid_json(mock_cls, infra):
    logger, gatekeeper, watchdog = infra
    client = MagicMock()
    client.messages.create.return_value = _fake_msg(CON_RESPONSES[0])
    mock_cls.return_value = client
    con = ConAgent(gatekeeper, watchdog, logger)
    raw = con.generate_response("Counter the PRO argument.")
    data = json.loads(raw)
    assert "argument" in data
    assert "references_used" in data


@patch("anthropic.Anthropic")
def test_judge_verdict_has_no_tie(mock_cls, infra):
    logger, gatekeeper, watchdog = infra
    client = MagicMock()
    client.messages.create.return_value = _fake_msg(JUDGE_VERDICT)
    mock_cls.return_value = client
    judge = JudgeAgent(gatekeeper, watchdog, logger)
    judge.debate_transcript = [
        {"side": "Pro", "argument": PRO_RESPONSES[0]},
        {"side": "Con", "argument": CON_RESPONSES[0]},
    ]
    verdict = judge.declare_winner()
    assert verdict["winner"] in ("Pro", "Con")
    assert verdict["score_pro"] != verdict["score_con"]


@patch("anthropic.Anthropic")
def test_con_prompt_contains_pro_argument(mock_cls, infra):
    """Con prompt must include Pro's argument to satisfy mutual-reference requirement."""
    logger, gatekeeper, watchdog = infra
    captured = []

    def capture(**kwargs):
        msgs = kwargs.get("messages", [])
        for m in msgs:
            if m["role"] == "user":
                captured.append(m["content"])
        return _fake_msg(CON_RESPONSES[0])

    client = MagicMock()
    client.messages.create.side_effect = capture
    mock_cls.return_value = client

    con = ConAgent(gatekeeper, watchdog, logger)
    pro_arg = json.loads(PRO_RESPONSES[0])["argument"]
    con.generate_response(f'Ping 1: Pro argued:\n"{pro_arg}"\n\nTear it apart.')
    assert any(pro_arg[:40] in str(p) for p in captured), (
        "Con prompt must contain Pro's argument for mutual reference"
    )


@patch("anthropic.Anthropic")
def test_judge_fallback_on_malformed_verdict(mock_cls, infra):
    """Judge must not crash when LLM returns non-JSON; must still return a winner."""
    logger, gatekeeper, watchdog = infra
    client = MagicMock()
    client.messages.create.return_value = _fake_msg("I cannot decide, both sides are equal.")
    mock_cls.return_value = client
    judge = JudgeAgent(gatekeeper, watchdog, logger)
    judge.debate_transcript = [{"side": "Pro", "argument": "test"}]
    verdict = judge.declare_winner()
    assert "winner" in verdict
    assert verdict["winner"] in ("Pro", "Con")


@patch("anthropic.Anthropic")
def test_recursive_tool_use_resolves_to_text(mock_cls, infra):
    """Agent must handle a second tool_use call in the follow-up (recursive handling)."""
    logger, gatekeeper, watchdog = infra
    from types import SimpleNamespace

    def _tool_msg(tool_id="t1"):
        block = SimpleNamespace(type="tool_use", id=tool_id, name="web_search", input={"query": "test"})
        usage = SimpleNamespace(input_tokens=10, output_tokens=5)
        return SimpleNamespace(content=[block], usage=usage, stop_reason="tool_use")

    final_msg = _fake_msg(json.dumps({"argument": "final answer", "references_used": []}))
    client = MagicMock()
    client.messages.create.side_effect = [_tool_msg("t1"), _tool_msg("t2"), final_msg]
    mock_cls.return_value = client

    with patch("src.tools.search.web_search", return_value=[]):
        pro = ProAgent(gatekeeper, watchdog, logger)
        result = pro.generate_response("Open argument.")

    assert "final answer" in result


def test_web_search_returns_list():
    """web_search returns a list even when DuckDuckGo is unavailable."""
    with patch("src.tools.search.DDGS") as mock_ddgs:
        mock_ddgs.return_value.__enter__.return_value.text.return_value = [
            {"title": "T", "href": "http://x.com", "body": "snippet text here"}
        ]
        from src.tools.search import web_search
        results = web_search("test")
    assert isinstance(results, list)
    assert results[0]["title"] == "T"
    assert results[0]["url"] == "http://x.com"
