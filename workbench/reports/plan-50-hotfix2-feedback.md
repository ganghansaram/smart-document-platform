# Plan-50 hotfix2 — 가이드 모달 타이포그래피 정합

> 작성일: 2026-04-30
> 변경 범위: `css/compare.css` (sim-help-* 영역), `compare.html` (inline 폰트 1건)
> 검증: 자동 회귀 + Playwright 3 모달 시각 검증

---

## 1. 배경

3개 가이드 모달 (점수·등급, 검사 설정, 매칭 유형) 의 본문 텍스트가 caption(11px)·tiny(10.5px) 위주로 짜여 있어 가독성 저하. 특히 매칭 유형 가이드의 `code` 태그가 `0.85em` 비율 곱셈으로 **10.2px** 까지 떨어져 핵심 임계값 (예: `fp ≥ 85%`) 가 거의 못 읽히는 상태.

코드 토큰 자체는 잘 활용 중이었으나 **모달 본문에 너무 작은 등급의 토큰을 적용한 매핑 자체** 가 페인의 근본 원인.

---

## 2. 변경 항목 (4 카테고리)

### 2-1. 폰트 매핑 정합 (`css/compare.css`)

| 영역 | 셀렉터 | 변경 (현재 → 새 매핑) |
|------|--------|---------------------|
| 산식 박스 | `.sim-help-formula` | caption 11px → **body 13px** |
| 산식 근거·검증 | `.sim-help-formula-basis` | tiny 10.5px → **caption 11px** |
| 표 base | `.sim-help-bands` | small 12px → **body 13px** |
| 표 헤더 | `.sim-help-bands th` | caption 11px → **small 12px** |
| **`.sim-help-bands code`** ★ | (위와 동일) | **0.85em (10.2px) → caption 11px (절대값 고정)** |
| 라벨 셀 | `.sim-help-label-cell` | caption 11px → **small 12px** |
| 변수 ul | `.sim-help-vars` | small 12px → **body 13px** |
| 인트로 | `.sim-help-intro` | small 12px → **body 13px** |
| 면책 박스 | `.sim-help-disclaimer` | caption 11px → **small 12px** |
| 색상 배지 | `.sim-help-band-badge` | caption 11px (유지) |

### 2-2. 모달 폭 + 표 padding
- `.sim-help-modal .modal-box` — 580 → **640px** (점수·등급, 검사 설정)
- `.sim-label-help-modal .modal-box` — 신규 **720px** (매칭 유형 5컬럼 분기)
- 표 padding `6px 10px` → **`8px 12px`** (폰트 ↑ 동반)

### 2-3. 매칭 유형 표 컬럼 wrap 정책
- 1번 (유형 라벨): `nowrap`
- 2~3번 (어휘·의미): 기존 `nowrap` 유지
- 4번 (설명): `min-width: 160px`, wrap 허용
- 5번 (임계값): `max-width: 200px`, code 자체 자연 줄바꿈
- code 의 `word-break: keep-all; overflow-wrap: break-word` — 단어 단위 자연 wrap

### 2-4. compare.html inline 폰트 제거
- 검사 설정 모달 안내 p — `style="font-size:var(--font-small)..."` inline → CSS 클래스 `.sim-help-section-note` 신설

---

## 3. 영향 분석 (코드 전문가 관점)

### 3-1. 격리 (다른 모달 영향 0)
모든 변경이 `.sim-help-modal` (또는 자식 클래스 `.sim-label-help-modal`, `.sim-check-help-modal`) 한정 셀렉터. `sim-excl-reason-modal`, `similarity-report-options` 등 다른 모달은 무영향.

### 3-2. 토큰 자체 보존
- `tokens.css` 의 `--font-*` 정의는 무수정
- 매핑 (어느 영역에 어느 토큰) 만 변경 — 시스템 전반 영향 0

### 3-3. code 비율 곱셈 → 절대값 토큰 전환
- 부모 사이즈 변경 시 자식이 따라 작아지는 종속성 끊음
- 향후 td 폰트 변경해도 code 는 caption 11px 고정 유지

### 3-4. 줄바꿈·잘림 안전망
- 매칭 유형 가이드 (가장 dense 5컬럼) 에서 가로 스크롤 0 확인
- 짧은 임계값 (`fp ≥ 85%`) 한 줄, 긴 임계값 (`fp < 10% + sem ≥ 0.75 + 다른 스크립트`) 자연 3줄 wrap
- 폭 720px max-width 로 safari·chrome 모두 안전 (1280×800 viewport 검증)

---

## 4. 영향 분석 (UX/UI 전문가 관점)

### 4-1. 정보 위계 보존
폰트를 균일 상향이 아니라 **차등 상향**으로 위계 유지:
- 산식 (가장 핵심): caption → body (+2px)
- 표 데이터·인트로·변수 (주요): small → body (+1px)
- 표 헤더·면책·라벨 (보조): caption → small (+1px)
- 색상 배지 (시각 요소): caption 유지

### 4-2. 사용자 시선 흐름
- **F-패턴 첫 진입** (산식 박스) 가 가장 큰 사이즈 — 핵심 정보 강조
- 표 헤더는 데이터보다 작아 **계층 인지** 자연스러움
- 면책 박스는 본문보다 작지만 11→12 상향으로 **신뢰 강조 정보의 가독성** 보장

### 4-3. 접근성 (WCAG)
- 가장 작은 텍스트 11px (caption·근거·배지 등) — WCAG AA 최소 충족 + 지원 가능 영역
- 본문 정보 컨텐츠 13px — 사용자 줌 없이 읽기 가능
- 시각 약자·고령 사용자 부담 완화

### 4-4. line-height 동반 조정
- 표 셀 padding 8/12 (이전 6/10) — 폰트 ↑ 동반 호흡감 확보
- 매칭 유형 5번 컬럼 line-height 1.5 명시 — 여러 줄 wrap 시 시각 안정

---

## 5. 검증 결과

### 5-1. 자동 회귀
| 검사 | 결과 |
|------|------|
| `tests/sim_label_consistency.sh` | ✅ PASS |
| `tests/sim_score_v3_unit_test.py` | ✅ 5/5 PASS |

### 5-2. Playwright 3 모달 시각 검증

**점수·등급 기준 모달**
- 폭: **640px** ✓
- 산식 박스: **13px** (이전 11px)
- 산식 근거·검증: **11px** (이전 10.5px)
- 표 데이터: **13px** (이전 12px)
- 변수 ul: **13px** (이전 12px)
- 면책: **12px** (이전 11px)

**검사 설정 가이드 모달**
- 폭: **640px** ✓
- 안내 p (`.sim-help-section-note`): **13px** ✓
- 표 데이터: **13px** ✓
- inline 폰트 제거 → CSS 클래스 적용 정합

**매칭 유형 가이드 모달** (5컬럼 가장 까다로움)
- 폭: **720px** (별도 분기) ✓
- 표 데이터 (td): **13px** ✓
- code (임계값): **11px** ✓ (이전 10.2px)
- 라벨 셀: **12px** (이전 11px)
- **가로 스크롤 0** (bodyScrollWidth = bodyClientWidth = 720)
- 짧은 임계값 한 줄, 긴 임계값 (예: `fp < 10% + sem ≥ 0.75 + 다른 스크립트`) 자연 3줄 wrap

### 5-3. 시각 캡처
- `modal-label-fixed.png` — 매칭 유형 가이드 (5컬럼 정합)
- `modal-score-after.png` — 점수·등급 기준
- `modal-check-after.png` — 검사 설정 가이드

---

## 6. 사용자 관점 피드백

### 페인 해소
**Before** (사용자 지적):
- "산식이 작아서 안 봄"
- "임계값 (`fp ≥ 85%`) 안 읽힘 — 학습 포기"
- "면책 문구 너무 작아 무시한 느낌"

**After**:
- 산식 13px → 핵심 정보 즉시 인지
- 임계값 11px (이전 10.2) + 자연 줄바꿈 → 모든 행 가독성 회복
- 면책 12px → 신뢰 강조 정보 충분히 인지

### 통일된 경험
- 3개 가이드 모달이 **동일한 폰트 매핑 + 동일한 폭 정책** 으로 통일감
- 표·인트로·면책·산식의 위계가 일관 → 사용자가 "이 모달 시리즈" 로 인지

---

## 7. 부수 발견 (현 범위 외)

| # | 항목 | 비고 |
|---|------|------|
| O-1 | 다른 모달 (sim-excl-reason, similarity-report-options) 도 같은 토큰 사용 — 페인 미보고 | 일관성 측면 후속 적용 가능. 사용자 의사 확인 필요 |
| O-2 | 사이드바 indicator·점수 카드 외 영역 작은 폰트 | 모달 외 영역은 사용자 페인 미보고 — 별건 |
| O-3 | line-height 일부 영역 (산식 1.6 / 면책 1.55) 미세 차이 | 가독성 큰 영향 없음, 후속 미세조정 가능 |

---

## 8. 한 줄 결론

**PASS.** Plan-50 hotfix2 완료 — 3개 가이드 모달 폰트 매핑 정합 + 모달 폭 조정 + 표 컬럼 wrap 정책 + code 비율 곱셈 폐기. 사용자 페인 (산식·임계값·면책 가독성) 직접 해소. 토큰 시스템 보존, 다른 모달 영향 0, 매칭 유형 5컬럼 가로 스크롤 0. 자동 회귀 + Playwright 시각 검증 모두 통과.
