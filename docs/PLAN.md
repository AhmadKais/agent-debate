# Architecture & Planning — AI Agent Debate System

---

## 1. Class Hierarchy (OOP)

```
BaseAgent
├── ProAgent   (AXIOM   — argues PRO, uses DuckDuckGo search)
├── ConAgent   (NEMESIS — argues CON, uses DuckDuckGo search)
└── JudgeAgent (THE ARBITER — routes messages, declares winner)

DebateSDK          — public facade, single entry point
Gatekeeper         — token budget enforcement
Watchdog           — timeout + exponential-backoff retry
FIFOLogger         — rotating structured JSONL logger
```

---

## 2. Message Flow (IPC)

All inter-agent communication is JSON-serialized. No agent calls another directly.

```
CLI / SDK
    │
    ▼
DebateSDK.run()
    │
    ├─ Pro.generate_response(opening)
    │       └─ Judge.observe("Pro", arg)       ← child→papa
    │
    └─ for ping in range(max_pings):
           ├─ Con.generate_response(pro_arg)
           │       └─ Judge.observe("Con", arg)   ← child→papa
           │
           └─ Pro.generate_response(con_arg)
                   └─ Judge.observe("Pro", arg)   ← child→papa
    │
    └─ Judge.declare_winner() → {"winner", "reason", "score_pro", "score_con"}
```

---

## 3. Module Map

```
agent-debate/
├── src/
│   ├── sdk.py               ← DebateSDK (single entry point)
│   ├── constants.py         ← immutable project constants
│   ├── agents/
│   │   ├── base_agent.py    ← BaseAgent: LLM calls, tool use, history
│   │   ├── debater_agent.py ← ProAgent + ConAgent
│   │   └── judge_agent.py   ← JudgeAgent: routing + verdict
│   ├── core/
│   │   ├── config.py        ← config.json loader
│   │   ├── gatekeeper.py    ← token budget
│   │   ├── logger.py        ← FIFO JSONL logger
│   │   └── watchdog.py      ← timeout + retry wrapper
│   └── tools/
│       └── search.py        ← DuckDuckGo web_search tool
├── tests/
│   ├── conftest.py
│   ├── mock_data.py         ← shared mock API responses
│   ├── test_gatekeeper.py
│   ├── test_logger.py
│   ├── test_watchdog.py
│   ├── test_integration.py
│   ├── test_agents_behavior.py
│   └── test_sdk.py
├── config/
│   ├── config.json          ← all app parameters
│   └── rate_limits.json     ← API rate limit config
└── docs/
    ├── PRD.md  PLAN.md  TODO.md  PROMPT_BOOK.md
```

---

## 4. Architectural Decisions (ADRs)

**ADR-1: SDK as single entry point**  
All external consumers (CLI, tests) go through `DebateSDK`. No direct imports from `src.agents` in `main.py`. Reason: testability, separation of concerns.

**ADR-2: DuckDuckGo instead of Anthropic web_search tool**  
DuckDuckGo has no API key requirement and is free. Satisfies the "internet search tool is mandatory" requirement without adding credentials.

**ADR-3: Pings reduced 10 → 5**  
Budget constraint (~$0.45 per full debate). Explicitly permitted by assignment if documented.

**ADR-4: BaseAgent holds conversation history**  
Each agent maintains its own `self.history` list for multi-turn context. Judge history is separate from debater history.

---

## 5. Sequence Diagram (simplified UML)

```
main.py → DebateSDK.run()
              │
              ├─► Pro.generate_response() → Anthropic API
              │         └─ Watchdog wraps (timeout/retry)
              │         └─ Gatekeeper records tokens
              │
              ├─► Judge.observe("Pro", arg)
              │
              ├─► [repeat for each ping] Con turn → Judge → Pro turn → Judge
              │
              └─► Judge.declare_winner() → verdict JSON
```
