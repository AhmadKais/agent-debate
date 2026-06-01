"""Tests for Pydantic data types: Message and DebateResult."""

import json

import pytest

from src.data_types.debate_result import DebateResult
from src.data_types.message import Message


class TestMessage:
    def test_serializes_to_dict(self):
        msg = Message(round=1, sender="pro", recipient="con", content="Test argument")
        d = msg.to_ipc_dict()
        assert d["round"] == 1
        assert d["sender"] == "pro"
        assert d["content"] == "Test argument"
        assert "timestamp" in d

    def test_roundtrip_json(self):
        msg = Message(round=2, sender="con", recipient="judge", content="Counter", references=["http://x.com"])
        restored = Message.from_ipc_dict(json.loads(json.dumps(msg.to_ipc_dict())))
        assert restored.round == 2
        assert restored.sender == "con"
        assert restored.references == ["http://x.com"]

    def test_summary_is_short(self):
        msg = Message(round=3, sender="judge", recipient="pro", content="A" * 200)
        assert len(msg.summary()) < 120

    def test_default_references_empty(self):
        msg = Message(round=1, sender="pro", recipient="con", content="arg")
        assert msg.references == []

    def test_timestamp_auto_set(self):
        msg = Message(round=1, sender="pro", recipient="con", content="arg")
        assert msg.timestamp != ""
        assert "T" in msg.timestamp  # ISO format


class TestDebateResult:
    def test_valid_pro_winner(self):
        r = DebateResult(topic="T", winner="Pro", score_pro=60, score_con=40, reason="Pro won")
        assert r.winner == "Pro"

    def test_valid_con_winner(self):
        r = DebateResult(topic="T", winner="Con", score_pro=45, score_con=55, reason="Con won")
        assert r.winner == "Con"

    def test_tie_rejected(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            DebateResult(topic="T", winner="Tie", score_pro=50, score_con=50, reason="Draw")

    def test_score_out_of_range_rejected(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            DebateResult(topic="T", winner="Pro", score_pro=150, score_con=40, reason="x")

    def test_serializes_to_dict(self):
        r = DebateResult(topic="T", winner="Pro", score_pro=70, score_con=30, reason="x", total_tokens=5000)
        d = r.to_dict()
        assert d["winner"] == "Pro"
        assert d["total_tokens"] == 5000
