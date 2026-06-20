from typing import Generator

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from groq import Groq
except ImportError:
    Groq = None

try:
    from config import settings
except ImportError:
    settings = None

STATIC_FALLBACK = (
    "I'm temporarily offline.\n"
    "→ github.com/psychopunksage\n"
    "→ Check [ resume.pdf ] above"
)

_key_state = {"gemini": 0, "groq": 0}

def _stream_gemini(prompt: str, key: str) -> Generator[str, None, None]:
    genai.configure(api_key=key)
    model = genai.GenerativeModel(settings.gemini_model)
    response = model.generate_content(prompt, stream=True)
    for chunk in response:
        if chunk.text:
            yield chunk.text

def _stream_groq(prompt: str, key: str) -> Generator[str, None, None]:
    client = Groq(api_key=key)
    stream = client.chat.completions.create(
        model=settings.groq_model,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta

def _try_keys(prompt: str, stream_fn, keys: list[str], state_key: str) -> Generator[str, None, None]:
    if not keys:
        raise RuntimeError(f"No keys configured for {state_key}")
    n = len(keys)
    start = _key_state[state_key]
    for i in range(n):
        idx = (start + i) % n
        try:
            yield from stream_fn(prompt, keys[idx])
            _key_state[state_key] = idx
            return
        except Exception:
            _key_state[state_key] = (idx + 1) % n
            if i < n - 1:
                continue
            raise

def _parse_keys(raw: str) -> list[str]:
    return [k.strip() for k in raw.split(",") if k.strip()]

def stream_response(prompt: str, fallback_prompt: str | None = None) -> Generator[str, None, None]:
    """Stream a response from available AI backends.

    prompt: full prompt sent to Gemini (may be large — Gemini handles 1M tokens).
    fallback_prompt: smaller prompt for Groq if Gemini fails. Uses prompt when None.
    """
    try:
        yield from _try_keys(prompt, _stream_gemini, _parse_keys(settings.gemini_api_keys), "gemini")
        return
    except Exception:
        pass

    groq_prompt = fallback_prompt if fallback_prompt is not None else prompt
    try:
        yield from _try_keys(groq_prompt, _stream_groq, _parse_keys(settings.groq_api_keys), "groq")
        return
    except Exception:
        pass

    yield STATIC_FALLBACK
