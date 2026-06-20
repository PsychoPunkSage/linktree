from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from routers import chat, github, admin
from services.context import init_context
from services.github import start_github_cache
from db import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    missing = [k for k, v in {
        "ADMIN_SECRET":   settings.admin_secret,
        "ALLOWED_ORIGIN": settings.allowed_origin,
        "GITHUB_USERNAME": settings.github_username,
    }.items() if not v]
    if missing:
        raise RuntimeError(f"Required env vars not set: {', '.join(missing)}")
    init_db()
    init_context()
    await start_github_cache()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.allowed_origin],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(chat.router)
app.include_router(github.router)
app.include_router(admin.router)

@app.get("/health")
def health():
    return {"status": "ok"}
