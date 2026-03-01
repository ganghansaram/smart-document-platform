"""
메뉴 관리 API
GET  /api/menu  — 콘텐츠 메뉴 트리 반환 (admin, 시스템 항목 제외)
POST /api/menu  — 콘텐츠 메뉴 트리 저장 (admin, 시스템 항목 자동 보존)
"""
import json
from pathlib import Path
from fastapi import APIRouter, Body, Depends

from dependencies import require_admin

router = APIRouter(tags=["menu"])

_MENU_PATH = Path(__file__).parent.parent.parent / "data" / "menu.json"

# 시스템 고정 항목 URL
SYSTEM_URLS = {
    "contents/home.html",
    "glossary:terms",
    "contents/about.html",
    "analytics:dashboard",
    "settings:admin",
}


def _is_system(node: dict) -> bool:
    return node.get("url", "") in SYSTEM_URLS


def _load_menu() -> list:
    if not _MENU_PATH.exists():
        return []
    with open(_MENU_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_menu(data: list) -> None:
    """원자적 저장: tmp → rename"""
    tmp = _MENU_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(_MENU_PATH)


def _extract_system_items(menu: list) -> dict:
    """시스템 항목을 URL → node 맵으로 추출"""
    result = {}
    for node in menu:
        if _is_system(node):
            result[node["url"]] = node
    return result


def _strip_system(menu: list) -> list:
    """시스템 항목을 제거한 콘텐츠 트리 반환"""
    return [node for node in menu if not _is_system(node)]


def _reassemble(content: list, system_items: dict) -> list:
    """홈 → [콘텐츠] → 용어집/정보/대시보드/관리자설정 순으로 재조립"""
    result = []

    # 홈 (맨 앞)
    home = system_items.get("contents/home.html")
    if home:
        result.append(home)

    # 콘텐츠 (시스템 항목이 혼입되어 있으면 제거)
    for node in content:
        if not _is_system(node):
            result.append(node)

    # 후미 시스템 항목 (순서 고정)
    for url in ["glossary:terms", "contents/about.html", "analytics:dashboard", "settings:admin"]:
        item = system_items.get(url)
        if item:
            result.append(item)

    return result


@router.get("/menu")
def get_menu(user: dict = Depends(require_admin)):
    """콘텐츠 메뉴 트리 반환 (시스템 항목 제외)"""
    menu = _load_menu()
    return {"menu": _strip_system(menu)}


@router.post("/menu")
def post_menu(body: list = Body(...), user: dict = Depends(require_admin)):
    """콘텐츠 메뉴 트리 저장 (시스템 항목 자동 보존)"""
    current = _load_menu()
    system_items = _extract_system_items(current)
    full_menu = _reassemble(body, system_items)
    _save_menu(full_menu)
    return {"success": True}
