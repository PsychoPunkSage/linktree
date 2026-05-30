from fastapi import APIRouter
from services.github import get_cached_summary

router = APIRouter()

@router.get("/api/github")
def github_summary():
    return {"summary": get_cached_summary()}
