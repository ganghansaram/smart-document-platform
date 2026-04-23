# Backend Architecture

Smart Document Platform 백엔드 시스템 설계 및 배포 문서 — Explorer, Notebook(Translator), Verify(Compare)

---

## 목차

1. [시스템 구성도](#1-시스템-구성도)
2. [서버별 설치 항목](#2-서버별-설치-항목)
3. [폴더 구조](#3-폴더-구조)
4. [API 설계](#4-api-설계)
5. [배포 절차](#5-배포-절차)
6. [연동 설정](#6-연동-설정)
7. [확장 로드맵](#7-확장-로드맵)
8. [프론트엔드 렌더링 최적화](#8-프론트엔드-렌더링-최적화)
9. [다크/라이트 모드](#9-다크라이트-모드)
10. [북마크](#10-북마크)
11. [항공 용어집](#11-항공-용어집)
12. [문서 변환 파이프라인](#12-문서-변환-파이프라인)
13. [배너 슬라이드쇼](#13-배너-슬라이드쇼)
14. [키보드 단축키](#14-키보드-단축키)
15. [브레드크럼 내비게이션](#15-브레드크럼-내비게이션)
16. [토스트 알림](#16-토스트-알림)
17. [문제 해결](#17-문제-해결)
18. [관련 문서](#18-관련-문서)

---

## 1. 시스템 구성도

플랫폼은 **배포 환경 3종**을 공식 지원합니다 (상세: [01-DEPLOYMENT-GUIDE](01-DEPLOYMENT-GUIDE.md)).

### 1.1 주 배포 — Docker 2-컨테이너 (회사 Linux VM, 개발 PC)

Plan-27 이후 Nginx + Backend 두 컨테이너로 단일 포트(80)로 운영합니다. 외부에는 Nginx 만 노출되고, 백엔드는 내부 네트워크에만 존재합니다.

```
┌──────────────────────────────────────────────────────────────────────┐
│  Docker Host (회사 Linux VM · 개발 PC WSL2)                          │
│                                                                      │
│  ┌────────────────────┐    ┌────────────────────────────────────┐   │
│  │  Nginx Container   │    │  Backend Container (비특권 appuser) │   │
│  │  (외부 :PORT→80)   │    │  (내부 :8000, 외부 비노출)          │   │
│  │ ─────────────────  │    │ ──────────────────────────────────  │   │
│  │  - 정적 서빙        │───▶│  FastAPI + uvicorn                  │   │
│  │    index / css /   │    │  /api/search · /api/chat            │   │
│  │    js / contents   │    │  /api/save-document     🔒 admin    │   │
│  │  - /api → backend  │    │  /api/document-submit   🔒 admin    │   │
│  │  - 보안 차단(403)  │    │  /api/reindex           🔒 admin    │   │
│  │  - gzip            │    │  /api/auth/*  /api/settings 🔒      │   │
│  └────────────────────┘    │  /api/menu    🔒 · /api/analytics   │   │
│                            │  /api/translator/*   Notebook       │   │
│  볼륨 마운트:              │  /api/compare/*      Verify          │   │
│  - data/      (보존)       │                                      │   │
│  - contents/  (보존)       │  Services (27종):                    │   │
│  - models/    (읽기 전용)  │   · Auth (SQLite sessions)          │   │
│  - backups/   (보존)       │   · KeywordSearch(BM25) / Vector    │   │
│  - logs/      (로테이팅)   │     Search(FAISS+RRF) / Reranker    │   │
│                            │   · QuestionRouter · QueryDecomposer│   │
│  네트워크:                 │     · RAGAgent · QueryRewriter       │   │
│  - 외부: :PORT (Nginx만)   │   · LLMProvider(Ollama/OpenAI호환)  │   │
│  - 내부: backend:8000      │   · TranslatorService · AISummary    │   │
│                            │   · NotebookChat · MdExtractor       │   │
│                            │   · MdTranslator · TextTranslator    │   │
│                            │   · CompareService · SimilarityEngine│   │
│                            │   · RuleEngine · ExportService       │   │
│                            │   · DocumentExtractor · doc_converter│   │
│                            │   · KoreanTokenizer · Analytics      │   │
│                            │   · SettingsService · Conversation   │   │
│                            │                                      │   │
│                            │  Converter (tools/converter/):       │   │
│                            │   · NumberingResolver · omml2mathml  │   │
│                            │   · preprocess/ 어댑터 체인           │   │
│                            │     (word_com / libreoffice / native)│   │
│                            └────────────┬─────────────────────────┘   │
└────────────────────────────────────────│──────────────────────────────┘
                                         │ HTTP (Ollama API)
                                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│  GPU 서버 (회사 Linux · Ollama 별도 호스팅)                          │
│  - LLM 모델: gemma3:27b · 임베딩: bge-m3 (1024차원)                 │
│  - API: http://<gpu-server>:11434                                    │
│  - Plan-40: EMBEDDING_BACKEND_INDEX=ollama 로 인덱싱 GPU 위임        │
│    (RUNTIME은 기본 local — 검색·유사도 저지연 유지)                   │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.2 대안 배포 — Windows 네이티브 (회사 Windows PC)

Docker 가 없는 환경용. 프론트엔드는 Tomcat, 백엔드는 Python 직접 실행입니다. 이 형태는 `03-DOCKER-OPERATIONS` 가 아닌 [01-DEPLOYMENT-GUIDE §5](01-DEPLOYMENT-GUIDE.md#5-환경-c--회사-windows-pc-톰캣--python-직접-실행) 를 참조하세요.

```
┌─────────────────────────────────────────────────────────────┐
│  Windows PC (Docker 없음)                                    │
│  ┌────────────────┐          ┌────────────────────────┐     │
│  │  Tomcat :8080  │─CORS────▶│  FastAPI :8000          │     │
│  │  - 정적 자원   │          │  (python main.py 직접)  │     │
│  └────────────────┘          └──────────┬──────────────┘     │
│                                          │                    │
│  · JDK 1.8 + Tomcat 7.0                 │  Word COM 전처리   │
│  · Python 3.11.9 + venv                 │  (.docx_1 DRM 우회)│
└──────────────────────────────────────────┼────────────────────┘
                                           │ HTTP (Ollama API)
                                           ▼
                                  (회사 GPU 서버의 Ollama)
```

---

## 2. 서버별 설치 항목

### 2.1 Linux 서버 (GPU)

#### 현재 설치됨
| 항목 | 버전 | 용도 |
|------|------|------|
| Ollama | 최신 | LLM 서비스 |
| LLM 모델 | gemma3:27b 등 | 텍스트 생성 |

#### Phase 3 설치됨
| 항목 | 버전 | 용도 |
|------|------|------|
| bge-m3 | - | 임베딩 모델 (Ollama 호스팅, 1024차원) |
| gemma3:27b | - | LLM 모델 (Ollama 호스팅) |

### 2.2 Windows 서버 (웹북)

#### 현재 설치됨
| 항목 | 버전 | 용도 |
|------|------|------|
| JDK | 1.8.0_51 | Tomcat 실행 |
| Apache Tomcat | 7.0.77 | 웹 서비스 |
| Python | 3.11.9 | 스크립트, 백엔드 |
| PyCharm | 2023 | 개발 IDE |

#### 백엔드 패키지
| 항목 | 버전 | 용도 |
|------|------|------|
| fastapi | 0.128.3 | REST API 프레임워크 |
| uvicorn | 0.40.0 | ASGI 서버 |
| pydantic | 2.12.5 | 데이터 검증 |
| pydantic-settings | 2.13.1 | 설정 관리 |
| python-multipart | 0.0.22 | 파일 업로드 지원 |
| requests | 2.32.3 | HTTP 클라이언트 |
| httpx | ≥0.27.0 | 비동기 HTTP (LLM 프로바이더) |
| faiss-cpu | 1.12.0 | FAISS 벡터 검색 |
| sentence-transformers | 5.1.2 | Cross-encoder 리랭커 |
| rank-bm25 | 0.2.2 | BM25 키워드 검색 |
| kiwipiepy | ≥0.18.0 | 한국어 형태소 분석 |
| ollama | 0.6.1 | Ollama 클라이언트 |
| pdf2zh-next | 2.8.2 | PDF 번역 엔진 (PDFMathTranslate) |
| python-docx | 1.2.0 | DOCX 변환 |
| openpyxl | ≥3.1.0 | Excel 파일 처리 |
| rapidocr-onnxruntime | 1.4.4 | 스캔 PDF OCR (Verify) |

---

## 3. 폴더 구조

```
smart-document-platform/
│
├── backend/                        # [NEW] Python 백엔드
│   ├── main.py                     # FastAPI 진입점
│   ├── config.py                   # 설정 (Ollama URL, 모델명 등)
│   ├── requirements.txt            # 의존성 패키지 목록
│   │
│   ├── dependencies.py             # FastAPI 의존성 (require_admin)
│   │
│   ├── api/                        # API 엔드포인트
│   │   ├── __init__.py
│   │   ├── auth.py                 # 인증 API (login/logout/me/users)
│   │   ├── search.py               # POST /api/search
│   │   ├── chat.py                 # POST /api/chat
│   │   ├── document.py             # POST /api/save-document (admin)
│   │   ├── upload.py              # POST /api/document-submit, /api/reindex (admin)
│   │   ├── settings.py            # 설정 API (GET/POST /api/settings, /api/settings/public)
│   │   ├── analytics.py           # 통계 API (heartbeat, dashboard)
│   │   ├── menu.py                # 메뉴 관리 API (GET/POST /api/menu)
│   │   ├── translator.py          # Translator API (번역, 추출, AI 요약, Q&A, 마킹, 용어집)
│   │   └── compare.py             # Compare API (업로드/검증/규칙/AI분류)
│   │
│   ├── services/                   # 비즈니스 로직 (28개 모듈)
│   │   ├── __init__.py
│   │   │── # ── Explorer 서비스 ──
│   │   ├── auth.py                 # 사용자/세션 관리 (SQLite)
│   │   ├── keyword_search.py       # 키워드 기반 검색 (BM25)
│   │   ├── vector_search.py        # FAISS 벡터 검색 + 하이브리드 RRF 병합
│   │   ├── embedding_client.py     # 임베딩 클라이언트 (로컬 sentence-transformers / Ollama)
│   │   ├── reranker.py             # Cross-encoder 리랭킹 (bge-reranker-v2-m3)
│   │   ├── conversation.py         # 인메모리 대화 세션 저장소 (LRU, 60분 유휴)
│   │   ├── query_rewriter.py       # LLM 기반 쿼리 재작성
│   │   ├── question_router.py      # 질문 유형 분류 (SIMPLE/COMPARE/REASON/CHAT)
│   │   ├── query_decomposer.py     # 복합 쿼리 분해 (1~3개 서브쿼리)
│   │   ├── rag_agent.py            # Agentic RAG 반복 검색-판단 루프
│   │   │── # ── 공통 인프라 ──
│   │   ├── llm_provider.py         # LLM 프로바이더 추상화 (Ollama/OpenAI 호환)
│   │   ├── llm_client.py           # LLM 응답 생성 래퍼 (동기/스트리밍)
│   │   ├── korean_tokenizer.py     # 한국어 형태소 분석 (kiwipiepy, 폴백: 공백 분리)
│   │   ├── doc_converter.py         # 문서 변환 (DOCX/PDF → HTML)
│   │   ├── document_extractor.py   # 문서 텍스트 추출 (HTML/PDF/DOCX)
│   │   ├── settings_service.py     # settings.json CRUD, 런타임 config 적용
│   │   ├── analytics.py            # 접속 통계 서비스 (SQLite, 대시보드 집계)
│   │   │── # ── Notebook(Translator) 서비스 ──
│   │   ├── translator_service.py   # 번역/추출/요약 오케스트레이션, 폴더·메타 관리
│   │   ├── ai_summary.py           # 크기 적응형 AI 요약 + 마인드맵 트리 생성
│   │   ├── notebook_chat.py        # 문서 Q&A (컨텍스트 폴백 체인, 스트리밍)
│   │   ├── md_extractor.py         # PDF → Markdown 추출 (PyMuPDF + DocLayout-YOLO)
│   │   ├── md_translator.py        # Markdown 블록 번역 + 병합
│   │   ├── text_translator.py      # 단일/배치 텍스트 번역 (LLM 기반)
│   │   │── # ── Verify(Compare) 서비스 ──
│   │   ├── compare_service.py      # 텍스트 추출, AI 의미 분류
│   │   ├── similarity_engine.py    # 유사도 검사 (Winnowing L1 + bge-m3 시맨틱 L3)
│   │   ├── rule_engine.py          # 문서 규칙 검증 엔진 (21종 규칙)
│   │   └── export_service.py       # 검토 리포트 내보내기 (XLSX/HTML/TXT)
│   │
│   ├── rules/                      # 규칙 엔진 정의 (Verify)
│   │   ├── _schema.json            # 규칙 JSON 스키마
│   │   ├── custom.json             # 자체 규칙 6종
│   │   ├── mil-structure.json      # MIL-STD 문서 구조 규칙 7종
│   │   └── ste-writing.json        # ASD-STE100 작성 규칙 8종
│   │
│   └── packages/                   # 오프라인 설치용 wheel 파일
│       └── (pip download 결과물)
│
├── data/
│   ├── menu.json                   # 트리 메뉴 구조
│   ├── search-index.json           # 키워드 검색 인덱스
│   ├── vector-index.faiss          # FAISS 벡터 인덱스
│   ├── vector-index_meta.json      # 벡터 인덱스 메타데이터
│   ├── auth.db                     # 사용자/세션 SQLite DB (자동 생성)
│   ├── analytics.db                # 접속 통계 SQLite DB (자동 생성)
│   ├── settings.json               # 런타임 설정 오버라이드
│   ├── glossary.json               # 항공 용어집 (26,000+)
│   ├── compare-rules.json          # Verify 검증 규칙 정의
│   ├── boilerplate-phrases.json    # 유사도 검사 보일러플레이트 제외 구문
│   ├── translator/                 # Notebook 개인 작업공간
│   │   └── {username}/             # 유저별 디렉토리
│   ├── compare/                    # Verify 비교 세션 데이터
│   └── verify/                     # Verify 검증 결과
│
├── models/                         # 로컬 ML 모델
│   └── bge-reranker-v2-m3/         # Cross-encoder 리랭커
│
├── backups/                        # 문서 편집 백업 파일
│   └── {문서명}_{날짜}_{시간}.bak
│
├── tools/
│   ├── build-search-index.py       # 키워드 인덱스 생성
│   ├── build-vector-index.py       # FAISS 벡터 인덱스 빌드
│   ├── html_to_text.py             # HTML→검색텍스트 (테이블→MD, MathML→LaTeX)
│   ├── excel-to-menu.py            # 엑셀 → menu.json 변환
│   ├── create-admin.py             # CLI admin 계정 생성/관리
│   ├── daily-backup.py             # 일일 백업 (SQLite + settings + translator, 30일 보존)
│   ├── import-glossary.py          # 용어집 임포트
│   └── converter/                  # 문서 변환기 (DOCX/PDF → HTML, 수식 변환, COM 전처리 포함)
│
├── index.html                     # Explorer (문서 탐색)
├── translator.html                # Notebook(Translator) — PDF 번역·분석
├── compare.html                   # Verify(Compare) — 문서 비교·검증
├── launcher.html                  # Launcher (시스템 선택)
├── admin.html                     # 관리자 설정
├── login.html                     # 로그인
│
├── js/
│   ├── app.js                     # Explorer 코어 (로딩, 스크롤, 설정)
│   ├── config.js                  # DISPLAY/AI/EDITOR/UPLOAD/AUTH_CONFIG
│   ├── auth.js                    # 3-role RBAC, 로그인 리다이렉트
│   ├── ai-chat.js                 # AI 채팅 기능 (스트리밍, 피드백)
│   ├── search.js                  # 검색 기능
│   ├── tree-menu.js               # 트리 메뉴 렌더링
│   ├── section-nav.js             # 우측 섹션 네비게이터
│   ├── editor.js                  # Monaco 에디터 기반 문서 편집기 (Explorer)
│   ├── editor-core.js             # 공통 편집기 코어 (Monaco 래퍼, Strategy 패턴)
│   ├── banner.js                  # 배너 슬라이드쇼
│   ├── figure-popup.js            # 그림/표 참조 팝업
│   ├── bookmarks.js               # 헤딩 북마크
│   ├── glossary.js                # 용어집 + 약어 하이라이트
│   ├── keyboard.js                # 키보드 단축키
│   ├── translator.js              # Notebook 뷰어 (PDF.js, 마킹, AI 분석, 용어집, Q&A)
│   ├── platform-header.js         # 공통 헤더 (SVG 시스템 스위처, 호버 드롭다운)
│   ├── platform-footer.js         # 공통 푸터
│   ├── admin-settings.js          # 관리자 설정 GUI
│   ├── analytics.js               # 접속 통계 (heartbeat, 대시보드)
│   ├── toast.js                   # 공통 토스트 알림 (Notebook/Verify 공용)
│   ├── lib/pdfjs/                 # PDF.js v3.11.174
│   └── lib/markmap/               # Markmap 마인드맵 (d3.min.js, markmap-view.js)
│
├── css/
│   ├── tokens.css                 # 디자인 토큰 (CSS 변수, 리셋, 글로벌 focus-visible)
│   ├── components.css             # 공통 컴포넌트 (버튼, 입력, 배지, 스피너, 슬라이더, 툴팁)
│   ├── modal.css                  # 공통 모달 스타일
│   ├── scrollbar.css              # 공통 스크롤바 스타일
│   ├── toast.css                  # 공통 토스트 알림 스타일
│   ├── platform-header.css        # 공통 헤더 스타일
│   ├── platform-footer.css        # 공통 푸터 스타일
│   ├── main.css, content.css      # Explorer 레이아웃 및 콘텐츠
│   ├── ai-chat.css, editor.css    # Explorer 채팅/편집기
│   ├── tree-menu.css, bookmarks.css, glossary.css  # Explorer 네비게이션
│   ├── figure-popup.css           # 그림/표 팝업
│   ├── auth.css                   # 인증 UI
│   ├── analytics.css              # 접속 통계 대시보드
│   ├── admin-settings.css         # 관리자 설정 스타일
│   ├── translator.css             # Notebook 뷰어 스타일
│   ├── compare.css                # Verify 전용 스타일
│   └── images/                    # UI 이미지 (로고, 배너 등)
│
├── contents/                      # Explorer HTML 콘텐츠
│
├── Dockerfile                     # Backend 컨테이너 (FastAPI + uvicorn)
├── docker-compose.yml             # 프로덕션 오케스트레이션 (Nginx + Backend)
├── docker-compose.override.yml    # 개발 환경 오버라이드 (bind mount)
├── .env.example                   # 환경 설정 템플릿 (PORT, OLLAMA_URL 등)
├── docker/                        # Docker 관련 설정
│   ├── Dockerfile.nginx           # Nginx 리버스 프록시 컨테이너
│   ├── nginx.conf                 # 프로덕션 Nginx 설정
│   └── nginx.dev.conf             # 개발 Nginx 설정
├── deploy.sh                      # 전체 이미지 배포 스크립트 (COMPOSE_FILE 고정 — Plan-31 방어선)
└── patch-apply.sh                 # 패치(소규모 코드) 적용 스크립트 (Plan-31 방어선 동일)
```

> Plan-37 Converter 통합 이후 `tools/converter/` 는 `preprocess/` 패키지(word_com / libreoffice / native 어댑터) + `numbering_resolver.py` + `omml_to_mathml.py` 를 포함하는 엔진 SSOT 이며, `tools/docx2html-standalone/` 은 이 엔진을 얇게 래핑한 EXE 배포판입니다. 상세: [13-CONVERTER-ARCHITECTURE](13-CONVERTER-ARCHITECTURE.md).

---

## 4. API 설계

### 4.1 검색 API

```
POST /api/search
Content-Type: application/json

Request:
{
    "query": "BM25 하이브리드 검색",
    "top_k": 5,
    "search_type": "auto"  // "keyword", "vector", "hybrid", "auto"
}

Response:
{
    "results": [
        {
            "title": "문서 제목",
            "content": "관련 내용...",
            "path": "contents/page.html",
            "section_id": "section-1-2",
            "score": 0.85
        }
    ],
    "search_type": "keyword",
    "total": 5
}
```

### 4.2 채팅 API

```
POST /api/chat
Content-Type: application/json

Request:
{
    "question": "KF-21의 주요 특징은?",
    "context": [                          // 선택: 프론트엔드 검색 결과
        {
            "title": "프로그램 소개",
            "content": "...",
            "path": "contents/dev-overview/introduction.html",
            "section_id": "section-1"
        }
    ],
    "conversation_id": "a1b2c3d4e5f6g7h8"  // 선택: 멀티턴 세션 ID
}

Response:
{
    "answer": "KF-21의 주요 특징은...",
    "sources": [
        {
            "title": "프로그램 소개",
            "path": "contents/dev-overview/introduction.html",
            "section_id": "section-1"
        }
    ],
    "model": "gemma3:27b",
    "conversation_id": "a1b2c3d4e5f6g7h8"   // 세션 추적용
}
```

**멀티턴 대화 동작:**
- `conversation_id` 미전달 → 새 세션 생성, 응답에 ID 포함
- `conversation_id` 전달 → 기존 세션 조회, 대화 기록 활용
- `context` 미전달 + 백엔드 모드 → 질문 라우팅 + 쿼리 재작성/분해 + 검색
- `context` 전달 → 프론트엔드 검색 결과 사용 (직접 호출 모드)

**스트리밍 채팅 API:**
```
POST /api/chat/stream
→ NDJSON 스트리밍 응답
{"type": "token", "content": "답변 토큰"}
...
{"type": "done", "sources": [...], "confidence": "high", "route": "SIMPLE"}
```

**피드백 API:**
```
POST /api/chat/feedback
{"question": "...", "answer": "...", "feedback": "positive"}
```

### 4.3 인증 API

**권한 분류:**

| 기능 | 권한 | 비고 |
|------|------|------|
| 콘텐츠 열람, 검색, AI 채팅, 북마크, 테마, 용어집 | 공개 | 로그인 불필요 |
| 문서 업로드 (`POST /api/document-submit`) | admin | httponly 쿠키 인증 |
| 문서 편집/저장 (`POST /api/save-document`) | admin | |
| 백업 복원 (`POST /api/restore-document`) | admin | |
| 인덱스 재생성 (`POST /api/reindex`) | admin | |
| 사용자 관리 (`/api/auth/users/*`) | admin | |

**엔드포인트:**

```
POST /api/auth/login       — 로그인 → httponly 쿠키 설정
POST /api/auth/logout      — 세션 삭제 → 쿠키 삭제
GET  /api/auth/me          — 현재 세션 사용자 정보 (null이면 미로그인)
GET  /api/auth/users       — 사용자 목록 (admin)
POST /api/auth/users       — 사용자 생성 (admin)
PUT  /api/auth/users/{id}  — 사용자 수정 (admin)
DELETE /api/auth/users/{id} — 사용자 삭제 (admin, 본인 불가)
```

**기술 구현:**
- DB: SQLite (`data/auth.db`) — Python 기본 내장, 설치 불필요
- 비밀번호: `hashlib.pbkdf2_hmac` (SHA-256, 260,000 iterations)
- 세션: httponly 쿠키 (`session_token`) + DB sessions 테이블
- 프론트엔드: `body.auth-admin` CSS 클래스 토글로 관리 기능 표시/숨김
- CLI: `python tools/create-admin.py`로 서버 없이 직접 계정 생성 (초기 세팅, 비상 복구)

### 4.4 문서 저장 API

```
POST /api/save-document
Content-Type: application/json

Request:
{
    "path": "contents/dev-overview/introduction.html",
    "content": "<h1>제목</h1><p>내용...</p>",
    "createBackup": true
}

Response:
{
    "success": true,
    "message": "Document saved successfully",
    "backupPath": "backups/introduction_20250209_143052.bak"
}
```

### 4.5 문서 업로드/변환 API

```
POST /api/document-submit
Content-Type: multipart/form-data

Request:
  file: Word(.docx) 또는 PDF(.pdf) 파일
  target_path: "contents/dev-overview/document.html"
  menu_path: '["개발 개요", "히스토리"]'  (선택, JSON 배열 문자열)

Response:
{
    "success": true,
    "message": "변환 완료, 메뉴 갱신됨 (인덱스 갱신 완료: 128건)",
    "output_path": "contents/dev-overview/document.html",
    "stats": { "images": 15, "tables": 8, "unextractable_shapes": 1 },
    "warnings": ["Word 도형/그리기 1개가 이미지로 변환되지 않았습니다. ..."]
}
```

### 4.6 인덱스 재생성 API

```
POST /api/reindex

Response:
{
    "success": true,
    "message": "인덱스 재생성 완료",
    "indexed_count": 128
}
```

### 4.7 헬스체크 API

```
GET /api/health

Response:
{
    "status": "ok",
    "ollama": "connected",
    "search_index": "loaded",
    "vector_index": "not_available"
}
```

### 4.8 메뉴 관리 API

```
GET /api/menu  🔒 admin
→ 콘텐츠 메뉴 트리 반환 (시스템 항목 제외)

Response:
{
    "menu": [
        { "label": "개발 개요", "children": [...] },
        ...
    ]
}

POST /api/menu  🔒 admin
Content-Type: application/json
Body: [ { "label": "...", "url": "...", "children": [...] }, ... ]

→ 콘텐츠 메뉴 트리 저장 (시스템 항목 자동 보존)

Response:
{ "success": true }
```

- 시스템 항목(홈/용어집/정보)은 서버에서 자동 보존
- GET 시 시스템 항목을 제거한 콘텐츠만 반환
- POST 시 홈 → [클라이언트 콘텐츠] → 용어집/정보 순으로 재조립
- 원자적 저장: tmp 파일 → rename

### 4.9 Verify(Compare) API

```
POST /api/compare/upload            — DOCX/PDF 텍스트 추출 (파일 저장 없음)
POST /api/compare/extract-document  — 문서 텍스트 추출
POST /api/compare/validate          — 규칙 기반 검증 → 이슈 목록
GET  /api/compare/rules             — 규칙 설정 조회
PUT  /api/compare/rules             — 규칙 설정 저장 (admin) 🔒
GET  /api/compare/rule-definitions  — 규칙 정의 목록 조회
POST /api/compare/ai-classify       — AI 의미 분류 (Ollama 구조화 출력)
POST /api/compare/similarity        — 유사도 검사 (Winnowing + 시맨틱 임베딩)
POST /api/compare/export            — 검토 리포트 내보내기 (XLSX/HTML/TXT)
GET  /api/compare/history           — 세션 이력 조회
POST /api/compare/history           — 세션 이력 저장
```

> **상세**: [11-VERIFY-SYSTEM.md](11-VERIFY-SYSTEM.md) 참조 (비교·유사도·규칙 검증 통합 문서)

### 4.10 Notebook(Translator) API

Notebook 시스템은 PDF 번역 외에 문서 분석(추출/요약/마인드맵), Q&A 챗봇, Markdown 편집 기능을 제공합니다.

| 카테고리 | 주요 엔드포인트 | 설명 |
|----------|----------------|------|
| 폴더 관리 | `GET/POST/PUT/DELETE /api/translator/folders` | 개인 폴더 CRUD |
| 문서 관리 | `POST /upload`, `GET /documents`, `PUT/DELETE /document/{id}` | PDF 업로드, 목록, 이름변경, 삭제 |
| PDF 번역 | `POST /translate/{id}/page/{n}`, `/pages` | pdf2zh 페이지별/범위 번역 |
| 웹 뷰 번역 | `POST /web-translate/{id}/page/{n}` | Markdown 추출+번역 |
| 문서 추출 | `POST /extract/{id}`, `GET /extracted-view/{id}/*` | 번역 없이 Markdown 추출 |
| AI 요약 | `POST/GET /document/{id}/summary` | 크기 적응형 AI 요약 생성/조회 |
| 마인드맵 | `GET /document/{id}/mindmap` | Markmap INode 트리 |
| Q&A 챗봇 | `POST /document/{id}/chat/stream` | NDJSON 스트리밍 Q&A |
| 편집 | `PUT /web-view/{id}/page/{n}` | Markdown 편집 저장 |
| 마킹 | `GET/POST/PUT/DELETE /document/{id}/annotations` | 형광펜 마킹 CRUD |
| 용어집 | `GET/PUT /glossary` | 개인 용어집 관리 |
| 다운로드 | `GET /document/{id}/download/zip` | ZIP 일괄 다운로드 |
| 검색 | `GET /search` | 사용자 문서 내 키워드 검색 |
| AI 선택 | `POST /ai/selection` | 텍스트 선택 → 번역/요약/마킹 |
| 모델 | `GET /models` | Ollama 사용 가능 모델 목록 |

> **상세**: [07-TRANSLATOR-SYSTEM.md](07-TRANSLATOR-SYSTEM.md#4-백엔드-api) 참조

---

## 5. 배포 절차

### 5.1 개발환경에서 패키징 (인터넷 있음)

```bash
# 1. 백엔드 폴더 생성 및 이동
cd smart-document-platform
mkdir -p backend/packages

# 2. requirements.txt 생성
cat > backend/requirements.txt << EOF
fastapi==0.109.0
uvicorn==0.27.0
requests==2.31.0
python-multipart==0.0.6
EOF

# 3. 오프라인 설치용 패키지 다운로드
cd backend
pip download -r requirements.txt -d ./packages/

# 4. 전체 프로젝트 압축
cd ../..
zip -r kf21-webbook-with-backend.zip smart-document-platform/
```

### 5.2 Windows 서버 배포 (폐쇄망)

```cmd
:: 1. 압축 해제
:: kf21-webbook-with-backend.zip을 원하는 위치에 압축 해제

:: 2. 웹북을 Tomcat에 배포 (기존과 동일)
xcopy /E /I /Y smart-document-platform\* C:\apache-tomcat-7.0.77\webapps\ROOT\

:: 3. 백엔드 패키지 설치
cd C:\apache-tomcat-7.0.77\webapps\ROOT\backend
pip install --no-index --find-links=./packages/ -r requirements.txt

:: 4. 설치 확인
pip list | findstr fastapi
```

### 5.3 서비스 실행

#### 실행 순서

```
1. [Linux] Ollama 실행 확인
   $ ollama list
   $ ollama serve  # 필요시

2. [Windows] FastAPI 백엔드 실행
   > cd C:\apache-tomcat-7.0.77\webapps\ROOT\backend
   > python main.py
   # 또는
   > uvicorn main:app --host 0.0.0.0 --port 8000

3. [Windows] Tomcat 실행
   > C:\apache-tomcat-7.0.77\bin\startup.bat

4. 브라우저 접속
   http://localhost:8080
```

#### 배치 파일 (선택)

`start-backend.bat` 생성:
```cmd
@echo off
cd /d C:\apache-tomcat-7.0.77\webapps\ROOT\backend
python main.py
pause
```

---

## 6. 동작 모드

AI 채팅은 두 가지 모드로 동작할 수 있으며, `js/config.js`의 `useBackend` 설정으로 전환합니다.

### 6.1 모드 비교

| 항목 | 백엔드 모드 (`useBackend: true`) | 직접 호출 모드 (`useBackend: false`) |
|------|----------------------------------|--------------------------------------|
| 호출 경로 | 프론트엔드 → 백엔드 → Ollama | 프론트엔드 → Ollama 직접 |
| 설정 위치 | `backend/config.py` | `js/config.js` |
| 검색 방식 | 백엔드 API (`/api/search`) | 로컬 인덱스 (브라우저) |
| 확장성 | Phase 2, 3 확장 가능 | 기본 기능만 |
| 권장 환경 | 운영 서버 | 로컬 테스트 |

### 6.2 동일 품질 보장

두 모드는 동일한 답변 품질을 보장합니다:

| 항목 | 설정 값 |
|------|--------|
| 시스템 프롬프트 | 동일 (KF-21 기술문서 어시스턴트) |
| 컨텍스트 길이 제한 | 8000자 (백엔드), 4000자 (직접 호출) |
| 검색 결과 개수 | 5개 |
| 프롬프트 형식 | 동일 (`=== 참고 문서 ===`, `=== 질문 ===`) |

### 6.3 백엔드 모드 설정 (`useBackend: true`)

**js/config.js:**
```javascript
const AI_CONFIG = {
    useBackend: true,
    backendUrl: 'http://localhost:8000',
    // 아래 설정은 백엔드에서 관리
    maxContextLength: 8000,
    maxSearchResults: 5
};
```

**backend/config.py:**
```python
OLLAMA_URL = "http://localhost:11434"  # 또는 Linux 서버 IP
OLLAMA_MODEL = "gemma3:27b"
MAX_CONTEXT_LENGTH = 8000
MAX_SEARCH_RESULTS = 5
```

### 6.4 직접 호출 모드 설정 (`useBackend: false`)

**js/config.js:**
```javascript
const AI_CONFIG = {
    useBackend: false,
    ollamaUrl: 'http://localhost:11434',
    model: 'gemma3:27b',
    maxContextLength: 4000,  // 직접 호출 모드는 싱글턴 (검색 결과만 전달)
    maxSearchResults: 5,
    systemPrompt: `...`  // 시스템 프롬프트 (백엔드와 동일)
};
```

### 6.5 데이터 흐름

**백엔드 모드:**
```
사용자 질문
    ↓
requestViaBackend() → POST /api/chat/stream (question + conversation_id)
    ↓
백엔드 내부:
    질문 라우팅 (SIMPLE/COMPARE/REASON/CHAT)
    → 쿼리 재작성 → 쿼리 분해(COMPARE) 또는 Agentic RAG(REASON)
    → 하이브리드 검색 → 리랭킹 → LLM 스트리밍 (기록 포함)
    ↓
NDJSON 토큰 스트리밍 → rAF 렌더링 → 응답 표시 (참고 링크, conversation_id 유지)
```

**직접 호출 모드:**
```
사용자 질문
    ↓
searchLocally() → 로컬 search-index.json 검색
    ↓
requestViaOllama() → Ollama /api/generate 직접 호출
    ↓
응답 표시 (참고 링크 포함)
```

---

## 7. 구현 현황 (요약)

주요 기능은 모두 완료 상태. **세부 진화 과정·기술 근거**는 다음 문서를 참조:

| 기능군 | 참조 문서 | 핵심 기술 |
|--------|-----------|-----------|
| AI 채팅 · 검색 | [06-RAG-PIPELINE](06-RAG-PIPELINE.md) · [RAG-TECHNICAL-REPORT](RAG-TECHNICAL-REPORT.md) | 하이브리드 검색(RRF) · Cross-encoder 리랭킹 · 질문 라우팅 · Agentic RAG · LLM 프로바이더 추상화 |
| Notebook (Translator) | [07-TRANSLATOR-SYSTEM](07-TRANSLATOR-SYSTEM.md) | PDF 페이지 번역 · 웹뷰 MD · AI 요약·마인드맵·Q&A · Monaco 편집기 |
| Verify (Compare) | [11-VERIFY-SYSTEM](11-VERIFY-SYSTEM.md) | 듀얼 diff · AI 의미 분류 · Winnowing+bge-m3 유사도 · 21종 규칙 · Acrolinx 스코어링 |
| DOCX→HTML 변환기 | [13-CONVERTER-ARCHITECTURE](13-CONVERTER-ARCHITECTURE.md) | 엔진 SSOT + 전처리 어댑터 체인(Word COM/LibreOffice/Native) · NumberingResolver · STYLEREF+SEQ · OMML→MathML · .docx_1 DRM 우회 |
| 문서 편집 · 참조 팝업 · 북마크 · 단축키 · 배너 · 토스트 | [04-USER-GUIDE](04-USER-GUIDE.md) (사용법) / 본 문서 §9~16 (구현) | 공통 컴포넌트 기반 |

---

## 8. 프론트엔드 렌더링 최적화

대용량 문서(4MB HTML, 100+ 이미지)의 렌더링 성능을 위해 다음 기법을 적용합니다.

### 8.1 content-visibility: auto

`app.js`의 `optimizeContent()` 함수가 콘텐츠 로드 시 자동으로 적용:

1. **이미지 비동기 디코딩**: 모든 `<img>`에 `decoding="async"` 속성 부여
2. **섹션 래핑**: h1/h2 기준으로 `<div class="content-section">`으로 감싸기
3. **CSS 최적화**: `.content-section`에 `content-visibility: auto` + `contain-intrinsic-size: auto 500px` 적용

```css
.content-section {
    content-visibility: auto;
    contain-intrinsic-size: auto 500px;
}
```

### 8.2 반복 수렴 스크롤 (scrollToElementReliably)

`content-visibility: auto`는 미렌더링 섹션의 높이를 추정값(500px)으로 대체하므로, 일반적인 `scrollIntoView`가 목표 위치를 놓칠 수 있습니다. 이를 해결하기 위해 **반복 수렴 방식**을 사용합니다:

```
instant scrollIntoView → 주변 섹션 렌더링 → 위치 재확인 → 수렴할 때까지 반복 (2~3프레임)
```

- TOC 클릭, 검색 결과 이동, AI 채팅 링크 등 모든 섹션 네비게이션에 적용
- `content-visibility`를 건드리지 않으므로 렌더링 최적화 이점 유지
- `getBoundingClientRect()`를 사용한 동적 위치 계산 (캐싱된 `offsetTop` 미사용)

### 8.3 URL 파라미터 페이지 접근

`?page=` 쿼리 파라미터로 특정 문서에 직접 접근할 수 있습니다:

```
http://localhost:8080/?page=contents/samples/SWA_PMS/SWA_PMS.html
```

- 메뉴 클릭 시 `updatePageUrl()`로 URL 업데이트 (브라우저 히스토리 지원)
- 초기 로드 시 `loadPageFromUrl()`로 파라미터 확인 → 해당 페이지 로드
- 파라미터 없으면 기본 홈 페이지(`contents/home.html`) 로드

### 8.4 캐시 버스팅

편집기로 문서 수정 후 즉시 반영을 위해 `fetch()` 호출 시 타임스탬프 파라미터:

- 콘텐츠 로드: `fetch(url + '?t=' + Date.now())`
- 검색 인덱스: `fetch('data/search-index.json?t=' + Date.now())`

### 8.5 배너 이미지 프리로드

첫 번째 배너 이미지를 `<link rel="preload">`로 사전 로드하고, 이미지 로드 완료 시 페이드인 트랜지션 적용:

```html
<link rel="preload" href="css/images/1-1_KF-21.jpg" as="image">
```

### 8.6 인쇄 지원

`@media print`에서 모든 섹션을 `content-visibility: visible`로 전환하여 인쇄 시 전체 콘텐츠가 표시됩니다.

---

## 9. 다크/라이트 모드

헤더 nav 영역의 해/달 아이콘 버튼으로 다크/라이트 테마를 전환합니다.

### 9.1 구현 방식

| 항목 | 설명 |
|------|------|
| 디자인 토큰 | `css/tokens.css`에 라이트/다크 CSS 변수 통합 관리, 글로벌 `:focus-visible` 포커스 링 |
| 테마 전환 | `body[data-theme="dark"]`에서 `:root` CSS 변수 오버라이드 |
| 저장 | `localStorage.getItem('theme')` — `'light'` 또는 `'dark'` |
| 기본값 | 라이트 모드 (저장된 값 없으면) |
| 초기화 | `initTheme()` — `js/app.js`에서 `initializeApp()` 초반 호출 |
| 인쇄 | `@media print`에서 라이트 색상 변수 강제 복원 |

### 9.2 CSS 변수 오버라이드 팔레트

다크 모드는 중립 그레이 계열 (`#121218` ~ `#2d2f3e`)을 사용합니다. 네이비 톤이 아닌 무채색 기반으로 장시간 읽기에 편안합니다.

### 9.3 주의사항

- `--white`, `--primary-navy` 등이 배경과 텍스트 양쪽에 쓰이므로, 텍스트 용도에는 별도 오버라이드 필요
- 다크 모드 이미지: 투명 배경 보호를 위해 `background-color: #ffffff` + `padding: 4px` 적용 (배너 제외)
- DOCX 변환 시 인라인 `style="color:..."` 값은 CSS 변수를 사용하지 않으므로, 특정 색상이 다크 배경에서 보이지 않을 수 있음

---

## 10. 북마크

자주 참조하는 섹션을 저장하고 빠르게 이동할 수 있는 기능입니다. SPA 구조이므로 **문서 경로 + 섹션 ID** 단위로 북마크하며, localStorage에 저장되어 서버 없이 동작합니다.

### 10.1 관련 파일

| 파일 | 역할 |
|------|------|
| `js/bookmarks.js` | 북마크 CRUD, 오버레이 UI, 헤딩 아이콘 주입, 네비게이션 |
| `css/bookmarks.css` | 오버레이 + 헤딩 북마크 아이콘 스타일 (다크 모드 포함) |
| `index.html` | nav에 Bookmarks 버튼, 오버레이 DOM 컨테이너 |
| `js/app.js` | `initBookmarks()` 호출, 콘텐츠 로드 후 `injectBookmarkIcons()` 호출 |

### 10.2 데이터 구조

```javascript
// localStorage key: 'webbook-bookmarks'
[
  {
    id: 1708123456789,                          // Date.now() (고유 ID)
    pagePath: "contents/samples/MyPaper/MyPaper.html",
    pageTitle: "MyPaper",
    sectionId: "3.1-하이브리드-검색-구조",
    sectionTitle: "3.1 하이브리드 검색 구조",
    timestamp: "2026-02-17T20:30:00"
  }
]
```

### 10.3 동작 원리

1. **아이콘 주입** (`injectBookmarkIcons`): 콘텐츠 로드 완료 시 `updateSectionNav()` 뒤에 호출. ID가 있는 h1~h4 헤딩에 `<span class="bookmark-icon">` 삽입
2. **토글** (`toggleBookmark`): 아이콘 클릭 시 해당 헤딩의 북마크 추가/제거 → localStorage 갱신 → 아이콘 상태 변경 (☆ ↔ ★)
3. **오버레이** (`renderBookmarksList`): 헤더 Bookmarks 클릭 시 오버레이 열림. 문서별(pageTitle)로 그룹핑하여 목록 표시
4. **네비게이션** (`navigateToBookmark`): 같은 문서 → `scrollToElementReliably()` 직접 호출, 다른 문서 → `window._pendingScrollToSection` + `loadContent()` (기존 패턴)
5. **전체 삭제**: 오버레이 헤더의 "Clear All" 버튼으로 모든 북마크 초기화 (confirm 확인)

---

## 11. 항공 용어집

26,000+ 항공 용어의 검색/탐색 및 본문 약어 자동 인식 시스템입니다.

### 11.1 관련 파일

| 파일 | 역할 |
|------|------|
| `js/glossary.js` | 용어집 페이지 렌더링, 검색, 본문 약어 하이라이트, 클릭 팝업 |
| `css/glossary.css` | 용어집 페이지/팝업/점선 밑줄 스타일 (다크 모드 포함) |
| `data/glossary.json` | 용어 데이터 (`[{abbr, en, ko}, ...]`) |
| `data/glossary.csv` | CSV 원본 (관리용, UTF-8 BOM) |
| `tools/import-glossary.py` | CSV → JSON 변환 스크립트 |

### 11.2 아키텍처

```
┌─ 용어집 페이지 ─────────────────────────────────────┐
│  loadContent('glossary:terms')                      │
│    → initGlossary() → glossary.json fetch (1회)     │
│    → renderGlossaryPage() → A-Z 카드 / 테이블       │
│    → updateGlossaryNav() → 우측 패널 A-Z 퀵링크     │
└─────────────────────────────────────────────────────┘

┌─ 본문 약어 하이라이트 ──────────────────────────────┐
│  콘텐츠 로드 완료                                    │
│    → highlightGlossaryTermsInContent()              │
│    → IntersectionObserver (rootMargin: 200px)       │
│    → 뷰포트 진입 섹션만 processGlossaryTermsInElement() │
│      → TreeWalker + /[A-Z]{2,}/ 사전 필터           │
│      → _glossaryAbbrSet (Set, O(1)) 매칭            │
│      → <span class="glossary-term"> 래핑            │
│    → 클릭 시 showGlossaryLookup() 팝업 표시         │
└─────────────────────────────────────────────────────┘

┌─ 통합 검색 연동 ────────────────────────────────────┐
│  performSearch(query)                               │
│    → searchGlossary(query) → abbr/en/ko 매칭        │
│    → displaySearchResults() → 용어집 그룹 (상단 3건) │
│    → 클릭 → loadGlossaryFromSearch()                │
│      → _pendingGlossaryQuery 패턴으로 상태 전달      │
└─────────────────────────────────────────────────────┘
```

### 11.3 성능 설계

대용량 문서(400+ 페이지, 4MB HTML)에서의 성능을 위해:

- **지연 처리**: `IntersectionObserver`로 뷰포트 근처 섹션만 처리 (전체 스캔 안 함)
- **사전 필터**: `/[A-Z]{2,}/` 정규식으로 대문자 연속이 있는 텍스트 노드만 수집
- **O(1) 조회**: `Set`에 약어를 저장하여 상수 시간 매칭
- **중복 방지**: `data-glossary-processed` 속성으로 처리 완료 섹션 스킵
- **`content-visibility: auto` 호환**: 같은 지연 처리 철학 — off-screen 섹션 건너뜀

### 11.4 데이터 관리 파이프라인

```
Excel/한셀 편집 → glossary.csv (UTF-8 BOM) → import-glossary.py → glossary.json
```

- CSV 헤더: `abbr,en,ko` (abbr, en 필수)
- 자동 정렬: abbr 기준 알파벳 오름차순
- 중복 감지: (abbr, en) 쌍 기준, 경고 출력 후 스킵

---

## 12. 문서 변환 파이프라인 (프론트엔드 연동 개요)

DOCX/PDF → HTML 변환 엔진 전체 아키텍처(전처리 어댑터 체인, NumberingResolver, STYLEREF+SEQ, OMML→MathML, DRM 우회)는 [13-CONVERTER-ARCHITECTURE](13-CONVERTER-ARCHITECTURE.md) 참조. 여기서는 변환 결과가 **프론트엔드에서 어떻게 활용되는지** 만 다룹니다.

### 12.1 그림/표 참조 팝업

| 파일 | 역할 |
|------|------|
| `css/figure-popup.css` | 모달 오버레이, 참조 링크 스타일 |
| `js/figure-popup.js` | 이벤트 위임 기반 팝업 로직 |
| `index.html` | 모달 DOM 컨테이너 (`#figure-popup-overlay`) |

### 12.2 마크업 규칙

변환기가 자동 생성하는 HTML 은 다음 두 가지 규칙을 따릅니다:

```html
<!-- 캡션: id 접두어 "fig-" / "tbl-" -->
<p id="fig-1"><strong>Figure 1 – 시스템 구성도</strong></p>
<p><img src="images/system.png" alt=""></p>

<!-- 본문 참조: data-fig-ref 속성 -->
<p>시스템 구성은 <a data-fig-ref="fig-1">Figure 1</a>에 나타나 있다.</p>
```

| 유형 | 접두어 | 예시 |
|------|--------|------|
| 그림 (Figure/그림) | `fig-` | `fig-1`, `fig-2-1` |
| 표 (Table/표) | `tbl-` | `tbl-1`, `tbl-2` |

### 12.3 JS 동작 원리

1. **이벤트 위임**: `#main-content`에 단일 클릭 리스너 등록 → 동적 로드된 콘텐츠에도 자동 적용
2. **콘텐츠 탐색**: `data-fig-ref` 값으로 대상 요소(`id`)를 찾고, 해당 요소 내부 또는 인접(±3 형제)에서 `img`/`table` 추출
3. **캡션 추출**: 인접 요소에서 "Figure/Table/그림/표 + 숫자" 패턴 자동 감지
4. **모달 표시**: 추출된 이미지/표를 모달에 복제하여 표시
5. **닫기**: ESC 키, 배경 클릭, X 버튼

### 12.4 팝업 콘텐츠 탐색 (`extractFigureContent`)

캡션 요소(`id`)를 기준으로 이미지/표를 찾는 양방향 탐색 로직:

1. 요소 자체가 `<img>` 또는 `<table>` 인 경우 → 즉시 사용
2. 요소 내부에서 `<img>` 또는 `<table>` 탐색
3. **양방향 형제 탐색**: 이전/다음 각 3개 형제까지 탐색, 가장 가까운 후보 선택
   - Word 에서 캡션이 표 아래/이미지 위 어느 쪽에 오든 대응

---

## 13. 배너 슬라이드쇼

홈페이지 상단의 배너 슬라이드쇼는 이미지와 영상을 혼합하여 표시합니다.

### 13.1 관련 파일

| 파일 | 역할 |
|------|------|
| `js/banner.js` | 슬라이드쇼 초기화, 전환 로직, 섹션 링크 생성 |
| `js/config.js` | `DISPLAY_CONFIG.version` (푸터 버전 표시) |
| `css/content.css` | 배너 스타일, Ken Burns 애니메이션, 통계 스트립 |
| `contents/home.html` | 배너 컨테이너, 섹션 링크 컨테이너 |

### 13.2 슬라이드 타입

| 타입 | 설명 | 효과 |
|------|------|------|
| `image` | 정적 이미지 (JPG/PNG) | Ken Burns 효과 (확대/이동 애니메이션) |
| `video` | MP4 영상 | 자동 재생, 음소거, 루프 |

### 13.3 Ken Burns 효과

이미지 슬라이드에는 CSS `@keyframes` 기반 Ken Burns 효과가 적용됩니다:
- `scale(1.0)` → `scale(1.1)` + 위치 이동으로 자연스러운 시각 효과
- 영상 슬라이드에는 미적용 (영상 자체 모션)

### 13.4 홈페이지 구성 요소

- **배너 슬라이드쇼**: 상단 영역, 뷰포트 적응형 높이
- **통계 스트립**: 문서 수, 이미지 수, 용어 수 등 핵심 통계 표시
- **섹션 카드 그리드**: `menu.json` 1레벨 항목에서 자동 생성, 트리 메뉴와 연동

---

## 14. 키보드 단축키 (구현)

키 일람표 및 사용자 관점 설명은 [04-USER-GUIDE § 키보드 단축키](04-USER-GUIDE.md#키보드-단축키) 참조.

**구현 파일**: `js/keyboard.js` · `css/main.css`(`.shortcuts-overlay`)

**핵심 원칙**:
- IIFE 패턴, `DOMContentLoaded` 초기화
- 입력 필드(`INPUT`, `TEXTAREA`, `contentEditable`) 활성 시 단축키 비활성
- 오버레이(검색·북마크·팝업) 열려 있으면 단축키 무시
- 문서 이동: `navigateDocument(±1)` — `AppState.menuData` 평탄화 → 현재 위치 기준 이전/다음 문서 로드

---

## 15. 브레드크럼 내비게이션

현재 문서의 메뉴 경로를 상단에 표시하여 위치 파악과 상위 메뉴 이동을 지원합니다.

### 15.1 동작 방식

1. **경로 추출**: `AppState.menuData`에서 현재 페이지의 메뉴 경로를 역추적
2. **렌더링**: `#breadcrumb` 요소에 `홈 > 상위메뉴 > 현재문서` 형태로 표시
3. **클릭 이동**: 각 경로 항목 클릭 시 해당 메뉴의 첫 번째 문서로 이동
4. **홈 페이지**: 홈에서는 브레드크럼 숨김

---

## 16. 토스트 알림

사용자 작업 결과를 하단 중앙에 일시적으로 표시하는 공용 알림 시스템입니다.

### 16.1 구현 위치

| 파일 | 역할 |
|------|------|
| `js/app.js` | `showToast(message, type)` — Explorer용 공용 함수 |
| `js/toast.js` | `showToast(message, type)` — Translator/Compare용 독립 모듈 |
| `css/toast.css` | `.toast` 스타일 (위치, 애니메이션, 타입별 색상) |

### 16.2 API

```javascript
showToast(message, type)
// type: 'success' | 'error' | 'warning' | 생략(기본 info)
```

- **싱글턴 DOM**: `#app-toast` 요소를 lazy 생성, 재사용
- **연속 호출 대응**: `clearTimeout`으로 이전 타이머 리셋, 메시지만 교체
- **자동 사라짐**: 3초 후 페이드아웃
- **z-index: 5000**: 모든 오버레이 위에 표시
- **pointer-events: none**: 토스트가 클릭을 방해하지 않음

### 16.3 사용처

| 모듈 | 상황 | 타입 |
|------|------|------|
| `editor.js` | 문서 저장 성공/실패 | success / error |
| `tree-menu.js` | 파일 업로드 성공/실패, 메뉴 갱신, 인덱스 재생성 | success / error |
| `keyboard.js` | 첫 번째/마지막 문서 도달 | info (기본) |
| `bookmarks.js` | 북마크 추가/제거 | info (기본) |

---

## 17. 문제 해결

### 백엔드 서버가 시작되지 않음

```cmd
:: 포트 사용 확인
netstat -ano | findstr :8000

:: Python 패키지 확인
pip list | findstr fastapi
pip list | findstr uvicorn
```

### Ollama 연결 실패

```cmd
:: Windows에서 Linux 서버 연결 테스트
curl http://<linux-server-ip>:11434/api/tags

:: 방화벽 확인 (Linux)
sudo firewall-cmd --list-ports
sudo firewall-cmd --add-port=11434/tcp --permanent
```

### CORS 오류

백엔드에서 CORS 설정 확인:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 또는 특정 origin
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 18. 관련 문서

- [06-RAG-PIPELINE.md](06-RAG-PIPELINE.md): 검색/AI 기술 상세 (청킹, 임베딩, 검색 전략)
- [RAG-TECHNICAL-REPORT.md](RAG-TECHNICAL-REPORT.md): RAG 답변 품질 개선 기술 보고서
- [01-DEPLOYMENT-GUIDE.md](01-DEPLOYMENT-GUIDE.md): 환경 3종 통합 배포 가이드
- [03-DOCKER-OPERATIONS.md](03-DOCKER-OPERATIONS.md): Docker 배포·운영 심화
- [07-TRANSLATOR-SYSTEM.md](07-TRANSLATOR-SYSTEM.md): Translator 시스템 설계 (API, 데이터 구조, 번역 파이프라인)
- [11-VERIFY-SYSTEM.md](11-VERIFY-SYSTEM.md): Verify 시스템 설계 (비교·유사도·규칙 검증·리포트)
- [04-USER-GUIDE.md](04-USER-GUIDE.md): 콘텐츠 관리, 검색 인덱스 업데이트
