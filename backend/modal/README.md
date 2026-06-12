# Modal Inference Service

Serves the fine-tuned portfolio SLM (Qwen2.5-3B QLoRA, GGUF) as a streaming HTTPS endpoint.
FastAPI calls this instead of Groq/Gemini when `MODAL_ENABLED=true`.

## Links

| What | URL |
|---|---|
| Inference endpoint | `https://abhinav-prakash319--abhinav-portfolio-slm-web.modal.run/generate` |
| Modal dashboard | `https://modal.com/apps/abhinav-prakash319/main/deployed/abhinav-portfolio-slm` |
| HuggingFace model | `https://huggingface.co/psychopunksage/portfolio-slm` |

---

## Model config

Set at the top of `app.py` — change these if the repo or file ever changes:

```python
HF_REPO_ID  = "psychopunksage/portfolio-slm"
HF_FILENAME = "abhinav-portfolio.Q4_K_M.gguf"   # 1.93GB, public repo
```

---

## First-time setup

```bash
cd backend
source .venv/bin/activate
pip install modal
modal setup   # opens browser — authenticate with your Modal account
```

Modal workspace: `abhinav-prakash319`

---

## Deploy

Run from `backend/` with venv active:

```bash
cd backend
source .venv/bin/activate
modal deploy modal/app.py
```

First deploy takes a few minutes — Modal builds the container image and installs `llama-cpp-python`.
Subsequent deploys are fast (image is cached).

Expected output:
```
✓ Created objects.
├── 🔨 Created mount ...
├── 🔨 Created web function web => https://abhinav-prakash319--abhinav-portfolio-slm-web.modal.run
└── ✓ App deployed!
```

---

## Test after deploy

### Smoke test (just prints the endpoint URL)

```bash
modal run modal/app.py::smoke_test
```

### curl (full streaming test)

```bash
curl -X POST "https://abhinav-prakash319--abhinav-portfolio-slm-web.modal.run/generate" \
  -H "Content-Type: application/json" \
  -d '{"question": "Where do you currently work?"}' \
  --no-buffer
```

Expected response — tokens stream in one at a time, ending with `[DONE]`:

```
data: {"token": "I"}
data: {"token": "'m"}
data: {"token": " at"}
data: {"token": " Supra"}
...
data: [DONE]
```

**First call after a period of inactivity:** cold start takes 15–30 seconds (Modal spins up the container). The 1.93GB GGUF is cached in a persistent volume after the first download — subsequent cold starts skip the download.

---

## How it works

- `@modal.asgi_app()` — full ASGI app, no response buffering (critical for SSE streaming)
- `model_volume` — persistent Modal volume at `/model`, caches the GGUF between invocations
- `X-Accel-Buffering: no` header — tells Caddy not to buffer the SSE stream
- `memory=4096` — 4GB container memory (1.93GB model + llama.cpp overhead)
- Fallback: if Modal is down or slow, set `MODAL_ENABLED=false` in `backend/.env` and restart FastAPI — traffic instantly falls back to Groq/Gemini

---

## Retrain / update model

If you upload a new GGUF to HuggingFace:

1. Update `HF_FILENAME` in `app.py` if the filename changed
2. Clear the volume cache (stale model):
   ```bash
   modal volume rm portfolio-model-cache
   modal volume create portfolio-model-cache
   ```
3. Redeploy:
   ```bash
   modal deploy modal/app.py
   ```
