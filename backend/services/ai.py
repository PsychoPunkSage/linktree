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
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt, stream=True)
    for chunk in response:
        if chunk.text:
            yield chunk.text

def _stream_groq(prompt: str, key: str) -> Generator[str, None, None]:
    client = Groq(api_key=key)
    stream = client.chat.completions.create(
        model="llama3-8b-8192",
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

def stream_response(prompt: str) -> Generator[str, None, None]:
    try:
        yield from _try_keys(prompt, _stream_gemini, settings.gemini_api_keys, "gemini")
        return
    except Exception:
        pass

    try:
        yield from _try_keys(prompt, _stream_groq, settings.groq_api_keys, "groq")
        return
    except Exception:
        pass

    yield STATIC_FALLBACK
