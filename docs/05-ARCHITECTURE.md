# Backend Architecture

AI 챗봇 + 문서 편집기 백엔드 시스템 설계 및 배포 문서

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

```
┌─────────────────────────────────────────────────────────────┐
│  가상 Windows PC (웹북 서버)                                  │
│                                                             │
│  ┌─────────────────┐    ┌─────────────────────────────┐    │
│  │  Tomcat:8080    │    │  FastAPI Backend:8000       │    │
│  │  ---------------│    │  ---------------------------│    │
│  │  - index.html   │───▶│  POST /api/search           │    │
│  │  - js/*.js      │    │  POST /api/chat             │    │
│  │  - css/*.css    │    │  POST /api/save-document 🔒 │    │
│  │  - contents/*   │    │  POST /api/upload        🔒 │    │
│  └─────────────────┘    │  POST /api/reindex       🔒 │    │
│                         │  /api/auth/* (login/users)   │    │
│                         │  POST /api/analytics/*  통계 API              │    │
│                         │  GET/POST /api/settings 설정 API (admin) 🔒   │    │
│                         │  GET/POST /api/menu    메뉴 관리 (admin) 🔒   │    │
│                         │  /api/translator/*     Translator API          │    │
│                         │  /api/translator/ai/*  AI 번역/요약 API        │    │
│                         │                              │    │
│                         │  Services:                   │    │
│                         │  - Auth (SQLite sessions)    │    │
│                         │  - KeywordSearch             │    │
│                         │  - VectorSearch (FAISS)      │    │
│                         │  - EmbeddingClient (bge-m3)  │    │
│                         │  - Reranker (Cross-encoder)  │    │
│                         │  - ConversationStore         │    │
│                         │  - QueryRewriter             │    │
│                         │  - QuestionRouter (4유형 분류)│    │
│                         │  - QueryDecomposer (쿼리 분해)│    │
│                         │  - RAGAgent (반복 검색-판단)  │    │
│                         │  - LLMProvider (Ollama/OpenAI)│    │
│                         │  - LLMClient (응답 생성 래퍼) │    │
│                         │  - KoreanTokenizer           │    │
│                         │  - DocumentSave              │    │
│                         │  - SettingsService (settings.json)  │    │
│                         │  - Analytics (heartbeat/dashboard)  │    │
│                         └──────────────┬──────────────┘    │
│                                        │                    │
│  설치 항목:                             │                    │
│  - JDK 1.8                             │                    │
│  - Apache Tomcat 7.0                   │                    │
│  - Python 3.11.9                       │                    │
│  - FastAPI + uvicorn                   │                    │
│  - faiss-cpu, sentence-transformers    │                    │
│                                        │                    │
│  models/bge-reranker-v2-m3/            │                    │
│  (로컬 Cross-encoder 리랭커 모델)      │                    │
└────────────────────────────────────────┼────────────────────┘
                                         │ HTTP (Ollama API)
                                         ▼
┌─────────────────────────────────────────────────────────────┐
│  가상 Linux (GPU 서버)                                       │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Ollama                                             │    │
│  │  - LLM 모델: gemma3:27b                             │    │
│  │  - 임베딩 모델: bge-m3 (1024차원)                    │    │
│  │  - API: http://<server-ip>:11434                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  설치 항목:                                                  │
│  - Ollama                                                   │
│  - LLM 모델 파일 (gemma3:27b)                               │
│  - 임베딩 모델 파일 (bge-m3)                                 │
└─────────────────────────────────────────────────────────────┘
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
| requests | 2.32.3 | Ollama API 호출 |
| python-multipart | 0.0.22 | 파일 업로드 지원 |
| faiss-cpu | ≥1.7.4 | FAISS 벡터 검색 |
| numpy | ≥1.24.0 | 벡터 연산 |
| sentence-transformers | ≥2.2.2 | Cross-encoder 리랭커 |

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
│   │   ├── upload.py              # POST /api/upload, /api/reindex (admin)
│   │   ├── settings.py            # 설정 API (GET/POST /api/settings, /api/settings/public)
│   │   ├── analytics.py           # 통계 API (heartbeat, dashboard)
│   │   └── menu.py                # 메뉴 관리 API (GET/POST /api/menu)
│   │
│   ├── services/                   # 비즈니스 로직
│   │   ├── __init__.py
│   │   ├── auth.py                 # 사용자/세션 관리 (SQLite)
│   │   ├── keyword_search.py       # 키워드 기반 검색
│   │   ├── vector_search.py        # FAISS 벡터 검색 + 하이브리드 RRF 병합
│   │   ├── embedding_client.py     # Ollama bge-m3 임베딩 클라이언트
│   │   ├── reranker.py             # Cross-encoder 리랭킹 (bge-reranker-v2-m3)
│   │   ├── conversation.py         # 인메모리 대화 세션 저장소 (LRU)
│   │   ├── query_rewriter.py       # LLM 기반 쿼리 재작성
│   │   ├── question_router.py      # 질문 유형 분류 (SIMPLE/COMPARE/REASON/CHAT)
│   │   ├── query_decomposer.py     # 복합 쿼리 분해 (1~3개 서브쿼리)
│   │   ├── rag_agent.py            # Agentic RAG 반복 검색-판단 루프
│   │   ├── llm_provider.py         # LLM 프로바이더 추상화 (Ollama/OpenAI 호환)
│   │   ├── llm_client.py           # LLM 응답 생성 래퍼 (동기/스트리밍)
│   │   ├── korean_tokenizer.py     # 한국어 형태소 분석 (kiwipiepy/폴백)
│   │   ├── settings_service.py    # settings.json CRUD, 런타임 config 적용
│   │   └── analytics.py           # 접속 통계 서비스
│   │
│   └── packages/                   # 오프라인 설치용 wheel 파일
│       └── (pip download 결과물)
│
├── data/
│   ├── menu.json                   # 트리 메뉴 구조
│   ├── search-index.json           # 키워드 검색 인덱스
│   ├── auth.db                     # 사용자/세션 SQLite DB (자동 생성)
│   ├── vector-index/               # FAISS 벡터 인덱스
│   │   ├── vector-index.faiss      # FAISS 인덱스 파일
│   │   └── vector-index_meta.json  # 메타데이터 (title, content, url 등)
│   └── translator/                 # Translator 개인 작업공간
│       └── {username}/             # 유저별 디렉토리
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
│   └── converter/                  # 문서 변환기 (DOCX/PDF → HTML, 수식 변환, COM 전처리 포함)
│
├── index.html                     # Explorer (문서 탐색)
├── translator.html                # Translator (논문 번역)
├── launcher.html                  # 런처 (시스템 선택)
├── admin.html                     # 관리자 설정
├── login.html                     # 로그인
│
├── js/
│   ├── platform-header.js         # 공통 헤더 (SVG 시스템 스위처, 호버 드롭다운)
│   ├── platform-footer.js         # 공통 푸터
│   ├── admin-settings.js          # 관리자 설정 GUI
│   ├── analytics.js               # 접속 통계 (heartbeat, 대시보드)
│   ├── app.js                     # Explorer 코어 (로딩, 스크롤, 설정)
│   ├── auth.js                    # 3-role RBAC, 로그인 리다이렉트
│   ├── config.js                  # DISPLAY/AI/EDITOR/UPLOAD/AUTH_CONFIG
│   ├── translator.js              # Translator 뷰어 로직 (PDF.js, 마킹, AI 선택)
│   └── ...                        # (기타 Explorer 모듈)
│
├── css/
│   ├── tokens.css                 # 디자인 토큰 (CSS 변수, 리셋, 글로벌 focus-visible)
│   ├── platform-header.css        # 공통 헤더 스타일
│   ├── platform-footer.css        # 공통 푸터 스타일
│   ├── admin-settings.css         # 관리자 설정 스타일
│   ├── translator.css             # Translator 뷰어 스타일
│   └── ...                        # (기타 스타일)
│
└── contents/                      # Explorer HTML 콘텐츠
```

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
| 문서 업로드 (`POST /api/upload`) | admin | httponly 쿠키 인증 |
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
POST /api/upload
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

## 7. 구현 현황

### AI 채팅 기능

| Phase | 상태 | 주요 내용 |
|-------|------|-----------|
| Phase 1 | ✅ 완료 | 백엔드 구축, 키워드 검색 API |
| Phase 2 | ✅ 완료 | 섹션 레벨 인덱싱, 참조 링크 이동 |
| Phase 3 | ✅ 완료 | 하이브리드 검색, 리랭킹, 멀티턴 대화, 구조 보존 인덱싱 |
| Phase 4 | ✅ 완료 | 질문 라우팅, 쿼리 분해, Agentic RAG, LLM 프로바이더 추상화 |

**Phase 3 세부 항목:**
- FAISS + bge-m3 하이브리드 검색 (RRF 병합, keyword 30% + vector 70%)
- Cross-encoder 리랭킹 (bge-reranker-v2-m3, 로컬 배포)
- 멀티턴 대화 (인메모리 세션, LLM 쿼리 재작성)
- 구조 보존 인덱싱 (테이블→마크다운, 수식→LaTeX)
- 토큰 예산 관리 (8000자), temperature=0
- 예외 처리, 메모리 보호, 타임아웃 강화

**Phase 4 세부 항목:**
- 질문 라우팅 (SIMPLE/COMPARE/REASON/CHAT 4유형 자동 분류)
- 쿼리 분해 (복합 질문 → 1~3개 서브쿼리 병렬 검색)
- Agentic RAG (반복 검색-판단-재검색 루프, 최대 3회)
- LLM 프로바이더 추상화 (Ollama + OpenAI 호환 API)
- 스트리밍 채팅 (NDJSON 토큰 스트리밍, rAF 렌더링 최적화)
- 채팅 UI 개선 (버블 제거, 복사 버튼, 스크롤-투-바텀)
- 한국어 형태소 분석 (kiwipiepy), 피드백 기록

> **기술 상세**: [06-RAG-PIPELINE.md](06-RAG-PIPELINE.md#8-구현-체크리스트) 참조
> **기술 보고서**: [RAG-TECHNICAL-REPORT.md](RAG-TECHNICAL-REPORT.md) 참조

### 문서 편집 기능

| 기능 | 상태 | 설명 |
|------|------|------|
| Monaco 에디터 | ✅ 완료 | HTML 소스 편집 + 실시간 미리보기 |
| 문서 저장 API | ✅ 완료 | HTML 포맷팅 후 저장 |
| 자동 백업 | ✅ 완료 | 저장 전 .bak 파일 생성 |
| 커서 하이라이트 | ✅ 완료 | 편집 위치 미리보기에서 강조 |
| 미리보기 이미지 | ✅ 완료 | 상대 경로 이미지 미리보기 표시 |
| 계정 연동 | 예정 | 권한 기반 편집 제어 |

### 문서 업로드/변환 기능

| 기능 | 상태 | 설명 |
|------|------|------|
| Word 변환 | ✅ 완료 | DOCX → HTML (python-docx) |
| PDF 변환 | ✅ 완료 | PDF → HTML (PyMuPDF) |
| 캡션 자동 ID | ✅ 완료 | Figure/Table/그림/표 캡션에 ID 부여 |
| 참조 링크 생성 | ✅ 완료 | 본문 참조 → `<a data-fig-ref>` 자동 변환 |
| SEQ 필드 처리 | ✅ 완료 | 빈 캐시 값 자동 채번 |
| 수식 변환 | ✅ 완료 | OMML → MathML (18종 요소, 외부 JS 불필요) |
| 하이퍼링크/북마크 | ✅ 완료 | Word 링크 → `<a href>`, 북마크 → `<a id>` |
| 각주/미주 | ✅ 완료 | 본문 참조 + 문서 끝 `<section class="footnotes">` |
| 표 셀 병합 | ✅ 완료 | gridSpan → colspan, vMerge → rowspan (raw XML 기반) |
| 텍스트 색상/하이라이트 | ✅ 완료 | `<span style="color:">`, `<mark>` (검정 스킵) |
| 줄바꿈/탭/페이지 나누기 | ✅ 완료 | `<br>`, `&emsp;`, `<hr class="page-break">` |
| 리스트 변환 | ✅ 완료 | 순서/비순서, 중첩, numFmt 기반 ol/ul 자동 판별 |
| 셀 정렬 보존 | ✅ 완료 | CENTER/RIGHT/JUSTIFY → `style="text-align"` |
| 문단 정렬 | ✅ 완료 | CENTER, RIGHT, JUSTIFY 지원 |
| TOC 자동 스킵 | ✅ 완료 | toc 스타일 문단 제외 (우측 패널이 대체) |
| 테이블 스타일 프리셋 | ✅ 완료 | bordered/simple/minimal (DISPLAY_CONFIG) |
| 이미지 비율 보존 | ✅ 완료 | Word 페이지 대비 % 폭으로 출력 (`style="width: N%"`) |
| 도형/그리기 감지 | ✅ 완료 | 추출 불가 Word 도형 → 플레이스홀더 경고 삽입 |
| menu.json 갱신 | ✅ 완료 | 업로드 시 메뉴 노드 URL 자동 설정 |
| 장절번호 평문화 | ✅ 완료 | COM 전처리로 자동번호 → 텍스트 변환 (Word 필요) |
| 자동 인덱싱 | ✅ 완료 | 업로드 후 검색 인덱스 재생성 |

### 그림/표 참조 팝업

| 기능 | 상태 | 설명 |
|------|------|------|
| 팝업 모달 | ✅ 완료 | 캡션 클릭 시 이미지/표 팝업 표시 |
| 양방향 탐색 | ✅ 완료 | 캡션 위/아래 방향 모두 콘텐츠 탐색 |
| 원본 위치 이동 | ✅ 완료 | 팝업에서 원본 위치로 스크롤 |

### 북마크

| 기능 | 상태 | 설명 |
|------|------|------|
| 헤딩 북마크 아이콘 | ✅ 완료 | h1~h4 호버 시 ☆ 표시, 클릭으로 토글 |
| 북마크 오버레이 | ✅ 완료 | 문서별 그룹핑 목록, 클릭으로 이동 |
| 문서 간 이동 | ✅ 완료 | 다른 문서 북마크 클릭 시 로드 → 스크롤 |
| 전체 삭제 | ✅ 완료 | Clear All 버튼으로 일괄 초기화 |
| localStorage 저장 | ✅ 완료 | 서버 없이 브라우저 로컬 저장 |

### 키보드 단축키

| 기능 | 상태 | 설명 |
|------|------|------|
| 단축키 처리 | ✅ 완료 | ?/←→/H/B, 입력 필드/오버레이 충돌 방지 |
| 도움말 모달 | ✅ 완료 | ? 키로 토글, DOM 동적 생성 |
| 문서 이동 | ✅ 완료 | ←→ 키로 이전/다음 문서 탐색, 끝 도달 토스트 |

### 배너 슬라이드쇼

| 기능 | 상태 | 설명 |
|------|------|------|
| 이미지 슬라이드 | ✅ 완료 | JPG/PNG, Ken Burns 효과 |
| 영상 슬라이드 | ✅ 완료 | MP4, 자동 재생/음소거/루프 |
| 혼합 구성 | ✅ 완료 | `bannerSlides` 배열로 이미지+영상 자유 조합 |
| 통계 스트립 | ✅ 완료 | 문서 수, 이미지 수 등 핵심 통계 표시 |
| 브레드크럼 | ✅ 완료 | 메뉴 경로 표시, 상위 메뉴 클릭 이동 |

### 토스트 알림

| 기능 | 상태 | 설명 |
|------|------|------|
| 공용 showToast() | ✅ 완료 | app.js에 싱글턴 함수, 4가지 타입 (info/success/error/warning) |
| 연속 호출 대응 | ✅ 완료 | clearTimeout으로 타이머 리셋, 메시지만 교체 |
| 다크 모드 | ✅ 완료 | body[data-theme="dark"] 대응 |

> **상세 설정**: [04-USER-GUIDE.md](04-USER-GUIDE.md#문서-편집기-설정) 참조

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

## 12. 문서 변환 파이프라인

DOCX/PDF 파일을 HTML로 변환하는 전체 파이프라인입니다. COM 전처리 → python-docx 변환 → 캡션/참조 후처리 순서로 동작하며, 그림/표 참조 팝업까지 포함합니다.

### 12.1 그림/표 참조 팝업 — 관련 파일

| 파일 | 역할 |
|------|------|
| `css/figure-popup.css` | 모달 오버레이, 참조 링크 스타일 |
| `js/figure-popup.js` | 이벤트 위임 기반 팝업 로직 |
| `index.html` | 모달 DOM 컨테이너 (`#figure-popup-overlay`) |

### 12.2 그림/표 참조 팝업 — 마크업 규칙

팝업이 동작하려면 문서 HTML에 다음 마크업이 필요합니다:

#### 1) 그림/표 캡션에 ID 부여

```html
<!-- 그림 캡션 -->
<p id="fig-1"><strong>Figure 1 – 시스템 구성도</strong></p>
<p><img src="images/system.png" alt=""></p>

<!-- 표 캡션 -->
<p id="tbl-1"><strong>Table 1 – 시험 결과</strong></p>
<table>...</table>
```

#### 2) 본문 참조 텍스트에 링크 추가

```html
<p>시스템 구성은 <a data-fig-ref="fig-1">Figure 1</a>에 나타나 있다.</p>
<p>시험 결과는 <a data-fig-ref="tbl-1">Table 1</a>을 참조한다.</p>
```

### 12.3 ID 명명 규칙

| 유형 | 접두어 | 예시 |
|------|--------|------|
| 그림 (Figure/그림) | `fig-` | `fig-1`, `fig-2`, `fig-10` |
| 표 (Table/표) | `tbl-` | `tbl-1`, `tbl-2`, `tbl-10` |

### 12.4 JS 동작 원리

1. **이벤트 위임**: `#main-content`에 단일 클릭 리스너 등록 → 동적 로드된 콘텐츠에도 자동 적용
2. **콘텐츠 탐색**: `data-fig-ref` 값으로 대상 요소(`id`)를 찾고, 해당 요소 내부 또는 인접(±3 형제)에서 `img`/`table` 추출
3. **캡션 추출**: 인접 요소에서 "Figure/Table/그림/표 + 숫자" 패턴 자동 감지
4. **모달 표시**: 추출된 이미지/표를 모달에 복제하여 표시
5. **닫기**: ESC 키, 배경 클릭, X 버튼

### 12.5 변환기 구현 (converter.py)

내장 변환기(`tools/converter/converter.py`)에 캡션 자동 ID 및 참조 링크 기능이 구현되어 있습니다.

#### 처리 흐름

```
Word OOXML 파싱
    ↓
1. _resolve_seq_fields()  ← 각 문단 처리 전 SEQ 필드 자동 채번
    ↓
2. _process_paragraph()   ← 텍스트 추출 + 캡션 감지
    ↓
3. _detect_caption()      ← 캡션이면 _caption_map에 등록, <p id="fig-1"> 추가
    ↓
4. _linkify_references()  ← 최종 HTML에서 참조 텍스트 → <a data-fig-ref> 변환
```

#### SEQ 필드 처리 (`_resolve_seq_fields`)

Word 캡션은 SEQ 필드로 번호를 관리합니다. 필드 갱신(Ctrl+A → F9) 없이 저장하면 빈 캐시 값이 됩니다.

- **복합 필드**: `fldChar begin → instrText → fldChar separate → 결과 run → fldChar end`
- **단순 필드**: `fldSimple` 요소 (자식 run을 부모 `<w:p>`로 승격)
- 빈 캐시 → 카테고리별 카운터 자동 증가, XML에 주입
- 유효 캐시 → 카운터 동기화

#### 캡션 감지 (`_detect_caption`)

```
패턴: ^(Figure|Fig.|Table|Tab.|그림|표)\s+(\d+(?:[-.]?\d+)*)\s*[:：–—-.]
```

- **구분자 필수**: 번호 뒤에 `: – — - .` 중 하나가 있어야 캡션으로 인식
- 예: "Figure 1 – Title" → `id="fig-1"` (캡션)
- 예: "Figure 1을 보면" → 캡션 아님 (본문 참조로 처리)
- ID 생성: Figure/Fig/그림 → `fig-`, Table/Tab/표 → `tbl-`

#### 참조 링크 생성 (`_linkify_references`)

최종 HTML에서 본문 참조 텍스트를 `<a data-fig-ref>` 링크로 변환합니다.

- `_caption_map`에 등록된 캡션만 링크 대상
- 스킵 영역: 기존 `<a>` 태그 내부, 캡션 `id=` 요소 내부

#### 이미지 비율 보존

Word 문서의 이미지 배치 크기(EMU)를 페이지 콘텐츠 폭 대비 비율(%)로 변환합니다.

- `_get_page_content_width()`: 문서의 `sectPr`에서 페이지 폭 − 좌우 여백 계산
- `_make_img_tag()`: `cx / 페이지콘텐츠폭 × 100` → `style="width: N%"` 출력
- 원문 작성자가 의도한 이미지-본문 간 비율이 웹에서도 유지됨
- 사용자가 에디터에서 `width: N%` 값을 수정하여 개별 이미지 크기 조절 가능

#### 도형/그리기 감지

Word 도형(DrawingML, VML)은 이미지로 추출할 수 없어 변환 시 누락됩니다. 변환기는 이를 감지하여 경고합니다.

- `_has_unextractable_shapes()`: `<w:drawing>`/`<w:pict>` 존재하나 `<a:blip>` 없는 경우 감지
- 도형만 있는 문단 → `<div class="shape-placeholder">` 블록 경고
- 텍스트와 혼합된 도형 → 문단 뒤에 블록 경고 추가
- 변환 결과에 `unextractable_shapes` 통계 + 경고 메시지 포함
- **해결 방법**: Word에서 도형 선택 → 복사 → 선택하여 붙여넣기 → "그림(PNG)" 변환 후 재변환

### 12.6 장절번호 평문화 (COM 전처리)

Word의 다단계 목록 자동번호(1.1, 3.2.4 등)는 python-docx로 텍스트를 읽을 수 없습니다. 업로드 시 `win32com`으로 Word를 COM 호출하여 자동번호를 텍스트로 변환하는 전처리 단계가 파이프라인에 포함되어 있습니다.

#### 관련 파일

| 파일 | 역할 |
|------|------|
| `tools/converter/word_preprocessor.py` | COM 기반 DOCX 전처리 (장절번호 평문화 + 필드 갱신) |
| `backend/api/upload.py` | `run_converter()` 내 DOCX 변환 전 전처리 호출 |

#### 처리 흐름

```
업로드된 DOCX
    ↓
1. preprocess_docx()          ← Word COM 인스턴스 생성 (백그라운드)
    ↓
2. _flatten_heading_numbers() ← 헤딩 단락의 ListString 수집 (Pass 1)
                               ← 역순으로 RemoveNumbers + InsertBefore (Pass 2)
    ↓
3. _update_fields()           ← SEQ 필드, TOC 등 일괄 갱신
    ↓
4. SaveAs2 → 임시 파일        ← 원본 DOCX는 변경하지 않음
    ↓
5. DocxConverter.convert()    ← 기존 python-docx 기반 변환
    ↓
6. 임시 파일 정리
```

#### 2-pass 방식

`RemoveNumbers()`는 리스트 체인을 끊어 후속 단락의 번호를 리셋합니다. 이를 방지하기 위해:
- **Pass 1**: 모든 헤딩의 `ListString`을 먼저 수집
- **Pass 2**: 역순(문서 끝→앞)으로 번호 제거 + 텍스트 삽입

#### Graceful Fallback

- `pywin32` 미설치 또는 Word 미설치 환경 → 경고 로그만 남기고 원본 DOCX 그대로 변환 (번호 없이)
- COM 오류 발생 시에도 동일하게 fallback → 서비스 중단 없음
- `finally` 블록에서 Word 프로세스 반드시 종료 (좀비 방지)

### 12.7 수식 변환 (OMML → MathML)

내장 변환기는 Word 수식(OMML)을 브라우저 네이티브 MathML로 변환합니다. 외부 JavaScript 라이브러리(MathJax, KaTeX 등) 없이 동작하므로 에어갭 환경에 적합합니다.

#### 관련 파일

| 파일 | 역할 |
|------|------|
| `tools/converter/omml_to_mathml.py` | OMML XML → MathML 변환 클래스 |
| `tools/converter/converter.py` | 수식 감지 및 변환 통합 |
| `css/content.css` | MathML 표시 스타일 (`.math-display`) |

#### 처리 흐름

```
Word OOXML (paragraph._element)
    ↓
1. _has_math()               ← m:oMathPara 또는 m:oMath 존재 여부 확인
    ↓
2-A. 디스플레이 수식 (m:oMathPara)
    → OmmlToMathml.convert_omath(display=True)
    → <div class="math-display"><math display="block">...</math></div>
    ↓
2-B. 인라인 수식 (m:oMath + w:r 혼합)
    → _process_paragraph_children()
    → <w:r>은 기존 _process_runs()로, <m:oMath>은 convert_omath(display=False)로 처리
    → <p>텍스트 <math>...</math> 텍스트</p>
```

#### 지원 OMML 요소 (18종)

| OMML | MathML | 설명 |
|------|--------|------|
| `m:f` | `<mfrac>` | 분수 (선형, 무선 분수 포함) |
| `m:sSub` / `m:sSup` / `m:sSubSup` | `<msub>` / `<msup>` / `<msubsup>` | 첨자 |
| `m:d` | `<mrow><mo>(</mo>...<mo>)</mo></mrow>` | 괄호/구분자 |
| `m:rad` | `<msqrt>` / `<mroot>` | 근호 |
| `m:nary` | `<munderover>` / `<msubsup>` + `<mo>` | 합(∑), 적분(∫) 등 |
| `m:func` | `<mrow>` | 함수 (sin, cos 등) |
| `m:acc` | `<mover accent>` | 악센트 (벡터 화살표 등) |
| `m:bar` | `<mover>` / `<munder>` | 윗줄/아랫줄 |
| `m:m` | `<mtable>` | 행렬 |
| `m:eqArr` | `<mtable>` | 수식 배열 |
| `m:limLow` / `m:limUpp` | `<munder>` / `<mover>` | 극한 |
| `m:groupChr` | `<munder>` / `<mover>` | 그룹 문자 (중괄호 등) |
| `m:sPre` | `<mmultiscripts>` | 앞첨자 |
| `m:box` | `<mrow>` | 박스 |
| `m:borderBox` | `<menclose>` | 테두리 박스 |
| `m:phant` | `<mphantom>` | 팬텀 |

#### 텍스트 분류 (`_classify_math_text`)

`m:r` / `m:t` 요소의 텍스트를 MathML 요소로 자동 분류:

- 숫자 (소수점 포함) → `<mn>`
- 연산자 (+, -, =, <, > 등) → `<mo>`
- 알려진 함수명 (sin, cos, log 등) → `<mi>`
- 변수/그리스 문자 → `<mi>`
- 혼합 문자열 → 문자 단위로 분리하여 각각 분류

#### 미지원 요소 폴백

구현되지 않은 OMML 요소는 `_convert_children()`로 자식을 재귀 처리하여 **내용은 보존**됩니다. 구조만 평탄화될 뿐 텍스트가 누락되지는 않습니다.

#### 주의사항

- **수식 편집**: MathML은 기계 생성 포맷으로 사람이 직접 편집하기 어렵습니다. 수식 수정이 필요하면 Word 원본을 수정 후 재변환을 권장합니다.
- **브라우저 호환**: Chrome 109+, Edge 109+, Firefox 전 버전, Safari 전 버전에서 MathML 네이티브 지원. IE는 미지원.
- **인쇄**: `@media print`에서 `.math-display`에 `page-break-inside: avoid` 적용.

### 12.8 팝업 콘텐츠 탐색 (`extractFigureContent`)

캡션 요소(`id`)를 기준으로 이미지/표를 찾는 양방향 탐색 로직:

1. 요소 자체가 `<img>` 또는 `<table>`인 경우 → 즉시 사용
2. 요소 내부에서 `<img>` 또는 `<table>` 탐색
3. **양방향 형제 탐색**: 이전/다음 각 3개 형제까지 탐색, 가장 가까운 후보 선택
   - Word에서 캡션이 표 아래에 오는 경우와 이미지 위에 오는 경우 모두 대응

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

## 14. 키보드 단축키

문서 탐색을 위한 키보드 단축키 시스템입니다.

### 14.1 관련 파일

| 파일 | 역할 |
|------|------|
| `js/keyboard.js` | 키 이벤트 처리, 도움말 모달 생성 |
| `css/main.css` | 도움말 모달 스타일 (`.shortcuts-overlay`, `.shortcuts-modal`) |

### 14.2 구현 방식

- **IIFE 패턴**: 전역 오염 방지, `DOMContentLoaded`에서 초기화
- **입력 필드 무시**: `INPUT`, `TEXTAREA`, `contentEditable` 활성 시 단축키 비활성
- **오버레이 충돌 방지**: 검색/북마크/팝업 오버레이가 열려있으면 단축키 무시
- **도움말 모달**: DOM 동적 생성 (싱글턴), CSS 트랜지션으로 페이드인/아웃

### 14.3 문서 이동 로직

`navigateDocument(direction)`:
1. `AppState.menuData`에서 `url`이 있는 항목만 평탄화(flatten)
2. `AppState.currentPage`로 현재 위치 검색
3. `direction` (+1/-1) 적용하여 이전/다음 문서 `loadContent()` 호출
4. 첫 번째/마지막 문서 도달 시 토스트 알림

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
| `js/app.js` | `showToast(message, type)` — 공용 함수 |
| `css/main.css` | `.toast` 스타일 (위치, 애니메이션, 타입별 색상) |

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
- [02-INSTALLATION.md](02-INSTALLATION.md): Tomcat 기본 설치
- [07-TRANSLATOR-SYSTEM.md](07-TRANSLATOR-SYSTEM.md): Translator 시스템 설계 (API, 데이터 구조, 번역 파이프라인)
- [04-USER-GUIDE.md](04-USER-GUIDE.md): 콘텐츠 관리, 검색 인덱스 업데이트
