"""
Analytics API -- heartbeat, page-view, dashboard data
"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from typing import Optional

from dependencies import require_admin, get_optional_user
from services.analytics import (
    get_client_ip, record_heartbeat, record_event,
    get_active_user_count, get_active_user_list,
    get_today_visitors, get_week_visitors,
    get_total_visitors, get_daily_visitors, get_top_pages,
    get_top_searches, get_chat_stats, get_daily_chat,
    get_feedback_summary, get_recent_negative, get_daily_feedback,
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
    return {"count": get_active_user_count()}


# -- Admin-only endpoints ------------------------------------------------------

@router.get("/analytics/active-user-list")
def active_user_list(user: dict = Depends(require_admin)):
    return {"users": get_active_user_list()}


@router.get("/analytics/dashboard")
def dashboard(user: dict = Depends(require_admin)):
    return {
        "active_users": get_active_user_count(),
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
    }


@router.delete("/analytics/reset")
def reset(user: dict = Depends(require_admin)):
    reset_all()
    return {"ok": True}


@router.post("/analytics/seed-demo")
def seed_demo(user: dict = Depends(require_admin)):
    count = seed_demo_data(30)
    return {"ok": True, "events_created": count}
