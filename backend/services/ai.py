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

def _stream_gemini(prompt: str) -> Generator[str, None, None]:
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt, stream=True)
    for chunk in response:
        if chunk.text:
            yield chunk.text

def _stream_groq(prompt: str) -> Generator[str, None, None]:
    client = Groq(api_key=settings.groq_api_key)
    stream = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta

def stream_response(prompt: str) -> Generator[str, None, None]:
    try:
        yield from _stream_gemini(prompt)
        return
    except Exception:
        pass

    try:
        yield from _stream_groq(prompt)
        return
    except Exception:
        pass

    yield STATIC_FALLBACK
