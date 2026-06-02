# PRD — FIFO Rotating JSONL Logger

**Mechanism:** `FIFOLogger`  
**Module:** `src/core/logger.py`  
**Version:** 1.0 | **Author:** Ahmad Kais, Ali Trabeh

---

## 1. Purpose

Provide a structured, rotating log facility for all agents and infrastructure
components. Uses JSONL format (one JSON object per line) so individual log
entries are independently parseable even if the file is truncated. Rotates
automatically to prevent unbounded disk growth.

---

## 2. Functional Requirements

| ID  | Requirement         | Description                                                         |
|-----|---------------------|---------------------------------------------------------------------|
| L1  | JSONL format        | Each entry: `{"ts": ISO, "level": str, "source": str, "msg": str}` |
| L2  | Auto-rotation       | Create new file when current file reaches `max_lines`              |
| L3  | FIFO eviction       | Delete the oldest file when `max_files` files exist                |
| L4  | Level API           | `info()`, `warning()`, `error()` — all write to the same JSONL     |
| L5  | Resume on open      | On init, re-open the most recent file if it still has capacity     |

---

## 3. Acceptance Criteria

| Criterion | Expected Behaviour |
|-----------|--------------------|
| AC-L1 | After `max_lines` writes, a new file is created                        |
| AC-L2 | After writing to `max_files + 1` full files, oldest file is deleted   |
| AC-L3 | Each written line is valid JSON parseable by `json.loads()`           |
| AC-L4 | Resumed logger appends to an existing file, not a new one             |

---

## 4. Parameters (from `config/config.json`)

| Key            | Default | Description                             |
|----------------|---------|-----------------------------------------|
| `log_dir`      | "logs"  | Directory to write log files into       |
| `log_max_files`| 20      | Maximum number of log files to retain   |
| `log_max_lines`| 500     | Lines per log file before rotation      |

---

## 5. File Naming

Files are named `debate_YYYYMMDD_HHMMSS_ffffff.log`, sorted lexicographically
to determine oldest-first eviction order.

---

## 6. Constraints

- `logger.py` ≤ 150 lines.
- A single corrupt write must not break the entire file (JSONL advantage).
- No external logging libraries — stdlib `json` + `datetime` only.
