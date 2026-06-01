# PRD — AI Agent Debate System

**Document version:** 1.0  
**Date:** 2026-06-01  
**Authors:** Ahmad Kais, Ali Trabeh  
**Course:** AI Orchestration (Dr. Yoram Segal) — Exercise 02

---

## 1. Project Overview

Build a three-agent AI debate system where a Pro agent and a Con agent argue opposite sides of a topic, supervised by a Judge agent that routes all messages and declares a non-tie winner.

**Target users:** Course evaluator, fellow students, developers exploring multi-agent orchestration.

---

## 2. Functional Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| F1 | Pro agent argues one side | Output is valid JSON `{"argument": ..., "references_used": [...]}` |
| F2 | Con agent argues opposite | Same JSON schema; never agrees with Pro |
| F3 | Judge routes all messages | Every message goes `Pro → Judge → Con → Judge → Pro` |
| F4 | Min 5 pings per side | `len(transcript) >= 10` (reduced from 10 for cost) |
| F5 | Judge declares winner, no tie | `verdict["winner"] in ("Pro", "Con")` |
| F6 | Web search tool mandatory | Each debater calls DuckDuckGo for at least one real citation |
| F7 | JSON IPC between agents | All inter-agent messages serializable as `Message` dicts |
| F8 | Structured JSONL logging | `logs/debate_*.log` files with `{ts, level, source, msg}` lines |
| F9 | Budget enforcement | Raises `BudgetExceededError` at `token_budget` tokens |
| F10 | Timeout + retry on API calls | Watchdog wraps every call; retries with back-off |

---

## 3. Non-Functional Requirements

- All Python files ≤ 150 lines
- Test coverage ≥ 85% (`pytest-cov`)
- Zero Ruff lint violations
- No hardcoded values — all parameters in `config/config.json`
- API key only via `ANTHROPIC_API_KEY` environment variable
- `uv` only (no pip)

---

## 4. System Architecture

```
External (CLI / SDK)
        │
    DebateSDK          ← single entry point
        │
  ┌─────┼──────┐
ProAgent  ConAgent  JudgeAgent
   └── BaseAgent (LLM calls, tool use, history)
        │
   Gatekeeper → token budget
   Watchdog   → timeout + retry
   FIFOLogger → structured JSONL logs
```

---

## 5. KPIs

| Metric | Target |
|--------|--------|
| Rounds completed | ≥ 5 per side |
| Winner declared | Always (no tie) |
| Token cost per debate | ≤ 150,000 tokens (~$0.45) |
| Test coverage | ≥ 85% |
| Lint violations | 0 |
