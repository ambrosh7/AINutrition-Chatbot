# AI Nutrition Assistant

Milestone 1 prototype: a chatbot for food, nutrition, and food safety questions. Answers come from the model’s own knowledge. Claim `source` fields stay `null` until Milestone 2.

See [problemStatement.md](./problemStatement.md), [architecture.md](./architecture.md), [implementation-plan.md](./implementation-plan.md), and [deployment-plan.md](./deployment-plan.md).

## Status

Phase 7 coding ready — **Railway (API) + Vercel (frontend)**. If Railway shows “Free plan resource provision limit exceeded”, delete unused projects first (no Hobby upgrade required).

## Requirements

- Python 3.11+ (see `.python-version`)
- Node 20+ for the Vite frontend
- A Groq API key for live chat

## Local setup (API)

```bash
cd backend
python3.12 -m venv .venv   # any 3.11+ works
source .venv/bin/activate
pip install -r requirements-dev.txt
cp ../.env.example ../.env
```

Set `GROQ_API_KEY` in `.env`. Optionally set `GROQ_MODEL` to `qwen/qwen3.6-27b`. Health check does not need a key.

## Local setup (frontend)

```bash
cd web
cp .env.example .env   # sets VITE_API_BASE for local API
npm install
npm run dev
```

Open http://127.0.0.1:5173 against the API on port 8000.

## Run API

From the `backend/` directory:

```bash
uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

```bash
curl -s http://127.0.0.1:8000/health
# {"status":"ok"}

CONV=$(curl -s -X POST http://127.0.0.1:8000/api/conversations | python3 -c "import sys,json; print(json.load(sys.stdin)['conversation_id'])")
curl -s -X POST http://127.0.0.1:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d "{\"conversation_id\":\"$CONV\",\"message\":\"How long does cooked rice keep?\"}"
```

## Storage

- Local default: SQLite at `data/app.db` (created on first start). The file is gitignored.
- Railway: without a volume, SQLite history resets on redeploy. Optional: attach a volume and set `DATABASE_URL=sqlite:////data/app.db`, or use a Postgres `DATABASE_URL`.

## Deploy (Railway + Vercel)

Full steps: [deployment-plan.md](./deployment-plan.md). Short path:

### Free Railway quota (if upgrade popup appears)

You do **not** need Hobby:

1. Railway → **Projects**
2. Open an unused project → **Settings** → **Delete project**
3. Or reuse a project: **Add service** → GitHub → this repo (instead of New Project)

### API on Railway

1. Deploy from GitHub → `ambrosh7/AINutrition-Chatbot` (repo root; uses `railway.toml`).
2. Variables: from `.env.example`; set real `GROQ_API_KEY`.
3. **Settings → Networking → Generate Domain**.
4. Confirm `GET https://YOUR-SERVICE.up.railway.app/health` → `{"status":"ok"}`.

### Wire Vercel

1. Replace `REPLACE_WITH_RAILWAY_URL` in **both** `vercel.json` and `web/vercel.json` (keep `https://`).
2. Push `main` and redeploy Vercel (Root Directory `web`). Do **not** set `VITE_API_BASE` or `GROQ_API_KEY` on Vercel.

Public entry point is the Vercel URL. Do not deploy `stitch_ai_nutrition_assistant_ui/`.

## Prompt eval

With the API running:

```bash
python scripts/run_eval.py
```

See [docs/prompt-eval.md](./docs/prompt-eval.md). After editing `backend/prompts/system.txt`, bump `PROMPT_VERSION` and re-run the full set.

## Tests

```bash
cd backend && source .venv/bin/activate
pip install -r requirements-dev.txt
cd ..
pytest -q
```

## Environment

| Variable | Purpose |
| --- | --- |
| `MODEL_PROVIDER` | `groq` |
| `GROQ_API_KEY` | Groq API key (Railway only) |
| `GROQ_API_BASE_URL` | Default `https://api.groq.com/openai/v1` |
| `GROQ_MODEL` | `openai/gpt-oss-120b` (default) or `qwen/qwen3.6-27b` |
| `TEMPERATURE` | Default `0.2` |
| `DATABASE_URL` | Default `sqlite:///./data/app.db` |
| `PROMPT_VERSION` | Prompt label stored on assistant rows (currently `m1-v2`) |
| `ALLOWED_ORIGINS` | CORS origins for local Vite; blank OK behind Vercel rewrites |
| `HISTORY_MESSAGE_LIMIT` | Max prior user/assistant messages sent to the model (default `20`) |
| `VITE_API_BASE` | Local frontend only; unset on Vercel |

For `openai/gpt-oss-120b`, the backend enforces Groq free-tier style caps before each call (30 RPM, 1k RPD, 8k TPM, 200k TPD). Prefer switching to `qwen/qwen3.6-27b` or waiting for the window to clear rather than retry-spamming. Quota state lives in `data/groq-usage.json`.

Never commit `.env` or real API keys.
