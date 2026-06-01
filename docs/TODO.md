# TODO — AI Agent Debate System

## Phase 1: Core Implementation ✅
- [x] BaseAgent with LLM calls, tool use, history management
- [x] ProAgent (AXIOM) with distinct system prompt and search strategy
- [x] ConAgent (NEMESIS) with distinct system prompt and search strategy
- [x] JudgeAgent (THE ARBITER) with routing and no-tie verdict
- [x] DuckDuckGo web search tool integration
- [x] Gatekeeper: token budget enforcement with BudgetExceededError
- [x] Watchdog: timeout + exponential back-off retry
- [x] FIFOLogger: rotating JSONL structured logging

## Phase 2: Architecture ✅
- [x] DebateSDK facade (single entry point)
- [x] src/constants.py (immutable constants)
- [x] config/config.json (all parameters, no hardcoding)
- [x] config/rate_limits.json (API rate limit config)
- [x] main.py CLI (thin UI layer using SDK)

## Phase 3: Tests ✅
- [x] test_gatekeeper.py (4 tests — budget enforcement)
- [x] test_logger.py (4 tests — FIFO rotation, JSON format)
- [x] test_watchdog.py (3 tests — timeout, retry)
- [x] test_integration.py (3 tests — orchestration, token tracking, logging)
- [x] test_agents_behavior.py (5 tests — JSON format, no-tie, mutual ref)
- [x] test_sdk.py (3 tests — SDK entry point, winner check, callback)
- [x] ≥ 85% coverage configured (fail_under = 85)

## Phase 4: Documentation ✅
- [x] docs/PRD.md
- [x] docs/PLAN.md (architecture + class hierarchy)
- [x] docs/TODO.md (this file)
- [x] docs/PROMPT_BOOK.md
- [x] README.md with setup, run, test, cost estimate, sample transcript

## Phase 5: Quality ✅
- [x] Ruff: all rules enabled, zero violations
- [x] All files ≤ 150 lines
- [x] .env.example committed, .env gitignored
- [x] No hardcoded API keys
- [x] uv sync + uv run confirmed

## Remaining / Future
- [ ] Add GUI mode (optional stretch goal)
- [ ] Support custom topic via CLI --topic flag
- [ ] Add rate limiting queue to Gatekeeper (currently uses simple budget only)
