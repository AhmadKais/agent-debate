# PRD — IPC Message Format

**Mechanism:** `Message` and `DebateResult` Pydantic models  
**Module:** `src/data_types/message.py`, `src/data_types/debate_result.py`  
**Version:** 1.0 | **Author:** Ahmad Kais, Ali Trabeh

---

## 1. Purpose

All inter-agent communication is serialised as typed, validated Pydantic objects.
This enforces the contract that "messages" in the child→papa→child routing are
structured data, not raw strings, and that the final verdict meets format
requirements before being returned to callers.

---

## 2. Message Schema

```json
{
  "round":     1,
  "sender":    "pro",
  "recipient": "judge",
  "content":   "<argument text>",
  "timestamp": "2026-06-01T14:22:31.012345+00:00",
  "references": ["https://..."]
}
```

| Field       | Type       | Constraints                            |
|-------------|------------|----------------------------------------|
| `round`     | int        | ≥ 1                                    |
| `sender`    | str        | Free text (agent name)                 |
| `recipient` | str        | Free text (agent name)                 |
| `content`   | str        | Non-empty                              |
| `timestamp` | datetime   | Auto-set to UTC now on creation        |
| `references`| list[str]  | Default empty; optional citation list  |

### Methods
- `to_ipc_dict()` — serialize to JSON-compatible dict (ISO timestamp).
- `from_ipc_dict(d)` — deserialize from dict.
- `summary()` — one-line human-readable summary for logging.

---

## 3. DebateResult Schema

```json
{
  "winner":     "Pro",
  "score_pro":  74,
  "score_con":  83,
  "reason":     "...",
  "violations": [...]
}
```

| Field       | Type     | Validator                            |
|-------------|----------|--------------------------------------|
| `winner`    | str      | Must be exactly `"Pro"` or `"Con"`   |
| `score_pro` | int      | 0–100                                |
| `score_con` | int      | 0–100                                |
| `reason`    | str      | Non-empty                            |

---

## 4. Acceptance Criteria

| Criterion | Expected Behaviour |
|-----------|--------------------|
| AC-M1 | `Message.to_ipc_dict()` round-trips via `from_ipc_dict()` without data loss |
| AC-M2 | `DebateResult(winner="Tie", ...)` raises `ValidationError`                   |
| AC-M3 | `DebateResult(score_pro=150, ...)` raises `ValidationError`                  |
| AC-M4 | `timestamp` field is auto-populated with UTC datetime if not supplied        |

---

## 5. Constraints

- Pydantic v2 (`pydantic>=2.13.4`) — uses `model_validator` and `field_validator`.
- No tie: the `winner` validator explicitly rejects the string `"Tie"`.
- `message.py` and `debate_result.py` each ≤ 150 lines.
