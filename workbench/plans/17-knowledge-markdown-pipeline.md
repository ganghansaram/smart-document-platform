# Plan 17: Library — 개인 지식 저장소 구축

> 작성일: 2026-03-19
> 최종 갱신: 2026-03-19
> 상태: 설계 중
> 선행: Plan 16 완료 (Phase 1~4)

---

## 1. 목적

Translator 시스템을 **Library(개인 지식 저장소)**로 리네이밍·확장한다.
PDF 문서를 Markdown으로 추출·번역·저장하여 검색·편집·AI 활용이 가능한 **개인 지식 자산**을 구축하고,
문서 간 관계를 AI가 자동으로 연결하여 **사용자 노력 없는 지식 관리**를 실현한다.

## 2. 배경

### 2.1 시스템 리네이밍: Translator → Library

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

**번역은 기능 중 하나**이지, 시스템의 정체성이 아니다. "Library"로 리네이밍하면 번역 안 한 문서를 보관·마킹·메모하는 것도 자연스러워진다.

### 2.2 리네이밍 범위 — 최소 변경 원칙

**사용자가 보는 이름만 바꾸고, 개발자가 보는 구조는 건드리지 않는다.**

| 변경 | 내용 |
|------|------|
| ✅ 파일명 | `translator.html` → `library.html`, `translator.css` → `library.css`, `translator.js` → `library.js` |
| ✅ UI 텍스트 | 런처 카드 이름/설명, 헤더 타이틀, HTML `<title>` |
| ❌ API 경로 | `/api/translator/*` 유지 (사용자가 안 봄, 변경 시 마이그레이션 필요) |
| ❌ 데이터 경로 | `data/translator/` 유지 (기존 데이터 호환) |
| ❌ 디렉토리 구조 | 플랫 구조 유지 (모놀리식 HTML + 빌드 없음 원칙) |

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
| 데이터 크기 | 원본 유지 | 원본+HTML | **원본+MD (경량)** |

> Explorer는 Word→HTML 유지 (복잡한 서식: 병합 표, MathML 수식, 이미지 크기 제어 필요).
> Library는 PDF→Markdown (번역 결과의 편집·활용·지식화가 목적).

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
- `pymupdf4llm`은 `pip install pymupdf4llm`만으로 설치 (PyMuPDF 순수 Python 래퍼)
- 우리가 이미 PyMuPDF 1.25.2를 사용 중 — 새 바이너리/모델 불필요
- `to_markdown()` 한 번의 호출로 텍스트+표+이미지+읽기순서 일괄 처리
- 폐쇄망에서 `.whl` 파일 하나 추가로 완료

### 3.2 표 처리 전략: 이중 접근

기술문서에서 표는 핵심 데이터다. 검색·복사·RAG에서 활용되려면 구조화된 텍스트여야 한다.

| 단계 | 처리 | 결과 |
|------|------|------|
| **1차: PyMuPDF 구조 추출** | `find_tables()` → 셀 데이터 추출 | Markdown 테이블 |
| **2차: 추출 실패 시** | 해당 영역 pixmap 캡처 → Ollama에 이미지 전달 → "이 표를 Markdown으로 변환해줘" | Markdown 테이블 (LLM 생성) |
| **백업: 어떤 경우든** | 원본 영역 이미지도 함께 저장 | 원본 대조용 이미지 |

```markdown
<!-- 추출 성공 시 결과 예시 -->
| 항목 | 인장강도 (MPa) | 연신율 (%) |
|------|:-------------:|:---------:|
| Ti-6Al-4V | 950 | 14 |
| Inconel 718 | 1380 | 12 |

<details><summary>원본 표 이미지</summary>

![Table](assets/table_0.png)
</details>
```

관리자 설정 `table_mode`로 동작 제어 (섹션 9 참조).

### 3.3 이미지 처리

| 유형 | 처리 | Markdown 표현 |
|------|------|-------------|
| 그림 (figure) | PyMuPDF4LLM `write_images=True` → PNG 추출 | `![Figure](assets/fig_0.png)` |
| 차트/그래프 | 이미지 추출 | `![Chart](assets/chart_0.png)` |

### 3.4 수식 처리: 관리자 설정 기반

PDF의 수식은 Word(OMML→MathML)와 달리 **구조 정보 없이 렌더링된 이미지**로 존재한다.
텍스트(LaTeX)로 복원하려면 수식 인식 AI 모델이 필요하다.

**업계 오픈소스 수식 인식 모델 현황 (2025~2026):**

| 모델 | 정확도 (렌더링 성공률) | 모델 크기 | 오프라인 |
|------|:--------------------:|:---------:|:--------:|
| UniMERNet | 97.6% | ~2GB | ✅ |
| **Pix2Text** | **86.2%** | **~200MB** | ✅ |
| TexTeller | ~93% | ~500MB | ✅ |
| pix2tex | 86.2% | ~150MB | ✅ |

**경량 후보: Pix2Text (~200MB)** — Mathpix 오픈소스 대안, TrOCR 기반, 80개 언어, 폐쇄망 설치 현실적.

관리자 설정 `formula_mode`로 동작 제어:

| 모드 | 동작 | 모델 필요 |
|------|------|:---------:|
| `latex` | Pix2Text로 LaTeX 변환 시도 → 실패 시 이미지 백업 | ✅ |
| `image` | 수식 영역 이미지 캡처만 (기본값) | ❌ |
| `off` | 수식 영역 무시 | ❌ |

### 3.5 번역 전략

Markdown 추출 후 번역은 **블록 단위**로 수행:

```
원문 Markdown → 블록 분리 (heading, paragraph, table, list, ...) → 블록별 Ollama 번역 → 번역 Markdown 조합
```

| 블록 유형 | 번역 방식 |
|----------|----------|
| 제목 (`## ...`) | 개별 번역 |
| 본문 단락 | 개별 번역 (긴 단락은 분할) |
| 표 셀 데이터 | 셀 텍스트 일괄 번역 (표 구조 유지) |
| 리스트 항목 | 항목 그룹 일괄 번역 |
| 이미지 캡션 | 개별 번역 |
| 이미지/수식 | 번역 대상 아님 (그대로 유지) |

기존 용어집(`glossary.json`)도 동일하게 프롬프트 주입 방식으로 적용.

### 3.6 브라우저 렌더링

| 용도 | 라이브러리 | 크기 | 비고 |
|------|-----------|------|------|
| MD→HTML 렌더링 | **marked.js** | ~40KB | GFM 지원, 단일 파일 |
| XSS 방어 | **DOMPurify** | ~15KB | marked.js 출력 새니타이징 |
| LaTeX 렌더링 | **KaTeX** | ~300KB | `formula_mode=latex` 시에만 로드 |
| Markdown 편집 | **EasyMDE** | ~140KB | CodeMirror 기반, 분할 모드, autosave |

모든 라이브러리는 `js/lib/`에 번들 (PDF.js, Monaco와 동일 패턴). 폐쇄망 완전 호환.

---

## 4. 데이터 관리 설계

### 4.1 현재 검색 구조 (유지)

현재 시스템은 업로드 시 PyMuPDF `get_text()`로 원문 텍스트를 추출하여 JSON 검색 인덱스를 구축한다:

```
_search_index.json (유저별, 기존)
{
  "doc_id": {
    "title": "문서 제목",
    "pages": { "1": "페이지1 원문 텍스트", "2": "..." }
  }
}
```

이 구조를 **그대로 유지**하고, 웹 뷰 번역 Markdown 텍스트를 검색 인덱스에 **추가**한다.
원문을 별도 Markdown으로 생성할 필요 없음 — 원문 검색은 기존 인덱스로 충분, 원문 열람은 PDF 뷰어로 충분.

### 4.2 저장 구조

```
data/translator/{username}/{doc_id}/
├── original.pdf                    ← 원본 (기존)
├── meta.json                       ← 문서 메타데이터 (기존)
├── _search_index.json              ← 원문 텍스트 검색 인덱스 (기존)
├── pages/{N}/
│   ├── translated.pdf              ← PDF 엔진 결과 (기존, 유지)
│   ├── text_translated.pdf         ← 텍스트 엔진 결과 (기존, 유지)
│   ├── text_mapping.json           ← 텍스트 엔진 매핑 (기존, 유지)
│   ├── translated.md               ← 신규: 웹 뷰 번역 Markdown
│   └── assets/                     ← 신규: 추출된 이미지/표
│       ├── fig_0.png
│       ├── table_0.png
│       └── formula_0.png
└── full_translated.md              ← 신규: 전체 번역 병합 (번역된 페이지만)
```

> `source.md`, `full_source.md` 제거 — 원문은 PDF 뷰어로 열람하고, 검색은 기존 JSON 인덱스가 담당.

### 4.3 Markdown Frontmatter

`translated.md` 파일에 YAML frontmatter를 포함하여 메타데이터 구조화:

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

본 시스템은 강화학습 기반 자율 회피 알고리즘을 ...
```

**활용**:
- 검색 시 메타데이터 필터링 (모델별, 날짜별, 태그별)
- AI 자동 요약/키워드가 `summary`, `keywords` 필드를 채움
- 지식 그래프 노드 속성
- Obsidian에서 열었을 때 속성 패널 자동 표시

### 4.4 전체 문서 병합

페이지별 웹 뷰 번역이 누적되면 `full_translated.md`로 자동 병합:

```yaml
---
title: "Deep-RACO 소프트웨어 아키텍처 규격서"
pages_translated: [1, 2, 3, 5, 7]
pages_total: 42
last_merged: "2026-03-19T16:00:00"
---
```

이 파일의 활용:
- **검색 확장**: 번역 텍스트를 기존 검색 인덱스에 추가 (원문 + 번역 동시 검색)
- **챗봇 RAG**: 청크 분할 → 벡터 인덱스 → 문서 기반 질의응답
- **자동 요약**: Ollama 요약 프롬프트 입력
- **다운로드**: 전체 번역 Markdown 내보내기

### 4.5 데이터 수명 관리

| 데이터 | 생성 시점 | 갱신 시점 | 삭제 시점 |
|--------|----------|----------|----------|
| `translated.md` | 웹 뷰 번역 완료 시 | 재번역 또는 사용자 편집 시 | 문서 삭제 시 |
| `assets/*.png` | 웹 뷰 번역 시 함께 추출 | 재번역 시 | 문서 삭제 시 |
| `full_translated.md` | 페이지 번역 완료마다 | 추가 번역 또는 편집 시 자동 갱신 | 문서 삭제 시 |
| 검색 인덱스 (번역) | 번역 완료 시 인덱스에 추가 | 재번역/편집 시 갱신 | 문서 삭제 시 |

---

## 5. 프론트엔드 설계

### 5.1 설계 원칙

- **기존 UX 패턴 최대 재활용** — Explorer, 현재 Translator에서 검증된 컴포넌트·레이아웃·동선 사용
- **UX 지침 준수** — `tokens.css` 변수, `components.css` 클래스, `modal.css` 패턴
- **불필요한 UI 제거** — 번역 결과가 없는데 빈 우측 패널을 보여주지 않음

### 5.2 뷰어 레이아웃 — 적응형 싱글/듀얼

현재는 항상 듀얼 패널이지만, Library에서는 **싱글이 기본, 번역 완료 시 듀얼로 자동 확장**.

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
│              │                              │
│              │                         💬   │
└──────────────┴──────────────────────────────┘

상태 3: 웹뷰 번역본 편집 → 팝업 (Explorer Monaco 패턴)
┌──────────────┬──────────────────────────────┐
│  원문 PDF     │  번역 Markdown               │
│      ┌───────┴───────────────────────┐      │
│      │  EasyMDE 편집기 (모달 오버레이)  │      │
│      │  .modal-overlay + .modal-box   │      │
│      │  저장 시 우측 패널 즉시 갱신     │      │
│      └───────────────────────────────┘      │
└──────────────┴──────────────────────────────┘
```

**싱글↔듀얼 전환 조건**:
- 현재 페이지에 번역 결과가 있음 → 듀얼 (자동)
- 번역 결과 없음 → 싱글 (원문 PDF 전체 너비)
- 사용자가 번역 실행 → 완료 시 자동으로 듀얼 전환 (현재 동작과 동일)

**기존 코드 변경 최소화**:
- 현재 우측 패널의 "번역 결과 없음" 상태를 `display: none` 처리 + 좌측 `width: 100%`
- 번역 완료 시 우측 패널 `display: block` + 좌측 `width: 50%` (현재 듀얼 레이아웃)
- 리사이즈 핸들(`.resize-handle`) 기존 로직 그대로 유지

### 5.3 카드 목록 (Home)

리네이밍에 따른 카드 표시 변경:

```
현재:
  [논문A] [번역: 3/10] [열기] [삭제]

변경 후:
  [논문A] [PDF번역: 3/10] [웹뷰: ✓] [메모: 5] [열기]
  [가이드B] [미번역] [웹뷰: ─] [메모: 0] [열기]    ← 번역 안 한 문서도 자연스러움
```

### 5.4 엔진 토글 확장

```
현재: PDF | 텍스트  (2종)
변경: PDF번역 | 텍스트번역 | 웹 뷰  (3종)
```

| 모드 | 좌측 패널 | 우측 패널 (번역 결과 있을 때) | 스크롤 동기화 |
|------|-----------|--------------------------|:----------:|
| PDF번역 | 원문 PDF (PDF.js) | 번역 PDF (pdf2zh) | O |
| 텍스트번역 | 원문 PDF | 번역 PDF (재조립) | O |
| **웹 뷰** | 원문 PDF | **번역 Markdown (marked.js)** | **X** |

> 번역 결과가 없으면 어떤 모드든 싱글 뷰어(원문 PDF 전체 너비).

### 5.5 툴바 — 모드별 동적 버튼

기존 툴바에 웹 뷰 전용 버튼을 **조건부 노출**:

| 버튼 | PDF번역 | 텍스트번역 | 웹 뷰 | 비고 |
|------|:-------:|:---------:|:-----:|------|
| 번역모드 선택 | ✅ | ✅ | ✅ | 기존 |
| 모델 선택 | ✅ | ✅ | ✅ | 기존 |
| 번역 실행 | ✅ | ✅ | ✅ | 기존 |
| 용어집 | ✅ | ✅ | ✅ | 기존 |
| 다운로드 | ✅ | ✅ | ✅ | 기존 (웹 뷰 시 .md 다운로드 추가) |
| **편집** | — | — | **✅** | 웹 뷰 모드 + 번역 결과 있을 때만 노출 |
| 폰트 크기 | ✅ | ✅ | ✅ | 기존 |

### 5.6 편집기 — Explorer 패턴 재활용

웹 뷰 모드에서 [편집] 버튼 클릭 시 **모달 오버레이**로 EasyMDE 편집기를 표시.
Explorer의 Monaco Editor 팝업과 동일한 UX 패턴.

- 모달: `modal.css`의 `.modal-overlay` + `.modal-box` 사용
- 편집기: EasyMDE (분할 모드: 좌=Markdown 편집, 우=미리보기)
- 저장: `.btn-primary` 버튼 → `PUT /api/translator/web-view/{doc_id}/page/{page_num}`
- 저장 완료 시: 모달 닫기 → 우측 패널 `marked.js` 재렌더링 (즉시 반영)
- 취소: `.btn-secondary` 또는 `Esc` 키

### 5.7 클릭 네비게이션 (원문 ↔ 번역)

듀얼 모드(번역 결과 있을 때)에서 **클릭 기반 양방향 탐색**:

- 우측 Markdown 블록 클릭 → 좌측 PDF 해당 영역으로 스크롤 + 박스 하이라이트
- 좌측 PDF 영역 클릭 → 우측 Markdown 해당 블록으로 스크롤 + 배경 플래시
- 기존 마킹 시스템의 `scrollIntoView` + 하이라이트 패턴 재활용

구현: 각 Markdown 블록에 `data-block-id` 속성 → source_rect 좌표와 매핑.

### 5.8 챗봇 연동

Explorer의 기존 패턴을 **그대로** 재활용:
- 우하단 플로팅 아이콘 (`ai-chat.js` 패턴)
- 클릭 시 대화창 슬라이드
- RAG 소스: 현재 열린 문서의 `full_translated.md` (번역 전이면 `full_source.md`)
- 백엔드: Explorer `conversation.py` + `query_rewriter.py` 재활용

### 5.9 좌측 트리 패널

**기존 그대로 유지**. 호버 트리거 + 핀 고정, 폴더 관리, 드래그앤드롭 — 변경 없음.
향후 "지식 맵" 탭을 트리 패널 하단에 추가할 수 있으나, 본 계획 범위에서는 기존 유지.

---

## 6. API 설계

### 6.1 신규 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/translator/web-translate/{doc_id}/page/{page_num}` | 웹 뷰 번역 시작 (추출+번역 일괄) |
| GET | `/api/translator/web-translate/{doc_id}/page/{page_num}/status` | 번역 상태 조회 |
| POST | `/api/translator/web-translate/{doc_id}/page/{page_num}/cancel` | 번역 취소 |
| GET | `/api/translator/web-view/{doc_id}/page/{page_num}` | 페이지 번역 Markdown 서빙 |
| GET | `/api/translator/web-view/{doc_id}/full` | 전체 병합 Markdown 서빙 |
| GET | `/api/translator/web-view/{doc_id}/page/{page_num}/assets/{filename}` | 페이지 이미지 자산 서빙 |
| PUT | `/api/translator/web-view/{doc_id}/page/{page_num}` | Markdown 편집 저장 |

> 기존 PDF/텍스트 번역 API 패턴(translate → status → cancel)과 동일한 구조.
> 추출과 번역을 분리하지 않음 — `web-translate` 한 번의 호출로 추출→번역→저장 연속 실행.

### 6.2 처리 흐름

```
사용자: "웹 뷰" 모드 선택 → 페이지 이동

1. translated.md 존재?
   YES → 3으로
   NO  → 2. 번역 버튼 표시 (기존 번역 버튼과 동일 위치)
         클릭 시:
           a. PyMuPDF4LLM으로 해당 페이지 추출 (텍스트+표+이미지 → Markdown)
           b. 추출된 Markdown을 블록 단위 Ollama 번역
           c. translated.md + assets/ 저장
           → 3으로

3. translated.md를 API로 전달 → 프론트에서 marked.js 렌더링 → 듀얼 패널 자동 전환
```

> 웹 뷰 모드에서는 추출(PyMuPDF4LLM)과 번역(Ollama)이 **한 번의 번역 요청**으로 연속 실행된다.
> 원문 Markdown은 별도 파일로 저장하지 않음 — 번역 과정의 중간 데이터일 뿐.

---

## 7. 실행 계획

### Phase 0: 리네이밍 (Translator → Library)

- [ ] `translator.html` → `library.html` (파일명 변경)
- [ ] `css/translator.css` → `css/library.css`
- [ ] `js/translator.js` → `js/library.js`
- [ ] 런처 카드 이름/설명 변경 (`launcher.html`)
- [ ] 헤더 타이틀 변경
- [ ] HTML `<title>` 변경
- [ ] 내부 JS 참조 경로 수정 (CSS link, script src)
- [ ] 기존 기능 회귀 테스트 (번역, 마킹, 폴더, 검색 등)
- [ ] 예상 공수: 0.5일

> API 경로(`/api/translator/*`), 데이터 경로(`data/translator/`), 백엔드 모듈명은 변경하지 않는다.

### Phase 1: 추출 파이프라인 (PyMuPDF4LLM)

- [ ] `pymupdf4llm` 패키지 설치 및 폐쇄망 whl 준비
- [ ] `services/md_extractor.py` — PDF→Markdown 추출 모듈
  - `extract_page(pdf_path, page_num) → (markdown_text, assets_list)`
  - 표 추출: `table_mode` 설정에 따라 구조 추출 / 이미지 / off 분기
  - 수식 추출: `formula_mode` 설정에 따라 LaTeX / 이미지 / off 분기
  - 이미지 추출: `write_images=True`, DPI 설정 반영
  - 반환값은 번역 파이프라인(Phase 2)의 입력으로 사용
  - 별도 파일 저장 없음 (중간 데이터, 번역 후 `translated.md`만 저장)
- [ ] 다양한 PDF 유형으로 추출 품질 검증
  - 논문 (2단, 수식)
  - 스팩 (표 다수, 병합 셀)
  - 매뉴얼 (이미지 다수)
  - 스캔 PDF (OCR 필요 여부 확인)
- [ ] 관리자 설정 키 추가 (`config.py`, `settings.json`)
- [ ] 예상 공수: 2~3일

### Phase 2: 번역 파이프라인

- [ ] `services/md_translator.py` — Markdown 블록 번역 모듈
  - Markdown 파싱 → 블록 분리 (heading, paragraph, table, list, image)
  - 블록별 Ollama 번역 (이미지/수식은 스킵)
  - 표 셀 번역 (Markdown 표 구조 유지)
  - 용어집 적용 (기존 `glossary.json` 재활용)
  - translated.md 저장 + frontmatter 갱신
- [ ] `full_translated.md` 자동 병합 로직
- [ ] 자동 요약 + 키워드 추출 (`auto_summary` 설정 시)
- [ ] 예상 공수: 2~3일

### Phase 3: API + 프론트엔드 (웹 뷰)

- [ ] `api/translator.py`에 웹 뷰 엔드포인트 추가 (6.1 참조)
- [ ] `marked.js` + `DOMPurify` 번들 (`js/lib/`)
- [ ] 엔진 토글 3종 확장 (`pdf | text | web`)
- [ ] 싱글/듀얼 적응형 레이아웃 (번역 결과 유무에 따라 자동 전환)
- [ ] 우측 패널: 웹 뷰 모드 Markdown 렌더링
- [ ] Markdown 스타일시트 (tokens.css 변수 활용, 다크모드)
- [ ] 클릭 네비게이션 (원문 PDF ↔ 번역 Markdown, 듀얼 시)
- [ ] 웹 뷰 전용 툴바 버튼 조건부 노출 (편집, MD 다운로드)
- [ ] 관리자 설정 GUI 추가 (섹션 9)
- [ ] 예상 공수: 3~4일

### Phase 4: 편집 + 다운로드 + 검색 통합

- [ ] EasyMDE 번들 (`js/lib/easymde/`)
- [ ] 편집 모달 (`.modal-overlay` + `.modal-box`, Explorer Monaco 팝업 패턴)
- [ ] 편집 저장 API (`PUT /api/translator/web-view/{doc_id}/page/{page_num}`)
- [ ] 저장 시 우측 패널 marked.js 즉시 재렌더링 + `full_translated.md` 자동 재병합
- [ ] Markdown 다운로드 (.md 단일 파일)
- [ ] 전체 병합 Markdown 다운로드
- [ ] 이미지 포함 ZIP 다운로드 (Obsidian vault 호환)
- [ ] 검색 인덱스에 Markdown 텍스트 포함 (기존 검색 확장)
- [ ] 예상 공수: 2~3일

### Phase 5: AI 지식 기능

- [ ] 자동 요약 + 키워드 추출 (번역 완료 콜백)
- [ ] 관련 문서 자동 추천 (임베딩 유사도 + 키워드 + 용어집)
- [ ] 용어 기반 자동 연결 (Markdown 렌더링 시 용어 하이라이트)
- [ ] 문서 타임라인 (frontmatter 날짜 기반)
- [ ] 카드 목록에 요약 미리보기 표시
- [ ] 예상 공수: 3~4일

### Phase 6: 시각화 + 챗봇

- [ ] 문서 클러스터 시각화 (D3.js force graph + UMAP)
- [ ] 개인 문서 AI 챗봇 (Explorer RAG 파이프라인 재활용)
- [ ] 좌측 트리 패널에 "지식 맵" 탭 추가
- [ ] 챗봇 슬라이드 패널 (Explorer `ai-chat.js` 패턴)
- [ ] 예상 공수: 4~5일

---

## 8. 지식 기능 상세 설계

Obsidian이 사용자 수동 작업에 의존하는 것과 달리,
**AI가 자동으로 처리**하여 사용자 노력을 최소화하는 것이 차별점이다.

### 8.1 자동 요약 + 키워드 추출

문서 업로드 또는 번역 완료 시, Ollama가 자동으로 요약과 키워드를 생성하여 frontmatter에 저장.
사용자 노력: **없음**.

```yaml
# frontmatter에 자동 추가
summary: "본 논문은 Ti-6Al-4V 합금의 적층제조 시 잔류응력 제어 방법을 제안한다..."
keywords: [적층제조, 잔류응력, Ti-6Al-4V, 열처리, 시뮬레이션]
```

**구현**: 번역 완료 콜백 → `full_translated.md` → Ollama 요약 프롬프트 → frontmatter 갱신.

### 8.2 관련 문서 자동 추천

문서 열람 시 하단에 관련 문서를 자동 표시. **시스템이 유사도를 계산하여 자동 연결.**

```
📎 관련 문서
├── [0.92] Ti-6Al-4V 적층제조 표준 시험법 (키워드 4개 일치)
├── [0.87] 잔류응력 측정 가이드라인 (임베딩 유사도)
└── [0.81] 열처리 공정 규격서 (용어집 3개 공유)
```

**구현**: 유사도 = 임베딩 코사인(70%) + 키워드 겹침(20%) + 용어집 공유(10%). 문서 수백 개 수준이므로 브루트포스 가능.

### 8.3 용어 기반 자동 연결

Markdown 렌더링 시 용어집 키워드를 자동 하이라이트. 클릭하면 같은 용어가 등장하는 다른 문서 목록 팝업.

**구현**: marked.js 렌더링 후 DOM에서 `glossary.json` 키워드 매칭 → `<span class="term-link">` 래핑.

### 8.4 문서 클러스터 시각화

임베딩 벡터를 UMAP으로 2D 축소 → D3.js force graph.

```
  [적층제조 논문들]        [재료 물성 스팩들]
    ●──●                    ●──●
    │  │                    │
    ●──●──●                 ●──●
              [피로 시험 가이드들]
                ●──●──●
```

**구현**: bge-m3 임베딩 (기존) → UMAP 2D → D3.js force graph (순수 JS). 좌측 트리 패널 하단 "지식 맵" 탭.

### 8.5 문서 타임라인

frontmatter 날짜로 시간순 시각화. 순수 CSS + JS (외부 라이브러리 불필요).

### 8.6 Markdown 편집기

**EasyMDE 채택** — CodeMirror 기반, 분할(편집+미리보기) 모드, autosave, GFM 표 삽입 툴바.
Explorer에 Monaco를 번들한 것과 동일 패턴으로 `js/lib/easymde/`에 배치.

```
웹 뷰 모드에서 "편집" 버튼 클릭
  → 모달 오버레이(.modal-overlay + .modal-box)로 EasyMDE 표시
     (Explorer Monaco 편집기 팝업과 동일 UX 패턴)
  → 사용자가 Markdown 수정 (오역 교정, 메모 추가 등)
  → "저장" → translated.md 갱신 + 모달 닫기 + 우측 패널 즉시 재렌더링
  → full_translated.md 자동 재병합
```

### 8.7 개인 문서 AI 챗봇

Explorer RAG 파이프라인(FAISS + bge-m3 + 리랭커 + 멀티턴)을 재활용.
`full_translated.md` → 청크 분할 → 벡터 인덱스 → 챗봇 UI (Explorer `ai-chat.js` 패턴).

---

## 9. 관리자 설정 (Admin Settings)

추출 파이프라인의 동작을 관리자 설정 GUI에서 제어한다.
기존 `admin-settings.js`의 탭 패턴을 따르며, "Library" 탭 내 **"웹 뷰 추출"** 섹션으로 추가.

### 9.1 설정 키 및 기본값

```python
# config.py 추가 항목
TRANSLATOR_MD_TABLE_MODE = "extract"          # "extract" | "image" | "off"
TRANSLATOR_MD_FORMULA_MODE = "image"          # "latex" | "image" | "off"
TRANSLATOR_MD_IMAGE_DPI = 150                 # 추출 이미지 해상도 (72~300)
TRANSLATOR_MD_AUTO_SUMMARY = False            # 번역 완료 시 자동 요약 생성
TRANSLATOR_MD_TABLE_STRATEGY = "lines_strict" # PyMuPDF 표 감지 전략
```

### 9.2 설정 UI 설계

기존 관리자 설정 GUI(`admin-settings.js`)의 패턴:
- `components.css`의 `.form-select`, `.form-range`, `.btn` 클래스 사용
- 각 항목에 `.tooltip-icon` (`data-tooltip="설명"`) 배치
- `settings.json`에 저장 → 백엔드 `apply_to_config()`로 즉시 반영

```
┌─ 웹 뷰 추출 설정 ──────────────────────────────────────────┐
│                                                            │
│  표 추출 모드        [구조 추출 ▾]  ⓘ                       │
│                                                            │
│  수식 추출 모드       [이미지만 ▾]  ⓘ                       │
│                                                            │
│  이미지 해상도 (DPI)  ───●──────── 150  ⓘ                  │
│                       72        300                        │
│                                                            │
│  표 감지 전략         [lines_strict ▾]  ⓘ                   │
│                                                            │
│  ☐ 번역 완료 시 자동 요약 생성  ⓘ                           │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 9.3 툴팁 설명문

| 설정 | 툴팁 |
|------|------|
| 표 추출 모드 | "구조 추출: 표 내용을 텍스트로 변환하여 검색/복사 가능. 이미지만: 원본 캡처만 저장." |
| 수식 추출 모드 | "LaTeX 변환: 수식을 텍스트로 변환 (Pix2Text 모델 필요). 이미지만: 수식 영역 캡처." |
| 이미지 해상도 | "추출 이미지 해상도. 높을수록 선명하지만 파일 크기 증가. 기본값 150 DPI." |
| 표 감지 전략 | "lines_strict: 셀 구분선이 명확한 표에 최적. text: 선 없는 표에 사용." |
| 자동 요약 | "번역 완료 시 AI가 문서 요약과 키워드를 자동 생성. Ollama 추가 호출 발생." |

### 9.4 공개 설정 (Public Settings)

| 설정 | 프론트엔드 용도 |
|------|---------------|
| `TRANSLATOR_MD_FORMULA_MODE` | `latex` 모드일 때 KaTeX 렌더러 로드 여부 결정 |
| `TRANSLATOR_MD_AUTO_SUMMARY` | 번역 완료 시 "요약 생성 중..." 상태 표시 여부 |

---

## 10. 착수 순서 및 예상 공수

| Phase | 내용 | 예상 공수 | 누적 |
|:-----:|------|:--------:|:----:|
| 0 | 리네이밍 (Translator → Library) | 0.5일 | 0.5일 |
| 1 | 추출 파이프라인 (PyMuPDF4LLM + 표/수식/이미지) | 2~3일 | 3일 |
| 2 | 번역 파이프라인 (블록 번역 + 자동 요약) | 2~3일 | 6일 |
| 3 | API + 프론트엔드 (웹 뷰 + 관리자 설정) | 3~4일 | 9일 |
| 4 | 편집 + 다운로드 + 검색 통합 | 2~3일 | 12일 |
| 5 | AI 지식 기능 (추천, 연결, 타임라인) | 3~4일 | 15일 |
| 6 | 시각화 + 챗봇 | 4~5일 | 20일 |

**Phase 0~4**: 핵심 파이프라인 (~12일) — 여기까지 완료하면 "Markdown 지식 저장소"로 사용 가능
**Phase 5~6**: 지식 플랫폼 확장 (~8일) — AI 자동화 차별점

---

## 11. 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| PyMuPDF4LLM 표 추출 정확도 | 복잡한 병합 표에서 깨질 수 있음 | 이미지 백업 + Ollama 2차 변환 + 관리자 모드 전환 |
| 스캔 PDF (이미지 기반) | 텍스트 추출 불가 | OCR 모드 (`use_ocr=True`, Tesseract 필요) 또는 대상 제외 |
| 번역 품질 (블록 단위) | 문맥 단절로 번역 부자연스러움 | 인접 블록 요약을 문맥 힌트로 전달 |
| 3종 엔진 UX 복잡도 | 사용자 혼동 | 모드별 명확한 설명 툴팁, 기본값을 웹 뷰로 설정 |
| Markdown 렌더링 보안 | XSS 가능성 | DOMPurify 필수 적용 |
| 리네이밍 회귀 | 파일명 변경 시 참조 누락 | 전수 grep + 기능 회귀 테스트 |
| Pix2Text 수식 정확도 | 복잡한 수식에서 86% | 이미지 백업 상시 보존, 관리자 모드 전환 |

---

## 12. 참고

### 핵심 라이브러리/도구

| 자료 | 용도 | 크기 |
|------|------|------|
| [PyMuPDF4LLM](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/) | PDF→Markdown 추출 엔진 | PyMuPDF 확장 (pip) |
| [marked.js](https://marked.js.org/) | Markdown→HTML 브라우저 렌더링 | ~40KB |
| [DOMPurify](https://github.com/cure53/DOMPurify) | Markdown 렌더링 XSS 방어 | ~15KB |
| [EasyMDE](https://github.com/Ionaru/easy-markdown-editor) | WYSIWYG Markdown 편집기 | ~140KB |
| [KaTeX](https://katex.org/) | LaTeX 수식 렌더링 (formula_mode=latex 시) | ~300KB |
| [Pix2Text](https://github.com/breezedeus/Pix2Text) | 수식→LaTeX 변환 (formula_mode=latex 시) | ~200MB |
| [D3.js](https://d3js.org/) | 클러스터/그래프 시각화 | ~250KB |

### 벤치마크/비교 자료

| 자료 | 용도 |
|------|------|
| [Marker vs MinerU vs MarkItDown](https://jimmysong.io/blog/pdf-to-markdown-open-source-deep-dive/) | PDF→MD 추출 엔진 벤치마크 |
| [MinerU](https://github.com/opendatalab/MinerU) | 향후 고품질 추출 엔진 후보 |
| [PyMuPDF RAG/LLM 가이드](https://artifex.com/blog/rag-llm-and-pdf-conversion-to-markdown-text-with-pymupdf) | 실전 활용 사례 |

### 프로젝트 내부 문서

| 문서 | 위치 | 관계 |
|------|------|------|
| Plan 16 (완료) | `workbench/plans/done-16-translator-quality-enhancement.md` | 선행 (HiDPI, 용어집, 다운로드) |
| 플랫폼 비전 | `docs/09-PLATFORM-VISION.md` | 지식 플랫폼 로드맵 |
| Explorer RAG | `backend/services/` | 챗봇 재활용 (faiss, reranker, conversation) |
| 텍스트 엔진 | `backend/services/text_translator.py` | 기존 파이프라인 (병행 유지) |
| 용어집 | `backend/services/translator_service.py` | glossary.json CRUD |
