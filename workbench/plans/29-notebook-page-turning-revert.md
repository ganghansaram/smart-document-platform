# Plan-29: Notebook 좌측 패널 페이지넘김 복원 ✅ 완료

> **목표**: 좌측 원문 PDF 패널을 연속 스크롤(Plan-26 Phase 2-α)에서 페이지넘김 방식으로 복원  
> **동기**: 우측 번역 PDF가 기술적 한계(페이지별 독립 PDF)로 연속 스크롤 불가 → 좌우 경험 불일치  
> **방침**: 수동 패치(B안) — 이후 커밋의 유용한 변경(캐시 최적화, 웹뷰 전체모드 등)을 보존  
> **완료**: 2026-04-07 — 커밋 `3e62107`, 3파일 350줄 제거

---

## 0. 현재 상태 vs 목표 상태

### 현재 (연속 스크롤)
```
좌측: $leftPagesStack 안에 전체 페이지 wrapper 배열 → IntersectionObserver로 가시 페이지만 렌더
우측 PDF: 단일 canvas 교체 (페이지넘김)
우측 웹뷰: 전체 문서 연속 스크롤 + 양방향 Observer 동기화
```

### 목표 (페이지넘김)
```
좌측: $leftContainer 안에 단일 canvas → goToPage() 시 renderLeftPage()로 교체
우측 PDF: 변경 없음 (기존 페이지넘김 유지)
우측 웹뷰: 변경 없음 (전체 문서 모드 유지, 동기화 방식만 단순화)
```

### 참고 커밋
- `d3a06a5` — Phase 2-α 좌측 연속 스크롤 도입
- `d3a06a5^` — 도입 직전 상태 (페이지넘김, 복원 대상 참조)
- `10ac310` — 우측 연속 스크롤 시도 후 롤백한 전력

---

## 1. 변경 대상 파일 (3개)

| 파일 | 변경 유형 | 범위 |
|------|----------|------|
| `translator.html` | HTML 구조 복원 | 3줄 교체 |
| `js/translator.js` | 핵심 로직 교체 | ~200줄 수정/제거, ~50줄 신규 |
| `css/translator.css` | CSS 정리 | `.pdf-pages-stack`, `.pdf-page-wrapper` 관련 |

---

## 2. 단계별 작업

### Step 1: translator.html — 좌측 패널 DOM 복원

**현재** (L149~153):
```html
<div class="panel-scroll" id="left-scroll">
    <div class="pdf-pages-stack" id="left-pages-stack">
        <!-- Phase 2-α: 페이지 wrapper가 JS로 동적 생성됨 -->
    </div>
</div>
```

**복원**:
```html
<div class="panel-scroll" id="left-scroll">
    <div class="pdf-page-container" id="left-page-container">
        <canvas id="left-canvas"></canvas>
        <div class="text-layer" id="left-text-layer"></div>
        <div class="annotation-layer" id="left-annotation-layer"></div>
    </div>
</div>
```

- `pdf-pages-stack` → `pdf-page-container` (우측과 동일 구조)
- 정적 canvas + text-layer + annotation-layer 복원

---

### Step 2: translator.js — 변수 선언부 복원 (L102~135)

**제거**:
```
$leftPagesStack, _pageViewports[], _pageWrappers[], _renderedPages{},
_leftObserver, _leftRenderTasks{}, _BUFFER
_dummyDiv, _dummyCanvas, _syncLeftRefs()
```

**복원** (d3a06a5^ 참조):
```js
// Left panel
var $panelLeft      = document.getElementById('panel-left');
var $leftScroll     = document.getElementById('left-scroll');  // 유지
var $leftCanvas     = document.getElementById('left-canvas');
var $leftContainer  = document.getElementById('left-page-container');
var $leftTextLayer  = document.getElementById('left-text-layer');
var $leftAnnotationLayer = document.getElementById('left-annotation-layer');
```

**주의**: `$leftCanvas`, `$leftContainer`, `$leftTextLayer`, `$leftAnnotationLayer`를 참조하는 기존 코드(마킹, 클릭 네비게이션 등 17곳)가 이 변수명에 의존. 변수명을 그대로 유지하면 이 코드들은 **수정 불필요**.

참조 위치 (변경 불필요 — 변수명 유지 시 자동 해소):
- L2386: `$leftContainer.getBoundingClientRect()` (마킹)
- L2485: `$leftAnnotationLayer.getBoundingClientRect()` (액션바)
- L2566: `$leftAnnotationLayer.appendChild($actionBar)` (액션바)
- L2627: `$leftAnnotationLayer.appendChild($aiPopover)` (AI 팝오버)
- L2851: `$leftContainer.getBoundingClientRect()` (팝오버)
- L2857: `$leftAnnotationLayer.appendChild($popover)` (팝오버)
- L3529: `$leftAnnotationLayer.querySelector(...)` (마킹 삭제)
- L5085~5130: `$leftContainer.querySelector/appendChild(...)` (네비 박스)

---

### Step 3: translator.js — loadLeftPdf() 교체 (L599~651)

**현재**: 전체 페이지 wrapper 생성 + Observer 호출 (53줄)

**복원** (d3a06a5^ 기반, ~12줄):
```js
function loadLeftPdf() {
    if (leftPdfDoc) { leftPdfDoc.destroy(); leftPdfDoc = null; }
    var url = API + '/api/translator/pdf/' + currentDocId;
    pdfjsLib.getDocument({ url: url, withCredentials: true }).promise.then(function(pdf) {
        leftPdfDoc = pdf;
        totalPages = pdf.numPages;
        updatePageNav();
        renderLeftPage(currentPage);
    }).catch(function(err) {
        console.error('[PDF.js] left load error:', err);
    });
}
```

**변경점**: `_teardownAllPages()` 호출 제거, `$leftPagesStack.innerHTML` 제거, wrapper 생성 제거, Observer 호출 제거

---

### Step 4: translator.js — 연속 스크롤 전용 함수 제거 (4개)

| 함수 | 줄번호 | 행동 |
|------|--------|------|
| `_setupLeftObserver()` | L653~691 | **전체 제거** |
| `_updateVisiblePages()` | L693~710 | **전체 제거** |
| `_teardownPage(pageNum)` | L798~818 | **전체 제거** |
| `_teardownAllPages()` | L820~827 | **전체 제거** |

**주의**: `_teardownAllPages()`는 `destroyPdfs()` (L571)과 `loadLeftPdf()` (L601)에서 호출됨.
- `destroyPdfs()`에서는 `leftRenderTask` cancel로 대체
- `loadLeftPdf()`에서는 제거 (단일 canvas라 불필요)

---

### Step 5: translator.js — renderLeftPage() 교체 (L712~796)

**현재**: wrapper 내 canvas/textLayer/annLayer를 동적 생성 (85줄)

**복원** (d3a06a5^ 기반): 단일 canvas에 직접 렌더. 변수 `leftRenderTask` 추가 필요.

핵심 차이:
- `var wrapper = _pageWrappers[pageNum - 1]` → `$leftContainer` 직접 사용
- `_renderedPages[pageNum] = true` → 불필요 (단일 페이지만 존재)
- canvas 동적 생성 → `$leftCanvas` 재사용
- text-layer 동적 생성 → `$leftTextLayer.innerHTML = ''` 후 재사용
- annotation-layer → `$leftAnnotationLayer` 재사용
- `_renderAnnotationsForPage()` → `renderAnnotations()` 호출로 복원

**추가 변수**: `var leftRenderTask = null;` (L110 부근에 선언)

---

### Step 6: translator.js — goToPage() 수정 (L2102~2145)

**현재 (L2112~2114)**:
```js
// Left: 해당 페이지로 스크롤 (연속 스크롤 — 렌더는 Observer가 관리)
var targetWrapper = _pageWrappers[currentPage - 1];
if (targetWrapper) targetWrapper.scrollIntoView({ block: 'start' });
```

**복원**:
```js
// Left: 원문 렌더링
renderLeftPage(currentPage);
var leftScroll = document.getElementById('left-scroll');
if (leftScroll) leftScroll.scrollTop = 0;
```

- `_syncLeftRefs()` 호출 제거 (L2110) — 직접 DOM 참조이므로 불필요

---

### Step 7: translator.js — _rerenderVisiblePages() → renderLeftPage() (L2187~2209)

**현재**: 모든 wrapper 크기 재계산 + 가시 범위 해제/재렌더 (23줄)

**복원**: 단순히 현재 페이지 재렌더
```js
function _rerenderVisiblePages() {
    renderLeftPage(currentPage);
}
```

호출 위치 3곳 (L990, L1105, L2176) — 함수명 유지하므로 변경 불필요.

---

### Step 8: translator.js — renderAnnotations() 단순화 (L2293~2320)

**현재**: `_renderedPages`를 순회하며 여러 페이지의 annotation layer를 갱신

**복원**: 현재 페이지의 `$leftAnnotationLayer`만 갱신 (d3a06a5^ 참조)
```js
function renderAnnotations() {
    // popover 등 보존
    var savedPopover = $popover;
    // ... (기존 보존 로직 유지)
    $leftAnnotationLayer.innerHTML = '';
    // annotationsCache에서 currentPage 마킹만 렌더
    if (annotationsCache && annotationsCache.highlights) {
        for (var i = 0; i < annotationsCache.highlights.length; i++) {
            if (annotationsCache.highlights[i].page === currentPage) {
                $leftAnnotationLayer.appendChild(createHighlightDiv(annotationsCache.highlights[i]));
            }
        }
    }
    // popover 등 복원
    // ...
}
```

`_renderAnnotationsForPage()` 헬퍼도 제거 가능 (인라인화).

---

### Step 9: translator.js — 이벤트 위임 수정 (L2724~2726)

**현재**:
```js
$leftPagesStack.addEventListener('mouseup', function(e) {
    if (!e.target.closest('.text-layer')) return;
```

**복원**: `$leftPagesStack` → `$leftContainer` (또는 `$leftAnnotationLayer.parentNode`)
```js
$leftContainer.addEventListener('mouseup', function(e) {
    if (!e.target.closest('.text-layer')) return;
```

---

### Step 10: translator.js — syncScroll 정리 (L2226~2245)

**현재**: 좌우 `scrollTop` 비율 동기화 — 연속 스크롤에서만 의미 있음

**복원 후**: 좌측이 단일 페이지이므로 `scrollTop` 비율 동기화는 무의미.
- `syncScroll()` 함수 제거
- `$leftScroll.addEventListener('scroll', ...)` 제거
- `$rightScroll.addEventListener('scroll', ...)` 제거

**주의**: `scrollSyncEnabled` 변수와 `$scrollSyncBtn` 토글은 유지 — `_emitPageChanged()`에서 여전히 사용 (페이지 단위 동기화 제어).

---

### Step 11: translator.js — 웹뷰 → 좌측 동기화 수정 (L1637~1643)

**현재**:
```js
_syncLeftRefs();
// 연속 스크롤: 좌측 해당 페이지로 스크롤 (Observer가 렌더 관리)
var w = _pageWrappers[currentPage - 1];
if (w) w.scrollIntoView({ block: 'start' });
```

**복원**:
```js
renderLeftPage(currentPage);
```

---

### Step 12: translator.js — destroyPdfs() 정리 (L570~582)

**현재 (L571)**: `_teardownAllPages()` 호출

**복원**: `leftRenderTask` cancel로 대체
```js
if (leftRenderTask) { leftRenderTask.cancel(); leftRenderTask = null; }
```

---

### Step 13: css/translator.css — 연속 스크롤 전용 스타일 정리

**제거 대상** (L1003~1035):
```css
/* 좌측 연속 스크롤 스택 (Phase 2-α) */
.pdf-pages-stack { ... }
.pdf-page-wrapper { ... }
.pdf-page-wrapper canvas { ... }
.pdf-page-wrapper .text-layer { ... }
.pdf-page-wrapper .annotation-layer { ... }
```

이 클래스들은 좌측 연속 스크롤 전용이며 다른 곳에서 사용되지 않음.

---

## 3. 변경하지 않는 것 (명시적 제외)

| 항목 | 이유 |
|------|------|
| 우측 PDF 렌더 (`renderRightPage`, `_rightPdfCache`, 프리로드) | 우측은 이미 페이지넘김, 544d6a9 캐시 최적화 보존 |
| 웹뷰 전체모드 (`showRightWebViewFull`, 인라인 번역) | a31fa2d 개선 보존, 동기화 방향만 변경 |
| `_emitPageChanged()` | 트리거만 바뀜(Observer→버튼), 함수 자체는 유지 |
| `webFullViewObserver` + `_scrollFullViewToPage()` | 웹뷰↔좌측 동기화 유지 필요 |
| 번역 요청/폴링, 카드 목록, 업로드 | 좌측 렌더링과 무관 |
| AI 요약, Q&A, 트리 패널, 검색 오버레이 | 좌측 렌더링과 무관 |
| 줌 (zoom 변수, ZOOM_MIN/MAX/STEP) | `rerenderBothPanels()` 경유, 내부 함수만 단순화 |
| 키보드 단축키 (ArrowLeft/Right) | `goToPage()` 호출, 함수 시그니처 불변 |

---

## 4. 검증 체크리스트

### 기본 동작
- [ ] PDF 로드 → 첫 페이지 렌더 정상
- [ ] 이전/다음 버튼 → 페이지 전환 + 좌측 렌더
- [ ] 키보드 ArrowLeft/Right → 페이지 전환
- [ ] 페이지 번호 표시 ("N / M") 갱신
- [ ] 줌 인/아웃 → 좌측 재렌더
- [ ] 브라우저 리사이즈 → 좌측 재렌더

### 좌우 동기화
- [ ] 좌측 페이지 이동 → 우측 PDF 번역 표시 갱신
- [ ] 좌측 페이지 이동 → 우측 웹뷰 해당 섹션으로 스크롤
- [ ] 우측 웹뷰 스크롤 → 좌측 해당 페이지 렌더 (webFullViewObserver)
- [ ] 스크롤 동기화 버튼 ON/OFF → 동기화 제어

### 마킹/형광펜
- [ ] 텍스트 드래그 → 형광펜 액션바 표시
- [ ] 형광펜 추가 → annotation layer에 렌더
- [ ] 페이지 전환 후 복귀 → 마킹 복원
- [ ] 형광펜 클릭 → 팝오버 표시
- [ ] 형광펜 삭제 → 즉시 반영

### 클릭 네비게이션
- [ ] 좌측 PDF 클릭 → 네비 박스 표시 → 우측 번역 반영
- [ ] `_navScale`, `_navPdfViewport` 갱신 정상

### 엣지 케이스
- [ ] 1페이지 PDF → 이전/다음 비활성화
- [ ] 50+ 페이지 PDF → 메모리 누수 없음 (단일 canvas)
- [ ] 문서 전환 (카드 목록 → 다른 문서) → 이전 PDF 정리
- [ ] 번역 엔진 전환 (PDF↔웹뷰) → 좌측 영향 없음

---

## 5. 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| `$leftPagesStack` 참조 누락 | JS 에러 | grep으로 전수 확인 완료 (L105, L602, L641, L2725 — 4곳) |
| `_renderedPages` 참조 누락 | 조건 분기 오류 | grep 확인 완료 (L108, L706, L713, L717, L721, L778, L799, L800, L825, L2295 — 10곳, 모두 제거 대상 함수 내부) |
| `_syncLeftRefs()` 호출 누락 | 변수 갱신 실패 | 직접 DOM 참조로 전환하면 함수 자체 불필요 (L122, L674, L791, L1640, L2110 — 5곳, 모두 제거) |
| renderAnnotations() 변경 시 popover 소실 | 마킹 UI 깨짐 | 기존 보존 로직(L2303~2316) 그대로 이식 |
| 웹뷰→좌측 동기화 경로 변경 누락 | 동기화 안 됨 | L1640~1643 수정 확인 |

---

## 6. 작업 순서

1. Step 1 (HTML) → Step 2 (변수) → Step 3 (loadLeftPdf) — 기반 구조 복원
2. Step 4 (함수 제거) → Step 5 (renderLeftPage) — 핵심 렌더 로직
3. Step 6 (goToPage) → Step 7 (_rerenderVisiblePages) — 페이지 이동
4. Step 8 (renderAnnotations) → Step 9 (이벤트 위임) — 마킹
5. Step 10 (syncScroll) → Step 11 (웹뷰 동기화) → Step 12 (destroyPdfs) — 정리
6. Step 13 (CSS) — 스타일 정리
7. 검증 (4절 체크리스트)
