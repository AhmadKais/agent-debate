import pytest

from src.core.gatekeeper import BudgetExceededError, Gatekeeper


def test_records_tokens():
    g = Gatekeeper(token_budget=1000)
    g.record(input_tokens=100, output_tokens=50)
    assert g.total_input_tokens == 100
    assert g.total_output_tokens == 50
    assert g.total_tokens == 150


def test_raises_on_budget_exceeded():
    g = Gatekeeper(token_budget=100)
    with pytest.raises(BudgetExceededError):
        g.record(input_tokens=60, output_tokens=50)


def test_status_shows_remaining():
    g = Gatekeeper(token_budget=500)
    g.record(input_tokens=100, output_tokens=100)
    s = g.status()
    assert s["remaining"] == 300
    assert s["total_tokens"] == 200


def test_exact_budget_raises():
    g = Gatekeeper(token_budget=100)
    with pytest.raises(BudgetExceededError):
        g.record(input_tokens=50, output_tokens=50)
