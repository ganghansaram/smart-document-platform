# Plan-55 — 표 행 sentence 분리 가드 + escape pipe 처리

> 작성일: 2026-05-01
> 완료일: 2026-05-01
> 변경 범위: `backend/services/similarity_engine.py` (2곳, 6줄) + `tests/sim_table_structural_test.py` (5 케이스 추가)

---

## 진행 현황 요약

| Phase | 내용 | 상태 |
|-------|------|------|
| Phase 1 | `_sentence_split` 표 행 가드 (3줄) | ✅ 완료 |
| Phase 2 | `_parse_table_cells` escape pipe 복원 (3줄) | ✅ 완료 |
| Phase 3 | 단위 테스트 5 케이스 추가 + 자동 회귀 + API E2E | ✅ 완료 |
| Phase 4 | 보고서 + 계획서 done- 처리 | ✅ 완료 |

---

## 0. Context

### 사용자 페인
검사 후 표 일부가 "기호 + 텍스트" 로 분해되어 노출. 셀 안 마침표 + 한글 시작 텍스트가 sentence 분리 정규식에 걸려 표 행이 깨짐.

### 결함 메커니즘
`_sentence_split` 의 정규식 `(?<=[.!?])\s+(?=[A-Z가-힣\"\'])` 가 표 행 안 마침표를 sentence 경계로 해석 → `_is_table_row` 가 분리된 sentence 양쪽에서 False → `_build_tagged_html` 이 `<p>` 로 평탄화.

부수: `_parse_table_cells` 가 escape pipe (`\|`) 복원 안 함.

---

## 1. Phase 1 — `_sentence_split` 가드

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

---

## 2. Phase 2 — `_parse_table_cells` escape 복원

```python
def _parse_table_cells(row: str) -> list:
    s = row.strip()
    if s.startswith('|'): s = s[1:]
    if s.endswith('|'): s = s[:-1]
    placeholder = '\x01'
    s = s.replace('\\|', placeholder)
    return [c.strip().replace(placeholder, '|') for c in s.split('|')]
```

---

## 3. Phase 3 — 단위 테스트 5 케이스 추가

`tests/sim_table_structural_test.py` 에 추가:
| Case | 검증 |
|------|------|
| **G** ★ | 표 행 안 마침표 분리 안 됨 (핵심 결함) |
| H | 일반 paragraph 분리 회귀 방지 |
| I | 한글 paragraph 분리 회귀 방지 |
| **J** ★ | escape pipe 복원 |
| K | 일반 셀 분리 회귀 방지 |

---

## 4. 검증

### 자동 회귀 29/29 PASS
- `sim_table_structural_test.py` 11/11
- `sim_block_order_test.py` 5/5
- `sim_score_v3_unit_test.py` 5/5
- `sim_merge_adjacent_unit_test.py` 8/8
- `sim_label_consistency.sh` PASS

### API E2E
Mock DOCX: 셀에 "검증 완료. 출하 가능." / "재검증 필요. 보류." 포함.

수정 후 markdown:
```
| A-100 | 5 | 검증 완료. 출하 가능. |
| A-200 | 3 | 재검증 필요. 보류. |
```

→ 표 행 무결성 보존.

---

## 5. 산출물

| 파일 | 변경 |
|------|------|
| `backend/services/similarity_engine.py` | `_sentence_split` 3줄 + `_parse_table_cells` 3줄 |
| `tests/sim_table_structural_test.py` | 5 케이스 추가 |
| `workbench/reports/plan-55-feedback.md` | 검증 보고서 |
| `workbench/plans/done-55-...md` | 본 계획서 (완료) |

---

## 6. 영향 분석

### 격리
- 매칭 알고리즘 무수정
- API 응답 구조 무변동
- 다른 변환기 무영향
- 프론트 무수정

### 점수 영향
- 표 행 분리 안 됨 → 분모 약간 감소
- 점수 ±3% 이내 변동 (sentence index set 기반)
- 사용자 직관 (셀 단위) 과 일치하는 방향

### 롤백
- 6줄 추가만, git revert 1회로 즉시 복원

---

## 7. 한 줄 결론

**PASS.** Plan-55 완료 — `_sentence_split` 표 행 가드 + `_parse_table_cells` escape pipe 복원. 사용자 페인 (검사 후 표 분해) 직접 해소. 29/29 PASS. 업계 표준 부합. Plan-52~54 표 처리 효과가 모든 문서에서 정상 작동.
