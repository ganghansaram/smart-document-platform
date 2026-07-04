"""
Analytics API -- heartbeat, page-view, dashboard data
"""
import asyncio

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from typing import Optional

from dependencies import require_admin, get_optional_user
from services.analytics import (
    get_client_ip, record_heartbeat, record_event,
    get_active_user_count, get_active_ip_count, get_active_user_list,
    get_today_visitors, get_week_visitors,
    get_total_visitors, get_daily_visitors, get_top_pages,
    get_top_searches, get_chat_stats, get_daily_chat,
    get_feedback_summary, get_recent_negative, get_daily_feedback,
    get_subsystem_stats, get_top_users, get_recent_failures,
    reset_all, seed_demo_data,
)

router = APIRouter(tags=["analytics"])


class HeartbeatBody(BaseModel):
    username: Optional[str] = None
    subsystem: Optional[str] = None


# -- Public endpoints ----------------------------------------------------------

@router.post("/analytics/heartbeat")
def heartbeat(request: Request, body: HeartbeatBody = None):
    ip = get_client_ip(request)
    # username 은 body 우선, 없으면 세션 쿠키에서 폴백 (클라이언트 생략 시에도 집계)
    username = body.username if body and body.username else None
    subsystem = body.subsystem if body else None
    if username is None:
        u = get_optional_user(request)
        username = u["username"] if u else None
    record_heartbeat(ip, username=username, subsystem=subsystem)
    return {"ok": True}


@router.post("/analytics/page-view")
def page_view(request: Request, body: dict):
    ip = get_client_ip(request)
    url = body.get("url", "")
    subsystem = body.get("subsystem") or "explorer"
    if url:
        u = get_optional_user(request)
        record_event("page_view", ip, {"url": url},
                     username=u["username"] if u else None,
                     subsystem=subsystem)
    return {"ok": True}


@router.get("/analytics/active-users")
def active_users():
    # Plan-43: count 의미가 "로그인 사용자 수" 로 전환됨 (username 유니크).
    # ip_count 는 기존 IP 유니크 카운트 (익명 포함) — 확장용.
    return {"count": get_active_user_count(), "ip_count": get_active_ip_count()}


# -- Admin-only endpoints ------------------------------------------------------

@router.get("/analytics/active-user-list")
def active_user_list(user: dict = Depends(require_admin)):
    return {"users": get_active_user_list()}


@router.get("/analytics/dashboard")
async def dashboard(user: dict = Depends(require_admin)):
    # Plan-41: health 는 기존 /api/health 로직 재사용 (중복 구현 회피)
    from main import health_check as _health_check
    try:
        health_resp = await _health_check()
    except Exception:
        health_resp = {"status": "unknown", "checks": {}}

    # Plan-68 C1: 인덱싱 관측은 Ollama /api/ps 동기 호출(최대 3초)을 포함 →
    # 이벤트 루프 블로킹 방지를 위해 스레드로 오프로드 (Ollama 지연 시에도 대시보드 무정지)
    indexing = await asyncio.to_thread(_safe_indexing_status)

    return {
        # 기존 필드 (Plan-43: active_users 의미가 "로그인 사용자 유니크" 로 전환)
        "active_users": get_active_user_count(),
        "active_ips": get_active_ip_count(),
        "today_visitors": get_today_visitors(),
        "week_visitors": get_week_visitors(),
        "total_visitors": get_total_visitors(),
        "daily_visitors": get_daily_visitors(14),
        "top_pages": get_top_pages(10),
        "top_searches": get_top_searches(10),
        "chat_stats": get_chat_stats(),
        "daily_chat": get_daily_chat(14),
        "feedback": {
            "summary": get_feedback_summary(),
            "recent_negative": get_recent_negative(10),
            "daily": get_daily_feedback(14),
        },
        # Plan-41 신규 필드
        "by_subsystem": get_subsystem_stats(14),
        "top_users": get_top_users(days=7, limit=10),
        "recent_failures": get_recent_failures(20),
        "health": health_resp,
        # Plan-44 Phase 5: AI 동시성 상태 (4 지표 + L2/L3 트리거 판정)
        "ai_status": _safe_ai_status(),
        # Plan-68 C1: 인덱싱 백엔드·GPU·마지막 재빌드 관측 (스레드 오프로드 결과)
        "indexing": indexing,
    }


def _safe_ai_status():
    try:
        from services.ai_metrics import get_ai_status
        return get_ai_status()
    except Exception:
        return None


def _safe_indexing_status():
    try:
        from api.upload import get_indexing_status
        return get_indexing_status()
    except Exception:
        return None


@router.delete("/analytics/reset")
def reset(user: dict = Depends(require_admin)):
    reset_all()
    return {"ok": True}


@router.post("/analytics/seed-demo")
def seed_demo(user: dict = Depends(require_admin)):
    count = seed_demo_data(30)
    return {"ok": True, "events_created": count}
