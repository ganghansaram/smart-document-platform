# Docker 배포 운영 가이드

Smart Document Platform을 Docker로 배포하고 운영하는 절차를 안내합니다.
Docker 경험이 없어도 이 문서의 절차를 따라 설치, 업데이트, 백업, 문제 해결을 수행할 수 있습니다.

## 목차

**PART 1. 개요**
- [1. 시스템 구조](#1-시스템-구조)
- [2. 디렉토리와 설정 파일](#2-디렉토리와-설정-파일)

**PART 2. 배포 가이드**
- [3. 버전 업데이트 (전체 이미지)](#3-버전-업데이트-전체-이미지)
- [4. 코드 패치 (간편 업데이트)](#4-코드-패치-간편-업데이트)
- [5. 최초 설치](#5-최초-설치)
- [6. 개발 PC에서 이미지 빌드](#6-개발-pc에서-이미지-빌드)

**PART 3. 운영 가이드**
- [7. 서비스 관리](#7-서비스-관리)
- [8. 설정 변경](#8-설정-변경)
- [9. 백업과 복원](#9-백업과-복원)
- [10. 웹북 콘텐츠 추가](#10-웹북-콘텐츠-추가)
- [11. 정기 점검](#11-정기-점검)
- [12. 문제 해결](#12-문제-해결)

**PART 4. 부록**
- [13. 파일 전송 주의사항](#13-파일-전송-주의사항)
- [14. 기술 참고](#14-기술-참고)

---

# PART 1. 개요

## 1. 시스템 구조

### 1-1. 배포 아키텍처

플랫폼은 2개의 Docker 컨테이너로 구성됩니다.
외부에는 Nginx 포트 1개만 노출되며, 백엔드는 내부 통신만 사용합니다.

```
리눅스 서버
│
├── Nginx 컨테이너 (포트 80, 유일하게 외부 노출)
│   ├── HTML/JS/CSS 서빙
│   ├── /api/* → 백엔드 리버스 프록시
│   └── 보안 차단 (민감 파일 403)
│
├── Backend 컨테이너 (내부 포트 8000, 외부 비노출)
│   ├── FastAPI 서버
│   ├── 검색, 번역, 검증 API
│   └── pdf2zh 번역 엔진
│
└── 볼륨 마운트 (호스트 폴더 → 컨테이너)
    ├── data/      사용자 데이터
    ├── contents/  웹북 콘텐츠
    ├── models/    AI 모델 (읽기 전용)
    ├── backups/   편집 백업
    └── logs/      서버 로그
```

Ollama(AI 모델 서버)는 별도 GPU 서버에서 운영하며 Docker에 포함하지 않습니다.

### 1-2. 핵심 개념

| 용어 | 비유 | 설명 |
|------|------|------|
| **이미지** | 설치 CD | 플랫폼 코드가 담긴 읽기 전용 파일. 업데이트 시 새 이미지로 교체 |
| **컨테이너** | 실행 중인 프로그램 | 이미지 기반으로 실행된 상태. 중지/시작 자유로움 |
| **볼륨** | 외부 저장장치 | 사용자 데이터 저장 폴더. 이미지 교체해도 유지 |

**핵심 원칙**: 이미지(코드)를 교체해도 볼륨(데이터)은 그대로 남습니다. 업데이트 시 사용자 계정, 문서, 설정이 유실되지 않습니다.

---

## 2. 디렉토리와 설정 파일

### 2-1. 서버 디렉토리 구조

`[보존]` 표시된 폴더는 사용자 데이터이므로 삭제하면 안 됩니다.

```
/opt/smart-document-platform/       ← 배포 루트
├── docker-compose.yml              ← 서비스 구성
├── .env                            ← 환경 설정
├── deploy.sh                       ← 배포 스크립트
├── patch-apply.sh                  ← 패치 스크립트
│
├── data/                           ← [보존] 사용자 데이터
│   ├── auth.db                     ←   계정 정보
│   ├── analytics.db                ←   사용 통계
│   ├── settings.json               ←   관리자 설정
│   ├── search-index.json           ←   키워드 검색 인덱스
│   ├── vector-index/               ←   AI 벡터 인덱스
│   ├── menu.json                   ←   메뉴 구조
│   ├── translator/                 ←   번역 작업물
│   └── verify/                     ←   검증 데이터
├── contents/                       ← [보존] 웹북 콘텐츠
├── models/                         ← [보존] AI 모델 (~4.4GB)
├── backups/                        ← [보존] 편집 백업
└── logs/                           ← 서버 로그
```

### 2-2. .env 설정 파일

`.env` 하나로 모든 인프라 설정을 관리합니다. `.env.example`을 복사하여 환경에 맞게 수정합니다.

| 항목 | 기본값 | 설명 |
|------|--------|------|
| `PORT` | `80` | 외부 접속 포트 |
| `OLLAMA_URL` | `http://gpu-server:11434` | Ollama GPU 서버 주소 |
| `EMBEDDING_BACKEND` | `local` | 임베딩 실행 위치: `local`(백엔드 내부) / `ollama`(Ollama 서버 위임) |
| `DATA_DIR` | `./data` | 사용자 데이터 경로 |
| `CONTENTS_DIR` | `./contents` | 웹북 콘텐츠 경로 |
| `MODELS_DIR` | `./models` | AI 모델 경로 |
| `BACKUPS_DIR` | `./backups` | 백업 경로 |

**AI 모델(`OLLAMA_MODEL`)과 검색 옵션 등 운영 설정은 브라우저 관리자 화면에서 변경합니다.** `.env`에는 포함하지 않습니다.

**`EMBEDDING_BACKEND` 선택 기준**

| 값 | 권장 상황 | 비고 |
|----|----------|------|
| `local` | 백엔드 컨테이너가 GPU에 접근 가능한 경우 | sentence-transformers가 백엔드 내부에서 직접 추론. 가장 빠름 |
| `ollama` | 백엔드 컨테이너에 GPU 패스스루가 없는 경우 | Ollama GPU 서버로 HTTP 위임. CPU 폴백 대비 훨씬 빠름 |

GPU 없는 서버에서 `local`로 운영하면 CPU 폴백되어 임베딩이 **10분 이상** 걸릴 수 있습니다. 이 경우 `.env`에 `EMBEDDING_BACKEND=ollama`를 추가하고 Ollama 서버에 `bge-m3` 모델이 설치되어 있는지 확인합니다.

`.env` 변경 후에는 반드시 `docker compose down && docker compose up -d`로 재시작해야 적용됩니다.

### 2-3. 환경 요구사항

**개발 PC (Windows)**

| 항목 | 버전 |
|------|------|
| Windows | 10/11 (WSL2 활성화) |
| Docker Desktop | 4.x 이상 |

**리눅스 서버**

| 항목 | 요구사항 |
|------|----------|
| Docker Engine | 20.x 이상 |
| Docker Compose | v2.x 이상 (plugin) |
| 디스크 여유 | 15GB 이상 |
| 메모리 | 4GB 이상 |

Ollama 서버가 연결되지 않아도 기본 기능(문서 탐색, 검색, 번역, 비교)은 정상 동작합니다. AI 채팅/요약/Q&A만 비활성화됩니다.

---

# PART 2. 배포 가이드

## 3. 버전 업데이트 (전체 이미지)

서버에서 운영 중인 플랫폼을 새 버전으로 교체하는 절차입니다.

### 3-1. 반출 파일 준비

빌드 시 개발자(Claude)가 **이번에 가져갈 파일 목록**을 안내합니다.
매번 동일하지 않으며, 변경 내용에 따라 달라집니다. 아래는 전체 목록과 조건입니다.

| 파일 | 매번 필수 | 조건부 | 설명 |
|------|:--------:|:-----:|------|
| `platform-vX.X.tar` | O | | Docker 이미지 (약 4GB) |
| `docker-compose.yml` | | O | compose 구조가 변경된 경우 |
| `deploy.sh` | | O | 스크립트가 변경된 경우 |
| `patch-apply.sh` | | O | 스크립트가 변경된 경우 |
| `data/` | | O | DB 스키마, 규칙 JSON, 인덱스 등이 변경된 경우 |
| `contents/` | | O | 가이드, 웹북 콘텐츠가 변경된 경우 |
| `models/` | | O | AI 모델이 변경된 경우 (드묾) |
| `.env` | | | 서버에서 직접 관리 — 가져가지 않음 |

> **빌드 결과 안내에 "반출 파일 목록"이 포함됩니다.** 해당 목록에 있는 파일만 USB/네트워크로 서버에 전달하면 됩니다.

### 3-2. 리눅스 서버에서 할 일

아래 절차를 **위에서 아래로 순서대로** 실행합니다.

**Step 1. 서비스 종료**

```bash
cd /opt/smart-document-platform
docker compose down
```

**Step 2. 파일 덮어쓰기**

반출 목록에 있는 파일만 복사합니다. 권한 오류 시 `sudo cp`를 사용합니다 ([PART 4](#13-파일-전송-주의사항) 참조).

```bash
# 예시: 이번 반출 목록이 tar + docker-compose.yml + data/ + contents/ 인 경우
cp -f platform-vX.X.tar /opt/smart-document-platform/
cp -f docker-compose.yml /opt/smart-document-platform/
cp -rf data/ /opt/smart-document-platform/
cp -rf contents/ /opt/smart-document-platform/
```

> `.env`는 덮어쓰지 않습니다. 서버 환경에 맞게 직접 관리하는 파일입니다.

**Step 3. .env 확인 (필요한 경우만)**

빌드 안내에 ".env 수정 필요"라고 명시된 경우에만 수행합니다.

```bash
nano /opt/smart-document-platform/.env
# 안내받은 항목만 수정 → Ctrl+O → Enter(저장) → Ctrl+X(종료)
```

**Step 4. 배포 실행**

```bash
cd /opt/smart-document-platform
./deploy.sh platform-vX.X.tar
```

`deploy.sh`가 자동으로 수행하는 작업:
1. Docker 이미지 로드
2. `.env` 존재 확인
3. 데이터 디렉토리 생성 (없는 경우)
4. 서비스 시작
5. 미사용 이미지 정리

**Step 5. 확인**

```bash
docker compose ps          # 두 컨테이너 모두 "Up" / "healthy"
curl -s http://localhost/api/health   # {"status":"ok"} 확인
```

브라우저에서 `http://서버주소`에 접속하여 로그인, 각 서브시스템 동작을 확인합니다.

### 3-3. 롤백

문제 발생 시 이전 버전의 tar 파일로 되돌립니다.

```bash
cd /opt/smart-document-platform
./deploy.sh platform-v[이전버전].tar
```

진행 중이던 번역 작업은 서비스 종료 시 중단되며 자동 재개되지 않습니다. 가능하면 작업이 없는 시간대에 업데이트합니다.

---

## 4. 코드 패치 (간편 업데이트)

Python/JS/HTML/CSS 등 코드만 변경된 경우 전체 이미지 대신 패치 파일만 전송합니다.
패치 파일은 수 MB 수준이라 전송이 빠릅니다.

### 4-1. 사용 가능 여부

| 변경 내용 | 업데이트 방법 |
|-----------|-------------|
| Python, JS, HTML, CSS 코드만 변경 | **패치** (이 장) |
| `Dockerfile`, `requirements.txt` 변경 | **전체 이미지** ([3장](#3-버전-업데이트-전체-이미지)) |
| `docker-compose.yml`, 새 pip/apt 패키지 | **전체 이미지** ([3장](#3-버전-업데이트-전체-이미지)) |

### 4-2. 개발 PC에서 할 일

Claude Code에서 `/docker-release --patch` 실행 → `patch-vX.X.X.tar.gz` 생성 → 서버로 전달

### 4-3. 리눅스 서버에서 할 일

```bash
cd /opt/smart-document-platform
./patch-apply.sh patch-vX.X.X.tar.gz
```

패치 스크립트가 컨테이너 내부에 파일을 복사하고 자동으로 재시작합니다. 완료 후 브라우저에서 정상 동작을 확인합니다.

---

## 5. 최초 설치

리눅스 서버에 플랫폼을 처음 설치할 때 한 번만 수행합니다.

### 5-1. Docker 확인

```bash
docker --version            # 20.x 이상
docker compose version      # v2.x 이상
```

### 5-2. 사용자 UID 확인 (중요)

플랫폼 컨테이너는 보안을 위해 **비특권 사용자(`appuser`)로 실행**됩니다. 기본 UID는 **1000**입니다. 배포 디렉토리 소유자 UID와 일치해야 볼륨 마운트된 `data/`, `contents/`, `backups/`에 쓰기 권한을 갖습니다.

```bash
# 배포 디렉토리의 소유자 UID 확인
cd /opt/smart-document-platform
ls -ln data/ | head -3
# 예: drwxr-xr-x 5 1000 1000 ...     ← UID=1000 (기본값과 일치 → OK)
# 예: drwxr-xr-x 5 1001 1001 ...     ← UID=1001 (다름 → 아래 조치 필요)
```

**UID가 1000이 아니면** 배포 전에 두 가지 방법 중 하나를 선택합니다:

**방법 A — 컨테이너 이미지를 해당 UID로 재빌드 (권장)**

tar 파일을 만들기 전 개발 PC에서:

```bash
docker compose build --build-arg APP_UID=1001 --build-arg APP_GID=1001
docker save -o platform-vX.X.tar smart-document-platform-backend smart-document-platform-nginx
```

**방법 B — 서버의 데이터 소유권 변경**

```bash
sudo chown -R 1000:1000 /opt/smart-document-platform/data /opt/smart-document-platform/contents /opt/smart-document-platform/backups /opt/smart-document-platform/logs
```

> 기존에 다른 UID로 실행 중이던 서비스가 있으면 방법 B는 권장하지 않습니다. 방법 A가 안전합니다.

### 5-3. 디렉토리 준비 및 파일 배치

```bash
sudo mkdir -p /opt/smart-document-platform
cd /opt/smart-document-platform
```

아래 파일을 USB/네트워크에서 이 디렉토리로 복사합니다. 권한 오류 발생 시 `sudo mv` 또는 `sudo cp`를 사용합니다([PART 4](#13-파일-전송-주의사항) 참조).

| 파일 | 필수 여부 | 설명 |
|------|---------|------|
| `platform-vX.X.tar` | 필수 | Docker 이미지 (약 3GB) |
| `docker-compose.yml` | 필수 | 서비스 구성 |
| `.env.example` | 필수 | 설정 템플릿 |
| `deploy.sh` | 필수 | 배포 스크립트 |
| `patch-apply.sh` | 선택 | 패치 스크립트 (이후 업데이트용) |
| `data/` | 필수 | 초기 데이터 (계정, 인덱스 등) |
| `contents/` | 필수 | 웹북 콘텐츠 |
| `models/` | 필수 | AI 모델 (~4.4GB) |
| `backups/` | 선택 | 빈 폴더 (생성됨) |

`data/` 폴더 필수 파일:

| 파일 | 없으면 |
|------|--------|
| `auth.db` | 로그인 불가 (서버 시작 시 자동 생성됨) |
| `search-index.json` | 문서 검색 안 됨 |
| `vector-index/` | AI 챗봇 응답 불가 |
| `menu.json` | 메뉴 비어있음 |
| `settings.json` | 기본값으로 동작 (문제없음) |

### 5-4. 설정 파일 생성

```bash
cp .env.example .env
nano .env
```

수정할 항목:
- `OLLAMA_URL` — GPU 서버 실제 주소 (예: `http://192.168.1.100:11434`)
- `PORT` — 서비스 포트 (기본 80, 방화벽에 등록된 포트 사용)

저장 후 편집기 종료 (nano: `Ctrl+O` → `Enter` → `Ctrl+X`).

### 5-5. 배포 실행

```bash
./deploy.sh platform-vX.X.tar
```

`deploy.sh`가 자동으로 다음을 수행합니다:
1. Docker 이미지 로드
2. `.env` 존재 확인 (없으면 `.env.example`에서 복사)
3. 데이터 디렉토리 생성
4. 서비스 시작
5. 미사용 이미지 정리

### 5-6. 접속 확인

```bash
docker compose ps   # 두 컨테이너 모두 "Up" / "healthy"
```

브라우저에서 `http://서버주소:PORT` 접속 → `testbot` / `test1234`로 로그인 → 각 서브시스템(Explorer, Notebook, Verify) 진입 확인.

---

## 6. 개발 PC에서 이미지 빌드

개발 PC(Windows)에서 이미지를 빌드하고 로컬 테스트 후 서버로 반출하는 절차입니다.

### 6-1. 사전 확인

PowerShell 또는 명령 프롬프트에서:

```bash
docker --version
docker compose version
```

버전이 출력되지 않으면 Docker Desktop이 실행 중인지 확인합니다.

### 6-2. .env 생성 및 빌드

```bash
cd C:\AHS_Proj\smart-document-platform
copy .env.example .env
notepad .env
```

개발 PC에서는 `OLLAMA_URL`을 `http://host.docker.internal:11434`로 설정합니다 (Docker 컨테이너에서 Windows 호스트를 가리키는 특수 주소).

```bash
docker compose build
```

첫 빌드는 10~30분 소요됩니다(Python 패키지 + AI 모델 약 500MB 다운로드). 이후는 변경분만 처리하므로 빠릅니다.

### 6-3. 로컬 테스트

```bash
docker compose up -d
docker compose ps
```

`http://localhost` 접속 → 런처 화면 표시 확인. 백엔드는 모델 로딩에 최대 2분 소요됩니다.

### 6-4. 기능 검증

| 항목 | 확인 방법 |
|------|-----------|
| 인증 | `testbot` / `test1234` 로그인 → 세션 유지 |
| Explorer | 웹북 열기 → 검색 → AI 채팅 (Ollama 연결 시) |
| Notebook | PDF 업로드 → 페이지 번역 → 웹뷰 |
| Verify | 문서 업로드 → 비교 → 규칙 검증 |
| 관리자 설정 | 설정 변경 → 저장 → 재접속 후 유지 확인 |

### 6-5. 보안 검증

브라우저 주소창에 직접 입력하여 확인합니다.

| URL | 기대 결과 |
|-----|-----------|
| `http://localhost/data/menu.json` | 정상 응답 (JSON) |
| `http://localhost/data/search-index.json` | 정상 응답 |
| `http://localhost/data/auth.db` | **403 Forbidden** |
| `http://localhost/data/settings.json` | **403 Forbidden** |
| `http://localhost/backend/` | **403 Forbidden** |
| `http://localhost/.env` | **403 Forbidden** |

### 6-6. 이미지 내보내기

```bash
docker compose down
docker save -o platform-vX.X.tar smart-document-platform-backend smart-document-platform-nginx
docker image prune -f
```

생성된 tar 파일 크기는 약 3GB입니다. USB/네트워크로 리눅스 서버에 전달합니다.

### 6-7. 개발 모드 (bind mount, 재빌드 없이 변경 즉시 반영)

로컬 소스를 수정할 때마다 `docker compose build`를 반복하지 않고, 호스트 파일을 컨테이너에 직접 마운트하여 **즉시 반영**할 수 있습니다. `docker-compose.override.yml`이 이 역할을 담당하며, `docker compose up` 실행 시 자동으로 병합됩니다.

#### 개발 모드 실행 (기본)

```bash
docker compose up -d
```

`docker-compose.override.yml`이 자동으로 적용되어:
- `css/`, `js/`, `docs/`, `*.html`, `favicon.svg` → 호스트 파일 그대로 마운트
- `backend/`, `tools/` → 호스트 파일 그대로 마운트
- `docker/nginx.dev.conf` → `sendfile off`, 캐시 무효화 (bind mount 호환 모드)
- `docker/config.docker.js` → 호스트 파일 그대로 마운트

#### 프로덕션 모드 실행 (override 무시)

리눅스 서버 배포나 이미지 스모크 테스트처럼 **이미지 내 파일만** 쓰려면 base compose 파일을 명시적으로 지정합니다.

```bash
docker compose -f docker-compose.yml up -d
```

#### 변경 반영 방법

| 변경 유형 | 반영 방법 |
|-----------|-----------|
| HTML / CSS / JS 편집 | 브라우저 **강제 새로고침** (Ctrl+F5) 또는 DevTools "Disable cache" 체크 |
| 백엔드 Python 편집 | `docker compose restart backend` (`python main.py`는 hot-reload 미지원) |
| `docker/nginx.dev.conf` 편집 | `docker compose restart nginx` |
| `docker/nginx.conf` 편집 | 프로덕션 config — 재빌드 필요 (`docker compose build nginx`) |
| `Dockerfile*` 편집 | 전체 재빌드 (`docker compose build`) |

#### 주의사항

- `/js/config.js`는 Nginx alias로 `docker/config.docker.js`를 서빙합니다. 로컬 `js/config.js`를 수정해도 도커에 반영되지 않으니, 도커용 설정은 `docker/config.docker.js`를 직접 수정하세요 (Plan-31 Phase 3에서 단일화 예정).
- 개발 모드에서는 `nginx.dev.conf`가 7일 캐시 대신 `no-store`를 사용하므로, 일반 새로고침(F5)으로도 반영이 빠르지만, 브라우저 자체 메모리 캐시가 있으면 강제 새로고침(Ctrl+F5)이 확실합니다.
- 프로덕션 이미지 빌드·배포 시에는 override를 반드시 제외하세요 (`-f docker-compose.yml` 명시).

---

# PART 3. 운영 가이드

## 7. 서비스 관리

배포 디렉토리(`/opt/smart-document-platform`)에서 실행합니다.

### 7-1. 시작 / 종료 / 재시작

| 동작 | 명령어 |
|------|--------|
| 시작 | `docker compose up -d` |
| 종료 | `docker compose down` |
| 재시작 | `docker compose restart` |
| 백엔드만 재시작 | `docker compose restart backend` |

**`.env`를 수정한 경우 `restart`로는 반영되지 않습니다.** 반드시 `docker compose down && docker compose up -d`로 컨테이너를 재생성해야 합니다.

### 7-2. 상태 및 로그 확인

| 동작 | 명령어 |
|------|--------|
| 컨테이너 상태 | `docker compose ps` |
| 전체 로그 (실시간) | `docker compose logs -f` |
| 백엔드 로그만 | `docker compose logs -f backend` |
| Nginx 로그만 | `docker compose logs -f nginx` |
| 최근 100줄 | `docker compose logs --tail 100` |

### 7-3. 컨테이너 내부 접속 (디버깅)

| 동작 | 명령어 |
|------|--------|
| 백엔드 쉘 접속 | `docker compose exec backend bash` |
| pdf2zh 확인 | `docker compose exec backend pdf2zh --version` |
| Ollama 연결 확인 | `docker compose exec backend curl -s $OLLAMA_URL/api/tags` |

---

## 8. 설정 변경

설정은 두 곳에서 관리됩니다.

| 종류 | 위치 | 재시작 필요 |
|------|------|-----------|
| **인프라 설정** (포트, Ollama 주소, 경로) | `.env` 파일 | 필요 |
| **운영 설정** (AI 모델, 검색 옵션, 번역 옵션 등) | 웹 관리자 화면 | 대부분 불필요 |

### 8-1. .env 수정 (인프라 설정)

```bash
cd /opt/smart-document-platform
nano .env
# 값 수정 후 저장

docker compose down
docker compose up -d
```

### 8-2. 웹 관리자 설정 (운영 설정)

브라우저에서 admin 계정으로 로그인 → 헤더의 설정(톱니바퀴) 메뉴 → 탭에서 항목 변경 → 저장.

대부분의 설정은 즉시 반영됩니다. 저장 시 "재시작 필요" 안내가 뜨는 항목은 `docker compose down && docker compose up -d`로 재시작합니다.

---

## 9. 백업과 복원

### 9-1. 백업

```bash
cd /opt/smart-document-platform
docker compose down
tar czf backup-$(date +%Y%m%d).tar.gz data/ backups/
docker compose up -d
ls -lh backup-*.tar.gz
```

서비스를 잠시 중지하는 이유는 DB 파일 일관성 확보 때문입니다.

### 9-2. 복원

```bash
docker compose down
mv data/ data-old/ && mv backups/ backups-old/
tar xzf backup-20260408.tar.gz
docker compose up -d
# 정상 동작 확인 후
# rm -rf data-old/ backups-old/
```

기존 데이터는 `*-old`로 보관한 후, 복원 결과를 확인하고 삭제합니다.

---

## 10. 웹북 콘텐츠 추가

### 10-1. 웹 관리자에서 업로드 (권장)

브라우저에서 admin 계정으로 로그인 → Explorer 좌측 트리 메뉴의 업로드 기능 사용. 검색 인덱스가 자동 갱신됩니다.

### 10-2. 서버에서 직접 복사

```bash
cp -r new-webbook/ contents/
docker compose restart backend
```

또는 웹 관리자 메뉴에서 "검색 인덱스 재생성"을 실행합니다.

---

## 11. 정기 점검

| 주기 | 항목 | 확인 방법 | 기준 |
|------|------|-----------|------|
| 매일 | 서비스 상태 | `docker compose ps` | 모두 "Up" |
| 매주 | 디스크 여유 | `df -h` | 사용률 80% 이하 |
| 매주 | 로그 크기 | `du -sh logs/` | 비정상 증가 여부 |
| 매월 | 데이터 백업 | [9-1](#9-1-백업) 수행 | 백업 파일 생성 |
| 필요 시 | 미사용 이미지 정리 | `docker image prune` | 디스크 확보 |

---

## 12. 문제 해결

### 12-1. 서비스가 시작되지 않을 때

```bash
docker compose ps           # "Exited" 상태 확인
docker compose logs backend # 백엔드 에러
docker compose logs nginx   # Nginx 에러
```

| 증상 | 원인 및 해결 |
|------|-------------|
| backend "Exited" | `.env` 파일이 없거나 `models/` 폴더 없음. 파일 배치 확인 |
| nginx "Exited" | 포트 충돌. `.env`의 `PORT` 값이 이미 사용 중인지 확인 |
| nginx가 backend 대기 중 | backend 헬스체크 통과 전까지 정상. 최대 2분 대기 |

### 12-2. 페이지가 열리지 않을 때

| 확인 항목 | 조치 |
|-----------|------|
| `docker compose ps`로 상태 확인 | 중지 상태면 `docker compose up -d` |
| 브라우저 주소의 포트 번호 | `.env`의 `PORT` 값과 일치해야 함 |
| `docker compose logs nginx` | Nginx 에러 로그 확인 |

### 12-3. AI 기능이 동작하지 않을 때

```bash
docker compose exec backend curl -s $OLLAMA_URL/api/tags
```

모델 목록이 표시되면 연결 정상. 응답이 없으면 `.env`의 `OLLAMA_URL`과 GPU 서버 상태를 확인합니다.

AI 기능(채팅, 요약, Q&A)이 동작하지 않아도 문서 탐색, 검색, 번역, 비교 등 기본 기능은 정상 동작합니다.

### 12-4. 디스크 부족

```bash
df -h                       # 시스템 디스크
docker system df            # Docker 사용량
docker image prune -a       # 미사용 이미지 정리
du -sh logs/                # 로그 크기 확인
```

### 12-5. 임베딩/검색이 매우 느림 (벡터 인덱싱 10분 이상)

벡터 인덱싱이 평소보다 현저히 느리면 임베딩이 **CPU로 폴백**되고 있을 가능성이 높습니다.

| 확인 항목 | 조치 |
|-----------|------|
| GPU가 컨테이너에서 보이는지 | `docker compose exec backend python -c "import torch; print(torch.cuda.is_available())"` → `False`면 GPU 없음 |
| `EMBEDDING_BACKEND` 설정 확인 | `grep EMBEDDING_BACKEND .env` |

**해결 방안**: `.env`에 아래 한 줄 추가 후 재시작합니다. Ollama GPU 서버가 임베딩을 처리하게 됩니다.

```bash
echo 'EMBEDDING_BACKEND=ollama' >> .env
docker compose down && docker compose up -d
```

Ollama 서버에 `bge-m3` 모델이 설치되어 있어야 합니다(`ollama list`로 확인).

### 12-6. 관리자 설정에서 "재시작 필요" 라벨이 계속 표시될 때

`ollama_url`, `ollama_model` 등 일부 항목은 실제로는 재시작 없이 즉시 반영됩니다. UI 라벨이 오래된 분류로 남아있을 수 있으니, **저장 후 기능이 정상 동작하면 재시작하지 않아도 됩니다.** 실제 재시작이 필요한 항목은 `embedding_model`, `security.*`, `session.session_expiry_hours` 정도입니다.

### 12-7. "Permission denied" — 볼륨 파일 쓰기 실패

컨테이너가 비특권 사용자(`appuser`, UID 1000)로 실행되는데, 호스트 디렉토리 소유자가 다르면 발생합니다.

**증상 예시**

```
docker compose logs backend
# PermissionError: [Errno 13] Permission denied: '/app/data/auth.db'
```

**진단**

```bash
cd /opt/smart-document-platform
ls -ln data/ | head -3
# 소유자 UID가 1000이 아니면 원인 확정
```

**해결** — 두 가지 중 하나 선택 ([§5-2 사용자 UID 확인](#5-2-사용자-uid-확인-중요) 참조)

1. **이미지 재빌드** (권장): 개발 PC에서 `--build-arg APP_UID=<해당 UID>`로 재빌드 후 재배포
2. **소유권 일괄 변경**: `sudo chown -R 1000:1000 data/ contents/ backups/ logs/`

---

# PART 4. 부록

## 13. 파일 전송 주의사항

리눅스 서버로 파일을 옮길 때 자주 발생하는 문제와 해결 방법입니다.

### 13-1. 숨김 파일(.env)이 보이지 않음

`.`으로 시작하는 파일(`.env`, `.env.example` 등)은 리눅스에서 **숨김 파일**로 취급되어 기본적으로 표시되지 않습니다.

**CLI에서 확인**

```bash
ls          # .env가 안 보임
ls -a       # .env를 포함하여 전부 표시
ls -la      # 권한 정보와 함께 전체 표시
```

**GUI 파일 전송 도구 (AnywhereClient 등)**

메뉴에서 "숨김 파일 표시" 옵션을 활성화합니다. 도구마다 메뉴 이름이 다르지만 일반적으로 다음 위치에 있습니다:
- 보기(View) → 숨김 파일 표시(Show Hidden Files)
- 설정(Preferences) → 파일 표시 옵션

### 13-2. 권한이 필요한 디렉토리로 파일 이동

배포 디렉토리(`/opt/smart-document-platform` 등)는 일반 사용자 권한으로는 쓰기가 안 될 수 있습니다. 다운로드 폴더에서 작업 폴더로 옮길 때 `Permission denied` 오류가 발생하면 `sudo`를 사용합니다.

```bash
# 일반 이동/복사 (실패)
mv ~/Downloads/platform-v1.2.tar /opt/smart-document-platform/
# → Permission denied

# sudo 사용 (성공)
sudo mv ~/Downloads/platform-v1.2.tar /opt/smart-document-platform/
sudo cp ~/Downloads/docker-compose.yml /opt/smart-document-platform/
```

여러 파일을 한 번에 옮길 때:

```bash
sudo mv ~/Downloads/{platform-v1.2.tar,docker-compose.yml,.env.example} /opt/smart-document-platform/
```

이동 후 파일 소유자를 확인합니다:

```bash
cd /opt/smart-document-platform
ls -la
# 소유자가 root면 일반 사용자로 편집이 안 될 수 있음
# 필요 시 소유권 변경:
sudo chown -R $USER:$USER .
```

### 13-3. 파일 권한이 달라진 경우

USB나 Windows 경유로 옮긴 `.sh` 파일은 실행 권한이 없을 수 있습니다.

```bash
chmod +x deploy.sh patch-apply.sh
```

### 13-4. Windows 경유 시 SVG 파일 손상 (DRM)

일부 환경에서 Windows로 압축 해제한 SVG 파일이 회사 보안 솔루션(DRM)에 의해 자동 암호화되는 경우가 있습니다. 이 상태로 서버에 올리면 브라우저에서 다음과 같은 오류가 발생합니다:

```
XML Parsing Error: not well-formed
```

파일 내용 확인 방법:

```bash
head -c 20 contents/guide/images/arch-system.svg
# 정상: <svg xmlns=...
# 손상: %UBDRM... (DRM 시그니처)
```

**해결**: Windows 경유 없이 USB 등에서 **리눅스 서버로 직접 복사**합니다. PNG/JPG 파일은 DRM 대상이 아니라 영향 없습니다. SVG 파일만 영향받습니다.

---

## 14. 기술 참고

### 14-1. 절대 실행하지 말아야 할 명령어

아래 명령어는 데이터를 복구할 수 없게 삭제합니다.

| 명령어 | 결과 |
|--------|------|
| `docker compose down -v` | 볼륨(데이터) 전부 삭제. 복구 불가 |
| `rm -rf data/` | 사용자 데이터 전부 삭제 |
| `docker system prune -a --volumes` | 모든 Docker 데이터 삭제 |
| `.env` 파일 삭제 | 설정 유실 |

`docker compose down`은 컨테이너만 제거하며 볼륨은 유지합니다. **`-v` 옵션을 절대 붙이지 않습니다.**

### 14-2. 보안 설정

Nginx가 다음 보안 정책을 자동으로 적용합니다.

| 정책 | 설명 |
|------|------|
| data/ 화이트리스트 | `menu.json`, `search-index.json`, `glossary.json`만 외부 접근 허용 |
| 백엔드 비노출 | 백엔드 포트(8000)는 외부에 노출되지 않음 |
| 민감 경로 차단 | `/backend/`, `/models/`, `/tools/`, `/backups/`, `/.env`, `/.git` → 403 |
| 업로드 제한 | 최대 100MB |
| 스트리밍 지원 | AI 채팅/Q&A의 NDJSON 스트리밍을 위해 프록시 버퍼링 비활성화 |

**컨테이너 실행 사용자**

백엔드 컨테이너는 보안을 위해 비특권 사용자 `appuser (UID 1000)`로 실행됩니다 (CIS Docker Benchmark). 빌드 시 `APP_UID`/`APP_GID` 빌드 인자로 호스트 사용자 UID에 맞춰 오버라이드할 수 있습니다.

```bash
docker compose build --build-arg APP_UID=1001 --build-arg APP_GID=1001
```

UID 불일치 시 볼륨 쓰기가 실패하므로 ([§5-2](#5-2-사용자-uid-확인-중요), [§12-7](#12-7-permission-denied--볼륨-파일-쓰기-실패) 참조), 최초 설치 전 반드시 확인합니다.

### 14-3. 알려진 제한

| 항목 | 설명 |
|------|------|
| 번역 중 재시작 | 진행 중 번역은 중단되며 자동 재개되지 않음. 해당 페이지 재요청 필요 |
| Word COM 전처리 | Windows 전용(장절번호 평문화)은 Linux Docker에서 사용 불가 |
| babeldoc 초기 로딩 | 첫 번역 시 ONNX 모델 로딩 지연 가능 (이미지에 사전 포함) |

### 14-4. Docker 설정 파일 목록

| 파일 | 위치 | 설명 |
|------|------|------|
| `Dockerfile` | 프로젝트 루트 | 백엔드 이미지 |
| `docker/Dockerfile.nginx` | `docker/` | 프론트엔드 이미지 |
| `docker/nginx.conf` | `docker/` | Nginx 라우팅/프록시/보안 |
| `docker/config.docker.js` | `docker/` | Docker 전용 프론트엔드 config |
| `docker-compose.yml` | 프로젝트 루트 | 서비스 오케스트레이션 |
| `.env.example` | 프로젝트 루트 | 설정 템플릿 |
| `.dockerignore` | 프로젝트 루트 | 빌드 제외 목록 |
