"""
SDK layer tests — verifies DebateSDK is the single entry point
and returns a well-structured result dict.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.sdk import DebateSDK
from tests.mock_data import CON_RESPONSES, JUDGE_ROUTE_RESPONSE, JUDGE_VERDICT, PRO_RESPONSES


def _fake_msg(text: str, input_tokens: int = 50, output_tokens: int = 80):
    block = SimpleNamespace(type="text", text=text)
    usage = SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens)
    return SimpleNamespace(content=[block], usage=usage, stop_reason="end_turn")


@pytest.fixture
def sdk(tmp_path):
    """DebateSDK pointed at a temp log dir via a patched config."""
    instance = DebateSDK.__new__(DebateSDK)
    instance.cfg = {
        "model": "claude-sonnet-4-6",
        "max_pings": 3,
        "timeout_seconds": 30,
        "max_retries": 1,
        "token_budget": 150_000,
        "log_dir": str(tmp_path / "logs"),
        "log_max_files": 5,
        "log_max_lines": 100,
        "debate_topic": "Test topic",
        "language": "English",
    }
    return instance


@patch("anthropic.Anthropic")
def test_sdk_run_returns_required_keys(mock_cls, sdk):
    pro_iter = iter(PRO_RESPONSES)
    con_iter = iter(CON_RESPONSES)
    judge_n = {"n": 0}

    def judge_side(**kw):
        judge_n["n"] += 1
        return _fake_msg(JUDGE_VERDICT if judge_n["n"] > 6 else JUDGE_ROUTE_RESPONSE)

    clients = iter([
        MagicMock(messages=MagicMock(create=MagicMock(
            side_effect=lambda **kw: _fake_msg(next(pro_iter, PRO_RESPONSES[-1]))))),
        MagicMock(messages=MagicMock(create=MagicMock(
            side_effect=lambda **kw: _fake_msg(next(con_iter, CON_RESPONSES[-1]))))),
        MagicMock(messages=MagicMock(create=MagicMock(side_effect=judge_side))),
    ])
    mock_cls.side_effect = lambda **kw: next(clients)

    result = sdk.run()
    assert "topic" in result
    assert "transcript" in result
    assert "verdict" in result
    assert "token_usage" in result


@patch("anthropic.Anthropic")
def test_sdk_winner_is_never_tie(mock_cls, sdk):
    pro_iter = iter(PRO_RESPONSES)
    con_iter = iter(CON_RESPONSES)
    judge_n = {"n": 0}

    def judge_side(**kw):
        judge_n["n"] += 1
        return _fake_msg(JUDGE_VERDICT if judge_n["n"] > 6 else JUDGE_ROUTE_RESPONSE)

    clients = iter([
        MagicMock(messages=MagicMock(create=MagicMock(
            side_effect=lambda **kw: _fake_msg(next(pro_iter, PRO_RESPONSES[-1]))))),
        MagicMock(messages=MagicMock(create=MagicMock(
            side_effect=lambda **kw: _fake_msg(next(con_iter, CON_RESPONSES[-1]))))),
        MagicMock(messages=MagicMock(create=MagicMock(side_effect=judge_side))),
    ])
    mock_cls.side_effect = lambda **kw: next(clients)

    result = sdk.run()
    assert result["verdict"]["winner"] in ("Pro", "Con")
    assert result["verdict"]["winner"] != "Tie"


@patch("anthropic.Anthropic")
def test_sdk_callback_is_called_per_argument(mock_cls, sdk):
    client = MagicMock()
    client.messages.create.side_effect = [
        _fake_msg(PRO_RESPONSES[0]),   # pro opens
        _fake_msg(CON_RESPONSES[0]),   # con ping 1
        _fake_msg(JUDGE_ROUTE_RESPONSE),  # judge observe 1
        _fake_msg(JUDGE_ROUTE_RESPONSE),  # judge observe 2
        _fake_msg(JUDGE_VERDICT),         # declare winner
    ] + [_fake_msg(JUDGE_ROUTE_RESPONSE)] * 20
    mock_cls.return_value = client

    calls = []
    sdk.cfg["max_pings"] = 1
    sdk.run(on_argument=lambda side, name, arg, ping, tokens: calls.append(side))
    assert len(calls) >= 1
