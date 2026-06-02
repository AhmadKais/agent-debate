# PRD — AI Agent Debate System

**Document version:** 1.0  
**Date:** 2026-06-01  
**Authors:** Ahmad Kais, Ali Trabeh  
**Course:** AI Orchestration (Dr. Yoram Segal) — Exercise 02

---

## 1. Project Overview

Build a three-agent AI debate system where a Pro agent and a Con agent argue opposite sides
of a topic, supervised by a Judge agent that routes all messages and declares a non-tie
winner. All communication uses JSON IPC. The system must be operable from a terminal menu,
reproducible via a single SDK entry point, and hardened with budget enforcement,
rate limiting, timeout/retry, and structured logging.

**Target users:** Course evaluator, fellow students, developers exploring multi-agent
orchestration patterns.

---

## 2. User Stories

| ID  | As a…            | I want to…                                             | So that…                                           |
|-----|------------------|--------------------------------------------------------|----------------------------------------------------|
| US1 | Course evaluator | Run a full debate from the terminal in under 5 minutes | I can verify the system works end-to-end           |
| US2 | Developer        | Import `DebateSDK` and call `.run(topic)`              | I can embed debates in any Python application      |
| US3 | Researcher       | Set a custom topic via CLI or SDK parameter            | I can explore any debate domain                    |
| US4 | Student          | See which agent violated a rule and why                | I can learn how LLM content moderation works       |
| US5 | Budget-conscious | Have the system stop automatically at a token limit    | I never pay more than the configured ceiling       |
| US6 | Developer        | Run tests without an API key                           | I can work offline and in CI environments          |

---

## 3. Functional Requirements

| ID  | Requirement                   | Acceptance Criteria                                                        |
|-----|-------------------------------|----------------------------------------------------------------------------|
| F1  | Pro agent argues one side     | Output is valid JSON `{"argument": ..., "references_used": [...]}`         |
| F2  | Con agent argues opposite     | Same JSON schema; agent never agrees with Pro                              |
| F3  | Judge routes all messages     | Every message flows `Pro → Judge → Con → Judge → Pro`                      |
| F4  | Min 5 pings per side          | `len(transcript) >= 10` (reduced from 10 for cost; documented in §9.7)    |
| F5  | Judge declares winner, no tie | `verdict["winner"] in ("Pro", "Con")`                                      |
| F6  | Web search tool mandatory     | Each debater calls DuckDuckGo for at least one real citation               |
| F7  | JSON IPC between agents       | All inter-agent messages serializable as `Message` Pydantic objects        |
| F8  | Structured JSONL logging      | `logs/debate_*.log` files with `{ts, level, source, msg}` per line        |
| F9  | Budget enforcement            | Raises `BudgetExceededError` at `token_budget` tokens                      |
| F10 | Rate limiting                 | Sliding-window RPM enforcement from `rate_limits.json` via `Gatekeeper`    |
| F11 | Timeout + retry on API calls  | Watchdog wraps every call; retries with exponential back-off               |
| F12 | Fallback verdict fairness     | If verdict JSON fails to parse, winner is decided by violation count       |

---

## 4. Non-Functional Requirements

- All Python files ≤ 150 lines
- Test coverage ≥ 85% (`pytest-cov`)
- Zero Ruff lint violations (rules: E,F,W,I,N,UP,B,C4,SIM; ignore only E501)
- No hardcoded values — all parameters in `config/config.json` or `config/rate_limits.json`
- API key only via `ANTHROPIC_API_KEY` environment variable
- `uv` only (no pip)

---

## 5. System Architecture

```
External (CLI / SDK)
        │
    DebateSDK          ← single entry point
        │
  ┌─────┼──────┐
ProAgent  ConAgent  JudgeAgent
   └── BaseAgent (LLM calls, tool use, history)
        │
   Gatekeeper → token budget + RPM rate limit
   Watchdog   → timeout + exponential back-off retry
   FIFOLogger → structured JSONL logs
```

Per-mechanism PRDs: `PRD_gatekeeper.md`, `PRD_watchdog.md`, `PRD_fifo_logger.md`,
`PRD_judge_rules.md`, `PRD_ipc_messages.md`.

---

## 6. KPIs

| Metric               | Target                          |
|----------------------|---------------------------------|
| Rounds completed     | ≥ 5 per side                    |
| Winner declared      | Always (no tie)                 |
| Token cost per debate| ≤ 400,000 tokens (~$2.40)       |
| Test coverage        | ≥ 85%                           |
| Lint violations      | 0                               |
| Rule violations caught | ≥ 1 per 5-round debate (live) |

---

## 7. Timeline / Milestones

| Phase | Milestone                                   | Target Date |
|-------|---------------------------------------------|-------------|
| 1     | Repo scaffolding, BaseAgent, Gatekeeper     | 2026-05-25  |
| 2     | ProAgent, ConAgent, JudgeAgent, SDK         | 2026-05-27  |
| 3     | Watchdog, FIFOLogger, IPC types             | 2026-05-28  |
| 4     | Web search tool, 8-rule judge moderation    | 2026-05-29  |
| 5     | TDD (≥85% coverage), Ruff zero violations   | 2026-05-31  |
| 6     | Live debate runs, docs, README, submission  | 2026-06-01  |

---

## 8. Out of Scope

The following are explicitly **not** part of this submission:

- Multi-process IPC using OS-level FIFO pipes or sockets (agents run in-process)
- REST API or web frontend
- Persistent database for debate history
- Authentication / authorisation layer
- Real-time streaming of tokens to the UI
- Support for non-English debate languages (configurable but untested)
