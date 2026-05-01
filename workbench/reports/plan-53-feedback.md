# Plan-53 — DOCX/PDF 본문/표 원본 순서 보존 검증

> 작성일: 2026-04-30
> 변경 범위: `backend/services/docx_utils.py` (신규) + `backend/services/document_extractor.py` (2곳 수정) + 신규 단위 테스트 1건
> 검증: 단위 테스트 5건 신규 (D 케이스 fail-then-pass) + 기존 회귀 19건 PASS + API E2E 토큰 위치 검증

---

## 1. 배경

### 사용자 페인 (Plan-52 검토 중 발견)
사용자 검토 (`테이블이 끝쪽에 모아둔거야?`) 로 식별:
- DOCX 의 본문 사이에 위치한 표가 모두 문서 **끝에 모이는** 결함
- 시각 패널에서 표가 원문 위치와 다르게 표시
- 페이지 마커가 표 사이에 못 들어가 PDF 페이지 정합 깨짐

### 결함 위치
`backend/services/document_extractor.py:_from_docx` (line 91~113):
```python
# 모든 단락 먼저
for para in doc.paragraphs:
    md_parts.append(text)
# 모든 표 끝에
for table in doc.tables:
    md_parts.append(_docx_table_to_md(table))
```

`_extract_text_page_fallback` (PDF 폴백, line 230~261) 도 동일 패턴.

### 우리 시스템 일관성 결함
3개 변환기 중 verify 만 어긋남:
| 변환기 | 위치 | 본문 순서 보존 (수정 전) |
|--------|------|-------------------------|
| Explorer (webbook) | `tools/converter/converter.py:_iter_block_items` | ✅ 표준 |
| Translator | `tools/converter/md_extractor.py` (PyMuPDF4LLM) | ✅ 자동 |
| **Verify (compare)** | `backend/services/document_extractor.py` | ❌ 단순 분리 |

### 업계 표준 부합도
| 도구 | 본문 순서 보존 |
|------|----------------|
| python-docx 공식 권장 (issue #40) | ✅ |
| pandoc, mammoth, Apache POI | ✅ |
| Copyleaks/Turnitin 등 표절 탐지 | ✅ |
| 우리 verify 시스템 (수정 전) | ❌ → ✅ 수정 후 |

---

## 2. 변경 항목

### 2-1. 공용 헬퍼 신규 (`backend/services/docx_utils.py`)
```python
def iter_block_items(doc) -> Iterator:
    """Document body 의 paragraph + table 을 원본 순서대로 yield.
    doc.element.body 의 child node 직접 순회로 XML 출현 순서 보존."""
    for child in doc.element.body:
        tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
        if tag == 'p':    yield doc.paragraphs[para_idx]
        elif tag == 'tbl': yield doc.tables[table_idx]
```
- 사내 검증된 `tools/converter/converter.py:_iter_block_items` 패턴 추출
- 30줄 깔끔한 구현

### 2-2. `_from_docx` 재구현 (`document_extractor.py`)
```python
# Plan-53: doc.paragraphs / doc.tables 분리 → iter_block_items 통합 순회
for block in iter_block_items(doc):
    if isinstance(block, Paragraph):
        # 페이지 마커 + 헤딩 감지 + 본문
    elif isinstance(block, Table):
        md_parts.append(_docx_table_to_md(block))
```
- `_docx_table_to_md` 함수 자체는 무수정 (호출부만 변경)
- 페이지 마커 (`<!-- Page N -->`) 가 정확한 위치에 삽입

### 2-3. PDF 폴백 bbox 정렬 (`_extract_text_page_fallback`)
```python
# (y0, x0, content) 튜플로 통합 → 위치 순 정렬
items.sort(key=lambda x: (x[0], x[1]))
```
- PyMuPDF4LLM 메인 경로는 무영향 (이미 위치 기반)
- 폴백 경로도 본문/표 원본 순서 정합

### 2-4. 신규 단위 테스트 (`tests/sim_block_order_test.py`)
5 케이스:
| Case | 시나리오 | 의도 |
|------|---------|------|
| A | paragraph 만 | iter_block_items 회귀 방지 |
| B | table 만 | iter_block_items 회귀 방지 |
| C | paragraph↔table 교차 | iter_block_items 핵심 |
| **D** ★★ | `_from_docx` E2E markdown 출력 순서 | **결함 직접 검증** |
| E | 빈 doc | 안전 동작 |

---

## 3. 검증 결과

### 3-1. 단위 테스트 — fail-then-pass

#### 수정 전 — 결함 객관 증거
```
PASS  A. paragraph 만 — 순서 보존
PASS  B. table 만 — 순서 보존
PASS  C. ★ paragraph↔table 교차 순서 보존 (iter_block_items 자체)
FAIL  D. ★★ _from_docx markdown 출력 순서 보존 (E2E)
      markdown 출력 순서 어긋남: {'INTRO': 0, 'HDR1': 52, 'MIDDLE': 17, 'HDR2': 105, 'END': 35}
      → 모든 paragraph 가 모든 table 보다 먼저 나옴 (INTRO < MIDDLE < END < HDR1 < HDR2)
PASS  E. 빈 doc — 안전 동작
```

→ **명확한 결함 객관 증거**: paragraph 위치 0, 17, 35 / table 위치 52, 105.

#### 수정 후
```
PASS  A. paragraph 만 — 순서 보존
PASS  B. table 만 — 순서 보존
PASS  C. ★ paragraph↔table 교차 순서 보존
PASS  D. ★★ _from_docx markdown 출력 순서 보존 (E2E)
PASS  E. 빈 doc — 안전 동작
```
→ 5/5 PASS — 의도된 순서 보존 확인.

### 3-2. 기존 회귀 테스트 — 영향 0

| 검사 | 결과 |
|------|------|
| `tests/sim_table_structural_test.py` | ✅ 6/6 PASS |
| `tests/sim_score_v3_unit_test.py` | ✅ 5/5 PASS (점수 공식 영향 0) |
| `tests/sim_merge_adjacent_unit_test.py` | ✅ 8/8 PASS |
| `tests/sim_label_consistency.sh` | ✅ PASS |
| `tests/sim_block_order_test.py` (신규) | ✅ 5/5 PASS |

총 **24건 단위 테스트 PASS** (회귀 0).

### 3-3. API E2E (실제 DOCX 업로드)

#### 시나리오
- Mock DOCX 생성 (python-docx): paragraph → table → paragraph → table → paragraph 5블록
- `/api/compare/extract-document` 호출 → markdown 응답 수신

#### 결과
```
--- 토큰 위치 검사 ---
  INTRO_PARAGRAPH     : 0
  HEADER1_A           : 35
  MIDDLE_PARAGRAPH    : 109
  HEADER2_A           : 143
  END_PARAGRAPH       : 194
  순서 정합: True
```

→ 본문/표/본문/표/본문 가 정확히 원본 순서대로 markdown 출력.

#### 출력 markdown 일부
```markdown
INTRO_PARAGRAPH 본문 시작 첫 단락 텍스트.

| HEADER1_A | HEADER1_B | HEADER1_C |
| --- | --- | --- |
| v1 | v2 | v3 |

MIDDLE_PARAGRAPH 본문 중간 단락 텍스트.

| HEADER2_A | HEADER2_B |
| --- | --- |
| v4 | v5 |

END_PARAGRAPH 본문 끝 단락 텍스트.
```

표가 본문 사이에 자연스럽게 위치.

---

## 4. 코드 전문가 관점 — 영향 분석

### 4-1. 격리
- **explorer 시스템 무영향**: `tools/converter/converter.py` 무수정. 자체 `_iter_block_items` 그대로 유지 (향후 일관성 차원에서 새 헬퍼로 마이그레이션 가능하나 본 작업 외)
- **translator 시스템 무영향**: `md_extractor.py` 무수정 (PyMuPDF4LLM 자체 위치 기반)
- **매칭 알고리즘 무수정**: split_sentences, L1/L3 그리디, _merge_adjacent 본체 무영향
- **API 응답 구조 무변동**: markdown 출력 순서만 변동

### 4-2. 점수 보존 — sentence index set 분모 안정
- `split_sentences` 입력 텍스트 순서만 변경 → sentence 자체 동일 (개수 동일)
- L1 fingerprint, L3 임베딩은 위치 무관 → 매칭 페어 거의 동일
- `_merge_adjacent` 의 ti 정렬 후 인접 병합 → 인접 관계 변동 → 카드 분포 약간 변동 가능
- `_compute_summary` 의 sentence index set 분모 → 분모 보존, 분자 거의 동일

### 4-3. 부수 효과
- **자동 제외 검출 정합**: `_detect_exclusions` 의 references_section 진입/종료 추적이 본문 순서 기반 → 표가 끝에 있을 때 잘못 인식되던 케이스 정정
- **페이지 마커 정합**: 표가 페이지 경계에 있어도 마커가 정확한 위치 삽입 (PDF 보고서 품질 향상)

---

## 5. UX/UI 전문가 관점 — 사용자 경험 변화

### 5-1. 시각 인식 회복
- 이전: 본문 → 표가 끝에 모임 → 사용자 "이 표가 본문 어디에 있었지?" 알 수 없음
- 이후: 본문 → 표 → 본문 자연스러운 흐름 → 원문 구조 그대로 인지

### 5-2. 페이지 마커 정합 (PDF)
- 이전: 표가 끝에 모여 페이지 정합 깨짐 → "원문 3페이지" 안내 부정확
- 이후: 표가 원본 페이지에 위치 → 보고서 신뢰도 향상

### 5-3. 도구 신뢰
- 표절 탐지 도구의 **기본 가정**: 원문 구조 보존
- 이전 결함 상태는 운영 측에 "이 도구는 원문을 망가뜨린다" 인상 가능
- 이후 표준 부합으로 신뢰 회복

---

## 6. 사용자 관점 피드백

### Before (사용자 보고)
- "테이블이 끝쪽에 모아둔거야? 왠지 그렇게 느껴져서"

### After
- 본문/표/본문/표 자연스러운 흐름
- 원문 그대로 시각 표시
- 페이지 마커 정합

### 통일성 회복
- 3 변환기 중 1개 어긋남 상태 → 모두 정합
- 사내 검증된 패턴 (`_iter_block_items`) 재사용으로 일관성

---

## 7. 부수 발견 (현 범위 외)

| # | 항목 | 비고 |
|---|------|------|
| O-1 | explorer (`converter.py`) 도 신규 `docx_utils.iter_block_items` 사용 마이그레이션 가능 | 코드 중복 제거 차원, 후속 일정 |
| O-2 | `compare_service.py:_extract_docx` 도 본문 순서 미보존 | API `/compare/upload` 가 paragraphs 배열 반환 — 표 자체 미처리. 별건 검토 필요 |
| O-3 | `_extract_text_pages_batch` 의 PyMuPDF4LLM 메인 경로 — 폴백 외 영역 점검 필요 | 메인 경로는 자동 보존이지만 검증 안 함 |

---

## 8. 한 줄 결론

**PASS.** Plan-53 완료 — DOCX/PDF 본문-표 원본 순서 보존. `docx_utils.iter_block_items` 공용 헬퍼 추출 + `_from_docx` 통합 순회 + PDF 폴백 bbox 정렬. 단위 테스트 신규 5건 fail-then-pass + 기존 19건 회귀 0 + API E2E 토큰 위치 정합. 매칭 알고리즘 무수정, 점수 분모 보존, explorer 시스템 무영향. 업계 표준 (python-docx 공식 권장 / pandoc / mammoth) 부합 + 사내 3 변환기 일관성 회복.
