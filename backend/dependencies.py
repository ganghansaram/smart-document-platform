"""
FastAPI 의존성 — 인증 체크
"""
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
