# Plan 19: Notebook 플랫폼 완성

> 작성일: 2026-03-26
> 상태: **완료 (Phase 1~6)** / Phase 7 → Plan-20으로 이관
> 완료일: 2026-03-29
> 브랜치: `plan17-library` (기존 브랜치 계속 사용)
> 선행: Plan-17 Phase 1~5 완료, Plan-18 Phase 1a~5 완료
> 범위: Plan-17/18 잔여 항목 통합 + 우선순위 재편

---

## 1. 목적

Plan-17(Markdown 파이프라인)과 Plan-18(뷰어 레이아웃 재설계)의 핵심이 완료되었다.
본 계획은 **양쪽의 잔여 항목을 통합**하여 Notebook 시스템과 플랫폼 전체를 완성한다.

## 2. 현재 상태 (2026-03-26 기준)

### 2.1 완료된 기반

| 영역 | 완료 내용 | 출처 |
|------|----------|------|
| **추출 파이프라인** | PyMuPDF4LLM → Markdown, 표/이미지/수식 모드, YOLO 컬럼 폴백 | Plan-17 Phase 1 |
| **번역 파이프라인** | 블록 단위 Ollama 번역, 표 셀 번역, 용어집 적용, frontmatter | Plan-17 Phase 2 |
| **웹 뷰 프론트엔드** | marked.js + DOMPurify, 엔진 2종(PDF/웹뷰), 폴링/캐시 | Plan-17 Phase 3~3+ |
| **웹 뷰 읽기 경험** | 전체 문서 연속 스크롤, IntersectionObserver 동기화, 인라인 번역 | Plan-17 Phase 4a |
| **텍스트 모드 제거** | 엔진 2종 축소, YOLO 폴백 이관, UI 리네이밍(Notebook) | Plan-17 Phase 5 |
| **라운드 패널 디자인** | tokens.css 확장, 캔버스 배경, panel-radius/shadow/gap | Plan-18 Phase 1a |
| **아이콘 레일 + 패널** | 7개 레일 버튼, 사이드 패널, 패널 헤더 4종, 공유 요소 패턴 | Plan-18 Phase 1b~2 |
| **메모/용어집 패널** | 사이드 패널 내 카드 목록, 인라인 CRUD, renderAnnotations 훅 | Plan-18 Phase 4 |
| **리사이즈 + UX** | 드래그 리사이즈, 아이콘 레일 간격, 폰트 토큰 통일, 회귀 테스트 | Plan-18 Phase 5 |

### 2.2 이미 구현되어 있지만 UI가 없는 것

| 기능 | 백엔드 상태 | 프론트엔드 상태 |
|------|-----------|---------------|
| ~~검색 인덱스 `translated_pages`~~ | ✅ | ✅ Phase 2에서 해결 (배지 구분) |
| ~~웹 뷰 설정 키 6개~~ | ✅ | ✅ Phase 3에서 해결 (admin-settings GUI) |
| ~~웹 뷰 Markdown 편집~~ | ✅ PUT API | ✅ Phase 5에서 해결 (EditorCore + Monaco) |
| ~~page_boxes 좌표 데이터~~ | ✅ `web_page_boxes.json` 저장, API 응답 포함 | ✅ Phase 6에서 해결 (양방향 클릭 네비게이션) |
| **frontmatter summary/keywords** | ✅ 빈 필드로 구조 존재 | ❌ 자동 생성 로직 없음 |
| **annotation CRUD API** | ✅ 완전 구현 | ❌ 카드 목록에 문서별 메모 수 미표시 |

### 2.3 아이콘 레일 현황

| # | 아이콘 | 상태 | 비고 |
|:-:|--------|:----:|------|
| 1 | PDF 번역 | ✅ 활성 | 듀얼 PDF 뷰어 |
| 2 | 웹 뷰 번역 | ✅ 활성 | Markdown 렌더링 |
| 3 | 메모 | ✅ 활성 | 카드 목록, 클릭 네비게이션 |
| 4 | 용어집 | ✅ 활성 | 인라인 추가/삭제 |
| 5 | AI 요약·Q&A | ❌ disabled | `data-panel="ai-summary"` |
| 6 | 문서 요약 | ❌ disabled | `data-panel` 미지정 |
| 7 | 마인드맵 | ❌ disabled | `data-panel="mindmap"` |

### 2.4 플랫폼 디자인 현황

| 화면 | 라운드 패널 | 캔버스 배경 | 토큰 사용 |
|------|:---------:|:---------:|:--------:|
| **Notebook** (translator.html) | ✅ | ✅ | ✅ |
| Explorer (index.html) | ❌ border-line | ❌ | 부분적 |
| Compare (compare.html) | ❌ border-line | ❌ | 부분적 |
| Launcher (launcher.html) | 부분 (카드만) | ❌ | 부분적 |
| Login (login.html) | 부분 | ❌ | 부분적 |

---

## 3. 실행 계획

### Phase 1: 플랫폼 디자인 언어 확산 — ~2.5일

> 출처: Plan-18 Phase 8
> Notebook만 라운드 패널이고 나머지 4개 화면은 구형 → 시각적 불일치 해소.
> 기능 변경 없이 CSS만 교체. 리스크 최저.
> 3단계로 분할하여 단계별 검증 후 다음 진행.

**공통 원칙:**
- Notebook(translator.html)을 기준 디자인으로 삼아 통일감 부여
- `tokens.css`의 `--panel-radius`, `--panel-gap`, `--canvas-bg`, `--panel-shadow` 사용
- 각 화면의 기존 `border-left`, `border-right` → 제거, 갭으로 대체
- 작업 공간(workspace) 화면: `body` 배경 → `var(--canvas-bg)`, 패널 → `var(--panel-radius)` + `var(--panel-shadow)`
- 진입 화면(Launcher/Login): 시네마틱 배경(`#0a1628`) 유지 — 작업 공간과 다른 성격이므로 예외 허용
- 각 화면 전용 CSS에서 하드코딩된 radius/shadow/color → 토큰 변수로 교체
- 화면별 Light + Dark 검증

**사전 결정 사항 (2026-03-26):**

| 항목 | 결정 | 근거 |
|------|------|------|
| Login 다크 모드 | **추가 안 함** | 진입 화면은 고정 테마 (어두운 배경 이미지 위 밝은 카드). 카드 내부 하드코딩만 토큰 교체 |
| Launcher/Login `#0a1628` | **예외 허용** | 시네마틱 진입 경험 ≠ 작업 공간. `--canvas-bg` 적용 대상 아님 |
| Explorer 리사이즈 핸들 | **`.resize-handle` 전환** | Notebook과 동일 패턴 (components.css), 플랫폼 일관성 |

#### Phase 1a: Launcher + Login — 완료

> 구조 변경 없이 토큰 교체 위주. 가장 가벼운 작업으로 패턴 확립.

**Launcher** (launcher.html, 인라인 CSS):
- ✅ `.system-card` `border-radius: 12px` → `var(--radius-lg)`
- ✅ 구조/레이아웃 변경 없음 (비디오 배경 유지)

**Login** (login.html, 인라인 CSS):
- ✅ `.login-card` `border-radius: 10px` → `var(--radius-xl)`, `box-shadow` → `var(--shadow-xl), var(--shadow-sm)`
- ✅ `.login-btn` `background: #1e3a6e` → `var(--active-color)`, `border-radius: 6px` → `var(--radius-md)`
- ✅ `.login-btn.success` → `var(--color-success-btn)`
- ✅ input focus `border-color: #2c5282` → `var(--active-color)`
- ✅ `.error-msg` `#c53030` → `var(--color-error)`, `border-radius: 5px` → `var(--radius-sm)`
- ✅ label `#666` → `var(--text-light)`, title `#1a1a2e` → `var(--text-dark)`
- ✅ 공지 `border-radius: 7px` → `var(--radius-md)`
- ✅ 다크 모드 추가 안 함 (결정대로)
- ✅ 검증: 로그인 동작 정상 확인

#### Phase 1b: Compare — 완료

> border-line → gap 전환 적용. diff 의미적 border-left 보존.

- ✅ `body` 배경: `var(--bg-gray)` → `var(--canvas-bg)`
- ✅ `.compare-body` 패딩 + gap 추가 (캔버스 여백)
- ✅ `.compare-toolbar` → `border-bottom` 제거, `border-radius: var(--panel-radius)` + `box-shadow: var(--panel-shadow)`
- ✅ `.cp-panels` → `gap: var(--panel-gap)` (패널 간 gap 분리)
- ✅ `.compare-panel` → `border-left` 제거, `background: var(--white)`, `border-radius: var(--panel-radius)` + `box-shadow: var(--panel-shadow)`
- ✅ `.cp-sidebar` → `border-left` 제거, `border-radius: var(--panel-radius)` + `box-shadow: var(--panel-shadow)`
- ✅ `.cp-sidebar-header` → 상단 radius 추가
- ✅ diff 의미적 `border-left: 3px solid` — 보존 (변경 안 함)
- ✅ 하드코딩 `box-shadow` → `var(--shadow-sm/lg)` 토큰 교체
- ✅ 리사이즈 핸들 하이라이트 제거 (Notebook 패턴 통일)
- ✅ 다크 모드: 불필요한 border-color 오버라이드 제거
- ✅ 검증: Light + Dark 스크린샷 확인

#### Phase 1c: Explorer — 완료

> 3-패널 grid 구조 유지, 시각만 변경. grid 5-column + JS updateLayout() 변경 없음.

- ✅ `body` 배경: `var(--bg-gray)` → `var(--canvas-bg)`
- ✅ `.container`: `padding: var(--panel-gap)` 추가 (캔버스 여백)
- ✅ `.left-panel`: `border-right` 제거, `border-radius: var(--panel-radius)` + `box-shadow: var(--panel-shadow)`, `margin-right: calc(var(--panel-gap)/2)`
- ✅ `.content-panel`: `border-radius: var(--panel-radius)` + `box-shadow: var(--panel-shadow)`
- ✅ `.right-panel`: `border-left` 제거, bg `var(--white)`, `border-radius` + `box-shadow`, `margin-left: calc(var(--panel-gap)/2)`
- ✅ `.panel-header`: 상단 `border-radius` 추가
- ✅ 하드코딩 `box-shadow`, `border-radius: 6px` → 토큰 교체 (show-panel-btn, search-container 등)
- ✅ 리사이즈 핸들 하이라이트 제거 (Notebook 패턴 통일)
- ✅ 다크 모드: shadow → 토큰 통일
- ✅ 검증: Light + Dark, 3패널 CSS 확인 (radius 16px, shadow 적용), 패널 접기/복원, 에러 0건

#### Phase 1d: Settings (관리자 설정) — 완료

> 구조 변경 없이 배경 + 카드 radius/shadow 토큰 교체.

- ✅ `body:has(.admin-settings-page)` 배경: `var(--bg-gray)` → `var(--canvas-bg)`
- ✅ `.admin-section`: `border-radius: 10px` → `var(--radius-lg)`, `box-shadow: var(--panel-shadow)` 추가
- ✅ `.admin-sidebar-btn/tab-btn/subtab-btn`: radius + shadow → 토큰 교체
- ✅ `.admin-modal`: 하드코딩 색상/shadow → 토큰 교체
- ✅ 검증: Light + Dark, 저장/초기화 정상

### Phase 2: 검색 구분 UI + ZIP 다운로드 — 완료

> 출처: Plan-17 Phase 4b
> 검색 인덱스에 `translated_pages`와 `match_source`가 이미 구현되어 있으나 UI에서 활용하지 않음.

**검색 UX:**
- ✅ 본문 결과에 match_source 배지 ("원문" badge-info / "웹뷰 번역" badge-success)
- ✅ 검색 결과 클릭 시 패널 자동 열기 (번역 매칭 → 웹뷰 패널, 메모 매칭 → 메모 패널)
- ✅ 검색어 하이라이트 — 웹뷰/메모 패널 내 TreeWalker 패턴, 5초 후 페이드아웃
- ✅ 검색 오버레이 Explorer↔Notebook 시각 통일 (780px, shadow/radius/font 토큰)
- ✅ Explorer 결과 타이틀색 var(--primary-navy) → var(--active-color) 통일
- ✅ mark 배경색 통일 (#ffe066 / 다크 #665500)
- ❌ 필터 버튼 → 설계 후 제거 (결과 그룹(메모/본문)과 축이 달라 혼란 유발, 향후 재도입 가능)

**다운로드:**
- ✅ MD 버튼 (페이지/전체) — 웹뷰 번역 있으면 엔진 무관 노출
- ✅ ZIP 다운로드 — 백엔드 `GET /api/translator/document/{doc_id}/download/zip` (zipfile 모듈)
  - 포함: `full_translated.md` + 페이지별 `web_translated.md` + `assets/*.png`
  - 임시 파일 자동 삭제 (BackgroundTasks)
- ✅ ZIP 버튼 — 다운로드 메뉴에 추가, 웹뷰 번역 있으면 노출

**백엔드:**
- ✅ 검색 API `source` 파라미터 추가 (하위 호환, 기본값 전체) — 향후 필터 재도입 대비
- ✅ `create_document_zip()` 서비스 함수

### Phase 3: 관리자 설정 GUI (웹 뷰) — 완료

> 출처: Plan-17 Phase 4d-2

- ✅ `admin-settings.js` "번역 품질" 섹션에 "웹 뷰 추출" 서브탭 추가 (PDF/AI 선택과 동일 패턴)
- ✅ 6개 설정 항목:
  - 표 추출 모드 (select: 구조 추출 / 이미지만 / 끄기)
  - 수식 추출 모드 (select: LaTeX 변환 / 이미지만 / 끄기)
  - 이미지 해상도 DPI (range: 72~300)
  - 표 감지 전략 (select: lines_strict / lines / text)
  - 번역 완료 시 자동 요약 (toggle)
  - 디버그 모드 (toggle)
- ✅ 각 항목에 설명 텍스트 포함
- ✅ `settings.json` 저장 + `apply_to_config()` 즉시 적용 (기존 매핑 활용)
- ✅ 검증: Light + Dark, 저장 정상

### Phase 4: AI 요약·Q&A 패널 — 완료

> 출처: Plan-18 Phase 6 + Plan-17 Phase 6(챗봇) + Plan-17 섹션 10(자동 요약)
> 상세 설계서: `workbench/plans/done-phase4-ai-summary-design.md`

**완료 항목:**

- ✅ 추출 전용 파이프라인 (번역 없이 MD 추출 → 요약·Q&A의 전제 조건)
- ✅ AI 요약 — 크기 적응형 (단일 패스 / 계층적), 원문 기준, `/api/chat` 업계 표준
- ✅ Q&A 챗봇 — NDJSON 스트리밍, 멀티턴, Explorer 인프라 재사용
- ✅ 아이콘 레일 5번 활성화, 6번(문서요약) 삭제 → 7→6개 축소
- ✅ 패널 UI: 요약 탭 (카드+키워드+아코디언) + Q&A 탭 (채팅+스트리밍)
- ✅ Q&A UX: 추천 질문, 출처 배지(페이지 이동), 복사, 스크롤 버튼, 대화 초기화
- ✅ 버그 11건 수정 (패널 간섭, XSS, 메모리 누수, 입력 disabled 등)
- ⏭️ 자동 요약 옵션 — 실사용 피드백 후 활성화 (관리자 GUI 토글 준비됨)

### Phase 5: Markdown 편집기 — 완료

> 출처: Plan-17 Phase 4c
> 번역 결과를 사용자가 직접 수정 가능 → "지식 저장소" 비전의 핵심 조각.
> **결정 (2026-03-29):** Monaco Editor 재활용 (이미 `js/monaco-editor/`에 번들됨). EasyMDE 도입 불요.

**백엔드 상태: 100% 완료** — PUT API + `merge_full_translated()` 재병합 이미 구현됨.

#### Step 1: 공통 에디터 코어 분리 (리팩토링)

> Explorer(`js/editor.js`)와 Translator가 동일 에디터 코어를 공유하도록 분리.
> 목적: 스타일·로직 변경을 한 곳에서 관리하여 시간에 따른 분기 방지.

- ✅ `js/editor-core.js` 신규 생성 — 공통 엔진 (Strategy 패턴)
  - `EditorCore.create(options)` — 콜백 주입 인터페이스
  - Monaco 로드, 분할 뷰, 양방향 네비게이션, 변경 감지, 미저장 경고, 전체화면
  - HTML/Markdown 양쪽 모드 지원 (하이라이트·소스이동 로직 분기)
  - 다크모드 자동 감지 (`vs-dark`), 테마 전환 시 MutationObserver 동기화
- ✅ `css/editor.css` 확장 — `#ec-*` 셀렉터 추가, flex 레이아웃 안정화
- ✅ `js/editor.js` 리팩토링 — Explorer 어댑터로 축소 (803→157줄)
  - `EditorCore.create({ language: 'html' })` 호출
  - 기존 외부 인터페이스 100% 유지 (`openEditor`, `updateEditButtonVisibility`, `EditorState`)
- ✅ `js/toast.js` 신규 — `showToast()` 공통화 (`app.js`에서 추출, Explorer+Notebook 공용)
- ✅ 검증: Explorer 편집기 기존 기능 전수 테스트 — 회귀 없음

#### Step 2: Translator 어댑터 구현

- ✅ translator.html에 `editor-core.js` + `css/editor.css` + `toast.js` 로드
- ✅ 웹 뷰 패널 헤더에 편집 아이콘 버튼 추가 (웹뷰 번역 완료 + 페이지별 모드에서만 노출)
- ✅ Translator 어댑터 — `EditorCore.create({ language: 'markdown' })` 호출
  - `renderPreview`: frontmatter 제거 → 이미지 경로 치환 → `marked.parse()` + DOMPurify
  - `onSave`: `PUT /api/translator/web-view/{doc_id}/page/{page_num}` → 웹뷰 재렌더링
- ✅ 저장 완료 → showToast 피드백 + 웹 뷰 패널 재렌더링 + `full_translated.md` 자동 재병합
- ✅ 전체 문서 모드에서 편집 버튼 숨김 (페이지 혼동 방지)
- ✅ 다크모드 검증 (Monaco `vs-dark` 테마 자동 전환 + 테마 토글 시 동기화)
- ✅ 검증: 편집→저장→프리뷰 갱신→전체 MD 재병합 E2E 테스트

### Phase 6: 클릭 네비게이션 — 완료

> 출처: Plan-17 Phase 4d-1
> `web_page_boxes.json`에 블록별 PDF 좌표가 이미 저장되어 있음. 프론트엔드만 구현.

- ✅ `page_boxes` 데이터 캐시 (`_navBoxes`) + 현재 scale 외부 노출 (`_navScale`, `_navPdfViewport`)
- ✅ 웹 뷰 렌더링 후 블록별 `data-box-index` 속성 부여 (순서 매칭, page-header/footer 제외)
- ✅ 좌측 PDF 위에 투명 boxes 오버레이 레이어 (`.nav-box-layer` → `.nav-box`)
- ✅ 우측→좌측: MD 블록 클릭 → PDF 해당 box 스크롤 + 아웃라인 하이라이트 (2초 페이드)
- ✅ 좌측→우측: PDF box 클릭 → MD 해당 블록 스크롤 + 배경 플래시 (2초 페이드)
- ✅ 호버: 양쪽 모두 dashed 아웃라인으로 클릭 가능 표시
- ✅ 줌/페이지 변경 시 오버레이 자동 재그리기 (`renderLeftPage` 완료 훅)
- ✅ 전체 문서 모드·PDF 엔진 모드에서 오버레이 비활성
- ✅ 기존 텍스트 선택/하이라이트 이벤트와 `stopPropagation`으로 충돌 방지
- ✅ CSS: `var(--active-color)`, `var(--transition-fast)`, `var(--radius-sm)` 토큰 사용
- ✅ 별도 API 호출 불필요 — 기존 웹뷰 API 응답의 `page_boxes` 필드 재사용

### Phase 7: 마인드맵 패널 — ~3일

> 출처: Plan-18 Phase 7
> 아이콘 레일 7번 버튼 활성화. 확장 모드(전체 화면) 패널.

**사전 조사 필요:**
- 폐쇄망 번들 가능한 경량 마인드맵/트리 라이브러리 선정
  - 후보: Markmap (~200KB, Markdown→마인드맵 직접 변환), D3.js 기반 커스텀
  - 기준: UMD/IIFE 빌드, 외부 CDN 의존 없음, 다크모드 지원

**구현 항목:**

- ⬜ 라이브러리 선정 + `js/lib/` 번들
- ⬜ 데이터 소스:
  - 번역 후: `full_translated.md`의 Markdown 헤딩 계층 + 키워드
  - 번역 전: PyMuPDF `get_toc()`로 목차 추출 → 트리 구성
  - 백엔드: `GET /api/translator/document/{doc_id}/toc` (신규)
- ⬜ 확장 모드 패널 렌더링 (원문 PDF 완전 밀어냄)
- ⬜ 노드 클릭 → 패널 닫기 + PDF 해당 위치로 스크롤
- ⬜ 아이콘 레일 7번 `disabled` 해제 + 핸들러 연결

---

## 4. 향후 과제 (본 계획 범위 밖)

실사용 피드백을 수집한 후 별도 계획으로 진행:

| 기능 | 난이도 | 비고 |
|------|:------:|------|
| 카드 목록 메모 수 표시 | 하 | annotation count API 확장 필요 |
| 번역 속도 최적화 (블록 병렬) | 하 | 현재 순차 ~22초 → 병렬 시 ~8초 예상 |
| 관련 문서 자동 추천 | 하 | bge-m3 임베딩 + 용어집 공유도 |
| 용어 기반 자동 연결 | 하 | marked.js 렌더링 후 DOM 키워드 매칭 |
| 문서 타임라인 | 하 | frontmatter 날짜 기반, 순수 CSS+JS |
| 개인 문서 벡터 검색 확장 | 중 | Phase 4 Q&A를 전체 문서로 확장 시 |
| 클러스터 시각화 | 중 | D3.js (~250KB) + UMAP, ROI 평가 후 |
| page-header/footer 텍스트 제거 | 하 | 추출 품질 개선 |
| 인라인 수식 크기 필터링 | 하 | 작은 수식 이미지 캡처 방지 |
| 알고리즘/의사코드 번역 스킵 | 하 | "Algorithm" 키워드 감지 |
| 파일명 리네이밍 (translator→notebook) | 중 | 전 기능 안정화 후, 연쇄 영향 큼 |

---

## 5. 착수 순서 및 예상 공수

| Phase | 내용 | 예상 공수 | 출처 | 상태 |
|:-----:|------|:--------:|:----:|:----:|
| 1a | **디자인 확산: Launcher + Login** (토큰 교체) | ~2시간 | Plan-18 Ph.8 | ✅ |
| 1b | **디자인 확산: Compare** (border→gap 전환 + 리사이즈 핸들) | ~반나절 | Plan-18 Ph.8 | ✅ |
| 1c | **디자인 확산: Explorer** (3-패널 라운드 + 캔버스) | ~1일 | Plan-18 Ph.8 | ✅ |
| 1d | **디자인 확산: Settings** (배경 + 토큰 교체) | ~2시간 | Plan-18 Ph.8 | ✅ |
| 2 | **검색 구분 UI + ZIP 다운로드 + 검색 UX 통일** | ~1.5일 | Plan-17 Ph.4b | ✅ |
| 3 | **관리자 설정 GUI** (웹 뷰 추출 서브탭 6개 항목) | ~반나절 | Plan-17 Ph.4d | ✅ |
| 4 | **AI 요약·Q&A 패널** (요약 탭 + 챗봇 탭) | ~4일 | Plan-18 Ph.6 + Plan-17 Ph.6 | ✅ |
| 5 | **Markdown 편집기** (공통 코어 분리 + Monaco 재활용 + toast 공통화) | ~2일 | Plan-17 Ph.4c | ✅ |
| 6 | **클릭 네비게이션** (원문↔번역 블록 양방향 매핑) | ~2일 | Plan-17 Ph.4d | ✅ |
| 7 | **마인드맵 패널** (확장 모드, 라이브러리 번들) | ~3일 | Plan-18 Ph.7 | ⬜ |

**전체 합계**: ~15.5일
**Tier 1 (Phase 1a~3)**: ~4.5일 — 즉시 체감되는 완성도 향상
**Tier 2 (Phase 4~5)**: ~6일 — 핵심 기능 보강
**Tier 3 (Phase 6~7)**: ~5일 — 경험 강화

---

## 6. 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| Explorer/Compare CSS 교체 시 기존 레이아웃 깨짐 | 화면별 개별 검증 필요 | 화면당 Light+Dark 전수 검증, 기능 변경 없이 CSS만 |
| ~~에디터 코어 분리 시 Explorer 회귀~~ | ~~편집기 동작 깨짐~~ | ✅ 해소 — Playwright 전수 테스트 통과, 회귀 없음 |
| AI 요약 품질 (Ollama 소형 모델) | 요약이 부정확할 수 있음 | 사용자 편집 가능, 모델 선택 옵션 제공 |
| 마인드맵 라이브러리 폐쇄망 호환 | CDN 의존 시 사용 불가 | UMD 빌드 확인, Markmap 우선 검토 |
| ZIP 대용량 문서 | 이미지 assets 다수 시 용량 | 스트리밍 응답 또는 용량 제한 |
| Q&A 컨텍스트 길이 | `full_translated.md`가 Ollama 컨텍스트 초과 | 청킹 + 관련 섹션만 전달, 8000자 제한 |

---

## 7. 참고

### 출처 매핑

| 본 계획 Phase | 원래 계획서 | 원래 Phase |
|:------------:|-----------|:----------:|
| 1 | Plan-18 (`done-18-notebook-viewer-redesign.md`) | Phase 8 |
| 2 | Plan-17 (`done-17-knowledge-markdown-pipeline.md`) | Phase 4b |
| 3 | Plan-17 | Phase 4d (관리자 설정) |
| 4 | Plan-18 + Plan-17 | Phase 6 + Phase 6 + 섹션 10 |
| 5 | Plan-17 | Phase 4c |
| 6 | Plan-17 | Phase 4d (클릭 네비) |
| 7 | Plan-18 | Phase 7 |

### 완료된 계획서 (아카이브)

- `workbench/plans/done-17-knowledge-markdown-pipeline.md` — Phase 1~5 완료, 4b~4d → 본 계획으로 이관
- `workbench/plans/done-18-notebook-viewer-redesign.md` — Phase 1a~5 완료, 6~8 → 본 계획으로 이관
