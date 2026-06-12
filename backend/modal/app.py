"""
Modal inference service for the portfolio SLM.

Deploy:  modal deploy modal/app.py   (run from backend/)
Test:    modal run modal/app.py::smoke_test
"""

import json
import os
from pathlib import Path

import modal

# ---------------------------------------------------------------------------
# Config — change these if the model repo or filename ever changes
# ---------------------------------------------------------------------------

HF_REPO_ID   = "psychopunksage/portfolio-slm"
HF_FILENAME  = "abhinav-portfolio.Q4_K_M.gguf"   # configurable: swap for any GGUF in the repo
MODEL_DIR    = Path("/model")

SYSTEM_PROMPT = (
    "You are Abhinav Prakash (handle: psychopunksage). "
    "You are a systems engineer focused on blockchain infrastructure, "
    "low-level systems programming, and Linux kernel development. "
    "You write Rust, Go, Solidity, and C. You are direct, technically precise, "
    "with dry humor. You have no patience for unnecessary abstraction. "
    "Answer all questions about yourself in first person. "
    "Be specific — give company names, dates, technologies, outcomes. "
    "Do not say 'I cannot answer that' for questions about yourself."
)

# ---------------------------------------------------------------------------
# Modal image — what gets installed inside the cloud container
# ---------------------------------------------------------------------------

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements("modal/requirements.txt")
)

app = modal.App("abhinav-portfolio-slm", image=image)

# Persistent volume: the 1.93GB GGUF is downloaded once and cached here.
# Subsequent cold starts skip the download entirely.
model_volume = modal.Volume.from_name("portfolio-model-cache", create_if_missing=True)

# ---------------------------------------------------------------------------
# ASGI app — gives us full control over the response pipeline (no buffering)
# ---------------------------------------------------------------------------

@app.function(
    volumes={str(MODEL_DIR): model_volume},
    memory=4096,   # 1.93GB model + llama.cpp overhead — 4GB is safe headroom
    timeout=120,
)
@modal.asgi_app()
def web():
    from fastapi import FastAPI, Request
    from fastapi.responses import StreamingResponse
    from huggingface_hub import hf_hub_download
    from llama_cpp import Llama

    api = FastAPI()

    # Download model on first cold start, use cache on all subsequent ones
    model_path = MODEL_DIR / HF_FILENAME
    if not model_path.exists():
        hf_hub_download(
            repo_id=HF_REPO_ID,
            filename=HF_FILENAME,
            local_dir=str(MODEL_DIR),
        )
        model_volume.commit()

    llm = Llama(
        model_path=str(model_path),
        n_ctx=2048,
        n_threads=4,
        verbose=False,
    )

    @api.post("/generate")
    async def generate(request: Request):
        body = await request.json()
        question = body.get("question", "")

        def token_stream():
            stream = llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": question},
                ],
                max_tokens=512,
                temperature=0.3,
                stream=True,
            )
            for chunk in stream:
                delta = chunk["choices"][0]["delta"]
                if "content" in delta and delta["content"]:
                    yield f"data: {json.dumps({'token': delta['content']})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            token_stream(),
            media_type="text/event-stream",
            headers={
                "X-Accel-Buffering": "no",   # tells any upstream proxy (Caddy, nginx) not to buffer
                "Cache-Control": "no-cache",
            },
        )

    return api


# ---------------------------------------------------------------------------
# Smoke test — run with: modal run modal/app.py::smoke_test
# ---------------------------------------------------------------------------

@app.local_entrypoint()
def smoke_test():
    print(web.web_url)
