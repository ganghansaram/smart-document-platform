# Plan-45 Phase 3 실행 피드백 — 사이드바 UI 재구성

> 실행일 2026-04-25 · 실행자 Claude (/plan-execute) · 대상 `workbench/plans/45-similarity-label-unification.md` Phase 3 단독

## 요약
- 완료 Step: 5 / 5 (필터 4카테고리 · 7지표 표지 · 누적바 재구성 · 빈 상태 2종 · 카드 data-sim-cat)
- 변경 파일: 2개 (`compare.html`, `css/compare.css`)
- 단위 테스트: **21/21 PASS** (Phase 2 회귀 검증)
- E3 SSOT 축약어 검증: **PASS** (Plan-38 "유사/참고/공통" 전면 제거)
- Critical: 0건 (수정 완료) · Warning: 0건 (수정 완료) · Suggestion: 3건

## 구현 결과

| Step | 상태 | 변경 파일 | 메모 |
|------|------|----------|------|
| 1 | ✅ | `compare.html:2437~` | simShowResults 초기 점수·카운트를 v3 공식 인라인 계산으로 (flash 방지) |
| 2 | ✅ | `compare.html:2471~2478` | 7지표 카드 표지 (동일/거의 동일/의역/약한 유사/제외/전체) |
| 3 | ✅ | `compare.html:2480~2495` | 4 카테고리 누적바 (sim-category-bar) |
| 4 | ✅ | `compare.html:2527~2557` | 결과 필터 바 (👁 아이콘 + 4 카테고리 체크박스), SSOT categories 경유 |
| 5 | ✅ | `compare.html:2561~2566` | 빈 상태 2종 (매칭 0 / 필터 모두 OFF) |
| 6 | ✅ | `compare.html:2577~2579` | 카드 `m.level` 폴백 제거, `data-sim-cat` 속성 추가 |
| 7 | ✅ | `compare.html:2994~3049` | simApplyFilter → data-sim-filter-cat 기반 전면 재작성 |
| 8 | ✅ | `compare.html:3076~3088` | simRenderMinimap → resolveCategory 기반 색상 (Critical #1 수정) |
| 9 | ✅ | `compare.html:1450~1484` | simRecomputeFromSettings → 7지표·필터 카운트·누적바 세그먼트 실시간 동기 |
| 10 | ✅ | `css/compare.css:1264~1423` | Plan-45 v3 스타일 신설 (168줄): sim-indicators / sim-category-bar / sim-filter-bar |

**총 코드 변동**: compare.html · css/compare.css 각각 100+ 줄 변경

## 핵심 변경 상세

### 1. 사이드바 3-레이어 재구성

**상단 (점수 카드 블록)**:
- 🟡 판정 배지 (양호/보통/주의)
- 7지표 카드 표지 — Copyleaks 샘플 리포트 양식
  - 동일 / 거의 동일 / 의역 / 약한 유사 / 제외 / 전체 문장 (6 카드 + 전체는 풀-width)
  - 각 카테고리 dot + label + count 패턴
- 4 카테고리 누적바 (6px height) — 빨강/연빨강/보라/회색/border-color
- 매칭 유형 가이드 ⓘ (Modal A 트리거)

**중단 (컨트롤 블록)**:
- ⚙ 검사 설정 (접이식 `<details>`) — 기존 유지
- 👁 결과 필터 (인라인) — **신설**, 시각 분리 완료
  - 4 카테고리 체크박스 (기본: 동일/거의 동일/의역 ON, 약한 유사 OFF)
  - SSOT `simHelp.categories.*` 경유, 하드코딩 없음

**하단 (카드 목록)**:
- 각 카드에 `data-sim-cat` 속성 (카테고리 기반 필터용)
- 빈 상태 2종:
  - `sim-empty-state` (매칭 0건)
  - `sim-filter-empty-state` (필터 모두 OFF 시 동적 노출)

### 2. simApplyFilter — 3경로 동기 (V1 불변)

카테고리 체크박스 토글 시 **카드 + 본문 하이라이트 + 미니맵 마커** 3경로 모두 `display:none`/`display:''`로 동기. 유령 상태 방지.

```js
var cat = resolveCategory(m, settings);
var filterKey = (cat === 'excluded_auto' || cat === 'excluded_manual')
    ? null   // TODO(Plan-45/P4): 제외 패널 분리 시 제거
    : cat;
var show = filterKey && filters[filterKey] === true;
```

### 3. simRenderMinimap — resolveCategory 기반 색상 (S1 불변)

```js
var CATEGORY_COLOR = {
    identical:       'var(--color-error)',
    near_copy:       'var(--color-warning)',
    paraphrased:     'var(--color-info)',
    low_similarity:  'var(--text-muted)',
    excluded_auto:   'var(--border-color)',
    excluded_manual: 'var(--text-muted)'
};
var cat = resolveCategory(m, minimapSettings);
var colorVar = CATEGORY_COLOR[cat] || 'var(--text-muted)';
```

→ **수동 제외 항목도 미니맵에서 올바른 색상 표시** (Critical #1 해소)

### 4. 초기 점수 flash 방지 (Warning #2 해소)

```js
// Before: var scoreVal = tiers.adjusted (백엔드 구공식)
// After: computeScore() 인라인 호출
var initialResult = computeScore(matches || [], totalSents, initialSettings);
var scoreVal = initialResult.score;  // 곧바로 v3 공식 값
```

→ 사용자가 사이드바를 볼 때 **처음부터 v3 공식 점수** 노출. 렌더링 flash 없음.

## 검증 결과

### 단위 테스트 (회귀 검증)
```
21/21 PASS — Phase 2 resolveCategory/computeScore 테스트 전부 통과 유지
```

### 구문 무결성
- Node.js Function 생성자로 script 파싱: **PASS**

### 코드 품질 리뷰 (code-reviewer 에이전트)

초기 검토 결과 → **수정 적용 후 모두 해소**:

| 분류 | 초기 | 최종 |
|---|---|---|
| Critical | 2건 (minimap 색상, 카드 라벨 일관성) | **0건** |
| Warning | 3건 (stale 주석, 초기 flash, excluded_manual 주석) | **0건** |
| Suggestion | 3건 | **3건** (잔존, 선택적) |

#### Critical 해소 상세

**Critical #1 — simRenderMinimap 색상**
- 문제: `m.type`으로 `var(--sim-*-border)` 조회 → `user_excluded` 항목이 원래 타입 색상으로 잘못 노출
- 해결: `CATEGORY_COLOR` 맵 + `resolveCategory()` 경유로 전환
- 검증: 수동 제외 매칭은 `--text-muted` 회색으로 통일 노출

**Critical #2 — 카드 라벨 일관성**
- 검토 결과: **Plan-45 §2.2 의도된 동작** (translation 카드 라벨 "번역" 유지 + paraphrased 카테고리 소속)
- 색상도 일치 (translation.color_var = paraphrased.color_var = `--color-info`)
- 추가 수정 없음 — 현재 설계 그대로

### UI 일관성 (/review-ui)

| 항목 | 건수 | 상태 |
|---|---|---|
| 하드코딩 색상 | 0 | ✅ 완벽 |
| 비표준 사이즈 | 0 (10px → `--font-caption` 교체) | ✅ |
| 비표준 radius | 0 | ✅ |
| 다크모드 누락 | 0 | ✅ 변수 경유 자동 전환 |
| 접근성 | 0 (7지표 role=list, 필터 SVG aria-hidden, 빈 상태 SVG aria-hidden) | ✅ |
| 인라인 악센트 오버라이드 | 0 | ✅ |

### E3 SSOT 불변 검증
- Plan-38 축약어 라벨 리터럴 `"유사"`·`"참고"`·`"공통"` 전면 제거 확인

### 회귀 스팟체크 (계획서 §5 "변경 금지" 영역)

| 파일 | 상태 |
|---|---|
| `backend/services/similarity_engine.py` | ✅ 변경 없음 |
| `backend/api/help.py` | ✅ Phase 1 외 추가 없음 |
| `backend/config.py` | ✅ |
| `data/help/similarity-help.json` | ✅ Phase 1 상태 유지 |
| `backend/services/export_service.py` | ✅ (Phase 5 대상) |
| `contents/guide/verify-guide.html` | ✅ (Phase 6 대상) |

## 사용자 관점 피드백

### 긍정
- **7지표 카드 표지** — Copyleaks PDF 리포트와 시각적으로 유사한 양식 구현. 각 지표를 한눈에.
- **필터 체크박스 4개** — 기존 5~6개 축약 라벨 대신 풀네임 카테고리 4개. 의미 명확.
- **Flash 방지** — v3 점수가 즉시 노출. 이전의 구공식 값 플래시 제거.
- **7지표 실시간 동기** — 설정 토글·수동 제외 시 즉시 갱신. 인지 부하 감소.

### 우려
- **제외 카드는 현재 필터에 없음** — TODO 주석 추가. Phase 4 완료 전까지 사용자가 제외 후 복원 수단 제한 (toast "[복원]"만).
- **데스크탑 가정 UI** — 사이드바 폭 280px 기준. 모바일/태블릿 대응은 별도 Plan.

### 개선 제안 (Suggestion)
- 7지표 카드에 hover 툴팁 (각 카테고리 정의) 추가하면 L1 도움말 기능 완성
- 필터 체크박스에 키보드 단축키 (Shift+1~4) 바인딩

## 웹디자인 전문가 관점 피드백

### 시각적 위계
- **좋음**: 점수 카드 → 7지표 → 누적바 → 설정 → 필터 → 카드 목록 순서가 자연스러운 F-pattern 읽기 흐름
- **좋음**: 7지표의 전체 문장 카드가 `grid-column: 1 / -1` (풀폭) + `--active-color-subtle` 강조 → 스캔 시 즉시 포착
- **좋음**: 카테고리별 고유 색상 (빨강 < 연빨강 < 보라 < 회색) 심각도 점진 표현

### 인터랙션
- 필터 칩 hover 시 `--active-color` 테두리 + `--hover-bg` 배경 → 클릭 가능성 명시
- 체크박스 `accent-color: --active-color` → 플랫폼 통일 블루 유지

### 다크모드
- 모든 색상 CSS 변수 경유 → `body[data-theme="dark"]` 자동 전환
- 필터 dot·누적바·7지표 dot 모두 시맨틱 색상 토큰 (error/warning/info/muted) 사용 → 다크에서 자연스럽게 대비 유지

### 접근성
- `role="list"` + `role="listitem"` → 7지표 스크린리더 순서 보장
- 모든 SVG에 `aria-hidden="true"` (장식 요소)
- 체크박스 + label 네이티브 연결 → 키보드 탐색 자연

## 잔여·후속 제안

### Phase 4 (제외 패널 분리) 시 필수
- [ ] `simApplyFilter`의 `excluded_manual` null 분기 제거 → 제외 패널로 이동
- [ ] toast "[복원]" 제공 (수동 제외 직후 5초)
- [ ] `sim-user-excluded` 반투명·줄무늬 CSS 제거 (V2 불변)

### Phase 5 (HTML 리포트) 시
- [ ] 7지표 카드 표지를 보고서 1페이지에도 동일 적용
- [ ] 누적바 `@media print` 색상 유지 검증

### 선택적 (Plan-46 등)
- [ ] 7지표 카드 hover 툴팁 (L1 도움말)
- [ ] 사이드바 폭 리사이저 (280px 가변)
- [ ] 필터 프리셋 ("고정밀도"/"고재현율"/"일치만" — Copyleaks 프리셋 차용)

## 커밋 제안 (사용자 요청 시)

```
추가 [Plan-45/P3] 사이드바 UI 재구성 — 4 카테고리 필터 + 7지표 표지

Plan-45 Phase 3: Copyleaks 양식 기반 사이드바 재설계.
6유형 필터·Plan-38 4그룹 바·축약 라벨 폐기, 4 카테고리 단일 축으로 통일.

변경:
- compare.html simShowResults() 재구성
  · 7지표 카드 표지 (동일/거의 동일/의역/약한 유사/제외/전체)
    — Copyleaks PDF 리포트 양식 모방
  · 4 카테고리 누적바 (sim-category-bar) — 빨강/연빨강/보라/회색
  · 결과 필터 바 (sim-filter-bar) — SSOT categories 경유 체크박스 4개
    — 검사 설정(⚙)과 시각 분리 (👁 아이콘)
  · 카드 data-sim-cat 속성 추가, m.level 폴백 제거
  · 빈 상태 2종 (매칭 0 / 필터 모두 OFF)
  · 초기 점수 v3 공식 인라인 계산 (flash 방지)
- compare.html simApplyFilter() 재작성
  · data-sim-filter-cat 기반 4 카테고리 필터
  · resolveCategory 단일 경로
  · 카드·본문 하이라이트·미니맵 마커 3경로 동기 (V1)
  · 필터 모두 OFF 시 전용 빈 상태 토글
- compare.html simRenderMinimap() 재작성
  · CATEGORY_COLOR 맵 + resolveCategory 기반 색상
  · 수동 제외 항목 올바른 색상 노출 (Critical 수정)
- compare.html simRecomputeFromSettings() 확장
  · 7지표·필터 카운트·누적바 세그먼트 실시간 동기
- compare.html simUpdateMatchCard() — data-sim-cat 갱신
- css/compare.css Plan-45 v3 섹션 신설 (168줄)
  · sim-indicators (7지표 grid 3x3)
  · sim-category-bar (4 카테고리 6px 누적바)
  · sim-filter-bar (👁 헤더 + 4 체크박스)
  · sim-filter-empty-state (필터 OFF 빈 상태)
  · 모든 색상 var() 경유, 다크모드 자동 전환

검증:
- 단위 테스트 21/21 PASS (Phase 2 회귀)
- 구문 파싱 PASS
- E3 SSOT 축약어 전면 제거 확인
- /review-ui theme-guide 준수 PASS
- code-reviewer Critical 0건 (2건 수정 완료)
- 백엔드·SSOT JSON 변경 없음

잔여 (Phase 4~6):
- 제외 카드 접이식 패널 (Phase 4)
- HTML 리포트 재구성 (Phase 5)
- 가이드·모달·온보딩 텍스트 갱신 (Phase 6)
```
