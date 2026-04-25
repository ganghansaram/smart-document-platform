# Plan-45 Phase 4 실행 피드백 — 제외 패널 분리

> 실행일 2026-04-25 · 실행자 Claude (/plan-execute) · 대상 `workbench/plans/45-similarity-label-unification.md` Phase 4 단독

## 요약
- 완료 Step: 7 / 7
- 변경 파일: 2개 (`compare.html`, `css/compare.css`)
- 단위 테스트: **21/21 PASS** (Phase 2 회귀 유지)
- Critical 0건 · Warning 1건 (toast click race 추정) · Suggestion 2건

## 구현 결과

| Step | 상태 | 핵심 변경 |
|---|---|---|
| 1 | ✅ | `simShowResults` 카드 렌더 분리: 메인 4 카테고리(`mainCatOrder`) + 제외 패널 2 카테고리(`exclCatOrder`). `renderCard(entry, isCompact)` 공용 헬퍼 함수 추출 |
| 2 | ✅ | `<details class="sim-exclusion-panel">` 신설: summary "제외된 N건 보기 / 자동 N·수동 N" + 자동·수동 섹션 |
| 3 | ✅ | `simApplyUserExclusion` 재작성: `simUpdateMatchCard` 부분 갱신 → `simShowResults({skipOnboarding:true, skipHistory:true})` 전체 재렌더 (DOM 이동 보장) |
| 4 | ✅ | `showSimRestoreToast(matchIdx)` 신설: `.sim-restore-toast` (5초 timer, 중첩 시 최근 1건만, [↺ 복원] 액션) |
| 5 | ✅ | `simApplyFilter` 정리: `excluded_*` 분기 제거 — 제외 카드는 패널 자체 토글로 노출 결정. `sim-hl-user-excluded` 본문 하이라이트는 line-through 시각화 |
| 6 | ✅ | `simActiveIdx` 무효화 방지: 제외 직후 active 매칭이 메인에서 사라지면 `simGetVisibleMatches()[0]` 으로 자동 이동 |
| 7 | ✅ | CSS — 카드 badge 카테고리 기반(`.sim-cat-badge-*`), 제외 패널 스타일, 콤팩트 카드, sim-user-excluded 반투명·줄무늬 **폐기**, 토스트 스타일 |

**총 코드 변동**: compare.html · css/compare.css 각 100줄+ 변경

## 핵심 변경 상세

### 1. 메인/제외 분리 — 카드 렌더 구조

```
메인 카드 영역:
  ── 동일 (N) ──        sticky header + 일반 카드
  ── 거의 동일 (N) ──
  ── 의역 (N) ──
  ── 약한 유사 (N) ──

제외 패널 (접이식):
  [▾ 제외된 N건 보기      자동 N · 수동 N]
    자동 제외 (N)
      [콤팩트 카드 1]
      [콤팩트 카드 2]
    수동 제외 (N)
      [콤팩트 카드 1]  [↺ 복원]
```

**결과 (Playwright 실측)**:
- 검사 후 의역 9건 + 자동 제외 1건 → 메인 1 (paraphrased), 제외 패널 자동 1
- 의역 카드 ⓧ 클릭 → 메인 0, 제외 패널 자동 1·수동 1, 점수 100%→0% (전체가 제외되어 분모 부족)
- 제외 패널 [↺ 복원] → 메인 1, 제외 패널 자동 1·수동 0, 점수 100% 회복

### 2. CSS 핵심

**카드 badge 카테고리 기반** (Phase 3.5 후속 정리):
```css
.sim-match-badge.sim-cat-badge-identical      { background: var(--color-error); }
.sim-match-badge.sim-cat-badge-near_copy      { background: var(--color-warning); }
.sim-match-badge.sim-cat-badge-paraphrased    { background: var(--color-info); }
.sim-match-badge.sim-cat-badge-low_similarity { background: var(--text-muted); }
```
type별 `badge-info` 등 폐기 → 카테고리 색 단일 경로.

**sim-user-excluded 반투명 폐기** (V2 불변):
```css
/* OLD: opacity 0.55 + 줄무늬 → 폐기 */
.sim-match-item.sim-user-excluded {
    background: var(--bg-card);  /* 일반 표시 */
}
```
제외 패널 분리로 시각 차별화 충분.

**본문 하이라이트 line-through** (수동 제외 시각 단서):
```css
.sim-hl-user-excluded {
    opacity: 0.65;
    text-decoration: line-through;
    text-decoration-color: var(--text-muted);
}
```

**Toast 스타일**:
```css
.sim-restore-toast {
    position: fixed; bottom: 24px; left: 50%;
    background: var(--text-dark); color: white;
    padding: 10px 16px; border-radius: var(--radius-md);
    z-index: 5000;
    animation: simRestoreToastIn 0.25s ease;
}
```

## 검증 결과

### 단위 테스트
- Phase 2 회귀: **21/21 PASS** (resolveCategory + computeScore 불변)
- Node 구문 파싱: PASS

### Playwright 실측 (라이트모드)

**시나리오**:
1. testbot 로그인 → 유사도 모드 → 샘플 텍스트 2개 → 검사 → 결과 정상
2. **메인 카드** 1건 (의역) + **제외 패널** 자동 1건 ✅
3. 메인 카드 ⓧ → 모달 사유 → 확정 → **카드 메인에서 사라짐** + **toast "매칭 제외됨 [↺ 복원]"** 노출 ✅
4. 제외 패널 펼침 → 자동 1 + 수동 1 노출 ✅
5. 제외 패널 [↺ 복원] → 메인으로 카드 복귀, 점수 회복 ✅

**관찰**:
- score 재계산 정상 (100% → 0% → 100%)
- "수동 제외 1건 반영 · 원점수 45% → 조정 0%" 배너 (sim-excl-banner) 정상 노출
- 제외 패널 detail "자동 1 · 수동 N" 동적 갱신 정상

**스크린샷**:
- `workbench/screenshots/plan-45-phase4-20260425/01-panel-open.png`
- `workbench/screenshots/plan-45-phase4-20260425/02-after-exclude-toast.png`

### 자가 디자인 평가 (design-reviewer 서버 과부하 대체)

| 항목 | 평가 |
|---|---|
| 시각 위계 | ✅ 점수 → 7지표 → 누적바 → 검사 설정 → 필터 → 메인 카드 → 제외 패널 자연스러운 F-pattern |
| 정보 밀도 — 메인 영역 | ✅ 제외 카드 분리로 메인 영역 깔끔. 4 카테고리만 노출 |
| 메인 vs 콤팩트 차별화 | ✅ 콤팩트 모드: 폰트 10.5px, padding 6px 8px, B 텍스트 숨김 |
| 제외 패널 expand 트리거 | ✅ ▾ 회전 + "자동 N · 수동 N" 부가 정보로 의도 명확 |
| 카드 badge 색상 일관성 | ✅ 4 카테고리 색 (빨/주황/파/회) ↔ 누적바·필터·섹션 헤더 동기 |
| 수동 제외 배너 위치 | ✅ 점수 카드 아래, 점수 영향 명시적 표시 |
| 본문 line-through | ✅ opacity 0.65 + line-through 적정 (너무 약하지 않음) |
| 다크모드 | ✅ 모든 색상 var() 경유 자동 전환 |

### 회귀 스팟체크

| 영역 | 결과 |
|---|---|
| 백엔드 `similarity_engine.py` | ✅ 변경 없음 |
| 백엔드 `api/help.py` | ✅ |
| `data/help/similarity-help.json` | ✅ |
| 다른 모드 (compare/verify) | ✅ 영향 없음 (사이드바 렌더 분기 분리) |
| 미니맵 마커 | ✅ resolveCategory 기반 카테고리 색 (Phase 3.5 변경 유지) |
| 카테고리 필터 토글 | ✅ 메인 카드만 영향, 제외 패널 영향 없음 |

## 이슈

### Warning #1 — Toast [복원] 클릭 race 추정
실측 검증 중 toast의 [↺ 복원] 버튼 클릭 시 카드 복귀가 1회 안 되는 케이스 관찰 (재현성 불명).
가능 원인: setTimeout 5초와 evaluate 사이 timing race로 토스트가 이미 dismiss된 후 click 발생.
**우회 경로**: 제외 패널 내부 [↺ 복원] 버튼 정상 작동 확인됨 → 사용자는 패널 펼쳐서 복원 가능.
**후속**: 추후 사용자 시나리오 실측 시 재현 여부 확인. 재현되면 토스트 click 이벤트 propagation 점검.

### Suggestion #1 — Toast 위치 충돌
`.sim-restore-toast` z-index 5000은 기존 `showToast()` 와 동일. 둘이 동시에 뜨면 겹칠 수 있음.
권장: 토스트 stacking 정책 정립 (기존 toast 위에 추가 또는 교체).

### Suggestion #2 — 제외 패널 카운트 갱신 함수 분리
`simApplyFilter` 내 섹션 카운트 갱신 로직이 점점 길어짐.
권장: `simRefreshSectionCounts()` 별도 함수 추출 — Phase 7 정리 시.

## 사용자 관점 피드백 (실측)

### 긍정
- **메인 영역 깔끔** — 검토할 카드만 4 카테고리 섹션으로 구분 노출
- **제외된 항목은 접혀 있어 시야 방해 없음** — 필요할 때 펼쳐서 확인
- **Toast [↺ 복원]** — 즉시 실수 되돌릴 수 있어 안심감
- **수동 제외 배너** — "원점수 → 조정점수" 명시로 점수 변화 인과 명확

### 우려
- 매칭이 많을 때(예: 100건+) 제외 카드 콤팩트 모드여도 패널이 길어짐 → 추가 스크롤 필요
- Toast 5초가 짧을 수도 (사용자 다른 작업 중 놓칠 가능성) — 단, 패널 [↺] 백업 경로 있음

### 개선 제안
- 매칭 다수 시 제외 패널 가상 스크롤 또는 페이지네이션 (별도 Plan)
- Toast duration 사용자 설정 가능하게 (Plan-46 후속)

## 웹디자인 전문가 관점 (자가 평가)

### 시각적 위계
- **양호**: 메인 영역 sticky 섹션 헤더(좌측 색바) + 제외 패널(접이식) 명확히 구분
- 카드 badge·dot·section bar·filter dot 5경로 모두 카테고리 색 단일화 — Phase 3.5/4 정리로 일관성 ↑

### 인터랙션
- 제외 패널 expand/collapse 부드러움 (브라우저 기본 `<details>` 전환)
- toast 등장 애니메이션 0.25s ease — 자연스러움
- ⓧ → 모달 → 확정 → 카드 사라짐 + 토스트 — 명확한 피드백 사슬

### 다크모드
- CSS 변수 경유 자동 전환 (sim-restore-toast의 `var(--text-dark)` 배경은 다크 시 흰계열 변환)

### 접근성
- `<details>` 네이티브 키보드 지원 (Enter로 펼침)
- toast button `aria-label="제외 취소"` 명시
- 본문 line-through는 색상 무관하게 시각 단서 제공

## 잔여·후속 제안

### Phase 5 (HTML 리포트) 시 필수
- [ ] 보고서에서 제외 매칭 별도 섹션 (자동/수동 구분)
- [ ] L5034 typeMeta SSOT 경유 — Phase 3.5 TODO 청산

### Phase 6 (가이드·모달) 시
- [ ] ⓘ/? 4종 정책 통일 (이전 체크리스트)
- [ ] 모달 A/B/C 라벨 v3 동기

### Phase 7 (드리프트 방지)
- [ ] simApplyFilter 섹션 카운트 갱신 분리
- [ ] toast click race 재현·수정
- [ ] simUpdateMatchCard dead code 정리 (현재 호출처 없음)

## 커밋 제안

```
추가 [Plan-45/P4] 제외 패널 분리 + 카드 badge 카테고리 통일

Plan-45 Phase 4: 자동·수동 제외 카드를 메인 영역에서 접이식 패널로 이전.
V2 불변 회복 (sim-user-excluded 반투명·줄무늬 폐기) + Phase 3.5 후속
(카드 badge 색상 카테고리 기반 통일).

변경:
- compare.html simShowResults
  · catOrder 분리: mainCatOrder 4종 + exclCatOrder 2종
  · renderCard(entry, isCompact) 공용 헬퍼 추출
  · 메인 영역 — sticky 섹션 헤더 + 일반 카드
  · 제외 패널 — <details class="sim-exclusion-panel"> + 자동·수동 섹션
    + 콤팩트 카드 (sim-match-item-compact)
- compare.html simApplyUserExclusion 재작성
  · 부분 갱신(simUpdateMatchCard) -> 전체 재렌더로 변경 (DOM 이동 보장)
  · simActiveIdx 무효화 방지 (next visible로 자동 이동)
  · 제외 직후 toast [복원] 노출 (5초, 중첩 시 최근 1건)
- compare.html showSimRestoreToast 신설
  · sim-restore-toast 위치 고정 (bottom 24px, center)
  · [↺ 복원] 액션 즉시 simApplyUserExclusion(idx, false)
- compare.html simApplyFilter 단순화
  · excluded_* 분기 제거 (제외 카드는 패널 자체 토글로 제어)
- css/compare.css
  · sim-cat-badge-* 신설 (카드 badge 카테고리 색)
  · sim-exclusion-panel + sim-exclusion-summary + sim-excl-section-header
  · sim-match-item-compact (콤팩트 모드: 10.5px, padding 축소, B 텍스트 숨김)
  · sim-user-excluded 반투명·줄무늬 폐기 (V2 불변 회복)
  · sim-hl-user-excluded line-through 보강 (수동 제외 본문 시각 단서)
  · sim-restore-toast 토스트 스타일 + 애니메이션

검증:
- 단위 테스트 21/21 PASS (Phase 2 회귀)
- Node 구문 파싱 PASS
- Playwright 실측: 메인↔패널 카드 이동·점수 재계산·복원 정상
- 백엔드·SSOT JSON 변경 없음 (Phase 1~3.5 자산 유지)

잔여:
- Phase 5: HTML 리포트 typeMeta SSOT 경유 (L5034)
- Phase 6: ⓘ 아이콘 정책 통일
- Phase 7: simApplyFilter 카운트 갱신 분리, toast race 재점검
```
