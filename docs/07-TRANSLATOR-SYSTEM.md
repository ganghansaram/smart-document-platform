# Notebook(Translator) 시스템 — 설계 문서

PDF 논문 업로드 → 페이지별 온디맨드 번역 → 듀얼 패널(원문/번역) 열람
문서 분석(추출/요약/마인드맵) → Q&A 챗봇 → Markdown 편집

---

## 목차

1. [개요](#1-개요)
2. [아키텍처](#2-아키텍처)
3. [화면 구성](#3-화면-구성)
4. [백엔드 API](#4-백엔드-api)
5. [데이터 구조](#5-데이터-구조)
6. [파이프라인](#6-파이프라인)
7. [파일 구조](#7-파일-구조)
8. [설정](#8-설정)

---

## 1. 개요

### 목적

- 영문 논문/기술문서 PDF를 업로드하면 **페이지별 온디맨드 번역**
- 듀얼 패널 뷰어: 좌측 원문, 우측 번역 PDF 동시 열람
- **문서 분석**: 추출 → AI 요약 → 마인드맵 자동 생성
- **Q&A 챗봇**: 문서 기반 질의응답, 스트리밍 응답
- 에어갭(폐쇄망) 환경에서 동작: 로컬 Ollama LLM 사용
- 사용자별 개인 작업공간 (username 기반 디렉토리 격리)
- **개인 폴더 트리**: 문서를 폴더로 분류·관리

### 핵심 특징

| 항목 | 설명 |
|------|------|
| 번역 엔진 | **PDF 모드**: PDFMathTranslate (`pdf2zh`) — 레이아웃/수식 보존 |
|  | **웹 뷰 모드**: Markdown 추출+번역 — PyMuPDF + Ollama (편집 가능) |
| 번역 단위 | 페이지별 온디맨드 (단일 또는 범위 최대 5페이지) |
| PDF 뷰어 | 듀얼 패널 (좌=원문, 우=번역), 스크롤 동기화 토글 |
| 문서 분석 | PDF → Markdown 추출 → AI 요약(크기 적응형) → 마인드맵(LLM 생성) |
| Q&A 챗봇 | 문서 기반 질의응답, 컨텍스트 폴백 체인, NDJSON 스트리밍 |
| 마인드맵 | Markmap 인터랙티브 트리, LLM 의미 분석 + 헤딩 폴백 |
| Markdown 편집기 | Monaco 기반 분할뷰 (editor-core.js Strategy 패턴) |
| 마킹/메모 | 원문 텍스트 드래그 → 형광펜 마킹, 색상 4종, 메모 작성, 목록 탐색 |
| 개인 용어집 | source/target 쌍 관리, pdf2zh 번역 시 자동 적용 |
| 문서 내 검색 | 원문+번역문+메모 키워드 검색, Ctrl+K |
| 개인 폴더 | 트리 패널로 폴더 생성/이름변경/삭제, 문서 이동 |
| ZIP 다운로드 | MD + 이미지 자산 일괄 다운로드 |
| 백그라운드 처리 | asyncio Task, 문서당 1페이지 동시 번역, 3초 폴링 |
| 개인 작업공간 | `data/translator/{username}/` 디렉토리 격리 |
| 권한 | 업로드/삭제/폴더관리: editor 이상 / 열람·번역: viewer 이상 |

---

## 2. 아키텍처

```
[업로드] → [카드 생성] → [뷰어 열기] → [페이지별 번역]
                                              ↓
                              [PMT/웹뷰 백그라운드 번역]
                                              ↓
                              [번역 결과 → 우측 패널에 표시]
                                              ↓
                              [문서 분석] → [추출 → 요약 → 마인드맵]
                                              ↓
                              [Q&A 챗봇 / Markdown 편집]
```

```
Browser (translator.html)
├── 트리 패널: 폴더 트리 + 문서 목록 (오버레이, 핀 고정)
├── 목록 뷰: 업로드 존 + 카드 그리드 (폴더별 필터링)
└── 뷰어: 듀얼 패널 (좌=원문 PDF.js, 우=번역 PDF/웹뷰)
    ├── 툴바: [모델▼] (●PDF ○웹뷰) [번역] [범위] [A-][A+]
    └── 우측 레일: [PDF번역] [웹뷰] [메모] [용어집] [AI분석]

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
│   ├── PUT    /document/{id}        ← 이름 변경
│   ├── DELETE /document/{id}        ← 삭제
│   └── POST   /document/{id}/move   ← 폴더 이동
├── 페이지별 번역 (PDF 모드 — pdf2zh)
│   ├── POST   /translate/{id}/page/{n}        ← 단일 페이지 번역
│   ├── POST   /translate/{id}/pages           ← 범위 번역 (최대 5p)
│   ├── GET    /translate/{id}/page/{n}/status  ← 페이지 상태
│   └── POST   /translate/{id}/page/{n}/cancel  ← 취소
├── 웹 뷰 번역 (Markdown 추출+번역)
│   ├── POST   /web-translate/{id}/page/{n}        ← 웹 뷰 번역 시작
│   ├── GET    /web-translate/{id}/page/{n}/status  ← 상태 폴링
│   └── POST   /web-translate/{id}/page/{n}/cancel  ← 취소
├── 문서 추출 (번역 없이 Markdown 추출)
│   ├── POST   /extract/{id}                    ← 전체/지정 페이지 추출
│   ├── GET    /extract/{id}/status              ← 추출 진행 상태
│   ├── GET    /extracted-view/{id}/page/{n}     ← 추출 원문 MD
│   └── GET    /extracted-view/{id}/full         ← 전체 추출 병합 MD
├── AI 요약/분석
│   ├── POST   /document/{id}/summary            ← 요약 생성
│   ├── GET    /document/{id}/summary             ← 요약 상태+데이터
│   └── POST   /document/{id}/analysis/cancel     ← 분석(추출+요약) 취소
├── 마인드맵
│   └── GET    /document/{id}/mindmap             ← Markmap INode 트리
├── Q&A 챗봇
│   └── POST   /document/{id}/chat/stream         ← 문서 Q&A 스트리밍
├── 웹 뷰 서빙/편집
│   ├── GET    /web-view/{id}/full                ← 전체 번역 MD
│   ├── GET    /web-view/{id}/page/{n}            ← 페이지 번역 MD
│   ├── GET    /web-view/{id}/page/{n}/assets/{f} ← 이미지 자산
│   └── PUT    /web-view/{id}/page/{n}            ← MD 편집 저장
├── PDF 서빙
│   ├── GET    /pdf/{id}                       ← 원본
│   ├── GET    /translated-pdf/{id}/page/{n}   ← 페이지별 번역 PDF
│   ├── GET    /translated-pdf/{id}            ← 레거시 통번역
│   └── GET    /dual-pdf/{id}                  ← 레거시 이중언어
├── 마킹(annotations) CRUD
│   ├── GET    /document/{id}/annotations          ← 마킹 목록
│   ├── POST   /document/{id}/annotations          ← 마킹 생성
│   ├── PUT    /document/{id}/annotations/{ann_id}  ← 수정
│   └── DELETE /document/{id}/annotations/{ann_id}  ← 삭제
├── AI 텍스트 선택
│   └── POST   /ai/selection                   ← 선택 텍스트 번역/요약
├── 검색/용어집
│   ├── GET    /search                         ← 문서 내 검색
│   ├── GET    /glossary                       ← 용어집 조회
│   └── PUT    /glossary                       ← 용어집 저장
├── 다운로드
│   └── GET    /document/{id}/download/zip     ← ZIP 다운로드
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
- **우측**: 번역 결과 — 상태에 따라 다른 화면 표시
  - `pending`: 번역 대기 (번역 버튼)
  - `translating`: 스피너 + 진행 상태
  - `done`: 번역 PDF 또는 웹 뷰 표시
  - `error`: 에러 메시지 + 재시도
  - `legacy`: 레거시 통번역 PDF 표시
- **엔진 토글**: PDF 모드 (pdf2zh, 레이아웃 보존) ↔ 웹 뷰 모드 (Markdown, 편집 가능)
- **헤더 내비게이션**: Home 버튼 (목록 복귀), 시스템 스위처 (격자 아이콘)
- **페이지 이동**: ◀ ▶ 버튼, 키보드 ← →
- **줌**: −/+ 버튼, 퍼센트 표시, 좌우 패널 독립 줌
- **스크롤 동기화**: 토글 버튼으로 좌우 패널 동기 스크롤
- **범위 번역**: "범위 번역" 버튼 → 시작/끝 페이지 입력 (최대 5페이지)

### 3.4 마킹/메모

원문 PDF 위에 형광펜 마킹 + 메모 기록 기능.

- **마킹 생성**: 좌측 원문 텍스트 드래그 → "마킹" 미니 버튼 클릭 → 노랑 형광펜 생성
- **우측 마진 마커**: 좌측 마킹 위치에 대응하는 4px 컬러 바 (y 위치 동기화)
- **popover 편집**: 형광펜 클릭 → 색상 변경(노/초/빨/파) + 메모 읽기/편집 + 삭제
  - 메모 있으면 읽기 모드 → 클릭 시 편집 모드 전환
  - 메모 포함 마킹 삭제 시 확인 문구 표시
- **마킹 목록**: 우측 상단 플로팅 아이콘 → 호버 시 페이지별 그룹 목록 드롭다운
  - 항목 클릭 → 해당 페이지 이동 + 포커스 플래시 효과
- **데이터**: `annotations.json` (문서 디렉토리 내, 서버 저장)

### 3.5 AI 텍스트 선택 메뉴

원문 PDF에서 텍스트를 드래그하면 마킹 외에 AI 번역/요약을 즉석으로 실행할 수 있는 기능.

- **액션 바**: 텍스트 선택 후 3버튼 그룹 표시 — [마킹] [번역] [요약] (SVG 아이콘)
- **AI 결과 popover**: 번역/요약 클릭 시 액션 바가 결과 popover로 교체
  - 스켈레톤 로딩 애니메이션 → 결과 텍스트 페이드인
  - 사용 모델명 표시
  - 최대 높이 240px, 스크롤 가능
  - **바깥 클릭으로 닫히지 않음** — X 버튼 또는 Esc 키로만 닫기 (결과 유실 방지)
  - **AbortController**: popover 닫힘 시 진행 중인 AI 요청을 즉시 취소 (서버 자원 절약)
- **복사 버튼**: 결과를 클립보드에 복사
- **마킹+메모**: AI 결과를 메모로 첨부한 마킹을 한 번에 생성
- **뷰포트 클램핑**: 모든 popover가 화면 밖으로 넘치지 않도록 자동 위치 보정
- **리사이즈 가능 팝업**: AI 결과(360px)·마킹(360px) popover에 `resize:both` 지원
- **설정 연동**: 관리자 설정에서 번역/요약 프롬프트, 타임아웃 변경 가능 (재시작 불필요)

### 3.6 AI 분석 패널 (우측 레일)

문서 분석(추출→요약→마인드맵)과 Q&A 챗봇을 제공하는 우측 패널.

- **문서 분석 흐름**: "문서 분석" 버튼 → 확인 모달(소요 시간 안내) → 전체 페이지 추출 + AI 요약 + 마인드맵 일괄 생성
- **탭 3종**: 요약 / Q&A / 마인드맵
  - 분석 완료 전: Q&A·마인드맵 탭 비활성화 (`disabled`, 안내 툴팁)
  - 분석 완료 후: 3개 탭 모두 활성화
- **요약 탭**:
  - 전체 요약문 (3~5문장)
  - 키워드 배지 목록
  - 섹션별 접이식 상세 요약 (클릭 펼침)
- **Q&A 탭**:
  - 질문 입력 → NDJSON 스트리밍 응답
  - 출처 페이지 배지 (클릭 시 해당 페이지로 이동)
  - 대화 세션 유지 (conversation_id)
  - "대화 초기화" 버튼
- **마인드맵 탭**:
  - Markmap 인터랙티브 트리 (d3.js 기반)
  - 노드 클릭 → 하단 드로어에서 LLM 스트리밍 설명
  - 컨트롤: 전체 펼치기/접기 (우상단), 줌 +/-/맞춤 (우하단)
  - 필 형태 노드 (배경색 + 둥근 모서리)
- **분석 취소**: 진행 중 취소 버튼 → 추출+요약 즉시 중단
- **재분석**: 분석 완료 후 "재분석" 버튼으로 강제 재생성

### 3.7 용어집 패널

개인 용어집을 관리하여 번역 품질을 향상시키는 기능.

- **source/target 쌍**: 영문 원어 → 한국어 번역어
- **인라인 편집**: 추가 (+) / 삭제 (×) 버튼
- **자동 적용**: pdf2zh 번역 시 `_glossary.csv` 자동 생성·전달
- **데이터**: `_glossary.json` (유저 디렉토리 내)

### 3.8 문서 내 검색

- **Ctrl+K** 또는 검색 아이콘 → 검색 오버레이
- 원문 + 번역문 + 메모 본문 대상 키워드 검색
- `source` 파라미터로 검색 대상 필터링 (원문/번역문/전체)
- 결과 클릭 시 해당 페이지·위치로 이동

### 3.9 Markdown 편집기

웹 뷰 번역 결과를 직접 편집할 수 있는 기능.

- **editor-core.js**: 공통 에디터 코어 (Strategy 패턴)
  - Monaco 에디터 래퍼, 분할뷰 (좌=편집, 우=미리보기)
  - 양방향 네비게이션 (편집↔미리보기 동기 스크롤)
- **진입 조건**: 웹 뷰 번역 완료 + 페이지별 모드에서만 편집 버튼 노출
- **저장**: `PUT /web-view/{doc_id}/page/{page_num}` → `full_translated.md` 자동 재병합
- **어댑터 패턴**: Explorer(HTML 편집)와 Notebook(MD 편집) 공통 코어 재사용

### 3.10 ZIP 다운로드

- 원본 PDF + 전체 MD(번역/추출) + 이미지 자산을 ZIP으로 일괄 다운로드
- DRM 환경에서 파일 반출 시 활용
- BackgroundTask로 임시 ZIP 생성 후 자동 정리

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
| `/document/{doc_id}` | PUT | editor | 이름 변경 `{ title }` |
| `/document/{doc_id}` | DELETE | editor | 문서 삭제 |
| `/document/{doc_id}/move` | POST | editor | 폴더 이동 `{ folder_id }` (null=루트) |
| `/document/{doc_id}/pages` | GET | viewer | 전체 페이지 상태 요약 |

### 번역 (PDF 모드 — pdf2zh)

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/translate/{doc_id}/page/{page_num}` | POST | viewer | 단일 페이지 번역 → 202 |
| `/translate/{doc_id}/pages` | POST | viewer | 범위 번역 `{ page_start, page_end, model? }` → 202 |
| `/translate/{doc_id}/page/{page_num}/status` | GET | viewer | 페이지 번역 상태 |
| `/translate/{doc_id}/page/{page_num}/cancel` | POST | viewer | 번역 취소 |

### 웹 뷰 번역 (Markdown 추출+번역)

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/web-translate/{doc_id}/page/{page_num}` | POST | viewer | 웹 뷰 번역 시작 `{ model? }` → 202 |
| `/web-translate/{doc_id}/page/{page_num}/status` | GET | viewer | 번역 상태 폴링 |
| `/web-translate/{doc_id}/page/{page_num}/cancel` | POST | viewer | 번역 취소 |

### 문서 추출 (번역 없이 Markdown 추출)

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/extract/{doc_id}` | POST | viewer | 전체/지정 페이지 추출 `{ pages: "all" \| [1,2] }` → 202 |
| `/extract/{doc_id}/status` | GET | viewer | 추출 진행 상태 |
| `/extracted-view/{doc_id}/page/{page_num}` | GET | viewer | 추출 원문 Markdown |
| `/extracted-view/{doc_id}/full` | GET | viewer | 전체 추출 병합 Markdown |

### AI 요약/분석

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/document/{doc_id}/summary` | POST | viewer | 요약 생성 `{ force? }` → 202 또는 기존 반환 |
| `/document/{doc_id}/summary` | GET | viewer | 요약 상태+데이터 조회 |
| `/document/{doc_id}/analysis/cancel` | POST | viewer | 문서 분석(추출+요약) 취소 |

### 마인드맵

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/document/{doc_id}/mindmap` | GET | viewer | Markmap INode 호환 트리 데이터 |

### Q&A 챗봇

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/document/{doc_id}/chat/stream` | POST | viewer | 문서 Q&A 스트리밍 (NDJSON) `{ question, conversation_id? }` |

- 응답 형식: NDJSON — `{"type":"token","content":"..."}` / `{"type":"done","model":"..."}`
- 컨텍스트 폴백: 번역문 → 추출문 → 원문 PDF 순서
- 출처 페이지: `<!-- Page N -->` 주석에서 추출

### 웹 뷰 서빙/편집

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/web-view/{doc_id}/full` | GET | viewer | 전체 병합 번역 Markdown |
| `/web-view/{doc_id}/page/{page_num}` | GET | viewer | 페이지 번역 Markdown + boxes |
| `/web-view/{doc_id}/page/{page_num}/assets/{filename}` | GET | viewer | 웹 뷰 이미지 자산 (표, 수식, 그림) |
| `/web-view/{doc_id}/page/{page_num}` | PUT | viewer | Markdown 편집 저장 `{ markdown }` → 자동 재병합 |

### PDF 서빙

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/pdf/{doc_id}` | GET | 원본 PDF |
| `/translated-pdf/{doc_id}/page/{page_num}` | GET | 페이지별 번역 PDF (PDF 모드) |
| `/translated-pdf/{doc_id}` | GET | 레거시 통번역 PDF |
| `/dual-pdf/{doc_id}` | GET | 레거시 이중언어 PDF |

### 마킹(annotations)

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/document/{doc_id}/annotations` | GET | viewer | 마킹 목록 `{ highlights: [...] }` |
| `/document/{doc_id}/annotations` | POST | viewer | 마킹 생성 `{ page, rects, color?, text?, memo? }` |
| `/document/{doc_id}/annotations/{ann_id}` | PUT | viewer | 수정 `{ memo?, color? }` |
| `/document/{doc_id}/annotations/{ann_id}` | DELETE | viewer | 삭제 |

### AI 텍스트 선택 (번역/요약)

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/ai/selection` | POST | viewer | 선택 텍스트 번역 또는 요약 `{ text, action, model? }` |

- `action`: `"translate"` (한국어 번역) 또는 `"summarize"` (3문장 요약)
- `text`: 최대 3000자 (초과 시 자동 절단)
- `model`: 생략 시 기본 Ollama 모델 사용
- 응답: `{ "result": "...", "model": "gemma3:4b" }`

### 검색/용어집

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/search` | GET | viewer | 문서 검색 (본문+메모) `?q=키워드&source=원문\|번역\|전체` |
| `/glossary` | GET | viewer | 유저 용어집 조회 |
| `/glossary` | PUT | viewer | 유저 용어집 저장 (전체 교체) |

### 다운로드/기타

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/document/{doc_id}/download/zip` | GET | ZIP 다운로드 (MD + 이미지 자산) |
| `/models` | GET | Ollama 사용 가능 모델 목록 |

---

## 5. 데이터 구조

### 저장 위치

```
data/translator/
├── {username}/
│   ├── _index.json              ← 유저별 문서 목록
│   ├── _folders.json            ← 유저별 폴더 구조
│   ├── _glossary.json           ← 유저별 용어집
│   ├── _glossary.csv            ← pdf2zh용 용어집 (자동 생성)
│   ├── _search_index.json       ← 유저별 검색 인덱스
│   ├── {doc_id}/
│   │   ├── original.pdf         ← 원본 PDF
│   │   ├── meta.json            ← 메타데이터 + 페이지별 상태
│   │   ├── pmt.log              ← PMT 실행 로그
│   │   ├── ai_summary.json      ← AI 요약 + 마인드맵 트리
│   │   ├── annotations.json     ← 마킹/메모 데이터
│   │   ├── full_translated.md   ← 전체 번역 병합 Markdown
│   │   ├── full_extracted.md    ← 전체 추출 병합 Markdown
│   │   ├── pages/
│   │   │   └── {N}/
│   │   │       ├── translated.pdf       ← PDF 모드 번역 결과 (1페이지 PDF)
│   │   │       ├── web_extracted.md     ← 추출 원문 Markdown
│   │   │       ├── web_translated.md    ← 웹 뷰 번역 Markdown
│   │   │       ├── page_boxes.json      ← 레이아웃 박스 (좌표)
│   │   │       └── assets/              ← 추출 이미지 (표, 수식, 그림)
│   │   ├── translated.pdf       ← (레거시) 통번역 결과
│   │   └── dual.pdf             ← (레거시) 이중언어 결과
```

### `meta.json`

```json
{
  "id": "20260303_120000_abc123",
  "filename": "paper.pdf",
  "title": "paper.pdf",
  "pages": 42,
  "uploaded_at": "2026-03-03T12:00:00",
  "status": "uploaded",
  "folder": "f_20260304_abc123",
  "has_legacy_translation": false,
  "page_status": {
    "1": { "status": "done", "model": "gemma3:4b", "translated_at": "..." },
    "2": { "status": "translating", "model": "gemma3:4b" },
    "3": { "status": "pending" }
  },
  "web_pages_status": {
    "1": { "status": "done", "extracted_at": "...", "translated_at": "..." },
    "2": { "status": "pending" }
  },
  "summary_status": { "status": "done" },
  "analysis_key": "doc_id:all"
}
```

- 페이지 상태: `pending` → `translating` → `done` | `error`
- `folder`: 폴더 ID (null 또는 필드 없음 = 루트)
- `summary_status`: 요약 생성 상태 (`pending` → `generating` → `done` | `error`)
- `analysis_key`: 추출+요약 비동기 태스크 키

### `ai_summary.json`

```json
{
  "version": 1,
  "strategy": "direct",
  "source": "extracted",
  "model": "gemma3:4b",
  "created_at": "2026-03-30T12:00:00",
  "elapsed_sec": 45.2,
  "overall_summary": "이 문서는 ... 에 대해 설명합니다.",
  "keywords": ["재료공학", "피로시험", "파괴역학"],
  "sections": [
    { "heading": "1. 서론", "level": 1, "summary": "연구 배경과 목적을 ..." },
    { "heading": "2. 실험 방법", "level": 1, "summary": "시편 준비 및 ..." }
  ],
  "mindmap_tree": {
    "content": "피로시험 분석",
    "depth": 0,
    "children": [
      {
        "content": "연구 배경",
        "depth": 1,
        "children": [
          { "content": "재료 피로 메커니즘의 이해 필요성", "depth": 2 },
          { "content": "기존 연구의 한계점 분석", "depth": 2 }
        ]
      }
    ]
  }
}
```

- `strategy`: `"direct"` (≤12,000자 단일 패스) 또는 `"hierarchical"` (초과 시 Map-Reduce)
- `mindmap_tree`: Markmap INode 호환 포맷 (루트 → 1단계 3~5개 → 2단계 2~3개)

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

### `_folders.json`

```json
[
  { "id": "f_20260304_abc123", "name": "계약서", "parent_id": null, "order": 0 },
  { "id": "f_20260304_def456", "name": "기술문서", "parent_id": null, "order": 1 },
  { "id": "f_20260304_ghi789", "name": "비행시험", "parent_id": "f_20260304_def456", "order": 0 }
]
```

### `annotations.json`

```json
{
  "highlights": [
    {
      "id": "h_1709500000000_abc123",
      "page": 1,
      "rects": [
        { "x": 0.12, "y": 0.34, "w": 0.56, "h": 0.02 }
      ],
      "color": "yellow",
      "text": "선택된 원문 텍스트",
      "memo": "메모 내용",
      "created_at": "2026-03-03T12:00:00"
    }
  ]
}
```

- `rects`: PDF 뷰포트 비율 좌표 (0~1), 복수 가능 (여러 줄 선택)
- `color`: `yellow` | `green` | `red` | `blue` (기본값 `yellow`)

### `_glossary.json`

```json
{
  "version": 1,
  "entries": [
    { "source": "fatigue", "target": "피로" },
    { "source": "fracture mechanics", "target": "파괴역학" }
  ]
}
```

---

## 6. 파이프라인

### 6.1 PDF 모드 번역 (pdf2zh)

```
사용자: 뷰어에서 (●PDF) 선택 → "이 페이지 번역" 클릭
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

### 6.2 웹 뷰 모드 번역 (Markdown 추출+번역)

```
사용자: 뷰어에서 (○웹뷰) 선택 → "이 페이지 번역" 클릭
    ↓
프론트엔드: POST /api/translator/web-translate/{doc_id}/page/{page_num}
    ↓
백엔드: asyncio.create_task → 즉시 202 응답
    ↓
1단계 — 추출 (md_extractor.py):
    1. PyMuPDF로 PDF 페이지 열기
    2. DocLayout-YOLO 레이아웃 감지 (실패 시 PyMuPDF 폴백)
       - title, plain text → Markdown 추출
       - figure, table, formula → 이미지 캡처 (assets/)
    3. web_extracted.md + page_boxes.json 저장
    ↓
2단계 — 번역 (md_translator.py):
    1. Markdown 블록 파싱 (heading/paragraph/table/list/image)
    2. 블록별 Ollama 번역 (용어집 자동 적용)
    3. 테이블 셀 단위 번역 (구조 보존)
    4. web_translated.md 저장
    5. full_translated.md 자동 재병합
    ↓
프론트엔드: 3초 폴링 → 완료 시 번역 Markdown 렌더링
```

### 6.3 문서 분석 파이프라인 (추출 → 요약 → 마인드맵)

```
사용자: AI 분석 패널에서 "문서 분석" 클릭
    ↓
확인 모달: "문서 크기에 따라 수 분이 소요될 수 있습니다"
    ↓
프론트엔드: POST /api/translator/document/{doc_id}/summary
    ↓
백엔드:
    1. 전체 페이지 Markdown 추출 (extract_page × N)
    2. full_extracted.md 병합
    3. AI 요약 생성 (ai_summary.py)
       - ≤ 12,000자: 단일 패스 (direct)
       - > 12,000자: 섹션 분할 → 개별 요약 → 통합 (hierarchical)
    4. 마인드맵 트리 생성 (LLM 의미 분석)
       - 성공 시: INode 트리 (루트 + 1단계 3~5개 + 2단계 2~3개)
       - 실패 시: 헤딩 파싱 폴백 (번호 패턴 → ALL CAPS → MD level)
    5. ai_summary.json 저장 (요약 + 키워드 + 섹션 + mindmap_tree)
    ↓
프론트엔드: 폴링으로 완료 감지 → 요약/마인드맵 탭 활성화
```

### 6.4 Q&A 챗봇

```
사용자: Q&A 탭에서 질문 입력 → 전송
    ↓
프론트엔드: POST /api/translator/document/{doc_id}/chat/stream
    ↓
백엔드 (notebook_chat.py):
    1. 컨텍스트 확보 (폴백 체인: translated → extracted → raw PDF)
    2. 크기 적응형 컨텍스트 구성:
       - 짧은 문서: 전체 텍스트 직접 주입
       - 긴 문서: 키워드 매칭으로 관련 섹션 선별
    3. LLM 스트리밍 응답 (NDJSON)
    4. 출처 페이지 번호 추출 (<!-- Page N --> 주석)
    ↓
프론트엔드: 토큰 단위 실시간 렌더링 + 출처 배지 표시
```

### 6.5 범위 번역

- "범위 번역" 버튼 → 시작/끝 페이지 입력 다이얼로그
- 최대 5페이지, PMT에 `--pages M-N` 전달
- 완료 시 각 페이지를 개별 1페이지 PDF로 분리 저장

### 6.6 PMT CLI 명령 (페이지별)

```bash
pdf2zh --ollama --ollama-model gemma3:4b --ollama-host http://localhost:11434 \
       --lang-in en --lang-out ko --primary-font-family sans-serif \
       --pages {N} --only-include-translated-page --no-dual \
       --output {tmp_dir} {original.pdf}
```

### 6.7 동시성 제어

- 키: `"{doc_id}:{pages_str}"` — 문서당 1개 번역만 동시 실행
- 추가 요청 시 409 Conflict 응답
- 타임아웃: 5분/페이지 (`TRANSLATOR_PAGE_TIMEOUT`)
- 분석 취소: `task.cancel(); await task` — CancelledError 분리 처리

---

## 7. 파일 구조

```
프론트엔드
├── translator.html                     ← Translator SPA (트리 + 카드 + 듀얼 뷰어 + AI 패널)
├── css/tokens.css                      ← 디자인 토큰 (CSS 변수, 리셋, 포커스 링)
├── css/translator.css                  ← Translator 전용 스타일 (뷰어, 카드, 마킹, AI 패널, 다크모드)
├── css/platform-header.css             ← 공통 헤더 스타일 (시스템 스위처 포함)
├── css/platform-footer.css             ← 공통 푸터 스타일
├── css/tree-menu.css                   ← 트리 메뉴 스타일 (Explorer 공유)
├── css/components.css                  ← 공통 컴포넌트 (버튼, 입력, 배지, 스피너)
├── css/modal.css                       ← 공통 모달 스타일
├── js/translator.js                    ← Translator 뷰어 로직 (PDF.js, 마킹, AI 분석, 폴링)
├── js/editor-core.js                   ← 공통 Markdown 편집기 코어 (Monaco 래퍼, Strategy 패턴)
├── js/toast.js                         ← 공통 토스트 알림 (Translator/Compare용)
├── js/platform-header.js               ← 공통 헤더 컴포넌트
├── js/platform-footer.js               ← 공통 푸터 컴포넌트
├── js/config.js                        ← AUTH_CONFIG (backendUrl)
├── js/lib/pdfjs/                       ← PDF.js v3.11.174 (legacy ES5)
└── js/lib/markmap/                     ← Markmap 마인드맵 라이브러리
    ├── d3.min.js                       ← D3 시각화 (IIFE 번들)
    └── markmap-view.js                 ← Markmap 트리 렌더링 (IIFE 번들)

백엔드
├── backend/api/translator.py           ← Translator API 라우터 (번역, 추출, AI, 마킹, 용어집)
├── backend/services/translator_service.py ← 오케스트레이션 (번역, 추출, 요약, 폴더, 메타 관리)
├── backend/services/ai_summary.py      ← 크기 적응형 AI 요약 + 마인드맵 트리 생성
├── backend/services/notebook_chat.py   ← 문서 Q&A (컨텍스트 폴백, 스트리밍)
├── backend/services/md_extractor.py    ← PDF → Markdown 추출 (PyMuPDF + DocLayout-YOLO)
├── backend/services/md_translator.py   ← Markdown 블록 번역 + 병합
├── backend/services/llm_provider.py    ← LLM 프로바이더 추상화 (Ollama + OpenAI 호환)
└── backend/config.py                   ← TRANSLATOR_* 설정

데이터
└── data/translator/{username}/
    ├── _index.json                     ← 문서 목록
    ├── _folders.json                   ← 폴더 구조
    ├── _glossary.json                  ← 개인 용어집
    └── {doc_id}/                       ← 문서별 디렉토리
        ├── meta.json, ai_summary.json, annotations.json
        ├── full_translated.md, full_extracted.md
        └── pages/{N}/ (translated.pdf, web_*.md, assets/)
```

---

## 8. 설정

`backend/config.py` 내 Translator 관련 설정:

### PDF 번역 (pdf2zh)

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `TRANSLATOR_DATA_DIR` | `data/translator` | 문서 저장 디렉토리 |
| `TRANSLATOR_MAX_PDF_SIZE` | `100MB` | 업로드 최대 크기 |
| `TRANSLATOR_TRANSLATION_MODEL` | `""` (OLLAMA_MODEL 폴백) | PMT 번역 모델 |
| `TRANSLATOR_PAGE_TIMEOUT` | `300` (5분) | 페이지별 번역 타임아웃 |
| `TRANSLATOR_PMT_TIMEOUT` | `3600` (1시간) | 레거시 통번역 타임아웃 |
| `TRANSLATOR_MAX_CONCURRENT` | `4` | 동시 번역 최대 수 (GPU 부하 제한) |
| `TRANSLATOR_CUSTOM_PROMPT` | `""` | pdf2zh 커스텀 시스템 프롬프트 |
| `TRANSLATOR_DISABLE_RICH_TEXT` | `False` | pdf2zh 리치 텍스트 번역 비활성화 |
| `TRANSLATOR_TRANSLATE_TABLE` | `False` | pdf2zh 테이블 텍스트 번역 |
| `TRANSLATOR_MIN_TEXT_LENGTH` | `0` | pdf2zh 최소 텍스트 길이 |
| `TRANSLATOR_QPS` | `0` | pdf2zh QPS 제한 (0=무제한) |
| `TRANSLATOR_OCR_WORKAROUND` | `False` | pdf2zh OCR 우회 (스캔 PDF용) |
| `TRANSLATOR_ENHANCE_COMPAT` | `False` | pdf2zh 호환성 강화 |

### 웹 뷰 (Markdown 추출+번역)

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `TRANSLATOR_WEB_TABLE_MODE` | `"image"` | 테이블 처리 (`"image"` / `"extract"` / `"off"`) |
| `TRANSLATOR_WEB_FORMULA_MODE` | `"image"` | 수식 처리 (`"latex"` / `"image"` / `"off"`) |
| `TRANSLATOR_WEB_IMAGE_DPI` | `150` | 이미지 추출 해상도 |
| `TRANSLATOR_WEB_AUTO_SUMMARY` | `False` | 번역 완료 후 자동 요약 |
| `TRANSLATOR_WEB_TABLE_STRATEGY` | `"lines_strict"` | PyMuPDF 테이블 감지 전략 |
| `TRANSLATOR_WEB_DEBUG` | `False` | 디버그 파일 저장 |

### AI 요약/Q&A

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `TRANSLATOR_AI_SUMMARY_MODEL` | `""` (OLLAMA_MODEL 폴백) | 요약 전용 모델 |
| `TRANSLATOR_AI_SUMMARY_THRESHOLD` | `0` (=12,000자) | 직접/계층적 요약 전환 임계값 |
| `TRANSLATOR_AI_QA_THRESHOLD` | `0` (=12,000자) | 전체/섹션 선별 컨텍스트 전환 임계값 |

### AI 텍스트 선택 (인라인 번역/요약)

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `TRANSLATOR_AI_SELECTION_TIMEOUT` | `30` (초) | AI 선택 메뉴 타임아웃 |
| `TRANSLATOR_AI_TRANSLATE_PROMPT` | *(한국어 번역 프롬프트)* | 텍스트 선택 번역 시스템 프롬프트 |
| `TRANSLATOR_AI_SUMMARIZE_PROMPT` | *(3문장 요약 프롬프트)* | 텍스트 선택 요약 시스템 프롬프트 |

### 공통

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `OLLAMA_URL` | `http://localhost:11434` | Ollama 서버 주소 |
| `OLLAMA_MODEL` | `gemma3:4b` | 기본 LLM 모델 |
