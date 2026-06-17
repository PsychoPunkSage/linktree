from typing import AsyncGenerator
import json
import httpx

try:
    from config import settings
except ImportError:
    settings = None


async def stream_from_slm(question: str, context: str = "") -> AsyncGenerator[str, None]:
    if not settings or not settings.modal_endpoint:
        raise RuntimeError("MODAL_ENDPOINT not configured")

    async with httpx.AsyncClient(timeout=90) as client:
        async with client.stream(
            "POST",
            settings.modal_endpoint,
            json={"question": question, "context": context},
            headers={"Accept": "text/event-stream"},
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                payload = line[len("data: "):]
                if payload == "[DONE]":
                    return
                try:
                    token = json.loads(payload).get("token", "")
                    if token:
                        yield token
                except json.JSONDecodeError:
                    continue
