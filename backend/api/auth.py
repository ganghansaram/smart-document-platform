"""
인증 API — 로그인/로그아웃/사용자 관리
"""
from fastapi import APIRouter, HTTPException, Request, Response, Depends
from pydantic import BaseModel
from typing import Optional

from services.auth import (
    authenticate, create_session, delete_session, get_session_user,
    create_user, list_users, update_user, delete_user,
)
from dependencies import require_admin
import config

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreateRequest(BaseModel):
    username: str
    password: str
    role: str = "admin"


class UserUpdateRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None


# ── 공개 엔드포인트 ──────────────────────────────────────

@router.post("/auth/login")
def login(body: LoginRequest, response: Response):
    user = authenticate(body.username, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_session(user["id"])
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=config.SESSION_EXPIRY_HOURS * 3600,
        secure=False,
    )
    return {"success": True, "user": user}


@router.post("/auth/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token:
        delete_session(token)
    response.delete_cookie("session_token")
    return {"success": True}


@router.get("/auth/me")
def me(request: Request):
    token = request.cookies.get("session_token")
    if not token:
        return {"user": None}
    user = get_session_user(token)
    return {"user": user}


# ── 관리자 전용 ──────────────────────────────────────────

@router.get("/auth/users")
def get_users(user: dict = Depends(require_admin)):
    return {"users": list_users()}


@router.post("/auth/users")
def add_user(body: UserCreateRequest, user: dict = Depends(require_admin)):
    try:
        new_user = create_user(body.username, body.password, body.role)
        return {"success": True, "user": new_user}
    except Exception as e:
        if "UNIQUE" in str(e):
            raise HTTPException(status_code=409, detail="Username already exists")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/auth/users/{user_id}")
def edit_user(user_id: int, body: UserUpdateRequest, user: dict = Depends(require_admin)):
    updated = update_user(user_id, body.username, body.password, body.role)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True, "user": updated}


@router.delete("/auth/users/{user_id}")
def remove_user(user_id: int, user: dict = Depends(require_admin)):
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    if not delete_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True}
