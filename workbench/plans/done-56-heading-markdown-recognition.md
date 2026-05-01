# Plan-56 — 헤딩 markdown 인식 + 자동 제외 정규식 prefix 정합

> 작성일: 2026-05-01
> 완료일: 2026-05-01
> 변경 범위: `backend/services/similarity_engine.py` + 단위 테스트 보강

---

## 진행 현황 요약

| Phase | 내용 | 상태 |
|-------|------|------|
| Phase 1 | 자동 제외 정규식 3종 prefix 옵션 | ✅ 완료 |
| Phase 2 | `_build_tagged_html` 헤딩 분기 (CommonMark `<h{1..6}>`) | ✅ 완료 |
| Phase 3 | 단위 테스트 8 케이스 추가 + 자동 회귀 37/37 PASS | ✅ 완료 |
| Phase 4 | API E2E + Playwright UI 시각 검증 | ✅ 완료 |
| Phase 5 | 사용자 + 코드/UX 전문가 입장 피드백 | ✅ 완료 |
| Phase 6 | 보고서 + 계획서 done- 처리 | ✅ 완료 |

---

## 0. Context

### 사용자 페인
검사 후 본문 패널에 `## 1.1 SCOPE` 같은 markdown 기호가 raw 로 노출. 처음 업로드 시점 (`<h2>` 정상 변환) 과 검사 후 시점 (`<p>## ...` 평탄화) 불일치.

### 부수 발견 (★ 핵심)
자동 제외 정규식 3종 (`_TOC_HEADING_RE`, `_REFERENCES_HEADER_RE`, `_CAPTION_RE`) 이 모두 `^\s*` 시작 → markdown prefix (`## `) 가 있으면 매칭 실패. 결과:
- `## References` → `references_section` 진입 못 함 → **참고문헌 섹션 전체 점수에 inflated**
- `## 1.1 SCOPE` → `toc_heading` 자동 제외 실패
- `## Figure 1` → `caption` 자동 제외 실패

---

## 1. Phase 1 — 정규식 3종 prefix 옵션

```python
# 기존: ^\s*\d+(\.\d+)*\s+[A-Z가-힣]
# 신규: ^\s*(?:#{1,6}\s+)?\d+(\.\d+)*\s+[A-Z가-힣]
_TOC_HEADING_RE = re.compile(r'^\s*(?:#{1,6}\s+)?\d+(\.\d+)*\s+[A-Z가-힣]')
_REFERENCES_HEADER_RE = re.compile(
    r'^\s*(?:#{1,6}\s+)?(References|Bibliography|참고\s*문헌|인용\s*문헌)\b',
    re.IGNORECASE
)
_CAPTION_RE = re.compile(
    r'^\s*(?:#{1,6}\s+)?(Figure|Fig\.?|Table|Tbl\.?|그림|표)\s+\d+',
    re.IGNORECASE
)
```

`(?:...)?` non-capturing optional → 기존 매칭 100% 보존.

---

## 2. Phase 2 — `_build_tagged_html` 헤딩 분기

```python
_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$')

# _build_tagged_html 내부, 표 분기 직전:
h_match = _HEADING_RE.match(sent.strip())
if h_match:
    level = len(h_match.group(1))
    text = h_match.group(2).strip()
    parts.append(
        f'<h{level} data-sent-idx="{i}" class="sim-sent">'
        f'{html_mod.escape(text)}</h{level}>'
    )
    i += 1
    continue
```

우선순위: 헤딩 → 표 (Plan-52) → paragraph.

---

## 3. Phase 3 — 단위 테스트 8 케이스

`tests/sim_table_structural_test.py` 보강:
| Case | 검증 |
|------|------|
| **L** ★ | `## References` → `_REFERENCES_HEADER_RE` 매칭 |
| M | `References` 회귀 방지 |
| **N** ★ | `## 1.1 SCOPE` → `_TOC_HEADING_RE` 매칭 |
| O | `1.1 SCOPE` 회귀 방지 |
| **P** ★ | `## Figure 1` → `_CAPTION_RE` 매칭 |
| Q | `Figure 1: ...` 회귀 방지 |
| **R** ★ | `_build_tagged_html` 헤딩 출력 |
| S | h1/h2/h3 다단계 |

---

## 4. 검증 결과

### 자동 회귀 37/37 PASS
- `sim_table_structural_test.py` 19/19 (기존 11 + 신규 8)
- `sim_block_order_test.py` 5/5
- `sim_score_v3_unit_test.py` 5/5
- `sim_merge_adjacent_unit_test.py` 8/8
- `sim_label_consistency.sh` PASS

### Playwright UI E2E
Mock DOCX (Heading 1/2 + 본문 + 표 + 참고문헌 섹션):
- H1 `1.` → 자동 제외 (toc_heading)
- H2 `1.1 검증 범위` → 자동 제외 (toc_heading)
- H2 `참고문헌` → 매칭 자체 없음 (references_section 진입)
- ASTM/ISO 항목 → 매칭 없음 (references_section 자동 제외)
- 점수 40% (정확)
- ★ `##` 기호 raw 노출 0건

---

## 5. 영향 분석

### 격리
- 매칭 알고리즘 무수정
- 표 처리 (Plan-52) 무수정 — 헤딩 분기 표보다 우선
- 자동 제외 정규식 — non-capturing optional 로 기존 매칭 보존
- 프론트/translator/explorer 무영향

### 점수 정확도 향상
- **참고문헌 섹션 자동 제외 정상화** — 학술/공식 문서 inflation 해소
- 헤딩 + 캡션 자동 제외도 정합

### 잔여 위험
- CSS 셀렉터 (`.sim-md-view p.sim-hl.sim-hl-excluded`) 에 `<h{1..6}>` 미포함 → 자동 제외 헤딩 시각 신호 약함 (후속 hotfix 권장)

### 롤백
- 정규식 3줄 + 헤딩 분기 11줄 — git revert 1회

---

## 6. 산출물

| 파일 | 변경 |
|------|------|
| `backend/services/similarity_engine.py` | 정규식 3종 prefix + `_build_tagged_html` 헤딩 분기 (~14줄) |
| `tests/sim_table_structural_test.py` | 8 케이스 추가 |
| `workbench/reports/plan-56-feedback.md` | 검증 보고서 |
| `workbench/reports/plan-56-user-feedback.md` | 사용자 + 전문가 4관점 피드백 |
| `workbench/plans/done-56-...md` | 본 계획서 (완료) |

---

## 7. 업계 표준 부합

| 항목 | 적용 |
|------|------|
| CommonMark 헤딩 | ✅ `<h{1..6}>` 변환 |
| GFM 표 (Plan-52) | ✅ |
| HTML escape | ✅ |
| 자동 제외 prefix 인식 | ✅ |

---

## 8. 한 줄 결론

**PASS.** Plan-56 완료 — 헤딩 CommonMark 인식 + 자동 제외 정규식 prefix 정합. 사용자 페인 (`##` 기호 노출) + 참고문헌 점수 inflation 양쪽 해소. 단위 테스트 37/37 PASS. CommonMark/GFM 업계 표준 부합. 후속 hotfix (CSS `<h>` 셀렉터 보강) 권장.
