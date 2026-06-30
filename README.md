# Terminal Portfolio

A terminal-aesthetic personal portfolio with an AI chatbot that answers as you. Visitors ask questions; the backend answers using RAG over your context files + Gemini/Groq.

## Stack

- **Backend:** FastAPI · ChromaDB (RAG) · Gemini + Groq · SQLite (logs)
- **Frontend:** Vanilla JS · Alpine.js · SSE streaming · canvas animation
- **Deployment:** Docker Compose · Caddy (TLS) · Umami (analytics)
- **Optional SLM:** Qwen2.5-3B fine-tuned via Unsloth + QLoRA on Colab, served on Modal

---

## Setup

### 1. Clone and configure the backend

```bash
cp backend/.env.example backend/.env
```

Fill in `backend/.env`:

| Key | What to set |
|-----|-------------|
| `GEMINI_API_KEYS` | Comma-separated Gemini API keys |
| `GROQ_API_KEYS` | Comma-separated Groq API keys |
| `ADMIN_SECRET` | Any strong random string |
| `GITHUB_USERNAME` | Your GitHub username (for repo pinning) |
| `ALLOWED_ORIGIN` | Your frontend URL, e.g. `https://yourdomain.dev` |
| `DOMAIN` | Your domain, e.g. `yourdomain.dev` |
| `CONTEXT_ENCRYPTION_KEY` | Strong passphrase for encrypting context files |
| `UMAMI_SECRET` | Random string for Umami analytics session signing |
| `POSTGRES_*` | Postgres credentials for Umami |

### 2. Write your context (your personal data — never committed)

```bash
cp backend/data/context/core.md.example backend/data/context/core.md
# Edit core.md with your info
```

Then create the detail files (all gitignored):

```
backend/data/context/detail/experience.md  — work history
backend/data/context/detail/projects.md    — projects
backend/data/context/detail/skills.md      — skills
backend/data/context/detail/setup.md       — your setup / gear
```

Encrypt them after editing:

```bash
./scripts/encrypt-context.sh
```

### 3. Configure the frontend

```bash
cp frontend/env.js.example frontend/env.js
# Fill in your name, domain, social links, etc.
```

### 4. Deploy

```bash
cd backend
docker compose up -d
```

Caddy handles TLS automatically for `api.{$DOMAIN}` and `analytics.{$DOMAIN}`.

---

## Local testing

```bash
# Backend
cd backend && uvicorn main:app --reload   # runs on :8000

# Frontend
cd frontend && python3 -m http.server 5500
```

Change two values for local testing (revert before deploy):

- `frontend/env.js` → set `API: 'http://localhost:8000'`
- `backend/.env` → set `ALLOWED_ORIGIN=http://localhost:5500`

---

## Optional: Fine-tune a local SLM

Train a personal Qwen2.5-3B model on your Q&A pairs:

```bash
# Generate training data from your context files
cd training && python3 scripts/regenerate_with_context.py

# Upload training/qa_dataset.jsonl to Google Drive
# Open training/finetune.ipynb in Colab (T4 GPU)
# Follow the notebook — it exports a GGUF and deploys to Modal
```

See `training/` for details. The `qa_dataset.jsonl` is gitignored — it contains your personal data.

---

## What's gitignored (your personal data)

```
backend/.env                          # secrets + config
backend/data/context/core.md          # your bio
backend/data/context/detail/*.md      # experience, projects, skills
backend/data/github_cache.json        # fetched at runtime
backend/data/portfolio.db             # chat logs
backend/data/vectordb/                # embeddings (rebuilt from context)
training/qa_dataset*.jsonl            # your personal Q&A training data
frontend/env.js                       # your identity + API URL
```

Everything committed is the framework. Everything gitignored is you.
