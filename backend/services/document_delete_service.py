"""
문서 삭제 서비스 (Plan-67)

Explorer 문서의 생애주기 삭제를 담당한다. 업계 표준(즉시 확인 + 휴지통 보관)을 따른다:
- 파일은 unlink 하지 않고 data/trash/<타임스탬프>/ 로 이동(복구 여지)
- 일반 업로드 문서(.html): 변환물 + 동명 _images/ 형제 폴더 + 검색·벡터 인덱스 제거
- authored 저작 문서(.md): 파일만 이동 (인덱스 미등록이므로 cascade 생략)

업로드(생성)의 대칭쌍. 인덱스 정합은 vector_search.remove_documents 가 보장한다.
"""
import os
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
CONTENTS_ROOT = (PROJECT_ROOT / "contents").resolve()
TRASH_ROOT = PROJECT_ROOT / "data" / "trash"
BACKUPS_ROOT = PROJECT_ROOT / "backups"
SEARCH_INDEX_PATH = PROJECT_ROOT / "data" / "search-index.json"
AUTHORED_PREFIX = "contents/authored/"


def classify_kind(url: str) -> str:
    """url 로 문서 종류 판별 — 'authored' | 'content'."""
    return "authored" if (url or "").startswith(AUTHORED_PREFIX) else "content"


def _resolve_under_contents(url: str) -> Path:
    """url 을 contents/ 하위 절대경로로 안전 변환 (traversal 차단)."""
    url = (url or "").strip().replace("\\", "/")
    if not url.startswith("contents/"):
        raise ValueError(f"Invalid url (contents/ 밖): {url}")
    full = (PROJECT_ROOT / url).resolve()
    if full != CONTENTS_ROOT and not str(full).startswith(str(CONTENTS_ROOT) + os.sep):
        raise ValueError(f"Invalid url (path traversal): {url}")
    return full


def validate_url(url: str) -> None:
    """삭제 가능한 url 인지 사전 검증 (traversal 차단). 실패 시 ValueError.

    다중 삭제에서 일부 url 만 통과해 파일/인덱스가 부분 변경되는 것을 막기 위해
    실제 변경 전에 전수 호출한다 (Plan-67 code-review Critical 3).
    """
    _resolve_under_contents(url)


def files_for_url(url: str) -> list[Path]:
    """url 에 딸린 실제 파일/폴더 목록 (존재하는 것만).

    - content(.html): 변환 HTML + 동명 `<stem>_images/` 형제 폴더
    - authored(.md): 파일 단일
    """
    target = _resolve_under_contents(url)
    out = []
    if target.exists():
        out.append(target)
    if classify_kind(url) == "content":
        images_dir = target.parent / (target.stem + "_images")
        if images_dir.exists() and images_dir.is_dir():
            out.append(images_dir)
    return out


def _load_search_index() -> list:
    if not SEARCH_INDEX_PATH.exists():
        return []
    with open(SEARCH_INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def count_search_sections(url: str) -> int:
    """search-index.json 에서 url 에 해당하는 섹션 수."""
    return sum(1 for d in _load_search_index() if d.get("url") == url)


def remove_from_search_index(url: str) -> int:
    """search-index.json(flat list)에서 url 항목 제거. 제거 섹션 수 반환 + BM25 캐시 무효화."""
    docs = _load_search_index()
    kept = [d for d in docs if d.get("url") != url]
    removed = len(docs) - len(kept)
    if removed:
        tmp = SEARCH_INDEX_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(kept, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(SEARCH_INDEX_PATH)
        try:
            from services.keyword_search import reload_bm25_index
            reload_bm25_index()
        except Exception:
            pass  # 캐시 무효화 실패는 다음 빌드에서 자동 복구
    return removed


def impact_for_url(url: str) -> dict:
    """삭제 전 영향 산출 (미리보기 모달용)."""
    kind = classify_kind(url)
    if kind == "authored":
        return {
            "url": url, "kind": kind,
            "files": len(files_for_url(url)),
            "search_sections": 0, "vector_sections": 0,
        }
    from services.vector_search import count_sections
    return {
        "url": url, "kind": kind,
        "files": len(files_for_url(url)),
        "search_sections": count_search_sections(url),
        "vector_sections": count_sections(url),
    }


def _move_to_trash(paths: list[Path], stamp: str) -> list[str]:
    """주어진 파일/폴더를 data/trash/<stamp>/<원상대경로> 로 이동. 이동된 상대경로 반환."""
    moved = []
    for src in paths:
        rel = src.relative_to(PROJECT_ROOT)
        dest = TRASH_ROOT / stamp / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        moved.append(str(rel).replace("\\", "/"))
    return moved


def delete_document_by_url(url: str) -> dict:
    """단건 문서 삭제 cascade — 파일 휴지통 이동 + (content 면) 인덱스 제거.

    returns: {url, kind, trashed:[...], search_removed:int, vector_removed:int}
    부분 실패 시 예외를 올리되, 파일 이동을 인덱스 제거보다 먼저 수행한다
    (인덱스 잔존은 정합성 재구축으로 회복 가능, 파일 잔존이 더 치명적).
    """
    kind = classify_kind(url)
    paths = files_for_url(url)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")  # 마이크로초 — 같은 초 충돌 방지

    trashed = _move_to_trash(paths, stamp) if paths else []

    search_removed = 0
    vector_removed = 0
    if kind == "content":
        search_removed = remove_from_search_index(url)
        from services.vector_search import remove_documents
        vector_removed = remove_documents(url).get("removed", 0)

    logger.info(
        "문서 삭제: url=%s kind=%s 파일=%d 검색=%d 벡터=%d",
        url, kind, len(trashed), search_removed, vector_removed,
    )
    return {
        "url": url, "kind": kind, "trashed": trashed,
        "search_removed": search_removed, "vector_removed": vector_removed,
    }


# ── Explorer 올클린 초기화 (Plan-68 Phase 4) ──────────────────────────────────
# allowlist 방식: 시스템 baseline 만 남기고 그 외 최상위 콘텐츠(=사용자 업로드/작성)를
# 전부 휴지통 이동. denylist(알려진 것만 삭제)보다 안전 — 미래 업로드도 자동 포함.
# 판별 근거(reports/plan-68-phase4-scope-2026-07-04): home/about=수기 시스템 페이지,
# guide=시스템 가이드, banner_images=화면 데코(translator/author/compare CSS 참조),
# authored=빈 시스템 폴더. 계정(auth.db)·통계(analytics.db)·설정은 무접촉.
_ALLCLEAN_PRESERVE = {"home.html", "about.html", "guide", "banner_images", "authored"}


def all_clean_explorer() -> dict:
    """Explorer 사용자 콘텐츠 올클린 — 보존 목록 외 최상위 항목을 휴지통 이동.

    인덱스·메뉴 갱신은 호출측(엔드포인트)에서 수행(재빌드가 파일시스템 스캔으로 정합).
    returns: {stamp, trashed:[상대경로...], preserved:[...]}
    """
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    targets = []
    for child in sorted(CONTENTS_ROOT.iterdir()):
        if child.name in _ALLCLEAN_PRESERVE or child.name.startswith("."):
            continue
        targets.append(child)

    trashed = _move_to_trash(targets, stamp) if targets else []
    logger.info("Explorer 올클린: %d개 항목 휴지통 이동 (stamp=%s): %s",
                len(trashed), stamp, trashed)
    return {"stamp": stamp, "trashed": trashed, "preserved": sorted(_ALLCLEAN_PRESERVE)}


# ── 보존정책 자동 청소 (Plan-67 후속) ──────────────────────────────────
# 소프트삭제(휴지통)·백업의 업계표준 보존정리. 서버 시작 시 1회 실행(main.py lifespan).
# 대상은 "이미 버린 것/옛 백업"뿐 — 살아있는 문서·인덱스는 건드리지 않는다.

def purge_expired_trash(retention_days: int) -> int:
    """휴지통 <stamp> 폴더 중 이름의 시각이 retention_days 초과한 것 삭제. 삭제 폴더 수 반환."""
    if not TRASH_ROOT.exists():
        return 0
    cutoff = datetime.now() - timedelta(days=retention_days)
    removed = 0
    for d in TRASH_ROOT.iterdir():
        if not d.is_dir():
            continue
        try:
            ts = datetime.strptime(d.name[:15], "%Y%m%d_%H%M%S")  # 규약 폴더만 대상
        except ValueError:
            continue  # 규약(YYYYMMDD_HHMMSS…) 밖 폴더는 건드리지 않음
        if ts < cutoff:
            shutil.rmtree(d, ignore_errors=True)
            removed += 1
    return removed


def purge_old_backups(keep_per_file: int) -> int:
    """backups/*.bak 를 원본(stem)별로 묶어 최신 keep_per_file 개만 남기고 삭제. 삭제 수 반환."""
    if not BACKUPS_ROOT.exists():
        return 0
    import re
    from collections import defaultdict
    groups = defaultdict(list)
    for p in BACKUPS_ROOT.glob("*.bak"):
        key = re.sub(r"_\d{8}_\d{6}.*$", "", p.name)  # 시각 앞부분 = 원본 stem 그룹키
        groups[key].append(p)
    removed = 0
    for files in groups.values():
        files.sort(key=lambda f: f.name, reverse=True)  # 이름=고정폭 시각 → 최신순
        for old in files[keep_per_file:]:
            try:
                old.unlink()
                removed += 1
            except OSError:
                pass
    return removed
