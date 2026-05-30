import google.generativeai as genai
from config import settings
from db import update_session_profile, get_conn

PROFILER_PROMPT = """Given a visitor's questions on a portfolio site, infer who they are.

Questions so far:
{questions}

Referrer: {referrer}
User-agent hint: {ua_hint}

Respond in this exact format (one field per line):
type: recruiter|engineer|researcher|collaborator|student|unknown
company: <inferred company or 'unknown'>
level: low|mid|high
intent: hiring|networking|curiosity|vetting|research|unknown
confidence: <float 0.0-1.0>
notes: <one sentence reasoning>"""

def _ua_hint(ua: str) -> str:
    ua = ua.lower()
    if "linkedin" in ua: return "linkedin app"
    if "mobile" in ua or "android" in ua or "iphone" in ua: return "mobile browser"
    return "desktop browser"

def _parse_profile(text: str) -> dict:
    result = {
        "inferred_type": "unknown", "inferred_company": "unknown",
        "technical_level": "unknown", "inferred_intent": "unknown",
        "confidence": 0.5, "inference_notes": ""
    }
    for line in text.strip().splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        val = val.strip()
        key = key.strip()
        if key == "type":     result["inferred_type"]     = val
        if key == "company":  result["inferred_company"]  = val
        if key == "level":    result["technical_level"]   = val
        if key == "intent":   result["inferred_intent"]   = val
        if key == "confidence":
            try: result["confidence"] = float(val)
            except ValueError: pass
        if key == "notes":    result["inference_notes"]   = val
    return result

async def run_profiler(session_id: str):
    if not settings.gemini_api_key:
        return

    with get_conn() as conn:
        rows = conn.execute(
            "SELECT question FROM chat_logs WHERE session_id = ? ORDER BY created_at",
            (session_id,)
        ).fetchall()
        session = conn.execute(
            "SELECT referrer, user_agent FROM sessions WHERE id = ?",
            (session_id,)
        ).fetchone()

    if not rows or not session:
        return

    questions = "\n".join(f"- {r['question']}" for r in rows)
    referrer = session["referrer"] or "direct"
    ua_hint = _ua_hint(session["user_agent"] or "")

    try:
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            PROFILER_PROMPT.format(
                questions=questions, referrer=referrer, ua_hint=ua_hint
            )
        )
        profile = _parse_profile(response.text)
        update_session_profile(session_id, **profile)
    except Exception:
        pass
