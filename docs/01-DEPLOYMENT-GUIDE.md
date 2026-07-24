# 배포 가이드 (DEPLOYMENT GUIDE)

Smart Document Platform 을 **운영 환경별로 설치·실행**하는 통합 가이드입니다.
신규 배포자가 **가장 먼저 읽는 문서**이며, 본인 환경에 해당하는 섹션만 순서대로 수행하면 서비스가 올라옵니다.

세부 심화 내용은 각 환경 섹션 끝의 **다음 단계** 링크를 참고하세요.

---

## 목차

- [1. 배포 환경 선택](#1-배포-환경-선택)
- [2. 공통 선결 작업](#2-공통-선결-작업)
- [3. 환경 A — 개발 PC (Windows + WSL2 + Docker Desktop)](#3-환경-a--개발-pc-windows--wsl2--docker-desktop)
- [4. 환경 B — 회사 Linux VM (Docker)](#4-환경-b--회사-linux-vm-docker)
- [5. 환경 C — 회사 Windows PC (톰캣 + Python 직접 실행)](#5-환경-c--회사-windows-pc-톰캣--python-직접-실행)
- [6. 최초 관리자 계정 생성](#6-최초-관리자-계정-생성)
- [7. 검증 체크리스트](#7-검증-체크리스트)
- [8. 다음 단계](#8-다음-단계)

---

## 1. 배포 환경 선택

배포는 **Docker(tar 이미지) 방식으로 표준화**되었습니다. 실운영은 **A·B(Docker) 2종**을 사용하세요. **C(톰캣 + Python 직접 실행)는 deprecated(폐지·보류)** — 과거 대안 방식이며 현재 배포 대상이 아닙니다(§5 참조).

| 구분 | A. 개발 PC (집) | B. 회사 Linux VM | ~~C. 회사 Windows PC~~ (deprecated) |
|------|-----------------|------------------|--------------------|
| **용도** | 개발·테스트 | **주 서비스** | ⛔ 보류 (과거 대안) |
| **실행 방식** | Docker (WSL2) | Docker | 톰캣 + Python 직접 실행 |
| **컨테이너** | Nginx + Backend | Nginx + Backend | — |
| **프론트엔드** | Nginx(80) | Nginx(80) | Tomcat 7.0(8080) |
| **백엔드** | FastAPI(8000, 내부) | FastAPI(8000, 내부) | FastAPI(8000, 외부) |
| **AI 기능 테스트** | ⚠️ WSL→Ollama 접근 제한 (아래 참조) | ✅ 회사 GPU 서버 사용 | ✅ 회사 GPU 서버 사용 |
| **배포 방법** | `docker compose up -d` | `./deploy.sh platform-vX.X.tar` | 파일 복사 + `python main.py` |
| **가이드** | [§3](#3-환경-a--개발-pc-windows--wsl2--docker-desktop) | [§4](#4-환경-b--회사-linux-vm-docker) + [03-DOCKER-OPERATIONS](03-DOCKER-OPERATIONS.md) | [§5](#5-환경-c--회사-windows-pc-톰캣--python-직접-실행) |

### 1-1. 설계 원칙

- **프론트엔드는 정적 파일**이므로 Nginx·톰캣·Python http.server 어디서든 서빙 가능.
- **백엔드는 `python main.py`로 직접 실행 가능**해야 하므로 Docker 전용 기능에 의존하지 않는다 (CLAUDE.md 제약).
- 코드 베이스는 **세 환경 모두에서 동작**해야 하며, 환경별로 관리되는 값은 `.env` 와 `data/settings.json` 두 파일에 집중한다.

### 1-2. WSL2 개발 PC 제한 사항

개발 PC(집)의 Docker Desktop 은 WSL2 위에서 동작하며, WSL 의 네트워크 제약 때문에 **컨테이너에서 Windows 호스트의 Ollama(11434) 에 직접 접근할 수 없는 경우**가 많습니다.

- AI 채팅/요약/Q&A 를 **Docker 환경에서 실제로 시험**해야 할 때는 **직접 실행 방식**(§5 의 Python 직접 실행)을 사용하거나,
- `OLLAMA_URL=http://host.docker.internal:11434` 설정을 시도한 뒤 접속 실패 시 호스트 직접 실행으로 폴백하세요.

문서 탐색·번역 엔진·비교 등 **AI 미의존 기능**은 Docker 만으로도 정상 테스트됩니다.

---

## 2. 공통 선결 작업

### 2-1. 소스 반입

플랫폼 소스(`smart-document-platform/`) 를 배포 대상 서버로 전달합니다. 폐쇄망인 경우 USB/반입 승인 파일을 통해 옮깁니다.

### 2-2. 필수 디렉토리 확인

```
smart-document-platform/
├── backend/                  # FastAPI 백엔드
├── contents/                 # Explorer 웹북 콘텐츠
├── css/ js/ lib/             # 프론트엔드 정적 자원
├── data/                     # [보존] 런타임 데이터 (auth.db, settings.json 등)
├── models/                   # [보존] AI 모델 (~4.4GB)
├── docker/                   # Nginx Dockerfile + 설정
├── tools/                    # 유틸리티 (create-admin.py, 인덱스 빌더, converter)
├── Dockerfile                # Backend 컨테이너
├── docker-compose.yml        # 프로덕션 오케스트레이션
├── docker-compose.override.yml # 개발 환경 bind mount
├── .env.example              # 환경 설정 템플릿
├── deploy.sh                 # 전체 이미지 배포 스크립트
└── patch-apply.sh            # 패치 적용 스크립트
```

### 2-3. `.env` 작성 (환경 A·B 필수)

`.env.example` 을 복사하여 `.env` 를 만들고 환경에 맞게 수정합니다. 환경 C(Windows 직접 실행)는 `.env` 대신 `data/settings.json` 과 환경변수를 사용합니다.

| 항목 | 기본값 | 설명 |
|------|--------|------|
| `PORT` | `80` | 외부 접속 포트 (Nginx) |
| `CORS_ORIGINS` | `http://localhost` | 허용 Origin (쉼표 구분) |
| `OLLAMA_URL` | `http://gpu-server:11434` | Ollama 서버 주소 |
| `EMBEDDING_BACKEND_INDEX` | `ollama` | 인덱싱 경로(대량 배치) — `local` / `ollama` |
| `EMBEDDING_BACKEND_RUNTIME` | `local` | 런타임 경로(검색·유사도) — `local` / `ollama` |
| `EMBEDDING_OLLAMA_BATCH` | `256` | Ollama 청크 분할 크기 |
| `EMBEDDING_BACKEND` *(레거시)* | *(미설정)* | 두 경로를 동일하게 맞추는 단일 토글. 신규 배포는 위 2개 변수 권장 |
| `DATA_DIR` / `CONTENTS_DIR` / `MODELS_DIR` / `BACKUPS_DIR` | `./data` 등 | 볼륨 마운트 경로 |

AI 모델명(`OLLAMA_MODEL`) 등 운영 설정은 **브라우저 관리자 설정 화면**에서 변경합니다. `.env` 에 포함하지 않습니다.

**GPU 없는 백엔드**의 경우 기본값(`_INDEX=ollama`, `_RUNTIME=local`) 그대로 사용하면 인덱싱은 Ollama GPU로 위임되고, 검색·유사도는 컨테이너 내부 로컬 추론으로 저지연을 유지합니다. Ollama 미구동 환경에서는 `_INDEX=local` 로 두 경로 모두 로컬로 전환하세요.

---

## 3. 환경 A — 개발 PC (Windows + WSL2 + Docker Desktop)

집·개인 작업용 Windows PC 에서 빠르게 개발·테스트하는 절차입니다.

### 3-1. 사전 준비

- **Windows 10/11** (WSL2 활성화)
- **Docker Desktop 4.x** 이상 실행 중
- **Python 3.11+** (선택, 인덱스 재생성·admin 계정 생성에 사용)

```powershell
docker --version          # 20.x 이상
docker compose version    # v2.x 이상
```

### 3-2. 최소 실행 (5분)

```powershell
cd C:\AHS_Proj\smart-document-platform
copy .env.example .env
notepad .env
# OLLAMA_URL=http://host.docker.internal:11434  (WSL 제한 있음 — §1-2 참조)
# PORT=80  그대로

docker compose up -d
```

첫 빌드는 **10~30분** 소요됩니다 (Python 패키지 + AI 모델 약 500MB). 이후 실행은 즉시 기동됩니다.

`docker-compose.override.yml` 이 자동 적용되어 소스를 bind mount 하므로:
- **프론트엔드**: 파일 수정 → 브라우저 `Ctrl+F5`
- **백엔드**: 파일 수정 → `docker compose restart backend`

### 3-3. 접속 확인

브라우저에서 `http://localhost` 접속:
- Launcher: `http://localhost/launcher.html`
- Explorer: `http://localhost/`
- Notebook(Translator): `http://localhost/translator.html`
- Verify(Compare): `http://localhost/compare.html`

테스트 계정: `testbot` / `test1234`

### 3-4. AI 기능 테스트 (선택)

WSL→Ollama 접근이 불가능한 경우, 호스트에서 직접 실행하세요:

```powershell
cd backend
python main.py               # FastAPI on :8000
# 새 터미널
python -m http.server 8080   # 정적 프론트 on :8080
```

→ `http://localhost:8080` 으로 접속. Ollama 가 **같은 Windows 호스트에서 기본 포트로 실행 중**이면 `OLLAMA_URL` 기본값(`http://localhost:11434`) 으로 자동 연결됩니다.
Ollama 가 원격 GPU 서버에 있으면 `backend/.env`(또는 쉘 환경변수)의 `OLLAMA_URL` 을 실제 주소로 설정하거나, 관리자 웹 UI 의 **공통 > Ollama URL** 을 변경하세요. `data/settings.json` 이 항상 `config.py` 의 기본값을 덮어씁니다.

### 3-5. 다음 단계

- 컨테이너 내부 동작·`.env` 항목 상세 → [03-DOCKER-OPERATIONS](03-DOCKER-OPERATIONS.md)
- 백엔드 코드 이해·인덱스 생성 → [02-BACKEND-SETUP](02-BACKEND-SETUP.md)

---

## 4. 환경 B — 회사 Linux VM (Docker)

플랫폼 **주 서비스** 환경입니다. 배포 PC 에서 빌드한 tar 이미지를 받아 `deploy.sh` 로 교체하는 방식입니다.

### 4-1. 사전 준비

| 항목 | 요구사항 |
|------|----------|
| OS | Ubuntu 24.04 (또는 Docker 지원 리눅스) |
| Docker Engine | 20.x 이상 |
| Docker Compose | v2.x (plugin 방식) |
| 디스크 여유 | 15GB 이상 |
| 메모리 | 4GB 이상 |

```bash
docker --version
docker compose version
```

### 4-2. 최초 설치

```bash
sudo mkdir -p /opt/smart-document-platform
cd /opt/smart-document-platform
# USB/반입 승인으로 받은 파일 복사:
#   platform-vX.X.tar, docker-compose.yml, .env.example, deploy.sh, patch-apply.sh,
#   data/, contents/, models/

cp .env.example .env
nano .env
# OLLAMA_URL=http://<GPU서버주소>:11434
# CORS_ORIGINS=http://<공식주소>
# PORT=80

./deploy.sh platform-vX.X.tar
```

`deploy.sh` 가 자동으로 이미지 로드 → 컨테이너 기동 → 미사용 이미지 정리를 수행합니다.

### 4-3. UID 매칭 (중요)

컨테이너는 보안상 비특권 사용자(`appuser`, 기본 UID **1000**) 로 실행됩니다. 볼륨 마운트 경로 소유자 UID 가 다르면 쓰기 권한 오류가 발생합니다.

```bash
ls -ln data/ | head -3
# 1000 이면 그대로 진행. 다르면:
sudo chown -R 1000:1000 data/ contents/ backups/ logs/
# 또는 개발 PC에서 --build-arg APP_UID=<UID> 로 재빌드 (03-DOCKER-OPERATIONS §5-2 참조)
```

### 4-4. 버전 업데이트

```bash
cd /opt/smart-document-platform
docker compose down
cp -f platform-vX.X.tar .           # 개발 PC에서 전달받은 파일만 갱신
./deploy.sh platform-vX.X.tar
docker compose ps                    # 두 컨테이너 모두 Up / healthy
```

### 4-5. 코드 패치 (소규모 변경)

Python/JS/HTML/CSS 변경만 있는 경우 전체 이미지 대신 패치 파일을 사용합니다.

```bash
./patch-apply.sh patch-vX.X.X.tar.gz
```

> **중요**: `deploy.sh` / `patch-apply.sh` / `docker-compose.yml` 내 `COMPOSE_FILE` 고정 설정은 Plan-31 4중 방어선입니다. 임의 수정 금지 (`memory/feedback_docker_prod_scripts.md`).

### 4-6. 다음 단계

- Docker 운영·백업·롤백 상세 → [03-DOCKER-OPERATIONS](03-DOCKER-OPERATIONS.md)
- 관리자 웹 설정 화면 사용법 → [04-USER-GUIDE](04-USER-GUIDE.md)

---

## 5. 환경 C — 회사 Windows PC (톰캣 + Python 직접 실행) — ⛔ **DEPRECATED**

> **이 방식은 폐지·보류 상태입니다.** 배포는 Docker(tar 이미지, §4)로 표준화되었으며, 환경 C는 현재 배포 대상이 아닙니다.
> 아래 절차는 **이력 보존용**입니다. 되살릴 경우 **선결 조건**: `/data/` 정적 노출 하드닝(`data/auth.db`·`data/authored/*` 무인증 노출 차단 — icebox 항목). 하드닝 없이 이 방식으로 서비스하지 마세요.

Docker 가 없는 회사 Windows PC 에서 운영하던 **과거 대안 방식**입니다. 프로젝트 디렉토리를 통째로 복사한 뒤 두 개의 프로세스(Tomcat + Python)를 직접 구동합니다.

### 5-1. 사전 준비

| 항목 | 버전 |
|------|------|
| JDK | 1.8.0_51 (Tomcat 구동용) |
| Apache Tomcat | 7.0.77 |
| Python | 3.11.9 (가상환경 권장) |
| MS Word | 선택 — DRM 문서 전처리가 필요한 경우 |

폐쇄망 반입 시 `.zip` 으로 위 파일을 함께 준비합니다.

### 5-2. 프론트엔드 (Tomcat)

1. `jdk-8u51-windows-x64.zip` → `C:\Java\jdk1.8.0_51` 해제, `JAVA_HOME` 환경변수 설정
2. `apache-tomcat-7.0.77-windows-x64.zip` → `C:\Tomcat\apache-tomcat-7.0.77` 해제
3. `smart-document-platform.zip` 의 **정적 자원 전체**(`index.html`, `css/`, `js/`, `contents/`, `data/`, `launcher.html`, `translator.html`, `compare.html`, `admin.html`, `login.html`) 를 `webapps/ROOT/` 로 복사
4. `bin\startup.bat` 실행 → `http://localhost:8080` 접속 확인

### 5-3. 백엔드 (Python 직접 실행)

```cmd
cd C:\path\to\smart-document-platform\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

python main.py
```

또는

```cmd
uvicorn main:app --host 0.0.0.0 --port 8000
```

백엔드가 `http://localhost:8000` 에서 기동되며, `config.py` 의 `CORS_ORIGINS` 에 `http://localhost:8080` 을 포함하여 Tomcat ↔ FastAPI 크로스 오리진 통신을 허용합니다.

### 5-4. Ollama (선택)

동일 Windows PC 또는 회사 GPU 서버에 Ollama 설치. `backend/config.py` 또는 `data/settings.json` 의 `OLLAMA_URL` 을 실제 주소로 변경.

### 5-5. PDF 내보내기 엔진 (선택)

Compare 유사도 리포트의 **PDF 내보내기**는 WeasyPrint 기반이며 Windows 에서는 GTK+ Runtime 이 추가로 필요합니다. 설치하지 않아도 PDF 요청 시 자동으로 HTML 포맷으로 폴백되므로 서비스 기능은 유지됩니다. PDF 다운로드를 사용하려면 [02-BACKEND-SETUP.md §WeasyPrint — Windows 네이티브 환경 설정](02-BACKEND-SETUP.md#weasyprint--windows-네이티브-환경-설정) 의 절차를 따릅니다.

### 5-6. 방화벽·다른 PC 접속

```cmd
netsh advfirewall firewall add rule name="Tomcat 8080" dir=in action=allow protocol=TCP localport=8080
netsh advfirewall firewall add rule name="FastAPI 8000" dir=in action=allow protocol=TCP localport=8000
```

같은 네트워크의 다른 PC 에서 `http://<서버IP>:8080` 접속.

### 5-7. 변환기 DRM 전처리

회사 Windows 환경에서는 Word COM 이 전처리 어댑터로 자동 선택되며, DRM 재잠금을 피하기 위해 `.docx_1` 확장자를 사용합니다. 자세한 메커니즘은 [13-CONVERTER-ARCHITECTURE §7](13-CONVERTER-ARCHITECTURE.md#7-drm-우회-규약-docx_1) 참조.

### 5-8. 다음 단계

- 백엔드 가상환경·의존성·오프라인 패키지 → [02-BACKEND-SETUP](02-BACKEND-SETUP.md)
- 운영자 기능(관리자 설정, 업로드, 인덱싱) → [04-USER-GUIDE](04-USER-GUIDE.md)

---

## 6. 최초 관리자 계정 생성

모든 환경 공통 — 서비스 기동 후 최초 1회 수행합니다.

```bash
# Docker 환경
docker compose exec backend python tools/create-admin.py

# 직접 실행 환경
cd backend && python ../tools/create-admin.py
```

기본 테스트 계정 `testbot` / `test1234` 가 `data/auth.db` 에 자동 생성되지만, **실제 운영 시 이 계정을 삭제하고 신규 admin 을 생성**해야 합니다.

---

## 7. 검증 체크리스트

배포 직후 아래 순서로 확인합니다. HTTP 200 만으로는 부족합니다 (`memory/feedback_docker_verification.md` 참조).

### 7-1. 컨테이너 상태 (환경 A·B)

```bash
docker compose ps
# nginx, backend 모두 "Up" + "healthy"

docker compose logs backend --tail=50
# uvicorn startup 로그, ERROR 없음
```

### 7-2. HTTP 응답 + 정적 리소스 최신 여부

```bash
curl -sI http://localhost/ | grep -i last-modified
# 기대: 최신 빌드 시점 (오래된 값이면 캐시 미반영)

curl -s http://localhost/api/health
# {"status":"ok"}
```

### 7-3. 컨테이너 내부 교차 검증

```bash
docker compose exec nginx curl -sI http://backend:8000/api/health
# 내부 네트워크에서도 응답 정상인지 확인
```

### 7-4. 브라우저 검증

- `testbot` / `test1234` 로그인 → 세션 유지
- **Explorer**: 메뉴 트리 표시 → 검색 → AI 채팅(Ollama 연결 시)
- **Notebook**: PDF 업로드 → 페이지 번역 → 웹뷰 모드 확인
- **Verify**: 두 문서 업로드 → diff + 유사도 검사 + 규칙 검증
- **관리자 설정**: 값 변경 → 저장 → 재접속 후 유지

### 7-5. 보안 점검

브라우저 주소창에 직접 입력:

| URL | 기대 결과 |
|-----|-----------|
| `http://<서버>/backend/config.py` | 403 또는 404 |
| `http://<서버>/data/auth.db` | 403 |
| `http://<서버>/.env` | 403 |

노출 시 `docker/nginx.conf` 의 deny 규칙을 재확인하세요.

---

## 8. 다음 단계

| 주제 | 문서 |
|------|------|
| Python 백엔드 심화 · 오프라인 패키지 · 인덱스 빌드 | [02-BACKEND-SETUP](02-BACKEND-SETUP.md) |
| Docker 이미지 빌드 · 패치 · 백업 · 롤백 | [03-DOCKER-OPERATIONS](03-DOCKER-OPERATIONS.md) |
| 사용자/관리자 기능 · 메뉴·콘텐츠 관리 | [04-USER-GUIDE](04-USER-GUIDE.md) |
| 시스템 구성·API·폴더 구조 | [05-ARCHITECTURE](05-ARCHITECTURE.md) |
| Converter(DOCX→HTML) 아키텍처 | [13-CONVERTER-ARCHITECTURE](13-CONVERTER-ARCHITECTURE.md) |
| 운영 준비도·장비 사양 (아카이브, Plan-11 평가서) | [workbench/reports/plan-11-production-readiness.md](../workbench/reports/plan-11-production-readiness.md) |
