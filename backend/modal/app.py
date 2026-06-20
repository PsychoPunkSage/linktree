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
# Config — all values read from environment (set via Modal secrets or .env)
# ---------------------------------------------------------------------------

HF_REPO_ID  = os.environ.get("HF_REPO_ID", "")
HF_FILENAME = os.environ.get("HF_FILENAME", "")
MODEL_DIR   = Path(os.environ.get("MODEL_DIR", "/model"))

SYSTEM_PROMPT = os.environ.get("SLM_SYSTEM_PROMPT", "")

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
model_volume = modal.Volume.from_name(os.environ.get("MODAL_VOLUME_NAME", ""), create_if_missing=True)

# ---------------------------------------------------------------------------
# ASGI app — gives us full control over the response pipeline (no buffering)
# ---------------------------------------------------------------------------

@app.function(
    volumes={str(MODEL_DIR): model_volume},
    memory=int(os.environ.get("MODAL_MEMORY", "4096")),
    timeout=int(os.environ.get("MODAL_TIMEOUT", "120")),
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
        n_ctx=int(os.environ.get("LLM_N_CTX", "4096")),
        n_threads=int(os.environ.get("LLM_N_THREADS", "4")),
        verbose=False,
    )

    @api.post("/generate")
    async def generate(request: Request):
        body = await request.json()
        question = body.get("question", "")
        context  = body.get("context", "").strip()

        user_message = (
            f"Context:\n{context}\n\nQuestion: {question}"
            if context else question
        )

        def token_stream():
            stream = llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_message},
                ],
                max_tokens=int(os.environ.get("LLM_MAX_TOKENS", "512")),
                temperature=float(os.environ.get("LLM_TEMPERATURE", "0.3")),
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
