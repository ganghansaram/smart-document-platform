# Plan-25: 플랫폼 데이터 아키텍처 로드맵

> **작성일**: 2026-04-05
> **상태**: 설계 논의 (구현 미착수)
> **목적**: PDF 입력 통일 → 서브시스템 간 데이터 통합
> **전략**: Notebook을 참조 구현으로 완성(Plan-26) → Explorer·Verify로 확장
> **선행**: [Plan-26](26-notebook-viewer-pipeline.md) — Notebook 뷰어 + 추출 파이프라인 개선

---

## 1. 현황 진단

### 1.1 데이터 포맷 현황

| 서브시스템 | 입력 | 변환 | 저장 | 열람 |
|-----------|------|------|------|------|
| **Explorer** | DOCX | word_to_html.py → HTML | HTML | innerHTML 렌더 |
| **Notebook** | PDF | PyMuPDF4LLM → MD | MD + JSON | PDF.js + marked.js |
| **Verify** | DOCX/PDF | 텍스트 직접 추출 | — (임시) | HTML 리포트 |

### 1.2 핵심 문제

1. **입력 포맷 불일치** — Explorer는 DOCX, Notebook은 PDF, Verify는 둘 다
2. **파이프라인 분산** — 각 시스템이 독자적 변환 코드 유지
3. **데이터 사일로** — 서브시스템 간 데이터 공유 없음 (재업로드 필요)
4. **MD 추출 품질** — PyMuPDF4LLM의 구조적 한계 (리스트 손실, 헤더 오염 등)

### 1.3 AS-IS 흐름도

```
┌──────────────────────────────────────────────────────┐
│ Explorer                                             │
│  DOCX → word_to_html.py → HTML → innerHTML           │
│                              ├→ html_to_text → JSON  │
│                              └→ 섹션ID 네비게이션     │
│                                   ├→ BM25 + FAISS    │
│                                   └→ RAG 챗봇         │
└──────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────┐
│ Notebook                                             │
│  PDF → PyMuPDF4LLM → MD 저장                         │
│   │                   ├→ marked.js (웹뷰)            │
│   │                   ├→ Ollama (번역)               │
│   ▼                   └→ 검색 인덱스 / 요약 / Q&A     │
│  PDF.js 뷰어 (원본)                                   │
└──────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────┐
│ Verify                                               │
│  DOCX/PDF → 텍스트 직접 추출 → 단락 배열 (임시)       │
│              ├→ 규칙 엔진 (21종)                      │
│              ├→ 유사도 비교                            │
│              └→ diff 비교                             │
└──────────────────────────────────────────────────────┘
  세 시스템이 각각 다른 입력·변환·저장. 데이터 공유 없음.
```

---

## 2. 설계 결정

### D1. PDF 입력 통일 (확정)

> 모든 서브시스템의 입력은 PDF로 통일. 서버 변환 없음.

- 사내 문화에서 DOCX/HWP → PDF 출력 배포가 자연스러운 흐름
- PDF 레이아웃 고정 → "원본과 다르게 보이는" 문제 없음
- 서버에 변환 도구 불필요 (폐쇄망 부담 감소)

### D2. PDF 열람 + MD 인덱싱 이원 구조 (확정)

| 계층 | 포맷 | 역할 |
|------|------|------|
| **프레젠테이션** | PDF | PDF.js 뷰어로 열람. 레이아웃 완벽 보존 |
| **콘텐츠** | Markdown | 검색, RAG, 번역, 검증, 편집 |
| **구조** | JSON | 상태 관리, 페이지 매핑, 관계, 검증 결과 |

### D3. Explorer HTML→PDF 전환 (확정)

기능별 영향 분석 — **포기 기능 없음**:

| 기능 | 현재 (HTML) | 전환 후 (PDF+MD) |
|------|------------|-----------------|
| 문서 열람 | innerHTML | PDF.js 뷰어 (레이아웃 개선) |
| 트리 네비게이션 | 헤딩 ID → scrollTo | MD 헤딩 → 페이지 매핑 → goToPage |
| 검색/챗봇 링크 | element ID | MD 인덱스 → 페이지 배지 (Notebook 검증 완료) |
| 콘텐츠 편집 | Monaco HTML | Monaco MD (Notebook 검증 완료) |
| 용어집/참조 팝업 | DOM 래핑 | 웹뷰 모드(MD 렌더)에서 유지 |
| 검색 하이라이트 | TreeWalker | PDF.js findController |

### D4~D7. 미정 항목

| # | 질문 | 현재 기울기 |
|---|------|-----------|
| D4 | 기존 HTML 웹북 처리 | 원본 DOCX→PDF 재출력 (기존 데이터 소량) |
| D5 | Phase 4 구조 변경 시기 | Author 경험 축적 후 |
| D6 | 서브시스템 간 연동 범위 | Notebook↔Verify 우선 |
| D7 | 추출 엔진 선택 | Phase 0 Step 1 벤치마크로 결정 (롤백 보장) |

---

## 3. 업계 근거

### 3.1 "PDF 열람 + 텍스트 추출" 패턴 채택 사례

| 시스템 | 분야 | 구조 |
|--------|------|------|
| **Paperless-ngx** | 문서관리 (오픈소스) | PDF 저장 + OCR 추출 → 검색 |
| **Google Scholar** | 학술 검색 | PDF 열람 + 추출 텍스트 → 검색/인용 |
| **NotebookLM** | AI 문서 분석 | PDF 업로드 → 추출 → AI Q&A |
| **IETM** | 항공/방산 기술교범 | 구조화 데이터 → 뷰어 + PDF 이중 출력 |

MIL-STD-38784 IETM 설계 원칙 **"열람은 뷰어, 데이터는 구조화 포맷"**과 동일.

### 3.2 PDF→MD 추출 도구 비교

| 도구 | 리스트 | 표 | 헤더/푸터 | 오프라인 | 모델 크기 |
|------|:------:|:--:|:--------:|:--------:|:---------:|
| **PyMuPDF4LLM** (현재) | 빈번 손실 | 보통 | 빈번 오염 | 완전 | 0 MB |
| **Marker** | 드문 손실 | 보통 | 드문 오염 | 완전 | ~2 GB |
| **Docling (IBM)** | 가끔 손실 | 우수 | 드문 오염 | 완전 | ~1.5 GB |
| **pdfplumber** | 해당 없음 | 최우수 | 해당 없음 | 완전 | 0 MB |

---

## 4. TO-BE 데이터 흐름

### 4.0 전체 구조도

```
┌──────────────────────────────────────────────────────────────┐
│                    공통 입력: PDF                              │
│                                                              │
│  PDF 업로드 (DOCX/HWP에서 이미 출력한 것)                      │
│         │                                                    │
│         ├──────────────────────┐                              │
│         ▼                      ▼                             │
│    PDF 원본 저장           PyMuPDF4LLM 추출 + 후처리           │
│    (source/)              (content/)                         │
│         │                      │                             │
│         │                      ▼                             │
│         │               MD + 페이지 매핑 JSON                 │
│         │                      │                             │
│         │         ┌────────────┼────────────┐                │
│         │         ▼            ▼            ▼                │
│         │     검색 인덱스    TOC 생성    벡터 인덱싱            │
│         │     (BM25)      (헤딩+페이지)  (FAISS)              │
│         │         └────────────┴────────────┘                │
│         │                      ▼                             │
│         │              통합 검색 / RAG                        │
└─────────┼────────────────────────────────────────────────────┘
          │
  ┌───────┼────────┬──────────────┬──────────────┐
  ▼       ▼        ▼              ▼              ▼
┌──────┐┌──────┐┌────────┐┌──────────┐┌────────────┐
│열람  ││웹뷰  ││검색/챗봇││검증      ││번역        │
│PDF.js││MD    ││MD기반  ││MD기반    ││MD기반      │
│뷰어  ││렌더  ││RAG     ││규칙엔진  ││Ollama      │
│스크롤││편집  ││페이지  ││점수+이슈 ││페이지별    │
│탐색  ││가능  ││링크    ││리포트    ││온디맨드    │
└──┬───┘└──┬───┘└───┬────┘└────┬─────┘└─────┬──────┘
   │  Explorer      │     Verify        Notebook
   └───────┴────────┘
         공통 PDF.js 뷰어 + 공통 MD 파이프라인
```

### 4.1 서브시스템별 흐름

**Explorer**:
```
PDF 업로드 → source/original.pdf
           → PyMuPDF4LLM + 후처리 → content/extracted.md + page_map.json
           → 인덱싱 (BM25 + FAISS)
  [열람] PDF.js 뷰어 (원본 스크롤)
  [웹뷰] MD → marked.js (용어집, 참조 팝업, 편집)
  [검색] 인덱스 → 결과 → goToPage(N)
  [챗봇] RAG(MD) → 응답 + 페이지 배지
```

**Notebook**:
```
PDF 업로드 → source/original.pdf
           → PyMuPDF4LLM + 후처리 → content/extracted.md (페이지별)
  [열람] PDF.js 뷰어 (좌측)
  [번역] MD 블록 → Ollama → content/translated.md
  [웹뷰] MD → marked.js (우측, 편집 가능)
  [요약] MD → LLM → ai_summary.json
  [Q&A]  MD → RAG → 응답 + 페이지 배지
```

**Verify**:
```
PDF 업로드 (또는 Notebook/Explorer 문서 직접 참조)
           → PyMuPDF4LLM + 후처리 → content/extracted.md
  [검증] MD → 단락 분할 → 규칙 엔진 21종 → 점수 + 이슈
  [비교] MD(A) + MD(B) → jsdiff → 변경점
  [유사도] MD(A) + MD(B) → 문장 매칭 → 리포트
```

### 4.2 공통 모듈

```
PDF.js 뷰어       ← Explorer, Notebook
PyMuPDF4LLM + 후처리 ← 전 시스템
marked.js          ← 전 시스템 웹뷰 렌더
Monaco 에디터      ← Explorer, Notebook
검색 인덱스        ← Explorer, Notebook
RAG 파이프라인     ← Explorer, Notebook
규칙/유사도 엔진   ← Verify, Author
LLM 프로바이더     ← 전 시스템
```

---

## 5. 단계별 로드맵

### 선행: Plan-26 (Notebook 뷰어 + 추출 파이프라인 개선)

> Phase 1 착수 전에 Plan-26을 통해 Notebook에서 연속 스크롤 뷰어와 MD 추출 품질을 먼저 완성한다.
> Notebook에서 검증된 패턴을 Explorer에 적용하는 것이 Phase 1의 핵심.

---

### Phase 1: Explorer PDF 전환

> **목표**: Explorer를 Notebook과 동일한 구조(PDF.js + MD)로 전환

**전환 전후**:
```
현재:  DOCX → word_to_html.py → HTML → innerHTML
전환:  PDF → PDF.js 뷰어 (열람) + PyMuPDF4LLM → MD (검색/AI)
```

**필요 작업**:
- [ ] PDF 업로드 API + 저장 구조 설계
- [ ] PDF.js 뷰어 Explorer 통합 (Notebook 코드 재사용)
- [ ] MD 추출 + 페이지-헤딩 매핑 생성
- [ ] 트리 메뉴: menu.json → 페이지 매핑 기반 네비게이션
- [ ] 검색 인덱스: MD 기반 재구축
- [ ] 챗봇: 페이지 배지 네비게이션 (Notebook 패턴 재사용)
- [ ] 웹뷰 모드: MD→marked.js (용어집/참조 팝업 유지)

**제거 대상**: `word_to_html.py`, `omml_to_mathml.py`, `word_preprocessor.py`, `html_to_text.py`
**재사용 대상**: PDF.js, PyMuPDF4LLM, marked.js, Monaco MD 에디터, 페이지 배지

---

### Phase 2: 서브시스템 간 연동

> **목표**: 재업로드 없이 문서 직접 참조

- **Notebook → Verify**: `full_extracted.md`를 Verify 입력으로 직접 사용
- **Explorer → Verify**: Explorer 문서를 검증 대상으로 선택
- **통합 검색**: Explorer + Notebook 문서 동시 검색, 소스 배지 표시

---

### Phase 3: 문서 관계 그래프

> **목표**: 문서 간 참조·유사·버전 관계를 메타데이터로 관리

- `relations.json` — 관계 유형별 문서 ID 목록
- Verify 교차참조 결과 → 관계 자동 등록
- "유사한 문서 3개" 추천

---

### Phase 4: Document-Centric 통합 (장기)

> **목표**: 물리적 디렉토리 구조를 문서 중심으로 재편

```
data/documents/{user}/{doc}/
  ├── source/original.pdf
  ├── content/extracted.md, translated.md
  ├── metadata/meta.json, relations.json
  ├── verification/results.json
  └── annotations/highlights.json
```

**전제 조건**: Phase 1~3 경험 축적 + Plan-24(Author) 요구사항 구체화 후.

---

## 6. 기존 코드 영향 (Phase 1 실행 시)

### 제거 예상

| 파일 | 역할 |
|------|------|
| `tools/converter/word_to_html.py` | DOCX→HTML 변환 |
| `tools/converter/omml_to_mathml.py` | 수식 변환 |
| `tools/converter/word_preprocessor.py` | COM 전처리 |
| `tools/html_to_text.py` | HTML→plain text |
| `contents/*.html` | 변환된 웹북 HTML |

### 재사용 확대

| 모듈 | 현재 | 전환 후 |
|------|------|--------|
| PDF.js 뷰어 | Notebook 전용 | Explorer + Notebook |
| PyMuPDF4LLM | Notebook 전용 | 전 시스템 |
| marked.js | Notebook 전용 | 전 시스템 |
| Monaco MD 에디터 | Notebook 전용 | Explorer + Notebook |
| 페이지 배지 | Notebook Q&A | Explorer + Notebook |

---

## 7. Plan-24 (Author)와의 관계

| Author 요구 | 이 계획서의 기여 |
|------------|---------------|
| 다중 문서 열람 | Phase 1 PDF.js 뷰어 공유 |
| 문서 간 비교 | Phase 3 관계 그래프 |
| 합성 결과 저장 | MD + JSON 표준 구조 |
| 합성 → 검증 연동 | Phase 2 연동 패턴 재활용 |

**권장**: Phase 0~1을 Author 착수 전에 완료 → 공통 인프라 + 품질 확보.

---

## 참고: 목업

- `workbench/mockups/explorer-pdf-comparison.html` — Explorer 뷰어 3안 비교 (HTML / PDF.js / MD 웹뷰)

---

*Phase별 구체적 구현 스펙은 착수 시 상세화한다.*
