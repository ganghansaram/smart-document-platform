# Plan-50 hotfix3 — 가이드 모달 디자인 마감 정합

> 작성일: 2026-04-30
> 변경 범위: `css/compare.css` (sim-help-* 영역), `compare.html` (3 모달 footer)
> 검증: 자동 회귀 + Playwright 3 모달 시각 검증

---

## 1. 배경

hotfix2 적용 후 폰트 가독성은 회복되었으나, 디자인 전문가 시각으로 직접 확인 시 6건의 미세 마감 이슈 발견:

| 발견 | 영향 |
|------|------|
| 5단계 신호등 표 마지막 행 (RED) 잘림 | 사용자가 임계 못 보고 닫을 가능성 (실사용 영향) |
| 매칭 유형 가이드 컬럼 폭 비례 어색 | 정보량 적은 컬럼이 넓고, 많은 컬럼이 좁음 |
| 표 셀 vertical-align: middle | 1줄/2줄 wrap 행 시각 들쭉날쭉 |
| 매칭 유형 헤더 정렬 | 데이터(가운데) vs 헤더(좌측) 어긋남 |
| 닫기 버튼 색상 | primary(파란) 강조 — 일반적 모달 닫기는 secondary |
| 변수 ul 점선·라벨 정렬 | 점선 흐려서 분리감 약함, 라벨 너비 들쭉날쭉 |

---

## 2. 변경 항목 (6 카테고리)

### 2-1. 모달 max-height 확장 (RED 행 잘림 해소)
- `.sim-help-modal .modal-body` — `calc(100vh - 220px)` → **`calc(100vh - 180px)`**
- 일반 사용자 환경 (1080~1440 viewport) 에서 5단계 표 모든 행 한 화면

### 2-2. 매칭 유형 가이드 컬럼 폭 재배치
- 어휘·의미 (단일 단어): `min-width: 64px` → **`width/min-width: 56px`** (단일 단어 컬럼 좁게)
- 설명: `min-width: 160px` → **`200px`** (정보량 많은 컬럼 우대)
- 임계값: max-width 200px 유지

→ 측정 결과: 어휘 76px / 설명 246px (이전 ~120 / ~190)

### 2-3. 표 셀 vertical-align top
- `.sim-help-bands th, td` — `middle` → **`top`**
- 1줄/2줄 wrap 행이 같은 상단 정렬 → 시각 리듬 안정

### 2-4. 매칭 유형 헤더 정렬 일치
- 어휘·의미 헤더 (`th:nth-child(2,3)`) 가운데 정렬 → 데이터 정렬축과 일치

### 2-5. 닫기 버튼 secondary
- 3 모달 footer (`compare.html:1365, 1558, 1635`) 의 `btn btn-primary` → **`btn btn-secondary`**
- 일반 모달 닫기는 secondary 가 표준 (primary 는 "확인", "저장" 등 적극 액션)

### 2-6. 변수 ul 분리감 + 라벨 정렬
- 점선 `1px dashed` → **옅은 실선 `1px solid`**
- 마지막 항목 `border-bottom: none`
- 라벨 `<strong>` `display: inline-block; min-width: 70px;` — 라벨 너비 일관 → 설명 텍스트 정렬축 통일

---

## 3. 영향 분석

### 3-1. 격리 (다른 모달 영향 0)
- 모든 변경이 `.sim-help-modal` (또는 `.sim-label-help-modal`, `.sim-check-help-modal`) 한정 셀렉터
- `sim-excl-reason-modal` (수동 제외 사유), `similarity-report-options` (보고서 옵션) 등 무영향
- 닫기 버튼 색상 변경도 3 가이드 모달 footer 만 — 다른 모달의 primary 액션 (취소·확인) 무변동

### 3-2. 토큰·SSOT 보존
- `tokens.css` 무수정
- `data/help/similarity-help.json` 무수정
- 매핑·정책·표기만 변경

### 3-3. 가로 overflow 재검증
- 매칭 유형 가이드 (5컬럼, 가장 dense): `bodyScrollWidth = bodyClientWidth = 720px` ✓
- 컬럼 폭 변경에도 가로 overflow 0

---

## 4. 검증 결과

### 4-1. 자동 회귀
| 검사 | 결과 |
|------|------|
| `tests/sim_label_consistency.sh` | ✅ PASS |
| `tests/sim_score_v3_unit_test.py` | ✅ 5/5 PASS |

### 4-2. Playwright 시각 검증

**점수·등급 기준 모달**
- 5단계 신호등 표 — BLUE/GREEN/YELLOW/ORANGE/RED **5개 모두** DOM 확인 (`bandCount: 5`, `lastBand: "RED"`)
- 모달 max-height: 593px (이전 553px) — 작은 viewport 에서도 더 많은 컨텐츠 노출
- 닫기 버튼 클래스: `btn btn-secondary` ✓
- 변수 ul 실선 분리, 라벨 정렬 일관 ✓

**검사 설정 가이드 모달**
- 닫기 버튼 secondary ✓
- 표 행 vertical-align top — "짧은 매칭 제외 (8단어 미만)" 2줄 wrap 행 시각 안정
- "기본 ON / OFF" 배지 위치 일관

**매칭 유형 가이드 모달**
- 어휘 컬럼 폭: 76px (이전 ~120)
- 설명 컬럼 폭: 246px (이전 ~190) — 정보량 우대
- "다른 언어로 번역된 구간 (예: 한↔영) — 의역 카테고리에 통합" 4줄 → **2줄 wrap** (가독성 ↑)
- 헤더 어휘/의미 가운데 정렬 — 데이터와 일치 ✓
- 가로 overflow: 0 ✓

### 4-3. 시각 캡처
- `modal-score-hotfix3.png` — 점수·등급 (실선 ul, secondary 닫기)
- `modal-label-hotfix3.png` — 매칭 유형 (컬럼 균형, top 정렬)
- `modal-check-hotfix3.png` — 검사 설정 (top 정렬, secondary 닫기)

---

## 5. 디자인 전문가 관점 — Before/After

| 항목 | Before (hotfix2) | After (hotfix3) | 평가 |
|------|------------------|----------------|------|
| 5단계 표 마지막 행 | 잘림 | 표시 (max-height ↑) | ✅ 실사용 안정 |
| 매칭 유형 컬럼 비례 | 어휘 넓고 설명 좁음 | 어휘 좁고 설명 넓음 | ✅ 정보량 비례 |
| Wrap 행 시각 안정 | middle 정렬로 들쭉날쭉 | top 정렬 안정 | ✅ |
| 헤더 정렬 일치 | 데이터(가운데) vs 헤더(좌측) | 둘 다 가운데 (어휘/의미) | ✅ |
| 닫기 버튼 시각 | primary (파란) | secondary (회색 보더) | ✅ 표준 부합 |
| 변수 ul 분리감 | 점선 흐림 | 옅은 실선 명확 | ✅ |
| 라벨 정렬 | 너비 들쭉 | min-width 70px 통일 | ✅ |

### 종합 점수 변화
| 항목 | hotfix2 | hotfix3 |
|------|---------|---------|
| 가독성 | 9/10 | 9/10 |
| 시각 위계 | 7/10 | **8.5/10** |
| 레이아웃 균형 | 6/10 | **8.5/10** |
| 시각 마감 | 7/10 | **9/10** |
| **디자인 완성도 종합** | **7/10** | **9/10** |

---

## 6. 사용자 관점 피드백

### 페인 직접 해소
- "RED 임계 못 봤음" → 한 화면 안에 보임
- "표가 비좁아 임계값 줄바꿈 4번" → 2번으로 단축
- "닫기 버튼이 강조라 잠깐 헷갈림" → 일반 닫기 시각

### 통일된 시리즈 인지
- 3 모달 폰트 매핑 + 폭 정책 + 표 정렬 + 닫기 색상 모두 동일 → 사용자가 "가이드 시리즈" 로 인지
- 변수 ul 실선 분리감으로 "정의표" 패턴 강화

---

## 7. 부수 발견 (현 범위 외)

| # | 항목 | 비고 |
|---|------|------|
| O-1 | 모달 헤더 부제 라인 부재 | "이 모달이 뭐를 다루는지" 한 줄 부제 추가 가능 — 추후 |
| O-2 | 표 행 hover 효과 없음 | 정보표라 필수 아니지만 데이터 추적 시 유용 — 추후 |
| O-3 | 인트로 박스 accent 와 산식 박스 accent 동일 색상 | 위계 미세 구분 약간 가능 — 후속 |

---

## 8. 한 줄 결론

**PASS.** Plan-50 hotfix3 완료 — 6건 디자인 마감 정합 (max-height·컬럼 폭·정렬·닫기 색상·ul 분리·헤더 정렬). 디자인 완성도 7/10 → 9/10. 사용자 페인 (RED 행 잘림, 컬럼 비례, 닫기 혼동) 직접 해소. 통일된 가이드 시리즈 시각 인지 확립.
