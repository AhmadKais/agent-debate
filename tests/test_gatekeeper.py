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


def test_status_includes_rate_limit_fields():
    g = Gatekeeper(token_budget=1000, requests_per_minute=10)
    s = g.status()
    assert s["rpm_limit"] == 10
    assert s["rpm_used"] == 0


def test_rate_limit_not_enforced_when_zero():
    """requests_per_minute=0 means unlimited — _enforce_rate_limit returns immediately."""
    g = Gatekeeper(token_budget=10_000, requests_per_minute=0)
    for _ in range(20):
        g._enforce_rate_limit()
    assert len(g._rpm_window) == 0


def test_rate_limit_window_tracks_calls():
    """Each _enforce_rate_limit call (with rpm>0) appends a timestamp to the window."""
    g = Gatekeeper(token_budget=10_000, requests_per_minute=10)
    g._enforce_rate_limit()
    g._enforce_rate_limit()
    g._enforce_rate_limit()
    assert len(g._rpm_window) == 3


def test_load_rate_limits_returns_empty_for_missing_file():
    from src.core.config import load_rate_limits
    result = load_rate_limits("/nonexistent/path/rate_limits.json")
    assert result == {}


def test_rate_limit_window_concurrent():
    """RPM window is updated correctly under concurrent calls from multiple threads."""
    import threading

    g = Gatekeeper(token_budget=100_000, requests_per_minute=100)
    results: list[int] = []

    def call_enforce() -> None:
        g._enforce_rate_limit()
        results.append(1)

    threads = [threading.Thread(target=call_enforce) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 5
