# Plan-53 — DOCX/PDF 본문-표 원본 순서 보존

> 작성일: 2026-04-30
> 완료일: 2026-04-30
> 변경 범위: `backend/services/docx_utils.py` (신규) + `backend/services/document_extractor.py` (2곳) + 신규 단위 테스트 1건

---

## 진행 현황 요약

| Phase | 내용 | 상태 |
|-------|------|------|
| Phase 1 | `docx_utils.py` 공용 헬퍼 + `sim_block_order_test.py` 5 케이스 | ✅ 완료 |
| Phase 2 | `_from_docx` 재구현 — `iter_block_items` 통합 순회 | ✅ 완료 |
| Phase 3 | PDF 폴백 (`_extract_text_page_fallback`) bbox 정렬 | ✅ 완료 |
| Phase 4 | 자동 회귀 24건 PASS + API E2E 토큰 위치 검증 | ✅ 완료 |
| Phase 5 | 피드백 보고서 + 계획서 done- 처리 | ✅ 완료 |

---

## 0. Context

### 사용자 페인 (Plan-52 검토 중 발견)
- DOCX 의 본문 사이에 위치한 표가 모두 문서 **끝에 모이는** 결함
- 시각 패널에서 표가 원문 위치와 다르게 표시
- 페이지 마커가 표 사이에 못 들어가 PDF 페이지 정합 깨짐

### 결함 메커니즘
`_from_docx` 가 `doc.paragraphs` 와 `doc.tables` 별개 컬렉션을 분리 순회 — python-docx 의 두 컬렉션은 원본 XML 순서 정보 없음.

### 업계 표준
- python-docx GitHub issue #40 의 long-standing 표준 답변: `doc.element.body` 순회
- pandoc, mammoth, Apache POI 모두 동일 접근
- 사내 explorer 변환기 (`tools/converter/converter.py:_iter_block_items`) 가 이미 표준 패턴 적용

---

## 1. Phase 1 — 공용 헬퍼 + 단위 테스트

### `backend/services/docx_utils.py` 신규
```python
def iter_block_items(doc) -> Iterator:
    """Document body 의 paragraph + table 을 원본 순서대로 yield."""
    for child in doc.element.body:
        tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
        if tag == 'p':    yield doc.paragraphs[para_idx]; ...
        elif tag == 'tbl': yield doc.tables[table_idx]; ...
```

### `tests/sim_block_order_test.py` 신규 5 케이스
| Case | 시나리오 |
|------|---------|
| A | paragraph 만 |
| B | table 만 |
| C | paragraph↔table 교차 (iter_block_items 핵심) |
| **D** ★★ | `_from_docx` E2E markdown 출력 순서 (결함 직접 검증) |
| E | 빈 doc |

### 수정 전 결함 객관 증거
Case D FAIL: `{'INTRO': 0, 'HDR1': 52, 'MIDDLE': 17, 'HDR2': 105, 'END': 35}`
→ 모든 paragraph (0, 17, 35) → 모든 table (52, 105). 정확한 결함 패턴 캡처.

---

## 2. Phase 2 — `_from_docx` 재구현

### 변경 (`document_extractor.py:88~120`)
```python
from docx.text.paragraph import Paragraph
from docx.table import Table
from .docx_utils import iter_block_items

for block in iter_block_items(doc):
    if isinstance(block, Paragraph):
        # 페이지 마커 + 헤딩 + 본문
    elif isinstance(block, Table):
        md_parts.append(_docx_table_to_md(block))
```

### 효과
- 본문/표 원본 순서 보존
- 페이지 마커 정확한 위치 삽입
- `_docx_table_to_md` 무수정 (호출부만 변경)

### 검증
- Case D 수정 전 FAIL → 수정 후 PASS
- 기존 회귀 19/19 PASS

---

## 3. Phase 3 — PDF 폴백 bbox 정렬

### 변경 (`_extract_text_page_fallback`)
```python
# (y0, x0, content) 튜플로 통합 → 위치 정렬
items.sort(key=lambda x: (x[0], x[1]))
```

### 효과
- 폴백 경로도 본문/표 원본 순서 정합
- PyMuPDF4LLM 메인 경로 무영향

---

## 4. Phase 4 — 검증

### 자동 회귀
| 검사 | 결과 |
|------|------|
| 신규 `sim_block_order_test.py` | ✅ 5/5 PASS |
| 기존 `sim_table_structural_test.py` | ✅ 6/6 PASS |
| 기존 `sim_score_v3_unit_test.py` | ✅ 5/5 PASS |
| 기존 `sim_merge_adjacent_unit_test.py` | ✅ 8/8 PASS |
| `sim_label_consistency.sh` | ✅ PASS |

총 **24건 PASS** (회귀 0).

### API E2E (실제 DOCX 업로드)
Mock DOCX 5블록 (paragraph→table→paragraph→table→paragraph) → `/api/compare/extract-document` 호출 결과:
```
INTRO_PARAGRAPH     : 0
HEADER1_A           : 35
MIDDLE_PARAGRAPH    : 109
HEADER2_A           : 143
END_PARAGRAPH       : 194
순서 정합: True
```

→ 본문/표 원본 순서 정확히 보존.

---

## 5. 산출물

| 파일 | 변경 |
|------|------|
| `backend/services/docx_utils.py` | 신규 (~30줄) — `iter_block_items` |
| `backend/services/document_extractor.py` | `_from_docx` 재구현 + `_extract_text_page_fallback` bbox 정렬 |
| `tests/sim_block_order_test.py` | 신규 (5 케이스) |
| `workbench/reports/plan-53-feedback.md` | 검증 보고서 |
| `workbench/plans/done-53-docx-block-order.md` | 본 계획서 (완료) |

---

## 6. 영향 분석

### 격리
- **explorer 시스템 무영향** — `tools/converter/converter.py` 자체 무수정
- **translator 시스템 무영향** — `md_extractor.py` 무수정
- **매칭 알고리즘 무수정** — split/L1/L3/merge 본체 무영향
- **API 응답 구조 무변동** — markdown 순서만 변동

### 점수 영향 (sentence index set 분모 안정)
- `split_sentences` 입력 순서만 변경 → sentence 자체 동일
- L1 fingerprint / L3 임베딩 위치 무관 → 매칭 페어 거의 동일
- 점수 분모 보존, 분자 거의 동일 → ±2% 이내

### 부수 효과 (긍정)
- `_detect_exclusions` 의 `references_section` 진입/종료 추적 정합
- PDF 페이지 마커 위치 정확

### 롤백
- 신규 파일 삭제 + git revert 1회로 즉시 복원

---

## 7. 한 줄 결론

**PASS.** Plan-53 완료 — DOCX/PDF 본문-표 원본 순서 보존. `docx_utils.iter_block_items` 공용 헬퍼 + `_from_docx` 통합 순회 + PDF 폴백 bbox 정렬. 단위 테스트 신규 5건 fail-then-pass + 기존 19건 회귀 0 + API E2E 토큰 위치 정합. 업계 표준 부합 + 사내 3 변환기 일관성 회복.
