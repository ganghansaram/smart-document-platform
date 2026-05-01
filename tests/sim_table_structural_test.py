"""Plan-52 — 테이블 구조 행 검출 + 점수 영향 검증.

backend/services/similarity_engine.py 의 신규 함수
(_is_table_row, _is_short_cell_row, _detect_table_structural) +
_detect_exclusions 통합 + _compute_summary 분자 영향을 검증한다.

실행: python tests/sim_table_structural_test.py
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from services.similarity_engine import (  # noqa: E402
    _is_table_row,
    _is_short_cell_row,
    _detect_table_structural,
    _detect_exclusions,
    _compute_summary,
    _sentence_split,
    _parse_table_cells,
    _build_tagged_html,
    _TOC_HEADING_RE,
    _REFERENCES_HEADER_RE,
    _CAPTION_RE,
    TYPE_PARAPHRASE,
    TYPE_IDENTICAL,
)


def _make_match(idx: int, mtype: str, sim: float = 0.85) -> dict:
    return {
        "target_idx": idx,
        "ref_idx": idx,
        "target_text": f"text_{idx}",
        "ref_text": f"ref_{idx}",
        "type": mtype,
        "similarity": sim,
        "scores": {"fingerprint": 0.5, "semantic": 0.8},
    }


CASES = []


# ─────────────────────────────────────────────────────────────
# Case A — _is_table_row 기본 동작
# ─────────────────────────────────────────────────────────────
def case_is_table_row():
    assert _is_table_row("| 항목 | 값 |") is True, "GFM 테이블 행 감지 실패"
    assert _is_table_row("| 한 셀만 |") is False, "셀 1개는 테이블 아님"
    assert _is_table_row("일반 문장") is False, "비테이블 문장 오감지"
    assert _is_table_row("") is False, "빈 문자열 오감지"


CASES.append(("A. _is_table_row 기본 동작", case_is_table_row))


# ─────────────────────────────────────────────────────────────
# Case B — _is_short_cell_row: 모든 셀 ≤ 3 단어 (구조성)
# ─────────────────────────────────────────────────────────────
def case_short_cell_row_detection():
    assert _is_short_cell_row("| 이름 | 직책 | 부서 |") is True
    assert _is_short_cell_row("| 1 | 2 | 3 | 4 |") is True
    # 한 셀이 4단어 이상이면 비구조성
    long_row = "| 짧은 셀 | 긴 셀 데이터 분석 결과 텍스트 입니다 |"
    assert _is_short_cell_row(long_row) is False, "긴 셀 포함인데 구조성으로 판정"


CASES.append(("B. _is_short_cell_row 구조성 판정", case_short_cell_row_detection))


# ─────────────────────────────────────────────────────────────
# Case C — _detect_table_structural: 첫 행 = 헤더 (구조성)
# 첫 행에 긴 셀이 있어도 헤더로 간주됨
# ─────────────────────────────────────────────────────────────
def case_first_row_is_structural():
    sentences = [
        "일반 문장입니다.",
        "| 데이터 분석 결과 컬럼 | 매우 긴 설명 텍스트 컬럼 |",  # 첫 행 (헤더)
        "| 값1 | 매우 길고 의미 있는 데이터 본문 텍스트 |",  # 데이터 행 (긴 셀이라 비구조성)
    ]
    structural = _detect_table_structural(sentences)
    assert 1 in structural, "첫 행이 헤더로 감지되지 않음"
    assert 2 not in structural, "긴 셀 데이터 행이 구조성으로 잘못 판정됨"


CASES.append(("C. 첫 행 헤더 + 긴 셀 데이터 행 구분", case_first_row_is_structural))


# ─────────────────────────────────────────────────────────────
# Case D — _detect_table_structural: 짧은 셀 데이터 행도 구조성
# ─────────────────────────────────────────────────────────────
def case_short_data_rows_also_structural():
    sentences = [
        "| 이름 | 직책 |",      # 첫 행
        "| 홍길동 | 부장 |",    # 짧은 셀 데이터 (구조성)
        "| 김철수 | 과장 |",    # 짧은 셀 데이터 (구조성)
    ]
    structural = _detect_table_structural(sentences)
    assert 0 in structural and 1 in structural and 2 in structural, \
        f"짧은 셀 행 모두 구조성이어야 함 (실제: {structural})"


CASES.append(("D. 짧은 셀 데이터 행도 구조성", case_short_data_rows_also_structural))


# ─────────────────────────────────────────────────────────────
# Case E — _detect_exclusions 통합: table_structural 사유 부여
# ─────────────────────────────────────────────────────────────
def case_detect_exclusions_integration():
    sentences = [
        "이것은 일반 문장입니다 데이터 처리 시스템에 대한 설명.",
        "| 항목 | 값 | 비고 |",  # 헤더
        "| 처리량 | 1000 | TPS |",  # 짧은 셀 (구조성)
    ]
    exclusions = _detect_exclusions(sentences)
    assert exclusions.get(1) == "table_structural", \
        f"헤더 행에 table_structural 미부여 (실제: {exclusions.get(1)})"
    assert exclusions.get(2) == "table_structural", \
        f"짧은 데이터 행에 table_structural 미부여 (실제: {exclusions.get(2)})"
    assert exclusions.get(0) is None, \
        f"일반 문장에 잘못 부여됨 (실제: {exclusions.get(0)})"


CASES.append(("E. _detect_exclusions 통합 — table_structural 부여", case_detect_exclusions_integration))


# ─────────────────────────────────────────────────────────────
# Case F — 점수 영향: 테이블 헤더 매칭이 분자에서 빠지는지
# 의역 4건 + 헤더 매칭 1건 (table_structural) 중 의역만 점수 반영
# total=10, scored = 4 (의역만), score = 4/9 ≈ 44.4%
# 분모: 10 - 1 (table_structural 활성 제외 인덱스) = 9
# ─────────────────────────────────────────────────────────────
def case_table_structural_excluded_from_score():
    matches = [_make_match(i, TYPE_PARAPHRASE) for i in range(4)]
    # 헤더 매칭 (table_structural 사유 부여)
    header_match = _make_match(4, TYPE_IDENTICAL)
    header_match["exclusion_reason"] = "table_structural"
    matches.append(header_match)
    target_sents = [f"sent {i}" for i in range(10)]
    exclusion_map = {4: "table_structural"}
    summary = _compute_summary(matches, [], target_sents, exclusion_map)
    score = summary["similarity_score"]
    # 4 / (10 - 1) = 4/9 = 44.4
    assert abs(score - 44.4) < 0.2, \
        f"테이블 구조 매칭이 점수에서 빠지지 않음 (점수={score}, 기대≈44.4)"
    assert summary["exclusion_breakdown"]["table_structural"] == 1, \
        f"exclusion_breakdown.table_structural 카운트 누락"


CASES.append(("F. 헤더 매칭 점수에서 제외 + breakdown 카운트", case_table_structural_excluded_from_score))


# ─────────────────────────────────────────────────────────────
# Plan-55 — 표 행 sentence 분리 가드 + escape pipe
# ─────────────────────────────────────────────────────────────

# Case G ★ — 표 행 안 마침표 + 한글 시작 → 분리 안 됨 (핵심 결함 회귀 방지)
def case_sentence_split_table_row_with_period():
    row = "| 항목 | 값. 자세한 설명 |"
    parts = _sentence_split(row)
    assert parts == [row], (
        f"Case G 실패: 표 행 분리됨 (수정 전 결함). "
        f"기대 1개, 실제 {len(parts)}개: {parts}"
    )
    # 분리 안 된 1개 sentence 가 _is_table_row True 인지도 검증
    assert _is_table_row(parts[0]), (
        f"Case G 실패: 분리 안 됐어도 _is_table_row 가 False 면 표 인식 못함"
    )


CASES.append(("G. ★ 표 행 안 마침표 분리 가드 (수정 전 FAIL 예상)", case_sentence_split_table_row_with_period))


# Case H — 일반 paragraph 의 sentence 분리 동작 회귀 방지
def case_sentence_split_normal_paragraph():
    para = "Hello world. This is the second sentence."
    parts = _sentence_split(para)
    assert len(parts) == 2, (
        f"Case H 실패: 일반 paragraph 분리 동작 깨짐. 기대 2개, 실제 {len(parts)}개: {parts}"
    )
    assert parts[0].endswith("world."), f"Case H 실패: 첫 sentence 끝 'world.' 아님 ({parts[0]!r})"


CASES.append(("H. 일반 paragraph 분리 회귀 방지 (Hello world. This is...)", case_sentence_split_normal_paragraph))


# Case I — 한글 paragraph 분리 회귀 방지
def case_sentence_split_korean_paragraph():
    para = "안녕하세요. 두 번째 문장입니다."
    parts = _sentence_split(para)
    assert len(parts) == 2, (
        f"Case I 실패: 한글 paragraph 분리 동작 깨짐. 기대 2개, 실제 {len(parts)}개: {parts}"
    )


CASES.append(("I. 한글 paragraph 분리 회귀 방지", case_sentence_split_korean_paragraph))


# Case J — escape pipe (\|) 셀 안 보존
def case_parse_table_cells_escape_pipe():
    cells = _parse_table_cells('| A\\|B | C |')
    assert cells == ['A|B', 'C'], (
        f"Case J 실패: escape pipe 복원 안 됨. 기대 ['A|B', 'C'], 실제 {cells}"
    )


CASES.append(("J. ★ 셀 안 escape pipe (\\|) 복원", case_parse_table_cells_escape_pipe))


# Case K — escape 없는 일반 셀 회귀 방지
def case_parse_table_cells_normal():
    cells = _parse_table_cells('| 항목 | 값 | 비고 |')
    assert cells == ['항목', '값', '비고'], (
        f"Case K 실패: 일반 셀 분리 깨짐. 실제 {cells}"
    )


CASES.append(("K. 일반 셀 분리 회귀 방지", case_parse_table_cells_normal))


# ─────────────────────────────────────────────────────────────
# Plan-56 — 자동 제외 정규식 markdown prefix 인식 + 헤딩 분기
# ─────────────────────────────────────────────────────────────

# Case L ★ — references_section markdown prefix 인식
def case_references_with_md_prefix():
    assert _REFERENCES_HEADER_RE.match('## References'), "Case L 실패: ## References 미매칭"
    assert _REFERENCES_HEADER_RE.match('### 참고문헌'), "Case L 실패: ### 참고문헌 미매칭"


CASES.append(("L. ★ references_section markdown prefix 인식", case_references_with_md_prefix))


# Case M — references_section 기존 패턴 회귀 방지
def case_references_no_prefix():
    assert _REFERENCES_HEADER_RE.match('References'), "Case M 실패: References 미매칭 (회귀)"
    assert _REFERENCES_HEADER_RE.match('참고문헌'), "Case M 실패: 참고문헌 미매칭 (회귀)"


CASES.append(("M. references_section 기존 패턴 회귀 방지", case_references_no_prefix))


# Case N ★ — toc_heading markdown prefix 인식
def case_toc_with_md_prefix():
    assert _TOC_HEADING_RE.match('## 1.1 SCOPE'), "Case N 실패: ## 1.1 SCOPE 미매칭"
    assert _TOC_HEADING_RE.match('### 2.3.1 검증'), "Case N 실패: ### 2.3.1 검증 미매칭"


CASES.append(("N. ★ toc_heading markdown prefix 인식", case_toc_with_md_prefix))


# Case O — toc_heading 기존 패턴 회귀 방지
def case_toc_no_prefix():
    assert _TOC_HEADING_RE.match('1.1 SCOPE'), "Case O 실패: 1.1 SCOPE 미매칭 (회귀)"
    assert _TOC_HEADING_RE.match('2.3.1 검증'), "Case O 실패: 2.3.1 검증 미매칭 (회귀)"


CASES.append(("O. toc_heading 기존 패턴 회귀 방지", case_toc_no_prefix))


# Case P ★ — caption markdown prefix 인식
def case_caption_with_md_prefix():
    assert _CAPTION_RE.match('## Figure 1'), "Case P 실패: ## Figure 1 미매칭"
    assert _CAPTION_RE.match('### 표 3'), "Case P 실패: ### 표 3 미매칭"


CASES.append(("P. ★ caption markdown prefix 인식", case_caption_with_md_prefix))


# Case Q — caption 기존 패턴 회귀 방지
def case_caption_no_prefix():
    assert _CAPTION_RE.match('Figure 1: Architecture'), "Case Q 실패: Figure 1: Architecture 미매칭 (회귀)"
    assert _CAPTION_RE.match('표 3'), "Case Q 실패: 표 3 미매칭 (회귀)"


CASES.append(("Q. caption 기존 패턴 회귀 방지", case_caption_no_prefix))


# Case R ★ — _build_tagged_html 헤딩 출력
def case_build_tagged_html_heading():
    sentences = ['## 1.1 SCOPE', '본문 단락이다 일반 텍스트.']
    html = _build_tagged_html(sentences)
    assert '<h2 data-sent-idx="0" class="sim-sent">1.1 SCOPE</h2>' in html, (
        f"Case R 실패: <h2> 태그 출력 안 됨. html={html}"
    )
    assert '<p data-sent-idx="1" class="sim-sent">본문 단락이다 일반 텍스트.</p>' in html, (
        f"Case R 실패: <p> 태그 출력 안 됨. html={html}"
    )
    # ## prefix 가 raw 로 남아있지 않아야
    assert '## ' not in html, f"Case R 실패: ## prefix 가 raw 노출됨. html={html}"


CASES.append(("R. ★ _build_tagged_html 헤딩 출력 + paragraph 보존", case_build_tagged_html_heading))


# Case S — _build_tagged_html h1, h2, h3 다단계 처리
def case_build_tagged_html_multi_level_heading():
    sentences = ['# 서론', '## 배경', '### 상세']
    html = _build_tagged_html(sentences)
    assert '<h1 data-sent-idx="0"' in html and '서론</h1>' in html, f"h1 출력 실패: {html}"
    assert '<h2 data-sent-idx="1"' in html and '배경</h2>' in html, f"h2 출력 실패: {html}"
    assert '<h3 data-sent-idx="2"' in html and '상세</h3>' in html, f"h3 출력 실패: {html}"


CASES.append(("S. _build_tagged_html h1/h2/h3 다단계", case_build_tagged_html_multi_level_heading))


def main() -> int:
    print("Plan-52 — 테이블 구조 행 검출 검증\n")
    fail = 0
    for name, fn in CASES:
        try:
            fn()
            print(f"  PASS  {name}")
        except AssertionError as e:
            print(f"  FAIL  {name}\n        {e}")
            fail += 1
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR {name}\n        {type(e).__name__}: {e}")
            fail += 1

    print()
    if fail == 0:
        print("=" * 60)
        print(f"PASS: {len(CASES)} 케이스 모두 통과")
        print("=" * 60)
        return 0
    print("=" * 60)
    print(f"FAIL: {fail}/{len(CASES)} 건 실패")
    print("=" * 60)
    return 1


if __name__ == "__main__":
    sys.exit(main())
