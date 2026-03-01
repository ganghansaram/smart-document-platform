# Backend Setup Guide

백엔드 환경 구성 단계별 가이드

---

## 목차

1. [개요](#개요)
2. [백엔드가 필요한 경우](#백엔드가-필요한-경우)
3. [Step 1: 폴더 구조 생성](#step-1-폴더-구조-생성)
4. [Step 2: requirements.txt 생성](#step-2-requirementstxt-생성)
5. [Step 3: 오프라인 패키지 다운로드](#step-3-오프라인-패키지-다운로드)
6. [Step 4: 백엔드 코드 작성](#step-4-백엔드-코드-작성)
7. [Step 5: 로컬 테스트](#step-5-로컬-테스트)
8. [Step 6: 폐쇄망 배포](#step-6-폐쇄망-배포)
9. [Step 7: 프론트엔드 연동](#step-7-프론트엔드-연동)
10. [체크리스트](#체크리스트)

---

## 개요

이 문서는 **통합 백엔드 서버**를 구성하는 단계별 절차입니다.

**백엔드가 제공하는 기능:**
- AI 채팅 API (`/api/chat`, `/api/search`)
- 문서 편집 저장 API (`/api/save-document`)
- 관리자 인증 API (`/api/auth/*`) — 업로드/편집/인덱싱은 admin 로그인 필요
- 관리자 설정 API (`/api/settings`) — 런타임 설정 변경
- 접속 통계 API (`/api/analytics/*`) — heartbeat, 대시보드

**서버 구성도:**
```
┌─────────────────────────────────────────────────────────┐
│  웹서버 (Tomcat:8080)                                    │
│  - 정적 파일 제공 (HTML, CSS, JS)                        │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  백엔드 (FastAPI:8000)                                   │
│  - /api/search          검색 API                         │
│  - /api/chat            AI 채팅 API (Ollama 연동)        │
│  - /api/auth/*          인증 API (login/logout/users)    │
│  - /api/save-document   문서 저장 API (admin)            │
│  - /api/upload          문서 업로드/변환 API (admin)     │
│  - /api/reindex         검색 인덱스 재생성 API (admin)   │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼ (AI 사용 시만)
┌─────────────────────────────────────────────────────────┐
│  Ollama (11434)                                          │
│  - LLM 추론 서버                                         │
└─────────────────────────────────────────────────────────┘
```

**환경:**
- 개발: 인터넷이 되는 Windows PC
- 운영: 폐쇄망 Windows 서버

---

## 백엔드가 필요한 경우

| 기능 | AI_CONFIG | EDITOR_CONFIG | UPLOAD_CONFIG | 백엔드 필요 | Ollama 필요 |
|------|-----------|---------------|---------------|-------------|-------------|
| 기본 웹북 | false | false | false | X | X |
| AI 채팅만 | true | false | false | O | O |
| 문서 편집만 | false | true | false | O | X |
| 문서 업로드 | false | false | true | O | X |
| AI + 편집 + 업로드 | true | true | true | O | O |

**결론:**
- AI, 편집, 업로드 기능 중 하나라도 사용하면 백엔드 필요
- AI 기능 사용 시 Ollama도 필요
- 업로드 기능 사용 시 변환기 Python 패키지 추가 설치 필요

---

## Step 1: 폴더 구조 생성

### 1.1 backend 폴더 생성

```cmd
cd C:\AHS_Proj\kf21-webbook-template
mkdir backend
mkdir backend\api
mkdir backend\services
mkdir backend\packages
```

### 1.2 확인

```
kf21-webbook-template/
└── backend/
    ├── api/
    ├── services/
    └── packages/
```

---

## Step 2: requirements.txt 생성

### 2.1 백엔드 기본 패키지

`backend/requirements.txt`:

```
fastapi==0.128.3
uvicorn==0.40.0
requests==2.32.3
python-multipart==0.0.22
faiss-cpu>=1.7.4
numpy>=1.24.0
```

### 2.2 리랭커 패키지 (검색 정밀도 향상, 선택)

```
sentence-transformers>=2.2.2
```

> **참고:** `sentence-transformers`는 Cross-encoder 리랭커(`bge-reranker-v2-m3`)에 필요합니다. 미설치 시 리랭킹이 비활성화되며 하이브리드 검색만 동작합니다.

### 2.3 변환기 패키지 (업로드 기능 사용 시)

`tools/converter/requirements.txt`:

```
python-docx>=0.8.11
PyMuPDF>=1.24.0
pywin32>=306
```

> **참고:** 문서 업로드 기능(`UPLOAD_CONFIG.enabled: true`)을 사용하지 않으면 변환기 패키지는 설치하지 않아도 됩니다.

> **pywin32 (장절번호 자동 평문화):** Word의 다단계 목록 자동번호(1.1, 3.2.4 등)를 텍스트로 변환합니다. **Word가 설치된 환경에서만 동작**하며, Word 또는 pywin32가 없으면 자동번호 없이 변환됩니다 (기존 동작과 동일).

---

## Step 3: 오프라인 패키지 다운로드

> **중요:** 이 단계는 **인터넷이 되는 PC**에서 수행합니다. 다운로드한 `.whl` 파일을 프로젝트에 포함시켜 폐쇄망으로 반입합니다.

### 3.1 백엔드 패키지 다운로드

```cmd
cd C:\AHS_Proj\kf21-webbook-template\backend
pip download -r requirements.txt -d ./packages/
```

`backend/packages/` 폴더에 `.whl` 파일들이 생성됨:
```
backend/packages/
├── fastapi-0.128.3-py3-none-any.whl
├── uvicorn-0.40.0-py3-none-any.whl
├── starlette-0.52.1-py3-none-any.whl
├── ... (의존성 패키지들)
```

### 3.2 변환기 패키지 다운로드 (업로드 기능 사용 시)

```cmd
cd C:\AHS_Proj\kf21-webbook-template\tools\converter
pip download -r requirements.txt -d ./packages/
```

`tools/converter/packages/` 폴더에 `.whl` 파일들이 생성됨:
```
tools/converter/packages/
├── python_docx-x.x.x-py3-none-any.whl
├── PyMuPDF-x.x.x-cpXX-cpXX-win_amd64.whl
├── pywin32-xxx-cpXX-cpXX-win_amd64.whl
├── lxml-x.x.x-cpXX-cpXX-win_amd64.whl
├── ... (의존성 패키지들)
```

> **주의:** PyMuPDF, pywin32의 `.whl` 파일은 **OS와 Python 버전에 따라 다릅니다**. 폐쇄망 대상 PC와 동일한 환경(Windows x64, Python 버전)에서 다운로드해야 합니다.

### 3.3 폐쇄망에서 설치

```cmd
:: 백엔드 패키지 설치
cd backend
pip install --no-index --find-links=./packages/ -r requirements.txt

:: 변환기 패키지 설치 (업로드 기능 사용 시)
cd ..\tools\converter
pip install --no-index --find-links=./packages/ -r requirements.txt
```

---

## Step 4: 백엔드 코드 작성

### 4.1 config.py

`backend/config.py`:

```python
"""
백엔드 설정
"""

# Ollama 서버 설정
OLLAMA_URL = "http://localhost:11434"  # 회사: http://<linux-server-ip>:11434
OLLAMA_MODEL = "gemma3:4b"

# 임베딩 설정
EMBEDDING_MODEL = "bge-m3"            # Ollama 임베딩 모델
EMBEDDING_DIMENSION = 1024            # bge-m3 출력 차원

# 검색 설정
SEARCH_INDEX_PATH = "../data/search-index.json"
VECTOR_INDEX_PATH = "../data/vector-index"
MAX_SEARCH_RESULTS = 5
MAX_CONTEXT_LENGTH = 8000             # LLM 컨텍스트 예산 (char)
DEFAULT_SEARCH_TYPE = "hybrid"        # "keyword" / "vector" / "hybrid"
HYBRID_KEYWORD_WEIGHT = 0.3           # 키워드 비중 (벡터 = 1 - 0.3 = 0.7)
HYBRID_RRF_K = 60                     # RRF 상수
MIN_VECTOR_SCORE = 0.48               # 벡터 유사도 임계값

# 리랭커 설정
RERANKER_ENABLED = True
RERANKER_MODEL = "models/bge-reranker-v2-m3"
RERANKER_TOP_K_MULTIPLIER = 3         # 리랭킹 전 후보 = top_k × 3

# 멀티턴 대화 설정
MAX_CONVERSATION_TURNS = 5            # 프롬프트에 포함 턴 수
MAX_HISTORY_LENGTH = 2000             # 대화 기록 최대 문자
MAX_SESSIONS = 100                    # 동시 세션 상한
MAX_IDLE_MINUTES = 60                 # 유휴 세션 자동 삭제
QUERY_REWRITE_ENABLED = True          # 쿼리 재작성 활성화

# 인증 설정
AUTH_DB_PATH = str(Path(__file__).parent.parent / "data" / "auth.db")
SESSION_EXPIRY_HOURS = 24
CORS_ORIGINS = ["http://localhost:8080", "http://127.0.0.1:8080"]
# 폐쇄망: CORS_ORIGINS = ["http://서버IP:8080"]

# 업로드 임시 디렉토리 (DRM 등으로 로컬 저장이 문제될 경우 네트워크 경로로 변경)
# 예: UPLOAD_TEMP_DIR = "\\\\server\\share\\webbook_temp"
UPLOAD_TEMP_DIR = None                # None이면 기본값 (backend/temp/)

# Word COM 전처리 (장절번호 평문화 + 필드 갱신)
# pywin32 + Word 설치 필요. DRM 환경에서 COM 임시 파일이 암호화되어 실패 시 False
WORD_COM_PREPROCESS = True

# 서버 설정
HOST = "0.0.0.0"
PORT = 8000
```

### 4.2 main.py

`backend/main.py`:

```python
"""
FastAPI 백엔드 진입점
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import search, chat, document
import config

app = FastAPI(title="KF-21 WebBook API")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(search.router, prefix="/api")      # 검색 API
app.include_router(chat.router, prefix="/api")        # AI 채팅 API
app.include_router(document.router, prefix="/api")    # 문서 저장 API

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.HOST, port=config.PORT)
```

### 4.3 api/__init__.py

`backend/api/__init__.py`:

```python
# API 모듈
```

### 4.4 api/document.py (문서 저장 API)

`backend/api/document.py`:

```python
"""
문서 저장 API
"""
import os
import re
import shutil
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["document"])

# 프로젝트 루트 디렉토리
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def prettify_html(html: str) -> str:
    """HTML 포맷팅"""
    block_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'ul', 'ol', 'li',
                  'table', 'tr', 'th', 'td', 'blockquote', 'pre']
    for tag in block_tags:
        html = re.sub(rf'(<{tag}[^>]*>)', r'\n\1', html, flags=re.IGNORECASE)
        html = re.sub(rf'(</{tag}>)', r'\1\n', html, flags=re.IGNORECASE)
    html = re.sub(r'\n\s*\n+', '\n\n', html)
    return html.strip()

class SaveDocumentRequest(BaseModel):
    path: str
    content: str
    createBackup: bool = True

@router.post("/save-document")
async def save_document(request: SaveDocumentRequest):
    # 경로 검증 (보안)
    if not request.path.startswith("contents/"):
        raise HTTPException(status_code=400, detail="Invalid path")

    file_path = os.path.normpath(os.path.join(PROJECT_ROOT, request.path))
    if not file_path.startswith(os.path.join(PROJECT_ROOT, "contents")):
        raise HTTPException(status_code=400, detail="Path traversal detected")

    # 백업 생성
    if request.createBackup:
        backup_dir = os.path.join(PROJECT_ROOT, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{os.path.splitext(os.path.basename(file_path))[0]}_{timestamp}.bak"
        shutil.copy2(file_path, os.path.join(backup_dir, backup_name))

    # 저장
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(prettify_html(request.content))

    return {"success": True, "message": "Document saved"}
```

### 4.5 api/search.py

`backend/api/search.py`:

```python
"""
검색 API
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

from services.keyword_search import search_documents

router = APIRouter()

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5

class SearchResult(BaseModel):
    title: str
    content: str
    path: str
    section_id: Optional[str] = None
    score: float

class SearchResponse(BaseModel):
    results: List[SearchResult]
    search_type: str = "keyword"
    total: int

@router.post("/search", response_model=SearchResponse)
def search(request: SearchRequest):
    results = search_documents(request.query, request.top_k)
    return SearchResponse(
        results=results,
        search_type="keyword",
        total=len(results)
    )
```

### 4.6 api/chat.py

`backend/api/chat.py`:

```python
"""
채팅 API — 멀티턴 대화 + 하이브리드 검색 통합
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

from services.llm_client import generate_response
from services.conversation import store as conversation_store

router = APIRouter()

class ContextDoc(BaseModel):
    title: str
    content: str
    path: Optional[str] = None
    section_id: Optional[str] = None

class ChatRequest(BaseModel):
    question: str
    context: List[ContextDoc] = []          # 프론트엔드 검색 결과 (선택)
    conversation_id: Optional[str] = None   # 멀티턴 세션 ID

class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]
    model: str
    conversation_id: str                    # 세션 추적용

@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    # 1. 세션 관리 (생성 또는 조회)
    # 2. 대화 기록 조회
    # 3. 컨텍스트 결정:
    #    - request.context 있으면 → 프론트엔드 결과 사용
    #    - 없으면 → 쿼리 재작성 + 백엔드 하이브리드 검색 + 리랭킹
    # 4. LLM 응답 생성 (대화 기록 포함)
    # 5. 대화 기록 저장
    ...
```

### 4.7 services/__init__.py

`backend/services/__init__.py`:

```python
# Services 모듈
```

### 4.8 services/keyword_search.py

`backend/services/keyword_search.py`:

```python
"""
키워드 기반 검색 서비스
"""
import json
from pathlib import Path
from typing import List

import config

def load_search_index():
    """검색 인덱스 로드"""
    index_path = Path(__file__).parent.parent / config.SEARCH_INDEX_PATH
    if not index_path.exists():
        return []

    with open(index_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def search_documents(query: str, top_k: int = 5) -> List[dict]:
    """
    키워드 기반 문서 검색
    """
    index = load_search_index()
    if not index:
        return []

    # 쿼리를 단어로 분리
    terms = [t.lower() for t in query.split() if len(t) >= 2]
    if not terms:
        return []

    results = []
    for doc in index:
        title_lower = doc.get('title', '').lower()
        content_lower = doc.get('content', '').lower()
        score = 0

        for term in terms:
            if term in title_lower:
                score += 10
            if term in content_lower:
                score += 1

        if score > 0:
            results.append({
                'title': doc.get('title', ''),
                'content': doc.get('content', '')[:500],  # 미리보기용
                'path': doc.get('url', ''),
                'section_id': doc.get('section_id'),
                'score': score
            })

    # 점수순 정렬
    results.sort(key=lambda x: -x['score'])
    return results[:top_k]
```

### 4.9 services/llm_client.py

`backend/services/llm_client.py`:

```python
"""
Ollama LLM 클라이언트 — 토큰 예산 관리, 대화 기록 지원
"""
import requests
from typing import List, Optional
import config

SYSTEM_PROMPT = """당신은 KF-21 전투기 기술 문서 전문 어시스턴트입니다.
제공된 참고 문서만을 기반으로 답변합니다.

[핵심 규칙]
1. 오직 제공된 문서 내용만 사용
2. 문서에 없는 내용은 절대 추측 금지
3. 정보 없으면 "제공된 문서에서 해당 정보를 찾지 못했습니다" 답변

[답변 방식]
- 핵심 내용 간결 제시, 불릿/번호 목록 사용
- 기술 용어는 문서 표기대로
- 답변 끝에 참고 문서 제목 명시
[언어] 한국어"""

def generate_response(
    question: str,
    context: List[dict],
    history: Optional[List[dict]] = None  # 멀티턴 대화 기록
) -> dict:
    """
    토큰 예산 관리:
    - 총 예산: MAX_CONTEXT_LENGTH (8000자)
    - 시스템 프롬프트: ~500자 (고정)
    - 컨텍스트 문서: ~5000자 (문서별 균등 할당)
    - 대화 기록: ~2000자 (MAX_HISTORY_LENGTH, 초과 시 오래된 턴 제거)
    - 질문: ~500자

    LLM 옵션: temperature=0 (결정적 응답)
    """
    ...
```

### 4.10 벡터 인덱스 빌드

하이브리드 검색을 사용하려면 FAISS 벡터 인덱스를 빌드해야 합니다.

```cmd
:: 사전 조건: Ollama에 bge-m3 모델 설치
ollama pull bge-m3

:: 벡터 인덱스 빌드 (search-index.json 기반)
python tools/build-vector-index.py
```

**출력:**
```
벡터 인덱스 빌드 시작...
임베딩 모델: bge-m3 (1024차원)
배치 크기: 32
...
벡터 인덱스 빌드 완료: data/vector-index/
총 128개 문서 인덱싱
```

> **참고:** 벡터 인덱스가 없으면 자동으로 키워드 검색으로 폴백합니다.

### 4.11 리랭커 모델 배포

Cross-encoder 리랭커를 사용하려면 모델 파일을 로컬에 배치합니다.

```cmd
:: 인터넷 환경에서 모델 다운로드 (Python)
python -c "from sentence_transformers import CrossEncoder; CrossEncoder('BAAI/bge-reranker-v2-m3').save('models/bge-reranker-v2-m3')"

:: 결과 확인
dir models\bge-reranker-v2-m3
```

폐쇄망에서는 `models/bge-reranker-v2-m3/` 폴더를 프로젝트에 포함시켜 반입합니다.

> **참고:** 리랭커 모델이 없으면 `RERANKER_ENABLED`가 자동으로 비활성화되며 하이브리드 검색 결과가 바로 반환됩니다.

### 4.12 DRM 환경 대응 (문서 변환)

회사 DRM이 적용된 환경에서는 Word COM 전처리 시 임시 파일이 자동 암호화되어 변환이 실패할 수 있습니다.

#### 증상

- 문서 업로드 시 "변환 실패" 오류 발생
- COM 전처리(`word_preprocessor.py`)가 임시 DOCX를 저장할 때 DRM이 개입

#### 대응 방법

**방법 1: COM 전처리 비활성화 (간단)**

`backend/config.py`에서 COM 전처리를 끕니다. 장절번호 자동 평문화가 생략되지만 변환 자체는 정상 동작합니다.

```python
WORD_COM_PREPROCESS = False
```

**방법 2: 수동 전처리 후 업로드 (장절번호 필요 시)**

DRM이 적용되지 않는 PC(개인 PC 등)에서 미리 전처리한 DOCX를 만들어 업로드합니다.

```cmd
:: DRM 미적용 PC에서 실행 (Word + pywin32 필요)
python tools/converter/word_preprocessor.py 원본문서.docx 전처리완료.docx
```

- 출력 파일(`전처리완료.docx`)에 장절번호가 텍스트로 삽입됨
- 이 파일을 회사 환경에서 업로드하면 COM 전처리 없이도 장절번호 포함 변환 가능
- `WORD_COM_PREPROCESS = False`와 함께 사용

**방법 3: DRM 예외 경로를 임시 디렉토리로 지정**

DRM 정책에서 제외되는 네트워크 드라이브가 있다면 임시 저장 경로를 변경합니다.

```python
# backend/config.py
UPLOAD_TEMP_DIR = "\\\\server\\share\\webbook_temp"  # DRM 예외 경로
WORD_COM_PREPROCESS = True                            # COM 전처리 활성화
```

#### 설정 조합 요약

| 환경 | `WORD_COM_PREPROCESS` | `UPLOAD_TEMP_DIR` | 장절번호 | 비고 |
|------|----------------------|-------------------|---------|------|
| 일반 (DRM 없음) | `True` | `None` (기본) | 자동 | 권장 |
| DRM + 장절번호 불필요 | `False` | `None` (기본) | 없음 | 가장 간단 |
| DRM + 수동 전처리 | `False` | `None` (기본) | 수동 | 방법 2 |
| DRM + 예외 경로 있음 | `True` | 네트워크 경로 | 자동 | 방법 3 |

---

## Step 5: 로컬 테스트

### 5.1 백엔드 서버 실행

```cmd
cd C:\AHS_Proj\kf21-webbook-template\backend
python main.py
```

### 5.2 확인

브라우저에서 접속:
```
http://localhost:8000/api/health
```

응답:
```json
{"status": "ok"}
```

### 5.3 API 테스트 (선택)

```cmd
curl -X POST http://localhost:8000/api/search -H "Content-Type: application/json" -d "{\"query\": \"KF-21\"}"
```

### 5.4 백엔드 운영

#### 실행 상태 확인

```cmd
:: 방법 1: Health API 호출
curl http://localhost:8000/api/health

:: 방법 2: 포트 확인
netstat -ano | findstr :8000
```

#### 백엔드 종료

```cmd
:: 방법 1: 실행한 터미널에서
Ctrl + C

:: 방법 2: 프로세스 강제 종료
taskkill /F /PID <프로세스ID>
```

> 프로세스 ID는 `netstat -ano | findstr :8000` 결과의 마지막 숫자

#### 코드 수정 후 재시작 절차

변환기 등 백엔드 Python 코드를 수정한 경우, 실행 중인 프로세스가 구버전 코드를 캐싱하고 있으므로 반드시 재시작해야 합니다.

```cmd
:: 1. 포트 8000 사용 프로세스 확인
netstat -ano | findstr :8000

:: 2. 해당 PID 강제 종료
taskkill /PID <프로세스ID> /F

:: 3. 포트 비었는지 확인
netstat -ano | findstr :8000

:: 4. 백엔드 시작
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

> **중요**: `netstat`으로 포트가 실제로 비었는지 반드시 확인 후 시작하세요. 종료 명령만으로는 프로세스가 남아 있을 수 있으며, 새 서버가 포트 충돌로 조용히 실패합니다.

**개발 중 (코드 자주 수정 시)**: `--reload` 옵션을 사용하면 파일 변경 시 자동으로 코드를 다시 로드하므로 재시작이 필요 없습니다.

```cmd
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### 주의사항

- **PC 재부팅 시**: 백엔드가 자동으로 시작되지 않음 → 수동 실행 필요
- **터미널 닫으면**: 백엔드도 종료됨
- **백그라운드 실행**: `start /B python main.py` (터미널 닫아도 유지, 권장하지 않음)

#### Windows 서비스 등록 (선택)

PC 재부팅 시 자동 시작이 필요하면 NSSM 등을 사용하여 서비스로 등록:

```cmd
:: NSSM 다운로드 후
nssm install KF21Backend "C:\Python311\python.exe" "C:\...\backend\main.py"
nssm start KF21Backend
```

---

## Step 6: 폐쇄망 배포

### 6.1 전체 프로젝트 압축

```cmd
cd C:\AHS_Proj
zip -r kf21-webbook-template.zip kf21-webbook-template/
```

또는 탐색기에서 폴더 우클릭 → "압축"

### 6.2 폐쇄망으로 파일 이동

USB 또는 승인된 방법으로 `kf21-webbook-template.zip` 이동

### 6.3 폐쇄망에서 설치

```cmd
:: 1. 압축 해제
:: 2. 오프라인 패키지 설치
cd backend
pip install --no-index --find-links=./packages/ -r requirements.txt

:: 3. Ollama URL 수정
:: backend/config.py에서 OLLAMA_URL을 실제 Linux 서버 IP로 변경

:: 4. 백엔드 실행
python main.py
```

---

## Step 7: 프론트엔드 연동

### 7.1 config.js 설정

`js/config.js` 파일을 열고 백엔드 사용 설정:

```javascript
const AI_CONFIG = {
    // 백엔드 모드 활성화
    useBackend: true,
    backendUrl: 'http://localhost:8000',

    // 아래 설정은 useBackend: false 일 때만 사용됨
    ollamaUrl: 'http://localhost:11434',
    model: 'gemma3:4b',

    // 공통 설정
    maxContextLength: 8000,
    maxSearchResults: 5
};
```

### 7.2 설정 옵션 설명

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `useBackend` | 백엔드 API 사용 여부 | `true` |
| `backendUrl` | 백엔드 서버 주소 | `http://localhost:8000` |
| `ollamaUrl` | Ollama 직접 호출 시 주소 | `http://localhost:11434` |
| `model` | Ollama 직접 호출 시 모델명 | `gemma3:4b` |

### 7.3 모드별 동작

**useBackend: true (권장)**
- 프론트엔드 → 백엔드(/api/search, /api/chat) → Ollama
- Ollama 주소는 `backend/config.py`에서 관리

**useBackend: false**
- 프론트엔드 → Ollama 직접 호출
- 백엔드 서버 실행 불필요

### 7.4 서버 실행 순서

```cmd
:: 1. Ollama 실행 확인 (Linux 서버)
:: 2. 백엔드 실행 (Windows)
cd backend
python main.py

:: 3. Tomcat 실행 (다른 터미널)
C:\apache-tomcat-7.0.77\bin\startup.bat

:: 4. 브라우저 접속
http://localhost:8080
```

---

## 체크리스트

- [ ] Step 1: 폴더 구조 생성
- [ ] Step 2: requirements.txt 생성
- [ ] Step 3: 오프라인 패키지 다운로드
- [ ] Step 4: 백엔드 코드 작성
- [ ] Step 5: 로컬 테스트
- [ ] Step 6: 폐쇄망 배포
- [ ] Step 7: 프론트엔드 연동 (config.js에서 useBackend: true 설정)
- [ ] Step 8: admin 계정 생성 (`python tools/create-admin.py`)

---

## 서버 실행 순서 요약

### 기능별 실행 순서

**기본 웹북만 (AI/편집 비활성화):**
```cmd
1. Tomcat 실행: C:\apache-tomcat-7.0.77\bin\startup.bat
2. 브라우저 접속: http://localhost:8080
```

**문서 편집만 (AI 비활성화):**
```cmd
1. 백엔드 실행: cd backend && python main.py
2. admin 계정 생성 (최초 1회): python tools/create-admin.py
3. Tomcat 실행: C:\apache-tomcat-7.0.77\bin\startup.bat
4. 브라우저 접속: http://localhost:8080
```

**AI 채팅만 (편집 비활성화):**
```cmd
1. Ollama 실행 확인 (Linux 서버 또는 로컬)
2. 백엔드 실행: cd backend && python main.py
3. Tomcat 실행: C:\apache-tomcat-7.0.77\bin\startup.bat
4. 브라우저 접속: http://localhost:8080
```

**AI + 편집 모두 사용:**
```cmd
1. Ollama 실행 확인 (Linux 서버 또는 로컬)
2. 백엔드 실행: cd backend && python main.py
3. admin 계정 생성 (최초 1회): python tools/create-admin.py
4. Tomcat 실행: C:\apache-tomcat-7.0.77\bin\startup.bat
5. 브라우저 접속: http://localhost:8080
```

### config.js 설정 확인

```javascript
// js/config.js

const AUTH_CONFIG = {
    enabled: true,                    // 인증 기능 활성화
    backendUrl: 'http://localhost:8000',
};

const AI_CONFIG = {
    enabled: true,                    // AI 채팅 활성화
    useBackend: true,                 // 백엔드 모드 (권장)
    backendUrl: 'http://localhost:8000',
    // ...
};

const EDITOR_CONFIG = {
    enabled: true,                    // 편집 기능 활성화
    requireAuth: true,                // admin 로그인 필요
    backendUrl: 'http://localhost:8000',
    // ...
};

const UPLOAD_CONFIG = {
    enabled: true,                    // 문서 업로드 활성화
    requireAuth: true,                // admin 로그인 필요
    backendUrl: 'http://localhost:8000',
    acceptFormats: ['.docx', '.pdf'], // 허용 파일 형식
    autoSearchIndex: true,            // 업로드 후 검색 인덱스 자동 재생성
    autoVectorIndex: true,            // 업로드 후 벡터 인덱스 자동 재생성
    // ...
};

const DISPLAY_CONFIG = {
    version: 'v5.5',                  // 푸터 버전 표시
    tableStyle: 'bordered',           // "bordered" | "simple" | "minimal"
};
```

### 종료 순서

```cmd
1. 브라우저 닫기
2. Tomcat 종료: C:\apache-tomcat-7.0.77\bin\shutdown.bat
3. 백엔드 종료: Ctrl+C (실행한 터미널에서)
4. Ollama 종료: (필요시)
```

---

## 관련 문서

- [ARCHITECTURE.md](ARCHITECTURE.md): 시스템 구조
- [RAG-PIPELINE.md](RAG-PIPELINE.md): 검색/AI 기술 상세
