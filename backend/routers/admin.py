from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from config import settings
from db import get_recent_sessions, get_top_questions, get_stats_today, get_referrer_breakdown

router = APIRouter()
templates = Jinja2Templates(directory="templates")

COOKIE_NAME = "pps_admin"
COOKIE_MAX_AGE = 30 * 24 * 3600  # 30 days

def _make_token() -> str:
    s = URLSafeTimedSerializer(settings.admin_secret)
    return s.dumps("admin")

def _verify_token(token: str) -> bool:
    s = URLSafeTimedSerializer(settings.admin_secret)
    try:
        s.loads(token, max_age=COOKIE_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False

def _is_authed(request: Request) -> bool:
    token = request.cookies.get(COOKIE_NAME, "")
    return bool(token) and _verify_token(token)

@router.get("/admin/auth")
def admin_auth(key: str, response: Response):
    if key != settings.admin_secret:
        return HTMLResponse(status_code=404)
    resp = RedirectResponse(url="/admin", status_code=302)
    resp.set_cookie(
        COOKIE_NAME, _make_token(),
        max_age=COOKIE_MAX_AGE, httponly=True, samesite="strict"
    )
    return resp

@router.get("/admin")
def admin_dashboard(request: Request):
    if not _is_authed(request):
        return HTMLResponse(status_code=404)

    return templates.TemplateResponse("admin.html", {
        "request": request,
        "stats": get_stats_today(),
        "sessions": get_recent_sessions(limit=20),
        "top_questions": get_top_questions(days=7, limit=10),
        "referrers": get_referrer_breakdown(days=7),
    })
