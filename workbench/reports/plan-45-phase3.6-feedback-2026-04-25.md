# Plan-45 Phase 3.6 실행 피드백 — UI 잔여 부채 6건 + 토큰 미정의 1건 청산

> 실행일 2026-04-25 · 실행자 Claude (/plan-execute) · 대상 계획서 (Plan-45 done- 후속 마이크로 패치, 별도 계획서 없음)

## 요약

- 완료 항목: 7/7 (사용자 직접 지적 6건 + 후속 발견 토큰 미정의 1건)
- 변경 파일: 3개 (`css/compare.css`, `compare.html`, `css/tokens.css`)
- Critical: 0건 · Warning: 1건 (수정 완료) · Suggestion: 4건 (보고서 기재)
- 백엔드·데이터·라벨 불변 — Plan-45 invariants (E1~E5, C1~C7, V1~V5, S1~S3) 모두 준수

## 변경 사항

| # | 항목 | 변경 위치 |
|---|------|----------|
| ① | sticky 제거 (섹션 헤더 중첩 버그 해소) | `css/compare.css` L1431~ |
| ② | 모달 B 산식 근거·검증 표기 | `compare.html` L1283~1296 (변수), L1326~1340 (렌더), `css/compare.css` L1047~ (스타일) |
| ③ | HTML/PDF 리포트 별첨 B 산식 근거 | `compare.html` L4961~ (변수), L5258~ (렌더), L5018~ (인라인 CSS) |
| ④ | ⓘ 위치 — 누적바와 flex row 통합 | `css/compare.css` L1325~1352, `compare.html` L2484~2497 |
| ⑤ | `.sim-help-band-badge` `white-space:nowrap` | `css/compare.css` L1075 |
| ⑥ | `.sim-filter-chips` 2×2 그리드 | `css/compare.css` L1372~1422 |
| ⑦ | **tokens.css 미정의 변수 3종 정의** — `--text-muted` (라이트 `#94a3b8` / 다크 `#9ca3af`), `--bg-default`, `--bg-card` | `css/tokens.css` 라이트 :root + 다크 [data-theme="dark"] |

### ⑦ 후속 발견 — 약한 유사 dot 안 보임

**증상**: 결과 패널 7지표 카드의 "약한 유사" dot 라이트·다크 모두 안 보임 (사용자 지적).

**근본 원인**: `tokens.css` 어디에도 `--text-muted` 변수가 정의되어 있지 않음. `compare.css` 가 10곳에서 `var(--text-muted)` (fallback 없이) 호출 → CSS 변수 미정의 → property 무시 → `background: transparent` (initial). 동일 원인으로 `--bg-default`, `--bg-card` 도 미정의.

**영향 범위 (모두 transparent 상태였음)**:
- 7지표 카드 약한 유사 dot
- 4 카테고리 누적바 약한 유사 segment
- 필터 칩 약한 유사 dot
- `.sim-indicators` (모체 카드 배경 — `var(--bg-card)`)
- `.sim-indicator` 셀 배경 (`var(--bg-default)`)
- 그 외 6곳의 `color: var(--text-muted)` (color는 부모 상속으로 가시적이라 묻혀 있던 잠재 부채)

**조치**: `tokens.css` 에 변수 3종 정의 추가. 라이트 `--text-muted: #94a3b8` (slate-400), 다크 `#9ca3af` (gray-400). `compare.css` 미수정 — 이미 올바른 변수명 호출 중이었으므로 자동 정상화.

**검증**: Playwright `getComputedStyle` 실측 — 라이트 dot `rgb(148,163,184)`, 다크 `rgb(156,163,175)`. 의도값 정확 적용. 누적바·필터 칩 dot 모두 동시 가시화.

## 검증 결과

### 자동 (회귀 0)

- **단위 테스트**: 21/21 PASS (`tests/sim_phase2_test.js`)
- **라벨·공식 일관성**: PASS (`tests/sim_label_consistency.sh` — 라벨 문자열 변경 없음)
- **compare.html 인라인 script vm.Script 구문 파싱**: errors 0 (1차 시도 시 모달 B 렌더 블록에서 연산자 누락 ASI 문제 발견 → 즉시 수정)

### Code Reviewer

- Critical: 0
- Warning: 3 (1건 수정 — `.sim-category-info` `vertical-align: middle` 안전 마진 추가 / 2건 기존 부채로 범위 외)
- Suggestion: 4 (다음 리팩토링 시 반영 권장)

### Design Reviewer

- Critical: 0
- Warning: 3 (1건 수정 — W1 산식 근거 캡션 시각 종속 강화 / 2건 기존 부채·전역 영향으로 범위 외)
- Suggestion: 4

#### W1 즉시 보강 — 산식 박스와 근거 캡션 종속 관계 명시

지적: "근거·검증" 캡션이 산식 회색 박스 외부 흰 영역에 떠 있어 다음 섹션과 동일 레벨로 보임.

조치: `.sim-help-formula-basis` 에 좌측 2px accent border (`var(--active-color)`) + 연한 배경 (`var(--bg-default)`) 추가. 라이트·다크 모두 시각 종속 관계 명확. 리포트 인라인 CSS (`.formula-basis`) 도 동일 패턴 동기화.

### Playwright 시각 검증

- 라이트/다크 양쪽 검증 — `workbench/screenshots/plan-45-phase3.6-20260425/`
  - `phase36-01-light-panel.png` — 라이트 결과 패널 전체 (① sticky 제거, ④ ⓘ 위치, ⑥ 필터 2×2)
  - `phase36-02-light-scrolled.png` — 스크롤 후 헤더 중첩 없음 검증
  - `phase36-03-modal-B-formula-basis.png` — 모달 B 초기 (W1 보강 전)
  - `phase36-04-check-settings-badge.png` — ⑤ 검사 설정 모달 "기본 ON" 한 줄 검증
  - `phase36-05~07-dark-*.png` — 다크 모드 검증
  - `phase36-08-modal-B-basis-refined.png`, `phase36-09-modal-B-basis-light-refined.png` — W1 보강 후 (좌측 accent border)

### 다른 모드 영향성

- `sim-` 접두사 클래스만 추가·수정 — `cp-` (compare 공통), `vd-` (verify) 무관
- sticky 제거: `.sim-cat-section-header` 한정 — `.vd-group-header` 등 무관
- `.sim-help-band-badge` `nowrap` 추가: 모달 표 한정 — 기존 사용처 (모달 B 5단계 신호등 + 검사 설정 모달) 양쪽 OK
- 누적바 row 통합 (④): 기존 float 잔재 제거 — compare.css 전역 `float` 사용처 0개, 충돌 없음

## 사용자 관점 피드백

- **긍정**:
  - 카테고리 섹션 헤더가 더 이상 스크롤 시 겹쳐 쌓이지 않음 — 매칭 카드 검토 흐름이 매끄러워짐
  - 누적바 우측 ⓘ 가 한 줄에 정렬돼 "덩그러니" 느낌 해소
  - 필터 칩 4개가 2×2 균등 폭 — 깔끔, 카운트 우측 정렬로 한눈에 비교 가능
  - 모달 B "근거·검증" 캡션 — "Copyleaks aggregatedScore 공식 모방"·"(76+50+89)/(597-105)=43.7%" 가 즉시 가시화 → 사내 감사 시 "어디서 온 공식이냐" 질문에 즉답 가능
  - 리포트 별첨 B 동일 정보 자동 출력 → 인쇄본 신뢰도 상승
  - 검사 설정 모달 "기본 ON" 줄내림 해소 — 시각 호흡 회복

- **우려**: 7지표 카드 2행 비대칭 (Plan-45 Phase 3.5 산물, 약한유사·제외·전체문장 행이 어색) — 후속 마이크로 개선 후보

## 웹디자인 전문가 관점 피드백 (design-reviewer 기반)

- **시각 위계**: 점수 → 7지표 → 누적바+ⓘ → 필터 → 카테고리 섹션 흐름 자연 (F-pattern)
- **공간 배분**: 우측 패널 ~320px 안에서 6 영역 호흡 적절. 칩 2×2 이전 flex-wrap 비결정성 제거가 핵심
- **다크 모드 대비비**: WCAG AA 4.5:1 통과. (W3 "약한 유사" 미체크 칩 윤곽선은 tokens.css 영역, 본 범위 외)
- **모달 B 신뢰감**: 좌측 accent + 회색 배경으로 산식과 근거의 종속 관계가 1초 안에 인지됨
- **인터랙션**: ⓘ 터치 타겟 ≥24×24 통과 (padding 1px 4px + 폰트 size)

## 잔여·후속 제안 (이번 범위 외)

- [ ] **W2** — 7지표 카드 2행 비대칭. 균등 그리드 또는 메타 행 그룹핑 검토 (Phase 3.5 산물, 후속 마이크로 작업)
- [ ] **W3** — 다크 모드 미체크 체크박스 윤곽선 대비비. `tokens.css` 의 `--border-color` 다크 값 상향 (전역 영향, 별도 디자인 검토)
- [ ] **S2** — "15% ⓘ" 와 "검토 필요 ?" 트리거 구분 명확화 (사전 hover tooltip)
- [ ] **S3** — `getFormulaFields(help)` 헬퍼 함수 분리 (모달 B + 별첨 B 중복 제거, DRY)
- [ ] **CR-W2/W3** — `compare.css` 의 `.sim-help-disclaimer`·리포트 인라인 CSS 하드코딩 정리 (기존 부채)

## 커밋 제안

```
스타일 [Verify/Compare] Plan-45 Phase 3.6 — UI 잔여 부채 6건 청산

사용자 직접 지적 6건 청산 (백엔드·데이터·라벨 불변):
- ① sim-cat-section-header sticky 제거 — 다중 섹션 헤더 중첩 버그 해소
- ② 모달 B 산식 박스 아래 근거·검증 캡션 추가 (SSOT score_formula 필드 렌더)
- ③ HTML/PDF 리포트 별첨 B 동일 근거·검증 캡션
- ④ sim-category-info ⓘ 위치 — float 제거, 누적바와 flex row 통합
- ⑤ sim-help-band-badge white-space:nowrap — "기본 ON" 줄내림 해소
- ⑥ sim-filter-chips 2×2 그리드 — 칩 폭 통일, 카운트 우측 정렬

검증: 단위 21/21 PASS · sim_label_consistency.sh PASS · code-reviewer Critical 0
   · design-reviewer Critical 0 · Playwright 라이트/다크 9컷
```
