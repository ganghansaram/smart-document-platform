# -*- coding: utf-8 -*-
"""
Plan-37 Phase 0 — 회귀 테스트

각 fixture 에 대해:
    1. 현재 converter 로 변환
    2. 골든 HTML 과 fingerprint 비교 (DOM 구조 + 정규화 텍스트 hash)
    3. 시맨틱 품질 게이트 실행 → error severity 0건이어야 통과

시맨틱 게이트 결과는 warning 이어도 출력은 되지만 실패시키지는 않는다.
error severity 만 실패 처리.

실행:
    pytest tools/converter/tests/ -v
    pytest tools/converter/tests/test_conversion.py::test_golden_match -v
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from conftest import GOLDEN_DIR, run_current_converter  # noqa: E402
from _paths import is_known_issue  # noqa: E402
from semantic_checks import (  # noqa: E402
    run_all_checks, format_issues, _strip_comments,
)


def _filter_known(fixture_id: str, issues: list) -> tuple[list, list]:
    """알려진 결함과 신규 결함 분리."""
    known = []
    novel = []
    for issue in issues:
        reason = is_known_issue(fixture_id, issue.get("rule", ""))
        if reason:
            issue["_known_reason"] = reason
            known.append(issue)
        else:
            novel.append(issue)
    return known, novel


# ───────────────────────────────────────────────────────────────
# Fingerprint: DOM 구조 + 텍스트 hash
# ───────────────────────────────────────────────────────────────

_TAG_OPEN_RE = re.compile(r'<([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>')
_TAG_CLOSE_RE = re.compile(r'</([a-zA-Z][a-zA-Z0-9]*)>')


def _normalize(html: str) -> str:
    """비교를 위한 정규화:
    - HTML 주석 제거 (provenance 변동 흡수)
    - 연속 공백 → 단일 공백
    - 앞뒤 공백 제거
    """
    html = _strip_comments(html)
    html = re.sub(r'\s+', ' ', html)
    return html.strip()


def _fingerprint(html: str) -> dict:
    """DOM 구조 + 정규화 본문 hash 반환."""
    normalized = _normalize(html)

    # 태그 시퀀스 — 구조적 차이 감지
    tag_sequence = []
    tag_sequence.extend(('o', t) for t in _TAG_OPEN_RE.findall(normalized))
    # 닫는 태그까지 섞어서 순서 유지
    combined = re.findall(r'<(/?)([a-zA-Z][a-zA-Z0-9]*)\b', normalized)
    tag_sequence = [(kind or 'o', tag.lower()) for kind, tag in combined]

    # 텍스트만 추출 (태그 제거)
    text_only = re.sub(r'<[^>]+>', '', normalized)
    text_only = re.sub(r'\s+', ' ', text_only).strip()

    return {
        "tag_count": len(tag_sequence),
        "tag_sequence_hash": hashlib.sha256(
            str(tag_sequence).encode('utf-8')).hexdigest()[:16],
        "text_hash": hashlib.sha256(
            text_only.encode('utf-8')).hexdigest()[:16],
        "text_length": len(text_only),
        "normalized_length": len(normalized),
    }


# ───────────────────────────────────────────────────────────────
# Tests
# ───────────────────────────────────────────────────────────────

def test_golden_match(fixture_case, tmp_path):
    """현재 converter 출력이 골든과 fingerprint 동등한지 검증."""
    if not fixture_case["golden"].exists():
        pytest.skip(
            f"골든 HTML 없음: {fixture_case['golden']}. "
            f"먼저 `python regenerate_golden.py` 실행하세요."
        )

    # 1. 현재 converter 로 변환
    actual_html_path = run_current_converter(fixture_case["docx"], tmp_path)
    actual_html = actual_html_path.read_text(encoding="utf-8")
    golden_html = fixture_case["golden"].read_text(encoding="utf-8")

    # 2. fingerprint 비교
    actual_fp = _fingerprint(actual_html)
    golden_fp = _fingerprint(golden_html)

    diffs = []
    for key in ("tag_count", "tag_sequence_hash", "text_hash", "text_length"):
        if actual_fp[key] != golden_fp[key]:
            diffs.append(f"  {key}: actual={actual_fp[key]}, golden={golden_fp[key]}")

    if diffs:
        pytest.fail(
            f"Fingerprint mismatch for {fixture_case['id']}:\n"
            + "\n".join(diffs)
            + f"\n  actual HTML: {actual_html_path}"
            + f"\n  golden HTML: {fixture_case['golden']}"
        )


def test_semantic_gates(fixture_case, tmp_path):
    """현재 converter 출력이 시맨틱 게이트를 통과하는지 검증.

    known_issues 에 등록된 결함은 통과 허용, 신규 error 는 실패.
    warning 은 출력만.
    """
    actual_html_path = run_current_converter(fixture_case["docx"], tmp_path)
    issues = run_all_checks(actual_html_path)

    errors = [i for i in issues if i.get("severity") == "error"]
    warnings = [i for i in issues if i.get("severity") == "warning"]

    known_err, novel_err = _filter_known(fixture_case["id"], errors)

    if warnings:
        print(f"\n[{fixture_case['id']}] 시맨틱 경고 {len(warnings)}건:")
        print(format_issues(warnings))

    if known_err:
        print(f"\n[{fixture_case['id']}] 알려진 결함 {len(known_err)}건 (허용):")
        for i in known_err:
            print(f"  - {i.get('rule')}: {i.get('_known_reason', '')}")

    if novel_err:
        pytest.fail(
            f"[{fixture_case['id']}] 신규 시맨틱 오류 {len(novel_err)}건:\n"
            + format_issues(novel_err)
        )


def test_golden_semantic_baseline(fixture_case):
    """골든 HTML 자체가 시맨틱 게이트를 통과하는지 확인 (sanity check).

    known_issues 는 허용, 신규 error 만 실패.
    """
    if not fixture_case["golden"].exists():
        pytest.skip(f"골든 HTML 없음: {fixture_case['golden']}")

    issues = run_all_checks(fixture_case["golden"])
    errors = [i for i in issues if i.get("severity") == "error"]
    warnings = [i for i in issues if i.get("severity") == "warning"]

    known_err, novel_err = _filter_known(fixture_case["id"], errors)

    if warnings:
        print(f"\n[{fixture_case['id']} golden] 경고 {len(warnings)}건:")
        print(format_issues(warnings))

    if known_err:
        print(f"\n[{fixture_case['id']} golden] 알려진 결함 {len(known_err)}건:")
        for i in known_err:
            print(f"  - {i.get('rule')}: {i.get('_known_reason', '')}")

    if novel_err:
        pytest.fail(
            f"[{fixture_case['id']} golden] 골든에 신규 시맨틱 오류 {len(novel_err)}건:\n"
            + format_issues(novel_err)
        )
