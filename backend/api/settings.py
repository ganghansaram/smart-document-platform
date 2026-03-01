"""
관리자 설정 API
GET  /api/settings         — 현재 설정 반환 (admin)
POST /api/settings         — 설정 저장 (admin)
POST /api/settings/reset   — 기본값 초기화 (admin)
GET  /api/settings/public  — 프론트엔드 공개 설정 (인증 불필요)
"""
from fastapi import APIRouter, Depends

from dependencies import require_admin
from services.settings_service import (
    load_settings, save_settings, reset_settings,
    get_public_settings, apply_to_config, DEFAULT_SETTINGS,
)

router = APIRouter(tags=["settings"])


@router.get("/settings/public")
def settings_public():
    """프론트엔드 시작 시 공개 설정 fetch (인증 불필요)."""
    return {"frontend": get_public_settings()}


@router.get("/settings")
def get_settings(user: dict = Depends(require_admin)):
    """현재 적용 중인 설정 전체 반환."""
    return {"settings": load_settings(), "defaults": DEFAULT_SETTINGS}


@router.post("/settings")
def post_settings(body: dict, user: dict = Depends(require_admin)):
    """설정 저장 + 런타임 즉시 반영. 재시작 필요 항목 목록 반환."""
    save_settings(body)
    restart_needed = apply_to_config(body)
    return {
        "success": True,
        "restart_needed": restart_needed,
    }


@router.post("/settings/reset")
def post_reset(user: dict = Depends(require_admin)):
    """기본값으로 초기화."""
    defaults = reset_settings()
    apply_to_config(defaults)
    return {"success": True, "settings": defaults}
