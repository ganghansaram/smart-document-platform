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

동시에 **라운드 패널 + 갭 기반 디자인 언어**를 도입한다.
Notebook에서 파일럿 적용 후, 플랫폼 전체(Explorer, Compare, Launcher, Login)로 확산한다.

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

### 2.3 라운드 패널 디자인 언어 (2026-03-24 결정)

업계 트렌드 조사 결과, 패널 간 border line 대신 **라운드 카드 + 갭 + 명도 차이**로
계층을 표현하는 패턴이 2024~2026 주류:

| 앱 | gap | radius | 특징 |
|----|:---:|:------:|------|
| NotebookLM | 8~12px | 16~24px | M3 surface-container 계층, shadow 최소 |
| Notion | ~6px | 8~12px | 배경색 차이로 구분 |
| Linear | ~8px | 12~16px | 짙은 배경 위 밝은 패널 |
| Arc Browser | ~8px | 16~20px | 명확한 명도 대비 |

**본 프로젝트 적용 값** (tokens.css 확장):

| 토큰 | Light | Dark | 근거 |
|------|-------|------|------|
| `--panel-radius` | `16px` | 동일 | MD3 Large (16dp) |
| `--panel-gap` | `8px` | 동일 | Notion/Linear/Arc 공통 |
| `--canvas-bg` | `#eef1f6` | `#0e0e18` | 패널 배경보다 한 단계 어둡게 (3~5% 차이) |
| `--panel-shadow` | `0 1px 3px rgba(0,0,0,0.04), 0 2px 8px rgba(0,0,0,0.06)` | shadow 강화 | 미세 elevation |

> 목업 검증 완료: `workbench/mockups/notebook-viewer-rounded.html`
> 아이콘 레일은 배경 없이 캔버스 위에 플로팅, hover 시에만 카드 느낌.

### 2.4 핵심 전환

**"번역기 뷰어" → "문서 워크벤치"**

- 원문 PDF가 항상 중앙에 전체 너비로 존재 (기본 상태)
- 번역/메모/용어집 등은 우측 패널의 **도구(tool)**
- 사용자가 도구를 열면 중앙이 축소되며 패널이 슬라이드
- 도구를 닫으면 원문이 다시 전체 너비로 복귀
- 모든 패널과 툴바는 **라운드 카드**로 캔버스 배경 위에 떠 있는 구조

---

## 3. 레이아웃 설계

### 3.1 기본 상태 (모든 패널 닫힘)

```
┌─────────────────────────────────────────────────────┬──┐
│ [◀ ▶ 1/4] [🔍 100% ±] [⬇]                          │  │
├─────────────────────────────────────────────────────┤📄│
│                                                     │📝│
│                                                     │📋│
│              원문 PDF (전체 너비)                      │📖│
│              마킹/하이라이트/메모 가능                   │──│
│                                                     │🤖│
│                                                     │📊│
│                                                     │🧠│
└─────────────────────────────────────────────────────┴──┘
```

### 3.2 패널 열림 상태 — 일반 도구 (예: PDF 번역)

원문 PDF를 축소하고 우측 50%에 패널이 슬라이드.

```
┌──────────────────────────┬────────────────────┬──┐
│ [◀ ▶ 1/4] [🔍 100% ±]   │                    │📄│← 활성
├──────────────────────────┤ PDF 번역 결과       │📝│
│                          │                    │📋│
│                          │ [모델 ▾] [번역 ▶]   │📖│
│   원문 PDF (축소)         │ [스크롤 동기화 ☐]   │──│
│                          │                    │🤖│
│                          │ ┌──────────────┐   │📊│
│                          │ │ 번역된 PDF    │   │🧠│
│                          │ └──────────────┘   │  │
└──────────────────────────┴────────────────────┴──┘
```

### 3.3 패널 확장 상태 (모든 패널 공통)

모든 패널에서 확장 버튼(↔)을 누르면 원문 PDF를 밀어내고 전체 영역 사용.
다시 누르면 50% 분할로 복귀. NotebookLM 패턴 참조.

```
┌─────────────────────────────────────────────┬──┐
│ 마인드맵                          [↔ 축소] ✕ │📄│
├─────────────────────────────────────────────┤📝│
│                                             │📋│
│                                             │📖│
│         패널 콘텐츠 (전체 화면)                │──│
│         (번역/메모/용어집/마인드맵 모두 동일)    │🤖│
│                                             │📊│
│                                             │🧠│← 활성
│                                             │  │
└─────────────────────────────────────────────┴──┘
```

### 3.4 아이콘 레일 구성

| 순서 | 아이콘 | 패널 이름 | 내용 |
|:----:|:------:|----------|------|
| 1 | 📄 | PDF 번역 | 모델 선택, 번역/취소, 범위 번역, 스크롤 동기화, 번역 PDF 뷰어 |
| 2 | 📝 | 웹 뷰 번역 | 모델 선택, 번역/취소, 폰트 크기, 전체 문서 토글, Markdown 렌더 |
| 3 | 📋 | 메모 | 메모 목록 (페이지별), 메모 검색, 메모 추가 |
| 4 | 📖 | 용어집 | 용어 목록, 추가/편집/삭제 (현재 모달 → 패널로 이관) |
| — | — | 구분선 | 상단: 문서 도구 / 하단: AI·분석 |
| 5 | 🤖 | AI 요약·Q&A | 문서 요약 + 챗봇 Q&A (탭 구성) |
| 6 | 📊 | 문서 요약 | 핵심 문장, 키워드, 통계 (향후, disabled) |
| 7 | 🧠 | 마인드맵 | 문서 구조 시각화 — 헤딩/키워드 기반 트리 (향후, disabled) |

> 모든 패널은 동일한 두 가지 모드를 지원: **일반 (50%)** / **확장 (전체)**.
> 패널 헤더의 확장/축소 토글 버튼(↔)으로 전환. 패널별 기본 모드 차이 없음.

> 아이콘은 실제 구현 시 SVG로 교체. 위 이모지는 설계 참고용.
> 구분선으로 "문서 도구"와 "AI·분석" 영역을 시각적으로 분리.
> Phase 1에서 7개 아이콘 자리를 모두 배치하되, 5~7번은 disabled 상태로 시작.

### 3.5 패널 동작 규칙

1. **한 번에 하나만** — 아이콘 클릭 시 해당 패널 열림, 다른 패널은 자동 닫힘
2. **토글** — 이미 열린 아이콘을 다시 클릭하면 패널 닫힘 (싱글 뷰로 복귀)
3. **슬라이드 애니메이션** — `var(--transition-normal)` 사용, 중앙 패널 flex 축소
4. **모든 패널 공통 두 가지 모드**:
   - **일반 모드** (50%): 원문 PDF와 나란히 표시. 리사이즈 핸들로 조절 가능.
   - **확장 모드** (100%): 원문 PDF를 완전히 밀어냄. 패널 헤더의 확장/축소 토글 버튼(↔)으로 전환.
   - 패널별 기본 모드 차이 없음 — 모두 일반(50%)으로 열리고, 사용자가 필요 시 확장.
5. **상태 유지** — 열린 패널 ID + 확장 여부를 `localStorage`에 저장, 재방문 시 복원

### 3.6 결정 사항 (2026-03-23)

| 항목 | 결정 | 이유 |
|------|------|------|
| Compare 통합 | ❌ 분리 유지 | Compare는 "두 문서 비교"가 본질, Notebook은 "한 문서 탐색" — 결이 다름 |
| 문서 요약 | ✅ 아이콘 레일 | AI 패널에 요약+Q&A 탭으로 통합, NotebookLM 패턴 |
| 마인드맵 | ✅ 아이콘 레일 (확장 모드) | Markdown 헤딩/키워드에서 트리 자동 생성, 전체 화면 사용 |
| 지식 그래프 (문서 간) | ❌ 별도 뷰 | 문서 뷰어가 아닌 카드 목록(홈) 레벨의 기능, 향후 별도 계획 |

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

### 5.3 메모 패널 (마킹 플로팅 위젯 대체)

기존 `marking-float` 플로팅 위젯(우측 패널 상단 형광펜 아이콘 + 드롭다운 목록)을
아이콘 레일의 **메모 사이드 패널**로 대체한다.

**제거 대상:**
- `#marking-float` DOM + CSS + JS (플로팅 아이콘, 드롭다운, 배지)

**상속 (그대로 유지):**
- 마킹 생성: 좌측 PDF 텍스트 선택 → 팝오버 → 4색 하이라이트 + 메모 작성 (변경 없음)
- 데이터/API: `get_annotations`, `create_annotation`, `update_annotation`, `delete_annotation`
- 마킹 색상(4색), 페이지 라벨, 메모 텍스트 등 시각적 표현

**메모 패널 (신규 UI):**
- 사이드 패널에서 전체 문서 메모 목록 (페이지별 그룹)
- 마킹 색상 표시 (하이라이트 배경색 그대로)
- 메모 항목 클릭 → 좌측 PDF 해당 페이지·위치로 스크롤
- 메모 편집/삭제 인라인

### 5.4 용어집 패널

현재 모달(`#glossary-modal`)을 패널로 이관:

- 용어 목록 표시 (현재 모달 내용 그대로)
- 추가/편집/삭제 인라인
- 패널이므로 원문 PDF를 보면서 동시에 용어집 편집 가능 (모달의 한계 해소)

### 5.5 AI 요약·Q&A 패널 (향후)

일반 모드 (50%) 패널. 탭 2개로 구성:

- **요약 탭**: 문서 요약문, 핵심 키워드, 핵심 문장 — Ollama 호출, 기존 번역 파이프라인 패턴 재활용
- **Q&A 탭**: 현재 문서 기반 챗봇 — Explorer `ai-chat.js` + `conversation.py` 패턴 재활용
- 데이터 소스: `full_translated.md` (번역 있으면) 또는 원문 텍스트 (없으면)

> Plan 17 Phase 6(챗봇)의 구현 위치가 이 패널이 됨.

### 5.6 마인드맵 패널 (향후)

**확장 모드 (전체 화면)** 패널. 원문 PDF를 완전히 밀어내고 전체 영역 사용.

- 데이터 소스: 웹뷰 번역의 Markdown 구조 (헤딩 계층 + 키워드)
- 번역 전 문서: PyMuPDF `get_toc()`로 목차 추출 → 트리 구성
- 렌더링: 경량 트리/마인드맵 라이브러리 (폐쇄망 번들, 후보 조사 필요)
- 노드 클릭 → 패널 닫기 + 좌측 PDF 해당 페이지/위치로 스크롤
- NotebookLM 마인드맵 뷰 참조

> 라이브러리 후보 조사 및 번들 크기 검토는 구현 Phase에서 수행.

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
        <!-- 문서 도구 -->
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
        <!-- 구분선 -->
        <div class="rail-separator"></div>
        <!-- AI · 분석 -->
        <button class="rail-btn" data-panel="ai-summary" title="AI 요약·Q&A" disabled>
            <svg>...</svg>
        </button>
        <button class="rail-btn" data-panel="doc-summary" title="문서 요약" disabled>
            <svg>...</svg>
        </button>
        <button class="rail-btn" data-panel="mindmap" title="마인드맵" disabled>
            <svg>...</svg>
        </button>
    </div>
</div>
```

### 6.2 CSS 핵심 (라운드 패널 기반)

```css
/* tokens.css에 추가할 패널 토큰 */
:root {
    --panel-radius: 16px;
    --panel-gap: 8px;
    --canvas-bg: #eef1f6;
    --panel-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 2px 8px rgba(0,0,0,0.06);
}
body[data-theme="dark"] {
    --canvas-bg: #0e0e18;
    --panel-shadow: 0 1px 3px rgba(0,0,0,0.2), 0 2px 8px rgba(0,0,0,0.3);
}

/* 뷰어 래퍼: 캔버스 배경 + 갭 */
.viewer-wrap {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: var(--panel-gap);
    gap: var(--panel-gap);
    background: var(--canvas-bg);
}

/* 툴바: 라운드 카드 */
.viewer-toolbar {
    border-radius: var(--panel-radius);
    background: var(--white);
    box-shadow: var(--panel-shadow);
}

/* 패널 영역: 갭으로 분리 */
.viewer-panels {
    flex: 1;
    display: flex;
    gap: var(--panel-gap);
    overflow: hidden;
}

/* 메인 패널: 라운드 카드 */
.viewer-main {
    flex: 1;
    overflow: auto;
    background: var(--white);
    border-radius: var(--panel-radius);
    box-shadow: var(--panel-shadow);
    transition: flex var(--transition-slow), opacity var(--transition-slow);
}
.viewer-main.collapsed { flex: 0; opacity: 0; overflow: hidden; }

/* 사이드 패널: 라운드 카드 */
.viewer-side-panel {
    width: 0;
    min-width: 0;
    overflow: hidden;
    background: var(--white);
    border-radius: var(--panel-radius);
    box-shadow: var(--panel-shadow);
    transition: width var(--transition-slow), min-width var(--transition-slow);
    /* border-left 제거 — 갭 + 라운드로 구분 */
}
.viewer-side-panel.open { width: 50%; min-width: 420px; }
.viewer-side-panel.expand { width: 100%; min-width: 100%; }

/* 아이콘 레일: 배경 없이 캔버스 위 플로팅 */
.icon-rail {
    width: 42px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    padding: 6px 0;
    /* border, background 없음 — 캔버스 배경과 일체 */
}

.rail-btn {
    width: 34px;
    height: 34px;
    border: none;
    background: transparent;
    border-radius: var(--radius-md);
    color: var(--text-light);
}
.rail-btn:hover {
    background: var(--white);
    box-shadow: var(--panel-shadow);
}
.rail-btn.active {
    background: var(--active-color);
    color: #fff;
    box-shadow: 0 2px 8px rgba(44,82,130,0.3);
}
```

> 목업 참조: `workbench/mockups/notebook-viewer-rounded.html`

---

## 7. 실행 계획

### Phase 1a: 디자인 토큰 + 라운드 패널 외형 — 완료

> 기존 기능을 유지한 채 외형만 변경. 기존 듀얼 뷰어 동작은 그대로.

- ✅ **tokens.css 확장**: `--panel-radius`, `--panel-gap`, `--canvas-bg`, `--panel-shadow` 추가 (Light + Dark)
- ✅ `translator.css` 뷰어 영역: 캔버스 배경 (`--canvas-bg`) 적용
- ✅ 기존 좌/우 패널에 `--panel-radius`, `--panel-shadow` 적용
- ✅ 패널 간 `border-left` → 제거, `gap: var(--panel-gap)` 으로 대체
- ✅ 툴바를 라운드 카드로 변경 (`--panel-radius`, `--panel-shadow`)
- ✅ 다크모드 검증 (캔버스↔패널 명도 차이) + 하드코딩 #1e1e2e → var(--white) 토큰화
- ✅ 기존 기능 회귀 확인 (PDF 번역, 웹뷰 번역, 마킹, 메모 정상 동작)

### Phase 1b: 아이콘 레일 + 패널 프레임 + 툴바 재배치 — 완료

> Phase 1a의 라운드 패널 위에서 레이아웃 구조 전환.

- ✅ DOM 구조 변경 (panel-right → side-panel 래퍼 + icon-rail 추가)
- ✅ 아이콘 레일 UI (7개 버튼 + 구분선, SVG 아이콘, 5~7번은 disabled)
- ✅ 아이콘 레일: 배경 없이 캔버스 위 플로팅 (hover 시 카드 shadow)
- ✅ 패널 열기/닫기 애니메이션 (CSS transition + transitionend 재렌더)
- ✅ 두 가지 패널 모드 지원 (일반 50% / 확장 100% — 패널 헤더 ↔ 토글)
- ✅ 패널 토글 로직 (한 번에 하나만, 같은 아이콘 재클릭 시 닫기)
- ✅ 패널 상태 localStorage 저장/복원
- ✅ 엔진 토글(PDF/웹뷰) → 아이콘 레일로 대체 (기존 토글 display:none)

### Phase 2: PDF 번역 패널 이관 (V4 재구현) — 완료

- ✅ 상단 toolbar 제거 → 좌측 패널 헤더에 원문 컨트롤 통합 (페이지/줌/다운로드)
- ✅ 우측 패널별 헤더 4종 (PDF/웹뷰/메모/용어집) — 패널 전용 고정 HTML
- ✅ 공유 요소(model-select, translate-btn, cancel-btn) shared-slot 패턴
- ✅ 초기 상태: 싱글 뷰 (아이콘 active 없음, 패널 닫힘)
- ✅ showRight* 함수에 activeRailPanel 가드 (자동 열림 차단)
- ✅ --panel-bg, --content-bg, --font-* 토큰 적용
- ✅ 번역 PDF.js 렌더링 정상, 확장/닫기 이벤트 위임

### Phase 3: 웹뷰 번역 패널 이관 — 1.5일

- ✅ 웹뷰 패널 내부 UI — Phase 2에서 hdr-web에 이미 구현 (폰트/전체문서/모델/번역)
- ✅ Markdown 렌더링 — panel-scroll 내부에서 정상 렌더
- ✅ 전체 문서 연속 스크롤 — 기존 JS 동작 유지
- ✅ 폴링 로직 — activeRailPanel 가드 적용됨
- ✅ 인라인 번역 버튼 — showRightPending에서 처리
- ✅ 웹뷰 상태 텍스트 — _setStatus()로 PDF/웹뷰 양쪽 동기화

### Phase 4: 메모 패널 + 용어집 패널 — 1.5일

- ✅ marking-float 위젯 display:none (메모 사이드 패널로 대체)
- ✅ 메모 패널: 색상 dot + 페이지 라벨 + 하이라이트 + 메모 카드 목록
- ✅ 카드 클릭 → goToPage + flashHighlight
- ✅ renderAnnotations 훅에 _renderMemoPanel 연결 (마킹 생성 시 자동 갱신)
- ✅ 용어집 패널: 인라인 테이블 + 추가/삭제 (기존 API 재사용)
- ✅ _showToolContent()로 번역/도구 패널 콘텐츠 전환

### Phase 5: 리사이즈 + UX 보정 + 회귀 테스트 — 1.5일

> Phase 4까지 식별된 UX 보정 사항을 포함. 전체 기능 회귀 테스트로 안정화.

- ⬜ 패널 리사이즈 핸들 (드래그로 좌/우 비율 조절 — 목업 V3에서 검증됨)
- ⬜ 용어집 입력란 헤더 통합 (패널 공간 효율 개선)
- ⬜ 메모 패널 빈 상태 안내 (마킹 없는 문서에서 가이드 텍스트)
- ⬜ 폰트/간격 목업(V4) 대비 미세 조정
- ⬜ 다크모드 전체 검증 (4개 패널 + 싱글 뷰)
- ⬜ 기존 기능 회귀 테스트 (PDF 번역, 웹뷰 번역, 마킹 생성, 검색, 다운로드)

> 보류: PDF 캔버스 등장 깜빡임 (최적화 한계로 판단, 현재 코드 유지)
> 제외: 용어집 하이라이트 연동 / 자동 추천 / 번역 적용 표시 → Phase 6 이후

### Phase 6: AI 요약·Q&A 패널 — 향후

> Plan 17 Phase 6(챗봇)과 통합. 백엔드 RAG 파이프라인 개인 문서 격리 구조 결정 후 착수.

- ⬜ 요약 탭: Ollama 문서 요약 + 키워드 추출
- ⬜ Q&A 탭: Explorer ai-chat.js 패턴 재활용, 현재 문서 기반 질의
- ⬜ 데이터 소스: full_translated.md 또는 원문 텍스트

### Phase 7: 마인드맵 패널 — 향후

> 확장 모드(전체 화면) 패널. 라이브러리 후보 조사 및 폐쇄망 번들 검토 선행 필요.

- ⬜ 마인드맵 라이브러리 선정 + 번들 (폐쇄망 호환)
- ⬜ 데이터 소스: Markdown 헤딩 계층 + 키워드 (번역 후), PyMuPDF get_toc() (번역 전)
- ⬜ 확장 모드 패널 렌더링 (원문 완전 밀어냄 + "원문으로 돌아가기" 버튼)
- ⬜ 노드 클릭 → 패널 닫기 + PDF 해당 위치로 스크롤

### Phase 8: 플랫폼 디자인 언어 확산 — Notebook 안정화 후

> Phase 1~5에서 확정된 패널 토큰을 다른 서브시스템에 점진 적용.
> 기능 변경 없이 CSS만 교체하는 작업이라 리스크 낮음.
> Notebook 안정화 후 순차 진행.

**적용 대상 및 순서:**

| 순서 | 화면 | 변경 범위 | 예상 공수 |
|:----:|------|----------|:--------:|
| 1 | **Explorer** (index.html) | 좌측 TOC + 중앙 콘텐츠 + AI 채팅 패널 → 라운드 카드 + 캔버스 배경 | 반나절 |
| 2 | **Compare** (compare.html) | 좌/우 문서 듀얼 패널 + diff 오버레이 → 라운드 카드 + 갭 | 반나절 |
| 3 | **Launcher** (launcher.html) | 캔버스 배경 + 카드 shadow 조정 (카드는 이미 라운드) | 2시간 |
| 4 | **Login** (login.html) | 로그인 카드 radius/shadow 통일 | 1시간 |

**적용 원칙:**
- `tokens.css`에 추가된 `--panel-radius`, `--panel-gap`, `--canvas-bg`, `--panel-shadow` 사용
- 각 화면의 기존 `border-left`, `border-right` → 제거, 갭으로 대체
- `body` 또는 래퍼 `background` → `var(--canvas-bg)`
- 패널 `background` → `var(--white)`, `border-radius` → `var(--panel-radius)`
- 각 화면 전용 CSS에서 하드코딩된 radius/shadow → 토큰 변수로 교체

---

## 8. 착수 순서 및 예상 공수

| Phase | 내용 | 예상 공수 | 상태 |
|:-----:|------|:--------:|:----:|
| **1a** | **디자인 토큰 + 라운드 패널 외형** (기존 기능 유지) | 1일 | ✅ |
| **1b** | **아이콘 레일 + 패널 프레임 + 툴바 재배치** | 1.5일 | ✅ |
| 2 | PDF 번역 패널 이관 (V4 재구현) | 1.5일 | ✅ |
| 3 | 웹뷰 번역 패널 이관 | 1.5일 | ✅ (검증 완료) |
| 4 | 메모 패널 + 용어집 패널 | 1.5일 | ✅ |
| 5 | 리사이즈 + UX 보정 + 회귀 테스트 | 1.5일 | ⬜ |
| 6 | AI 요약·Q&A 패널 | 미정 | 향후 |
| 7 | 마인드맵 패널 | 미정 | 향후 |
| 8 | **플랫폼 디자인 언어 확산** (Explorer → Compare → Launcher → Login) | 2일 | 향후 |

**Phase 1a~5 합계**: ~8.5일 (Notebook 레이아웃 재설계 핵심)
**Phase 1a 완료 시 중간 검증**: 기존 기능이 라운드 패널에서 정상 동작하는지 확인 후 1b 착수
**Phase 6~7**: 향후 — AI/분석 기능
**Phase 8**: 향후 (~2일) — Notebook 안정화 확인 후 플랫폼 전체 확산

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
| 좁은 화면에서 아이콘 레일 + 패널 | 콘텐츠 영역 부족 | 사이드 패널 min-width 420px 확보, 모바일은 오버레이 방식 검토 |
| border-radius + overflow | PDF 캔버스 모서리 클리핑 | `overflow: hidden`이 이미 적용, panel-main 내부 구조 유지로 해결 |
| 플랫폼 확산 시 기존 CSS 충돌 | 각 화면 전용 CSS에 하드코딩된 값 | Phase 8에서 토큰 변수로 교체, 화면별 개별 검증 |
| tokens.css 토큰 추가 | 기존 화면에 의도치 않은 영향 | 신규 토큰(`--panel-*`, `--canvas-bg`)은 기존 변수와 이름 충돌 없음. 기존 화면은 사용하지 않으므로 영향 없음 |

---

## 11. 참고

### 핵심 파일

| 파일 | 역할 | 줄 수 |
|------|------|:-----:|
| `translator.html` | DOM 구조 | 285 |
| `css/translator.css` | 레이아웃 스타일 | ~960 |
| `css/tokens.css` | 디자인 토큰 (패널 토큰 추가 대상) | ~130 |
| `js/translator.js` | 뷰어 로직 전체 | 3222 |

### 목업

| 파일 | 설명 |
|------|------|
| `workbench/mockups/notebook-viewer-layout.html` | 초기 목업 (border line 방식) |
| `workbench/mockups/notebook-viewer-rounded.html` | **확정 목업** (라운드 패널 + 갭 + 캔버스 배경) |

### 현재 레이아웃 전환 진입점

| 함수 | 줄 | 용도 |
|------|:--:|------|
| `_showDualPanel()` | 640 | 우측 패널 표시 |
| `_hideDualPanel()` | 648 | 우측 패널 숨김 (싱글 복귀) |
| `rerenderBothPanels()` | 1455 | 패널 크기 변경 시 PDF 재렌더 |
