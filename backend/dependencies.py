"""
FastAPI 의존성 — 인증 체크
"""
from typing import Optional
from fastapi import Request, HTTPException
from services.auth import get_session_user

ROLE_LEVELS = {"viewer": 1, "editor": 2, "admin": 3}


def get_current_user(request: Request) -> dict:
    """로그인 여부만 확인 (role 무관)"""
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = get_session_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return user


def get_optional_user(request: Request) -> Optional[dict]:
    """로그인 여부 선택 — 쿠키가 있고 유효하면 user dict, 아니면 None.
    비로그인 허용 엔드포인트에서 analytics 계측용 username 추출에 사용."""
    token = request.cookies.get("session_token")
    if not token:
        return None
    return get_session_user(token)


def require_editor(request: Request) -> dict:
    """editor 이상 권한 필요 (editor, admin)"""
    user = get_current_user(request)
    if ROLE_LEVELS.get(user["role"], 0) < 2:
        raise HTTPException(status_code=403, detail="Editor access required")
    return user


def require_admin(request: Request) -> dict:
    """admin 권한 필요"""
    user = get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
