# Deployment plan

Deploy the AI Nutrition Assistant as two services:

| Piece | Host | What ships |
| --- | --- | --- |
| API | **Render** | FastAPI in `backend/` — Groq structured chat, scope gate, SQLite conversations |
| Frontend | Vercel | **Latest** React + Vite UI in `web/` (Stitch clinical dark theme) |

`stitch_ai_nutrition_assistant_ui/` is the design source only. Do not deploy it. The page users should see is the built output of `web/` (`ChatWindow`, empty `SourcesPanel`, decline styling).

Today the browser talks to the API on `http://127.0.0.1:8000` via `VITE_API_BASE` in local Vite. In production keep the same relative `/api/*` and `/health` contract: the browser calls the **Vercel origin**, and Vercel rewrites those paths to **Render**. Do not put `GROQ_API_KEY` on Vercel. Do not set a production `VITE_API_BASE` that points the browser at Render (CORS sprawl).

```text
Browser
  → Vercel (web/ → dist/)
      /, /assets/*              Vite static build (Stitch UI)
      /health, /api/*           rewritten to Render
  → Render (FastAPI)
      GET  /health
      POST /api/conversations
      POST /api/chat            → scope gate → Groq → SQLite
```

Deploy the API first. The Vercel rewrite needs the public Render URL (`https://….onrender.com`).

Maps to: [architecture.md](./architecture.md) §14 (topology is the same; host is Render instead of Railway), [implementation-plan.md](./implementation-plan.md) Phase 7.

Optional: root `railway.toml` / `nixpacks.toml` remain in the repo for a Railway alternative but are **not** used for the Render path.

---

## What must change before the first deploy

Local API starts as:

```bash
cd backend && uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

Render injects `PORT` and must bind `0.0.0.0`. Config is in root `render.yaml`. `vercel.json` / `web/vercel.json` still use a placeholder host until the Render service is live.

### 1. Production start command (Render)

Prefer **repo root as the service root** so `app.config.REPO_ROOT` (two levels above `backend/app/config.py`) still resolves to the monorepo root and `data/app.db` / `data/groq-usage.json` land in the expected place.

Root `render.yaml` (already in repo):

```yaml
services:
  - type: web
    name: ai-nutrition-api
    runtime: python
    plan: free
    buildCommand: pip install -r backend/requirements.txt
    startCommand: uvicorn app.main:create_app --factory --app-dir backend --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
```

`--app-dir backend` puts `app` on the import path while the process working directory stays the repo root.

Python: `.python-version` is `3.11`; `render.yaml` also sets `PYTHON_VERSION=3.11.9`. Do not point Render at `.venv`.

**Manual Web Service (same settings if you skip Blueprint):**

| Setting | Value |
| --- | --- |
| Runtime | Python 3 |
| Root Directory | leave empty (repo root) |
| Build Command | `pip install -r backend/requirements.txt` |
| Start Command | `uvicorn app.main:create_app --factory --app-dir backend --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |

### 2. Runtime dependencies

`backend/requirements.txt` is what Render installs (runtime only). Local/tests use `backend/requirements-dev.txt`. Do **not** put a root `requirements.txt` in the monorepo — Vercel will detect Python at the repo root and fail with “No python entrypoint found” if Root Directory is not set to `web`.

Runtime packages that must be present:

- `fastapi`, `uvicorn`, `python-dotenv`, `pydantic`
- `openai` (Groq OpenAI-compatible client)
- `sqlalchemy`

### 3. SQLite and ephemeral disk

| Path | Purpose | Git? | On Render |
| --- | --- | --- | --- |
| `data/app.db` | Conversation history | No (gitignored) | Created on first request. **Lost on redeploy** (and free-tier disk is ephemeral). |
| `data/groq-usage.json` | Local gpt-oss quota counters | No (gitignored) | Recreated on boot; counters reset on redeploy. Groq still enforces real quotas. |
| `backend/prompts/system.txt` | System prompt | Yes | Must ship in the image. |

**Prototype default (acceptable for Milestone 1):** no persistent disk. Document that history resets on every Render redeploy / cold recreate.

**Optional persistence:**

- Attach a Render **persistent disk** and set `DATABASE_URL=sqlite:////var/data/app.db` (or your mount path), **or**
- Provision Render Postgres and set `DATABASE_URL` to the Postgres URL SQLAlchemy accepts (add a Postgres driver to requirements if you go this route).

**Free-tier cold starts:** Render free web services sleep after idle. The first request after sleep can take 30–60+ seconds. Vercel rewrites may 502 if they time out waiting. Wake the API once (`curl https://YOUR-SERVICE.onrender.com/health`) before demoing the UI, or upgrade the Render plan.

Do not commit `.env`, `data/*.db`, or `data/groq-usage.json`.

### 4. Vercel rewrite file (latest frontend)

Both `vercel.json` (repo root) and `web/vercel.json` rewrite `/health` and `/api/*` and fall back to the SPA. Replace the placeholder with the real Render HTTPS host after the API is live. Do not leave `REPLACE_WITH_RENDER_URL` in production.

```json
{
  "rewrites": [
    { "source": "/health", "destination": "https://YOUR-SERVICE.onrender.com/health" },
    { "source": "/api/:path*", "destination": "https://YOUR-SERVICE.onrender.com/api/:path*" },
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

Update **both** files (root and `web/`) so either Root Directory layout works.

`web/src/api/client.ts` uses `VITE_API_BASE` only when set. For production:

- Leave `VITE_API_BASE` **unset** on Vercel so fetches stay same-origin (`/api/conversations`, `/api/chat`, `/health`).
- Keep `web/.env` / local `VITE_API_BASE=http://127.0.0.1:8000` for local Vite only.

The SPA fallback rewrite must stay **after** the API rewrites so `/api/*` is not swallowed by `index.html`.

### 5. CORS

With Vercel rewrites, the browser never talks to Render directly. Production `ALLOWED_ORIGINS` can stay empty.

Keep local origins for development:

`ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`

Do not use `allow_origins=["*"]` while `GROQ_API_KEY` is on the API.

### 6. What not to ship as the public UI

| Path | Deploy? |
| --- | --- |
| `web/` (Vite React app — Stitch UI) | **Yes** — this is the public frontend |
| `web/dist/` | Built by Vercel; do not commit |
| `stitch_ai_nutrition_assistant_ui/` | **No** — design HTML only |
| `backend/` | Render only |
| `.env` | **Never** |

---

## GitHub

Render and Vercel both deploy from GitHub ([ambrosh7/AINutrition-Chatbot](https://github.com/ambrosh7/AINutrition-Chatbot)).

1. Confirm `main` is up to date.
2. Confirm the remote does **not** contain `.env`, `web/.env`, `.venv/`, `node_modules/`, `data/*.db`, or `data/groq-usage.json`.
3. Confirm `backend/prompts/system.txt`, `web/src/**`, `render.yaml`, and `web/package.json` are in the commit.

Render: repo root. Vercel: Root Directory `web` (recommended) or repo root with root `vercel.json`.

---

## Render — API

1. [Render Dashboard](https://dashboard.render.com/) → **New** → **Blueprint** (uses `render.yaml`) **or** **Web Service** → connect this GitHub repo.
2. If Web Service manually: use the build/start commands in the table above. Service root = repository root.
3. Instances: **1** on free tier. The Groq usage limiter for `openai/gpt-oss-120b` counts inside one process (`data/groq-usage.json`). Prefer `qwen/qwen3.6-27b` if you hit 503 quota errors.
4. Environment (set in Render; `GROQ_API_KEY` is `sync: false` in the Blueprint so you must paste it):

| Variable | Value |
| --- | --- |
| `MODEL_PROVIDER` | `groq` |
| `GROQ_API_KEY` | from local `.env` only. **Never** put this on Vercel. |
| `GROQ_API_BASE_URL` | `https://api.groq.com/openai/v1` |
| `GROQ_MODEL` | `openai/gpt-oss-120b` (default) or `qwen/qwen3.6-27b` |
| `TEMPERATURE` | `0.2` |
| `DATABASE_URL` | `sqlite:///./data/app.db` (ephemeral) or disk/Postgres URL |
| `PROMPT_VERSION` | match current prompt label (e.g. `m1-v2`) |
| `ALLOWED_ORIGINS` | blank for rewrite-only prod |
| `HISTORY_MESSAGE_LIMIT` | `20` |
| `PYTHON_VERSION` | `3.11.9` (Blueprint sets this) |

`PORT` is set by Render. Do not override it.

5. After deploy, copy the public URL (`https://….onrender.com`) into both `vercel.json` files (replace `REPLACE_WITH_RENDER_URL`).
6. Health check path: `/health` → `{"status":"ok"}`.

Smoke test from a terminal **before** updating Vercel:

```bash
RENDER=https://YOUR-SERVICE.onrender.com

curl -sS "$RENDER/health"
# {"status":"ok"}

CONV=$(curl -sS -X POST "$RENDER/api/conversations" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['conversation_id'])")

curl -sS -X POST "$RENDER/api/chat" \
  -H 'content-type: application/json' \
  -d "{\"conversation_id\":\"$CONV\",\"message\":\"How long does cooked rice keep in the fridge?\"}"
```

Expect HTTP 200, a non-empty `answer`, `claims[].source` all `null`, and `meta.declined: false`.

Scope check:

```bash
curl -sS -X POST "$RENDER/api/chat" \
  -H 'content-type: application/json' \
  -d "{\"conversation_id\":\"$CONV\",\"message\":\"Give me a daily calorie target to lose weight.\"}"
```

Expect `meta.declined: true` without depending on the model alone.

`/docs` is disabled on purpose. Do not turn OpenAPI back on for production.

---

## Vercel — latest frontend (`web/`)

This is a **Vite + React + TypeScript** app. Vercel must build it.

1. Project already exists for this repo, or: New project → import the same GitHub repo.
2. Framework preset: **Vite**.
3. Root directory: **`web`**. If this stays empty / repo root, use root `vercel.json` (builds via `npm run build --prefix web`). Prefer Root Directory `web`.
4. Turn **off** “Include files outside the root directory in the Build Step” when Root Directory is `web`.
5. Build settings:

| Setting | Value |
| --- | --- |
| Install command | `npm install` |
| Build command | `npm run build` |
| Output directory | `dist` |
| Node version | 20.x |

6. Environment variables on Vercel:

| Variable | Production value |
| --- | --- |
| `VITE_API_BASE` | **Do not set** |
| `GROQ_API_KEY` | **Do not set** |

7. Commit both `vercel.json` files with the **real** Render host, push `main`, redeploy.
8. Confirm Production is a commit that contains the Stitch UI.

Production URL is `https://<project>.vercel.app`. Prefer that over the raw Render URL as the product entry point.

---

## End-to-end checks

Run these on the **Vercel** URL, in the browser.

- [ ] Stitch clinical dark UI loads (not a Python/Vercel error page).
- [ ] Empty state prompt cards work; sending one returns an assistant reply.
- [ ] Sources panel empty state visible (Milestone 1).
- [ ] Claims show `Source: —`.
- [ ] Calorie / medical asks show the decline card.
- [ ] Network panel: `/api/*` hits the **Vercel** host (rewrite), not `api.groq.com` and not a direct browser call to Render.
- [ ] No `GROQ_API_KEY` in the browser bundle.
- [ ] `GET https://<vercel>/health` returns `{"status":"ok"}` via rewrite (wake Render first on free tier).

---

## After it is up

- Redeploy Render on every `backend/` or prompt change. Bump `PROMPT_VERSION` when `system.txt` changes.
- Redeploy Vercel on every `web/` change.
- Rotate `GROQ_API_KEY` in Render only.
- Wake the Render service before demos if on free tier.
- Phase 8 failure log should run against the **public** Vercel URL once deploy is green.

---

## Checklist (Phase 7 exit)

- [ ] Render start command binds `0.0.0.0` and `$PORT`
- [ ] Public Render `GET /health` → `{"status":"ok"}`
- [ ] Live `POST /api/chat` returns schema-valid JSON with `claims[].source: null`
- [ ] Both `vercel.json` files use the real Render HTTPS host
- [ ] Vercel builds the Stitch UI and completes a chat round-trip via rewrite
- [ ] Model keys are Render-only
- [ ] Secrets stay gitignored

---

## Out of scope

- Deploying `stitch_ai_nutrition_assistant_ui/` HTML as the site
- Putting `GROQ_API_KEY` or provider URLs in `VITE_*` env
- Calling Render from the browser in production (skip rewrites)
- Milestone 2 retrieval / real citations
- User accounts, streaming tokens, or multi-region API replicas
- Hardcoding nutrition FAQ answers to beautify demos
