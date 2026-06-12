# Plan-59 — Verify verdict 라벨 재갱신 + verdict_legacy 임계 정합 — v1

> 작성일: 2026-05-20
> 대상 시스템: Verify (`compare.html`)
> 변경 범위: 프론트엔드 `simRecomputeFromSettings()` 내 verdict 라벨 재갱신 + `payload.verdict_legacy` 임계 1 off 정정 + verdict 결정 로직 헬퍼 추출
> 상태: 계획 단계 (사용자 승인 후 진행)
> 선행: Plan-58 완료 (`matchVerdictBand()` 헬퍼 도입)

---

## 진행 현황 요약

| Phase | 내용 | 예상 공수 | 상태 |
|-------|------|---------|------|
| Phase 0 | 영향성 조사 (완료) — `simRecomputeFromSettings` 호출처 3건, `.sim-verdict` DOM, `verdict_legacy` 사용처 | — | ✅ |
| Phase 1 | `resolveVerdict(score)` 헬퍼 추출 → 첫 렌더 + 재계산 경로 통일 | 0.2일 | ⬜ 대기 |
| Phase 2 | `simRecomputeFromSettings`에 `.sim-verdict` DOM 갱신 추가 (F-58-2) | 0.2일 | ⬜ 대기 |
| Phase 3 | `payload.verdict_legacy` 임계 1 off 정정 (F-58-1) | 0.05일 | ⬜ 대기 |
| Phase 4 | 단위 테스트 추가 — resolveVerdict + 재계산 시나리오 | 0.2일 | ⬜ 대기 |
| Phase 5 | 브라우저 E2E — 수동 제외 후 verdict 라벨 변동 확인 | 0.25일 | ⬜ 대기 |
| Phase 6 | 피드백 보고서 | 0.1일 | ⬜ 대기 |
| **합계** | — | **1.0일** | **0/6** |

---

## 배경

Plan-58 피드백 보고서 F-58-2 + F-58-1 후속.

### F-58-2 (핵심 페인)
`compare.html:2481` 주석에 명시된 *"5단계 신호등은 simRecomputeFromSettings 에서 최종 갱신"* 약속이 구현 누락. 함수 본체(`compare.html:1435~1518`)에 점수·카운트·누적바·매칭 카드 갱신 코드는 있어도 `.sim-verdict` 라벨 갱신 코드가 없음.

**사용자 시나리오 (재현)**:
1. 검사 결과 30% "검토 필요(노랑)" 표시
2. 사용자가 매칭 카드 여러 개 수동 제외 → 점수 카드 `0.9%`로 즉시 갱신
3. **verdict 박스는 여전히 "검토 필요(노랑)"** — 실제로는 "양호(녹색)"가 되어야 함

### F-58-1 (트리비얼 정합)
`compare.html:5307` `payload.verdict_legacy` 가 `verdictBoundHigh = 74` 를 사용 → `>= 74` 가 "위험". 백엔드 5단계 임계는 `>= 75`. 결과: `74.x%` 점수에서 verdict_legacy 가 "위험"으로 표시되지만 백엔드 verdict_label은 "상당량 매칭(orange)". 호환 필드 (실사용 빈도 거의 0) 라 영향 미미하나 백엔드 정합 위해 1 off 정정.

### F-58-3 분리
`settings_service.py:226-227` 디폴트 (30/60) vs `compare.html` 디폴트 (25/74) 불일치는:
- 관리자 GUI 라벨(`admin-settings.js:316,319`)과 묶여 있어 GUI 어휘도 같이 손봐야 함
- 5단계 임계는 `[0, 25, 50, 75]` 4개인데 GUI는 2개 임계만 노출 — 의미 차이가 크다
- 변경 표면이 크고 호환성 위험 → **별도 Plan으로 분리**

본 Plan은 사용자 직접 페인(F-58-2) 해결에 집중 + F-58-1 묶음 처리.

---

## 변경 범위

### A. `resolveVerdict(score)` 헬퍼 추출 (Phase 1)

현재 `simShowResults` 의 verdict 결정 로직 (line 2498~2510) 을 함수로 추출.

위치: `compare.html` `matchVerdictBand()` 직후 (line 2429~).

```js
// Plan-59: verdict 라벨/색/툴팁 결정 — 첫 렌더(simShowResults) + 재계산(simRecomputeFromSettings) 공통.
// SSOT verdict_bands 가 있으면 matchVerdictBand 사용, 없으면 v3 정합 fallback (25/74).
function resolveVerdict(score) {
    var bands = (simHelp && Array.isArray(simHelp.verdict_bands)) ? simHelp.verdict_bands : null;
    var match = bands ? matchVerdictBand(score, bands) : null;
    if (match) {
        var classMap = { blue: 'sim-verdict-blue', green: 'sim-verdict-good', yellow: 'sim-verdict-yellow', orange: 'sim-verdict-orange', red: 'sim-verdict-warning' };
        return {
            label: match.label,
            cls:   classMap[match.color] || 'sim-verdict-moderate',
            tip:   '유사율 ' + match.range_min + (match.range_min === match.range_max ? '%' : '~' + match.range_max + '%') + ' — ' + (match.meaning || '')
        };
    }
    // simHelp 미로드 fallback — v3 5단계 임계와 정합 (25/74)
    if (score >= verdictBoundHigh) return { label: '위험',      cls: 'sim-verdict-warning',  tip: '유사율 ' + verdictBoundHigh + '% 이상' };
    if (score >= verdictBoundLow)  return { label: '검토 필요', cls: 'sim-verdict-moderate', tip: '유사율 ' + verdictBoundLow + '~' + verdictBoundHigh + '% 구간' };
    return                                { label: '양호',      cls: 'sim-verdict-good',     tip: '유사율 ' + verdictBoundLow + '% 미만' };
}
```

### B. `simShowResults` 첫 렌더 — 헬퍼 호출로 교체 (Phase 1)

기존 line 2498~2510 의 인라인 분기를 `var v = resolveVerdict(scoreVal);` 한 줄로 축소.

### C. `simRecomputeFromSettings` — DOM 갱신 추가 (Phase 2)

함수 후반부 (현재 line 1517 `simUpdateExclusionBanner` 호출 직전) 에 추가:

```js
// Plan-59 (F-58-2): verdict 라벨/색/툴팁도 새 점수 기준 재산출.
// 기존 주석 (compare.html:2481) 이 약속한 동작 — 구현 누락분 보완.
var verdictEl = document.querySelector('.sim-verdict');
if (verdictEl) {
    var v = resolveVerdict(score);
    var allClasses = ['sim-verdict-blue', 'sim-verdict-good', 'sim-verdict-yellow', 'sim-verdict-orange', 'sim-verdict-warning', 'sim-verdict-moderate'];
    allClasses.forEach(function(c) { verdictEl.classList.remove(c); });
    verdictEl.classList.add(v.cls);
    // tooltip-icon 노드 보존하면서 라벨 텍스트만 갱신
    var tipIcon = verdictEl.querySelector('.tooltip-icon');
    verdictEl.textContent = v.label + ' ';
    if (tipIcon) {
        tipIcon.setAttribute('data-tooltip', v.tip);
        verdictEl.appendChild(tipIcon);
    }
}
```

### D. `payload.verdict_legacy` 임계 정정 (Phase 3)

현재 (line 5305~5308):
```js
payload.verdict_legacy = payload.score >= verdictBoundHigh ? '위험'
    : (payload.score >= verdictBoundLow ? '검토 필요' : '양호');
```

`verdictBoundHigh = 74` → 백엔드 75 와 1 off. 정정:
- 변수 자체는 그대로 두되 비교 연산 `>=` → `>`  (74 초과부터 "위험")
- 또는 더 명확하게 SSOT `verdict_bands` 의 마지막 밴드 `range_min` 사용

가장 안전한 선택: **`matchVerdictBand` + 3단계 매핑**으로 산출 — verdict_label (5단계) 을 3단계로 단순 매핑.

```js
// Plan-59 (F-58-1): verdict_legacy 를 v3 5단계 → 3단계 매핑으로 산출 (verdictBoundHigh=74 off-by-one 해소).
var legacyMap = { blue: '양호', green: '양호', yellow: '검토 필요', orange: '검토 필요', red: '위험' };
payload.verdict_legacy = matchBand
    ? (legacyMap[matchBand.color] || '양호')
    : (payload.score >= verdictBoundHigh ? '위험' : (payload.score >= verdictBoundLow ? '검토 필요' : '양호'));
```

→ SSOT 로드 시: 5단계 → 3단계 결정론적 매핑. 미로드 시: 옛 fallback (단, `verdictBoundHigh` 가 5단계와 정합인 74 이므로 74 초과 시점에 위험으로 분류되어 백엔드 75 와 1 off 잔존하나 미로드 경로는 거의 발생 안 함).

---

## 영향성 분석

### A. resolveVerdict 헬퍼 추출 영향
- 기존 첫 렌더(line 2498~2510) 로직과 **100% 동일**. 단순 함수 추출.
- 두 곳에서 호출 → 향후 verdict 규칙 변경 시 단일 지점만 수정 (Plan-58 의 `matchVerdictBand` 와 동일 철학).

### B. simRecomputeFromSettings DOM 갱신 영향

| 항목 | 영향 |
|---|---|
| 첫 렌더 시 | line 2750 에서 `simRecomputeFromSettings()` 가 직후 호출됨 → `.sim-verdict` 가 막 생성된 직후 한 번 더 갱신됨. **렌더 결과 동일** (라벨 변동 0) — 같은 점수 같은 결과. |
| 검사 설정 토글 시 | line 2908 호출 → 새 점수 기준 라벨 갱신. **체감 개선** — 옛 동작에서는 점수만 바뀌고 라벨 stale 이었음. |
| 수동 제외/복원 시 | line 1031 호출 → 동일. 사용자 보고된 F-58-2 시나리오 해결. |
| 미초기화 시 (`.sim-verdict` 없음) | `if (verdictEl)` 가드로 silent skip. |
| simHelp 미로드 + SSOT 미적용 | `resolveVerdict` 의 fallback 분기 — 옛 라벨 유지. |

### C. payload.verdict_legacy 정정 영향

| 항목 | 영향 |
|---|---|
| 사용처 1: `compare.html:5490` 보고서 카드 | `p.verdict_label || p.verdict_legacy || '—'` — verdict_label 항상 채워짐 → legacy 실사용 빈도 ~0 |
| 사용처 2: `backend/services/export_service.py:105` Excel | 동일 — verdict_label 우선 → legacy 실사용 빈도 ~0 |
| 5단계 → 3단계 매핑 | blue/green → 양호, yellow/orange → 검토 필요, red → 위험. **시맨틱 일관** (orange 가 옛 3단계의 "검토 필요" 영역) |
| 점수 74.5% 케이스 | 옛: "위험" (verdictBoundHigh=74 off-by-one) → 신: "검토 필요" (5단계 orange → 3단계 검토 필요). **백엔드 verdict_label 과도 정합** |

### D. 백엔드 영향
- **변경 0**. 모든 변경이 프론트엔드 한 파일 (`compare.html`).
- 백엔드 응답·DB·이력 포맷 무변동.

### E. 관리자 설정 영향
- 본 PR 은 `verdictBoundLow/High` 변수 자체 (관리자 설정 영향 받음) 를 변경하지 않음.
- 새 헬퍼 `resolveVerdict` 도 같은 변수를 fallback 분기에서만 사용 → 관리자 설정 영향 동일하게 유지.
- F-58-3 (settings 디폴트 정합화) 은 별도 PR.

### F. 회귀 위험

| 시나리오 | 위험 |
|---|---|
| 첫 렌더 → 즉시 재계산 (line 2750) | 같은 점수·같은 결과 → 라벨 변동 0. 위험 0. |
| 검사 설정 체크박스 토글 | 점수 변화 시 라벨도 같이 변경 → 의도된 변화. 회귀 0. |
| 수동 제외 → 복원 | 점수 원복 → 라벨도 원복. 회귀 0. |
| simHelp fetch 실패 | fallback 분기 동작 → 옛 동작 유지. 회귀 0. |
| `.sim-verdict` DOM 미존재 | 가드 처리. 위험 0. |
| `verdict_legacy` 옛 보고서 호환 | 5→3 매핑이 더 정확. 실사용 빈도 0 에 가까워 가시 회귀 거의 없음. |

---

## 검증 계획

### Phase 4 — 단위 테스트
`tests/sim_verdict_band_test.js` 확장 또는 신규 `tests/sim_resolve_verdict_test.js`:
- resolveVerdict(0.9) → `{ label: '양호', cls: 'sim-verdict-good', ... }`
- resolveVerdict(49.9) → `{ label: '검토 필요', cls: 'sim-verdict-yellow', ... }`
- resolveVerdict(74.5) → `{ label: '상당량 매칭', cls: 'sim-verdict-orange', ... }`
- resolveVerdict(75) → `{ label: '위험', cls: 'sim-verdict-warning', ... }`
- legacy 매핑 — 74.5 → "검토 필요", 75 → "위험"

### Phase 5 — 브라우저 E2E (Playwright)
1. 로그인 → compare.html 로드
2. 강제로 `.sim-verdict` 요소 생성 + simRecomputeFromSettings 호출 시뮬레이션
3. 또는 실제 사용자 시나리오: 검사 → 매칭 카드 수동 제외 → verdict 라벨 변경 확인
4. 정적 검사: 페이지 스크립트에 `resolveVerdict` 정의 + 호출 2건 존재 확인

### Phase 6 — 피드백 보고서
`workbench/reports/plan-59-feedback.md`
- 전문가 관점: 코드 품질, 단일 지점 원칙, 잔존 이슈
- 사용자 관점: F-58-2 시나리오 해결 확인, F-58-1 trivial 정합 효과
- F-58-3 별도 Plan 권고

---

## 롤백 계획

단일 commit. 회귀 발견 시 `git revert <commit>` 1회 원복.
- 백엔드 변경 0
- DOM 구조 변경 0 (요소 갱신만)
- 데이터 마이그레이션 0

---

## 작업 원칙 준수
- 의견 먼저, 구현은 승인 후 — **본 계획서가 그 의견**
- 기존 코드 패턴 재사용 — Plan-58 의 `matchVerdictBand` 헬퍼 그대로 활용
- 과도한 엔지니어링 금지 — F-58-3 (GUI 라벨/디폴트 정합) 은 본 PR 에 미포함, 별도 분리
- 커밋은 요청 시에만 — 사용자 명시 요청 후 commit
