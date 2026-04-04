"""
Phase 3V-c/d: 검증 모드 스코어링 + 규칙 정확도 테스트
- 3종 테스트 문서 (양호/불량/중간)로 점수 분포 + 규칙 정확도 측정
- 실행: cd backend && python -m pytest ../tests/verify/test_scoring.py -v
"""
import sys
from pathlib import Path

# backend를 import path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

from services.compare_service import validate_paragraphs

# ══════════════════════════════════════════
# 테스트 문서 1: 양호한 MIL-STD 스타일 문서
# 기대: 높은 점수 (80+), 이슈 0~1건
# ══════════════════════════════════════════
DOC_GOOD = [
    "1. SCOPE",
    "1.1 Purpose. This specification establishes the electromagnetic interference (EMI) requirements and test procedures for electronic equipment.",
    "1.2 Applicability. This specification applies to all electronic subsystems intended for installation in military aircraft.",
    "2. APPLICABLE DOCUMENTS",
    "2.1 Government documents. The following documents form a part of this specification. MIL-STD-461G applies to all conducted and radiated emission requirements. MIL-STD-464C establishes system-level electromagnetic environmental effects requirements.",
    "3. REQUIREMENTS",
    "3.1 General requirements. The Equipment Under Test (EUT) shall comply with the emission and susceptibility limits defined in Table 1.",
    "3.2 Conducted emissions. The EUT shall not produce conducted emissions exceeding the limits specified in Table 2 over the frequency range of 10 kHz to 10 MHz.",
    "3.3 Radiated emissions. The EUT shall not produce radiated emissions exceeding the limits specified in Table 3 over the frequency range of 10 kHz to 18 GHz.",
    "3.4 Susceptibility. The EUT shall operate without degradation when subjected to the electromagnetic environments defined in Figure 1 and Figure 2.",
    "Table 1. Emission and Susceptibility Test Summary.",
    "Table 2. Conducted Emission Limits (CE102).",
    "Table 3. Radiated Emission Limits (RE102).",
    "Figure 1. Conducted Susceptibility Test Setup.",
    "Figure 2. Radiated Susceptibility Test Setup.",
    "4. VERIFICATION",
    "4.1 Test conditions. All tests shall be performed at ambient temperature between 15°C and 35°C with relative humidity not exceeding 80 percent.",
    "4.2 Test procedures. Test procedures shall follow the detailed methods described in MIL-STD-461G.",
]

# ══════════════════════════════════════════
# 테스트 문서 2: 문제 많은 문서
# 기대: 낮은 점수 (0~30), 다수 이슈
# ══════════════════════════════════════════
DOC_BAD = [
    "1. Introduction",
    "This document is about testing stuff and making sure things work properly and also covers various requirements.",
    "The unit must comply with some standards.",
    "2. Scope",
    "Figure 1 shows the overall test configuration for the radiated emission measurement performed in the shielded room.",
    "3. Requirements",
    "Table 1 contains the test data for the various emission limits across different frequency bands.",
    "The equipment shall be tested under all conditions and it should also be verified for susceptibility and the results must be documented in a comprehensive report that covers all aspects of the electromagnetic compatibility assessment including both conducted and radiated measurements.",
    "Table 3 provides additional measurement data for reference purposes only.",
    "Figure 4 illustrates the block diagram of the test instrumentation chain.",
    "The unit utilizes advanced filtering and the unit also employs shielding techniques.",
    "5. Verification",
]

# ══════════════════════════════════════════
# 테스트 문서 3: 중간 품질 문서
# 기대: 중간 점수 (50~75), 일부 이슈
# ══════════════════════════════════════════
DOC_MEDIUM = [
    "1. SCOPE",
    "1.1 Purpose. This document defines electromagnetic compatibility requirements for airborne systems.",
    "2. APPLICABLE DOCUMENTS",
    "2.1 The following standards apply: MIL-STD-461G and DO-160G.",
    "3. REQUIREMENTS",
    "3.1 The EUT shall comply with conducted emission limits per Table 1.",
    "3.2 Radiated emissions shall not exceed limits in Table 2 from 30 MHz to 18 GHz.",
    "3.3 The test setup is shown in Figure 1.",
    "Figure 3 shows the susceptibility test configuration.",
    "Table 1. Conducted Emission Limits.",
    "Table 2. Radiated Emission Limits.",
    "Figure 1. Test Setup Overview.",
    "4. VERIFICATION",
    "4.1 All tests shall be conducted per MIL-STD-461G procedures at ambient conditions.",
]


def test_good_document_high_score():
    """양호한 문서는 90점 이상이어야 한다"""
    result = validate_paragraphs(DOC_GOOD)
    print(f"\n[양호 문서] score={result['score']}, issues={result['summary']}, words={result['word_count']}")
    for iss in result["issues"]:
        print(f"  - [{iss['severity']}] {iss['rule_id']}: {iss['message']}")
    assert result["score"] >= 90, f"양호 문서 점수가 90 미만: {result['score']}"


def test_bad_document_low_score():
    """불량 문서는 30점 이하여야 한다"""
    result = validate_paragraphs(DOC_BAD)
    print(f"\n[불량 문서] score={result['score']}, issues={result['summary']}, words={result['word_count']}")
    for iss in result["issues"]:
        print(f"  - [{iss['severity']}] {iss['rule_id']}: {iss['message']}")
    assert result["score"] <= 30, f"불량 문서 점수가 30 초과: {result['score']}"


def test_medium_document_mid_score():
    """중간 문서는 40~85점 범위여야 한다"""
    result = validate_paragraphs(DOC_MEDIUM)
    print(f"\n[중간 문서] score={result['score']}, issues={result['summary']}, words={result['word_count']}")
    for iss in result["issues"]:
        print(f"  - [{iss['severity']}] {iss['rule_id']}: {iss['message']}")
    assert 40 <= result["score"] <= 85, f"중간 문서 점수 범위 이탈: {result['score']}"


def test_category_scores_present():
    """응답에 category_scores가 포함되어야 한다"""
    result = validate_paragraphs(DOC_GOOD)
    assert "category_scores" in result
    assert "structure" in result["category_scores"]
    assert "terminology" in result["category_scores"]
    assert "readability" in result["category_scores"]
    for cat, score in result["category_scores"].items():
        assert 0 <= score <= 100, f"카테고리 점수 범위 이탈: {cat}={score}"


def test_word_count_accuracy():
    """word_count가 실제 단어 수와 일치해야 한다"""
    result = validate_paragraphs(DOC_GOOD)
    expected = sum(len(p.split()) for p in DOC_GOOD)
    assert result["word_count"] == expected, f"단어 수 불일치: {result['word_count']} != {expected}"


def test_empty_document():
    """빈 문서는 100점이어야 한다"""
    result = validate_paragraphs([])
    assert result["score"] == 100


def test_structure_analysis():
    """구조 분석이 정확해야 한다"""
    result = validate_paragraphs(DOC_GOOD)
    st = result["structure"]
    # 헤딩 4개 (1. SCOPE, 2. APPLICABLE DOCUMENTS, 3. REQUIREMENTS, 4. VERIFICATION)
    assert len(st["headings"]) >= 4, f"헤딩 감지 부족: {len(st['headings'])}"
    # Table 3개, Figure 2개
    assert len(st["tables"]) >= 2, f"테이블 감지 부족: {len(st['tables'])}"
    assert len(st["figures"]) >= 2, f"그림 감지 부족: {len(st['figures'])}"


def test_requirements_classification():
    """요구사항 분류가 정확해야 한다"""
    result = validate_paragraphs(DOC_GOOD)
    rq = result["requirements"]
    # shall 문장 4개 이상 존재
    assert rq["counts"]["shall"] >= 4, f"shall 감지 부족: {rq['counts']['shall']}"


def test_terms_extraction():
    """용어 추출이 정확해야 한다"""
    result = validate_paragraphs(DOC_GOOD)
    tm = result["terms"]
    spec_ids = [s["id"] for s in tm["specifications"]]
    assert "MIL-STD-461G" in spec_ids, f"MIL-STD-461G 미감지: {spec_ids}"
    # 단위
    unit_names = [u["unit"] for u in tm["units"]]
    assert "kHz" in unit_names or "MHz" in unit_names or "GHz" in unit_names, f"주파수 단위 미감지: {unit_names}"


# ══════════════════════════════════════════
# 규칙별 정확도 측정 (precision/recall)
# ══════════════════════════════════════════

def test_numbering_continuity():
    """번호 연속성: 불연속 감지"""
    # 1, 2, 4 → 3 누락 감지해야 함
    doc = ["1. First", "2. Second", "4. Fourth"]
    result = validate_paragraphs(doc)
    numbering_issues = [i for i in result["issues"] if i["rule_id"] == "numbering_continuity"]
    assert len(numbering_issues) >= 1, "번호 불연속 미감지"


def test_figure_caption_gap():
    """그림 번호 불연속: Figure 1, Figure 3 → Figure 2 누락"""
    doc = ["Figure 1 shows setup.", "Figure 3 shows results."]
    result = validate_paragraphs(doc)
    fig_issues = [i for i in result["issues"] if i["rule_id"] == "figure_caption" and "불연속" in i["message"]]
    assert len(fig_issues) >= 1, "그림 번호 불연속 미감지"


def test_table_unreferenced():
    """표 참조 누락: Table 1이 본문에서 참조되지 않음"""
    doc = ["Some text without reference.", "Table 1. Test Data."]
    result = validate_paragraphs(doc)
    tbl_issues = [i for i in result["issues"] if i["rule_id"] == "table_caption" and "참조" in i["message"]]
    assert len(tbl_issues) >= 1, "표 미참조 미감지"


def test_sentence_length():
    """장문 감지: 30단어 이상 문장"""
    long_sentence = "The equipment under test shall be placed on the ground plane and connected to the power source through the line impedance stabilization network and all cables shall be arranged according to the specified layout in the test plan document."
    doc = [long_sentence]
    result = validate_paragraphs(doc)
    len_issues = [i for i in result["issues"] if i["rule_id"] == "sentence_length"]
    assert len(len_issues) >= 1, "장문 미감지"


def test_no_false_positive_on_clean():
    """양호 문서에서 오탐(false positive)이 최소여야 한다"""
    result = validate_paragraphs(DOC_GOOD)
    # 양호 문서에서 이슈 2건 이하
    total = result["summary"]["error"] + result["summary"]["warning"] + result["summary"]["suggestion"]
    assert total <= 2, f"양호 문서 오탐 과다: {total}건"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
