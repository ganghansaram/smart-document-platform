# Reader 시스템 — 설계 문서

논문 PDF 업로드 → 원문 열람 → AI 번역 시스템

---

## 목차

1. [개요](#1-개요)
2. [아키텍처](#2-아키텍처)
3. [화면 구성](#3-화면-구성)
4. [백엔드 API](#4-백엔드-api)
5. [데이터 구조](#5-데이터-구조)
6. [번역 파이프라인](#6-번역-파이프라인)
7. [파일 구조](#7-파일-구조)
8. [설정](#8-설정)
9. [개발 로드맵](#9-개발-로드맵)

---

## 1. 개요

### 목적

- 영문 논문/기술문서 PDF를 업로드하면 원문을 그대로 보면서 한국어 번역을 병렬로 확인
- 에어갭(폐쇄망) 환경에서 동작: 외부 API 없이 로컬 Ollama LLM 사용
- scholar-translator(PDFMathTranslate 포크) 컨셉 참고

### 핵심 특징

| 항목 | 설명 |
|------|------|
| PDF 렌더링 | 좌측 패널에 PDF.js로 원본 그대로 표시 (레이아웃/수식/이미지 보존) |
| 번역 표시 | 우측 패널에 페이지 동기화된 한국어 번역 텍스트 |
| 번역 엔진 | Ollama (로컬 LLM) — 에어갭 호환 |
| 스트리밍 | 업로드/번역 진행률을 NDJSON 스트리밍으로 실시간 표시 |
| 권한 | 업로드: editor 이상 / 열람·번역: viewer 이상 |

---

## 2. 아키텍처

```
┌─────────────────────────────────────────────────┐
│  Browser (reader.html)                          │
│                                                 │
│  ┌──────────────┐   ┌────────────────────────┐  │
│  │  목록 뷰     │   │  뷰어 뷰              │  │
│  │  - 업로드    │   │  ┌─────┐  ┌─────────┐ │  │
│  │  - 문서 카드 │──▶│  │PDF  │  │번역 텍스│ │  │
│  │              │   │  │.js  │  │트 (페이 │ │  │
│  │              │   │  │원본 │  │지 동기화)│ │  │
│  │              │   │  └─────┘  └─────────┘ │  │
│  └──────────────┘   └────────────────────────┘  │
│         │                      │                │
└─────────┼──────────────────────┼────────────────┘
          │  fetch               │  fetch
          ▼                      ▼
┌─────────────────────────────────────────────────┐
│  FastAPI Backend (:8000)                        │
│                                                 │
│  /api/reader/upload      ← PDF 업로드 + 파싱    │
│  /api/reader/documents   ← 문서 목록            │
│  /api/reader/document/:id ← 문서 상세/삭제      │
│  /api/reader/translate   ← Ollama 번역          │
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ PyMuPDF  │  │ Ollama   │  │ data/reader/ │  │
│  │ PDF 파싱 │  │ 번역 API │  │ JSON 저장소  │  │
│  └──────────┘  └──────────┘  └──────────────┘  │
└─────────────────────────────────────────────────┘
```

---

## 3. 화면 구성

### 3.1 공통 헤더

`platform-header.js` 공통 컴포넌트 사용 (Explorer/Launcher/Reader 통일).

| 요소 | 설명 |
|------|------|
| 로고 + "Reader" | 좌측 |
| midSlot | 페이지 네비게이션 (뷰어 모드에서만 표시) |
| nav | Platform 링크 · ← 목록 · username \| Logout · 테마 토글 |

### 3.2 목록 뷰 (기본)

- **업로드 존**: PDF 드래그 앤 드롭 또는 클릭 업로드
- **프로그레스 바**: NDJSON 스트리밍으로 파싱 진행률 실시간 표시
- **문서 카드 그리드**: 파일명, 페이지 수, 번역 진행률, 삭제 버튼

### 3.3 뷰어 (문서 카드 클릭 시)

- **좌측 패널**: PDF.js canvas로 원본 PDF 렌더링 (`has_pdf` 문서), 레거시 텍스트 폴백
- **우측 패널**: 페이지 동기화 번역 텍스트 (`white-space: normal`로 한글 자연 줄바꿈)
- **헤더 midSlot**: ◀ 페이지 ▶ | 번역 아이콘 | 세그먼트 프로그레스 바
- **번역 프로그레스 바**: 번역 버튼 우측 인라인 표시 (80px 바 + `n/m` 텍스트), 완료 후 1.5초 뒤 숨김
- **번역 완료 하이라이트**: 완료 순간 플래시 애니메이션 (800ms) + 영구 좌측 파란 보더
- **좌우 클릭 동기화**:
  - PDF 모드: 우측 단락 클릭 → 좌측 PDF 위 바운딩박스 오버레이 (`bbox` 좌표 기반)
  - 레거시 모드: 좌/우 단락 클릭 → 양쪽 DOM 하이라이트 동기화

---

## 4. 백엔드 API

모든 엔드포인트 prefix: `/api/reader`

### POST `/upload`

PDF 업로드 → PyMuPDF 파싱 → NDJSON 스트리밍 응답.

- **권한**: editor 이상 (`require_editor`)
- **요청**: `multipart/form-data` — `file` 필드
- **제한**: 최대 100MB (`READER_MAX_PDF_SIZE`)
- **응답**: `text/plain` NDJSON 스트림

```jsonl
{"step": "parsing", "status": "progress", "current": 1, "total": 31}
{"step": "parsing", "status": "progress", "current": 2, "total": 31}
...
{"step": "done", "status": "completed", "document_id": "20260228_090917_b81b73", "meta": {"pages": 31, "paragraphs": 1008}}
```

### GET `/documents`

업로드된 문서 목록 반환.

- **권한**: viewer 이상
- **응답**: `[{ id, filename, title, pages, paragraphs, translated, created_at }]`

### GET `/document/{doc_id}`

문서 상세 (원문 + 번역 포함).

- **권한**: viewer 이상
- **응답**: `{ id, filename, title, pages, paragraphs, has_pdf, content: [{ id, page, text, translated, type, bbox?, page_size? }], created_at }`

### DELETE `/document/{doc_id}`

문서 삭제.

- **권한**: editor 이상
- **응답**: `{ success: true }`

### POST `/translate`

문단 번역 — Ollama API 호출, NDJSON 스트리밍.

- **권한**: viewer 이상
- **요청**: `{ "document_id": "...", "paragraph_ids": [0, 1, 2] | null }`
  - `paragraph_ids`가 null이면 미번역 전체 번역
- **응답**: NDJSON 스트림

```jsonl
{"step": "translate", "status": "progress", "paragraph_id": 0, "translated": "번역 텍스트...", "current": 1, "total": 50}
...
{"step": "done", "status": "completed", "translated_count": 50}
```

---

## 5. 데이터 구조

### 저장 위치

`data/reader/` 디렉토리 (파일 기반, DB 미사용).

```
data/reader/
  _index.json                      ← 문서 목록 인덱스
  20260228_090917_b81b73.json      ← 개별 문서 (원문 + 번역)
  pdfs/
    20260228_090917_b81b73.pdf     ← PDF 원본 바이너리 (PDF.js 렌더링용)
```

### `_index.json` — 문서 목록

```json
[
  {
    "id": "20260228_090917_b81b73",
    "filename": "paper.pdf",
    "title": "AIR-BENCH: Automated Heterogeneous...",
    "pages": 31,
    "paragraphs": 1008,
    "translated": 245,
    "created_at": "2026-02-28T09:09:17.123456"
  }
]
```

### 개별 문서 JSON — `{doc_id}.json`

```json
{
  "id": "20260228_090917_b81b73",
  "filename": "paper.pdf",
  "title": "AIR-BENCH: ...",
  "pages": 31,
  "paragraphs": 1008,
  "has_pdf": true,
  "content": [
    {
      "id": 0,
      "page": 1,
      "text": "AIR-BENCH: Automated Heterogeneous Information Retrieval Benchmark",
      "translated": null,
      "type": "text",
      "bbox": [72.0, 71.25, 523.2, 95.63],
      "page_size": [612.0, 792.0]
    },
    {
      "id": 1,
      "page": 1,
      "text": "[Figure]",
      "translated": null,
      "type": "figure",
      "bbox": [100.0, 200.0, 500.0, 450.0],
      "page_size": [612.0, 792.0]
    }
  ],
  "created_at": "2026-02-28T09:09:17.123456"
}
```

### 단락 타입

| type | 설명 |
|------|------|
| `text` | 일반 텍스트 — 번역 대상 |
| `figure` | 이미지 블록 — `[Figure]`로 표시, 번역 스킵 |
| `formula` | 수식 (특수문자 비율 30% 초과) — 원문 유지 |

### 단락 부가 필드

| 필드 | 타입 | 설명 |
|------|------|------|
| `bbox` | `[x0, y0, x1, y1]` | PDF 페이지 내 블록 좌표 (pt 단위). 클릭 시 PDF 오버레이 하이라이트에 사용 |
| `page_size` | `[width, height]` | PDF 페이지 원본 크기 (pt). bbox→canvas 좌표 변환 시 스케일 계산에 사용 |

> `bbox`/`page_size`는 신규 업로드 문서부터 포함됩니다. 기존 문서는 이 필드가 없으며, 프론트엔드는 필드 부재 시 오버레이를 스킵합니다.

---

## 6. 번역 파이프라인

### 흐름

```
사용자: 번역 버튼 클릭 (전체 또는 단락 클릭)
    ↓
프론트엔드: POST /api/reader/translate
    ↓
백엔드: 대상 단락 필터링 (미번역 text 타입만)
    ↓
각 단락마다:
    1. MD5 캐시 확인 → 히트 시 캐시 반환
    2. Ollama API 호출 (generate, stream: false)
    3. 줄바꿈 후처리: 단일 \n → 공백 치환 (\n\n 문단 구분은 유지)
    4. 번역 결과 NDJSON 이벤트로 스트리밍
    5. 매 5단락마다 중간 저장
    ↓
최종 저장 + 인덱스 갱신
```

### 번역 프롬프트

```
You are an expert academic translator.
Translate the following English text to Korean.
Keep technical terms, abbreviations, and proper nouns in English.
Output ONLY the translation, no explanation.
```

### 캐시

- 인메모리 MD5 해시 기반 — 동일 텍스트 재번역 방지
- 서버 재시작 시 캐시 초기화 (영구 캐시 아님)

---

## 7. 파일 구조

```
프론트엔드
├── reader.html                      ← Reader SPA (목록 + 뷰어)
├── css/platform-header.css          ← 공통 헤더 스타일
├── js/platform-header.js            ← 공통 헤더 컴포넌트
└── js/config.js                     ← AUTH_CONFIG (backendUrl)

백엔드
├── backend/api/reader.py            ← Reader API 라우터
├── backend/services/reader_service.py ← PDF 파싱, 번역, 저장
└── backend/config.py                ← READER_* 설정

데이터
└── data/reader/                     ← 문서 JSON 저장소
    ├── _index.json
    ├── {doc_id}.json
    └── pdfs/{doc_id}.pdf            ← PDF 원본 바이너리
```

---

## 8. 설정

`backend/config.py` 내 Reader 관련 설정:

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `READER_DATA_DIR` | `data/reader` | 문서 저장 디렉토리 |
| `READER_MAX_PDF_SIZE` | `100MB` | 업로드 최대 크기 |
| `READER_TRANSLATION_TIMEOUT` | `120초` | 단락별 번역 타임아웃 |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama 서버 주소 |
| `OLLAMA_MODEL` | 설정에 따름 | 번역에 사용할 모델 |

---

## 9. 개발 로드맵

### Phase 1 — PDF.js 뷰어 전환 ✅

- [x] 좌측 패널: PDF.js canvas 원본 렌더링 (레거시 텍스트 폴백 유지)
- [x] PDF 바이너리 저장/서빙 (`GET /api/reader/pdf/{doc_id}`)
- [x] 우측 패널: 페이지 단위 번역 텍스트 (좌측 페이지와 동기화)
- [x] 페이지 네비게이션이 양쪽 패널을 동시에 제어
- [x] 리사이즈 debounce 200ms로 canvas 재렌더링

### Phase 1.5 — 번역 UX 개선 ✅

- [x] 세그먼트 프로그레스 바 (번역 버튼 우측 인라인)
- [x] 번역 완료 단락 하이라이트 (플래시 애니메이션 + 영구 좌측 보더)
- [x] 좌우 패널 클릭 동기화 (레거시: DOM 양쪽, PDF: 바운딩박스 오버레이)
- [x] 한글 줄바꿈 정리 (CSS `white-space: normal` + 백엔드 `\n` → 공백 후처리)
- [x] PDF 바운딩박스 오버레이 (`bbox`/`page_size` 좌표로 원문 위치 표시)

### Phase 2 — 번역 품질 개선

- [ ] 번역 캐시 영구화 (파일 또는 SQLite)
- [ ] 번역 모델 선택 UI (settings 연동)
- [ ] 번역 결과 수동 편집 기능

### Phase 3 — 고급 기능

- [ ] 다크/라이트 테마 전환 (테마 토글 연동)
- [ ] 번역 PDF 내보내기
- [ ] 논문 메모/하이라이트 기능
