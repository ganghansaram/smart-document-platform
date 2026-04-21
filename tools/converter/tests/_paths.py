# -*- coding: utf-8 -*-
"""
Plan-37 Phase 0 — 경로·fixture 카탈로그 공통 상수

conftest.py 와 standalone 스크립트(regenerate_golden.py 등) 모두
import 할 수 있도록 pytest 의존성 없이 분리.
"""
from pathlib import Path

# ───────────────────────────────────────────────────────────────
# 경로
# ───────────────────────────────────────────────────────────────
TESTS_DIR = Path(__file__).resolve().parent
CONVERTER_DIR = TESTS_DIR.parent
PROJECT_ROOT = CONVERTER_DIR.parent.parent
SAMPLES_DIR = PROJECT_ROOT / "contents" / "samples"
GOLDEN_DIR = TESTS_DIR / "golden"


# ───────────────────────────────────────────────────────────────
# fixture 카탈로그
#
# 각 튜플: (id, docx_path, description)
#   - id: golden HTML 파일명 + 테스트 case ID
#   - docx_path: SAMPLES_DIR 기준 상대 경로
#   - description: 사람이 읽는 설명
# ───────────────────────────────────────────────────────────────
FIXTURE_CATALOG = [
    ("sample_small",  "sample_20260317.docx",
     "(a) 단순 문서, 빠른 smoke test"),
    ("mypaper",       "MyPaper/MyPaper_20251109_V2.8_Claude.docx",
     "(c) 수식 (OMML), 캡션"),
    ("swa_pms",       "SWA_PMS/SWA_PMS.docx",
     "(b) 대형 매뉴얼, heading 자동번호"),
    ("swa_kor",       "SWA_Sample_KOR/SWA_Sample_KOR.docx",
     "(f) 한글 heading 자동번호 재현"),
    # swa_eng 은 3.6MB 로 느려서 기본 테스트에서는 제외. 수동 실행 시만.
    # ("swa_eng",       "SWA_Sample_ENG/SWA_Sample_ENG.docx",
    #  "영문 대형 매뉴얼 (선택)"),
]


# ───────────────────────────────────────────────────────────────
# 알려진 결함 허용 (Known Issues — 자세한 내용은 known_issues.md)
#
# 구조: {fixture_id: {rule_name: reason}}
# 해당 fixture 의 해당 rule error 는 기록만 하고 테스트 실패시키지 않음.
# Phase 1~4 진행 중 결함 해결되면 해당 항목을 제거.
# ───────────────────────────────────────────────────────────────
KNOWN_ISSUES = {
    "mypaper": {
        "caption_id_unique": "KI-001 · 원본 DOCX 저자가 '표 16' 을 두 번 사용",
        # heading_level_skip 은 warning 이라 자동 통과
    },
    "swa_kor": {
        # image_orphan 은 warning 이라 자동 통과. backlog 에 converter 버그 등록 대상.
    },
}


def is_known_issue(fixture_id: str, rule: str) -> str | None:
    """알려진 결함 여부. 해당하면 reason 문자열 반환."""
    return KNOWN_ISSUES.get(fixture_id, {}).get(rule)
