# PRD — API Gatekeeper

**Mechanism:** `Gatekeeper`  
**Module:** `src/core/gatekeeper.py`  
**Version:** 1.0 | **Author:** Ahmad Kais, Ali Trabeh

---

## 1. Purpose

Centralise every outbound Anthropic API call through a single gateway that enforces
a hard token budget and a sliding-window requests-per-minute (RPM) rate limit.
No agent code may call `anthropic.Anthropic.messages.create` directly.

---

## 2. Functional Requirements

| ID  | Requirement                  | Description                                                               |
|-----|------------------------------|---------------------------------------------------------------------------|
| G1  | Token budget enforcement     | Raise `BudgetExceededError` when `total_tokens >= token_budget`           |
| G2  | Two-phase enforcement        | Check budget **before** the call in `execute()`; check again in `record()`|
| G3  | RPM rate limiting            | Enforce `requests_per_minute` from `config/rate_limits.json` (§5.3)      |
| G4  | Sliding-window queue         | Use `collections.deque` with 60-second window; sleep until capacity frees  |
| G5  | Call count tracking          | Increment `_call_count` in `execute()`; expose via `status()`             |
| G6  | Status snapshot              | `status()` returns input/output/total tokens, budget, remaining, rpm info |

---

## 3. Acceptance Criteria

| Criterion | Expected Behaviour |
|-----------|--------------------|
| AC-G1 | `Gatekeeper(token_budget=100).record(50, 50)` raises `BudgetExceededError` |
| AC-G2 | `status()["remaining"]` equals `token_budget - total_tokens` |
| AC-G3 | `Gatekeeper(requests_per_minute=0)._enforce_rate_limit()` returns immediately |
| AC-G4 | `status()` dict includes `rpm_limit` and `rpm_used` keys |
| AC-G5 | `_rpm_window` grows by 1 per `_enforce_rate_limit()` call (when RPM > 0) |

---

## 4. Configuration Source

`requests_per_minute` is loaded from `config/rate_limits.json`:

```json
{ "services": { "anthropic": { "requests_per_minute": 10 } } }
```

`DebateSDK.__init__` reads this and injects it into `self.cfg["requests_per_minute"]`
so tests that bypass `__init__` (via `__new__`) default to 0 (unlimited).

---

## 5. Constraints

- `gatekeeper.py` ≤ 150 lines.
- `RateLimitExceededError` is defined for future use (e.g., hard abort instead of sleep).
- No direct calls to `anthropic` package from agent code — gateway pattern is mandatory.
