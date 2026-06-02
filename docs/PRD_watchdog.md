# PRD — Watchdog: Timeout + Retry Wrapper

**Mechanism:** `Watchdog`  
**Module:** `src/core/watchdog.py`  
**Version:** 1.0 | **Author:** Ahmad Kais, Ali Trabeh

---

## 1. Purpose

Every autonomous agent project must have a process-level supervisor that detects
stalls and retries failed calls with back-off (§8.6). The Watchdog wraps any
blocking callable and enforces a hard timeout per attempt, retrying up to
`max_retries` times before giving up.

---

## 2. Functional Requirements

| ID  | Requirement            | Description                                                          |
|-----|------------------------|----------------------------------------------------------------------|
| W1  | Timeout enforcement    | Kill stalled calls after `timeout_seconds` using `ThreadPoolExecutor`|
| W2  | Exponential back-off   | Sleep `2^attempt` seconds between retries (2 s, 4 s, 8 s …)         |
| W3  | Retry limit            | After `max_retries` failed attempts, re-raise the last exception     |
| W4  | Logging                | Log every timeout and error via the shared `FIFOLogger`              |
| W5  | Generic callable       | `run(fn, *args, **kwargs)` works for any blocking function           |

---

## 3. Acceptance Criteria

| Criterion | Expected Behaviour |
|-----------|--------------------|
| AC-W1 | A callable that sleeps indefinitely is killed within `timeout_seconds + ε` |
| AC-W2 | On success at attempt 2, no exception is raised                            |
| AC-W3 | After `max_retries` exhausted, `WatchdogTimeoutError` is raised             |

---

## 4. Parameters (from `config/config.json`)

| Key               | Default | Description                          |
|-------------------|---------|--------------------------------------|
| `timeout_seconds` | 60      | Max seconds per attempt              |
| `max_retries`     | 3       | Number of attempts before giving up  |

---

## 5. Constraints

- `watchdog.py` ≤ 150 lines.
- Uses `concurrent.futures.ThreadPoolExecutor` (not `multiprocessing`) so the
  Gatekeeper's shared state remains visible across the call boundary.
- Back-off sleep must not block the main thread beyond `2^max_retries` seconds total.
