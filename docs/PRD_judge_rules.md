# PRD — Judge Agent: 8-Rule Moderation System

**Mechanism:** `JudgeAgent` (Papa agent)  
**Module:** `src/agents/judge_agent.py`  
**Version:** 1.0 | **Author:** Ahmad Kais, Ali Trabeh

---

## 1. Purpose

The Judge agent acts as the Papa process that routes every message between debaters
and enforces a set of content-moderation rules before each routing decision. The
Judge must always declare a winner — no ties are permitted.

---

## 2. Functional Requirements

| ID  | Rule              | Trigger Condition                                      | Action         |
|-----|-------------------|--------------------------------------------------------|----------------|
| R1  | off_topic         | Argument does not address the debate topic             | Log warning    |
| R2  | no_rebuttal       | Agent ignores the opponent's last point                | Log warning    |
| R3  | empty_argument    | Response is blank or fewer than 20 words               | Log violation  |
| R4  | concession        | Agent explicitly concedes a core claim to opponent     | Log violation  |
| R5  | no_evidence       | No factual citations or evidence presented             | Log warning    |
| R6  | profanity         | Offensive or inappropriate language detected           | Log violation  |
| R7  | ad_hominem        | Personal attack on opponent rather than argument       | Log violation  |
| R8  | repetition        | Argument is substantively identical to a prior round   | Log warning    |

**Routing rule:** After evaluating all 8 rules, the Judge returns the next speaker
as `{"route_to": "Pro"|"Con", "violations": [...], "warnings": [...]}`.

---

## 3. Acceptance Criteria

| Criterion | Expected Behaviour |
|-----------|--------------------|
| AC-J1 | `observe(side, arg)` always returns either "Pro" or "Con" |
| AC-J2 | Violations are accumulated in `self.violations` across all rounds |
| AC-J3 | `declare_winner()` passes violation summary to the LLM for penalty scoring |
| AC-J4 | Fallback winner (parse failure) is determined by violation count, not hardcoded |
| AC-J5 | `score_pro ≠ score_con` in every verdict (no tie) |
| AC-J6 | `declare_winner()` uses `max_tokens=2048` to avoid truncated JSON |

---

## 4. Constraints

- Judge must **never** route a message back to the sender (child→papa→child, not papa→papa).
- Violation log must be attached to every `DebateResult` under key `"violations"`.
- The 8-rule prompt lives in `src/agents/prompts.py`; `judge_agent.py` stays ≤ 150 lines.
