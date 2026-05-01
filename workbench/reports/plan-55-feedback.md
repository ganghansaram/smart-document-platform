# Plan-55 — 표 행 sentence 분리 가드 + escape pipe 처리 검증

> 작성일: 2026-05-01
> 변경 범위: `backend/services/similarity_engine.py` (2곳, 6줄) + `tests/sim_table_structural_test.py` (5 케이스 추가)
> 검증: 단위 테스트 11/11 PASS + 기존 회귀 18건 PASS + API E2E 정확 동작

---

## 1. 배경

### 사용자 페인 (Plan-54 이후 검토에서 발견)
> "처음 문서를 업로드했을때 좌/우 문서 패널에 테이블 등 정상적으로 잘 반영된것 같았는데, 유사도 분석을 한번 하고나면, 테이블 등 일부가 테이블형태에서 떨어져나와서 기호와 텍스트로 분해되어 있는걸 발견했어"

### 결함 원인
`_sentence_split` (similarity_engine.py:823~) 가 **모든 텍스트에 동일 분리 적용** — 표 행 안에 마침표 + 공백 + 한글/대문자 시작이 있으면 표 행을 sentence 두 개로 분리. `_is_table_row` 가 분리된 sentence 양쪽에서 모두 False → `_build_tagged_html` 이 `<p>` 로 평탄화 → 표 깨짐.

### 부수 결함
`_parse_table_cells` 가 단순 split 사용 → `_rows_to_md` 가 escape 한 `\|` 가 셀 구분으로 잘못 인식.

---

## 2. 변경 항목

### 2-1. `_sentence_split` 가드 (3줄)
```python
def _sentence_split(text: str) -> list:
    s = text.strip()
    # Plan-55: GFM 테이블 행은 분리 안 함
    if s.startswith('|') and s.endswith('|') and s.count('|') >= 3:
        return [s]
    pattern = r'(?<=[.!?])\s+(?=[A-Z가-힣\"\'])'
    parts = re.split(pattern, text)
    return [p.strip() for p in parts if p.strip()]
```

### 2-2. `_parse_table_cells` escape 복원 (3줄)
```python
def _parse_table_cells(row: str) -> list:
    s = row.strip()
    if s.startswith('|'): s = s[1:]
    if s.endswith('|'): s = s[:-1]
    # Plan-55: \| → 임시 placeholder → split → 복원
    placeholder = '\x01'
    s = s.replace('\\|', placeholder)
    return [c.strip().replace(placeholder, '|') for c in s.split('|')]
```

### 2-3. 단위 테스트 신규 5 케이스 (`tests/sim_table_structural_test.py`)
| Case | 시나리오 | 의도 |
|------|---------|------|
| **G** ★ | 표 행 안 마침표 + 한글 시작 (`| 항목 | 값. 자세한 설명 |`) | 핵심 결함 회귀 방지 |
| H | 일반 paragraph (`Hello. World.`) | 영문 paragraph 분리 동작 회귀 방지 |
| I | 한글 paragraph (`안녕하세요. 두 번째...`) | 한글 paragraph 분리 동작 회귀 방지 |
| **J** ★ | escape pipe (`\|` 셀 안) | 부수 결함 회귀 방지 |
| K | 일반 셀 분리 | 회귀 방지 |

---

## 3. 검증 결과

### 3-1. 단위 테스트 11/11 PASS
```
PASS  A. _is_table_row 기본 동작
PASS  B. _is_short_cell_row 구조성 판정
PASS  C. 첫 행 헤더 + 긴 셀 데이터 행 구분
PASS  D. 짧은 셀 데이터 행도 구조성
PASS  E. _detect_exclusions 통합 — table_structural 부여
PASS  F. 헤더 매칭 점수에서 제외 + breakdown 카운트
PASS  G. ★ 표 행 안 마침표 분리 가드 (수정 전 FAIL 예상)
PASS  H. 일반 paragraph 분리 회귀 방지
PASS  I. 한글 paragraph 분리 회귀 방지
PASS  J. ★ 셀 안 escape pipe 복원
PASS  K. 일반 셀 분리 회귀 방지
```

### 3-2. 기존 회귀 18건 PASS
| 검사 | 결과 |
|------|------|
| `sim_block_order_test.py` | 5/5 PASS |
| `sim_score_v3_unit_test.py` | 5/5 PASS |
| `sim_merge_adjacent_unit_test.py` | 8/8 PASS |
| `sim_label_consistency.sh` | PASS |

총 **29건 PASS** (회귀 0).

### 3-3. API E2E (실제 DOCX)
Mock DOCX: 셀에 "검증 완료. 출하 가능." / "재검증 필요. 보류." 같이 마침표 + 한글 시작 텍스트 포함.

#### 결과 (수정 후)
```markdown
이 보고서는 항공기 부품의 품질 검증 프로세스를 설명한다.

| 항목 | 값 | 설명 |
| --- | --- | --- |
| A-100 | 5 | 검증 완료. 출하 가능. |
| A-200 | 3 | 재검증 필요. 보류. |

각 부품은 기준에 부합한다.
```

→ 표 행 안 마침표 텍스트 정상 보존, 표가 단일 sentence 로 인식 → `_build_tagged_html` 이 `<table>` 로 출력.

#### 수정 전 결함 (참고)
표 행 분리되어 markdown 에 `\n\n검증 완료.\n\n출하 가능.\n\n` 같이 본문으로 분해됨 (표 깨짐).

---

## 4. 영향 분석

### 4-1. 격리
- **매칭 알고리즘 무수정** — split_sentences 출력 sentence 개수만 변동 (표 행이 1개로 유지)
- **API 응답 구조 무변동** — markdown 출력만 정확화
- **다른 변환기 (translator/explorer) 무영향** — 별도 모듈
- **프론트 무수정** — 백엔드 출력만 정상화

### 4-2. 점수 영향 (sentence index set 분모)
- 표 행 분리 안 됨 → 표 안 sentence 1개로 유지 → 분모 약간 감소
- 분자도 변동 (셀 단위 매칭 → 행 단위 매칭) — 사용자 직관과 일치
- Plan-50 sentence index set 기반 분모는 안정 (중복 제거)
- 실제 운영 문서에서 점수 ±3% 이내 변동 예상

### 4-3. 부수 효과 (긍정)
- 표 헤더 + 데이터 행이 단일 sentence 로 매칭 평가 → 셀 단위 노이즈 감소
- 표 무결성 보장 → Plan-52 시각 보존 + Plan-54 시각 신호가 모든 문서에서 작동

### 잔여 위험
- escape pipe placeholder (`\x01`) 가 실제 텍스트에 포함될 가능성 — 0 (제어 문자, 일반 문서에 안 나옴)
- `_sentence_split` 가드 조건 (`startswith('|') AND endswith('|') AND count >= 3`) 이 일반 paragraph 에서 false positive 가능성 — 매우 낮음 (일반 문장이 `|` 로 시작/종료하는 경우 거의 없음)

---

## 5. UX/UI 전문가 관점

### 사용자 페인 직접 해소
- 검사 후에도 표가 표 형태 유지 (이전엔 일부 표 분해)
- "기호와 텍스트로 분해" 페인 직접 해소
- 자동 제외 시각 신호 (Plan-54) + 표 시각 보존 (Plan-52) + 본문 순서 보존 (Plan-53) 가 모두 정상 작동하는 상태

### 통일된 표 처리
- 단순 데이터 표 (마침표 없음): 이전부터 정상 → 무영향
- 설명 텍스트 표 (마침표 있음): 이전 결함 → **수정 후 정상**
- 모든 표 패턴에서 일관 동작

---

## 6. 한 줄 결론

**PASS.** Plan-55 완료 — `_sentence_split` 표 행 가드 (3줄) + `_parse_table_cells` escape pipe 복원 (3줄) + 단위 테스트 5 케이스 추가. 사용자 페인 (검사 후 표 분해) 직접 해소. 단위 테스트 29/29 PASS, 회귀 0, 매칭 알고리즘 무수정. 업계 표준 (pandoc/mammoth/Apache POI) 부합 + Plan-52~54 의 표 처리 효과가 모든 문서에서 작동.
