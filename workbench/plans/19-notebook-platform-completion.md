# Plan 19: Notebook 플랫폼 완성

> 작성일: 2026-03-26
> 상태: 설계 완료 / Phase 1 미착수
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
| **검색 인덱스 `translated_pages`** | ✅ 저장·검색·`match_source` 구분 완료 | ❌ UI에서 원문/번역 구분 없음 |
| **웹 뷰 설정 키 6개** | ✅ `config.py`에 `TRANSLATOR_WEB_*` 정의, `settings_service.py` 매핑 | ❌ admin-settings GUI 없음 |
| **page_boxes 좌표 데이터** | ✅ `web_page_boxes.json` 저장, `get_web_page_boxes()` API | ❌ 클릭 네비게이션 미구현 |
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

### Phase 1: 플랫폼 디자인 언어 확산 — ~2일

> 출처: Plan-18 Phase 8
> Notebook만 라운드 패널이고 나머지 4개 화면은 구형 → 시각적 불일치 해소.
> 기능 변경 없이 CSS만 교체. 리스크 최저.

**적용 순서:**

| 순서 | 화면 | 변경 범위 | 예상 공수 |
|:----:|------|----------|:--------:|
| 1 | **Explorer** (index.html) | 좌측 TOC + 중앙 콘텐츠 + AI 채팅 패널 → 라운드 카드 + 캔버스 배경 | 반나절 |
| 2 | **Compare** (compare.html) | 좌/우 문서 듀얼 패널 + diff 오버레이 → 라운드 카드 + 갭 | 반나절 |
| 3 | **Launcher** (launcher.html) | 캔버스 배경 + 카드 shadow 조정 (카드는 이미 라운드) | 2시간 |
| 4 | **Login** (login.html) | 로그인 카드 radius/shadow 통일 | 1시간 |

**적용 원칙:**
- `tokens.css`의 `--panel-radius`, `--panel-gap`, `--canvas-bg`, `--panel-shadow` 사용
- 각 화면의 기존 `border-left`, `border-right` → 제거, 갭으로 대체
- `body` 또는 래퍼 `background` → `var(--canvas-bg)`
- 패널 `background` → `var(--white)`, `border-radius` → `var(--panel-radius)`
- 각 화면 전용 CSS에서 하드코딩된 radius/shadow → 토큰 변수로 교체
- 화면별 개별 검증 (Light + Dark)

### Phase 2: 검색 구분 UI + ZIP 다운로드 — ~1.5일

> 출처: Plan-17 Phase 4b
> 검색 인덱스에 `translated_pages`와 `match_source`가 이미 구현되어 있으나 UI에서 활용하지 않음.

- ⬜ 검색 결과에 원문/번역 출처 구분 배지 (`.badge-info` "원문" / `.badge-success` "번역")
- ⬜ 검색 입력란에 필터 옵션 (전체 / 원문만 / 번역만) — 또는 결과 그룹핑
- ⬜ ZIP 다운로드 버튼 (다운로드 메뉴에 추가)
  - 포함: `full_translated.md` + 페이지별 `web_translated.md` + `assets/*.png`
  - 백엔드: `GET /api/translator/document/{doc_id}/download/zip`
  - Python `zipfile` 모듈 (표준 라이브러리, 추가 설치 없음)
- ⬜ 다운로드 메뉴의 "현재 페이지 MD" / "전체 문서 MD" 버튼 상시 표시 (현재 `display:none`)

### Phase 3: 관리자 설정 GUI (웹 뷰) — ~반나절

> 출처: Plan-17 Phase 4d-2
> 백엔드 `config.py`에 6개 키가 정의되어 있으나 admin-settings UI 없음.

- ⬜ `admin-settings.js` 스키마에 "웹 뷰 추출" 서브탭 추가 (기존 "PDF (pdf2zh)" 패턴)
- ⬜ 설정 항목:

| 설정 | 타입 | 현재 기본값 | UI 컴포넌트 |
|------|------|-----------|------------|
| `TRANSLATOR_WEB_TABLE_MODE` | select | `"image"` | `.form-select` ("구조 추출" / "이미지만" / "끄기") |
| `TRANSLATOR_WEB_FORMULA_MODE` | select | `"image"` | `.form-select` ("LaTeX" / "이미지만" / "끄기") |
| `TRANSLATOR_WEB_IMAGE_DPI` | range | `150` | `.form-range` (72~300) |
| `TRANSLATOR_WEB_TABLE_STRATEGY` | select | `"lines_strict"` | `.form-select` |
| `TRANSLATOR_WEB_AUTO_SUMMARY` | checkbox | `false` | 체크박스 |
| `TRANSLATOR_WEB_DEBUG` | checkbox | `false` | 체크박스 |

- ⬜ 각 항목에 `.tooltip-icon` 설명 추가
- ⬜ `settings.json` 저장 + `apply_to_config()` 적용 — 기존 패턴 그대로

### Phase 4: AI 요약·Q&A 패널 — ~4일

> 출처: Plan-18 Phase 6 + Plan-17 Phase 6(챗봇) + Plan-17 섹션 10(자동 요약)
> 아이콘 레일 5번 버튼 활성화. disabled 해제 후 가장 임팩트 큰 기능.

**사전 설계 결정 필요:**
- 챗봇 대상 범위: 현재 열린 문서 1개만 vs 전체 개인 문서
  - 1개 문서: `full_translated.md` (또는 원문 텍스트)를 컨텍스트로 직접 전달 (RAG 불필요)
  - 전체 문서: 개인 문서별 벡터 인덱스 격리 구조 필요 (Explorer RAG와 분리)
  - **권장**: 1개 문서로 시작 → 피드백 후 확장

**구현 항목:**

- ⬜ 패널 UI: 탭 2개 구성 (요약 / Q&A)
  - **요약 탭**: 문서 요약문 + 핵심 키워드 표시, "요약 생성" 버튼
  - **Q&A 탭**: 채팅 인터페이스 (Explorer `ai-chat.js` 패턴 재활용)
- ⬜ 백엔드 — 자동 요약 + 키워드 추출:
  - `POST /api/translator/document/{doc_id}/summary` → Ollama 요약 생성
  - 데이터 소스: `full_translated.md` (번역 있으면) 또는 원문 텍스트 (없으면)
  - 결과 저장: `meta.json`의 `summary` / `keywords` 필드 (frontmatter와 동기화)
  - `TRANSLATOR_WEB_AUTO_SUMMARY = true` 시 번역 완료 후 자동 실행
- ⬜ 백엔드 — Q&A:
  - `POST /api/translator/document/{doc_id}/chat` → Ollama 질의응답
  - 컨텍스트: `full_translated.md` 전문 (문서 1개 기준, 8000자 제한)
  - 세션: Explorer `conversation.py` 패턴 재활용 (인메모리 LRU)
- ⬜ 프론트엔드 — 아이콘 레일 5번 활성화:
  - `disabled` 제거, `data-panel="ai-summary"` 핸들러 연결
  - 패널 헤더 `#hdr-ai` 추가 (탭 전환 UI)
  - `_showToolContent('ai-summary')` 지원
- ⬜ 6번 "문서 요약" 버튼 → 5번과 통합 (별도 패널 불필요, 탭으로 충분)
  - 레일에서 6번 제거하거나 5번과 병합 → 레일 아이콘 6개로 축소

### Phase 5: Markdown 편집기 — ~2일

> 출처: Plan-17 Phase 4c
> 번역 결과를 사용자가 직접 수정 가능 → "지식 저장소" 비전의 핵심 조각.

- ⬜ EasyMDE 번들 준비 (~400KB, CodeMirror 포함) → `js/lib/easymde/`
  - 폐쇄망 호환: UMD 빌드 `<script>` 로드
  - 대안 검토: Monaco Editor가 이미 `js/monaco-editor/`에 존재 — 재활용 가능성 평가
- ⬜ 웹 뷰 패널 헤더에 "편집" 버튼 추가 (번역 완료 상태에서만 노출)
- ⬜ 편집 UI: 모달 오버레이 (`.modal-overlay` + `.modal-box` 패턴) 또는 패널 내 인라인
- ⬜ 저장: `PUT /api/translator/web-view/{doc_id}/page/{page_num}` (API 이미 설계됨)
- ⬜ 저장 완료 → marked.js 재렌더링 + `full_translated.md` 자동 재병합
- ⬜ 다크모드 검증 (EasyMDE/Monaco 테마 오버라이드)

### Phase 6: 클릭 네비게이션 — ~2일

> 출처: Plan-17 Phase 4d-1
> `web_page_boxes.json`에 블록별 PDF 좌표가 이미 저장되어 있음. 프론트엔드만 구현.

- ⬜ 웹 뷰 Markdown 렌더링 시 블록별 `data-box-index` 속성 부여
- ⬜ 우측 Markdown 블록 클릭 → 좌측 PDF 해당 영역으로 스크롤 + 박스 하이라이트
- ⬜ 좌측 PDF 영역 클릭 → 우측 Markdown 해당 블록으로 스크롤 + 배경 플래시
- ⬜ 기존 마킹 시스템의 `scrollIntoView` + 하이라이트 패턴 재활용
- ⬜ `GET /api/translator/web-translate/{doc_id}/page/{page_num}/boxes` API 연결

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
| 1 | **플랫폼 디자인 언어 확산** (Explorer→Compare→Launcher→Login) | ~2일 | Plan-18 Ph.8 | ⬜ |
| 2 | **검색 구분 UI + ZIP 다운로드** | ~1.5일 | Plan-17 Ph.4b | ⬜ |
| 3 | **관리자 설정 GUI** (웹 뷰 추출 설정) | ~반나절 | Plan-17 Ph.4d | ⬜ |
| 4 | **AI 요약·Q&A 패널** (요약 탭 + 챗봇 탭) | ~4일 | Plan-18 Ph.6 + Plan-17 Ph.6 | ⬜ |
| 5 | **Markdown 편집기** (EasyMDE 또는 Monaco) | ~2일 | Plan-17 Ph.4c | ⬜ |
| 6 | **클릭 네비게이션** (원문↔번역 블록 매핑) | ~2일 | Plan-17 Ph.4d | ⬜ |
| 7 | **마인드맵 패널** (확장 모드, 라이브러리 번들) | ~3일 | Plan-18 Ph.7 | ⬜ |

**전체 합계**: ~15일
**Tier 1 (Phase 1~3)**: ~4일 — 즉시 체감되는 완성도 향상
**Tier 2 (Phase 4~5)**: ~6일 — 핵심 기능 보강
**Tier 3 (Phase 6~7)**: ~5일 — 경험 강화

---

## 6. 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| Explorer/Compare CSS 교체 시 기존 레이아웃 깨짐 | 화면별 개별 검증 필요 | 화면당 Light+Dark 전수 검증, 기능 변경 없이 CSS만 |
| EasyMDE CodeMirror CSS 충돌 | 다크모드 깨짐 | Monaco Editor 재활용 대안 검토, CSS 스코핑 |
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
