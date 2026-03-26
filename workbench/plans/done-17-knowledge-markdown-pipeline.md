# Plan 17: Notebook — 개인 지식 저장소 구축

> 작성일: 2026-03-19
> 최종 갱신: 2026-03-26
> 상태: Phase 1~5 완료 (핵심 완료). 잔여 4b~4d → Plan-19로 이관
> 브랜치: `plan17-library`
> 선행: Plan 16 완료 (Phase 1~4)
> 범위: Phase 1~5 확정 / Phase 6~7 피드백 후 별도 계획

---

## 1. 목적

Translator 시스템을 **Notebook(개인 지식 저장소)**로 확장한다.
PDF 문서를 Markdown으로 추출·번역·저장하여 검색·편집·AI 활용이 가능한 **개인 지식 자산**을 구축한다.

## 2. 배경

### 2.1 시스템 리네이밍: Translator → Notebook

Translator는 이미 개인 지식 저장소의 뼈대를 갖추고 있다:

| 기능 | 번역과 무관 | 이미 구현 |
|------|:----------:|:--------:|
| 개인 작업공간 (유저별 격리) | ✅ | ✅ |
| 폴더 관리 (트리 패널, 드래그앤드롭) | ✅ | ✅ |
| 마킹/하이라이트 (4색) | ✅ | ✅ |
| 메모 (팝오버) | ✅ | ✅ |
| 전역 검색 (본문 + 메모) | ✅ | ✅ |
| PDF 다운로드 | ✅ | ✅ |
| PDF 번역 (pdf2zh, 텍스트 엔진) | | ✅ |
| 용어집 | | ✅ |

**번역은 기능 중 하나**이지, 시스템의 정체성이 아니다.

### 2.2 리네이밍 범위 — 최소 변경 원칙

**파일명은 유지하고, 사용자가 보는 UI 텍스트만 변경한다.**

검토 결과 파일명 변경(`translator.html` → `library.html`)은 연쇄 영향이 크다:
`launcher.html` 참조, `platform-header.js`의 `currentSystem`, `admin-settings.js`의 스키마 키,
`settings.json`의 그룹 키(기존 사용자 설정 유실 위험), 문서 전반.
따라서 **파일명·API 경로·데이터 경로·설정 키는 모두 `translator` 그대로 유지**한다.

| 변경 | 내용 |
|------|------|
| ✅ UI 텍스트 | 런처 카드 이름/설명을 "Notebook (개인 문서함)"으로, 헤더 타이틀, HTML `<title>` |
| ❌ 파일명 | `translator.html`, `translator.css`, `translator.js` 유지 |
| ❌ API 경로 | `/api/translator/*` 유지 |
| ❌ 데이터 경로 | `data/translator/` 유지 |
| ❌ 설정 키 | `admin-settings.js`의 `id: 'translator'`, `settings.json` 그룹 키 유지 |

> 파일명까지 변경하려면 전 기능 안정화 후 별도 리네이밍 작업으로 분리. 본 계획 범위 밖.

### 2.3 Plan 16에서의 이관 사유

Plan 16 Phase 5는 "텍스트 엔진의 HTML 출력"으로 설계되었으나, 다음 변화에 의해 독립 계획으로 분리:

1. **출력 포맷**: HTML → **Markdown** (편집·외부 호환·RAG 연계에 유리)
2. **추출 엔진**: DocLayout-YOLO 재활용 → **PyMuPDF4LLM** (표 구조 추출, 이미지 일괄 처리)
3. **범위**: 단순 뷰어 → **지식 저장소 기반** (챗봇, 검색, 문서 연결의 토대)
4. **대상 문서**: 논문 → **전체 기술문서** (논문, 지침서, 가이드, 스팩 등)
5. **경영층 방향**: NotebookLM + Obsidian의 폐쇄망 버전

### 2.4 대상 문서 유형

| 유형 | 특성 | 핵심 추출 대상 |
|------|------|--------------|
| 학술 논문 | 2단 레이아웃, 수식, 참조 | 텍스트, 수식, 그림 |
| 기술 지침서 | 장절 구조, 절차 표, 주의사항 블록 | 텍스트, **표**, 주의 블록 |
| 가이드/매뉴얼 | 그림 多, 단계별 설명 | 텍스트, **이미지**, 리스트 |
| 스팩/규격 문서 | 요구사항 표, 물성 데이터, 수식 | **표**, 텍스트, 수식 |
| 회의록/보고서 | 단순 텍스트, 간단한 표 | 텍스트, 표 |

**설계 제약**: NotebookLM과 동일하게 **PDF 전용**. 다른 포맷은 외부에서 PDF로 변환 후 업로드.

### 2.5 Markdown을 선택하는 이유

| 관점 | PDF 유지 | HTML 생성 | **Markdown 생성** |
|------|---------|----------|-----------------|
| 검색 | 별도 텍스트 추출 필요 | HTML 파싱 필요 | **즉시 검색 가능** |
| RAG | 별도 청킹 파이프라인 | 태그 제거 후 청킹 | **구조 보존 자연 청킹** |
| 편집 | 불가 | 복잡 (HTML 지식 필요) | **누구나 가능** |
| 외부 호환 | PDF 뷰어 | 브라우저 | **Obsidian, Typora, VS Code 등** |
| 다크모드 | PDF.js 미지원 | CSS 필요 | **렌더러가 자동 처리** |
| 복사/붙여넣기 | 깨짐 빈번 | 가능 | **완벽** |

> Explorer는 Word→HTML 유지 (복잡한 서식: 병합 표, MathML 수식 필요).
> Notebook은 PDF→Markdown (번역 결과의 편집·활용·지식화가 목적).

---

## 3. 핵심 기술 결정

### 3.1 추출 엔진: PyMuPDF4LLM

| 후보 | 장점 | 단점 | 판정 |
|------|------|------|------|
| **PyMuPDF4LLM** | 이미 PyMuPDF 사용 중, 추가 설치 최소, 표 구조 추출, 이미지 일괄 저장 | 스캔 PDF에서 표 추출 한계 | **✅ 채택** |
| MinerU | 최고 품질, DocLayout-YOLO 내장, 수식 LaTeX 변환 | 별도 대형 모델 필요 (~2GB), 폐쇄망 설치 복잡 | 보류 |
| Marker | 인기, LLM 연동 고품질 | GPU 필수, 별도 모델 다운로드, 표 약함 | 부적합 |
| 텍스트 엔진 재활용 | 기존 코드 활용 | 표 구조 미추출, 이미지 별도 저장 안 됨 | 부적합 |

**선택 근거**:
- `pymupdf4llm`은 PyMuPDF 순수 Python 래퍼, `.whl` 하나 추가로 완료
- `to_markdown(pages=[N])` — 페이지 지정 추출 지원 확인 필요 (Phase 1 사전 검증)
- `page_chunks=True` 시 JSON 출력에 bbox 좌표 포함 여부도 확인 필요 (클릭 네비게이션 전제)

### 3.2 표 처리 전략: 이중 접근

기술문서에서 표는 핵심 데이터다. 검색·복사·RAG에서 활용되려면 구조화된 텍스트여야 한다.

| 단계 | 처리 | 결과 |
|------|------|------|
| **1차: PyMuPDF 구조 추출** | `find_tables()` → 셀 데이터 추출 | Markdown 테이블 |
| **2차: 추출 실패 시** | 해당 영역 pixmap 캡처 → Ollama에 이미지 전달 | Markdown 테이블 (LLM 생성) |
| **백업: 어떤 경우든** | 원본 영역 이미지도 함께 저장 | 원본 대조용 이미지 |

관리자 설정 `TRANSLATOR_WEB_TABLE_MODE`로 동작 제어 (섹션 8 참조).

### 3.3 이미지 처리

| 유형 | 처리 | Markdown 표현 |
|------|------|-------------|
| 그림 (figure) | PyMuPDF4LLM `write_images=True` → PNG 추출 | `![Figure](assets/fig_0.png)` |
| 차트/그래프 | 이미지 추출 | `![Chart](assets/chart_0.png)` |

### 3.4 수식 처리: 관리자 설정 기반

PDF 수식은 Word(OMML→MathML)와 달리 **구조 정보 없이 렌더링된 이미지**로 존재.

**경량 후보: Pix2Text (~200MB)** — Mathpix 오픈소스 대안, TrOCR 기반, 86.2% 정확도.

관리자 설정 `TRANSLATOR_WEB_FORMULA_MODE`로 동작 제어:

| 모드 | 동작 | 모델 필요 |
|------|------|:---------:|
| `latex` | Pix2Text LaTeX 변환 시도 → 실패 시 이미지 백업 | ✅ |
| `image` | 수식 영역 이미지 캡처만 (기본값) | ❌ |
| `off` | 수식 영역 무시 | ❌ |

### 3.5 번역 전략

Markdown 추출 후 번역은 **블록 단위**로 수행:

| 블록 유형 | 번역 방식 |
|----------|----------|
| 제목 (`## ...`) | 개별 번역 |
| 본문 단락 | 개별 번역 (긴 단락은 분할) |
| 표 셀 데이터 | 셀 텍스트 일괄 번역 (**Markdown 표 구문 보존**) |
| 리스트 항목 | 항목 그룹 일괄 번역 |
| 이미지 캡션 | 개별 번역 |
| 이미지/수식 | 번역 대상 아님 (그대로 유지) |

> 표 셀 번역은 Markdown 표 구문(`| | |`)을 보존하면서 셀 내용만 번역하는 로직이 필요. 공수 주의.

기존 용어집(`glossary.json`)도 동일하게 프롬프트 주입 방식으로 적용.
Ollama 호출은 기존 `text_translator.py`의 직접 호출 패턴(`requests.post`)을 따름.

### 3.6 브라우저 렌더링

| 용도 | 라이브러리 | 실제 크기 | 비고 |
|------|-----------|----------|------|
| MD→HTML 렌더링 | **marked.js** | ~40KB (UMD 빌드) | GFM 지원, `<script>` 로드 확인 필요 |
| XSS 방어 | **DOMPurify** | ~15KB | marked.js 출력 필수 새니타이징 |
| LaTeX 렌더링 | **KaTeX** | ~300KB | `formula_mode=latex` 시에만 로드 |
| Markdown 편집 | **EasyMDE** | ~400KB (JS+CSS+CodeMirror 포함) | CodeMirror CSS 충돌 검증 필요 |

> EasyMDE 실제 번들은 CodeMirror 포함 ~400KB. `js/lib/easymde/`에 배치.
> CodeMirror 기본 CSS가 `tokens.css`와 충돌하지 않는지 Phase 4에서 검증.
> marked.js, DOMPurify는 Vanilla JS `<script>` 로드 가능한 UMD/IIFE 빌드 사용.

모든 라이브러리는 `js/lib/`에 번들 (PDF.js, Monaco와 동일 패턴). 폐쇄망 완전 호환.

---

## 4. 데이터 관리 설계

### 4.1 현재 검색 구조 (유지)

현재 시스템은 업로드 시 PyMuPDF `get_text()`로 원문 텍스트를 추출하여 JSON 검색 인덱스를 구축:

```json
// _search_index.json (유저별, data/translator/{username}/)
{
  "doc_id": {
    "title": "문서 제목",
    "pages": { "1": "페이지1 원문 텍스트", "2": "..." }
  }
}
```

이 구조를 **그대로 유지**하고, 번역 Markdown 텍스트를 **별도 키로** 검색 인덱스에 추가:

```json
{
  "doc_id": {
    "title": "문서 제목",
    "pages": { "1": "원문 텍스트", "2": "..." },
    "translated_pages": { "1": "번역 텍스트", "3": "..." }
  }
}
```

> 원문/번역을 분리하면 검색 결과에서 매칭 출처를 구분할 수 있음.

### 4.2 저장 구조

```
data/translator/{username}/{doc_id}/
├── original.pdf                    ← 원본 (기존)
├── meta.json                       ← 문서 메타데이터 (기존)
├── pages/{N}/
│   ├── translated.pdf              ← PDF 엔진 결과 (기존, 유지)
│   ├── text_translated.pdf         ← 텍스트 엔진 결과 (기존, 유지)
│   ├── text_mapping.json           ← 텍스트 엔진 매핑 (기존, 유지)
│   ├── web_translated.md           ← 신규: 웹 뷰 번역 Markdown
│   └── assets/                     ← 신규: 추출된 이미지/표
│       ├── fig_0.png
│       ├── table_0.png
│       └── formula_0.png
└── full_translated.md              ← 신규: 전체 번역 병합 (번역된 페이지만)
```

> `meta.json`의 `page_status`에 웹 뷰 상태를 추가:
> `page_status.{N}.web_translate: { status, model, translated_at }`
> (기존 `text_translate` 키와 동일 패턴, `translator_service.py:674` 참조)

### 4.3 Markdown Frontmatter

```yaml
---
title: "Deep-RACO: 자율 회피 통신 운용기"
source: "original.pdf"
page: 3
total_pages: 42
model: "gemma3:27b"
translated_at: "2026-03-19T15:35:00"
summary: ""
keywords: []
tags: []
---

## 3.2 시스템 아키텍처
...
```

### 4.4 전체 문서 병합

페이지별 웹 뷰 번역이 누적되면 `full_translated.md`로 자동 병합.
각 페이지 구간에 사용 모델/번역 일자를 주석으로 포함:

```markdown
<!-- Page 1 | gemma3:27b | 2026-03-19 -->
## 1. 프로젝트 개요
...

<!-- Page 3 | gemma3:12b | 2026-03-20 -->
## 2. 아키텍처 드라이버
...
```

> 페이지별 독립 번역의 한계(용어/문체 불일치)를 사용자가 인지할 수 있도록 모델 정보 포함.

### 4.5 데이터 수명 관리

| 데이터 | 생성 시점 | 갱신 시점 | 삭제 시점 |
|--------|----------|----------|----------|
| `web_translated.md` | 웹 뷰 번역 완료 시 | 재번역 또는 사용자 편집 시 | 문서 삭제 시 |
| `assets/*.png` | 웹 뷰 번역 시 함께 추출 | 재번역 시 | 문서 삭제 시 |
| `full_translated.md` | 페이지 번역 완료마다 | 추가 번역/편집 시 자동 갱신 | 문서 삭제 시 |
| 검색 인덱스 (번역) | 번역 완료 시 추가 | 재번역/편집 시 갱신 | 문서 삭제 시 |

---

## 5. 프론트엔드 설계

### 5.1 설계 원칙

- **기존 UX 패턴 최대 재활용** — Explorer, 현재 Translator에서 검증된 컴포넌트·레이아웃·동선 사용
- **UX 지침 준수** — `tokens.css` 변수, `components.css` 클래스, `modal.css` 패턴
- **불필요한 UI 제거** — 번역 결과가 없는데 빈 우측 패널을 보여주지 않음
- **기존 코드 패턴 엄수** — 엔진 분기(`updateRightPanel()`), 폴링(`startPolling()`/`stopPolling()`), 모달(glossary 패턴), config(`TRANSLATOR_*`)

### 5.2 뷰어 레이아웃 — 적응형 싱글/듀얼

**싱글이 기본(원문 PDF 전체 너비). 번역 완료 시 듀얼로 자동 확장.**

```
상태 1: 기본 (싱글 뷰어 — 번역 전 또는 번역 불필요 문서)
┌─────────────────────────────────────────────┐
│  [툴바: 번역모드 ▾ | 모델 ▾ | 번역 ▶ | ...]  │
├─────────────────────────────────────────────┤
│                                             │
│  원문 PDF (전체 너비)                        │
│  마킹/하이라이트, 메모, AI 선택 번역 등       │
│  (기존 기능 그대로)                          │
│                                        💬   │ ← 챗봇: Explorer 플로팅 아이콘 패턴
└─────────────────────────────────────────────┘

상태 2: 번역 완료 → 자동 듀얼 (기존 레이아웃 그대로)
┌──────────────┬──────────────────────────────┐
│  원문 PDF     │  번역 결과                    │
│              │  (PDF / 텍스트PDF / 웹뷰MD)   │
│              │                         💬   │
└──────────────┴──────────────────────────────┘

상태 3: 웹뷰 번역본 편집 → 모달 (Explorer Monaco 패턴)
┌──────────────┬──────────────────────────────┐
│      ┌───────┴───────────────────────┐      │
│      │  EasyMDE 편집기 (모달 오버레이)  │      │
│      │  .modal-overlay + .modal-box   │      │
│      │  저장 시 우측 패널 즉시 갱신     │      │
│      └───────────────────────────────┘      │
└──────────────┴──────────────────────────────┘
```

**싱글↔듀얼 전환**:
- 현재 우측 패널의 `pending` 상태(`$rightPlaceholder` 표시)를 **완전히 숨기는** 것으로 변경
- 번역 결과가 있을 때만 우측 패널 표시 + 좌측 축소
- 기존 리사이즈 핸들 로직 유지

### 5.3 엔진 토글 확장

기존 `.mode-toggle` 패턴에 `data-engine="web"` 버튼 추가:

```html
<!-- 기존 패턴 그대로 -->
<div class="mode-toggle" id="engine-toggle">
  <button class="mode-toggle-btn active" data-engine="pdf">PDF</button>
  <button class="mode-toggle-btn" data-engine="text">텍스트</button>
  <button class="mode-toggle-btn" data-engine="web">웹 뷰</button>  <!-- 추가 -->
</div>
```

| 모드 | 좌측 패널 | 우측 패널 (번역 결과 있을 때) | 스크롤 동기화 |
|------|-----------|--------------------------|:----------:|
| PDF | 원문 PDF | 번역 PDF (pdf2zh) | O |
| 텍스트 | 원문 PDF | 번역 PDF (재조립) | O |
| **웹 뷰** | 원문 PDF | **번역 Markdown (marked.js)** | **X** |

> 번역 결과가 없으면 어떤 모드든 싱글 뷰어(원문 PDF 전체 너비).

### 5.4 translator.js 구조 개선 (사전 리팩토링)

현재 `updateRightPanel()` 내의 `if/else` 분기에 세 번째 엔진을 추가하면 유지보수성이 심각하게 악화된다.
Phase 3 착수 시 **엔진별 전략 객체 분리**를 선행:

```javascript
// 모드별 전략 객체 (미니 리팩토링)
var engineHandlers = {
    pdf:  { updatePanel: updatePdfPanel,  startTranslation: startPdfTranslation,  ... },
    text: { updatePanel: updateTextPanel, startTranslation: startTextTranslation, ... },
    web:  { updatePanel: updateWebPanel,  startTranslation: startWebTranslation,  ... }
};

// 기존 if/else 대체
engineHandlers[translateEngine].updatePanel(currentPage);
```

이 리팩토링은 기존 동작을 변경하지 않으면서, 향후 모드 추가/수정 시 한 곳만 수정하면 되는 구조를 만든다.

### 5.5 상태 캐시 + 폴링 (web 엔진)

기존 패턴을 그대로 따름:

```javascript
// 기존: pageStatusCache, textPageStatusCache
// 추가: webPageStatusCache
var webPageStatusCache = {};
var webPollingTimer = null;

function startWebPolling() { /* startPolling()과 동일 패턴, 3초 간격 */ }
function stopWebPolling()  { /* stopPolling()과 동일 패턴 */ }
```

`goToPage()`, `showList()`에서 `stopWebPolling()` 호출 추가 필수.

### 5.6 툴바 — 모드별 동적 버튼

| 버튼 | PDF | 텍스트 | 웹 뷰 | 비고 |
|------|:---:|:------:|:-----:|------|
| 번역모드 선택 | ✅ | ✅ | ✅ | 기존 |
| 모델 선택 | ✅ | ✅ | ✅ | 기존 |
| 번역 실행 | ✅ | ✅ | ✅ | 기존 |
| 용어집 | ✅ | ✅ | ✅ | 기존 |
| 다운로드 | ✅ | ✅ | ✅ | 웹 뷰 시 .md 다운로드 추가 |
| **편집** | — | — | **✅** | 웹 뷰 + 번역 완료 시에만 노출 |
| 폰트 크기 | ✅ | ✅ | ✅ | 기존 |

### 5.7 편집기 — Explorer 패턴 재활용

웹 뷰 모드에서 [편집] 클릭 시 **모달 오버레이**로 EasyMDE 편집기 표시.
Explorer Monaco 편집기 팝업 + glossary 모달과 동일한 UX 패턴.

- 모달: `.modal-overlay` + `.modal-box` (glossary 모달 `translator.html:226~257` 참조)
- 닫기: 3종 (close 버튼, overlay 배경 클릭, Esc 키) — 기존 패턴 그대로
- 저장: `.btn-primary` → `PUT /api/translator/web-view/{doc_id}/page/{page_num}`
- 저장 완료: 모달 닫기 → 우측 패널 `marked.js` 재렌더링 → `full_translated.md` 자동 재병합
- EasyMDE 다크모드: `data-theme="dark"` 시 EasyMDE 테마 CSS 오버라이드 필요 (검증)

### 5.8 클릭 네비게이션 (원문 ↔ 번역)

듀얼 모드에서 **클릭 기반 양방향 탐색**:

- 우측 Markdown 블록 클릭 → 좌측 PDF 해당 영역으로 스크롤 + 박스 하이라이트
- 좌측 PDF 영역 클릭 → 우측 Markdown 해당 블록으로 스크롤 + 배경 플래시
- 기존 마킹 시스템의 `scrollIntoView` + 하이라이트 패턴 재활용

> **사전 확인 필요**: PyMuPDF4LLM `to_markdown(page_chunks=True)` 출력에 원본 PDF 좌표(bbox)가 포함되는지.
> 포함되지 않으면 별도 좌표 추출 로직이 필요하며, 클릭 네비게이션은 Phase 3에서 제외하고 후속 Phase로 이동.

### 5.9 챗봇 연동

Explorer의 기존 패턴을 **그대로** 재활용:
- 우하단 플로팅 아이콘 (`ai-chat.js` 패턴)
- 클릭 시 대화창 슬라이드
- RAG 소스: 현재 열린 문서의 `full_translated.md` (번역 전이면 기존 검색 인덱스의 원문 텍스트)
- 백엔드: Explorer `conversation.py` + `query_rewriter.py` 재활용

> **결정 필요**: 챗봇이 현재 문서 1개만 대상인지, 전체 개인 문서를 대상으로 하는지.
> 전체 대상이면 문서별 벡터 인덱스를 언제 생성하는지 (번역 완료 시? 별도 인덱싱?).
> Explorer RAG는 조직 공용 문서 대상이므로 개인 문서용 인덱스 격리 구조가 다름.
> → Phase 6 착수 전 결정.

### 5.10 좌측 트리 패널

**기존 그대로 유지**. 호버 트리거 + 핀 고정, 폴더 관리, 드래그앤드롭 — 변경 없음.

---

## 6. API 설계

### 6.1 신규 엔드포인트

기존 PDF/텍스트 번역 API 패턴(`translate → status → cancel`)과 동일 구조:

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/translator/web-translate/{doc_id}/page/{page_num}` | 웹 뷰 번역 시작 (추출+번역 일괄) |
| GET | `/api/translator/web-translate/{doc_id}/page/{page_num}/status` | 번역 상태 조회 |
| POST | `/api/translator/web-translate/{doc_id}/page/{page_num}/cancel` | 번역 취소 |
| GET | `/api/translator/web-view/{doc_id}/page/{page_num}` | 페이지 번역 Markdown 서빙 |
| GET | `/api/translator/web-view/{doc_id}/full` | 전체 병합 Markdown 서빙 |
| GET | `/api/translator/web-view/{doc_id}/page/{page_num}/assets/{filename}` | 이미지 자산 서빙 |
| PUT | `/api/translator/web-view/{doc_id}/page/{page_num}` | Markdown 편집 저장 |

> 동시성: 기존 `_active_tasks`(PDF), `_text_active_tasks`(텍스트)와 별도로 `_web_active_tasks` 딕셔너리 사용.
> 같은 페이지의 PDF 번역 + 웹 뷰 번역 동시 실행 허용 (서로 독립 파이프라인).

### 6.2 처리 흐름

```
사용자: "웹 뷰" 모드 선택 → 페이지 이동

1. web_translated.md 존재?
   YES → 3으로
   NO  → 2. 번역 버튼 표시 (기존 번역 버튼과 동일 위치)
         클릭 시:
           a. PyMuPDF4LLM으로 해당 페이지 추출 (텍스트+표+이미지 → Markdown)
           b. 추출된 Markdown을 블록 단위 Ollama 번역
           c. web_translated.md + assets/ 저장
           d. meta.json page_status 갱신
           e. 검색 인덱스에 번역 텍스트 추가
           → 3으로

3. web_translated.md를 API로 전달 → 프론트에서 marked.js + DOMPurify 렌더링 → 듀얼 전환
```

---

## 7. 실행 계획

### Phase 1: 추출 파이프라인 (PyMuPDF4LLM) — 완료

- ✅ `pymupdf4llm` 1.27.2.1 설치 + 폐쇄망 whl 준비
- ✅ 사전 검증 완료 (`pages=[N]`, `page_boxes` bbox, 표 구조 추출, 이미지 추출)
- ✅ `services/md_extractor.py` 구현 (표/수식/이미지 모드 분기, 디버그 모드)
- ✅ 추출 품질 검증 (MyPaper PDF)
- ✅ 관리자 설정 키 추가 (`config.py`, `settings_service.py`)
- ✅ 코드 리뷰 반영 (`table_mode` 분기, `_remove_markdown_tables` 개선)

> PyMuPDF 1.25.2→1.27.2 업그레이드됨. 기존 기능 정상. (리스크 섹션 참조)

### Phase 2: 번역 파이프라인 — 완료

- ✅ `services/md_translator.py` 구현 (블록 파서 6종, 일괄 번역, 표 셀 번역, 용어집, frontmatter)
- ✅ `translator_service.py` 웹 번역 서비스 통합 (start/status/cancel/get_md/get_boxes)
- ✅ `full_translated.md` 자동 병합 (페이지별 모델/일자 주석)
- ✅ 검색 인덱스 확장 (`translated_pages` 별도 키, `match_source`)
- ✅ 코드 리뷰 반영 (일괄 번역 65초→22초, Markdown 보존 프롬프트, 죽은 코드 제거)
- ⬜ 자동 요약 + 키워드 추출 → Phase 5+ 이후

### Phase 3: 프론트엔드 (웹 뷰) — 완료

- ✅ API 7개 엔드포인트, marked.js + DOMPurify 번들
- ✅ 엔진 토글 3종, 웹 뷰 엔진 통합, 폴링/캐시/취소
- ✅ Markdown 스타일시트 (tokens.css 변수, 다크모드)
- ✅ E2E 테스트 + PDF 회귀 테스트 통과
- ✅ 코드 리뷰 반영 (로딩 스피너, 범위 번역 숨김, 에러 클래스, 용어집 태그 방지)

> 백엔드 실행 시 venv 활성화 필수 (`pymupdf4llm` 의존)

### Phase 3+: 사용자 피드백 + 품질 개선 — 완료

**UX 개선:**
- ✅ 엔진 토글 툴바 가장 우측 끝으로 이동
- ✅ Markdown 스타일 Explorer 패턴 통일 (max-width 900px, line-height 1.8, 좌측 정렬)
- ✅ done 상태 툴바: `[웹뷰]` 접두사 + 모델/시간
- ✅ 로딩 스피너, 범위 번역 숨김, 에러 클래스, 용어집 태그 방지

**이미지/표/수식 처리:**
- ✅ 비텍스트 영역 일괄 이미지 캡처 (picture/formula/기타 → 자동 캡처)
- ✅ `<figure>` + `<figcaption>` 래핑 (HTML5 표준, 캡션 위/아래 자동 감지)
- ✅ 이미지 크기: 페이지 대비 폭 비율(%) 적용
- ✅ 캡션 패턴: 아라비아 숫자 + 로마 숫자(I,II,III...) 대응
- ✅ `table_mode` 기본값 `"image"` (표/수식/이미지 모두 이미지 기본)
- ✅ `table_mode="extract"` 시 Markdown 테이블 구조 추출 (관리자 전환 가능)

**텍스트 정리:**
- ✅ 제목 이탤릭/볼드 서식 제거
- ✅ PyMuPDF4LLM 아티팩트 제거 (omitted placeholder, `****` 빈 서식)
- ✅ figure 전후 빈 줄 보장 (제목 ## 렌더링)

**데이터 무결성:**
- ✅ 재번역 시 기존 assets 폴더 정리 (고아 파일 방지)
- ✅ 검색 인덱스 번역 텍스트 포함 검증 (`match_source: "translated"` 정상)
- ✅ `full_translated.md` 병합 검증 (다수 문서 정상)
- ✅ 다크모드 검증 (텍스트/제목/배경/이미지 정상)

**알려진 한계 (현재 허용):**
- 벡터 그래픽 이미지 약간 잘림 — PyMuPDF4LLM bbox 감지 정밀도 한계, 패딩 3px
- 번역 속도가 PDF 번역보다 느림 — Ollama 블록별 호출
- 웹 뷰에서 마킹/메모 미동작 — PDF 텍스트 레이어 기반 기능이라 div에서 비동작
- 자동 표 품질 판별 + 이미지 폴백 — 향후 (다양한 문서 패턴 축적 후)
- 제목 레벨 개선 (PDF TOC 활용) — 향후 (다양한 문서 테스트 후)
- 알고리즘/의사코드 블록 — PyMuPDF4LLM이 `text` class로 분류하여 일반 텍스트로 번역됨. 향후 "Algorithm" 키워드 감지 시 번역 스킵 처리 검토
- 번역 모델 선택 — 범용 모델(`gemma3:4b` 등)은 Markdown 서식(`**`, `##`)을 임의 추가/제거할 수 있음. **번역 특화 모델(`translategemma`) 사용 권장**
- 인라인 수식 — 비텍스트 일괄 캡처 시 작은 인라인 수식(변수, 짧은 표현식)까지 이미지로 캡처되면 문단 파편화 + 속도 저하 발생. 크기 필터링 필요 (향후)
- 특수 2컬럼 PDF — 텍스트 스트림이 행 단위로 저장된 PDF에서 `column_boxes()` 실패 → 좌우 컬럼 교차 혼합. **Phase 4a DocLayout-YOLO 폴백으로 해결 예정**

### Phase 4a: 웹 뷰 읽기 경험 + 즉시 가치 UX — 완료

> **핵심 목표**: 웹 뷰를 "주 읽기 경험"으로 격상. Notebook 비전의 첫 단추.

- ✅ **웹 뷰 전체 문서 연속 스크롤** (아래 구현 설계 참조)
- ✅ **DocLayout-YOLO 컬럼 감지 폴백** (아래 설계 참조)
- ✅ 싱글/듀얼 적응형 레이아웃 (번역 없으면 원문 PDF 전체 너비)
- ✅ 카드 목록에 웹뷰 번역 상태 반영
- ✅ MD 다운로드 (단일 페이지 + 전체 병합)
- ✅ 웹 뷰 폰트 크기 조절 (CSS font-size)

#### 웹 뷰 전체 문서 연속 스크롤 — 구현 설계

**배경**: 현재 웹 뷰는 페이지 단위로 Markdown을 표시한다. 하지만 Notebook의 핵심 가치는
**번역된 콘텐츠의 연속 읽기**에 있으며, 이를 위해 전체 문서를 이어 붙여 스크롤하는 모드가 필요하다.

**업계 사례**:
- NotebookLM: 원문은 페이지 참조용, AI 생성 콘텐츠(요약/노트)는 연속 스크롤
- Readable/Scholarcy: 번역·요약 결과를 연속 텍스트로 제공, 원문 PDF는 별도 참조
- Obsidian: 마크다운 파일이 1등 시민, 원본은 링크/임베드

**기본 원칙**:
1. 좌측 PDF 뷰어는 그대로 유지 (페이지 단위, 참조용)
2. 웹 뷰에 **"페이지별"(기존)** / **"전체 문서"(신규)** 두 가지 보기 모드 제공
3. 전체 문서 모드에서는 좌측 PDF가 우측 스크롤 위치에 따라 해당 페이지로 자동 이동

**데이터 소스**: `full_translated.md` (이미 존재, 페이지별 HTML 주석 구분)

```markdown
<!-- Page 1 | gemma3:27b | 2026-03-19 -->
## 1. 프로젝트 개요
...

<!-- Page 3 | gemma3:12b | 2026-03-20 -->
## 2. 아키텍처 드라이버
...
```

**렌더링 흐름**:
1. `GET /api/translator/web-view/{doc_id}/full` → 전체 Markdown 수신
2. `<!-- Page N -->` 주석을 기준으로 **섹션 div** 래핑:
   ```html
   <div class="web-page-section" data-page="1">
     <div class="web-page-marker">Page 1</div>
     [번역된 Markdown HTML]
   </div>
   <div class="web-page-section web-page-not-translated" data-page="2">
     <div class="web-page-placeholder">
       <p>2 페이지 — 아직 번역되지 않았습니다</p>
       <button class="btn btn-primary btn-sm">번역하기</button>
     </div>
   </div>
   <div class="web-page-section" data-page="3">
     <div class="web-page-marker">Page 3</div>
     [번역된 Markdown HTML]
   </div>
   ```
3. 미번역 페이지는 플레이스홀더 카드 (페이지 번호 + [번역하기] 버튼)
4. `IntersectionObserver`로 현재 보이는 섹션 감지 → 좌측 PDF 자동 페이지 이동
5. 좌측 PDF 페이지 변경 시 → 우측 해당 섹션으로 스크롤 (역방향 동기화)

**미번역 페이지 처리**:
- 온디맨드 번역 모델이므로 일부만 번역된 상태가 자연스러움
- 플레이스홀더에서 바로 번역 트리거 가능 → 완료 시 해당 섹션만 갱신
- 전체 번역 버튼도 별도 제공 (순차 자동 번역)

**스크롤 동기화 (좌측 PDF ↔ 우측 연속 스크롤)**:
- 기존 비율 기반 동기화 대신, **페이지 경계 기반** 동기화
- 우측에서 `data-page="N"` 섹션이 뷰포트 중앙에 오면 좌측 `goToPage(N)` 호출
- 좌측 페이지 변경 시 우측 `scrollIntoView({ behavior: 'smooth' })` 대응 섹션으로 이동

#### DocLayout-YOLO 컬럼 감지 폴백 — 구현 설계

**배경**: PyMuPDF4LLM의 `column_boxes()`는 텍스트 블록 좌표 기반으로 컬럼을 감지한다.
대부분의 2컬럼 논문에서 정상 동작하나, 텍스트 스트림이 행 단위(좌→우 교차)로 저장된
특수 PDF에서는 블록이 전체 페이지 폭으로 합쳐져 컬럼 분리에 실패한다 (0개 반환).

**검증 결과** (`8_Error.pdf`):
- `column_boxes()` → 0개 반환 (실패)
- 동일 문서 `1_AIR-BENCH.pdf`, `7_Error.pdf` 등 → 정상 분리
- 텍스트 모드의 DocLayout-YOLO (`text_translator.py`)는 이미지 기반이라 정상 처리

**폴백 전략**:
```
md_extractor.py extract_page() 호출 시:
  │
  ├─ column_boxes() 결과 > 0개 → 기존 PyMuPDF4LLM 추출 (변경 없음)
  │   └─ 99% 문서: 추가 비용 0, 기존 품질 그대로
  │
  └─ column_boxes() 결과 = 0개 (특수 PDF)
      └─ DocLayout-YOLO 영역 감지 → 영역별 clip 추출 → Markdown 조립
         └─ text_translator.py의 _detect_layout_yolo() 재활용
         └─ 퍼포먼스: 첫 호출 ~2초(모델 로드), 이후 ~300ms/페이지
```

**정상 문서 영향**: `len(column_boxes) > 0` 체크 1회 추가만. 퍼포먼스/품질 영향 없음.

**텍스트 모드 제거 계획**:
이 폴백이 검증되면 텍스트 번역 모드의 존재 이유가 사라진다.
웹 뷰가 PDF 모드의 유일한 우회 경로가 되며, 엔진 토글을 2종(PDF | 웹 뷰)으로 축소한다.
- 텍스트 모드 UI 제거 (엔진 토글에서 버튼 삭제)
- `text_translator.py` 코드는 보존하되 비활성화 (참조용)
- Phase 4a 폴백 검증 완료 후 Phase 5(리네이밍)에서 함께 정리

### Phase 5: UI 리네이밍 + 텍스트 모드 정리 — 완료

> **순서 변경 근거 (2026-03-22)**:
> Phase 4a에서 YOLO 컬럼 폴백이 완료되어 텍스트 모드의 존재 이유가 사라짐.
> 텍스트 모드를 먼저 제거하면 엔진 2종(PDF/웹뷰)으로 줄어,
> 이후 4b~4d의 코드 분기·테스트 매트릭스가 절반으로 감소.

- ✅ 텍스트 번역 모드 UI 제거 (엔진 토글 2종으로 축소: PDF | 웹 뷰)
- ✅ `text_translator.py` 비활성화 (코드 보존, 참조용)
- ✅ YOLO 폴백 함수 `md_extractor.py`로 이관 (`_detect_layout_yolo` 및 의존 함수 7개)
- ✅ 백엔드 정리: API 4개 엔드포인트, 서비스 함수 4개, config 키 5개, settings 매핑 5개, 관리자 설정 서브탭 1개 제거
- ✅ 프론트엔드 정리: 변수 3개, 함수 3개, 분기 12개소, 폴링 코드 제거
- ✅ 런처 카드 → "Notebook" + "개인 문서함 · PDF 번역 · 지식 관리"
- ✅ 헤더 타이틀 → "Notebook", HTML `<title>` → "Notebook — Smart Document Platform"
- ✅ 시스템 스위처 드롭다운 → "Notebook"
- ✅ 기존 기능 회귀 테스트 (PDF 번역, 웹뷰 번역, 카드 상태, 폴더, 폰트 조절 정상)
- ⬜ 카드 목록 메모 수 표시 → 백엔드 annotation count 확장 필요, 별도 작업으로 분리

> 기존 `text_translated.pdf` 데이터는 디스크에 보존, `meta.json`의 `text_translate` 키도 보존.
> UI에서만 노출 제거되어 하위 호환 문제 없음.

### Phase 4b~4d: Plan-18 완료 후 진행

> **레이아웃 재설계 선행 결정 (2026-03-23)**:
> Plan-18(Notebook 뷰어 레이아웃 재설계 — 아이콘 레일 + 슬라이드 패널)을 먼저 완료한 후,
> 아래 항목들을 새 레이아웃 위에서 구현한다.
> 기존 레이아웃에서 만들고 다시 옮기는 이중 작업을 방지하기 위함.
> 상세: `workbench/plans/18-notebook-viewer-redesign.md`

**Phase 4b: 검색 + 다운로드 확장**
- ⬜ 검색 결과 원문/번역 구분 UI 표시
- ⬜ ZIP 다운로드 (MD + 이미지 assets 포함)

**Phase 4c: 편집기**
- ⬜ EasyMDE 번들 + 웹뷰 패널 내 편집 모드
- ⬜ 편집 저장 API + marked.js 즉시 재렌더링 + `full_translated.md` 재병합

**Phase 4d: 고급 기능**
- ⬜ 클릭 네비게이션 (page_boxes 데이터 저장됨, 원문↔번역 블록 매핑)
- ⬜ 관리자 설정 GUI (웹 뷰 추출 설정 — 섹션 8 참조)

**별도 리팩토링 (기능 안정화 후):**
- ~~translator.js 전략 객체 패턴 분리~~ → 엔진 2종 축소 후 불필요 (Phase 5 완료 시 재평가)
- 번역 속도 최적화 (블록 병렬 호출)
- page-header/footer 텍스트 제거 옵션

---

## 8. 관리자 설정 (Admin Settings)

### 8.1 설정 키 및 기본값

```python
# config.py 추가 항목 — 접두사 TRANSLATOR_WEB_ (기존 _TEXT_ 패턴과 일관)
TRANSLATOR_WEB_TABLE_MODE = "extract"          # "extract" | "image" | "off"
TRANSLATOR_WEB_FORMULA_MODE = "image"          # "latex" | "image" | "off"
TRANSLATOR_WEB_IMAGE_DPI = 150                 # 추출 이미지 해상도 (72~300)
TRANSLATOR_WEB_AUTO_SUMMARY = False            # 번역 완료 시 자동 요약 생성
TRANSLATOR_WEB_TABLE_STRATEGY = "lines_strict" # PyMuPDF 표 감지 전략
TRANSLATOR_WEB_DEBUG = False                   # 디버그: 추출 중간 결과 파일 저장
```

> `_WEB_` 접두사 사용 — 기존 `_TEXT_`(텍스트 엔진) 패턴과 일관.
> `admin-settings.js` 스키마에서 `translator` 그룹 내 서브탭으로 추가 (기존 패턴 `admin-settings.js:251~362`).

### 8.2 설정 UI 설계

```
┌─ 웹 뷰 추출 설정 ──────────────────────────────────────────┐
│                                                            │
│  표 추출 모드        [구조 추출 ▾]  ⓘ                       │
│  수식 추출 모드       [이미지만 ▾]  ⓘ                       │
│  이미지 해상도 (DPI)  ───●──────── 150  ⓘ                  │
│  표 감지 전략         [lines_strict ▾]  ⓘ                   │
│  ☐ 번역 완료 시 자동 요약 생성  ⓘ                           │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

`components.css` 클래스(`.form-select`, `.form-range`, `.tooltip-icon`), `settings.json` 저장, `apply_to_config()` 적용 — 기존 패턴 그대로.

---

## 9. 착수 순서 및 예상 공수

> **순서 조정 (2026-03-22)**: Phase 5를 4b 앞으로 이동. 텍스트 모드 제거를 먼저 하여
> 이후 작업의 코드 분기·테스트 복잡도를 줄임. 4c/4d는 실사용 피드백 후 선택적 진행.

| 순서 | Phase | 내용 | 예상 공수 | 상태 |
|:----:|:-----:|------|:--------:|:----:|
| 1 | 1 | 추출 파이프라인 (PyMuPDF4LLM + 사전 검증) | 2~3일 | ✅ |
| 2 | 2 | 번역 파이프라인 (블록 번역 + 표 셀 + 일괄 최적화) | 3~4일 | ✅ |
| 3 | 3 | 프론트엔드 (웹 뷰 + API + Markdown 렌더링) | 5~6일 | ✅ |
| 4 | 3+ | 사용자 피드백 + 품질 개선 (이미지/표/수식/스타일) | — | ✅ |
| 5 | 4a | 웹 뷰 읽기 경험 (전체 연속 스크롤 + 싱글/듀얼 + 다운로드) | 2~3일 | ✅ |
| 6 | 5 | UI 리네이밍 + 텍스트 모드 정리 (엔진 2종 축소) | 1일 | ✅ |
| — | 4b~4d | 검색/편집/고급 기능 → **Plan-18 완료 후 진행** | — | 보류 |

**핵심 완결 (Phase 5 + 4b)**: ~2일 — 텍스트 모드 정리 + 리네이밍 + 검색 확장으로 **Notebook 핵심 워크플로우 완결**
**전체 합계 (4c/4d 포함)**: ~5.5일 — 편집기·썸네일은 실사용 피드백 확인 후

---

## 10. 향후 확장 (Phase 1~5 완료 후 별도 계획)

실사용 피드백을 수집한 후, 아래 기능들을 별도 계획으로 진행:

| 기능 | 난이도 | 새 라이브러리 | 비고 |
|------|:------:|:----------:|------|
| 자동 요약 + 키워드 추출 | 하 | 없음 | Phase 2에서 기반 구현, 여기서는 UI/UX 보강 |
| 관련 문서 자동 추천 | 하 | 없음 | bge-m3 임베딩 + 용어집 공유도 |
| 용어 기반 자동 연결 | 하 | 없음 | marked.js 렌더링 후 DOM 키워드 매칭 |
| 문서 타임라인 | 하 | 없음 | frontmatter 날짜 기반, 순수 CSS+JS |
| 개인 문서 AI 챗봇 | 중 | 없음 (Explorer 재활용) | 인덱스 격리 구조 결정 필요 |
| 클러스터 시각화 | 중 | D3.js (~250KB) + UMAP | ROI 평가 후 |

> 이 기능들은 기존 데이터(임베딩, 용어집, frontmatter, Markdown)를 활용하므로 Phase 1~5가 기반.
> D3.js/UMAP은 폐쇄망 배포 부담이 있으므로 실사용 피드백 후 판단.

---

## 11. 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| PyMuPDF4LLM 표 추출 정확도 | 복잡한 병합 표에서 깨짐 | 이미지 백업 + Ollama 2차 + 관리자 모드 전환 |
| PyMuPDF4LLM bbox 미제공 | 클릭 네비게이션 불가 | Phase 1 사전 검증, 불가 시 네비게이션 제외 |
| 스캔 PDF | 텍스트 추출 불가 | OCR 모드 또는 대상 제외 |
| Markdown 표 구문 보존 번역 | 구현 복잡도 | Phase 2 공수 3~4일로 반영 |
| ~~translator.js 3종 분기~~ | ~~유지보수성 악화~~ | Phase 5에서 엔진 2종 축소 후 해소 (if/else 관리 가능) |
| EasyMDE CSS 충돌 | 다크모드 깨짐 | Phase 4에서 테마 오버라이드 검증 |
| Markdown 렌더링 보안 | XSS 가능성 | DOMPurify 필수 적용 |
| Pix2Text 수식 정확도 | 86% (복잡 수식 한계) | 이미지 백업 상시 보존, 관리자 모드 전환 |
| 검색 인덱스 크기 2배 | 대량 문서 시 성능 | 현 규모(수백 문서)에서는 문제 없음 |
| PyMuPDF 버전 업그레이드 | pymupdf4llm이 PyMuPDF 1.27.2 요구, pdf2zh-next는 `<1.25.3` 요구 | Phase 1에서 1.27.2로 업그레이드 완료, 기존 PDF/텍스트 번역 정상 동작 확인. 문제 발생 시 `pymupdf==1.25.2` 핀 필요 |

---

## 12. 참고

### 핵심 라이브러리/도구

| 자료 | 용도 | 크기 |
|------|------|------|
| [PyMuPDF4LLM](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/) | PDF→Markdown 추출 엔진 | pip (순수 Python) |
| [marked.js](https://marked.js.org/) | Markdown→HTML 렌더링 | ~40KB |
| [DOMPurify](https://github.com/cure53/DOMPurify) | XSS 방어 | ~15KB |
| [EasyMDE](https://github.com/Ionaru/easy-markdown-editor) | Markdown 편집기 | ~400KB (CodeMirror 포함) |
| [KaTeX](https://katex.org/) | LaTeX 수식 렌더링 | ~300KB |
| [Pix2Text](https://github.com/breezedeus/Pix2Text) | 수식→LaTeX 변환 | ~200MB |

### 프로젝트 내부 문서/코드

| 문서 | 위치 | 관계 |
|------|------|------|
| Plan 16 (완료) | `workbench/plans/done-16-translator-quality-enhancement.md` | 선행 (HiDPI, 용어집, 다운로드) |
| 플랫폼 비전 | `docs/09-PLATFORM-VISION.md` | 지식 플랫폼 로드맵 |
| translator.js | `js/translator.js` (~2889줄) | 프론트엔드 핵심, `updateRightPanel()` 545행~ |
| translator_service.py | `backend/services/translator_service.py` (~1404줄) | 검색 인덱스, page_status, annotations |
| text_translator.py | `backend/services/text_translator.py` (~569줄) | Ollama 호출 패턴, 블록 번역 참조 |
| config.py | `backend/config.py` (63~108행) | `TRANSLATOR_*` 설정 키 패턴 |
| admin-settings.js | `js/admin-settings.js` (251~362행) | 설정 스키마 패턴 |
| glossary 모달 | `translator.html` (226~257행) | 모달 UI 패턴 참조 |
