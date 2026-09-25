# Architecture: AI Nutrition Assistant Prototype

## 1. Purpose

This document describes how to build the Milestone 1 nutrition chatbot so that:

- The model answers from its own knowledge (no retrieval yet).
- Every response is structured, parseable, and contract-stable.
- Claim `source` fields stay `null` by design.
- Scope limits are enforced in code, not only in the prompt.
- The UI already has a sources panel that Milestone 2 can fill without changing the interface, endpoints, or response schema.

This is an architecture for a **measurable failure surface**, not a production nutrition authority.

---

## 2. Design Principles

| Principle | Implication |
| --- | --- |
| Contract before quality | Fix the response schema and UI slots now. Do not invent good answers by hardcoding. |
| Failures are data | Record inventiveness, drift, and refusals. Do not patch individual bad answers. |
| Server owns the model | Browser never holds API keys or calls the LLM directly. |
| Dual enforcement | Prompt states scope. Code refuses calorie targets, weight advice, and medical advice. |
| Milestone 2 ready | Retrieval plugs in behind the same `/api/chat` contract and the same sources panel. |
| Parse or fail | Invalid structured output is a hard error, not a best-effort prose fallback. |

---

## 3. Recommended Stack

The problem statement allows Next.js or React + FastAPI. Prefer the split below because deploy requires **both** Vercel and Railway, and the model call must stay on a backend you control.

| Layer | Choice | Why |
| --- | --- | --- |
| Frontend | React + Vite (TypeScript) | Static UI on Vercel; simple message list + sources panel. |
| Backend | FastAPI (Python 3.11+) | Clear chat endpoint, schema validation, scope gates, LLM call. |
| Model | OpenAI or Anthropic with **structured outputs** | Schema enforced by the provider, not by regex on prose. |
| Storage | SQLite (prototype) or Postgres/Supabase | Conversation history for multi-turn scope tests. |
| Frontend host | Vercel | Serves `web/`; rewrites `/api/*` and `/health` to Railway. |
| Backend host | Railway | Runs FastAPI + model calls + DB. |

Alternative: a Next.js App Router app on Vercel with Route Handlers can work, but then Railway has little to host unless you still put the LLM service there. The split stack maps cleanly to the brief’s “Vercel and Railway” requirement.

---

## 4. System Context

```text
┌─────────────┐         ┌──────────────────────┐         ┌─────────────────┐
│   Browser   │  HTTPS  │  Vercel (frontend)   │ rewrite │ Railway (API)   │
│  Chat UI +  │ ──────► │  React static assets │ ──────► │ FastAPI         │
│ Sources pan │         │  /api/* → Railway    │         │ Scope gate      │
└─────────────┘         └──────────────────────┘         │ Prompt + LLM    │
                                                         │ Conversation DB │
                                                         └────────┬────────┘
                                                                  │
                                                                  ▼
                                                         ┌─────────────────┐
                                                         │ OpenAI / Anthropic│
                                                         │ Structured output │
                                                         └─────────────────┘
```

Milestone 1 has **no** retrieval, vector store, or citation resolver. Milestone 2 inserts those between “prompt assembly” and “LLM call” (or immediately after claim extraction) without changing the public API.

---

## 5. Repository Layout

```text
ai-nutrition-chatbot/
├── problemStatement.md
├── architecture.md
├── README.md
├── .env.example
├── .gitignore
├── docs/
│   ├── failure-log.md          # 10 questions + recorded failures
│   └── prompt-eval.md          # fixed prompt regression set
├── web/                        # React + Vite frontend (Vercel)
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── vercel.json             # rewrites to Railway
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/client.ts
│       ├── components/
│       │   ├── ChatWindow.tsx
│       │   ├── MessageList.tsx
│       │   ├── MessageInput.tsx
│       │   └── SourcesPanel.tsx
│       └── types/chat.ts
├── backend/                    # FastAPI (Railway)
│   ├── requirements.txt
│   ├── railway.toml
│   ├── app/
│   │   ├── main.py             # create_app factory
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── health.py
│   │   │   └── chat.py
│   │   ├── schemas/
│   │   │   └── response.py     # Answer + Claim schema (source: null)
│   │   ├── services/
│   │   │   ├── scope_gate.py   # code-enforced refusals
│   │   │   ├── llm.py          # structured model call
│   │   │   ├── conversation.py
│   │   │   └── prompt.py
│   │   └── db/
│   │       ├── models.py
│   │       └── session.py
│   └── prompts/
│       └── system.txt
└── scripts/
    ├── run_eval.py             # fixed question set after prompt changes
    └── run_failure_log.py      # the 10 canonical questions
```

Keep frontend and backend deployable independently. Shared TypeScript/Python types should mirror the same JSON contract; document that contract in one place (`backend/app/schemas/response.py` as source of truth).

---

## 6. Core Response Contract

This schema is the product boundary for Milestone 1 and Milestone 2.

### 6.1 JSON shape

```json
{
  "answer": "string — assistant reply shown in the chat",
  "claims": [
    {
      "text": "string — atomic factual claim extracted from the answer",
      "source": null
    }
  ],
  "meta": {
    "conversation_id": "uuid",
    "message_id": "uuid",
    "declined": false,
    "decline_reason": null
  }
}
```

### 6.2 Rules

| Field | Milestone 1 rule |
| --- | --- |
| `answer` | Required non-empty string for both normal and decline replies. |
| `claims` | Array. May be empty for declines. Each item must have `text` and `source`. |
| `claims[].source` | Always `null`. Server may overwrite non-null model output to `null` to protect the contract, but prefer instructing structured output so the model emits `null`. |
| `meta.declined` | `true` when the scope gate or model decline path fires. |
| Parse failure | Return HTTP 502 / domain error; do not stream prose. |

### 6.3 Python schema (conceptual)

```python
class Claim(BaseModel):
    text: str
    source: None = None  # literal null in Milestone 1

class ChatResponse(BaseModel):
    answer: str
    claims: list[Claim]
    meta: Meta
```

Use the provider’s structured-output / JSON-schema mode so the model is constrained to this shape. Then validate again with Pydantic. Double validation: provider + app.

### 6.4 Why claims exist before citations

Claims are the slots citations will attach to. If Milestone 1 only returned prose, Milestone 2 would have to change the schema. Extract claims now even though every `source` is `null`.

---

## 7. API Design

All browser traffic goes to the Vercel origin. Vercel rewrites API paths to Railway.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Liveness for Railway + Vercel rewrite checks. |
| `POST` | `/api/chat` | Send a user message; get structured assistant response. |
| `GET` | `/api/conversations/{id}` | Optional: reload history for the UI. |
| `POST` | `/api/conversations` | Create a new conversation; returns `conversation_id`. |

### 7.1 `POST /api/chat`

**Request**

```json
{
  "conversation_id": "uuid | null",
  "message": "user text"
}
```

If `conversation_id` is null, create a conversation first (or require `POST /api/conversations`). Prefer explicit create so the UI owns the session lifecycle.

**Success response:** the Core Response Contract above.

**Decline response:** same schema, with a refusal `answer`, `claims: []` or a single non-actionable claim, `meta.declined: true`.

**Error responses**

| Status | When |
| --- | --- |
| `400` | Empty message, missing conversation. |
| `422` | Request body invalid. |
| `502` | Model returned unparseable structured output after retries. |
| `503` | Model provider unavailable. |

Do not expose raw provider error bodies to the client.

---

## 8. Request Lifecycle

```text
1. UI posts { conversation_id, message }
2. API loads conversation history from DB
3. Scope gate runs on the new user message (+ optional history heuristics)
   ├─ If blocked → persist decline turn → return declined ChatResponse
   └─ If allowed → continue
4. Build messages: system prompt + history + new user message
5. Call LLM with structured output schema = ChatResponse (claims.source = null)
6. Validate with Pydantic
   ├─ Invalid → retry once with “return valid JSON for schema” repair prompt
   └─ Still invalid → 502; log raw payload for debugging
7. Force claims[].source = null (contract guard)
8. Persist user + assistant messages and claims
9. Return ChatResponse to UI
10. UI renders answer in thread; SourcesPanel stays empty (or shows “No sources yet”)
```

Milestone 2 inserts after step 4 or 5:

- retrieve passages → attach to prompt / post-process claims → fill `source` → populate SourcesPanel from the same response.

---

## 9. Scope Gate (Code Enforcement)

The prompt alone is insufficient. Implement a dedicated module that runs **before** the LLM for clear cases, and may also post-check the answer.

### 9.1 Categories to refuse

1. Calorie or weight **targets** (e.g. “how many calories should I eat”, “give me a deficit”)
2. Recommendations about what someone **should weigh**
3. **Medical** advice (conditions, diagnoses, treatment diets, “I have X, what should I eat”)

### 9.2 Implementation strategy

Use layered checks:

| Layer | Mechanism | Role |
| --- | --- | --- |
| A. Heuristic / classifier | Keyword + pattern rules, optionally a small LLM classify call with a yes/no schema | Cheap, deterministic refusals for obvious asks |
| B. System prompt | Explicit “will not” section | Soft guidance for ambiguous wording |
| C. Post-check | Scan assistant `answer` for target-like prescriptions if needed | Catch jailbreak-through replies |

Recommended Milestone 1 approach:

1. Run a **deterministic gate** on the user message (and recent history for “ask sideways after unrelated messages”).
2. If flagged, return a fixed decline template without calling the main nutrition model (saves cost and prevents leakage).
3. If not flagged, call the model; if the model still produces a clear calorie target or medical plan, replace with decline via post-check.

Decline copy should:

- State that the assistant cannot provide that guidance.
- Point the user to a qualified professional (dietitian / physician as appropriate).
- Offer to answer a related **in-scope** question (e.g. general food safety, nutrient roles) without giving a personal target.

### 9.3 Adversarial coverage (acceptance tests)

The gate must still refuse when the user:

- Rephrases (“macros for cutting” ≈ calorie target)
- Asks sideways (“hypothetically for a 30-year-old…”)
- Reintroduces the request after unrelated turns (check recent conversation, not only the last message)

Store `declined` on the message row so the failure log and eval scripts can assert refusals.

---

## 10. System Prompt Architecture

Keep the prompt as a versioned file (`backend/prompts/system.txt`), not buried in code.

### 10.1 Required sections

1. **Role** — food, nutrition, food safety assistant (general information).
2. **How it answers** — clear, concise, structured; separate claims; no invented authority quotes presented as verified.
3. **Length** — short default (e.g. 3–6 short paragraphs or equivalent); no walls of text.
4. **Out of scope** — calorie/weight targets, weight recommendations, medical advice; decline and redirect.
5. **Output contract** — must match JSON schema; every claim `source` is `null`.
6. **Honesty about uncertainty** — when nobody has a clear answer, say so; still emit claims that reflect uncertainty rather than fake precision.

### 10.2 Prompt change process

- Maintain a **fixed eval set** in `docs/prompt-eval.md` / `scripts/run_eval.py`.
- After every prompt edit, re-run the full set.
- Do not tune the prompt to silence failure-log inventiveness by hardcoding factual answers.

---

## 11. LLM Integration

### 11.1 Responsibilities (`services/llm.py`)

- Load API key from env (never from the frontend).
- Send chat messages + JSON schema / tool schema.
- Set temperature low enough for eval stability **without** pretending that makes answers correct (still expect drift; that is what the failure log measures).
- Parse provider response into `ChatResponse`.
- Time out and retry on transient errors; do not retry forever on schema failure.

### 11.2 Structured output

Prefer native structured outputs:

- OpenAI: JSON schema / structured outputs
- Anthropic: tool use or structured output mode equivalent

Do not ask for markdown and then regex-parse claims.

### 11.3 Temperature and determinism

Consistency tests ask the same question 3 times. Architecture should:

- Log `model`, `temperature`, and prompt version on each assistant message.
- Not “fix” numeric drift by caching answers. Drift is a recorded failure for Milestone 1.

---

## 12. Conversation Storage

### 12.1 Minimal tables

**conversations**

| Column | Type | Notes |
| --- | --- | --- |
| id | UUID PK | |
| created_at | timestamptz | |
| updated_at | timestamptz | |

**messages**

| Column | Type | Notes |
| --- | --- | --- |
| id | UUID PK | |
| conversation_id | FK | |
| role | `user` \| `assistant` \| `system` | |
| content | text | For assistant, the `answer` field |
| claims_json | JSON | Assistant only; list of `{text, source}` |
| declined | bool | Default false |
| model | text | Nullable for user rows |
| prompt_version | text | |
| created_at | timestamptz | |

SQLite is enough for the prototype. Use Postgres/Supabase if you want Railway persistence across redeploys without a volume. If using SQLite on Railway, attach a volume or accept that history resets on redeploy (document that choice).

### 12.2 What not to store

- Provider API keys
- Full raw provider dumps in the client-visible API (server-side debug logs only)

---

## 13. Frontend Architecture

### 13.1 Layout

One primary composition for the chat screen:

```text
┌──────────────────────────────────────────────────────────┐
│  Brand / title                                           │
├───────────────────────────────┬──────────────────────────┤
│  Message list                 │  Sources panel           │
│  (user + assistant bubbles)   │  Empty state in M1:      │
│                               │  “Sources will appear    │
│                               │   here in Milestone 2”   │
├───────────────────────────────┴──────────────────────────┤
│  Input box + send                                        │
└──────────────────────────────────────────────────────────┘
```

On narrow screens, stack: messages → input → sources (collapsed empty state is fine).

### 13.2 Component responsibilities

| Component | Responsibility |
| --- | --- |
| `ChatWindow` | Owns `conversation_id`, loading/error state. |
| `MessageList` | Renders turns; shows decline styling if `meta.declined`. |
| `MessageInput` | Submit; disable while in flight. |
| `SourcesPanel` | Reads `claims` / sources from the **selected** assistant message. Milestone 1: always empty / all sources null → empty state. Do not hide the panel. |

### 13.3 Client API

`web/src/api/client.ts` calls same-origin `/api/chat`. No provider keys in Vite env for the browser. Optional `VITE_API_BASE` only for local dev against `localhost:8000`.

### 13.4 Rendering claims vs sources

- Message bubble shows `answer`.
- Optional “Claims” disclosure under an assistant message can list `claims[].text` for debugging/evals — not required by the brief.
- Sources panel only shows non-null sources. In Milestone 1 that means empty. Building the empty panel is mandatory.

---

## 14. Deployment Topology

### 14.1 Railway (API)

- Build from `backend/` with Nixpacks or Docker.
- Start: `uvicorn app.main:create_app --factory --host 0.0.0.0 --port $PORT`
- Health check: `GET /health`
- Env: `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`, `DATABASE_URL` or SQLite path, `ALLOWED_ORIGINS`, `PROMPT_VERSION`

### 14.2 Vercel (web)

- Root or `web/` as the Vite project.
- `vercel.json` rewrites:

```json
{
  "rewrites": [
    { "source": "/health", "destination": "https://<railway-url>/health" },
    { "source": "/api/:path*", "destination": "https://<railway-url>/api/:path*" },
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

Deploy API first; paste the public Railway URL into Vercel rewrites / env.

### 14.3 CORS

If the UI is only same-origin via Vercel rewrites, CORS can stay tight. If local Vite talks directly to Railway, allow `http://localhost:5173` in FastAPI CORS middleware.

### 14.4 Secrets

| Secret | Where |
| --- | --- |
| Model API key | Railway only |
| DB URL | Railway only |
| Railway public URL | Vercel rewrite config |

---

## 15. Failure Log Architecture

Not a runtime feature of the chat API — a **documented evaluation artifact**.

### 15.1 Canonical set (`docs/failure-log.md`)

10 questions spanning:

1. Nutrient requirements (e.g. protein for vegetarian adults)
2. Food safety and storage
3. Cooking methods
4. Questions with no clear answer

### 15.2 Per-response recording fields

For each run, capture:

- Claims stated as fact with nothing behind them
- Numbers that shift across runs
- Sources cited that cannot be found (expect none if contract holds; still check the answer text for fake authority names)
- Questions that should have been declined
- Questions that hedged into uselessness

Group and count. Store raw answers in the doc or a sibling `docs/failure-log-runs/` folder.

### 15.3 Automation helper

`scripts/run_failure_log.py` should:

- Call the live or local `/api/chat` for each question (fresh conversation each time, unless testing multi-turn scope).
- Print/save JSON responses.
- Not auto-fix the model.

Milestone 2 reuses the **same 10 questions** and compares counts.

---

## 16. Consistency and Scope Test Plan (Engineering)

| Test | Method |
| --- | --- |
| Schema parse | Unit tests: valid payload accepts; missing `claims` fails; non-null `source` normalized or rejected per policy. |
| Scope direct | POST calorie target + medical diet asks → `declined: true`. |
| Scope rephrase | Paraphrases and indirect asks → still declined. |
| Scope multi-turn | Unrelated messages, then reintroduce blocked ask → still declined. |
| Consistency | Same question × 3; human or script diffs numeric claims; record drift in failure log. |
| Contract guard | Mock LLM returning `source: "WHO"` → API still emits `null`. |

---

## 17. Milestone 2 Extension Points

Design these seams now; leave them empty or stubbed.

| Seam | Milestone 1 | Milestone 2 |
| --- | --- | --- |
| `services/retrieve.py` | Not called | Fetch passages for the user question |
| Prompt assembly | System + history only | System + retrieved context + history |
| `claims[].source` | Forced `null` | Object or string citation (URL, doc id, snippet id) |
| `SourcesPanel` | Empty state | Renders citations for selected message |
| Failure log | Baseline counts | Same 10 questions; compare inventiveness / drift / hedging |

**Do not** change:

- Frontend route structure for chat
- `POST /api/chat` request shape
- Top-level `{ answer, claims }` presence

If Milestone 2 needs richer `source` objects, extend the `source` field from `null` to a typed object **without removing** the field or the claims array.

Suggested future `source` shape (do not implement yet):

```json
{
  "title": "...",
  "url": "...",
  "publisher": "...",
  "retrieved_at": "..."
}
```

---

## 18. Configuration

### 18.1 `.env.example` (backend)

```text
MODEL_PROVIDER=openai
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
MODEL_NAME=gpt-4.1-mini
TEMPERATURE=0.2
DATABASE_URL=sqlite:///./data/app.db
PROMPT_VERSION=m1-v1
ALLOWED_ORIGINS=http://localhost:5173
```

### 18.2 Frontend env (local only)

```text
VITE_API_BASE=http://127.0.0.1:8000
```

Production uses same-origin rewrites; leave `VITE_API_BASE` empty.

---

## 19. Security and Safety Boundaries

- No LLM keys in the browser or git.
- Scope gate + prompt for health-adjacent refusals; still not a medical device.
- Rate limiting (simple IP or token bucket on `/api/chat`) recommended before a public URL gets abused.
- Log declines and schema failures; do not log full secrets.
- Do not implement “helpful” workarounds that give calorie targets in disguise.

---

## 20. Build Sequence

Suggested implementation order (each step leaves the contract intact):

1. Scaffold FastAPI + health + Pydantic `ChatResponse`.
2. Implement `POST /api/chat` with structured LLM call and `source: null` guard.
3. Add conversation persistence.
4. Implement scope gate + decline path.
5. Version the system prompt; wire eval script.
6. Build React UI: messages, input, empty sources panel.
7. Local end-to-end against Vite + API.
8. Deploy Railway, then Vercel with rewrites.
9. Run consistency ×3 and the 10-question failure log; write `docs/failure-log.md`.
10. Run adversarial scope tests; fix gate/prompt only for refusals, not for factual inventiveness.

---

## 21. Non-Goals (Milestone 1)

- RAG, embeddings, document ingestion
- Real citations or authority verification
- Hardcoded FAQ answers to suppress hallucinations
- Personalization profiles, accounts, or diet plan generators
- Streaming token UI (optional later; schema can still be returned as a final JSON object)

---

## 22. Success Criteria (Architecture View)

The architecture is successful when:

1. A public URL serves the chat UI and a working `/api/chat`.
2. Every successful assistant reply validates against the shared schema.
3. Every claim’s `source` is `null`.
4. The sources panel exists and is empty.
5. Blocked topics are refused in code under direct, rephrased, and multi-turn asks.
6. A failure log of 10 questions exists with grouped counts, and no hardcoded factual patches were added to “look better.”
7. Milestone 2 can add retrieval by filling sources without redesigning the app shell or public endpoints.
