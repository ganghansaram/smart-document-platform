# Translator 시스템 — 설계 문서

PDF 논문 업로드 → PMT(PDFMathTranslate) 통번역 → 번역 PDF 열람

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

- 영문 논문/기술문서 PDF를 업로드하면 PMT(PDFMathTranslate)가 문서 단위 통번역
- 번역 PDF(mono), 이중언어 PDF(dual), 원문 3가지 뷰 제공
- 에어갭(폐쇄망) 환경에서 동작: 로컬 Ollama LLM 사용
- 사용자별 개인 작업공간 (username 기반 디렉토리 격리)

### 핵심 특징

| 항목 | 설명 |
|------|------|
| 번역 엔진 | PDFMathTranslate CLI (`pdf2zh`) — 레이아웃/수식 보존 통번역 |
| PDF 뷰어 | PDF.js 단일 패널, 3탭(번역PDF/이중언어/원문) 전환 |
| 백그라운드 번역 | asyncio Task로 비동기 실행, 3초 폴링으로 상태 갱신 |
| 개인 작업공간 | `data/translator/{username}/` 디렉토리 격리 |
| 권한 | 업로드/삭제: editor 이상 / 열람·번역: viewer 이상 |

---

## 2. 아키텍처

```
[업로드] → [카드 생성(pending)] → [번역 버튼] → [PMT 백그라운드 번역]
                                                       ↓
                                 [카드 활성화(done)] ← [translated.pdf + dual.pdf]
                                       ↓
                              [뷰어: 번역PDF / 이중언어 / 원문]
```

```
Browser (translator.html)
├── 목록 뷰: 업로드 + 카드 그리드 (상태별 UI)
└── 뷰어: 단일 PDF.js 캔버스 + 3탭 전환

FastAPI Backend (:8000)
├── POST /upload         ← PDF 업로드 (즉시 응답)
├── GET  /documents      ← 유저별 문서 목록
├── POST /translate/:id  ← PMT 번역 시작 (202)
├── GET  /translate/:id/status ← 폴링
├── GET  /pdf/:id        ← 원본 PDF
├── GET  /translated-pdf/:id ← 번역 PDF
└── GET  /dual-pdf/:id   ← 이중언어 PDF
```

---

## 3. 화면 구성

### 3.1 목록 뷰 (기본)

- **업로드 존**: PDF 드래그 앤 드롭 또는 클릭 업로드
- **문서 카드**: 파일명, 페이지 수, 상태, 모델 선택, 액션 버튼

카드 상태:

| 상태 | UI |
|------|-----|
| pending | 모델 드롭다운 + 번역 버튼 + 삭제 |
| translating | 프로그레스 바(indeterminate) + 단계 텍스트, 버튼 비활성 |
| done | 보기 + 재번역 + 삭제 버튼, 카드 클릭 → 뷰어 |
| error | 에러 메시지, 모델 드롭다운 + 번역 버튼(재시도) |

### 3.2 뷰어

- **3탭**: 번역PDF (기본) / 이중언어 / 원문
- **단일 PDF.js 캔버스**: 탭 전환 시 해당 PDF 로드
- **헤더 midSlot**: ◀ 페이지 ▶ (이전/다음)
- **줌 컨트롤**: −/+ 버튼, 퍼센트 표시
- **키보드**: ← → 페이지 이동

---

## 4. 백엔드 API

모든 엔드포인트 prefix: `/api/translator`

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/upload` | POST | PDF 업로드 (즉시 JSON 응답) |
| `/documents` | GET | 유저별 문서 목록 |
| `/document/{doc_id}` | GET | 문서 메타 (meta.json) |
| `/document/{doc_id}` | DELETE | 문서 삭제 |
| `/translate/{doc_id}` | POST | 번역 시작 (body: {model}) → 202 |
| `/translate/{doc_id}/status` | GET | 번역 진행 상태 |
| `/retranslate/{doc_id}` | POST | 재번역 (body: {model}) → 202 |
| `/pdf/{doc_id}` | GET | 원본 PDF 서빙 |
| `/translated-pdf/{doc_id}` | GET | 번역 PDF 서빙 |
| `/dual-pdf/{doc_id}` | GET | 이중언어 PDF 서빙 |
| `/models` | GET | Ollama 모델 목록 |

모든 엔드포인트에서 `user["username"]`으로 개인 작업공간 격리.

---

## 5. 데이터 구조

### 저장 위치

```
data/translator/
├── {username}/
│   ├── _index.json              ← 유저별 문서 목록
│   ├── {doc_id}/
│   │   ├── original.pdf         ← 원본 PDF
│   │   ├── translated.pdf       ← PMT mono 출력 (번역PDF)
│   │   ├── dual.pdf             ← PMT dual 출력 (원문+번역)
│   │   └── meta.json            ← 메타데이터 + 번역 상태
```

### `meta.json`

```json
{
  "id": "20260303_120000_abc123",
  "filename": "paper.pdf",
  "title": "paper.pdf",
  "pages": 4,
  "uploaded_at": "2026-03-03T12:00:00",
  "status": "pending|translating|done|error",
  "progress_stage": "번역 중...",
  "model": "gemma3:4b",
  "translated_at": null,
  "error": null
}
```

### `_index.json`

```json
[
  {
    "id": "20260303_120000_abc123",
    "filename": "paper.pdf",
    "pages": 4,
    "status": "done",
    "uploaded_at": "2026-03-03T12:00:00"
  }
]
```

---

## 6. 번역 파이프라인

### 흐름

```
사용자: 카드에서 모델 선택 + "번역" 클릭
    ↓
프론트엔드: POST /api/translator/translate/{doc_id} (body: {model})
    ↓
백엔드:
    1. meta.json status → "translating"
    2. asyncio.create_task(_run_pmt()) 생성
    3. 즉시 202 응답
    ↓
_run_pmt (비동기):
    1. pdf2zh CLI 실행 (subprocess)
    2. stderr 파싱 → progress_stage 갱신
    3. 완료 시: *.mono.pdf → translated.pdf, *.dual.pdf → dual.pdf
    4. meta.json status → "done"
    (실패 시: status → "error", error 메시지 기록)
    ↓
프론트엔드: 3초 폴링으로 상태 갱신 → 카드 UI 업데이트
```

### PMT CLI 명령

```bash
pdf2zh --ollama --ollama-model gemma3:4b --ollama-host http://localhost:11434 \
       --lang-in en --lang-out ko --primary-font-family sans-serif \
       --output {tmp_dir} {original.pdf}
```

---

## 7. 파일 구조

```
프론트엔드
├── translator.html                     ← Translator SPA (카드 목록 + PDF.js 뷰어)
├── css/platform-header.css             ← 공통 헤더 스타일
├── js/platform-header.js               ← 공통 헤더 컴포넌트
├── js/lib/pdfjs/                       ← PDF.js v3.11.174 (legacy ES5)
└── js/config.js                        ← AUTH_CONFIG (backendUrl)

백엔드
├── backend/api/translator.py           ← Translator API 라우터
├── backend/services/translator_service.py ← PMT 번역, 개인 작업공간, 메타 관리
└── backend/config.py                   ← TRANSLATOR_* 설정

데이터
└── data/translator/{username}/{doc_id}/ ← 문서별 디렉토리
```

---

## 8. 설정

`backend/config.py` 내 Translator 관련 설정:

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `TRANSLATOR_DATA_DIR` | `data/translator` | 문서 저장 디렉토리 |
| `TRANSLATOR_MAX_PDF_SIZE` | `100MB` | 업로드 최대 크기 |
| `TRANSLATOR_TRANSLATION_MODEL` | `""` (OLLAMA_MODEL 폴백) | PMT 번역 모델 |
| `TRANSLATOR_PMT_TIMEOUT` | `1200` (20분) | PMT CLI 타임아웃 |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama 서버 주소 |
