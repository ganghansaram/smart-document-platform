# -*- coding: utf-8 -*-
"""
Plan-37 §0 시맨틱 품질 게이트

바이트 diff 가 놓치는 실버그를 잡기 위한 **의미 단위 검증**.
각 check 함수는 HTML 문자열 (+ 필요 시 부가 정보) 을 받아 문제 리스트를 반환한다.
빈 리스트 = 통과, 비어있지 않으면 실패.

반환 형식:
    [
        {"severity": "error" | "warning", "rule": "...", "message": "...", "detail": {...}},
        ...
    ]

의존성: Python stdlib 만 (폐쇄망 호환).
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Iterable

# ───────────────────────────────────────────────────────────────
# 정규식 상수
# ───────────────────────────────────────────────────────────────
_ID_ATTR_RE = re.compile(r'\bid="([^"]+)"', re.IGNORECASE)
_HEADING_OPEN_RE = re.compile(r'<(h[1-6])(\s[^>]*)?>', re.IGNORECASE)
_HEADING_BLOCK_RE = re.compile(
    r'<(h[1-6])([^>]*)>(.*?)</\1>', re.IGNORECASE | re.DOTALL
)
_CAPTION_ID_RE = re.compile(
    r'<[^>]*\bid="((?:fig|tbl)-[0-9][0-9a-z\-]*)"', re.IGNORECASE
)
_FIG_REF_RE = re.compile(r'data-fig-ref="([^"]+)"', re.IGNORECASE)
_HREF_HASH_RE = re.compile(r'href="#((?:fig|tbl)-[^"]+)"', re.IGNORECASE)
_IMG_SRC_RE = re.compile(r'<img\b[^>]*\bsrc="([^"]+)"', re.IGNORECASE)
_CAPTION_CLASS_RE = re.compile(
    r'<[^>]*class="[^"]*\bcaption\b[^"]*"[^>]*>(.*?)</[^>]+>',
    re.IGNORECASE | re.DOTALL,
)

# 캡션 ID 패턴: fig-1, fig-1-1, tbl-3-2 등
_CAPTION_ID_PATTERN = re.compile(r'^(fig|tbl)-\d+(-\d+)*$', re.IGNORECASE)

# 미해결 SEQ 플레이스홀더 감지용
_UNRESOLVED_SEQ_RE = re.compile(
    r'(?:Figure|Fig\.?|Table|Tab\.?|그림|표)\s+(?:\?|NaN|None|null|\{[^}]+\})',
    re.IGNORECASE,
)


def _strip_comments(html: str) -> str:
    """HTML 주석 제거 — provenance 주석이 매칭에 잡히는 것 방지."""
    return re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)


# ───────────────────────────────────────────────────────────────
# Check 1: 캡션 무결성
# ───────────────────────────────────────────────────────────────

def check_caption_integrity(html: str) -> list[dict]:
    """
    - 같은 id 중복 없음 (fig-1이 두 번 나오면 FAIL)
    - id 패턴 준수: ^(fig|tbl)-\\d+(-\\d+)*$
    - 모든 [data-fig-ref] / href="#fig-..." 가 실제 id 를 가리킴 (dead link 0건)
    """
    html = _strip_comments(html)
    issues: list[dict] = []

    # 캡션 ID 수집 + 중복 검사
    caption_ids = _CAPTION_ID_RE.findall(html)
    id_counter = Counter(caption_ids)
    for cid, count in id_counter.items():
        if count > 1:
            issues.append({
                "severity": "error",
                "rule": "caption_id_unique",
                "message": f"캡션 id '{cid}' 가 {count}회 중복 등장",
                "detail": {"id": cid, "count": count},
            })

    # 패턴 위반 검사
    for cid in set(caption_ids):
        if not _CAPTION_ID_PATTERN.match(cid):
            issues.append({
                "severity": "error",
                "rule": "caption_id_pattern",
                "message": f"캡션 id '{cid}' 가 패턴 '^(fig|tbl)-N(-N)*$' 위반",
                "detail": {"id": cid},
            })

    # 참조 dead link 검사
    id_set = set(caption_ids)
    for ref_target in _FIG_REF_RE.findall(html):
        if ref_target and ref_target not in id_set:
            issues.append({
                "severity": "error",
                "rule": "caption_ref_dead",
                "message": f"[data-fig-ref='{ref_target}'] 가 존재하지 않는 캡션을 참조",
                "detail": {"ref": ref_target},
            })
    for href_target in _HREF_HASH_RE.findall(html):
        if href_target and href_target not in id_set:
            issues.append({
                "severity": "warning",
                "rule": "caption_href_dead",
                "message": f"href='#{href_target}' 가 존재하지 않는 캡션을 가리킴",
                "detail": {"ref": href_target},
            })

    return issues


# ───────────────────────────────────────────────────────────────
# Check 2: 헤딩 구조
# ───────────────────────────────────────────────────────────────

def check_heading_structure(html: str, expected_count: int | None = None) -> list[dict]:
    """
    - heading 개수가 기대치(expected_count)와 일치 (None 이면 스킵)
    - h 레벨이 건너뛰지 않음 (h2 다음 h4 직접 등장 시 경고)
    - heading id 중복 없음 (동일 id 가진 heading 여러 개 금지)
    """
    html = _strip_comments(html)
    issues: list[dict] = []

    headings: list[tuple[str, str]] = []  # (tag, attrs)
    for m in _HEADING_BLOCK_RE.finditer(html):
        tag = m.group(1).lower()
        attrs = m.group(2) or ""
        headings.append((tag, attrs))

    # 개수 비교
    if expected_count is not None and len(headings) != expected_count:
        issues.append({
            "severity": "error",
            "rule": "heading_count",
            "message": f"헤딩 개수 불일치: 실제 {len(headings)}, 기대 {expected_count}",
            "detail": {"actual": len(headings), "expected": expected_count},
        })

    # 레벨 건너뜀 (한 단계씩 내려가야 함)
    prev_level = 0
    for idx, (tag, _attrs) in enumerate(headings):
        level = int(tag[1])
        if prev_level and level > prev_level + 1:
            issues.append({
                "severity": "warning",
                "rule": "heading_level_skip",
                "message": f"헤딩 레벨 건너뜀: h{prev_level} → {tag} (idx={idx})",
                "detail": {"index": idx, "from": prev_level, "to": level},
            })
        prev_level = level

    # heading id 중복 검사 (heading 자체가 id 를 가진 경우만 — 현재 converter 는 캡션만 id 부여)
    heading_ids: list[str] = []
    for _tag, attrs in headings:
        m = _ID_ATTR_RE.search(attrs)
        if m:
            heading_ids.append(m.group(1))

    heading_id_counter = Counter(heading_ids)
    for hid, count in heading_id_counter.items():
        if count > 1:
            issues.append({
                "severity": "error",
                "rule": "heading_id_unique",
                "message": f"heading id '{hid}' 가 {count}회 중복",
                "detail": {"id": hid, "count": count},
            })

    return issues


# ───────────────────────────────────────────────────────────────
# Check 3: 이미지 무결성
# ───────────────────────────────────────────────────────────────

def check_image_integrity(html: str, html_path: Path) -> list[dict]:
    """
    - 모든 <img src> 경로가 실제 파일로 존재 (상대 경로 기준)
    - 이미지 디렉토리 내 모든 파일이 HTML 에서 참조됨 (고아 파일 0건)
    """
    html = _strip_comments(html)
    issues: list[dict] = []
    base_dir = html_path.parent

    # HTML 에서 참조된 이미지 수집
    referenced = []
    for src in _IMG_SRC_RE.findall(html):
        # 외부 URL / data URI 스킵
        if src.startswith(("http://", "https://", "data:", "//")):
            continue
        referenced.append(src)

    for src in referenced:
        img_path = (base_dir / src).resolve()
        if not img_path.exists():
            issues.append({
                "severity": "error",
                "rule": "image_missing",
                "message": f"참조된 이미지 파일 없음: {src}",
                "detail": {"src": src, "resolved": str(img_path)},
            })

    # 이미지 폴더 고아 파일 검사
    # 관례: {html_stem}_images/ 폴더
    images_dir = base_dir / f"{html_path.stem}_images"
    if images_dir.exists() and images_dir.is_dir():
        referenced_basenames = {Path(s).name for s in referenced}
        orphan_files = []
        for img_file in images_dir.iterdir():
            if img_file.is_file() and img_file.name not in referenced_basenames:
                orphan_files.append(img_file.name)
        if orphan_files:
            issues.append({
                "severity": "warning",
                "rule": "image_orphan",
                "message": f"참조되지 않는 이미지 파일 {len(orphan_files)}건 (고아)",
                "detail": {"dir": str(images_dir), "orphans": orphan_files[:10]},
            })

    return issues


# ───────────────────────────────────────────────────────────────
# Check 4: SEQ 필드 해결
# ───────────────────────────────────────────────────────────────

def check_seq_resolution(html: str) -> list[dict]:
    """
    - 캡션 텍스트에 미해결 플레이스홀더 없음 ("그림 ?", "Figure NaN", "{...}" 등)
    """
    html = _strip_comments(html)
    issues: list[dict] = []

    # 캡션 블록 안에서 미해결 패턴 검색
    for m in _CAPTION_CLASS_RE.finditer(html):
        caption_text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        if _UNRESOLVED_SEQ_RE.search(caption_text):
            issues.append({
                "severity": "error",
                "rule": "seq_unresolved",
                "message": f"캡션에 미해결 SEQ 플레이스홀더: '{caption_text[:80]}'",
                "detail": {"text": caption_text[:200]},
            })

    return issues


# ───────────────────────────────────────────────────────────────
# 통합 실행기
# ───────────────────────────────────────────────────────────────

def run_all_checks(html_path: Path) -> list[dict]:
    """모든 check 를 실행하고 문제 리스트 반환.

    Args:
        html_path: 검사 대상 HTML 파일 경로.

    Returns:
        issues: 발견된 모든 문제 (severity + rule + message + detail).
    """
    html = html_path.read_text(encoding="utf-8")
    issues: list[dict] = []
    issues.extend(check_caption_integrity(html))
    issues.extend(check_heading_structure(html))
    issues.extend(check_image_integrity(html, html_path))
    issues.extend(check_seq_resolution(html))
    return issues


def format_issues(issues: Iterable[dict]) -> str:
    """진단 출력용 텍스트 포맷."""
    lines = []
    for i, issue in enumerate(issues, 1):
        sev = issue.get("severity", "?")
        rule = issue.get("rule", "?")
        msg = issue.get("message", "?")
        lines.append(f"  [{i}] [{sev.upper()}] {rule}: {msg}")
    return "\n".join(lines) if lines else "  (문제 없음)"


if __name__ == "__main__":
    # 단독 실행: python semantic_checks.py <html_path>
    import sys
    if len(sys.argv) < 2:
        print("사용법: python semantic_checks.py <html_path>")
        sys.exit(1)
    target = Path(sys.argv[1]).resolve()
    print(f"검사 대상: {target}")
    found = run_all_checks(target)
    print(format_issues(found))
    sys.exit(1 if any(i.get("severity") == "error" for i in found) else 0)
