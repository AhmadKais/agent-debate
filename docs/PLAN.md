# Architecture & Planning — AI Agent Debate System

---

## 1. Class Hierarchy (OOP)

```
BaseAgent
├── ProAgent   (AXIOM   — argues PRO, uses DuckDuckGo search)
├── ConAgent   (NEMESIS — argues CON, uses DuckDuckGo search)
└── JudgeAgent (THE ARBITER — routes messages, declares winner)

DebateSDK          — public facade, single entry point
Gatekeeper         — token budget + RPM rate limit enforcement
Watchdog           — timeout + exponential-backoff retry
FIFOLogger         — rotating structured JSONL logger
```

---

## 2. C4 Context Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Agent Debate System                   │
│                                                             │
│  ┌──────────┐   run(topic)   ┌─────────────────────────┐   │
│  │ Terminal │ ────────────►  │       DebateSDK         │   │
│  │  User    │                │  (single entry point)   │   │
│  └──────────┘                └──────────┬──────────────┘   │
│                                         │                   │
│              ┌──────────────────────────┼──────────────┐   │
│              ▼                          ▼              ▼   │
│        ┌──────────┐             ┌──────────┐   ┌──────────┐│
│        │ ProAgent │             │JudgeAgent│   │ConAgent  ││
│        │ (AXIOM)  │             │(ARBITER) │   │(NEMESIS) ││
│        └────┬─────┘             └────┬─────┘   └────┬─────┘│
│             │                        │               │      │
│             └────────────────────────┴───────────────┘      │
│                              │                              │
│                    ┌─────────▼──────────┐                  │
│                    │  Anthropic Claude  │  [external API]  │
│                    │  + DuckDuckGo      │  [external API]  │
│                    └────────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Message Flow (IPC Sequence)

All inter-agent communication is JSON-serialized via Pydantic `Message` objects.

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

## 4. Module Map

```
agent-debate/
├── src/
│   ├── sdk.py               ← DebateSDK (single entry point)
│   ├── constants.py         ← immutable project constants
│   ├── agents/
│   │   ├── base_agent.py    ← BaseAgent: LLM calls, tool use, history
│   │   ├── debater_agent.py ← ProAgent + ConAgent
│   │   ├── judge_agent.py   ← JudgeAgent: routing + verdict
│   │   └── prompts.py       ← all 3 system prompts (extracted for line-limit)
│   ├── core/
│   │   ├── config.py        ← config.json + rate_limits.json loaders
│   │   ├── gatekeeper.py    ← token budget + RPM rate limiting
│   │   ├── logger.py        ← FIFO JSONL logger
│   │   └── watchdog.py      ← timeout + retry wrapper
│   ├── data_types/
│   │   ├── message.py       ← Pydantic Message IPC model
│   │   └── debate_result.py ← Pydantic DebateResult model
│   └── tools/
│       └── search.py        ← DuckDuckGo web_search tool
├── tests/
│   ├── conftest.py
│   ├── mock_data.py
│   ├── test_gatekeeper.py
│   ├── test_logger.py
│   ├── test_watchdog.py
│   ├── test_integration.py
│   ├── test_agents_behavior.py
│   ├── test_sdk.py
│   └── test_data_types.py
├── config/
│   ├── config.json          ← all app parameters (token_budget, max_pings, …)
│   └── rate_limits.json     ← API RPM + concurrency config
├── docs/
│   ├── PRD.md  PLAN.md  TODO.md  PROMPT_BOOK.md
│   ├── PRD_judge_rules.md   ← per-mechanism PRD
│   ├── PRD_gatekeeper.md    ← per-mechanism PRD
│   ├── PRD_watchdog.md      ← per-mechanism PRD
│   ├── PRD_fifo_logger.md   ← per-mechanism PRD
│   └── PRD_ipc_messages.md  ← per-mechanism PRD
├── notebooks/
│   └── results_analysis.ipynb
├── scripts/
│   ├── mock_responses.json  ← mock debate data for simulation
│   ├── simulate_debate.py   ← offline demo (no API key needed)
│   └── generate_charts.py   ← matplotlib token/cost charts
└── results/
    ├── debate_social_media.json
    └── debate_soviet_union.json
```

---

## 5. UML Deployment Diagram

```
┌─────────────────── Developer Machine ─────────────────────┐
│                                                            │
│  ┌───────────────────────────────────────────────────┐    │
│  │           Python 3.12 Process (uv venv)           │    │
│  │                                                   │    │
│  │  main.py ──► DebateSDK ──► BaseAgent ──► Gatekeeper│   │
│  │                                   └──► Watchdog  │    │
│  │                                   └──► FIFOLogger│    │
│  │                                                   │    │
│  │  logs/debate_*.log  (JSONL, FIFO 20×500)          │    │
│  │  results/*.json     (debate transcripts)          │    │
│  └───────────────────────────────────────────────────┘    │
│                         │                                  │
│                         │ HTTPS                            │
└─────────────────────────┼──────────────────────────────────┘
                          │
          ┌───────────────┴──────────────┐
          │                              │
   ┌──────▼──────┐               ┌───────▼──────┐
   │  Anthropic  │               │  DuckDuckGo  │
   │  Claude API │               │  Search API  │
   │  (Messages) │               │  (ddgs pkg)  │
   └─────────────┘               └──────────────┘
```

---

## 6. Architectural Decisions (ADRs)

**ADR-1: SDK as single entry point**  
All external consumers (CLI, tests) go through `DebateSDK`. No direct imports from
`src.agents` in `main.py`. Reason: testability, separation of concerns.

**ADR-2: DuckDuckGo instead of Anthropic web_search tool**  
DuckDuckGo has no API key requirement and is free. Satisfies the "internet search
tool is mandatory" requirement without adding credentials.

**ADR-3: Pings reduced 10 → 5 (assignment-permitted, cost-justified)**  
The assignment explicitly states: *"ניתן להוריד מ-10 ל-5 — לא יגרע מהציון"* (§8.7 — "You may
reduce from 10 to 5; it will not reduce the grade"). Each side argues 5 times = 10 total
exchanges. Cost rationale: 10 pings/side consumes ~800k–1M tokens (~$5–6 per debate), which
is prohibitive for a demo system. 5 pings produces substantive 10-exchange debates at ~$2.40.

**ADR-4: BaseAgent holds conversation history**  
Each agent maintains its own `self.history` list for multi-turn context. Judge
history is separate from debater history.

**ADR-5: Rate limits merged into cfg at SDK init**  
`DebateSDK.__init__` loads `rate_limits.json` and merges RPM into `self.cfg`.
Tests that bypass `__init__` (via `__new__`) default to `requests_per_minute=0`
(unlimited), keeping the test suite fast without patching.

**ADR-6: Sequential debate execution (not parallel threads)**  
Agents execute one at a time: Pro → Judge → Con → Judge → Pro (strictly ordered turns).
A debate protocol is inherently sequential — each rebuttal must receive and process the
opponent's previous argument before forming a response. Parallel execution would require
synchronized message queues that still serialize turns at the logical level, adding
complexity with no benefit. The "separate agent instances" requirement (§8.5) is fully
satisfied: each agent is a distinct Python object with independent `history`,
`system_prompt`, and `_client` — no state is shared between Pro and Con.

---

## 7. Sequence Diagram (detailed UML)

```
main.py → DebateSDK.run()
              │
              ├─► Pro.generate_response() → Gatekeeper.execute()
              │         └─ Watchdog.run() → Anthropic API → record tokens
              │         └─ tool_use? → web_search() → follow-up call
              │
              ├─► Judge.observe("Pro", arg)
              │         └─ generate_response() → Gatekeeper.execute()
              │         └─ parse route_to JSON → return next speaker
              │
              ├─► [repeat for each ping] Con turn → Judge → Pro turn → Judge
              │
              └─► Judge.declare_winner()
                        └─ generate_response(transcript + violations)
                        └─ parse verdict JSON → attach violations list
```
