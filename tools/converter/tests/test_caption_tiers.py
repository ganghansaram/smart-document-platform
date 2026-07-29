# -*- coding: utf-8 -*-
"""
Plan-73 — 캡션 2계층(참조/표시) 경계 회귀 테스트

run_tests.py 의 fingerprint 는 태그 이름만 해싱하므로 class·id 변화를
잡지 못한다. 캡션 계층은 전적으로 속성으로 표현되므로 여기서 따로 지킨다.

지키는 것:
  1. 표기별 판정 — 참조 캡션은 class+id, 표시 캡션은 class 만, 나머지는 무속성
  2. 프론트 폴백(js/app.js)과의 기준 동치 — 한쪽만 바뀌면 Explorer(엔진∪JS)와
     웹북(엔진 단독)의 화면이 어긋난다

pytest 없이도 돌아간다:
    python test_caption_tiers.py
    pytest test_caption_tiers.py -v
"""
from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))

from _paths import CONVERTER_DIR, PROJECT_ROOT  # noqa: E402

if str(CONVERTER_DIR) not in sys.path:
    sys.path.insert(0, str(CONVERTER_DIR))

FIXTURE_DOCX = THIS_DIR / "fixtures" / "caption_variants.docx"
APP_JS = PROJECT_ROOT / "js" / "app.js"

# (문단 텍스트 앞부분, class 기대, id 기대)
#   "ref"     참조 캡션 — class + id
#   "display" 표시 캡션 — class 만
#   None      캡션 아님
CASES = [
    ("표 1. 시스템 구성",              "ref"),
    ("표 2: 주요 제원",                "ref"),
    ("그림 3-1. 흐름도",               "ref"),
    ("Table 4. Overview",              "ref"),
    ("Tab. 5: Legacy abbreviation",    "ref"),
    ("표 6 시스템 구성",               "display"),
    ("표7 붙여쓴 표기",                "display"),
    ("Table 8 Overview",               "display"),
    ("그림 9 흐름도",                  "display"),
    ("Fig. 10 Diagram",                "display"),

    # 조사가 붙으면 본문 — 짧아도 캡션이 아니다
    ("표 11을 보면",                    None),
    ("표 12는 주요 제원을",             None),
    ("그림 13과 같이",                  None),
    ("그림 14의 흐름을",                None),
    ("Table 15를 참조한다",             None),

    ("그림 16 또한 중요하다",           None),      # 150자 초과
    ("본 절에서는 시스템 구성을 설명한다.", None),
    ("표 없이 시작하는 문장",           None),
]


def _ensure_fixture() -> Path:
    if not FIXTURE_DOCX.exists():
        sys.path.insert(0, str(THIS_DIR / "fixtures"))
        from make_caption_fixture import build
        build(FIXTURE_DOCX)
    return FIXTURE_DOCX


def _convert() -> str:
    from converter import DocxConverter
    docx = _ensure_fixture()
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "caption_variants.html"
        conv = DocxConverter(config_path=str(CONVERTER_DIR / "config.json"))
        result = conv.convert(str(docx), str(out))
        if not result.success:
            raise RuntimeError(f"변환 실패: {result.error_message}")
        return out.read_text(encoding="utf-8")


def _find_block(html: str, text_prefix: str) -> str | None:
    """텍스트로 시작하는 블록 요소의 여는 태그를 반환."""
    for m in re.finditer(r'<(p|h[1-6])\b([^>]*)>(.*?)</\1>', html, re.DOTALL):
        inner = re.sub(r'<[^>]+>', '', m.group(3)).strip()
        if inner.startswith(text_prefix):
            return m.group(2)
    return None


def check_tiers() -> list[str]:
    """표기별 판정 검증. 실패 메시지 목록 반환(빈 리스트 = 통과)."""
    html = _convert()
    failures = []

    for text_prefix, expected in CASES:
        attrs = _find_block(html, text_prefix)
        if attrs is None:
            failures.append(f"문단을 찾지 못함: {text_prefix!r}")
            continue

        has_class = 'class="caption"' in attrs
        has_id = bool(re.search(r'\bid="(fig|tbl)-', attrs))

        if expected == "ref":
            if not has_class:
                failures.append(f"참조 캡션인데 class 없음: {text_prefix!r}")
            if not has_id:
                failures.append(f"참조 캡션인데 id 없음: {text_prefix!r}")
        elif expected == "display":
            if not has_class:
                failures.append(f"표시 캡션인데 class 없음: {text_prefix!r}")
            if has_id:
                failures.append(
                    f"표시 캡션에 id 가 붙음 — 중복 id·오탐 링크 위험: {text_prefix!r}")
        else:
            if has_class:
                failures.append(f"캡션이 아닌데 class 붙음: {text_prefix!r}")
            if has_id:
                failures.append(f"캡션이 아닌데 id 붙음: {text_prefix!r}")

    return failures


def _normalize_js_regex(body: str) -> str:
    """JS 정규식의 캡처 그룹을 논캡처로 정규화 — Python 패턴과 비교 가능하게."""
    return re.sub(r'\((?!\?)', '(?:', body)


def check_js_parity() -> list[str]:
    """표시 캡션 기준이 프론트 폴백(js/app.js)과 동치인지 확인."""
    from converter import (
        DISPLAY_CAPTION_RE, DISPLAY_CAPTION_MAX_LEN, DISPLAY_CAPTION_PARTICLE_RE)

    if not APP_JS.exists():
        return [f"js/app.js 를 찾지 못함 — 동치 검증 생략 불가: {APP_JS}"]

    src = APP_JS.read_text(encoding="utf-8")
    failures = []

    for js_var, py_re, label in (
        ('captionPattern', DISPLAY_CAPTION_RE, '표시 캡션'),
        ('captionParticle', DISPLAY_CAPTION_PARTICLE_RE, '조사 배제'),
    ):
        m = re.search(rf'{js_var}\s*=\s*/\^(.+?)/i', src)
        if not m:
            failures.append(f"js/app.js 에서 {js_var} 를 찾지 못함")
            continue
        js_body = _normalize_js_regex(m.group(1))
        py_body = py_re.pattern.lstrip('^')
        if js_body != py_body:
            failures.append(
                f"{label} 정규식 불일치 — js={js_body!r} py={py_body!r}")

    m = re.search(r'text\.length\s*<\s*(\d+)', src)
    if not m:
        failures.append("js/app.js 에서 길이 가드를 찾지 못함")
    elif int(m.group(1)) != DISPLAY_CAPTION_MAX_LEN:
        failures.append(
            f"길이 가드 불일치 — js={m.group(1)} py={DISPLAY_CAPTION_MAX_LEN}")

    # 조사 배제가 JS 판정에도 실제로 걸려 있는지 (선언만 하고 안 쓰는 경우 방지)
    if not re.search(r'!\s*captionParticle\.test\(', src):
        failures.append("js/app.js 판정문에서 captionParticle 이 사용되지 않음")

    return failures


# ── pytest 진입점 ──

def test_caption_tiers():
    failures = check_tiers()
    assert not failures, "\n".join(failures)


def test_js_parity():
    failures = check_js_parity()
    assert not failures, "\n".join(failures)


# ── standalone 진입점 ──

def main() -> int:
    total = 0
    for label, fn in (("계층 판정", check_tiers), ("JS 동치", check_js_parity)):
        failures = fn()
        if failures:
            print(f"  [FAIL] {label}: {len(failures)}건")
            for f in failures:
                print(f"      - {f}")
            total += len(failures)
        else:
            print(f"  [OK] {label}")
    return 1 if total else 0


if __name__ == "__main__":
    print("[caption_tiers] Plan-73 캡션 2계층 경계")
    sys.exit(main())
