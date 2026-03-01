"""
Analytics API -- heartbeat, page-view, dashboard data
"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from typing import Optional

from dependencies import require_admin
from services.analytics import (
    get_client_ip, record_heartbeat, record_event,
    get_active_user_count, get_active_user_list,
    get_today_visitors, get_week_visitors,
    get_total_visitors, get_daily_visitors, get_top_pages,
    get_top_searches, get_chat_stats, get_daily_chat,
    reset_all, seed_demo_data,
)

router = APIRouter(tags=["analytics"])


class HeartbeatBody(BaseModel):
    username: Optional[str] = None


# -- Public endpoints ----------------------------------------------------------

@router.post("/analytics/heartbeat")
def heartbeat(request: Request, body: HeartbeatBody = None):
    ip = get_client_ip(request)
    username = body.username if body else None
    record_heartbeat(ip, username=username)
    return {"ok": True}


@router.post("/analytics/page-view")
def page_view(request: Request, body: dict):
    ip = get_client_ip(request)
    url = body.get("url", "")
    if url:
        record_event("page_view", ip, {"url": url})
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
    }


@router.delete("/analytics/reset")
def reset(user: dict = Depends(require_admin)):
    reset_all()
    return {"ok": True}


@router.post("/analytics/seed-demo")
def seed_demo(user: dict = Depends(require_admin)):
    count = seed_demo_data(30)
    return {"ok": True, "events_created": count}
