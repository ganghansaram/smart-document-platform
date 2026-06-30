"""
메뉴 관리 API
GET  /api/menu  — 콘텐츠 메뉴 트리 반환 (admin, 시스템 항목 제외)
POST /api/menu  — 콘텐츠 메뉴 트리 저장 (admin, 시스템 항목 자동 보존)
"""
import json
import threading
from pathlib import Path
from fastapi import APIRouter, Body, Depends

from dependencies import require_admin

router = APIRouter(tags=["menu"])

_MENU_PATH = Path(__file__).parent.parent.parent / "data" / "menu.json"

# menu.json load→save 사이 동시 수정으로 인한 last-writer-wins 손실 방지 (Plan-67)
_MENU_LOCK = threading.Lock()

# 시스템 고정 항목 URL
SYSTEM_URLS = {
    "contents/home.html",
    "glossary:terms",
}

# 시스템 고정 항목 label (URL이 없는 카테고리용)
SYSTEM_LABELS = {
    "플랫폼 가이드",
}


def _is_system(node: dict) -> bool:
    if node.get("url", "") in SYSTEM_URLS:
        return True
    if node.get("label", "") in SYSTEM_LABELS:
        return True
    return False


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
    """시스템 항목을 키(URL 또는 label) → node 맵으로 추출"""
    result = {}
    for node in menu:
        if _is_system(node):
            key = node.get("url") or node.get("label", "")
            result[key] = node
    return result


def _strip_system(menu: list) -> list:
    """시스템 항목을 제거한 콘텐츠 트리 반환"""
    return [node for node in menu if not _is_system(node)]


def _reassemble(content: list, system_items: dict) -> list:
    """홈 → [콘텐츠] → 용어집/정보/대시보드 순으로 재조립"""
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
    for key in ["플랫폼 가이드", "glossary:terms"]:
        item = system_items.get(key)
        if item:
            result.append(item)

    return result


def _iter_nodes(nodes: list):
    """메뉴 트리 전체 노드를 순회 (재귀)."""
    for node in nodes:
        yield node
        if node.get("children"):
            yield from _iter_nodes(node["children"])


def count_url_references(urls: set) -> int:
    """menu.json 에서 주어진 url 들을 참조하는 노드 수 (중복 노드 감지·미리보기용)."""
    return sum(1 for n in _iter_nodes(_load_menu()) if n.get("url") in urls)


def remove_or_detach_urls(urls: set, keep_nodes: bool) -> dict:
    """menu.json 에서 urls 참조 노드 처리 (Plan-67 cascade).

    - keep_nodes=True (detach): 노드는 두고 url 만 분리 → 빈 항목
    - keep_nodes=False (delete): 노드 제거. 단 하위 children 보유 시 폴더로 보존(고아 방지)
    중복 url 노드도 모두 일괄 처리(깨진 링크 0). 시스템 항목은 url 이 매칭되지 않아 무손상.
    returns: {"affected": int}
    """
    affected = [0]

    def walk(nodes: list) -> list:
        result = []
        for node in nodes:
            if node.get("children"):
                node["children"] = walk(node["children"])
            if node.get("url") in urls:
                affected[0] += 1
                if keep_nodes or node.get("children"):
                    node.pop("url", None)
                    result.append(node)
                # children 없는 leaf 는 드롭
            else:
                result.append(node)
        return result

    with _MENU_LOCK:
        menu = walk(_load_menu())
        _save_menu(menu)
    return {"affected": affected[0]}


@router.get("/menu")
def get_menu(user: dict = Depends(require_admin)):
    """콘텐츠 메뉴 트리 반환 (시스템 항목 제외)"""
    menu = _load_menu()
    return {"menu": _strip_system(menu)}


@router.post("/menu")
def post_menu(body: list = Body(...), user: dict = Depends(require_admin)):
    """콘텐츠 메뉴 트리 저장 (시스템 항목 자동 보존)"""
    with _MENU_LOCK:
        current = _load_menu()
        system_items = _extract_system_items(current)
        full_menu = _reassemble(body, system_items)
        _save_menu(full_menu)
    return {"success": True}
