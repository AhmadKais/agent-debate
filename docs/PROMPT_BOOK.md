# Prompt Engineering Log

Development log of all key prompts used to build this project.

---

## 1. Pro Agent System Prompt (AXIOM)

**Purpose:** Define a relentless PRO debater with a distinct personality.  
**Iteration:** 3 refinements. Original prompt produced overly polite arguments; added "ruthless counter-attacks" and the requirement to quote the opponent's words explicitly.

**Final prompt key rules:**
- Output ONLY valid JSON `{"argument": ..., "references_used": [...]}`
- Must directly attack the PREVIOUS argument — quote opponent's words
- Must use web_search for every argument
- Maximum 250 words
- Never concede, never hedge

**Why it works:** The JSON constraint prevents prose bleed-through. Quoting the opponent satisfies the "mutual reference" rubric requirement.

---

## 2. Con Agent System Prompt (NEMESIS)

**Purpose:** Distinct CON personality from AXIOM — cold logic vs. aggressive passion.  
**Iteration:** 2 refinements. Differentiated by tone (sarcasm + cold facts vs. aggressive rhetoric).

**Key distinction from AXIOM:** Uses irony and provocation rather than emotional appeals. Different search query strategy — looks for statistics that contradict Pro's claims rather than supporting Con's.

---

## 3. Judge System Prompt (THE ARBITER)

**Purpose:** Impartial judge that routes messages and declares a non-tie winner.  
**Iteration:** 4 refinements. Most critical prompt — needed:
1. Absolute no-tie rule with explicit score differentiation
2. Routing output format `{"route_to": "Con"}` vs verdict format
3. Criterion: PERSUASIVENESS not factual accuracy (per assignment)
4. Fallback behavior when LLM returns non-JSON

**Critical line added:** "ABSOLUTE RULE: You CANNOT declare a tie. Even if scores are close (e.g., 71 vs 70), pick the winner and justify it."

---

## 4. Opening Debate Prompt

**Purpose:** Start the debate by giving Pro the topic and role.

```
The debate topic is: "{topic}"
You are arguing the PRO side. Open with your strongest argument.
Use web_search to cite real evidence.
```

**Design choice:** Give Pro the topic explicitly rather than letting it infer from system prompt. Tested that without explicit topic injection, Pro sometimes argued a different framing.

---

## 5. Round Continuation Prompts

**Con turn:**
```
Ping {n}: The Pro side just argued:
"{pro_arg}"

Tear it apart and make your strongest counter-argument for the CON side.
```

**Pro turn:**
```
Ping {n}: The Con side just argued:
"{con_arg}"

Refute it decisively and advance your PRO argument further.
```

**Design choice:** Include opponent's argument verbatim in the prompt (not just in history). This ensures the agent explicitly addresses the previous argument even when context window compression occurs.

---

## 6. Winner Declaration Prompt

**Purpose:** Trigger the judge to produce the final verdict JSON.

The judge accumulates `debate_transcript` via `observe()` calls throughout the debate. At the end, `declare_winner()` passes the full transcript and requests the verdict JSON schema.

**Key:** Transcript is summarized in the prompt itself (not only in history) to ensure the judge has full context even after many conversation turns.
