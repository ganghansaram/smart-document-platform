# -*- coding: utf-8 -*-
"""
Plan-37 Phase 0 — pytest 없이 동작하는 standalone 테스트 러너

폐쇄망 환경에서 pytest 미설치 상태에서도 회귀 방어망을 굴릴 수 있도록
세 가지 검증을 순차 실행:
  1. 골든 fingerprint 매치
  2. 현 converter 출력 시맨틱 게이트
  3. 골든 HTML baseline 시맨틱 게이트

사용법:
    python run_tests.py                # 전체
    python run_tests.py sample_small   # 특정 fixture
    python run_tests.py --with-word-com

종료 코드:
    0 = 전체 통과
    1 = 하나 이상 실패
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
import tempfile
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))

from _paths import (  # noqa: E402
    FIXTURE_CATALOG, SAMPLES_DIR, GOLDEN_DIR, CONVERTER_DIR, is_known_issue,
)

if str(CONVERTER_DIR) not in sys.path:
    sys.path.insert(0, str(CONVERTER_DIR))

from semantic_checks import run_all_checks, format_issues, _strip_comments  # noqa: E402


# ───────────────────────────────────────────────────────────────
# Fingerprint (test_conversion.py 와 동일 로직)
# ───────────────────────────────────────────────────────────────

def _normalize(html: str) -> str:
    html = _strip_comments(html)
    html = re.sub(r'\s+', ' ', html)
    return html.strip()


def _fingerprint(html: str) -> dict:
    normalized = _normalize(html)
    combined = re.findall(r'<(/?)([a-zA-Z][a-zA-Z0-9]*)\b', normalized)
    tag_sequence = [(kind or 'o', tag.lower()) for kind, tag in combined]
    text_only = re.sub(r'<[^>]+>', '', normalized)
    text_only = re.sub(r'\s+', ' ', text_only).strip()
    return {
        "tag_count": len(tag_sequence),
        "tag_sequence_hash": hashlib.sha256(
            str(tag_sequence).encode('utf-8')).hexdigest()[:16],
        "text_hash": hashlib.sha256(
            text_only.encode('utf-8')).hexdigest()[:16],
        "text_length": len(text_only),
    }


# ───────────────────────────────────────────────────────────────
# 각 테스트
# ───────────────────────────────────────────────────────────────

def run_converter(docx_path: Path, output_dir: Path, use_word_com: bool) -> Path:
    from converter import DocxConverter
    output_dir.mkdir(parents=True, exist_ok=True)
    output_html = output_dir / (docx_path.stem + ".html")
    preprocessed = None
    try:
        if use_word_com:
            try:
                from word_preprocessor import preprocess_docx
                preprocessed = preprocess_docx(str(docx_path))
            except Exception:
                preprocessed = None
        conv = DocxConverter(config_path=str(CONVERTER_DIR / "config.json"))
        result = conv.convert(preprocessed or str(docx_path), str(output_html))
        if not result.success:
            raise RuntimeError(f"변환 실패: {result.error_message}")
        return output_html
    finally:
        if preprocessed and preprocessed != str(docx_path):
            try:
                Path(preprocessed).unlink(missing_ok=True)
            except OSError:
                pass


def test_fingerprint_match(fid: str, docx: Path, golden: Path, tmp_dir: Path,
                           use_word_com: bool) -> tuple[bool, str]:
    if not golden.exists():
        return (True, "SKIP (no golden)")
    actual_html_path = run_converter(docx, tmp_dir, use_word_com)
    actual_fp = _fingerprint(actual_html_path.read_text(encoding="utf-8"))
    golden_fp = _fingerprint(golden.read_text(encoding="utf-8"))
    diffs = []
    for key in ("tag_count", "tag_sequence_hash", "text_hash", "text_length"):
        if actual_fp[key] != golden_fp[key]:
            diffs.append(f"{key}: actual={actual_fp[key]} golden={golden_fp[key]}")
    if diffs:
        return (False, "MISMATCH: " + "; ".join(diffs))
    return (True, "OK")


def test_semantic(fid: str, html_path: Path, label: str) -> tuple[bool, str, list, list]:
    """시맨틱 게이트 실행. (passed, summary, known_errors, warnings) 반환."""
    issues = run_all_checks(html_path)
    errors = [i for i in issues if i.get("severity") == "error"]
    warnings = [i for i in issues if i.get("severity") == "warning"]

    known = []
    novel = []
    for e in errors:
        reason = is_known_issue(fid, e.get("rule", ""))
        if reason:
            e["_known_reason"] = reason
            known.append(e)
        else:
            novel.append(e)

    if novel:
        return (False,
                f"{label}: 신규 {len(novel)}건 error, 알려진 {len(known)}건, 경고 {len(warnings)}건",
                known, warnings)
    return (True,
            f"{label}: 신규 0건, 알려진 {len(known)}건, 경고 {len(warnings)}건",
            known, warnings)


# ───────────────────────────────────────────────────────────────
# 메인
# ───────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('fixture', nargs='?', default=None,
                    help="특정 fixture id 만 실행 (생략 시 전체)")
    ap.add_argument('--with-word-com', action='store_true')
    ap.add_argument('-v', '--verbose', action='store_true')
    args = ap.parse_args()

    targets = FIXTURE_CATALOG
    if args.fixture:
        targets = [t for t in FIXTURE_CATALOG if t[0] == args.fixture]
        if not targets:
            print(f"Unknown fixture: {args.fixture}")
            return 1

    print(f"Running {len(targets)} fixture(s) (word_com={'ON' if args.with_word_com else 'OFF'})")
    print("=" * 72)

    total_fail = 0
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        for fid, rel_path, desc in targets:
            print(f"\n[{fid}] {desc}")
            docx = SAMPLES_DIR / rel_path
            golden = GOLDEN_DIR / f"{fid}.html"
            case_tmp = tmp_root / fid
            case_tmp.mkdir()

            if not docx.exists():
                print(f"  SKIP: 원본 DOCX 없음 — {docx}")
                continue

            try:
                # 1. fingerprint
                ok1, msg1 = test_fingerprint_match(fid, docx, golden, case_tmp,
                                                   args.with_word_com)
                icon = "[OK]" if ok1 else "[FAIL]"
                print(f"  {icon} fingerprint: {msg1}")
                if not ok1:
                    total_fail += 1

                # 2. 현 converter 출력 시맨틱
                current_html = case_tmp / f"{docx.stem}.html"
                if current_html.exists():
                    ok2, summary2, known2, warns2 = test_semantic(
                        fid, current_html, "current")
                    icon = "[OK]" if ok2 else "[FAIL]"
                    print(f"  {icon} semantic(current): {summary2}")
                    if args.verbose and (known2 or warns2):
                        for k in known2:
                            print(f"      KNOWN {k['rule']}: {k.get('_known_reason', '')}")
                        for w in warns2:
                            print(f"      WARN {w['rule']}: {w['message']}")
                    if not ok2:
                        total_fail += 1

                # 3. golden baseline 시맨틱
                if golden.exists():
                    ok3, summary3, known3, warns3 = test_semantic(
                        fid, golden, "golden ")
                    icon = "[OK]" if ok3 else "[FAIL]"
                    print(f"  {icon} semantic(golden):  {summary3}")
                    if args.verbose and (known3 or warns3):
                        for k in known3:
                            print(f"      KNOWN {k['rule']}: {k.get('_known_reason', '')}")
                        for w in warns3:
                            print(f"      WARN {w['rule']}: {w['message']}")
                    if not ok3:
                        total_fail += 1

            except Exception as e:
                print(f"  [ERROR] {type(e).__name__}: {e}")
                total_fail += 1

    print("\n" + "=" * 72)
    if total_fail == 0:
        print(f"[OK] All checks passed.")
        return 0
    print(f"[FAIL] {total_fail} check(s) failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
