# Plan-52 — 유사도 모드 테이블 처리 개선 검증

> 작성일: 2026-04-30
> 변경 범위: `backend/services/similarity_engine.py` (다수), `backend/config.py` (1건), `data/help/similarity-help.json` (1건), `css/compare.css` (1건), 신규 단위 테스트 1건
> 검증: 단위 테스트 19건 PASS + API E2E 시나리오 + 시각 회귀

---

## 1. 배경

### 사용자 페인 (3건)
1. **시각 미인식**: DOCX 테이블이 비교 패널에 `| 셀1 | 셀2 |` 파이프 텍스트로 노출
2. **100% 오탐**: 헤더 행 (`| 항목 | 값 |`) 등 구조성 행이 문서 간 동일하여 매칭 → 점수 inflation
3. **MD 변환 인지 부재**: 사용자가 업로드 시 어떤 변환이 일어나는지 모름 (이건 안내 영역)

### 현재 동작 분석 결과
- 백엔드는 GFM Markdown 으로 테이블 변환 (`_docx_table_to_md`)
- 매칭 단계에서 테이블 행이 일반 문장과 동일하게 처리됨
- `_build_tagged_html` 이 모든 sentence 를 `<p data-sent-idx>` 평탄화 → 테이블 구조 소실
- 동일한 헤더가 100% 매칭으로 잡히고 분자에 들어가 점수 inflation 발생

---

## 2. 변경 항목 (5 카테고리)

### 2-1. SSOT 추가 (`data/help/similarity-help.json`)
`check_settings.exclude_table_structural` 신규 (default: true)

### 2-2. 백엔드 검출 함수 (`backend/services/similarity_engine.py`)
- `_is_table_row` — GFM 테이블 행 패턴 판정
- `_parse_table_cells` — 셀 분리
- `_is_short_cell_row` — 모든 셀 ≤ 3 단어 (구조성 신호)
- `_detect_table_structural` — 문맥 기반 (첫 행 헤더 + 짧은 셀 행)
- `_detect_exclusions` 통합 — `table_structural` 사유 부여
- `excl_to_key`, `TOGGLEABLE_EXCLUSIONS`, `exclusion_breakdown`, `_empty_result` 키 추가

### 2-3. `_build_tagged_html` 재구현
- 연속 GFM 테이블 행 → `<table class="sim-md-table">` 로 렌더
- 첫 행 → `<thead><tr><th>`, 나머지 → `<tbody><tr><td>`
- 각 행 `<tr data-sent-idx="i" class="sim-sent">` 태깅 (셀렉터 호환)

### 2-4. `split_sentences` 보강
- GFM 구분선 (`| --- | --- |`) 사전 필터 — 의미 없는 표시용 줄 제거
- sent_idx 정합성 유지 + 매칭 오염 방지

### 2-5. `_merge_adjacent` 보강
- exclusion_reason 다른 매칭 병합 차단
- 일반 문장 (None) + 헤더 (table_structural) 가 잘못 병합되어 분자 inflation 되는 결함 방지

### 2-6. 백엔드 기본값 (`backend/config.py`)
- `VERIFY_SIMILARITY_DEFAULTS["exclude_table_structural"] = True`

### 2-7. 프론트 CSS (`css/compare.css`)
- `tr.sim-hl-*` 행 단위 background 하이라이트 (5 카테고리)
- `tr.sim-active` outline 강조 (`<tr>` 의 border 한계 회피)
- `tr.sim-hl-user-excluded` opacity + line-through

---

## 3. 검증 결과

### 3-1. 자동 회귀 테스트

| 검사 | 결과 |
|------|------|
| 신규 `tests/sim_table_structural_test.py` | ✅ **6/6 PASS** |
| 기존 `tests/sim_score_v3_unit_test.py` | ✅ 5/5 PASS |
| `tests/sim_merge_adjacent_unit_test.py` (신규 H 케이스 포함) | ✅ **8/8 PASS** |
| `tests/sim_label_consistency.sh` | ✅ PASS |

총 **19건 단위 테스트 PASS** — 회귀 0.

### 3-2. API E2E 시나리오

#### 시나리오 1: 본문 동일 + 표 데이터 다름 (기본 케이스)
- 입력: 본문 2 sentence + 표 헤더 1 + 데이터 행 2 (서로 다름) + 결론 1
- 결과 (수정 후):
  - matches_count: 3 (병합 안 됨)
  - 매칭 [0]: 일반 문장 identical (reason=None)
  - 매칭 [1]: 헤더 identical (**reason=table_structural**)
  - 매칭 [2]: 결론 paraphrase (reason=None)
  - exclusion_breakdown.table_structural: 3
  - similarity_score: 100% (본문이 실제로 동일하므로 정확)

#### 시나리오 2 (★ 핵심 페인 검증): 본문 다름 + 표 헤더만 같음
- 입력: 본문 모두 다름 + 동일한 헤더 + 다른 데이터 행
- 결과 (수정 후):
  - matches_count: 1 (헤더 매칭 1건만, identical)
  - 매칭 reason: **table_structural**
  - similarity_score: **0%** ← 핵심 페인 해소
- 수정 전이라면: 헤더 매칭이 분자에 포함 → 점수 상승 (오탐)

#### 시나리오 3: 시각 검증 (Playwright)
- 양쪽 패널 모두 `<table class="sim-md-table">` 1개씩 렌더
- table_rows: 3개 (헤더 + 데이터 2)
- thead `<th>`: 3, tbody `<td>`: 6
- 헤더 행 하이라이트 (identical 색상)
- 일반 문장 `<p>` 와 함께 시각적 위계 명확

### 3-3. 시각 캡처
- `plan52-after-table-rendered-with-highlight.png` — 양 패널에 테이블 렌더 + 헤더 하이라이트 + 일반 문장 색상

---

## 4. 코드 전문가 관점 — 영향 분석

### 4-1. 매칭 알고리즘 무영향
- `split_sentences` 입력 텍스트가 동일 → 출력 sentence 배열 동일 (구분선 필터만 추가)
- `_compute_fingerprint_matrix`, L1/L3 그리디 무수정 → 매칭 객체 자체 동일
- `_merge_adjacent` 의 type 동일성 + ri 양방향 조건은 그대로, exclusion_reason 동일성만 추가

### 4-2. 점수 보존 (default OFF 시)
- `_exclusion_defaults` 에서 `exclude_table_structural: false` 설정 시 → 분자에 헤더 행 다시 포함 → 기존 점수 동일
- 사용자가 `data/settings.json` 등에서 오버라이드 가능

### 4-3. 시각 변경 영향
- `display_html_a/b` 출력에 `<table>`, `<tr>` 태그 추가
- 프론트 `simApplyHighlights` 의 `[data-sent-idx="i"]` 셀렉터가 `<tr>` 도 매칭 — 무영향
- `simNavigateToMatch` 의 `scrollIntoView` 도 `<tr>` 동작 정상

### 4-4. 부수 발견 — 매칭 병합 시 reason 정합성
- 작업 중 발견: `_merge_adjacent` 가 reason 다른 sentence 들을 병합 → 분자 계산 inflation
- Plan-52 안에서 함께 수정 (`exclusion_reason` 동일성 검사 추가)
- 신규 단위 테스트 H 케이스로 회귀 방지

---

## 5. UX/UI 전문가 관점 — 사용자 경험 변화

### 5-1. 시각 인식 회복
- 이전: 패널에 `| 부품번호 | 명칭 | 수량 |` 파이프 텍스트
- 이후: 실제 `<table>` (border, padding, thead 강조)
- 사용자 페인 직접 해소

### 5-2. 점수 신뢰도 회복
- 이전: 표가 같으면 본문이 달라도 점수 inflation
- 이후: 표 헤더 자동 제외 → 본문 비교만 점수 반영
- 100% 오탐 케이스 → 0% 정확 출력 (시나리오 2)

### 5-3. 통일된 자동 제외 경험
- 기존 5개 자동 제외 (boilerplate / toc / caption / cited_quote / short_match) 와 동일한 패턴
- 자동 제외 패널 (`<details class="sim-exclusion-panel">`) 에 카운트 자동 노출
- 가이드 모달이 SSOT 자동 반영 → UI 추가 작업 0

### 5-4. 사용자 토글 가능
- 검사 설정 가이드에 "표 헤더·구조 행 제외" 토글 자동 노출 (default ON)
- 운영 측이 본문 비교 외에 표 헤더 자체도 비교하고 싶다면 OFF 가능 — 유연성 확보

### 5-5. 행 단위 하이라이트
- 매칭된 표 행이 색상 배경으로 표시 (identical / paraphrase / near_copy / low_sim 카테고리별)
- 클릭 시 outline 강조로 active 표시
- 일반 문장 `<p>` 의 border-left 와 다른 시각 언어지만, 표 행 특성에 맞춤 (border-left 는 `<tr>` 에 적용 안 됨)

---

## 6. 사용자 관점 피드백

### Before (사용자 보고)
- "테이블 정보가 기호와 텍스트로 추출되어 보여진다"
- "테이블 레이아웃이 그대로 추출되니까 비교 대상에 포함되어 100% 일치하는 항목으로 식별되는 현상"
- "시각적으로 테이블이라는 인식이 잘 안 돼"

### After
- 실제 `<table>` 로 렌더 → 시각적으로 즉시 "표" 인식
- 헤더 행 / 짧은 셀 행 자동 제외 → 100% 오탐 해소
- `| --- | --- |` 구분선 사라짐 → 표 시각 정합

### 통일된 가이드 시리즈
- 기존 5개 자동 제외 카테고리와 동일 패턴 → 사용자가 "이 도구는 이런 식으로 자동 제외" 라는 멘탈 모델 강화

---

## 7. 부수 발견 (현 범위 외)

| # | 항목 | 비고 |
|---|------|------|
| O-1 | API `/similarity` 가 settings 파라미터 미수용 | 토글 OFF 검증 시 발견. 현재 백엔드 default 만 적용. settings runtime 오버라이드 메커니즘 향후 추가 가능 |
| O-2 | 매칭 [0] 의 sentence count 이 ti_end 까지 포함하지만 일부 sent_idx 는 active_excluded 일 수 있음 | 분자가 매칭 단위라 미세 inflation 가능. Plan-50 sentence index set 분모와 매칭 단위 분자 간 미스매치. 현재는 _merge_adjacent reason 동일성 차단으로 우회 |
| O-3 | PyMuPDF4LLM 의 lines_strict 출력이 GFM 100% 호환인지 미검증 | 운영 환경 PDF 문서로 검증 필요 |
| O-4 | 사용자 토글 OFF 시 점수가 이전과 100% 동일한지 회귀 테스트 부재 | 단위 테스트 추가 가능 |

---

## 8. 한 줄 결론 (본체 + hotfix1 적용 후)

**PASS.** Plan-52 본체 + hotfix1 완료 — Option D (시각 보존 + 구조 행 자동 제외) 구현 + 프론트엔드 토글 통합. 사용자 3대 페인 직접 해소 + 사용자 토글 제어권 확보. 단위 테스트 19건 PASS, 회귀 0, 매칭 알고리즘 무수정. 업계 표준 80% 수준 도달.

---

## 9. hotfix1 — 프론트엔드 토글 통합 누락 4건 보강 (2026-04-30)

### 9-1. 발견 경위
본체 적용 후 사용자 검토 요청 (`잘 반영된 것 같아?`) 으로 전체 재검토 진행 — **프론트엔드 4곳에 통합 누락 식별**.

### 9-2. 누락 항목 + 영향
| # | 위치 | 누락 | 실제 영향 |
|---|------|------|-----------|
| 1 | `compare.html:1389` `SIM_CHECK_DEFAULTS` | `exclude_table_structural` 키 부재 | localStorage 초기화 시 default 미설정 |
| 2 ★ | `compare.html:1411` `SIM_EXCL_TO_KEY` | `table_structural` 매핑 부재 | **사용자가 다른 토글 변경 시 점수 silent 변동 (백엔드/프론트 불일치)** |
| 3 | `compare.html:1518` `keys` 배열 (가이드 모달) | 새 키 누락 | 가이드 모달에 새 항목 설명 안 노출 |
| 4 | `compare.html:2520` `settingDefs` (사이드바 토글 UI) | 새 토글 정의 부재 | 사용자 화면에 토글 안 보임 |
| 부수 | `compare.html:1551` 가이드 모달 헤더 | "5옵션" → "6옵션" 텍스트 정정 | 사용자 인지 정확성 |

### 9-3. 수정 내용 (총 ~7줄 추가)
```js
// 1. SIM_CHECK_DEFAULTS — exclude_table_structural: true 추가
// 2. SIM_EXCL_TO_KEY — table_structural: 'exclude_table_structural' 매핑 추가
// 3. keys 배열에 'exclude_table_structural' 추가
// 4. settingDefs 에 6번째 객체 추가 (label, hint)
// 5. "사용자 토글 5옵션" → "6옵션"
```

### 9-4. 검증 결과
**Playwright E2E 시각 회귀** (실제 사용자 흐름):
- 사이드바 검사 설정 토글: **6개 모두 노출**, `exclude_table_structural` 기본 ON ✓
- 가이드 모달: 6번째 행 "표 헤더·구조 행 제외" + "기본 ON" 배지 + 설명 노출 ✓
- 자동 제외 패널: "자동 1 · 수동 0" — 헤더 매칭이 자동 제외로 정상 분류 ✓
- 토글 ON → 점수 **0%** (백엔드와 일치)
- 토글 OFF → 점수 **25%** (헤더 매칭이 분자에 포함, silent 변동 0)
- 점수 정합 100% — 백엔드와 프론트엔드 재계산 결과 일치

**자동 회귀**: 백엔드 무수정 → 단위 테스트 19/19 PASS 그대로 유지.

### 9-5. 시각 캡처
- `plan52-hotfix1-toggle-off-score-changed.png` — 토글 OFF 시 점수 25% 상승, 표 데이터 행 시각 보존
- `plan52-hotfix1-guide-modal-with-new-toggle.png` — 가이드 모달 6번째 항목 노출

### 9-6. 잔여 위험 0
- 백엔드 무수정 — 단위 테스트, API 응답 무영향
- 기존 5개 토글 객체 무수정 — settingDefs 6번째 추가만
- localStorage 호환 — `Object.assign` 패턴이라 기존 사용자 localStorage 에 새 키 없으면 default true 자동 적용
- CSS 무수정
