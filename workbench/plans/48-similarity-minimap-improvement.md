# Plan-48 — Verify 유사도 미니맵 정상화 + 표준 기능 보강

> Plan-45 (유사도 분류 통합) 완료 후속. 사용자 지적 — "색깔 막대는 보이는데 클릭이 안 되고, 본문 하이라이트와 위치도 어긋나는 것 같다." (2026-04-25)

## 진행 현황

| Phase | 상태 | 커밋 | 비고 |
|-------|------|------|------|
| 계획서 작성 | ✅ 완료 | `7ffc90a` | 현 상태 진단 + 업계 표준 분석 |
| **Phase 1** — Critical 정상화 + 위치 정확도 | ✅ **완료 (2026-04-25)** | `263abec` | 단위 21/21 · code-reviewer Critical 0 |
| **Phase 2** — L2 호버 툴팁 | ✅ **완료 (2026-04-25)** | `2775990` | code-reviewer Critical 2 + Warning 2 + design-reviewer Warning 1 즉시 반영 |
| Phase 3 — diff·sim 코드 통합 | ⏸ 보류 | — | 선택적, ROI 낮음. 사용자 만족 시 미진행 |

피드백 보고서:
- Phase 1 — `workbench/reports/plan-48-phase1-feedback-2026-04-25.md`
- Phase 2 — `workbench/reports/plan-48-phase2-feedback-2026-04-25.md`

## 배경 / 사용자 인식 문제

1. "정상 작동하는 것 맞아? 클릭이 안 되는 것 같다."
2. "본문 마킹된 색상 위치와 미니맵 색상 위치가 안 맞는다는 생각이 든다."
3. (분포 인지 가치) "문서 내 얼마나, 어떻게 분포되어 있는지 알 수 있어서 좋을 것 같다."

→ **분포 인지(distribution awareness)** 는 미니맵의 고유 가치. 사이드바 카드는 카운트만 알려주지만 미니맵은 "어디에 몰려 있는지"를 시각적으로 한눈에 알려준다. 이 가치를 살리려면 위치 정확도가 전제.

---

## 현재 적용 상태 (정적 분석, 2026-04-25 기준)

### 코드 좌표
- **HTML 마운트**: `compare.html:234, 289` — `<div class="cp-minimap" id="cp-minimap-a/b">` (양 패널 우측, scrollbar 위 z-index:2)
- **CSS 컨테이너**: `css/compare.css:118~126` — `.cp-minimap { position:absolute; top:0; right:0; width:14px; height:100%; pointer-events:none; z-index:2 }`
- **diff 모드 미니맵 코드**: `compare.html:4155~4211` — `updateMinimapMarkers()`, `renderMinimapFor()`, `ResizeObserver(panelBodyA)`
- **sim 모드 미니맵 코드**: `compare.html:3083~3161` — `simRenderMinimap()`
- **diff 마커 CSS**: `css/compare.css:128~156` — `.cp-minimap-mark` + `.diff-para-added/deleted/modified` + `.active`
- **sim 마커 CSS**: **존재하지 않음** (인라인 style 만 있음)

### diff 모드 vs sim 모드 비교 (현 상태)

| 항목 | diff 모드 (`updateMinimapMarkers`) | sim 모드 (`simRenderMinimap`) |
|------|-----------------------------------|-------------------------------|
| 대상 elements | `.cp-paragraph[data-change-index]` (블록) | `[data-sim-idx]` (인라인 span, 문장 단위) |
| CSS 클래스 규칙 존재 | ✅ `.cp-minimap-mark { pointer-events: auto; ... }` (L134) | ❌ **없음** — 인라인 style 만 (`compare.html:3130, 3142`) |
| 클릭 동작 | ✅ pointer-events:auto + 개별 마커 addEventListener | ❌ 부모의 `pointer-events:none` cascade로 클릭 발화 안 함 |
| 클릭 핸들러 등록 위치 | 마커 생성 시 1회 | 함수 호출마다 컨테이너에 위임 등록 (누적) |
| ResizeObserver | ✅ `ResizeObserver(panelBodyA) → updateMinimapMarkers` (L4208) | ❌ 없음 |
| 활성 마커 표시 | ✅ `.active` 클래스 + 네비게이션 시 토글 (L149~) | ❌ `simNavigateToMatch`(L2933)는 카드·하이라이트만 갱신 |
| 마커 높이 | ✅ `Math.max(3, hRatio * trackH)` — 단락 길이 비례 | ❌ 고정 4px |
| 마커 위치 기준 | ✅ 블록 element offsetTop (정확) | ⚠ querySelector(첫 element)만 — 5문장 매칭도 첫 문장 위치만 표시 |
| `diff-gap`/`diff-hidden` 처리 | ✅ 분기 skip | (해당 없음) |
| 필터 OFF 처리 | (해당 없음) | ✅ `card.style.display === 'none'` 검사 후 skip (`compare.html:3119`) |
| 필터 변화 시 재렌더 | ✅ diff 모드는 필터 개념 없음 | ✅ `simApplyFilter` 끝에 `simRenderMinimap()` 호출 (L3080) |
| 색상 매핑 | CSS 클래스로 분리 | 인라인 `var(--...)` (다크모드 자동 전환은 됨) |

### 위치 mismatch 원인 (사용자 인지 문제 — 5가지)

코드 분석 결과 다음 원인이 합쳐져 본문 하이라이트와 미니맵 마커가 어긋나 보임:

#### A. 마커는 매칭의 "시작점"만 표시 (가장 큰 원인)
```js
// compare.html:3125, 3137
var elA = panelA.querySelector('[data-sim-idx="' + i + '"]');  // 첫 element만
```
한 매칭이 5문장을 덮어도 마커는 첫 문장 위치(idx=10)만. 본문엔 5문장 전체(idx=10~14) 하이라이트. → "마커 위치는 30%인데 빨간 영역은 30~45% 까지 펼쳐진다"는 시각 mismatch.

#### B. 마커 고정 높이 4px (정보 손실)
```js
// compare.html:3130
markA.style.cssText = '...height:4px;...'
```
diff 모드는 `Math.max(3, hRatio * trackH)`. sim 모드만 고정 4px. 짧은 매칭(1문장)과 긴 매칭(5문장)이 같은 두께. A 와 결합되어 mismatch 가중.

#### C. 폰트·이미지 로딩 후 레이아웃 변동 미반영
- `simRenderMinimap()` 은 `simApplyHighlights()` 직후 호출
- 그러나 display_html 에 이미지·MathML·웹폰트 있으면 비동기 로드 후 `panelA.scrollHeight` 늘어남
- 마커는 옛 scrollHeight 기준 위치에 고정 → **점진적으로 어긋남**
- ResizeObserver 부재(앞서 발견)로 영구 고정

#### D. 줄바꿈된 긴 문장 (작은 영향)
한 sentence span 이 3줄 차지하면 하이라이트는 3줄 모두 빨갛지만 `offsetTop` 은 첫 줄 기준 → 본문 끝 줄과 약 2줄 어긋남. (A·B 해결 시 자동 해소 — offsetHeight 가 실제 렌더 높이 반환하므로)

#### E. 패딩 포함 (무시 가능, ~1%)
`.cp-panel-body { padding: 0 16px 16px }` — bottom padding 16px 가 `scrollHeight` 에 포함. 모든 ratio 가 1% 미만 작게 나옴. 사용자 인지 거의 안 됨.

### 클릭 동작 결함 정리 (동시 영향)

1. **부모 컨테이너 pointer-events: none, 자식에 override 없음** (`css/compare.css:124`)
   - diff: `.cp-minimap-mark { pointer-events: auto }` (L134) ← 정상 작동
   - sim: `.sim-minimap-mark` CSS 클래스 자체가 없음 ← 클릭 발화 안 함

2. **이벤트 리스너 무한 누적** (`compare.html:3150~3160`)
   - `simRenderMinimap()` 끝에서 `[minimapA, minimapB].forEach(mm => mm.addEventListener('click', …))` 매 호출마다 추가만 됨
   - 호출 트리거: `simShowResults`, `simApplyFilter`, `simRecomputeFromSettings`, 수동 제외 등 → 5~10회 누적 일상
   - 현재 클릭 발화 안 되어 잠재적 버그, 살리는 순간 다중 점프 발생

3. **ResizeObserver 부재** (sim 한정)
   - 사이드바 드래그·창 리사이즈 시 마커 위치 어긋남, 영구 고정

4. **활성 마커 동기화 부재**
   - `simNavigateToMatch(idx)` 은 카드·하이라이트의 `.sim-active`/`.sim-item-active` 만 토글
   - 미니맵 마커 `.active` 클래스 갱신 누락 → "지금 어디 있는지" 미니맵으로 표시 안 됨

### 결론

**현재 sim 미니맵은 "장식 + 잘못된 위치"** 상태. 색은 정확히 표시되나 클릭 불가·리사이즈 무대응·활성 표시 없음·**위치 부정확**(마커가 매칭 시작점만 표시, 길이 정보 누락). 사용자 의심 정확함.

비교 모드 미니맵은 거의 완성품(블록 단위 + ResizeObserver + 클릭 + active + 비례 높이 모두 OK). 손볼 거 거의 없고 Phase 2 호버 툴팁만 추가 가능.

---

## 업계 표준 분석

### 미니맵/스크롤 어노테이션 패턴 4단계

| 단계 | 대표 사례 | 기능 |
|------|----------|------|
| **L1 — 어노테이션 스트립** | GitHub diff 우측, Chrome 검색 매치, Acrobat 코멘트 마커 | 색·위치 표시 + 클릭 점프. 미리보기 없음 |
| **L2 — 어노테이션 + 호버 툴팁** | PyCharm 우측 마커, IntelliJ Inspector | L1 + 호버 시 200~400px 폭 툴팁 (요약·라인 텍스트·심각도) |
| **L3 — 텍스처 미니맵** | VSCode, Sublime Text | 실제 텍스트 축소 렌더링 (canvas/SVG). 콘텐츠 형태 자체가 인식 단서 |
| **L4 — 라이브 프리뷰** | PyCharm "Preview Tab" 옵션 | 호버 시 본문 실제 영역을 부동 윈도우로 표시 |

### 도메인별 채택 경향
- **코드 에디터** (VSCode/Sublime/IntelliJ): L2~L3 표준
- **diff/리뷰** (GitHub/GitLab PR): L1 (충분)
- **표절 검사** (Turnitin/Copyleaks/iThenticate): **대부분 미니맵 자체를 안 씀** — 좌측 사이드바 매칭 리스트 + 본문 하이라이트로 충분
- **문서 비교** (Word·BeyondCompare·Araxis): L1

### 우리 컨텍스트 적정 수준 = **L2 (호버 툴팁까지)**
1. 분포 인지가 사용자 명시 가치 — L1 필수
2. 매칭 카드가 사이드바에 있어도 본문 위치를 빨리 알기 어려움 → L2 호버 툴팁이 큰 도움 (카테고리·점수·미리보기 60자)
3. L3 (텍스처)는 코드 아닌 문서라 가치 낮음
4. L4 (라이브 프리뷰)는 사이드바 카드 클릭으로 점프 가능하므로 중복

### 표준 multi-sentence 마커 패턴 (검증된 코드)
```js
var els = panelA.querySelectorAll('[data-sim-idx="' + i + '"]');
if (els.length === 0) continue;
var first = els[0], last = els[els.length - 1];
var topRatio = first.offsetTop / panelA.scrollHeight;
var bottomRatio = (last.offsetTop + last.offsetHeight) / panelA.scrollHeight;
var markTop = ARROW_H + topRatio * trackHA;
var markH = Math.max(3, (bottomRatio - topRatio) * trackHA);
```
PyCharm·VSCode·Chrome 검색 어노테이션이 모두 이 패턴(범위 시작 + 끝 element).

---

## 작업 범위

### Phase 1 — Critical 정상화 + 위치 정확도 (2시간)

**목표**: 클릭·리사이즈·활성·마커 길이·레이아웃 변동 모두 표준 패턴 적용. 옵션 A (제거) 백업안 보존.

#### Step 1.1 — `.sim-minimap-mark` CSS 클래스 추가
```css
/* css/compare.css L156 부근 (cp-minimap-mark.active 다음) */
.sim-minimap-mark {
    position: absolute;
    left: 1px;
    right: 1px;
    border-radius: 2px;
    pointer-events: auto;       /* 부모 .cp-minimap 의 none cascade 무력화 */
    cursor: pointer;
    opacity: 0.85;
    transition: opacity var(--transition-fast), transform var(--transition-fast);
}
.sim-minimap-mark:hover {
    opacity: 1;
    transform: scaleX(1.3);
    transform-origin: right center;
}
.sim-minimap-mark.active {
    opacity: 1;
    box-shadow: 0 0 0 1px var(--white), var(--shadow-sm);
}

/* 카테고리별 색상 (인라인 style 제거 → 클래스 cascade) */
.sim-minimap-mark.sim-mark-cat-identical       { background: var(--color-error); }
.sim-minimap-mark.sim-mark-cat-near_copy       { background: var(--color-warning); }
.sim-minimap-mark.sim-mark-cat-paraphrased     { background: var(--color-info); }
.sim-minimap-mark.sim-mark-cat-low_similarity  { background: var(--text-muted); }
.sim-minimap-mark.sim-mark-cat-excluded_auto   { background: var(--border-color); opacity: 0.5; }
.sim-minimap-mark.sim-mark-cat-excluded_manual { background: var(--text-muted); opacity: 0.5; }
```

#### Step 1.2 — `simRenderMinimap()` 재작성 (multi-sentence + 클래스 분리)
```js
// compare.html:3084 재작성
function simRenderMinimap() {
    var minimapA = document.getElementById('cp-minimap-a');
    var minimapB = document.getElementById('cp-minimap-b');
    if (!minimapA || !minimapB) return;

    minimapA.querySelectorAll('.sim-minimap-mark').forEach(function(m) { m.remove(); });
    minimapB.querySelectorAll('.sim-minimap-mark').forEach(function(m) { m.remove(); });
    if (!simLastResult) return;

    var panelA = document.getElementById('panel-body-a');
    var panelB = document.getElementById('panel-body-b');
    if (!panelA || !panelB) return;

    var ARROW_H = 14;
    var trackHA = minimapA.clientHeight - ARROW_H * 2;
    var trackHB = minimapB.clientHeight - ARROW_H * 2;
    if (trackHA <= 0 || trackHB <= 0) return;

    var matches = simLastResult.matches || [];
    var settings = simLoadCheckSettings();
    for (var i = 0; i < matches.length; i++) {
        var m = matches[i];
        var card = document.querySelector('.sim-match-item[data-idx="' + i + '"]');
        if (card && card.style.display === 'none') continue;

        var cat = resolveCategory(m, settings);
        var colorClass = 'sim-mark-cat-' + cat;

        renderSpanMark(panelA, minimapA, i, ARROW_H, trackHA, colorClass);
        renderSpanMark(panelB, minimapB, i, ARROW_H, trackHB, colorClass);
    }

    // 활성 마커 동기화 (재렌더 후에도 active 유지)
    if (simActiveIdx != null) {
        document.querySelectorAll(
            '.sim-minimap-mark[data-sim-idx="' + simActiveIdx + '"]'
        ).forEach(function(m) { m.classList.add('active'); });
    }
}

// 매칭 i의 첫·끝 element를 한 마커로 (PyCharm 패턴)
function renderSpanMark(panel, minimap, idx, arrowH, trackH, colorClass) {
    var els = panel.querySelectorAll('[data-sim-idx="' + idx + '"]');
    if (els.length === 0 || panel.scrollHeight <= 0) return;
    var first = els[0], last = els[els.length - 1];
    var topRatio = first.offsetTop / panel.scrollHeight;
    var bottomRatio = (last.offsetTop + last.offsetHeight) / panel.scrollHeight;
    var mark = document.createElement('div');
    mark.className = 'sim-minimap-mark ' + colorClass;
    mark.style.top = (arrowH + topRatio * trackH) + 'px';
    mark.style.height = Math.max(3, (bottomRatio - topRatio) * trackH) + 'px';
    mark.dataset.simIdx = idx;
    minimap.appendChild(mark);
}
```

#### Step 1.3 — 클릭 위임 1회 등록 (모듈 초기화 시점)
```js
// compare.html 결과 처리 IIFE 또는 DOMContentLoaded 시점, 1회만
(function bindSimMinimapClickOnce() {
    [document.getElementById('cp-minimap-a'),
     document.getElementById('cp-minimap-b')].forEach(function(mm) {
        if (!mm) return;
        mm.addEventListener('click', function(e) {
            var mark = e.target.closest('.sim-minimap-mark');
            if (!mark) return;
            var idx = parseInt(mark.dataset.simIdx);
            if (!isNaN(idx)) {
                simNavigateToMatch(idx);
                simUpdateNavIndicator();
            }
        });
    });
})();
// → simRenderMinimap 내 forEach addEventListener 블록 삭제
```

#### Step 1.4 — ResizeObserver 추가 (sim 한정)
```js
// compare.html:4211 부근, diff ResizeObserver 옆
var simMinimapResizeTimer = null;
new ResizeObserver(function() {
    clearTimeout(simMinimapResizeTimer);
    simMinimapResizeTimer = setTimeout(function() {
        if (currentMode === 'similarity' && simLastResult) simRenderMinimap();
    }, 100);
}).observe(panelBodyA);
// panelBodyB 별도 관찰 불필요 — 좌우 동시 리사이즈, diff와 동일 패턴
```

#### Step 1.5 — 활성 마커 동기화 (simNavigateToMatch 보강)
```js
// compare.html:2960 부근 (simNavigateToMatch 끝)
function simHighlightMinimapActive(idx) {
    document.querySelectorAll('.sim-minimap-mark.active').forEach(function(m) {
        m.classList.remove('active');
    });
    document.querySelectorAll(
        '.sim-minimap-mark[data-sim-idx="' + idx + '"]'
    ).forEach(function(m) { m.classList.add('active'); });
}
// simNavigateToMatch 마지막 줄에 추가
simHighlightMinimapActive(idx);
```

#### Step 1.6 — 이미지·폰트 로드 후 재계산 (Cause C 해소)
```js
// simApplyHighlights 끝, simShowResults 가 채운 후 호출되는 지점
function simRecalcMinimapAfterLayoutSettle() {
    var panels = [
        document.getElementById('panel-body-a'),
        document.getElementById('panel-body-b')
    ];
    panels.forEach(function(panel) {
        if (!panel) return;
        // (1) 미로딩 이미지 로드 후 재계산
        panel.querySelectorAll('img').forEach(function(img) {
            if (!img.complete) {
                img.addEventListener('load', simRenderMinimap, { once: true });
                img.addEventListener('error', simRenderMinimap, { once: true });
            }
        });
    });
    // (2) 폰트 로딩 완료 후 재계산
    if (document.fonts && document.fonts.ready) {
        document.fonts.ready.then(function() {
            if (currentMode === 'similarity' && simLastResult) simRenderMinimap();
        });
    }
}
// simShowResults 의 simRenderMinimap() 호출 직후 1회 실행
```

**Phase 1 종료 시 상태**: 클릭·리사이즈·활성·multi-sentence 비례 높이·레이아웃 변동 대응 모두 정상.
**사용자 체감**: "이제 미니맵을 누르면 점프되고, 마커가 본문 하이라이트와 일치한다."

---

### Phase 2 — L2 호버 툴팁 (권장, 2~3시간)

**목표**: 마커에 마우스 올리면 매칭 미리보기 (PyCharm 패턴).

#### 툴팁 내용 (3줄)
1. 카테고리 라벨 + 유사도 % (예: "동일 · 98%")
2. 본문 첫 60자 (말줄임 ...)
3. (선택) 매칭 인덱스 (예: "#3 / 47")

#### 구현 방식 — 단일 부동 div + 위임
- 페이지에 `#sim-minimap-tooltip` 1개
- `mouseenter`/`mouseleave` 위임 (`mouseover`/`mouseout` 사용)
- 200ms delay (PyCharm 기본값)
- viewport 경계 보정 — 잘리면 반대 방향으로 표시
- 다크모드: `--popover-bg`, `--popover-bg-hover`
- z-index: 1500 (모달 2000 미만, 토스트 5000 미만 — 구현 시 1000→1500 상향, DR-W1)
- ESC 또는 스크롤 시 자동 닫힘

#### 구현 코드 (생략, Phase 2 진입 시 작성 — 사전 v1 계획서에 스케치 보존)

---

### Phase 3 — 코드 통합 (선택, 후속, 2~3시간)

**목표**: diff 미니맵과 sim 미니맵 코드 중복 해소. 별도 PR 권장.
**판단**: Phase 1·2 완료 후 사용성 만족 시 보류 가능. user-facing 변화 0.

---

## 옵션 A (백업안) — 제거

위 정상화가 어려워 보이거나 회귀 우려 시 대안. **현재 권장 안 함**.

### 근거
- 표절 검사 도메인 표준이 미니맵을 안 씀 (Turnitin/Copyleaks)
- 사이드바 카드가 카운트·점프 제공
- 본문 하이라이트 자체가 "지도"

### 작업 범위
- `.sim-minimap-mark` 관련 JS·CSS 모두 제거 (~80줄)
- diff 모드 미니맵은 그대로 유지
- 유사도 모드 진입 시 `cp-minimap-a/b` 컨테이너 자체를 `display: none` 토글
- 작업 30분, 회귀 위험 0

### 권장 0순위 아닌 이유
사용자 명시 가치 — "분포 인지" — 가 사이드바로 대체되지 않음. 옵션 A 는 Phase 1 시도 중 회귀 폭발 시의 비상 탈출구로만 보존.

---

## 영향 범위

| 파일 | Phase 1 | Phase 2 | Phase 3 |
|------|---------|---------|---------|
| `css/compare.css` | +35줄 (.sim-minimap-mark, 6 카테고리 색상) | +25줄 (툴팁) | -10줄 (정리) |
| `compare.html` | ±60줄 (simRenderMinimap 재작성, ResizeObserver, simHighlightMinimapActive, simRecalcMinimapAfterLayoutSettle, 클릭 1회 등록) | +60줄 (showTooltip IIFE) | -100줄 통합 시 |
| **백엔드** | **무관** | **무관** | **무관** |
| **데이터·SSOT** | **무관** | **무관** | **무관** |
| **다른 모드 영향** | 없음 (sim-* 접두사 격리) | 없음 | diff 미니맵 동작 동일성 검증 필요 |

---

## 리스크

| 리스크 | 확률 | 완화 |
|--------|------|------|
| diff 미니맵 회귀 (실수로 `.cp-minimap-mark` 규칙 변경) | 낮 | sim 코드는 `.sim-minimap-mark` 별도 클래스만 사용, diff 코드 손대지 않음 |
| `simHighlightMinimapActive` 와 `simRenderMinimap` 사이 race (재계산 중 active 마커 사라짐) | 중 | `simRenderMinimap` 끝에서 `simActiveIdx` 기준 active 재부여 (Step 1.2 마지막 블록) |
| 툴팁 z-index 모달 위로 뜸 | 낮 | `z-index: 1500` 명시 (모달 2000 미만 — 구현 시 1000→1500 상향) |
| 다크모드 `text-muted` (low_similarity) 가시성 부족 | 중 | tokens.css 다크값 `#9ca3af` 검증, 필요 시 `opacity` 보강 |
| 짧은 마커(3px)에서 hover 트리거 어려움 | 낮 | `:hover { transform: scaleX(1.3) }` 이미 적용 |
| `document.fonts.ready` 미지원 브라우저 | 낮 | 옵셔널 체이닝 — 미지원 시 ResizeObserver 가 폴백 |
| `panelB` ResizeObserver 누락 | 낮 | A 만 관찰 (좌우 동시 리사이즈), diff 와 동일 |
| 이미지 로드 무한 루프 | 낮 | `{ once: true }` 옵션으로 1회만 등록 |
| 활성 마커가 필터 OFF 카테고리에 속한 경우 마커 자체가 없음 | 중 | `simHighlightMinimapActive` 가 `querySelectorAll` 후 length 0 체크 (no-op) |

---

## 검증 계획

### 자동
- 단위 테스트 21/21 PASS 유지 (`tests/sim_phase2_test.js`)
- `bash tests/sim_label_consistency.sh` PASS (라벨 SSOT 우회 없음)
- `vm.Script` 구문 errors 0

### Playwright (필수)
- 라이트·다크 양쪽 미니맵 마커 정상 렌더 확인
- **클릭 작동** — 임의 마커 클릭 → 해당 매칭 카드 active + 본문 스크롤
- **위치 정확도** — 마커 top·height 가 첫·마지막 sentence 의 실제 화면 위치와 일치 (5문장 매칭 기준 실측)
- **활성 마커** — 사이드바 다음/이전 → 미니맵 active 동기 갱신
- **리사이즈** — 사이드바 폭 조절 후 마커 위치 정확
- **필터 응답** — "약한 유사" OFF → 약한 유사 마커 사라짐 + 나머지 마커 위치 변화 (본문 layout 변경 반영)
- **이미지 포함 문서** — 이미지 로드 후 마커 위치 자동 보정
- 누적 핸들러 검증 — DevTools `getEventListeners(minimapA)` 클릭 1개만 (재계산 N회 후에도)
- (Phase 2) 호버 200ms 후 카테고리·점수·스니펫 표시. ESC·스크롤 시 닫힘. viewport 경계 보정

### 회귀 스팟체크
- diff 모드 미니맵 — 클릭/active/리사이즈 모두 동일 작동 (`.cp-minimap-mark` 손대지 않으므로 영향 0 예상)
- 모달(Modal A·B) 열린 상태에서 미니맵 호버 — 툴팁 z-index 충돌 없음

### 수동 체크 (최종)
- M1: 매칭 1개의 카테고리·색·라벨이 사이드바·본문·미니맵 3경로 동기 (V1 불변 재확인)
- M2: 필터 OFF → 사이드바 카드·본문 하이라이트·미니맵 마커 3경로 동시 사라짐
- M3: 미니맵 마커 클릭 → simNavigateToMatch 발화 → 본문 스크롤 + active 표시
- M4: 사이드바 다음/이전 → 미니맵 active 마커 이동
- M5: 사이드바 폭 드래그 → 미니맵 마커 위치 자동 보정
- M6: 5문장 매칭 마커 — 첫 문장부터 마지막 문장까지 세로로 길게 1개 마커 (분포 인지 가치 회복)

---

## 수용 기준 (Phase 1+2 완료 시)

- [ ] sim 미니맵 마커 클릭 → 매칭 점프
- [ ] 클릭 핸들러 1개 (재계산 N회 후에도 누적 0)
- [ ] 사이드바 리사이즈 시 마커 위치 정확
- [ ] 사이드바 다음/이전 버튼 → 미니맵 active 표시
- [ ] **마커 높이가 매칭 span 길이에 비례** (첫 sentence 의 top + 마지막 sentence 의 bottom)
- [ ] **이미지·폰트 로드 후 마커 위치 자동 보정** (mismatch Cause C 해소)
- [ ] 필터 OFF/ON 시 마커 정확 동기 (V1 불변)
- [ ] 호버 200ms 후 툴팁 (카테고리·점수·스니펫 60자) — Phase 2
- [ ] 라이트·다크 모드 모두 WCAG AA 통과
- [ ] 단위 테스트 21/21 PASS · sim_label_consistency PASS
- [ ] design-reviewer Critical 0
- [ ] code-reviewer Critical 0
- [ ] diff 모드 미니맵 회귀 0

---

## 실행 단위 / 커밋 분할 제안

1. **커밋 1** (Phase 1.1~1.6) — `버그 [Verify/Compare] 유사도 미니맵 핵심 결함 5건 정상화 + 위치 정확도 개선`
   - sim-minimap-mark CSS 클래스 추가 (pointer-events: auto, 6 카테고리 색상)
   - simRenderMinimap multi-sentence 마커 (querySelectorAll 첫·끝 + 길이 비례)
   - 클릭 위임 1회 등록 (누적 해소)
   - ResizeObserver 추가
   - 활성 마커 동기화
   - 이미지·폰트 로드 후 재계산

2. **커밋 2** (Phase 2) — `추가 [Verify/Compare] 유사도 미니맵 호버 툴팁 (PyCharm 패턴 L2)`
   - sim-minimap-tooltip DOM/CSS
   - 호버 200ms delay + viewport 경계 보정
   - ESC/스크롤 자동 닫힘

3. **커밋 3** (Phase 3, 선택) — `리팩토링 [Verify/Compare] diff·sim 미니맵 공통 코어 통합`

---

## 우선순위 / 의사결정 포인트

| 결정 | 권장 |
|------|------|
| Phase 1 만? Phase 2 까지? | **Phase 1+2 권장** — Phase 1 만으로는 "고장났던 게 정상화"에 그쳐 사용자 체감 가치 낮음. Phase 2 까지 가야 "미니맵이 풍성하다" |
| Phase 3 (코드 통합) 시점 | **보류** — 다음 미니맵 관련 Plan 발생 시 같이 처리 |
| 다른 모드(diff)도 같은 패턴 적용? | Phase 2 호버 툴팁은 diff 에도 가치 있음. diff 카테고리(added/deleted/modified) 별도 PR로 분리 권장 |
| 옵션 A (제거) 시점 | Phase 1 회귀 폭발 시 비상 탈출구로만 |

---

## 잔여·후속 가능 항목 (이번 범위 외)

- diff 모드 호버 툴팁 (Phase 2 패턴 재사용 — 별 PR)
- 미니맵에 카테고리별 시각 토글(필터 칩과 별도) — 사용자 요청 시
- 모바일 터치 지원 — 현재 데스크탑 전용 가정
- 미니맵 우측 좁아 좌우 패널 사이드바 호버 시 툴팁 가림 → 좌측 표시 우선 정책
