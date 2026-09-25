# Implementation plan

Phase-wise plan for the service in [architecture.md](./architecture.md), built from [problemStatement.md](./problemStatement.md). Each phase is shippable on its own. Do not start a phase until the previous phase’s exit checks pass.

Stack: React + Vite frontend on Vercel, FastAPI backend on Railway, **Groq** (OpenAI-compatible chat API) with structured JSON output, SQLite (or Postgres) for conversations. The model answers from its own knowledge. Every claim `source` stays `null`. Do not add retrieval, citations, or hardcoded factual patches in any phase.

## Model

The chat path uses Groq’s OpenAI-compatible chat API with JSON-mode structured output, then Pydantic validation. Phase 0–1 do not call it. Phase 2 introduced the LLM path; **Phase 3 standardizes on Groq** (and adds conversation persistence).

| Setting | Value |
| --- | --- |
| Provider | Groq (`MODEL_PROVIDER=groq`) |
| `GROQ_API_BASE_URL` | `https://api.groq.com/openai/v1` |
| Default `GROQ_MODEL` | `openai/gpt-oss-120b`. Limits: 30 requests/min, 1,000 requests/day, 8,000 tokens/min, 200,000 tokens/day. Do not exceed them. Prefer failing with `503` over waiting out a daily quota. |
| Allowed alternate | `qwen/qwen3.6-27b` (selected only by setting `GROQ_MODEL`) |
| `GROQ_API_KEY` | Blank in `.env.example`. A local `.env` / Railway env supplies it. Never commit the key. Never put keys in the Vite client. |
| `TEMPERATURE` | `0.2` (low enough for eval stability; do not cache answers to hide drift) |
| `PROMPT_VERSION` | `m1-v1` at first ship; bump on every system-prompt edit |
| Structured output | Prefer `response_format` JSON object / schema when the model supports it; always re-validate with Pydantic. One repair retry, then `502`. |

Do not substitute another host or model id unless this table changes. Do not parse free-form prose for claims without a schema validation step.

## How to use this plan

Work in order. A phase is done only when its exit checks pass. Later phases must not rewrite earlier contracts (response JSON shape, `/api/chat` request body, empty sources panel) unless an exit check failed.

Out of scope for every Milestone 1 phase:

- Retrieval, embeddings, vector stores, or real citations
- Filling `claims[].source` with anything other than `null`
- Hardcoded FAQ answers to suppress hallucinations
- User accounts / login
- Streaming token UI (optional later; not required)
- Medical advice, calorie targets, or weight recommendations as product features

## Target layout

Create files only when the phase that owns them starts.

```text
AI Nutrition Chatbot/
  problemStatement.md
  architecture.md
  implementation-plan.md
  README.md
  .env.example
  .gitignore
  docs/
    failure-log.md
    prompt-eval.md
  backend/
    requirements.txt
    railway.toml
    prompts/
      system.txt
    app/
      main.py
      config.py
      api/
        health.py
        chat.py
      schemas/
        response.py
      services/
        scope_gate.py
        llm.py
        conversation.py
        prompt.py
      db/
        models.py
        session.py
  web/
    package.json
    vite.config.ts
    vercel.json
    index.html
    src/
      main.tsx
      App.tsx
      api/client.ts
      types/chat.ts
      components/
        ChatWindow.tsx
        MessageList.tsx
        MessageInput.tsx
        SourcesPanel.tsx
  scripts/
    run_eval.py
    run_failure_log.py
  tests/
    test_schema.py
    test_scope_gate.py
    test_chat_api.py
```

Suggested dependencies, added in the phase that first needs them:

- Phase 0: `fastapi`, `uvicorn`, `python-dotenv`, `pydantic`
- Phase 2: `openai` SDK (also used as the Groq OpenAI-compatible client)
- Phase 3: SQLAlchemy (or equivalent) for SQLite/Postgres; finalize Groq env (`GROQ_API_KEY`, `GROQ_MODEL`, `GROQ_API_BASE_URL`)
- Phase 6: React, Vite, TypeScript (frontend `package.json`)

---

## Phase 0 — Project skeleton

**Goal.** A runnable empty API with config, health, and repo hygiene. No model calls yet.

**Maps to.** Architecture §5 (layout), §18 (config), §20 step 1.

**Depends on.** Nothing.

**Create**

- `backend/requirements.txt`
- `.env.example` with `MODEL_PROVIDER`, blank API keys, `MODEL_NAME`, `TEMPERATURE=0.2`, `DATABASE_URL=sqlite:///./data/app.db`, `PROMPT_VERSION=m1-v1`, `ALLOWED_ORIGINS=http://localhost:5173`
- `.gitignore` (`.env`, `__pycache__`, `node_modules`, `dist`, `data/*.db`, `.venv`)
- `backend/app/config.py`
- `backend/app/main.py` with `create_app` factory
- `backend/app/api/health.py` — `GET /health` → `{ "status": "ok" }`
- `README.md` with local run commands (API only for now)

**Tasks**

1. Pin Python 3.11+.
2. Confirm uvicorn starts with `--host 127.0.0.1` locally and `/health` responds.
3. Do not create the React app yet.
4. Do not call any LLM.

**Exit checks**

- [ ] `GET /health` returns JSON `{"status":"ok"}`.
- [ ] No secrets are committed.
- [ ] `.env.example` documents every backend variable from architecture §18.1.

**Do not.** Implement `/api/chat`, the UI, or the failure log in this phase.

---

## Phase 1 — Response contract and chat stub

**Goal.** Freeze the JSON contract the rest of the app will obey. A stub `/api/chat` returns a valid `ChatResponse` without calling a model.

**Maps to.** Architecture §6 (core response contract), §7 (API design).

**Depends on.** Phase 0.

**Create**

- `backend/app/schemas/response.py` — `Claim`, `Meta`, `ChatResponse`, request models
- `backend/app/api/chat.py` — `POST /api/conversations`, `POST /api/chat` stub
- `tests/test_schema.py`

**Tasks**

1. Define Pydantic models:
   - `Claim`: `text: str`, `source: None` (always null in Milestone 1)
   - `ChatResponse`: `answer`, `claims`, `meta` (`conversation_id`, `message_id`, `declined`, `decline_reason`)
   - Request: `{ "conversation_id": uuid | null, "message": str }`
2. Implement `POST /api/conversations` → creates an in-memory conversation id (DB comes in Phase 3).
3. Implement stub `POST /api/chat` that returns a fixed valid payload with `claims[].source = null` and `declined: false`.
4. Reject empty messages with `400`.
5. Unit-test: schema accepts a valid payload; rejects missing `claims`; documents that non-null `source` will be normalized in Phase 2.

**Exit checks**

- [ ] `POST /api/conversations` returns a `conversation_id`.
- [ ] `POST /api/chat` returns a body that validates as `ChatResponse`.
- [ ] Every claim in the stub has `"source": null`.
- [ ] Empty `message` → `400`.

**Do not.** Call the LLM, enforce scope, or build the UI yet.

---

## Phase 2 — Structured LLM call

**Goal.** Real answers from the model, always parsed against the schema, with `source` forced to `null`.

**Maps to.** Architecture §8 (lifecycle steps 4–7), §11 (LLM integration).

**Depends on.** Phase 1.

**Create**

- `backend/app/services/llm.py`
- `backend/app/services/prompt.py` (minimal system string inline or file; full prompt lands in Phase 5)
- `backend/prompts/system.txt` (short placeholder is fine)
- Update `tests/test_chat_api.py` with mocked provider responses

**Tasks**

1. Load provider credentials from env only.
2. Call the model with structured output constrained to `answer` + `claims[{text, source}]`.
3. Validate with Pydantic. On failure, retry **once** with a repair instruction. Still invalid → `502`.
4. Contract guard: after parse, set every `claims[].source = null` even if the model emitted a string.
5. Map provider outages to `503`. Do not leak raw provider error bodies.
6. Log `model`, `temperature`, `prompt_version` server-side (persist in Phase 3).
7. Tests with mocked LLM: valid JSON → 200; garbage → 502 after retry; non-null source → response still has `null`.

**Note.** Phase 2 may have used a generic OpenAI/Anthropic client. **Phase 3 switches the live provider to Groq** per the Model table (`openai/gpt-oss-120b` or `qwen/qwen3.6-27b`). Keep the same `complete()` contract and mocks.

**Exit checks**

- [ ] A real local call (with key in `.env`) returns a parseable `ChatResponse`.
- [ ] Contract guard test passes for mocked non-null sources.
- [ ] No API key appears in responses, logs committed to git, or frontend env.

**Do not.** Add retrieval, cache answers for consistency, or hardcode nutrition facts.

---

## Phase 3 — Conversation persistence (+ Groq)

**Goal.** Multi-turn history stored so scope tests and the UI can reuse a `conversation_id`. Live chat uses **Groq** (`openai/gpt-oss-120b` or `qwen/qwen3.6-27b`).

**Maps to.** Architecture §12 (storage), §7 (`GET` conversation optional); Model table (Groq).

**Depends on.** Phase 2.

**Create**

- `backend/app/db/session.py`
- `backend/app/db/models.py`
- `backend/app/services/conversation.py`
- Optional `GET /api/conversations/{id}`
- Update `.env.example` / config for `GROQ_API_KEY`, `GROQ_MODEL`, `GROQ_API_BASE_URL`

**Tasks**

1. Point `llm.py` at Groq’s OpenAI-compatible API. Allow only `openai/gpt-oss-120b` and `qwen/qwen3.6-27b`. Reject any other `GROQ_MODEL`.
2. Create `conversations` and `messages` tables per architecture §12.1.
3. On chat: load history, append user message, append assistant message with `claims_json`, `declined`, `model`, `prompt_version`.
4. Replace Phase 1 in-memory conversation ids with DB-backed ids.
5. SQLite file under `data/` locally; document Railway volume **or** Postgres `DATABASE_URL` choice in README.
6. Ensure history is passed into the Groq call in order (user/assistant turns only; system prompt stays the system message).
7. Keep structured JSON + one repair retry + `source: null` contract guard from Phase 2.

**Exit checks**

- [ ] Two turns in the same `conversation_id` show prior context affecting the second reply (spot-check).
- [ ] Assistant rows store `claims_json` with `source: null`.
- [ ] Restarting the local API keeps SQLite history (file-backed).
- [ ] With `GROQ_API_KEY` set, a live chat returns a parseable `ChatResponse` from Groq.
- [ ] Disallowed `GROQ_MODEL` values do not call the provider.

**Do not.** Build accounts, or use the DB to store “approved” canned answers. Do not call OpenAI/Anthropic hosts for Milestone 1 chat.

---

## Phase 4 — Scope gate (code enforcement)

**Goal.** Refuse calorie/weight targets, weight recommendations, and medical advice in code, including rephrases and multi-turn retries.

**Maps to.** Architecture §9; problem statement §5 and acceptance “Test the Scope Limit.”

**Depends on.** Phase 3.

**Create**

- `backend/app/services/scope_gate.py`
- `tests/test_scope_gate.py`
- Decline answer template (constant or small helper)

**Tasks**

1. Implement a deterministic gate on the new user message **and** recent history (for “ask again after unrelated turns”).
2. Categories: calorie/weight targets; what someone should weigh; medical/condition-specific eating advice.
3. If blocked: persist user + declined assistant turn **without** calling the main nutrition model; return same `ChatResponse` shape with `meta.declined: true` and an empty or non-actionable `claims` list.
4. Optional post-check on model `answer` for leaked targets; if found, replace with decline.
5. Tests: direct asks, rephrases (“macros for cutting”), sideways hypotheticals, multi-turn reintroduction → all `declined: true`.
6. In-scope control questions (e.g. general fridge storage) still call the model and return `declined: false`.

**Exit checks**

- [ ] Direct calorie-target ask is declined without relying on the model alone.
- [ ] Medical “I have X, what should I eat?” is declined.
- [ ] Rephrase + multi-turn adversarial cases in tests pass.
- [ ] Decline copy points to a qualified professional and does not give a target anyway.

**Do not.** “Soft allow” personal calorie numbers with a disclaimer. A disclaimer is not a pass.

---

## Phase 5 — System prompt and prompt eval harness

**Goal.** A versioned prompt that states role, style, length, and refusals, plus a fixed question set re-run after every prompt change.

**Maps to.** Architecture §10; problem statement §4.

**Depends on.** Phase 4.

**Create**

- Full `backend/prompts/system.txt`
- `docs/prompt-eval.md` — fixed questions (can overlap failure-log categories but keep this set stable for prompt diffs)
- `scripts/run_eval.py`

**Tasks**

1. Write prompt sections: what it does; how it answers; length; what it will not touch; output contract (`source` null); uncertainty honesty.
2. Wire `PROMPT_VERSION` into responses/DB.
3. `run_eval.py` hits local `/api/chat` for every eval question and writes raw JSON under a gitignored folder or prints a summary.
4. After any prompt edit: bump `PROMPT_VERSION`, re-run the full eval set, spot-check that scope declines still hold.
5. Do not edit the prompt to hardcode numeric nutrition answers for eval questions.

**Exit checks**

- [ ] Prompt file contains all four required content areas from the problem statement (does / how / length / won’t touch).
- [ ] Eval script runs end-to-end against local API.
- [ ] Scope declines still pass after the real prompt is loaded.

**Do not.** Treat eval failures about inventiveness as bugs to patch with canned facts.

---

## Phase 6 — Chat frontend with empty sources panel

**Goal.** Message list, input, and a sources panel that stays empty. Talks only to the backend.

**Maps to.** Architecture §13; problem statement §1.

**Depends on.** Phase 5 (API must be complete enough for real chat).

**Create**

- `web/` Vite + React + TypeScript app
- `web/src/types/chat.ts` mirroring `ChatResponse`
- `web/src/api/client.ts`
- Components: `ChatWindow`, `MessageList`, `MessageInput`, `SourcesPanel`
- `web/.env.example` with optional `VITE_API_BASE=http://127.0.0.1:8000`

**Tasks**

1. On load: `POST /api/conversations`, store `conversation_id`.
2. Send messages via `POST /api/chat`; render `answer` in the thread.
3. Show distinct styling when `meta.declined` is true.
4. Build `SourcesPanel` beside the conversation. Milestone 1 empty state: e.g. “Sources will appear here in Milestone 2.” Do not hide the panel.
5. Panel reads the selected assistant message’s claims/sources; with all `source: null`, it stays empty.
6. Disable input while a request is in flight; surface HTTP errors without dumping stack traces.
7. No provider keys in any `VITE_*` variable.

**Exit checks**

- [ ] Local UI can complete a multi-turn chat against the API.
- [ ] Sources panel is visible and empty for normal answers.
- [ ] Declined turns are visible as declines in the UI.
- [ ] Browser network tab shows calls to the API origin only (no `api.openai.com` / Anthropic from the client).

**Do not.** Implement citation rendering beyond the empty state. Do not call the LLM from the browser.

---

## Phase 7 — Deploy (Railway + Vercel)

**Goal.** Public URL: static UI on Vercel, API on Railway, same-origin `/api/*` via rewrites.

**Maps to.** Architecture §14; problem statement §6.

**Depends on.** Phase 6.

**Create**

- `backend/railway.toml` — uvicorn factory on `0.0.0.0`, `$PORT`, healthcheck `/health`
- `web/vercel.json` — rewrite `/health` and `/api/:path*` to the Railway URL; SPA fallback
- Production env vars on Railway (keys, model, DB)
- Short deploy section in `README.md`

**Tasks**

1. Deploy API first; confirm public `GET /health`.
2. Set secrets on Railway only.
3. Point Vercel project at `web/`; set rewrites to Railway; deploy.
4. Confirm the Vercel URL loads the UI and a chat message round-trips through the rewrite.
5. Add a simple rate limit on `/api/chat` if public abuse is a concern (architecture §19).
6. Push the project to GitHub if not already.

**Exit checks**

- [ ] Public frontend URL loads the chat UI.
- [ ] Chat works on the public URL without local Vite.
- [ ] Model keys are not visible in the browser bundle or Vercel client env.
- [ ] Railway healthcheck passes.

**Do not.** Put the LLM key on Vercel. Do not skip rewrites by calling Railway from the browser in production (CORS sprawl).

---

## Phase 8 — Failure log, consistency, and submission gates

**Goal.** Record model failures without fixing them. Prove consistency drift and scope limits on the live (or local) app.

**Maps to.** Architecture §15–16; problem statement §7 and “Before You Submit.”

**Depends on.** Phase 7 (prefer live URL; local API is acceptable for drafting, then re-run once on prod).

**Create**

- `docs/failure-log.md` — 10 questions + per-response notes + grouped counts
- `scripts/run_failure_log.py` — fetches JSON for each question; does not auto-fix answers
- Optional `docs/failure-log-runs/` (gitignored raw dumps)

**Tasks**

1. Write **10 questions** across: nutrient requirements; food safety/storage; cooking methods; no-clear-answer.
2. Run all 10; for each response record:
   - Claims stated as fact with nothing behind them
   - Numbers that shift between runs
   - Sources cited that cannot be found (including fake authorities in prose)
   - Questions it should have declined
   - Questions that hedged into uselessness
3. Group failures and count them in `docs/failure-log.md`.
4. Consistency: pick one in-scope numeric question; ask **3 times**; compare substance (especially numbers); log drift.
5. Scope suite on the deployed app: calorie target; condition-specific diet; rephrase both; ask sideways; reintroduce after unrelated messages — must decline every time.
6. Confirm no phase introduced hardcoded factual patches to beautify the failure log.

**Exit checks**

- [ ] `docs/failure-log.md` has 10 questions, notes, and grouped counts.
- [ ] Consistency ×3 results are written down.
- [ ] Scope adversarial suite passes on the public app.
- [ ] Every sampled response still has `claims[].source === null`.
- [ ] Sources panel still empty in the live UI.
- [ ] Failures were recorded, not patched around.

**Do not.** Change the model answers to reduce failure counts. Milestone 2 compares against this baseline.

---

## Phase dependency graph

```text
Phase 0  Skeleton
   └─► Phase 1  Schema + chat stub
          └─► Phase 2  Structured LLM
                 └─► Phase 3  Persistence
                        └─► Phase 4  Scope gate
                               └─► Phase 5  Prompt + eval
                                      └─► Phase 6  Frontend
                                             └─► Phase 7  Deploy
                                                    └─► Phase 8  Failure log + acceptance
```

---

## Milestone 1 done when

All Phase 8 exit checks pass, and:

1. Public chatbot answers food / nutrition / food safety questions from model memory.
2. Every successful response parses as `{ answer, claims[{ text, source: null }], meta }`.
3. Scope limits live in code and survive rephrase / multi-turn attacks.
4. Sources panel exists and is empty.
5. Failure log is filled; inventiveness and drift are counted, not hidden.
6. Interface, endpoints, and schema are stable for Milestone 2 retrieval to fill `source` and the sources panel.

---

## Handoff notes for Milestone 2 (do not build now)

When retrieval starts, extend only these seams from architecture §17:

- Add `services/retrieve.py` and prompt context injection.
- Allow `claims[].source` to become a citation object; keep the claims array.
- Fill `SourcesPanel` from non-null sources.
- Re-run the **same** 10 failure-log questions and compare counts.

Do not redesign `/api/chat` or the chat shell to “make room” for citations — the room is already there.
