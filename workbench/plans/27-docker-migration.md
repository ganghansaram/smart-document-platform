# Plan-27: Docker 컨테이너화 및 Nginx 리버스 프록시 전환

> **목표**: 현재 윈도우 VM(2포트) 직접 실행 → Docker + Nginx(1포트)로 전환하여  
> 리눅스 VM(폐쇄망)에서 단일 포트로 서비스 운영  
> **제약**: 기존 윈도우 직접 실행 방식을 깨뜨리지 않을 것

---

## 0. 현황 분석

### 현재 배포 구조
```
윈도우 VM (폐쇄망)
├── python -m http.server 8080    ← 프론트엔드 (정적 파일)
├── python main.py                ← FastAPI 백엔드 (포트 8000)
├── models/bge-m3 (2.2GB)        ← 임베딩 모델
├── models/bge-reranker-v2-m3 (2.2GB) ← 리랭커 모델
└── Ollama → 별도 GPU 서버 (외부 URL)
```
- 방화벽 포트 2개 (8080, 8000) 보안팀 신청 필요
- 프론트·백엔드 각각 수동 실행
- 파일 복사로 배포 (빌드 시스템 없음)

### 데이터 현황
| 경로 | 내용 | 크기 | 갱신 주기 |
|------|------|------|----------|
| `data/auth.db` | 사용자 계정·세션 | ~90KB | 수시 |
| `data/analytics.db` | 사용 통계 | ~900KB | 수시 |
| `data/settings.json` | 런타임 설정 | ~3KB | 가끔 |
| `data/translator/{user}/` | 번역 작업물 (PDF, MD, 이미지) | 가변 | 수시 |
| `data/verify/` | 검증 히스토리 | 가변 | 수시 |
| `data/compare/` | 비교 데이터 | 가변 | 수시 |
| `data/search-index.json` | 검색 인덱스 | ~770KB | 업로드 시 |
| `data/vector-index.*` | FAISS 벡터 인덱스 | ~1.3MB | 업로드 시 |
| `data/glossary.*` | 용어집 | ~3.3MB | 드물게 |
| `data/menu.json` | 메뉴 구성 | ~5KB | 업로드/관리 시 |
| `data/compare-rules.json` | 비교 규칙 | ~5KB | 가끔 |
| `data/boilerplate-phrases.json` | 상용구 | ~2KB | 드물게 |
| `contents/` | 웹북 HTML 콘텐츠 | 가변 | 업로드 시 |
| `models/` | ML 모델 (bge-m3, reranker) | ~4.4GB | 거의 안 바뀜 |
| `backups/` | 문서 편집 백업 (.bak) | 가변 | 편집 시 |
| `backend/logs/` | 서버 로그 | 가변 | 수시 |

---

## 1. 목표 아키텍처

```
리눅스 VM (폐쇄망)
│
│  docker-compose.yml
│  .env                     ← 포트, Ollama URL 등 외부 설정
│
├── nginx 컨테이너 (포트: ${PORT:-80}, 유일하게 외부 노출)
│   ├── /             → 정적 프론트엔드 (HTML/JS/CSS)
│   ├── /api/*        → proxy_pass → backend:8000
│   ├── /contents/*   → 웹북 콘텐츠 (볼륨)
│   └── /data/*.json  → 화이트리스트 3개만 허용 (나머지 403)
│
├── backend 컨테이너 (내부 8000, 외부 비노출)
│   ├── FastAPI (uvicorn)
│   ├── tools/ (인덱스 빌드, 문서 변환)
│   └── pdf2zh (번역 서브프로세스)
│
└── 볼륨 마운트 (호스트 → 컨테이너)
    ├── ./data/      → /app/data        (RW)
    ├── ./contents/  → /app/contents    (RW)
    ├── ./models/    → /app/models      (RO)
    ├── ./backups/   → /app/backups     (RW)
    └── ./logs/      → /app/backend/logs (RW)
```

### 핵심 원칙
1. **이미지 = 코드, 볼륨 = 데이터** — 이미지 교체해도 데이터 유지
2. **설정 = `.env` 1개** — 포트, Ollama URL 등 환경별 차이 흡수
3. **models/ = 볼륨** — 4.4GB를 이미지에 넣으면 너무 커짐
4. **기존 코드 수정 없음** — Docker 설정 파일만 추가

---

## 2. Phase 구성

### Phase 1: Docker 기반 파일 작성
- [x] `Dockerfile` — 백엔드 이미지 (Python + 의존성 + tools/)
- [x] `docker/nginx.conf` — 리버스 프록시 + 정적 파일 + 보안 차단
- [x] `docker/Dockerfile.nginx` — 프론트엔드 이미지 (Nginx + HTML/JS/CSS)
- [x] `docker/config.docker.js` — Docker 전용 프론트엔드 설정
- [x] `docker-compose.yml` — 서비스 오케스트레이션
- [x] `.env.example` — 설정 템플릿
- [x] `.dockerignore` — 빌드 제외 목록

### Phase 2: 코드 조정 (최소 변경)
- [x] `config.py` — `OLLAMA_MODEL`을 `os.getenv()` 연동 (1행 변경)
- [x] `CORS_ORIGINS` — 기존 `os.getenv()` 유지, Docker에서는 compose가 주입
- [x] `config.js` — 원본 수정 없음 (Nginx가 Docker 전용 버전으로 오버라이드)

### Phase 3: 로컬 빌드·검증
- [x] 이 PC(Windows)에서 Docker Desktop으로 빌드·실행 테스트
- [x] 6개 서브시스템별 핵심 기능 검증 (상세: 4절)
- [x] 볼륨 마운트 후 컨테이너 재시작해도 데이터 유지 확인

### Phase 4: 이미지 반출·반입
- [x] `docker save` → tar 파일 생성
- [x] 리눅스 VM에서 `docker load` → `docker compose up -d`
- [x] 배포 스크립트 (`deploy.sh`) 작성 — 첫 설치 + 업데이트 겸용

### Phase 5: 운영 매뉴얼
- [x] `docs/13-DOCKER-OPERATIONS.md` — 비전문가용 배포·운영 가이드

---

## 3. 설계 상세

### 3-1. 외부 설정 (`.env`)
```env
# 서비스
PORT=80                              # Nginx 외부 포트 (유일하게 노출)

# Ollama
OLLAMA_URL=http://gpu-server:11434   # GPU 서버 주소
OLLAMA_MODEL=gemma3:4b

# 데이터 경로 (기본값 그대로 사용 가능)
DATA_DIR=./data
CONTENTS_DIR=./contents
MODELS_DIR=./models

# 로그
LOG_LEVEL=INFO
```

### 3-2. Nginx 라우팅 상세

프론트엔드가 일부 `data/` 파일을 **API가 아닌 정적 파일로 직접 fetch**하는 것이 확인됨:
- `js/search.js` → `fetch('data/search-index.json')`
- `js/glossary.js` → `fetch('data/glossary.json')`
- `js/tree-menu.js`, `js/app.js`, `js/banner.js` → `fetch('data/menu.json')`

이 3개만 화이트리스트로 허용하고, `auth.db`, `settings.json` 등 민감 파일은 차단해야 한다.

```nginx
server {
    listen 80;
    client_max_body_size 100m;           # PDF 업로드 크기 제한

    # ── 프론트엔드 정적 파일 (이미지에 포함) ──
    root /app/frontend;
    index index.html;
    location / {
        try_files $uri $uri/ /index.html;
    }

    # ── config.js Docker 오버라이드 ──
    location = /js/config.js {
        alias /app/docker/config.docker.js;
    }

    # ── data/ 화이트리스트 (볼륨, 3개만 허용) ──
    location = /data/menu.json         { alias /app/data/menu.json; }
    location = /data/search-index.json { alias /app/data/search-index.json; }
    location = /data/glossary.json     { alias /app/data/glossary.json; }

    # ── 웹북 콘텐츠 (볼륨) ──
    location /contents/ { alias /app/contents/; }

    # ── API ���버스 프록시 ──
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 600s;         # 번역 등 장시간 API 대응
        proxy_buffering off;             # SSE/NDJSON 스트리밍 (챗봇, Q&A)
    }

    # ── 보안 차단 (catch-all, 위 화이트리스트보다 후순위) ──
    location /data/    { return 403; }
    location /backend/ { return 403; }
    location /models/  { return 403; }
    location /tools/   { return 403; }
    location /backups/ { return 403; }
    location /.env     { return 403; }
}
```
> `location =` (exact match)가 `location /data/` (prefix)보다 우선하므로 화이트리스트 정상 동작.

### 3-3. `config.js` 이중 환경 대응

**문제**: `js/config.js`에 `backendUrl: 'http://localhost:8000'` 하드코딩.
- 윈도우 (2포트): 크로스오리진 → 절대 URL 필요
- Docker (1포트): Nginx 동일 포트 프록시 → 상대경로 필요

**해결**: Nginx가 `/js/config.js` 요청 시 Docker 전용 파일로 대체 응답.
- `docker/config.docker.js` — `backendUrl: ''` (상대경로)
- 원본 `js/config.js` — 변경 없음 (윈도우에서 그대로 사용)
- **코드 1벌 유지, Nginx가 환경 차이를 흡수**

### 3-4. 백엔드 이미지 내용물

`backend/` 외에 아래 항목이 반드시 이미지에 포함되어야 한다:

| 항목 | 근거 | 비고 |
|------|------|------|
| `tools/` | `upload.py:150,215` — subprocess로 호출 | build-search-index, build-vector-index, converter, html_to_text |
| `backend/rules/` | `rule_engine.py` — 규칙 JSON 로드 | backend/ COPY에 자동 포함 |
| `pdf2zh` 커맨드 | `translator_service.py:1023` — subprocess 호출 | pip install pdf2zh-next로 PATH 등록 |
| 시스템 폰트 | pdf2zh 렌더링에 필요 | `fonts-liberation` 등 apt install |

```dockerfile
# Dockerfile 핵심 구조
FROM python:3.11-slim
RUN apt-get update && apt-get install -y fonts-liberation fonts-dejavu-core
COPY backend/requirements.txt /app/backend/
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend/ /app/backend/
COPY tools/   /app/tools/
WORKDIR /app/backend
CMD ["python", "main.py"]
```

### 3-5. 프론트엔드(Nginx) 이미지 정적 자산

| 항목 | 크기 | 내용 |
|------|------|------|
| `*.html` (루트) | <1MB | index, launcher, login, translator, compare, admin |
| `css/` + `css/lib/` | ~3.2MB | 디자인 토큰, 컴포넌트, KaTeX CSS |
| `css/images/` | ~65MB | cloud.mp4, 로고, 배경 이미지 |
| `js/` (코어) | ~500KB | app, auth, translator 등 |
| `js/lib/` | ~2.2MB | PDF.js, KaTeX, marked, purify, jsdiff, markmap |
| `js/monaco-editor/` | ~13MB | 에디터 (로컬 번들) |
| `docker/config.docker.js` | <1KB | Docker 전용 config 오버라이드 |

**이미지 크기 예상:**
- 백엔드: ~2~2.5GB (Python + pip 의존성 + tools/ + babeldoc ONNX ~500MB)
- 프론트/Nginx: ~110MB
- `docker save` tar: ~2.5~3GB

### 3-6. babeldoc 캐시 (폐쇄망 대응)

`md_extractor.py`와 `text_translator.py`가 `OnnxModel.from_pretrained()`을 호출하면
`~/.cache/babeldoc/`에 ONNX 모델(~500MB)을 다운로드한다. 폐쇄망이라 자동 다운로드 불가.

| 방안 | 장점 | 단점 |
|------|------|------|
| **A: 이미지에 COPY** | 배포 시 추가 작업 없음 | 이미지 +500MB |
| **B: 별도 볼륨 마운트** | 이미지 경량 유지 | 첫 설치 시 캐시 파일 별도 반입 필요 |

→ 방안 A 권장 (배포 편의성 우선, 이미지 크기 허용 범위 내)

### 3-7. 인메모리 상태 — 컨테이너 재시작 시 유실

번역기(Notebook)의 아래 상태는 메모리에만 존재한다:
- `_active_tasks` — 진행 중인 번역 asyncio Task
- `_active_procs` — pdf2zh 서브프로세스 PID
- `_page_progress` — 페이지별 번역 진행률

**영향**: 서비스 재시작 시 진행 중 번역이 중단되며 자동 재개 불가.
사용자가 해당 페이지를 다시 번역 요청해야 한다.

**운영 권고**: 버전 업데이트는 번역 작업이 없는 시간대에 수행.

### 3-8. 기존 윈도우 실행 호환성

이번 작업으로 추가되는 파일:
```
Dockerfile, docker/nginx.conf, docker/Dockerfile.nginx,
docker/config.docker.js, docker-compose.yml, .env.example,
.dockerignore, deploy.sh
```
기존 파일은 **수정 없음**:
- `config.py` — 상대경로 기반, 환경변수 폴백 이미 지원
- `js/config.js` — 원본 유지 (Docker에서만 Nginx 오버라이드)
- `main.py`, HTML/JS/CSS — 변경 없음

→ 윈도우 VM에서 기존 `python main.py` + `python -m http.server 8080` 그대로 동작.

---

## 4. 검증 체크리스트

### 데이터 안전
- [ ] 컨테이너 재생성해도 `data/` 볼륨 보존 확인
- [ ] 첫 배포 시 기존 `data/` 마운트 → 기존 계정·작업물 유지
- [ ] `docker compose down`은 볼륨 미삭제 확인 (`down -v`만 삭제)

### Nginx 라우팅
- [ ] `data/menu.json`, `data/search-index.json`, `data/glossary.json` 정상 서빙
- [ ] `data/auth.db`, `data/settings.json` 등 접근 시 403
- [ ] `/api/*` 프록시 정상 동작
- [ ] `/contents/*` 웹북 HTML 정상 로딩 (내부 상대 이미지 포함)
- [ ] `config.js` Docker 오버라이드 (`backendUrl: ''`) 동작 확인
- [ ] `client_max_body_size` — 100MB PDF 업로드 성공

### 서브시스템별 검증
- [ ] **인증**: 로그인 → 세션 쿠키 → 페이지 전환 → 로그아웃
- [ ] **Explorer**: 웹북 열기 → 검색 → AI 챗봇(스트리밍 응답 확인) → 문서 업로드·인덱싱
- [ ] **Notebook**: PDF 업로드 → 페이지 번역 → 웹뷰 → 요약 → Q&A
- [ ] **Verify**: 문서 업로드 → 비교 → 유사도 → 규칙 검증 → 내보내기
- [ ] **관리자 설정**: 설정 변경 → 저장 → 재시작 후 유지
- [ ] **Launcher**: 메뉴 → 가이드 페이지 → 시스템 전환

### 백엔드 이미지
- [ ] `tools/` 포함 확인 — 업로드 후 인덱스 빌드 정상
- [ ] `pdf2zh` PATH 실행 가능 — `docker exec backend pdf2zh --version`
- [ ] babeldoc ONNX 모델 로드 성공 — 번역 시 DocLayout-YOLO 동작
- [ ] 시스템 폰트 설치 확인 — PDF 렌더링 정상

### Ollama 연계
- [ ] `.env`의 OLLAMA_URL로 GPU 서버 접근 가능
- [ ] AI 기능 비활성 시에도 기본 기능 정상 동작

---

## 5. 리스크 & 대응

| 리스크 | 영향 | 대응 |
|--------|------|------|
| ~~리눅스 VM에 Docker 미설치~~ | ~~시작 불가~~ | Docker 29.3.1 + Compose 5.1.1 설치 확인됨 |
| GPU 서버 네트워크 미연결 | AI 기능 불가 | AI 비활성 상태로 기본 기능만 동작 |
| babeldoc 캐시 미준비 | PDF 번역 시 YOLO 모델 로드 실패 | 이미지에 포함 (방안 A) |
| 이미지 크기 초과 (USB 제한) | 반입 불가 | multi-stage 빌드, 필요시 이미지 분할 |
| 윈도우용 whl이 리눅스에서 안 됨 | 빌드 실패 | Dockerfile에서 pip install (리눅스 네이티브) |
| pdf2zh 리눅스 동작 차이 | 번역 실패 | Phase 3에서 Docker 환경 번역 테스트 |
| 번역 중 컨테이너 재시작 | 진행 중 작업 유실 | 운영 매뉴얼 명시, 비사용 시간대 업데이트 |
| `data/` Nginx 화이트리스트 누락 | 검색·메뉴·용어집 로딩 실패 | exact-match location으로 해결 |
| `tools/` 이미지 미포함 | 업로드+인덱싱 불가 | Dockerfile에 COPY tools/ 명시 |

---

## 6. 산출물

| 파일 | 위치 | 설명 |
|------|------|------|
| `Dockerfile` | 프로젝트 루트 | 백엔드 이미지 (Python + tools/ + pdf2zh) |
| `docker/Dockerfile.nginx` | `docker/` | 프론트엔드 이미지 (Nginx + HTML/JS/CSS) |
| `docker/nginx.conf` | `docker/` | Nginx 라우팅·프록시·보안 설정 |
| `docker/config.docker.js` | `docker/` | Docker 전용 프론트엔드 config |
| `docker-compose.yml` | 프로젝트 루트 | 서비스 오케스트레이션 |
| `.env.example` | 프로젝트 루트 | 설정 템플릿 |
| `.dockerignore` | 프로젝트 루트 | 빌드 제외 목록 |
| `deploy.sh` | 프로젝트 루트 | 리눅스 배포 스크립트 (첫 설치 + 업데이트) |
| `OPERATIONS.md` | 배포 디렉토리 | 운영 매뉴얼 (섹션 7 기반) |

---

## 7. 환경 요구사항 및 작업 절차

### 7-1. 소프트웨어 버전

#### 개발 PC (Windows 11)
| 항목 | 버전 | 비고 |
|------|------|------|
| OS | Windows 11 Home 10.0.26200 | 개발·빌드 환경 |
| Docker Desktop | 9.3.1 | Windows용, WSL2 백엔드 |
| Docker Compose | v5.1.1 | Docker Desktop에 포함 |
| Python | 3.11.9 | 로컬 개발·테스트용 |

#### Docker 이미지 내부 (빌드 시 결정)
| 항목 | 버전 | 비고 |
|------|------|------|
| 베이스 이미지 | `python:3.11-slim` (Debian) | 백엔드 컨테이너 |
| Nginx | `nginx:1.27-alpine` | 프론트엔드 컨테이너 |

#### 핵심 Python 패키지 (requirements.txt 기준)
| 패키지 | 버전 | 용도 |
|--------|------|------|
| fastapi | 0.128.3 | 웹 프레임워크 |
| uvicorn | 0.40.0 | ASGI 서버 |
| PyMuPDF | 1.25.2+ | PDF 처리 (현재 로컬 1.27.2) |
| pdf2zh-next | 2.8.2 | PDF 번역 (subprocess) |
| babeldoc | 0.5.23 | DocLayout-YOLO, 번역 엔진 |
| sentence-transformers | 5.1.2 | 임베딩 모델 로딩 |
| faiss-cpu | 1.12.0 | 벡터 검색 |
| ollama | 0.6.1 | Ollama 클라이언트 |
| rank-bm25 | 0.2.2 | 키워드 검색 |
| kiwipiepy | 0.22.2 | 한국어 형태소 분석 |
| python-docx | 1.2.0 | DOCX 처리 |
| openpyxl | 3.1.5 | Excel 내보내기 |
| httpx | 0.28.1 | HTTP 클라이언트 |

#### 리눅스 VM (폐쇄망) — 이미 설치 완료
| 항목 | 버전 | 비고 |
|------|------|------|
| OS | Linux | 폐쇄망 (외부 인터넷 차단) |
| Docker Engine | 29.3.1 | **설치 완료** |
| Docker Compose | v5.1.1 | **설치 완료** (plugin) |
| 디스크 여유 | 최소 15GB 권장 | 이미지 ~3GB + models ~4.4GB + data 가변 |
| 메모리 | 최소 4GB 권장 | 임베딩 모델 + 리랭커 상주 |

> Docker 이미 설치되어 있으므로 오프라인 Docker 설치 과정 불필요.

#### 외부 연계
| 항목 | 요구사항 | 비고 |
|------|----------|------|
| Ollama 서버 | GPU 서버에서 운영 중 | URL을 `.env`에 설정 |
| Ollama 모델 | gemma3:4b (또는 운영 모델) | GPU 서버에 사전 pull |

---

### 7-2. 개발 PC에서 할 일 (Phase 1~4)

#### Step 1: Docker Desktop 확인
```powershell
docker --version          # Docker Desktop 9.3.1
docker compose version    # v5.1.1
```
> 미설치 시: Docker Desktop for Windows 설치 (WSL2 백엔드 활성화)

#### Step 2: Docker 파일 작성 (Phase 1)
이 단계에서 아래 파일을 프로젝트에 추가:
```
smart-document-platform/
├── Dockerfile                  ← 백엔드 이미지
├── docker-compose.yml          ← 서비스 구성
├── .env.example                ← 설정 템플릿
├── .dockerignore               ← 빌드 제외
└── docker/
    ├── Dockerfile.nginx        ← 프론트엔드 이미지
    ├── nginx.conf              ← Nginx 설정
    └── config.docker.js        ← Docker 전용 프론트엔드 config
```

#### Step 3: 로컬 빌드·테스트 (Phase 3)

> 전제: Docker Desktop이 실행 중이어야 한다.

**3-1. Docker Desktop 상태 확인**

CMD 또는 PowerShell에서:
```powershell
docker --version          # 버전 출력되면 정상
docker compose version
```

**3-2. .env 파일 생성**
```powershell
cd C:\AHS_Proj\smart-document-platform
copy .env.example .env
notepad .env
```
수정할 항목:
- `OLLAMA_URL` — 로컬 Ollama라면 `http://host.docker.internal:11434` (기본값 그대로)
- GPU 서버가 따로 있다면 해당 IP로 변경 (예: `http://192.168.x.x:11434`)

> `host.docker.internal`은 Docker 컨테이너에서 호스트 PC를 가리키는 특수 주소.

**3-3. 이미지 빌드**
```powershell
cd C:\AHS_Proj\smart-document-platform
docker compose build
```
- 첫 빌드 **10~30분** 소요 (pip install + babeldoc ONNX ~500MB 다운로드)
- `backend`(sdp-backend)와 `nginx`(sdp-nginx) 이미지 2개 생성

**3-4. 컨테이너 실행**
```powershell
docker compose up -d
docker compose ps
```
- 두 컨테이너 모두 **Up (healthy)** / **running** 이면 정상
- 백엔드 healthcheck로 모델 로딩 완료까지 대기 (최대 ~2분)
- 이상 시: `docker compose logs`

**3-5. 브라우저 접속 및 서브시스템 검증**

`http://localhost` 접속 (포트 80, `.env`의 PORT 값).

| 순서 | 검증 항목 | 방법 |
|------|-----------|------|
| 1 | 인증 | testbot / test1234 로그인 → 세션 유지 → 로그아웃 |
| 2 | Launcher | 메뉴 목록 노출, 가이드 페이지 열기 |
| 3 | Explorer | 웹북 열기 → 검색 → AI 챗봇 (Ollama 연결 시) |
| 4 | Notebook | PDF 업로드 → 페이지 번역 시도 → 웹뷰 |
| 5 | Verify | 문서 업로드 → 비교 → 규칙 검증 |
| 6 | 관리자 설정 | 설정 변경 → 저장 → 재접속 후 유지 확인 |

**3-6. Nginx 보안 검증**

브라우저 주소창에서 직접 확인:

| URL | 기대 결과 |
|-----|-----------|
| `http://localhost/data/menu.json` | 정상 응답 (JSON) |
| `http://localhost/data/search-index.json` | 정상 응답 (JSON) |
| `http://localhost/data/glossary.json` | 정상 응답 (JSON) |
| `http://localhost/data/auth.db` | **403 Forbidden** |
| `http://localhost/data/settings.json` | **403 Forbidden** |
| `http://localhost/backend/` | **403 Forbidden** |
| `http://localhost/.env` | **403 Forbidden** |

**3-7. 데이터 영속성 확인**
```powershell
docker compose down
docker compose up -d
```
재접속 → 이전 계정·업로드 문서 유지되면 성공.

**3-8. 유용한 디버깅 명령어**
```powershell
docker compose logs -f              # 실시간 로그 (Ctrl+C 종료)
docker compose logs -f backend      # 백엔드만
docker compose exec backend bash    # 컨테이너 쉘 접속
docker compose exec backend pdf2zh --version   # pdf2zh 설치 확인
```

**3-9. 테스트 완료 후 정리**
```powershell
docker compose down
```

#### Step 4: 이미지 내보내기 (Phase 4)
```bash
# 이미지 tar 생성
docker save -o platform-v1.0.tar \
  smart-document-platform-backend \
  smart-document-platform-nginx

# 크기 확인 (예상 ~2.5~3GB)
ls -lh platform-v1.0.tar
```

#### Step 5: 반출 준비물 목록
USB 또는 네트워크로 리눅스 VM에 가져갈 파일:

| 파일/디렉토리 | 크기 | 용도 | 최초만/매번 |
|--------------|------|------|-----------|
| `platform-v1.0.tar` | ~3GB | Docker 이미지 | 매 버전 |
| `docker-compose.yml` | <1KB | 서비스 구성 | 변경 시 |
| `.env.example` | <1KB | 설정 템플릿 | 최초만 |
| `deploy.sh` | <1KB | 배포 스크립트 | 변경 시 |
| `data/` | 가변 | 초기 데이터 (빈 디렉토리 또는 기존) | 최초만 |
| `contents/` | 가변 | 웹북 콘텐츠 | 최초 + 콘텐츠 추가 시 |
| `models/` | ~4.4GB | ML 모델 | 최초만 (거의 안 바뀜) |
| `backups/` | 가변 | 빈 디렉토리 | 최초만 |

> Docker는 리눅스 VM에 이미 설치되어 있으므로 (29.3.1) 오프라인 패키지 반입 불필요.

> **버전 업데이트 시**: `platform-v1.0.tar` + `docker-compose.yml` (변경 시)만 가져가면 됨.
> data/, contents/, models/ 등 볼륨 데이터는 기존 것 유지.

---

### 7-3. 리눅스 VM에서 할 일

#### 최초 설치 (1회)

```bash
# 0. Docker 확인 (이미 설치됨)
docker --version          # 29.3.1
docker compose version    # v5.1.1

# 1. 배포 디렉토리 구성
sudo mkdir -p /opt/smart-document-platform
cd /opt/smart-document-platform

# 3. 반출 파일 배치
#    platform-v1.0.tar, docker-compose.yml, .env.example
#    data/, contents/, models/, backups/ 디렉토리

# 4. 설정
cp .env.example .env
nano .env    # PORT, OLLAMA_URL 등 환경에 맞게 수정

# 5. 이미지 로드 + 실행
docker load < platform-v1.0.tar
docker compose up -d

# 6. 확인
docker compose ps
docker compose logs -f      # Ctrl+C로 중단
# 브라우저에서 http://서버주소:PORT 접속
```

#### 버전 업데이트 (반복)

```bash
cd /opt/smart-document-platform
docker compose down                           # 서비스 중지
docker load < platform-v1.2.tar               # 새 이미지 로드
cp new-docker-compose.yml docker-compose.yml  # 설정 교체 (변경 시만)
docker compose up -d                          # 서비스 시작
docker compose ps                             # 확인
```

> 번역 작업이 없는 시간대에 수행 권장 (진행 중 번역은 중단됨).

---

## 8. 운영 매뉴얼 (비전문가용)

> Docker 경험이 없는 운영자 대상.
> 모든 명령은 리눅스 VM의 배포 디렉토리에서 실행.

---

### 8-1. 개념 이해

```
이미지(image)     = 설치 CD      → 플랫폼 코드가 담겨 있음 (읽기 전용)
컨테이너(container) = 실행 중 프로그램  → CD를 넣고 실행한 상태
볼륨(volume)      = 외부 저장장치   → 사용자 데이터 (프로그램과 무관하게 유지)

→ 이미지를 새 버전으로 교체해도 볼륨(데이터)은 그대로 남는다
```

**우리 시스템 대응:**
- 이미지 = 플랫폼 코드 (업데이트 시 교체)
- 볼륨 = `data/`, `contents/`, `models/`, `backups/` (**절대 삭제 금지**)
- `.env` = 설정 파일 (포트, Ollama 주소 등)

### 8-2. 배포 디렉토리 구조

```
/opt/smart-document-platform/       ← 배포 루트
├── docker-compose.yml              ← 서비스 구성
├── .env                            ← 설정 (직접 편집 가능)
├── data/                           ← [보존] 사용자 데이터
│   ├── auth.db                     ←   계정 정보
│   ├── analytics.db                ←   통계
│   ├── settings.json               ←   관리자 설정
│   ├── translator/                 ←   번역 작업물
│   ├── verify/                     ←   검증 데이터
│   └── ...
├── contents/                       ← [보존] 웹북 콘텐츠
├── models/                         ← [보존] AI 모델 (4.4GB)
├── backups/                        ← [보존] 문서 편집 백업
└── logs/                           ← 서버 로그
```

### 8-3. 서비스 관리

```bash
# 시작
docker compose up -d

# 종료
docker compose down

# 재시작
docker compose restart

# 백엔드만 재시작
docker compose restart backend

# 상태 확인 (모두 "Up"이면 정상)
docker compose ps

# 로그 보기 (Ctrl+C로 중단)
docker compose logs -f

# 백엔드 로그만
docker compose logs -f backend

# 최근 100줄만
docker compose logs --tail 100
```

### 8-4. 버전 업데이트

상세 절차는 **7-2절 (개발 PC)**, **7-3절 (리눅스 VM)** 참조.

요약: 개발 PC에서 `docker compose build` → `docker save` → tar 반출 → 리눅스 VM에서 `docker load` → `docker compose up -d`. 데이터 볼륨은 그대로 유지됨.

> **주의**: 서비스 중지 시점에 진행 중이던 번역은 중단되며 자동 재개되지 않음.  
> 가능하면 번역 작업이 없는 시간대에 업데이트 수행.

### 8-5. 설정 변경

**인프라 설정 (`.env`):**
```bash
nano .env                                     # 편집
docker compose down && docker compose up -d   # 재시작 필요
```

**기능 설정 (웹 관리자):**
- 브라우저 → 플랫폼 접속 → admin 로그인 → 설정 메뉴
- AI 모델, 검색, 번역 옵션 등 — 대부분 즉시 반영 (일부 재시작 필요)

### 8-6. 백업 / 복원

**백업:**
```bash
docker compose down                                         # 서비스 중지 (DB 안전)
tar czf backup-$(date +%Y%m%d).tar.gz data/ backups/        # 백업 생성
docker compose up -d                                        # 서비스 재시작
```

**복원:**
```bash
docker compose down
mv data/ data-old/ && mv backups/ backups-old/              # 기존 보관 (안전장치)
tar xzf backup-20260406.tar.gz                              # 복원
docker compose up -d
# 정상 확인 후 data-old/, backups-old/ 삭제
```

### 8-7. 웹북 콘텐츠 추가

```bash
cp -r new-webbook/ contents/                  # 파일 복사
docker compose restart backend                # 인덱스 반영
# 또는 웹 관리자 메뉴에서 검색 인덱스 재생성
```

### 8-8. 트러블슈팅

**서비스가 안 뜰 때:**
```bash
docker compose ps                             # Exited 컨테이너 확인
docker compose logs backend                   # 에러 메시지 확인
# 흔한 원인: .env 없음, 포트 충돌, models/ 미배치
```

**페이지가 안 열릴 때:**
```bash
docker compose logs nginx
# 포트 확인: .env의 PORT 값 = 브라우저 주소 포트
```

**AI 기능이 안 될 때:**
```bash
docker compose exec backend curl -s ${OLLAMA_URL}/api/tags
# 모델 목록이 나오면 정상. 안 되면 .env OLLAMA_URL 확인 + GPU 서버 상태 확인
```

**디스크 부족:**
```bash
df -h                                         # 시스템 디스크
docker system df                              # Docker 디스크
docker image prune -a                         # 미사용 이미지 정리
```

### 8-9. 절대 하면 안 되는 것

| 명령 | 결과 |
|------|------|
| `docker compose down -v` | 볼륨(데이터) 전부 삭제 — 계정, 작업물 복구 불가 |
| `rm -rf data/` | 사용자 데이터 전부 삭제 |
| `docker system prune -a --volumes` | 모든 Docker 볼륨 삭제 |
| `.env` 파일 삭제 | 설정 유실 — 서비스 시작 불가 |

### 8-10. 첫 설치 (최초 1회)

상세 절차는 **7-3절 (리눅스 VM 최초 설치)** 참조.

### 8-11. 정기 점검

| 주기 | 항목 | 방법 |
|------|------|------|
| 매일 | 서비스 정상 | `docker compose ps` — 모두 "Up" |
| 매주 | 디스크 여유 | `df -h` — 80% 이하 유지 |
| 매주 | 로그 크기 | `du -sh logs/` — 비정상 증가 여부 |
| 매월 | 데이터 백업 | 8-6절 절차 수행 |
| 필요 시 | 이미지 정리 | `docker image prune` |

---

## 비고
- 기존 윈도우 직접 실행 방식은 유지됨 (Docker 파일 추가만)
- Ollama는 Docker에 포함하지 않음 (기존대로 별도 GPU 서버 연계)
- `backend/packages/*.whl`은 윈도우용 — Docker 빌드 시 pip install로 리눅스 네이티브 설치
- Phase 5 완료 시 섹션 7을 `OPERATIONS.md`로 별도 산출

---

## 9. Phase 1 완료 리뷰 (2026-04-07)

### 산출물

| 파일 | 크기 | 계획서 대응 |
|------|------|------------|
| `Dockerfile` | 1.4KB | 3-4절 백엔드 이미지 |
| `docker/Dockerfile.nginx` | 0.7KB | 3-5절 프론트엔드 이미지 |
| `docker/nginx.conf` | 2.2KB | 3-2절 Nginx 라우팅 |
| `docker/config.docker.js` | 2.4KB | 3-3절 config.js 이중 환경 |
| `docker-compose.yml` | 1.3KB | 1절 목표 아키텍처 |
| `.env.example` | 0.5KB | 3-1절 외부 설정 |
| `.dockerignore` | 0.8KB | Phase 1 빌드 최적화 |
| `deploy.sh` | 1.7KB | Phase 4 배포 스크립트 |
| `.gitignore` 추가분 | — | `.env`, `*.tar` 제외 |

### 계획서 대비 변경/보강 사항

1. **healthcheck 추가** — `docker-compose.yml`에 `/api/health` 기반 헬스체크 + Nginx `depends_on: condition: service_healthy`. 계획서에 없었으나 백엔드 모델 로딩 시간을 고려하면 필수
2. **config.js 캐시 금지** — `location = /js/config.js`에 `Cache-Control: no-store` 추가. 7일 캐시가 걸리면 설정 변경이 브라우저에 반영 안 됨
3. **`.git` 차단 강화** — `location ~ /\.git`(정규식)으로 `.gitignore` 등도 차단
4. **CORS 정리** — `http://nginx`(컨테이너 내부 이름, 브라우저 Origin 아님) 제거
5. **logs 경로 통일** — 계획서 1절 아키텍처(`./logs/`)와 일치하도록 `./logs:/app/backend/logs` 적용
6. **deploy.sh 안전장치** — `cd "$(dirname "$0")"` + BSD grep 호환 포트 출력
7. **`try_files` 변경** — 계획서 3-2절은 `/index.html` SPA 폴백이었으나, 플랫폼은 multi-page이므로 `=404`가 적절. 계획서 예시와 의도적 차이
8. **`docs/` COPY 추가** — 계획서 3-5절에 없었으나 가이드 페이지 서빙에 필요

### Phase 2에서 처리할 항목

| 항목 | 근거 | 우선도 |
|------|------|--------|
| `config.py` `OLLAMA_MODEL` 환경변수 연동 | `os.getenv()` 미사용 → `.env`의 `OLLAMA_MODEL` 값이 첫 기동 시 무시됨 | 필수 |
| `config.py` `LLM_PROVIDER` 등 추가 환경변수 | Docker 환경에서 settings.json 없이도 `.env`로 제어 가능하면 편의성 향상 | 선택 |

### 검증 대기 항목 (Phase 3)

- [ ] `backend/packages/`(152개 whl, 윈도우 전용)가 `.dockerignore`로 제외 → pip install이 리눅스 네이티브로 정상 설치되는지
- [ ] babeldoc ONNX 캐시가 빌드 시 다운로드되는지 (실패 시 WARN 출력, 런타임 재시도)
- [ ] `tools/` subprocess 호출이 Docker 내 경로(`/app/tools/`)에서 정상 동작하는지
- [ ] `data/` 화이트리스트 3개만 Nginx에서 접근 가능하고 나머지 403인지
- [ ] 쿠키 `samesite=lax` + Nginx 프록시 조합에서 세션이 유지되는지
- [ ] `css/images/` 내 `cloud.mp4`가 `.dockerignore`에 걸리지 않는지 → .dockerignore에 `*.mp4` 없으므로 안전

### 알려진 제한

- `WORD_COM_PREPROCESS`(Win32 COM)는 Linux Docker에서 사용 불가 → `config.py` 기본값 `False`이므로 영향 없음
- `pywin32`는 requirements.txt에서 주석 처리됨 → Docker 빌드에 영향 없음

### Phase 2 완료 리뷰 (2026-04-07)

**변경 사항**: `config.py:13` 1행 — `OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")`

**검증 결과**:

| 항목 | 결과 |
|------|------|
| 환경변수 오버라이드 | PASS — `os.getenv()` 동적 치환 확인 |
| 경로 정합성 (9개 경로) | PASS — `Path(__file__).parent.parent` = `/app/` 기준, 볼륨 매핑과 일치 |
| .dockerignore vs COPY 충돌 | PASS — Nginx/Backend 모두 충돌 없음 |
| 볼륨 대상 제외 | PASS — data/, contents/, models/, backups/, logs/ 모두 제외 |
| Nginx 라우팅 규칙 | PASS — 화이트리스트 3개, 보안 차단 7개, 프록시/스트리밍 정상 |
| config.js 키 정합성 | PASS — 5개 CONFIG 블록 키 완전 일치 |
| docker-compose.yml 구조 | PASS — YAML 파싱, 서비스 2개, healthcheck, depends_on 확인 |
| 윈도우 기존 실행 호환 | PASS — 백엔드 API 200, 프론트엔드 정적 파일 200 |
| 브라우저 테스트 | PASS — 로그인 → Launcher → Explorer → Notebook → Verify 모두 정상 로드 |

**미변경 (계획서 원문 준수)**:
- `CORS_ORIGINS` — 기존 `os.getenv()` 유지, 추가 변경 불필요
- `config.js` — 원본 수정 없음 (Docker에서 Nginx 오버라이드)
- `LLM_PROVIDER` 등 — 선택 사항, settings.json 런타임 제어 가능하므로 생략
