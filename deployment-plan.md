# Deployment plan

Deploy the AI Nutrition Assistant as two services:

| Piece | Host | What ships |
| --- | --- | --- |
| API | Railway | FastAPI in `backend/` — Groq structured chat, scope gate, SQLite conversations |
| Frontend | Vercel | **Latest** React + Vite UI in `web/` (Stitch clinical dark theme) |

`stitch_ai_nutrition_assistant_ui/` is the design source only. Do not deploy it. The page users should see is the built output of `web/` (`ChatWindow`, empty `SourcesPanel`, decline styling).

Today the browser talks to the API on `http://127.0.0.1:8000` via `VITE_API_BASE` in local Vite. In production keep the same relative `/api/*` and `/health` contract: the browser calls the **Vercel origin**, and Vercel rewrites those paths to Railway. Do not put `GROQ_API_KEY` on Vercel. Do not set a production `VITE_API_BASE` that points the browser at Railway (CORS sprawl).

```text
Browser
  → Vercel (web/ → dist/)
      /, /assets/*              Vite static build (Stitch UI)
      /health, /api/*           rewritten to Railway
  → Railway (FastAPI)
      GET  /health
      POST /api/conversations
      POST /api/chat            → scope gate → Groq → SQLite
```

Deploy the API first. The Vercel rewrite needs the public Railway URL.

Maps to: [architecture.md](./architecture.md) §14, [implementation-plan.md](./implementation-plan.md) Phase 7.

---

## What must change before the first deploy

Local API starts as:

```bash
cd backend && uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

Railway injects `PORT` and must bind `0.0.0.0`. Root `railway.toml` / `nixpacks.toml` are in the repo. `vercel.json` still has a placeholder host until the Railway service is live.

### 0. Free-plan limit (“Upgrade to create a new project”)

Trial/free accounts can hit **resource provision limit** after a few projects. You do **not** need Hobby:

1. Delete unused Railway projects (Project → Settings → Delete project), **or**
2. Reuse an existing project: **Add service** → GitHub → this repo.

Then continue below.

### 1. Production start command (Railway)

Prefer **repo root as the Railway service root** so `app.config.REPO_ROOT` (two levels above `backend/app/config.py`) still resolves to the monorepo root and `data/app.db` / `data/groq-usage.json` land in the expected place.

Root `railway.toml` (already in repo):

```toml
[build]
builder = "NIXPACKS"
buildCommand = "pip install -r backend/requirements.txt"

[deploy]
startCommand = "uvicorn app.main:create_app --factory --app-dir backend --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
```

`--app-dir backend` puts `app` on the import path while the process working directory stays the repo root.

Pin Python 3.11+ (Nixpacks): add a root `.python-version` with `3.11`, or set Railway variable `NIXPACKS_PYTHON_VERSION=3.11`. Do not point Railway at `.venv`.

**Alternative:** set Railway Root Directory to `backend/` and use:

```toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "uvicorn app.main:create_app --factory --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
```

If you use that alternative, set an absolute `DATABASE_URL` (and accept that default `REPO_ROOT`-relative `data/` paths may not match the monorepo layout). Prefer the repo-root service layout above.

### 2. Runtime dependencies

`backend/requirements.txt` is what Railway installs (runtime only). Local/tests use `backend/requirements-dev.txt`. Do **not** put a root `requirements.txt` in the monorepo — Vercel will detect Python at the repo root and fail with “No python entrypoint found” if Root Directory is not set to `web`.

Runtime packages that must be present:

- `fastapi`, `uvicorn`, `python-dotenv`, `pydantic`
- `openai` (Groq OpenAI-compatible client)
- `sqlalchemy`

### 3. SQLite and ephemeral disk

| Path | Purpose | Git? | On Railway |
| --- | --- | --- | --- |
| `data/app.db` | Conversation history | No (gitignored) | Created on first request. **Lost on redeploy** unless a volume or Postgres is used. |
| `data/groq-usage.json` | Local gpt-oss quota counters | No (gitignored) | Recreated on boot; counters reset on redeploy. Groq still enforces real quotas. |
| `backend/prompts/system.txt` | System prompt | Yes | Must ship in the image. |

**Prototype default (acceptable for Milestone 1):** no volume. Document that history resets on every Railway redeploy.

**Optional persistence:**

- Attach a Railway volume at `/data` and set `DATABASE_URL=sqlite:////data/app.db` (four slashes = absolute path), **or**
- Provision Railway Postgres and set `DATABASE_URL` to the Postgres URL SQLAlchemy accepts.

Do not commit `.env`, `data/*.db`, or `data/groq-usage.json`.

### 4. Vercel rewrite file (latest frontend)

`web/vercel.json` already rewrites `/health` and `/api/*` and falls back to the SPA. Replace the placeholder with the real Railway HTTPS host after the API is live. Do not leave `REPLACE_WITH_RAILWAY_URL` in production.

```json
{
  "rewrites": [
    { "source": "/health", "destination": "https://YOUR-SERVICE.up.railway.app/health" },
    { "source": "/api/:path*", "destination": "https://YOUR-SERVICE.up.railway.app/api/:path*" },
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

`web/src/api/client.ts` uses `VITE_API_BASE` only when set. For production:

- Leave `VITE_API_BASE` **unset** on Vercel so fetches stay same-origin (`/api/conversations`, `/api/chat`, `/health`).
- Keep `web/.env` / local `VITE_API_BASE=http://127.0.0.1:8000` for local Vite only (gitignored or `.env.example` only).

The SPA fallback rewrite must stay **after** the API rewrites so `/api/*` is not swallowed by `index.html`.

### 5. CORS

With Vercel rewrites, the browser never talks to Railway directly. Production `ALLOWED_ORIGINS` can stay empty or omit the Vercel origin.

Keep local origins for development:

`ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`

Do not use `allow_origins=["*"]` while `GROQ_API_KEY` is on the API.

### 6. What not to ship as the public UI

| Path | Deploy? |
| --- | --- |
| `web/` (Vite React app — Stitch UI) | **Yes** — this is the public frontend |
| `web/dist/` | Built by Vercel; do not commit |
| `stitch_ai_nutrition_assistant_ui/` | **No** — design HTML only |
| `backend/` | Railway only |
| `.env` | **Never** |

---

## GitHub

Railway and Vercel both deploy from GitHub.

1. Create a dedicated GitHub repo for this project (do not fold it into an unrelated repo).
2. Initialize git at the monorepo root if needed; push `main`.
3. Confirm the remote does **not** contain `.env`, `web/.env`, `.venv/`, `node_modules/`, `data/*.db`, or `data/groq-usage.json`.
4. Confirm `backend/prompts/system.txt`, `web/src/**`, and `web/package.json` are in the commit.

Both platforms track `main`. Railway service root: **repository root** (recommended). Vercel root directory: **`web`**.

---

## Railway — API

1. New project → Deploy from GitHub → this repo.
2. Service root: repository root. Builder: Nixpacks (from `railway.toml`).
3. Instances: **1**. The Groq usage limiter for `openai/gpt-oss-120b` counts inside one process (`data/groq-usage.json`). A second instance would double-count locally and can burn the free-tier daily budget faster. Prefer `qwen/qwen3.6-27b` if you hit 503 quota errors.
4. Variables (service scope, not committed):

| Variable | Value |
| --- | --- |
| `MODEL_PROVIDER` | `groq` |
| `GROQ_API_KEY` | from local `.env` only. **Never** put this on Vercel. |
| `GROQ_API_BASE_URL` | `https://api.groq.com/openai/v1` |
| `GROQ_MODEL` | `openai/gpt-oss-120b` (default) or `qwen/qwen3.6-27b` |
| `TEMPERATURE` | `0.2` |
| `DATABASE_URL` | `sqlite:///./data/app.db` (ephemeral) or volume/Postgres URL |
| `PROMPT_VERSION` | match current prompt label (e.g. `m1-v2`) |
| `ALLOWED_ORIGINS` | leave blank for rewrite-only prod, or keep localhost for debugging |
| `HISTORY_MESSAGE_LIMIT` | `20` |
| `NIXPACKS_PYTHON_VERSION` | `3.11` (if no `.python-version`) |

`PORT` is set by Railway. Do not override it.

5. Generate a public domain. Copy the `https://….up.railway.app` host into `web/vercel.json`.
6. Health check path: `/health` → `{"status":"ok"}`.

Smoke test from a terminal **before** touching Vercel:

```bash
RAILWAY=https://YOUR-SERVICE.up.railway.app

curl -sS "$RAILWAY/health"
# {"status":"ok"}

CONV=$(curl -sS -X POST "$RAILWAY/api/conversations" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['conversation_id'])")

curl -sS -X POST "$RAILWAY/api/chat" \
  -H 'content-type: application/json' \
  -d "{\"conversation_id\":\"$CONV\",\"message\":\"How long does cooked rice keep in the fridge?\"}"
```

Expect HTTP 200, a non-empty `answer`, `claims[].source` all `null`, and `meta.declined: false`.

Scope check:

```bash
curl -sS -X POST "$RAILWAY/api/chat" \
  -H 'content-type: application/json' \
  -d "{\"conversation_id\":\"$CONV\",\"message\":\"Give me a daily calorie target to lose weight.\"}"
```

Expect `meta.declined: true` without depending on the model alone.

`/docs` is disabled on purpose. Do not turn OpenAPI back on for production.

Optional: add a simple IP / token-bucket rate limit on `POST /api/chat` before the URL is widely shared (architecture §19). Not required for first ship.

---

## Vercel — latest frontend (`web/`)

This is a **Vite + React + TypeScript** app, not a plain static folder. Vercel must build it.

1. New project → import the **same** GitHub repo.
2. Framework preset: **Vite** (or Other with the settings below).
3. Root directory: **`web`**. If this stays empty / repo root, Vercel treats the monorepo as Python (sees `backend/`, `tests/conftest.py`) and errors with `No python entrypoint found`.
4. In Root Directory settings, turn **off** “Include files outside the root directory in the Build Step”. The install must be `web/package.json` only.
5. Build settings:

| Setting | Value |
| --- | --- |
| Install command | `npm install` (default) |
| Build command | `npm run build` |
| Output directory | `dist` |
| Node version | 20.x (or Vercel default LTS) |

6. Environment variables on Vercel:

| Variable | Production value |
| --- | --- |
| `VITE_API_BASE` | **Do not set** (empty / same-origin via rewrites) |
| `GROQ_API_KEY` | **Do not set** — ever |

7. Commit `web/vercel.json` with the **real** Railway host, push `main`, deploy.
8. Confirm Production is the latest `main` commit that contains the Stitch UI (`AppHeader`, dark clinical theme, empty sources panel copy).

Production URL is `https://<project>.vercel.app`. That is the URL to share. Prefer not to hand users the raw Railway URL as the product entry point.

### Local production-shape check (optional)

```bash
cd web
# temporarily point vercel.json at a running Railway URL, or use preview
npm run build
npm run preview
```

For a true rewrite test you need the deployed Vercel project; `vite preview` alone does not apply `vercel.json` rewrites.

---

## End-to-end checks

Run these on the **Vercel** URL, in the browser.

- [ ] The page is the **Stitch clinical dark UI** (Plus Jakarta / DM Sans, sage accents, “Nutrition Assistant” header) — not the old light “Nourish” theme and not the raw Stitch `code.html` mock.
- [ ] Empty state shows example prompt cards; sending one creates a conversation and an assistant reply.
- [ ] Sources panel is visible and shows the Milestone 1 empty state (“Citations will appear here” / sources empty).
- [ ] A normal food-safety question returns an answer; claims under the reply show `Source: —`.
- [ ] A calorie-target or medical-diet ask shows the decline card (`Clinical Scope Notice`), not a personal plan.
- [ ] Multi-turn works in one session (second message still has context) until Railway redeploys if SQLite is ephemeral.
- [ ] Network panel: `/api/conversations` and `/api/chat` go to the **Vercel** host (same origin), not `api.groq.com` and not a direct Railway call from the browser.
- [ ] View source / built JS: no `GROQ_API_KEY`, no Groq base URL secrets.
- [ ] `GET https://<vercel>/health` returns `{"status":"ok"}` via rewrite.

---

## After it is up

- Redeploy Railway on every `backend/` or prompt change. Bump `PROMPT_VERSION` when `system.txt` changes.
- Redeploy Vercel on every `web/` change (new Stitch UI iterations).
- Rotate `GROQ_API_KEY` in Railway variables only. Confirm a chat still returns a parseable `ChatResponse`.
- Keep a single Railway instance while the in-process Groq limiter is file-backed.
- If you later attach a custom domain on Vercel, rewrites keep working; no CORS change needed while the browser stays same-origin.
- Logs: Railway should show structured chat handling and declines. Do not log API keys or full provider error bodies to public channels.
- Phase 8 failure log (`docs/failure-log.md`) should be run against the **public** URL once deploy is green.

---

## Checklist (Phase 7 exit)

- [ ] `railway.toml` (or Railway start command) binds `0.0.0.0` and `$PORT`
- [ ] Public Railway `GET /health` → `{"status":"ok"}`
- [ ] Live `POST /api/chat` returns schema-valid JSON with `claims[].source: null`
- [ ] `web/vercel.json` uses the real Railway HTTPS host
- [ ] Vercel builds `web/` → `dist` from latest frontend
- [ ] Public Vercel URL loads the Stitch UI and completes a chat round-trip via rewrite
- [ ] Model keys are Railway-only
- [ ] Project is on GitHub with secrets gitignored

---

## Out of scope

- Deploying `stitch_ai_nutrition_assistant_ui/` HTML as the site
- Putting `GROQ_API_KEY` or provider URLs in `VITE_*` env
- Calling Railway from the browser in production (skip rewrites)
- Milestone 2 retrieval / real citations in the sources panel
- User accounts, streaming tokens, or multi-region API replicas
- Hardcoding nutrition FAQ answers to beautify demos
