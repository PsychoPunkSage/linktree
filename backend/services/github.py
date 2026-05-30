import asyncio
import json
from pathlib import Path
from datetime import datetime
import httpx
from config import settings

CACHE_PATH = Path("data/github_cache.json")
CACHE_TTL_SECONDS = 6 * 3600  # 6 hours

async def _fetch_repos() -> str:
    url = f"https://api.github.com/users/{settings.github_username}/repos"
    params = {"sort": "updated", "per_page": 30, "type": "public"}
    headers = {"Accept": "application/vnd.github.v3+json"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        repos = resp.json()

    lines = []
    for r in repos:
        lang = r.get("language") or "unknown"
        desc = r.get("description") or ""
        pushed = r.get("pushed_at", "")[:10]
        lines.append(f"- {r['name']} ({lang}) — {desc} [last push: {pushed}]")

    return "\n".join(lines) if lines else "No public repos found."

async def refresh_cache():
    try:
        summary = await _fetch_repos()
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps({
            "summary": summary,
            "fetched_at": datetime.utcnow().isoformat()
        }))
    except Exception:
        pass  # keep stale cache on failure

def get_cached_summary() -> str:
    if not CACHE_PATH.exists():
        return ""
    data = json.loads(CACHE_PATH.read_text())
    return data.get("summary", "")

async def start_github_cache():
    await refresh_cache()
    asyncio.create_task(_refresh_loop())

async def _refresh_loop():
    while True:
        await asyncio.sleep(CACHE_TTL_SECONDS)
        await refresh_cache()
