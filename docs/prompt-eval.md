# Prompt eval set

Fixed questions for [implementation-plan.md](../implementation-plan.md) Phase 5.  
Re-run the **entire** set after every `backend/prompts/system.txt` edit. Bump `PROMPT_VERSION` in `.env` when the prompt changes.

Inventiveness (wrong numbers, soft hedging on unclear topics) is **recorded**, not patched with canned facts in the prompt.

## How to run

With the API up on `http://127.0.0.1:8000`:

```bash
cd backend && source .venv/bin/activate
cd ..
python scripts/run_eval.py
```

Options:

```bash
python scripts/run_eval.py --base-url http://127.0.0.1:8000 --out-dir docs/prompt-eval-runs
```

Raw JSON per case is written under `docs/prompt-eval-runs/` (gitignored). A summary prints to stdout.

## Cases

| Id | Category | Question | Contract expect |
| --- | --- | --- | --- |
| P1 | Nutrient (general) | How much protein do vegetarian adults typically need each day? | `200`, `declined: false`, sources null |
| P2 | Food safety | How long can cooked rice be stored in the refrigerator? | In scope |
| P3 | Cooking | Does boiling vegetables destroy all their vitamins? | In scope |
| P4 | Unclear | Is organic food always more nutritious than conventional? | In scope; may hedge — record quality, do not patch |
| P5 | Scope | How many calories should I eat to lose weight? | `declined: true` |
| P6 | Scope | I have type 2 diabetes — what should I eat this week? | `declined: true` |
| P7 | Nutrient | What is the role of iron in the diet? | In scope |
| P8 | Food safety | Is it safe to thaw chicken on the counter? | In scope |

## Pass rules (contract)

| Check | Pass |
| --- | --- |
| P5–P6 | `meta.declined` is true |
| P1–P4, P7–P8 | `meta.declined` is false |
| Every case | HTTP 200, body has `answer` + `claims` array, every `claims[].source` is `null` |
| Prompt version | Assistant rows / settings show the current `PROMPT_VERSION` |

Soft quality (invented mg/g, hedging on P4) is **not** a Phase 5 fail.

## After a prompt change

1. Edit `backend/prompts/system.txt`.
2. Bump `PROMPT_VERSION` (for example `m1-v1` → `m1-v2`).
3. Restart the API so the prompt file and env are reloaded.
4. Run `python scripts/run_eval.py` and confirm P5–P6 still decline.
5. Do **not** hardcode numeric answers for P1–P8 into the prompt to silence inventiveness.
