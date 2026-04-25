# Plan-47 실행 피드백 — 모달 A·B 마감 정리

> 실행일 2026-04-25 · 실행자 Claude (/plan-execute) · 대상 계획서 `workbench/plans/47-modal-AB-refinement.md`

## 요약

- 완료 Step: 3 + 검증 보강 1 = 4/4
- 변경 파일: 3 (`css/tokens.css`, `css/compare.css`, `compare.html`)
- Critical: 0 · Warning: 5건 (1건 즉시 반영, 4건 후속) · Suggestion: 7건
- Plan-45 invariants (E1~E5, C1~C7, V1~V5, S1~S3) 모두 준수, 백엔드·데이터·라벨 불변

## 변경 사항

| Step | 항목 | 위치 |
|------|------|------|
| 1 | `--font-tiny: 10.5px` 토큰 신설 | `css/tokens.css` L94 + 라이트·다크 동일 주석 |
| 1 | `.sim-help-formula` 좌측 3px accent + weight 600 + color (시각 무게 강화) | `css/compare.css` L1038~ |
| 1 | `.sim-help-formula-basis` font-tiny + border-color 보더 (위계 정상화) | `css/compare.css` L1048~ |
| 2 | `.sim-label-help-modal .sim-help-bands` 어휘·의미 컬럼 nowrap + min-width 64px | `css/compare.css` L1136~ |
| 2 | 리포트 `.types-table` th/td:nth-child(2,3) nowrap + min-width 50px | `compare.html` L4985, L5240 |
| 3 | 모달 A SVG 60줄 제거 + `.sim-help-intro` 한 줄 텍스트 | `compare.html` L1570~1628 |
| 3 | 인트로 박스 3px accent + 강조 단어 active-color (W3 보강) | `css/compare.css` L1136~ |
| 1 | 리포트 `.formula` weight 600 + 좌측 3px accent · `.formula-basis` 옅은 border | `compare.html` L4981~4984 |

## 검증 결과

### 자동 (회귀 0)
- 단위 테스트 21/21 PASS
- `tests/sim_label_consistency.sh` PASS
- compare.html vm.Script 구문 errors 0

### Playwright 실측

| 모달 | 항목 | 측정값 | 판정 |
|------|------|-------|------|
| B | 산식 폰트 | 11px Consolas weight 600, border-left 3px rgb(44,82,130) | ✅ |
| B | 근거 폰트 | 10.5px sans-serif, border-left 2px rgb(221,228,232) | ✅ 위계 정상 |
| A | 어휘 컬럼 td | 68px nowrap | ✅ 한 줄 |
| A | 의미 컬럼 td | 64px nowrap | ✅ 한 줄 |
| A | 인트로 박스 | 3px accent + active-color 강조 (W3 후) | ✅ 본 정보 명시 |

스크린샷 5컷: `workbench/screenshots/plan-47-20260425/`

### code-reviewer

- Critical 0 / Warning 3 / Suggestion 3
- Warning 모두 리포트 인라인 CSS 하드코딩 (구조적 한계 — `window.open` 새 창은 tokens.css 미참조). 즉시 반영 부적절, backlog
- S1 (tokens.css 폰트 라이트·다크 동일 주석) → 즉시 반영 ✅

### design-reviewer

- Critical 0 / Warning 4 / Suggestion 3
- **W3 즉시 반영 ✅** — 모달 A 인트로 박스가 본 정보임을 시각화: 좌측 2px 회색 → 3px active-color, 강조 단어도 active-color로 격상. 모달 B 산식과 일관된 "본 정보 = 파란 3px accent / 보조 = 회색 2px" 규칙 성립
- W1, W2, W4 후속 폴리싱 후보로 보고서에 기재 (사소·선택적)

## 사용자 관점 피드백

- **긍정**:
  - 모달 B 산식이 한눈에 본 정보로 인식됨 — 좌측 파란 막대 + 굵은 글자 + 적절한 폰트 사이즈 위계
  - 근거·검증이 보조 캡션으로 명확히 종속 — 폰트도 작고 border도 옅음
  - 모달 A 다이어그램 사라지고 표가 viewport 안에 모두 들어옴 — 스크롤 없이 한 화면 파악, 표가 정보 핵심임이 자명
  - 표 어휘/의미 컬럼 한 줄 처리 — "매우 높음", "거의 0" 모두 자연스러움. 이전 "의"/"미" 세로 분리 해소
  - 인트로 한 줄 텍스트 — 학술적 톤 제거, 일반 사용자 친화 ("Winnowing fingerprint" 같은 전문 용어 사라짐)
  - PDF 출력도 모달과 일관 (산식 굵은 글자 + accent, 표 컬럼 nowrap)

- **우려**: 없음 (이전에 다이어그램이 익숙했던 개발자 입장에서는 "정보가 줄어든 느낌"이 있을 수 있으나, 표가 동일 정보를 더 정확히 전달)

## 웹디자인 전문가 관점 피드백 (design-reviewer 기반)

- **시각 위계 일관성**: 모달 A·B 모두 "본 정보 = 3px active-color + 큰 폰트 / 보조 = 2px border-color + 작은 폰트" 규칙 성립
- **공간 효율**: 모달 A 다이어그램 320px 제거 → 표가 viewport 안에 들어옴, 스크롤 0
- **모달 폭 일관성** (S1 후속 후보) — 모달 A는 720px 명시, 모달 B는 default `.modal-box` 폭에 의존. 두 모달은 ⓘ에서 즉시 교차 호출되므로 폭 통일이 시선 잔상 감소에 기여 가능
- **다크 모드 대비비**: 라이트·다크 양쪽 모두 WCAG AA 4.5:1 통과 (산식 본문 weight 600 더 안전)
- **인트로 박스 W3 후 효과**: 다이어그램 부재가 어색하지 않음. "이게 본 분류 원리 설명"임을 1초 안에 인지

## 잔여·후속 제안 (이번 범위 외)

- [ ] **DR-W1** — 라이트 모드 산식 좌측 accent를 box-shadow inset 으로 더 두껍게 보강
- [ ] **DR-W2** — 근거 캡션 orphan 줄바꿈 — `text-wrap: pretty` (modern browser) 또는 `&nbsp;` 결속
- [ ] **DR-W4** — 어휘/의미 컬럼 min-width 64→56px 검토 (`—` 단독 row 공백 부담 완화)
- [ ] **DR-S1** — 모달 A·B 폭 통일 (`.sim-help-modal .modal-box max-width: 720px`)
- [ ] **CR-W1** — 리포트 인라인 CSS 의 `#2c5282` 분산 7곳을 JS 상단 `LIGHT_ACCENT` 상수로 일원화
- [ ] **CR-W3** — `.sim-help-label-identical` 등 6종 배지 색상 하드코딩 → 토큰 변환 (Plan-45 잔여 부채)

## 커밋 제안

```
스타일 [Verify/Compare] Plan-47 — 모달 A·B 마감 정리

Plan-45 Phase 3.6 후속 마이크로 패치 (사용자 추가 지적 2건 청산):
- 모달 B 산식 vs 근거 폰트 위계 정상화 — 산식 11px Consolas weight 600
  + 좌측 3px active accent / 근거 10.5px sans + 옅은 border
  (이전 산식 11px / 근거 12px 위계 역전 해소)
- --font-tiny 토큰 신설 (10.5px), 라이트·다크 동일 주석
- 모달 A 어휘·의미 컬럼 nowrap + min-width 64px (.sim-label-help-modal 한정)
- 모달 A 2축 다이어그램 SVG 60줄 제거 — 한 줄 sim-help-intro 텍스트로 대체
  (어휘 일치도 + 의미 유사도 두 축. 학술적 톤·다크모드 부조화 동시 해소)
- 인트로 박스 좌측 3px active accent (모달 B 산식과 일관성)
- 리포트 별첨 B types-table 동일 nowrap + 산식 박스 동일 패턴
- 온보딩 안내 문구 "(2축 다이어그램)" → "(매칭 유형 6종 정의표)" 동기화

검증: 단위 21/21 PASS · sim_label_consistency.sh PASS · vm.Script errors 0
   · code-reviewer Critical 0 · design-reviewer Critical 0
   · Playwright 라이트/다크 5컷, 폰트·border·컬럼 폭 실측
백엔드·데이터·라벨 불변. Plan-45 invariants 준수.
```
