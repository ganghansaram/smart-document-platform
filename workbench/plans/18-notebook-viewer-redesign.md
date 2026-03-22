# Plan 18: Notebook 뷰어 레이아웃 재설계

> 작성일: 2026-03-23
> 상태: 설계 중
> 브랜치: `plan18-viewer`
> 선행: Plan 17 Phase 5 완료 (텍스트 모드 제거 + Notebook 리네이밍)
> 관련: Plan 17 Phase 4b/4c/4d — 본 계획 완료 후 새 레이아웃 위에서 진행

---

## 1. 목적

현재 "번역 상태에 따라 싱글/듀얼이 자동 전환되는" 뷰어를
**"중앙 원문 + 우측 아이콘 레일 + 슬라이드 패널"** 구조로 재설계한다.

사용자가 필요한 도구를 직접 열고 닫는 **문서 워크벤치** 패턴으로 전환하여,
번역 여부와 무관하게 일관된 읽기 경험을 제공한다.

## 2. 배경

### 2.1 현재 구조의 문제

| 문제 | 상세 |
|------|------|
| **레이아웃 제어권이 시스템에 있음** | 번역 없으면 싱글, 있으면 듀얼 — 사용자 선택 불가 |
| **툴바가 모드에 따라 변신** | PDF 모드/웹뷰 모드에 따라 버튼이 나타나고 사라짐 |
| **번역 없는 문서의 자리가 없음** | 한국어 문서도 번역 중심 UI를 통과해야 함 |
| **기능 확장 시 레이아웃 재설계 필요** | AI 챗봇, 검색 결과 등 추가할 때마다 패널 구조 변경 |

### 2.2 업계 사례

| 제품 | 패턴 |
|------|------|
| **NotebookLM** | 중앙 콘텐츠 + 우측 패널 (최소화 시 아이콘 레일) |
| **PyCharm / VS Code** | 에디터 중앙 + 좌/우 Tool Window (아이콘 레일 + 슬라이드 패널) |
| **Notion** | 메인 콘텐츠 + 우측 사이드바 (댓글, 속성) |

### 2.3 핵심 전환

**"번역기 뷰어" → "문서 워크벤치"**

- 원문 PDF가 항상 중앙에 전체 너비로 존재 (기본 상태)
- 번역/메모/용어집 등은 우측 패널의 **도구(tool)**
- 사용자가 도구를 열면 중앙이 축소되며 패널이 슬라이드
- 도구를 닫으면 원문이 다시 전체 너비로 복귀

---

## 3. 레이아웃 설계

### 3.1 기본 상태 (모든 패널 닫힘)

```
┌─────────────────────────────────────────────────────┬──┐
│ [◀ ▶ 1/4] [🔍 100% ±] [⬇]                          │  │
├─────────────────────────────────────────────────────┤📄│
│                                                     │  │
│                                                     │📝│
│              원문 PDF (전체 너비)                      │  │
│              마킹/하이라이트/메모 가능                   │📋│
│                                                     │  │
│                                                     │📖│
│                                                     │  │
│                                                     │💬│
│                                                     │  │
└─────────────────────────────────────────────────────┴──┘
```

### 3.2 패널 열림 상태 (예: PDF 번역)

```
┌──────────────────────────┬────────────────────┬──┐
│ [◀ ▶ 1/4] [🔍 100% ±]   │                    │  │
├──────────────────────────┤ PDF 번역 결과       │📄│← 활성
│                          │                    │  │
│                          │ [모델 ▾] [번역 ▶]   │📝│
│   원문 PDF (축소)         │ [스크롤 동기화 ☐]   │  │
│                          │                    │📋│
│                          │ ┌──────────────┐   │  │
│                          │ │ 번역된 PDF    │   │📖│
│                          │ │              │   │  │
│                          │ └──────────────┘   │💬│
│                          │                    │  │
└──────────────────────────┴────────────────────┴──┘
```

### 3.3 아이콘 레일 구성

| 순서 | 아이콘 | 패널 이름 | 내용 |
|:----:|:------:|----------|------|
| 1 | 📄 | PDF 번역 | 모델 선택, 번역/취소, 범위 번역, 스크롤 동기화, 번역 PDF 뷰어 |
| 2 | 📝 | 웹 뷰 번역 | 모델 선택, 번역/취소, 폰트 크기, 전체 문서 토글, Markdown 렌더 |
| 3 | 📋 | 메모 | 메모 목록 (페이지별), 메모 검색, 메모 추가 |
| 4 | 📖 | 용어집 | 용어 목록, 추가/편집/삭제 (현재 모달 → 패널로 이관) |
| 5 | 💬 | AI 챗봇 | 현재 문서 기반 질의 (Plan 17 Phase 6 예정, 자리만 확보) |

> 아이콘은 실제 구현 시 SVG로 교체. 위 이모지는 설계 참고용.

### 3.4 패널 동작 규칙

1. **한 번에 하나만** — 아이콘 클릭 시 해당 패널 열림, 다른 패널은 자동 닫힘
2. **토글** — 이미 열린 아이콘을 다시 클릭하면 패널 닫힘 (싱글 뷰로 복귀)
3. **슬라이드 애니메이션** — `var(--transition-normal)` 사용, 중앙 패널 flex 축소
4. **패널 너비** — 기본 50% (현재 듀얼과 동일), 리사이즈 핸들로 조절 가능
5. **상태 유지** — 열린 패널 ID를 `localStorage`에 저장, 재방문 시 복원

---

## 4. 툴바 재배치

### 4.1 툴바에 남는 항목 (공통, 모든 상태에서 동일)

| 항목 | 현재 id | 비고 |
|------|---------|------|
| 페이지 네비게이션 | `page-prev`, `page-next`, `page-info` | 변경 없음 |
| PDF 줌 | `zoom-out`, `zoom-in`, `zoom-level` | 변경 없음 |
| 다운로드 | `download-btn` + 메뉴 | 메뉴 내용은 열린 패널에 따라 동적 |
| 검색 | 헤더의 `Search` | 변경 없음 |

### 4.2 패널 내부로 이동하는 항목

| 항목 | 현재 id | 이동 대상 패널 |
|------|---------|---------------|
| 모델 선택 | `model-select` | PDF 번역 / 웹뷰 번역 패널 상단 |
| 번역 버튼 | `translate-page-btn` | 각 번역 패널 상단 |
| 재번역 버튼 | (translate-page-btn 상태) | 각 번역 패널 상단 |
| 취소 버튼 | `cancel-page-btn` | 각 번역 패널 상단 |
| 범위 번역 | `range-translate-btn` | PDF 번역 패널 |
| 번역 상태 텍스트 | `toolbar-page-status` | 각 번역 패널 상단 |
| 스크롤 동기화 | `scroll-sync-btn` | PDF 번역 패널 |
| 폰트 크기 | `font-scale-controls` | 웹뷰 번역 패널 |
| 전체 문서 토글 | `web-full-toggle` | 웹뷰 번역 패널 |

### 4.3 제거되는 항목

| 항목 | 현재 id | 이유 |
|------|---------|------|
| 엔진 토글 (PDF/웹뷰) | `engine-toggle` | 아이콘 레일이 대체 |

---

## 5. 기존 기능 이관 매핑

### 5.1 PDF 번역 패널

현재 `translateEngine === 'pdf'` 분기의 모든 코드가 이 패널로 이관:

| 기존 코드 | 이관 방식 |
|-----------|----------|
| `updateRightPanel()` PDF 분기 (js:659~) | 패널 내부 `updatePdfPanel()` |
| `showRightTranslatedPage()` (js:687) | 패널 내부 PDF.js 로드 |
| `startPolling()` / `stopPolling()` (js:1461~) | 패널 활성 시에만 폴링 |
| `pageStatusCache` | 유지 (패널 독립) |
| 범위 번역 다이얼로그 | 패널 내부 인라인 또는 기존 모달 유지 |

### 5.2 웹뷰 번역 패널

현재 `translateEngine === 'web'` 분기의 모든 코드:

| 기존 코드 | 이관 방식 |
|-----------|----------|
| `updateRightPanel()` 웹뷰 분기 (js:555~) | 패널 내부 `updateWebPanel()` |
| `showRightWebView()` (js:715) | 패널 내부 Markdown 렌더 |
| `showRightWebViewFull()` (js:759) | 패널 내부 전체 문서 모드 |
| `startWebPolling()` / `stopWebPolling()` | 패널 활성 시에만 폴링 |
| `webPageStatusCache` | 유지 (패널 독립) |

### 5.3 메모 패널 (신규)

현재 마킹/메모는 PDF 텍스트 레이어 위에서 동작하며 별도 목록 UI가 없음.
메모 패널은 **기존 메모 기능의 목록 뷰**를 제공:

- 현재 문서의 전체 메모 목록 (페이지별 그룹)
- 메모 클릭 → 좌측 PDF 해당 위치로 스크롤
- 메모 추가/편집/삭제 (기존 API 재사용)

> 마킹/하이라이트 자체는 좌측 PDF 텍스트 레이어에서 계속 동작 (변경 없음).

### 5.4 용어집 패널

현재 모달(`#glossary-modal`)을 패널로 이관:

- 용어 목록 표시 (현재 모달 내용 그대로)
- 추가/편집/삭제 인라인
- 패널이므로 원문 PDF를 보면서 동시에 용어집 편집 가능 (모달의 한계 해소)

---

## 6. DOM 구조 변경

### 6.1 현재 → 신규

```html
<!-- 현재 -->
<div class="viewer-panels" id="viewer-panels">
    <div class="viewer-panel" id="panel-left">...</div>
    <div class="viewer-panel" id="panel-right">...</div>
</div>

<!-- 신규 -->
<div class="viewer-panels" id="viewer-panels">
    <div class="viewer-panel viewer-main" id="panel-main">
        <!-- 원문 PDF (기존 panel-left 내용) -->
    </div>
    <div class="viewer-side-panel" id="side-panel" style="display:none">
        <!-- 활성 도구 패널 내용 (동적) -->
        <div class="side-panel-header">
            <span class="side-panel-title">PDF 번역</span>
            <button class="side-panel-close">✕</button>
        </div>
        <div class="side-panel-body" id="side-panel-body">
            <!-- 각 도구별 컨텐츠가 여기에 렌더 -->
        </div>
    </div>
    <div class="icon-rail" id="icon-rail">
        <button class="rail-btn" data-panel="pdf-translate" title="PDF 번역">
            <svg>...</svg>
        </button>
        <button class="rail-btn" data-panel="web-translate" title="웹 뷰 번역">
            <svg>...</svg>
        </button>
        <button class="rail-btn" data-panel="memo-list" title="메모">
            <svg>...</svg>
        </button>
        <button class="rail-btn" data-panel="glossary" title="용어집">
            <svg>...</svg>
        </button>
        <button class="rail-btn" data-panel="ai-chat" title="AI 챗봇" disabled>
            <svg>...</svg>
        </button>
    </div>
</div>
```

### 6.2 CSS 핵심

```css
.viewer-panels {
    flex: 1;
    display: flex;
    overflow: hidden;
}

.viewer-main {
    flex: 1;
    overflow: auto;
    transition: flex var(--transition-normal);
}

.viewer-side-panel {
    width: 0;
    overflow: hidden;
    transition: width var(--transition-normal);
    border-left: 2px solid var(--border-color);
}

.viewer-side-panel.open {
    width: 50%;   /* 기본값, 리사이즈 핸들로 조절 */
}

.icon-rail {
    width: 40px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    padding: 8px 0;
    border-left: 1px solid var(--border-color);
    background: var(--bg-secondary);
}

.rail-btn {
    width: 32px;
    height: 32px;
    border-radius: var(--radius-sm);
    /* tokens.css 변수 사용 */
}

.rail-btn.active {
    background: var(--active-color);
    color: #fff;
}
```

---

## 7. 실행 계획

### Phase 1: 아이콘 레일 + 패널 프레임 — 2일

- ⬜ DOM 구조 변경 (panel-left → panel-main, panel-right → side-panel + icon-rail)
- ⬜ 아이콘 레일 UI (5개 버튼, SVG 아이콘)
- ⬜ 패널 열기/닫기 애니메이션 (CSS transition)
- ⬜ 패널 토글 로직 (한 번에 하나만, 같은 아이콘 재클릭 시 닫기)
- ⬜ 패널 상태 localStorage 저장/복원
- ⬜ 툴바 정리 (공통 항목만 남기기)

### Phase 2: PDF 번역 패널 이관 — 1.5일

- ⬜ PDF 번역 패널 내부 UI (모델 선택, 번역/취소, 범위 번역, 상태 텍스트)
- ⬜ 번역 PDF.js 렌더링을 패널 내부로 이관
- ⬜ 스크롤 동기화를 패널 내부 토글로 이관
- ⬜ 폴링 로직 — 패널 열려있을 때만 활성
- ⬜ 레거시 통번역 PDF 호환

### Phase 3: 웹뷰 번역 패널 이관 — 1.5일

- ⬜ 웹뷰 패널 내부 UI (모델 선택, 번역/취소, 폰트 크기, 전체 문서 토글)
- ⬜ Markdown 렌더링을 패널 내부로 이관
- ⬜ 전체 문서 연속 스크롤 + IntersectionObserver 이관
- ⬜ 폴링 로직 — 패널 열려있을 때만 활성
- ⬜ 인라인 번역 버튼 (미번역 페이지 플레이스홀더)

### Phase 4: 메모 패널 + 용어집 패널 — 1.5일

- ⬜ 메모 목록 패널 (페이지별 그룹, 클릭 시 스크롤)
- ⬜ 용어집을 모달 → 패널로 이관 (인라인 편집)
- ⬜ AI 챗봇 아이콘 (disabled, 자리 확보만)

### Phase 5: 리사이즈 + 다크모드 + 회귀 테스트 — 1일

- ⬜ 패널 리사이즈 핸들 (`.resize-handle` 공통 컴포넌트)
- ⬜ 다크모드 검증
- ⬜ 기존 기능 회귀 테스트 (PDF 번역, 웹뷰 번역, 마킹, 메모, 검색, 다운로드)
- ⬜ 모바일/좁은 화면 대응 검토

---

## 8. 착수 순서 및 예상 공수

| Phase | 내용 | 예상 공수 | 상태 |
|:-----:|------|:--------:|:----:|
| 1 | 아이콘 레일 + 패널 프레임 + 툴바 정리 | 2일 | ⬜ |
| 2 | PDF 번역 패널 이관 | 1.5일 | ⬜ |
| 3 | 웹뷰 번역 패널 이관 | 1.5일 | ⬜ |
| 4 | 메모 패널 + 용어집 패널 | 1.5일 | ⬜ |
| 5 | 리사이즈 + 다크모드 + 회귀 테스트 | 1일 | ⬜ |

**합계**: ~7.5일

---

## 9. Plan 17 잔여 작업과의 관계

Plan 17의 미완료 항목은 본 계획 완료 후 새 레이아웃 위에서 진행:

| Plan 17 항목 | Plan 18 이후 위치 |
|-------------|-----------------|
| Phase 4b: 검색 구분 UI + ZIP | 검색은 툴바/패널에서, ZIP은 다운로드 메뉴에서 |
| Phase 4c: 편집기 (EasyMDE) | 웹뷰 패널 내 편집 모드 또는 별도 패널 |
| Phase 4d: 썸네일 사이드바 | 좌측 아이콘 레일 또는 panel-main 내 토글 |
| Phase 4d: 관리자 설정 GUI | 변경 없음 (독립) |

---

## 10. 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| DOM 구조 대폭 변경 | 마킹/메모 텍스트 레이어 깨짐 | Phase 1에서 panel-main에 기존 구조 그대로 유지 |
| PDF.js 재렌더 타이밍 | 패널 열림/닫힘 시 캔버스 크기 불일치 | `rerenderBothPanels()` 패턴 재활용, transition 종료 후 렌더 |
| 기존 translator.js 3200줄 리팩토링 범위 | 전체 재작성 유혹 | 기존 함수를 최대한 재사용, 패널 래퍼만 추가하는 방식 |
| 좁은 화면에서 아이콘 레일 + 패널 | 콘텐츠 영역 부족 | 최소 너비 설정, 모바일은 오버레이 방식 검토 |

---

## 11. 참고

### 핵심 파일

| 파일 | 역할 | 줄 수 |
|------|------|:-----:|
| `translator.html` | DOM 구조 | 285 |
| `css/translator.css` | 레이아웃 스타일 | ~960 |
| `js/translator.js` | 뷰어 로직 전체 | 3222 |

### 현재 레이아웃 전환 진입점

| 함수 | 줄 | 용도 |
|------|:--:|------|
| `_showDualPanel()` | 640 | 우측 패널 표시 |
| `_hideDualPanel()` | 648 | 우측 패널 숨김 (싱글 복귀) |
| `rerenderBothPanels()` | 1455 | 패널 크기 변경 시 PDF 재렌더 |
