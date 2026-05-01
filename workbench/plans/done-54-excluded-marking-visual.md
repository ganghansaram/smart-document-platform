# Plan-54 — 자동 제외 매칭 본문 시각 신호 + 표 셀 폰트 정합

> 작성일: 2026-04-30
> 완료일: 2026-04-30
> 변경 범위: `css/compare.css` + `compare.html`
> 사용자 승인: Plan-53 사용자 피드백 → 업계 표준 조사 → Option D + table 폰트 채택

---

## 진행 현황 요약

| Phase | 내용 | 상태 |
|-------|------|------|
| Phase 1 | CSS — `.sim-hl-excluded` (paragraph + table 셀) + 표 셀 폰트 13px | ✅ 완료 |
| Phase 2 | `simApplyHighlights` — 자동 제외 분기 추가 | ✅ 완료 |
| Phase 3 | `simRecomputeFromSettings` — 본문 마킹 토글 갱신 | ✅ 완료 |
| Phase 4 | Playwright 시각 검증 + 자동 회귀 24건 PASS | ✅ 완료 |
| Phase 5 | 보고서 + 계획서 done- 처리 | ✅ 완료 |

---

## 0. Context

### 사용자 페인
표 헤더 등 자동 제외 매칭이 본문 패널에서 일반 매칭과 **동일 색상** 으로 표시됨 → 사용자가 "이 매칭이 점수에 들어가는지" 본문만 보고는 모름. 자동 제외 패널을 펼쳐야 인지.

### 업계 표준 (Copyleaks / Turnitin / iThenticate)
모든 주요 도구가 자동 제외를 본문에서 회색 + 점선 + 흐림으로 시각 구분.

### 결함 위치 (Plan-50~52 적용 후 잠재)
- `simApplyHighlights` (compare.html:2769~) 가 매칭 type 만 보고 클래스 부여, `excluded_auto` 카테고리 무시
- `simApplyFilter` (compare.html:3281~) 가 자동 제외 매칭 본문 hl 을 inline `display:none` 으로 숨김 — 결정적 결함

---

## 1. Phase 1 — CSS

### `css/compare.css`
```css
/* paragraph 매칭 + 자동 제외 (paragraph 한정 셀렉터 — opacity 가 <tr> 에서 thead collapse 발생) */
.sim-md-view p.sim-hl.sim-hl-excluded,
.sim-md-view div.sim-hl.sim-hl-excluded {
    opacity: 0.55;
    border-left-style: dashed !important;
}
/* 표 행 매칭 + 자동 제외 — 셀 단위 background/color (border-collapse 모드 layout 안전) */
.sim-md-view table.sim-md-table tr.sim-hl.sim-hl-excluded > th,
.sim-md-view table.sim-md-table tr.sim-hl.sim-hl-excluded > td {
    background: var(--bg-gray);
    color: var(--text-muted);
}
.sim-md-view p.sim-hl.sim-hl-excluded:hover,
.sim-md-view div.sim-hl.sim-hl-excluded:hover { opacity: 0.7; }

/* 표 셀 폰트 본문과 동일 */
.sim-md-view table.sim-md-table { font-size: var(--font-body); }
```

---

## 2. Phase 2 — `simApplyHighlights` 보강

```js
var settings = simLoadCheckSettings();
var isExcluded = resolveCategory(m, settings) === 'excluded_auto';
...
els[ei].classList.add('sim-hl', 'sim-hl-' + type);
if (isExcluded) els[ei].classList.add('sim-hl-excluded');
```

---

## 3. Phase 3 — `simRecomputeFromSettings` 본문 마킹 토글

사이드바 카드 토글 직후 본문 hl 도 동일 갱신:
```js
var hlEls = document.querySelectorAll('#panel-body-a [data-sim-idx], #panel-body-b [data-sim-idx]');
for (var hi = 0; hi < hlEls.length; hi++) {
    var hlEl = hlEls[hi];
    var hlMatch = matches[parseInt(hlEl.getAttribute('data-sim-idx'))];
    if (hlMatch && resolveCategory(hlMatch, settings) === 'excluded_auto') {
        hlEl.classList.add('sim-hl-excluded');
    } else {
        hlEl.classList.remove('sim-hl-excluded');
    }
}
```

---

## 4. 부수 — `simApplyFilter` 결함 수정

기존:
```js
var hlShow = isExcluded ? false : show;  // 자동 제외 본문 숨김
```
수정:
```js
var hlShow = isExcluded ? true : show;  // 자동 제외도 본문 표시 (sim-hl-excluded 시각 구분)
```

→ 업계 표준 부합 + Plan-54 의 의도와 정합.

---

## 5. 검증 결과

### 자동 회귀 24/24 PASS
- `sim_block_order_test.py` 5/5
- `sim_table_structural_test.py` 6/6
- `sim_score_v3_unit_test.py` 5/5
- `sim_merge_adjacent_unit_test.py` 8/8
- `sim_label_consistency.sh` PASS

### Playwright E2E
- 토글 ON: 표 헤더 회색 처리 + text-muted, 점수 66.7%
- 토글 OFF: 일반 매칭 색상 복원, 점수 71.4% (헤더 분자 포함)
- 표 셀 폰트 13px 정합

### 발견 + 해결한 부수 이슈
1. CSS opacity 가 `<tr>` 에 적용 시 thead height collapse → paragraph 한정 셀렉터로 좁힘
2. simApplyFilter 의 자동 제외 본문 숨김 → 표시로 변경

---

## 6. 산출물

| 파일 | 변경 |
|------|------|
| `css/compare.css` | `.sim-hl-excluded` (paragraph + table 셀) + 표 폰트 (~12줄) |
| `compare.html` | `simApplyHighlights` (3줄) + `simRecomputeFromSettings` (12줄) + `simApplyFilter` (1줄) |
| `workbench/reports/plan-54-feedback.md` | 검증 보고서 |
| `workbench/plans/done-54-...md` | 본 계획서 (완료) |

---

## 7. 영향 분석

### 격리
- 백엔드 무수정 — 단위 테스트 24건 무영향
- 기존 시각 토큰 무수정
- `.sim-md-table` 한정 셀렉터 — 다른 표 (.sim-help-bands 등) 무영향

### 사용자 인지
- 본문에서 자동 제외 매칭이 시각 구분 (회색/점선/흐림)
- 토글 변경 시 본문 + 점수 양쪽 즉시 갱신
- 업계 표준 부합

### 롤백
- 1줄 simApplyFilter 변경 + CSS 블록 + JS 추가 라인 — git revert 1회

---

## 8. 한 줄 결론

**PASS.** Plan-54 완료 — 자동 제외 본문 시각 신호 (paragraph 점선 + table 회색) + 표 셀 폰트 정합 + simApplyFilter 자동 제외 본문 표시로 변경. 업계 표준 (Copyleaks/Turnitin/iThenticate) 부합. 단위 테스트 24/24 PASS, 백엔드 무수정.
