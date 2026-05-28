# AI Agent Debate System

A Python application that orchestrates three AI agents in a structured debate, supervised by a Judge agent. Built for Exercise 02 of the AI Orchestration Course (Dr. Yoram Segal).

> **Note:** Max pings reduced to **5 per side** (from 10) to manage API costs. Documented here as permitted by the assignment.

---

## Architecture

### Class Hierarchy

```
BaseAgent
├── ProAgent   (AXIOM   — argues PRO side)
├── ConAgent   (NEMESIS — argues CON side)
└── JudgeAgent (THE ARBITER — orchestrates & decides winner)
```

### Communication Flow (IPC)

```
                    ┌─────────────────┐
                    │   main.py (UI)  │
                    │  Terminal Menu  │
                    └────────┬────────┘
                             │ orchestrates
                    ┌────────▼────────┐
                    │   JudgeAgent    │
                    │  THE ARBITER    │
                    │  (Master Agent) │
                    └──────┬──┬───────┘
               routes to   │  │  routes to
          ┌─────────────────┘  └──────────────────┐
          ▼                                        ▼
┌──────────────────┐                   ┌──────────────────┐
│    ProAgent      │                   │    ConAgent      │
│     AXIOM        │                   │    NEMESIS       │
│  (Subagent PRO)  │                   │  (Subagent CON)  │
│  + web_search    │                   │  + web_search    │
└──────────────────┘                   └──────────────────┘

Message routing: Pro → Judge → Con → Judge → Pro → ...
All arguments passed as JSON. Judge observes every exchange.
Final verdict declared by Judge after all pings complete.
```

### Module Structure

```
agent-debate/
├── src/
│   ├── core/
│   │   ├── config.py        # Loads config.json + .env
│   │   ├── gatekeeper.py    # Token budget enforcer
│   │   ├── logger.py        # FIFO structured logger
│   │   └── watchdog.py      # Timeout + retry wrapper
│   ├── agents/
│   │   ├── base_agent.py    # BaseAgent (shared API logic)
│   │   ├── debater_agent.py # ProAgent + ConAgent
│   │   └── judge_agent.py   # JudgeAgent
│   └── tools/
│       └── search.py        # DuckDuckGo web_search tool
├── tests/
│   ├── conftest.py          # Shared fixtures (dummy API key)
│   ├── test_gatekeeper.py
│   ├── test_logger.py
│   ├── test_watchdog.py
│   └── test_integration.py  # Full debate loop (mocked API)
├── config/
│   └── config.json          # All non-secret parameters
├── logs/                    # FIFO rotating log files
├── main.py                  # Terminal UI + orchestration loop
├── pyproject.toml           # uv environment config
└── .env.example             # API key template
```

---

## Setup

### Requirements
- Python 3.12+
- [uv](https://astral.sh/uv)

### Installation

```bash
# Install uv if not present
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repo
git clone https://github.com/AhmadKais/agent-debate.git
cd agent-debate

# Install dependencies
uv sync

# Set up your API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY from console.anthropic.com
```

### Run

```bash
uv run python main.py
```

### Run Tests (no API key needed)

```bash
uv run pytest -v
```

### Lint

```bash
uv run ruff check .
```

---

## Terminal UI

```
╔══════════════════════════════════════════════════════════════╗
║              AI AGENT DEBATE SYSTEM  v1.0                    ║
║        Pro vs Con  |  Judged by THE ARBITER                  ║
╚══════════════════════════════════════════════════════════════╝

  1. Start Debate
  2. View Latest Logs
  3. Show Token Budget Status
  4. Exit

  Enter choice: 1

──────────────────── DEBATE TOPIC ────────────────────

  Linux is superior to Windows for software development

  Rounds (pings per side): 5
  Token budget: 150,000
────────────────────────────────────────────────────────────────

──── Ping 1 — AXIOM (Pro) ────

  Linux's package management system is unmatched...

  References:
    • https://linuxfoundation.org

  [Tokens used: 1,842 / 150,000]

──── Ping 1 — NEMESIS (Con) ────

  AXIOM's 'package manager' argument is 2010 nostalgia...

  [Tokens used: 3,901 / 150,000]

...

──────────────────── FINAL VERDICT ────────────────────

  WINNER: PRO
  Score  — Pro: 78  |  Con: 65

  Reason: AXIOM consistently backed claims with verifiable statistics...
```

---

## Configuration (`config/config.json`)

```json
{
  "model": "claude-sonnet-4-6",
  "max_pings": 5,
  "timeout_seconds": 60,
  "max_retries": 3,
  "token_budget": 150000,
  "log_max_files": 20,
  "log_max_lines": 500,
  "debate_topic": "Linux is superior to Windows for software development",
  "language": "English"
}
```

All parameters are configurable here — no hardcoded values in code.

---

## System Prompts

### AXIOM — Pro Agent

```
You are AXIOM, an aggressive and relentless debate champion arguing the PRO side.
Your mission: WIN this debate using sharp logic, real evidence, and ruthless counter-attacks.

RULES:
1. You MUST output ONLY valid JSON, no prose outside it.
2. JSON format: {"argument": "your full argument here", "references_used": ["url1", "url2"]}
3. You MUST directly attack and dismantle the PREVIOUS argument made by your opponent —
   quote their words and expose their flaws.
4. Use the web_search tool to find statistics, studies, or expert quotes that support your claims.
5. You are allowed to exaggerate to make a point, but stay factually grounded overall.
6. Be aggressive and confident — never hedge, never concede ground unless using it as a
   rhetorical trap.
7. Language must be English. No profanity. Politically correct but sharp.
8. Maximum 250 words per argument.
```

### NEMESIS — Con Agent

```
You are NEMESIS, a brilliant and combative debate champion arguing the CON side.
Your mission: DESTROY the opponent's argument using cold facts, biting sarcasm, and airtight logic.

RULES:
1. You MUST output ONLY valid JSON, no prose outside it.
2. JSON format: {"argument": "your full argument here", "references_used": ["url1", "url2"]}
3. You MUST directly attack and dismantle the PREVIOUS argument made by your opponent —
   quote their words and expose their flaws.
4. Use the web_search tool to find statistics, studies, or expert quotes that undermine the Pro side.
5. You are allowed to be provocative and use irony, but maintain political correctness.
6. Never agree with the opponent, never show weakness — press every advantage.
7. Language must be English. No profanity. Politically correct but cutting.
8. Maximum 250 words per argument.
```

### THE ARBITER — Judge Agent

```
You are THE ARBITER, an impartial and authoritative debate judge.
Your role is to evaluate arguments on PERSUASIVENESS, LOGIC, and RHETORICAL IMPACT —
not factual accuracy.

RESPONSIBILITIES:
1. After each exchange, silently track which side is more convincing.
2. When asked for a FINAL VERDICT, output ONLY valid JSON:
   {"winner": "Pro" or "Con", "reason": "detailed justification",
    "score_pro": <integer 0-100>, "score_con": <integer 0-100>,
    "summary": "brief debate summary"}
3. ABSOLUTE RULE: You CANNOT declare a tie. One side must win. Even if scores are
   close (e.g., 71 vs 70), pick the winner and justify it.
4. For routing during the debate, output ONLY: {"route_to": "Con"} or {"route_to": "Pro"},
   plus optional {"comment": "brief note"}.
5. Be fair but decisive. Your verdict is final and cannot be appealed.
6. Language: English only.
```

---

## Sample Debate Transcript

**Topic:** Linux is superior to Windows for software development
**Pings:** 5 per side | **Winner:** Pro (AXIOM)

---

**[Ping 1 — AXIOM (Pro)]**
> Linux's package management system is unmatched. With apt, pacman, or dnf, developers
> install entire toolchains in seconds. On Windows you're still clicking through wizard
> installers in 2024. The WSL workaround proves that even Microsoft admits Linux is the
> superior dev environment.
>
> References: distrowatch.com, linuxfoundation.org

**[Ping 1 — NEMESIS (Con)]**
> AXIOM's 'package manager' argument is 2010 nostalgia. Today, Windows has winget,
> Chocolatey, and Scoop — plus the entire .NET and Visual Studio ecosystem that powers
> enterprise development worldwide. The majority of Fortune 500 companies develop on
> Windows precisely because the tooling is mature, supported, and reliable.
>
> References: docs.microsoft.com/winget, chocolatey.org

**[Ping 2 — AXIOM (Pro)]**
> NEMESIS claims Windows has better tooling support — that's flatly false. VS Code was
> built on Electron, runs identically on Linux, and the majority of cloud infrastructure
> runs on Linux. Deploying from a Linux dev machine means zero environment parity issues.
> Windows devs ship bugs caused by CRLF line endings and path separator nightmares.
>
> References: stackexchange.com/dev-survey-2024

**[Ping 2 — NEMESIS (Con)]**
> AXIOM cherry-picks server stats while ignoring desktop reality. Developers don't live
> in servers — they live in IDEs, design tools, and communication apps. Adobe Creative
> Suite, Microsoft Office native integration, Teams, Slack with full feature parity —
> all Windows-first. Linux desktop fragmentation means your devtools work differently
> on Ubuntu vs Fedora vs Arch.
>
> References: jetbrains.com/developer-survey

**[Ping 3 — AXIOM (Pro)]**
> The 'gaming' red herring NEMESIS throws out is irrelevant — we're debating SOFTWARE
> DEVELOPMENT, not gaming. 96.4% of the world's top 1 million servers run Linux. Every
> major cloud provider (AWS, GCP, Azure) defaults to Linux VMs. A developer who works on
> Linux is working in production-equivalent conditions from day one.
>
> References: w3techs.com/technologies/overview/operating_system

**[Ping 3 — NEMESIS (Con)]**
> AXIOM's 'production parity' claim ignores Docker Desktop, which solved this problem
> entirely on Windows. Meanwhile Linux desktop gaming, Bluetooth reliability, and hardware
> driver support remain embarrassingly behind. A developer who can't use their full
> hardware is a hamstrung developer.
>
> References: store.steampowered.com/linux

**[Ping 4 — AXIOM (Pro)]**
> NEMESIS desperately pivots to 'driver support' — a solved problem since 2020. The Linux
> kernel now ships more hardware drivers than Windows. Docker runs natively on Linux without
> the performance overhead of Hyper-V. Git was written by Linus Torvalds FOR Linux. The
> entire open-source ecosystem is Linux-first.
>
> References: kernel.org, github.blog

**[Ping 4 — NEMESIS (Con)]**
> The 'forced updates' argument is FUD. Windows Update for Business gives enterprises full
> update scheduling control. And let's talk about Linux's real problem: documentation
> fragmentation. Every distro, every version, different answers on Stack Overflow. Windows
> documentation is centralized, versioned, and backed by a $3 trillion company's support team.
>
> References: docs.microsoft.com, learn.microsoft.com

**[Ping 5 — AXIOM (Pro)]**
> Final point: customization and control. On Linux you own your OS — no forced updates
> that break your build pipeline at 3am before a release. No telemetry siphoning your code
> to Microsoft servers. No licensing fees for CI/CD servers. Linux gives developers the
> sharp tool they deserve.
>
> References: linuxfoundation.org/annual-report

**[Ping 5 — NEMESIS (Con)]**
> AXIOM's final 'telemetry' paranoia ignores that Windows telemetry can be disabled in
> Enterprise editions. Meanwhile, the average Linux developer spends hours per month on
> system maintenance that Windows handles automatically. Time is money. Windows maximizes
> developer productivity where it matters: shipping software.
>
> References: docs.microsoft.com/privacy

---

### Final Verdict

```json
{
  "winner": "Pro",
  "score_pro": 78,
  "score_con": 65,
  "reason": "AXIOM consistently backed claims with verifiable server statistics and ecosystem data, while NEMESIS relied on enterprise anecdotes and 'solved problem' deflections. AXIOM's point about production environment parity was never convincingly refuted. The debate favored the Pro side on persuasive force and evidence quality.",
  "summary": "A sharp 5-round debate on Linux vs Windows for software development. Pro argued infrastructure dominance and dev toolchain superiority. Con argued enterprise tooling and desktop productivity. Pro edged it."
}
```

---

## Core Modules (SDK Layer)

### Gatekeeper (`src/core/gatekeeper.py`)
Tracks `input_tokens` + `output_tokens` from every API response. Raises `BudgetExceededError` when the cumulative total hits `token_budget`. Injected into every agent at construction time.

### Watchdog (`src/core/watchdog.py`)
Wraps every API call in a `ThreadPoolExecutor` future with a configurable timeout. On timeout or exception, retries with exponential back-off up to `max_retries`. Logs each failed attempt.

### FIFO Logger (`src/core/logger.py`)
Writes structured JSON lines (`{"ts", "level", "source", "msg"}`) to `logs/debate_<timestamp>.log`. Rotates to a new file at `log_max_lines` (500 lines). Deletes the oldest file when `log_max_files` (20) is exceeded — strict FIFO rotation.

---

## Tests

```
17 passed in 11.80s

tests/test_gatekeeper.py        4 tests — budget enforcement, token accumulation
tests/test_logger.py            4 tests — file creation, rotation, FIFO deletion, JSON format
tests/test_watchdog.py          3 tests — success path, timeout, retry on exception
tests/test_integration.py       6 tests — full debate loop, JSON output, no-tie verdict,
                                          token tracking, structured logs, mutual reference
```

---

## Constraints & Limitations

- **Pings reduced to 5** (from 10) to manage API costs. The assignment explicitly permits this when documented in the README.
- Debate topic is configurable in `config/config.json` — no code changes needed to change the topic.
- The transcript above was generated from the integration test with realistic mock responses. A live run with a real `ANTHROPIC_API_KEY` will produce a genuine AI-generated debate with live web searches.

---

## Submission

- GitHub: https://github.com/AhmadKais/agent-debate
- Submitted via Moodle as a PDF containing the repository link.
