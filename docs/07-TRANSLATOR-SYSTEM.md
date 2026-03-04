# Translator 시스템 — 설계 문서

PDF 논문 업로드 → 페이지별 온디맨드 번역 → 듀얼 패널(원문/번역) 열람

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

---

## 1. 개요

### 목적

- 영문 논문/기술문서 PDF를 업로드하면 PMT(PDFMathTranslate)가 **페이지별 온디맨드 번역**
- 듀얼 패널 뷰어: 좌측 원문, 우측 번역 PDF 동시 열람
- 에어갭(폐쇄망) 환경에서 동작: 로컬 Ollama LLM 사용
- 사용자별 개인 작업공간 (username 기반 디렉토리 격리)
- **개인 폴더 트리**: 문서를 폴더로 분류·관리

### 핵심 특징

| 항목 | 설명 |
|------|------|
| 번역 엔진 | PDFMathTranslate CLI (`pdf2zh`) — 레이아웃/수식 보존 |
| 번역 단위 | 페이지별 온디맨드 (단일 또는 범위 최대 5페이지) |
| PDF 뷰어 | 듀얼 패널 (좌=원문, 우=번역), 스크롤 동기화 토글 |
| 개인 폴더 | 트리 패널로 폴더 생성/이름변경/삭제, 문서 이동 |
| 백그라운드 번역 | asyncio Task, 문서당 1페이지 동시 번역, 3초 폴링 |
| 개인 작업공간 | `data/translator/{username}/` 디렉토리 격리 |
| 권한 | 업로드/삭제/폴더관리: editor 이상 / 열람·번역: viewer 이상 |

---

## 2. 아키텍처

```
[업로드] → [카드 생성] → [뷰어 열기] → [페이지별 번역 버튼]
                                              ↓
                              [PMT 백그라운드 번역 (1페이지)]
                                              ↓
                              [번역 PDF → 우측 패널에 표시]
```

```
Browser (translator.html)
├── 트리 패널: 폴더 트리 + 문서 목록 (오버레이, 핀 고정)
├── 목록 뷰: 업로드 존 + 카드 그리드 (폴더별 필터링)
└── 뷰어: 듀얼 패널 (좌=원문 PDF.js, 우=번역 PDF.js)

FastAPI Backend (:8000)
├── 폴더 CRUD
│   ├── GET    /folders              ← 폴더 목록
│   ├── POST   /folders              ← 폴더 생성
│   ├── PUT    /folders/{id}         ← 이름 변경
│   └── DELETE /folders/{id}         ← 삭제 (하위→상위 이동)
├── 문서 관리
│   ├── POST   /upload               ← PDF 업로드
│   ├── GET    /documents            ← 문서 목록
│   ├── GET    /document/{id}        ← 메타 조회
│   ├── DELETE /document/{id}        ← 삭제
│   └── POST   /document/{id}/move   ← 폴더 이동
├── 페이지별 번역
│   ├── POST   /translate/{id}/page/{n}        ← 단일 페이지 번역
│   ├── POST   /translate/{id}/pages           ← 범위 번역 (최대 5p)
│   ├── GET    /translate/{id}/page/{n}/status  ← 페이지 상태
│   └── POST   /translate/{id}/page/{n}/cancel  ← 취소
├── PDF 서빙
│   ├── GET    /pdf/{id}                       ← 원본
│   ├── GET    /translated-pdf/{id}/page/{n}   ← 페이지별 번역 PDF
│   ├── GET    /translated-pdf/{id}            ← 레거시 통번역
│   └── GET    /dual-pdf/{id}                  ← 레거시 이중언어
├── GET    /document/{id}/pages               ← 전체 페이지 상태 요약
└── GET    /models                            ← Ollama 모델 목록
```

---

## 3. 화면 구성

### 3.1 트리 패널 (개인 폴더)

- **오버레이 슬라이드 패널**: 좌측 핸들 버튼(›) 클릭 시 등장
- **핀 고정**: 핀 버튼으로 패널 고정, 언핀 시 커서 이탈하면 자동 닫힘
- **트리 구조**: Explorer `tree-menu.css` 스타일 재사용
  - 루트 "내 문서" (항상 존재)
  - 폴더 노드: 확장/축소, 하위 폴더 지원
  - 문서 노드: 파일명 + 페이지 수 뱃지
- **컨텍스트 메뉴** (우클릭):
  - 폴더: 새 폴더 / 이름 변경 / 삭제
  - 문서: 이동... → 폴더 선택 다이얼로그
- **드래그 앤 드롭**: 카드를 트리의 폴더에 드롭하여 이동
- **상태 유지**: 핀/확장 상태 `localStorage` 저장

### 3.2 목록 뷰 (Home)

- **업로드 존**: PDF 드래그 앤 드롭 또는 클릭 업로드
- **카드 그리드**: 선택된 폴더의 문서만 표시
  - Home(루트) 선택 시: 폴더에 넣지 않은 문서만
  - 특정 폴더 선택 시: 해당 폴더 문서만
- **카드 정보**: 파일명, 페이지 수, 업로드일, 번역 진행 상태
- **카드 버튼**: 열기 / 삭제

### 3.3 뷰어 (듀얼 패널)

- **좌측**: 원문 PDF (PDF.js)
- **우측**: 번역 PDF — 상태에 따라 다른 화면 표시
  - `pending`: 번역 대기 (번역 버튼)
  - `translating`: 스피너 + 진행 상태
  - `done`: 번역 PDF 표시
  - `error`: 에러 메시지 + 재시도
  - `legacy`: 레거시 통번역 PDF 표시
- **헤더 내비게이션**: Home 버튼 (목록 복귀), Platform 링크
- **페이지 이동**: ◀ ▶ 버튼, 키보드 ← →
- **줌**: −/+ 버튼, 퍼센트 표시, 좌우 패널 독립 줌
- **스크롤 동기화**: 토글 버튼으로 좌우 패널 동기 스크롤
- **범위 번역**: "범위 번역" 버튼 → 시작/끝 페이지 입력 (최대 5페이지)

---

## 4. 백엔드 API

모든 엔드포인트 prefix: `/api/translator`

### 폴더 관리

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/folders` | GET | viewer | 폴더 목록 |
| `/folders` | POST | editor | 폴더 생성 `{ name, parent_id? }` |
| `/folders/{folder_id}` | PUT | editor | 이름 변경 `{ name }` |
| `/folders/{folder_id}` | DELETE | editor | 삭제 (하위 항목은 상위로 이동) |

### 문서 관리

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/upload` | POST | editor | PDF 업로드 (즉시 JSON 응답) |
| `/documents` | GET | viewer | 유저별 문서 목록 |
| `/document/{doc_id}` | GET | viewer | 문서 메타 (meta.json) |
| `/document/{doc_id}` | DELETE | editor | 문서 삭제 |
| `/document/{doc_id}/move` | POST | editor | 폴더 이동 `{ folder_id }` (null=루트) |
| `/document/{doc_id}/pages` | GET | viewer | 전체 페이지 상태 요약 |

### 번역

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/translate/{doc_id}/page/{page_num}` | POST | viewer | 단일 페이지 번역 → 202 |
| `/translate/{doc_id}/pages` | POST | viewer | 범위 번역 `{ page_start, page_end, model? }` → 202 |
| `/translate/{doc_id}/page/{page_num}/status` | GET | viewer | 페이지 번역 상태 |
| `/translate/{doc_id}/page/{page_num}/cancel` | POST | viewer | 번역 취소 |

### PDF 서빙

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/pdf/{doc_id}` | GET | 원본 PDF |
| `/translated-pdf/{doc_id}/page/{page_num}` | GET | 페이지별 번역 PDF |
| `/translated-pdf/{doc_id}` | GET | 레거시 통번역 PDF |
| `/dual-pdf/{doc_id}` | GET | 레거시 이중언어 PDF |

### 기타

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/models` | GET | Ollama 사용 가능 모델 목록 |

---

## 5. 데이터 구조

### 저장 위치

```
data/translator/
├── {username}/
│   ├── _index.json              ← 유저별 문서 목록
│   ├── _folders.json            ← 유저별 폴더 구조
│   ├── {doc_id}/
│   │   ├── original.pdf         ← 원본 PDF
│   │   ├── meta.json            ← 메타데이터 + 페이지별 번역 상태
│   │   ├── pmt.log              ← PMT 실행 로그
│   │   ├── pages/
│   │   │   └── {N}/
│   │   │       └── translated.pdf  ← 페이지별 번역 결과 (1페이지 PDF)
│   │   ├── translated.pdf       ← (레거시) 통번역 결과
│   │   └── dual.pdf             ← (레거시) 이중언어 결과
```

### `meta.json`

```json
{
  "id": "20260303_120000_abc123",
  "filename": "paper.pdf",
  "title": "paper.pdf",
  "pages": 4,
  "uploaded_at": "2026-03-03T12:00:00",
  "status": "uploaded",
  "has_legacy_translation": false,
  "page_status": {
    "1": { "status": "done", "model": "gemma3:4b", "translated_at": "..." },
    "2": { "status": "translating", "model": "gemma3:4b" },
    "3": { "status": "pending" }
  }
}
```

페이지 상태: `pending` → `translating` → `done` | `error`

### `_index.json`

```json
[
  {
    "id": "20260303_120000_abc123",
    "filename": "paper.pdf",
    "pages": 4,
    "status": "uploaded",
    "uploaded_at": "2026-03-03T12:00:00",
    "folder": "f_20260304_abc123"
  }
]
```

- `folder`: 폴더 ID (null 또는 필드 없음 = 루트, 하위 호환)

### `_folders.json`

```json
[
  { "id": "f_20260304_abc123", "name": "계약서", "parent_id": null, "order": 0 },
  { "id": "f_20260304_def456", "name": "기술문서", "parent_id": null, "order": 1 },
  { "id": "f_20260304_ghi789", "name": "비행시험", "parent_id": "f_20260304_def456", "order": 0 }
]
```

---

## 6. 번역 파이프라인

### 흐름

```
사용자: 뷰어에서 페이지 이동 → 미번역 페이지면 "번역" 버튼 표시
    ↓
프론트엔드: POST /api/translator/translate/{doc_id}/page/{page_num}
    ↓
백엔드:
    1. 문서당 동시 번역 체크 (이미 번역 중이면 409)
    2. page_status[N] → "translating"
    3. asyncio.create_task(_run_pmt_page()) 생성
    4. 즉시 202 응답
    ↓
_run_pmt_page (비동기):
    1. pdf2zh CLI 실행 (--pages N --only-include-translated-page --no-dual)
    2. 완료 시: pages/{N}/translated.pdf 저장
    3. page_status[N] → "done"
    (실패 시: page_status[N] → "error")
    ↓
프론트엔드: 3초 폴링으로 상태 갱신 → 우측 패널에 번역 PDF 표시
```

### 범위 번역

- "범위 번역" 버튼 → 시작/끝 페이지 입력 다이얼로그
- 최대 5페이지, PMT에 `--pages M-N` 전달
- 완료 시 각 페이지를 개별 1페이지 PDF로 분리 저장

### PMT CLI 명령 (페이지별)

```bash
pdf2zh --ollama --ollama-model gemma3:4b --ollama-host http://localhost:11434 \
       --lang-in en --lang-out ko --primary-font-family sans-serif \
       --pages {N} --only-include-translated-page --no-dual \
       --output {tmp_dir} {original.pdf}
```

### 동시성 제어

- 키: `"{doc_id}:{pages_str}"` — 문서당 1개 번역만 동시 실행
- 추가 요청 시 409 Conflict 응답
- 타임아웃: 5분/페이지 (`TRANSLATOR_PAGE_TIMEOUT`)

---

## 7. 파일 구조

```
프론트엔드
├── translator.html                     ← Translator SPA (트리 + 카드 + 듀얼 뷰어)
├── css/platform-header.css             ← 공통 헤더 스타일
├── css/tree-menu.css                   ← 트리 메뉴 스타일 (Explorer 공유)
├── js/platform-header.js               ← 공통 헤더 컴포넌트
├── js/lib/pdfjs/                       ← PDF.js v3.11.174 (legacy ES5)
└── js/config.js                        ← AUTH_CONFIG (backendUrl)

백엔드
├── backend/api/translator.py           ← Translator API 라우터
├── backend/services/translator_service.py ← PMT 번역, 폴더 CRUD, 메타 관리
└── backend/config.py                   ← TRANSLATOR_* 설정

데이터
└── data/translator/{username}/
    ├── _index.json                     ← 문서 목록
    ├── _folders.json                   ← 폴더 구조
    └── {doc_id}/                       ← 문서별 디렉토리
```

---

## 8. 설정

`backend/config.py` 내 Translator 관련 설정:

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `TRANSLATOR_DATA_DIR` | `data/translator` | 문서 저장 디렉토리 |
| `TRANSLATOR_MAX_PDF_SIZE` | `100MB` | 업로드 최대 크기 |
| `TRANSLATOR_TRANSLATION_MODEL` | `""` (OLLAMA_MODEL 폴백) | PMT 번역 모델 |
| `TRANSLATOR_PAGE_TIMEOUT` | `300` (5분) | 페이지별 번역 타임아웃 |
| `TRANSLATOR_PMT_TIMEOUT` | `3600` (1시간) | 레거시 통번역 타임아웃 |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama 서버 주소 |
