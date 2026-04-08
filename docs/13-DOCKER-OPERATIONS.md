# Docker 배포 운영 가이드

Smart Document Platform을 Docker로 배포하고 운영하는 절차를 안내합니다.
Docker 경험이 없어도 이 문서의 절차를 따라 설치, 업데이트, 백업, 문제 해결을 수행할 수 있습니다.

---

## 1. 시스템 구조

### 1-1. 배포 아키텍처

플랫폼은 2개의 Docker 컨테이너로 구성됩니다.
외부에는 Nginx 포트 1개만 노출되며, 백엔드는 내부 통신만 사용합니다.

```
리눅스 서버
│
├── Nginx 컨테이너 (포트 80, 유일하게 외부 노출)
│   ├── HTML/JS/CSS 서빙 (프론트엔드)
│   ├── /api/* → 백엔드로 전달 (리버스 프록시)
│   └── 보안 차단 (민감 파일 접근 403)
│
├── Backend 컨테이너 (내부 포트 8000, 외부 비노출)
│   ├── FastAPI 서버
│   ├── 검색, 번역, 검증 등 모든 API
│   └── pdf2zh (번역 엔진)
│
└── 볼륨 마운트 (호스트 폴더 → 컨테이너)
    ├── data/      → 사용자 데이터 (읽기/쓰기)
    ├── contents/  → 웹북 콘텐츠 (읽기/쓰기)
    ├── models/    → AI 모델 (읽기 전용)
    ├── backups/   → 편집 백업 (읽기/쓰기)
    └── logs/      → 서버 로그 (읽기/쓰기)
```

> Ollama(AI 모델 서버)는 별도 GPU 서버에서 운영합니다. Docker에 포함하지 않습니다.

### 1-2. 핵심 개념

Docker 운영에서 알아야 할 3가지 개념입니다.

| 용어 | 비유 | 설명 |
|------|------|------|
| **이미지** | 설치 CD | 플랫폼 코드가 담긴 읽기 전용 파일. 업데이트 시 새 이미지로 교체 |
| **컨테이너** | 실행 중인 프로그램 | 이미지를 기반으로 실행된 상태. 중지/시작 자유로움 |
| **볼륨** | 외부 저장장치 | 사용자 데이터가 저장되는 폴더. 이미지 교체해도 유지됨 |

> **핵심 원칙**: 이미지(코드)를 새 버전으로 교체해도 볼륨(데이터)은 그대로 남습니다.
> 업데이트 시 사용자 계정, 문서, 설정이 유실되지 않습니다.

---

## 2. 디렉토리 구조

리눅스 서버의 배포 디렉토리입니다.
`[보존]` 표시된 폴더는 사용자 데이터이므로 삭제하면 안 됩니다.

```
/opt/smart-document-platform/       ← 배포 루트
├── docker-compose.yml              ← 서비스 구성 파일
├── .env                            ← 환경 설정 (포트, Ollama 주소 등)
│
├── data/                           ← [보존] 사용자 데이터
│   ├── auth.db                     ←   계정 정보
│   ├── analytics.db                ←   사용 통계
│   ├── settings.json               ←   관리자 설정
│   ├── translator/                 ←   번역 작업물
│   ├── verify/                     ←   검증 데이터
│   └── ...
├── contents/                       ← [보존] 웹북 콘텐츠
├── models/                         ← [보존] AI 모델 (약 4.4GB)
├── backups/                        ← [보존] 문서 편집 백업
└── logs/                           ← 서버 로그
```

---

## 3. 환경 요구사항

### 3-1. 개발 PC (Windows)

이미지를 빌드하고 내보내는 환경입니다.

| 항목 | 버전 | 비고 |
|------|------|------|
| OS | Windows 10/11 | WSL2 활성화 필요 |
| Docker Desktop | 4.x 이상 | WSL2 백엔드 |
| Docker Compose | v2.x 이상 | Docker Desktop에 포함 |

### 3-2. 리눅스 서버 (폐쇄망)

서비스가 실제로 운영되는 서버입니다.

| 항목 | 요구사항 | 비고 |
|------|----------|------|
| Docker Engine | 20.x 이상 | 설치 완료 상태 |
| Docker Compose | v2.x 이상 | plugin 방식 |
| 디스크 여유 | 15GB 이상 | 이미지 3GB + 모델 4.4GB + 데이터 |
| 메모리 | 4GB 이상 | 임베딩 모델 + 리랭커 상주 |

### 3-3. 외부 연계

| 항목 | 설명 |
|------|------|
| Ollama 서버 | GPU 서버에서 별도 운영. URL을 `.env`에 설정 |
| Ollama 모델 | GPU 서버에 사전 설치 필요 (예: `gemma3:4b`) |

> Ollama 서버가 연결되지 않아도 기본 기능(문서 탐색, 검색, 번역, 비교)은 정상 동작합니다.
> AI 채팅, 요약, Q&A 기능만 비활성화됩니다.

---

## 4. 설정 파일 (.env)

`.env` 파일 하나로 모든 환경 설정을 관리합니다.
`.env.example` 파일을 복사하여 환경에 맞게 수정합니다.

| 항목 | 기본값 | 설명 |
|------|--------|------|
| `PORT` | `80` | 외부 접속 포트 (브라우저에서 접속할 포트) |
| `OLLAMA_URL` | `http://gpu-server:11434` | Ollama GPU 서버 주소 |
| `OLLAMA_MODEL` | `gemma3:4b` | 사용할 AI 모델 이름 |
| `DATA_DIR` | `./data` | 사용자 데이터 경로 (변경 불필요) |
| `CONTENTS_DIR` | `./contents` | 웹북 콘텐츠 경로 (변경 불필요) |
| `MODELS_DIR` | `./models` | AI 모델 경로 (변경 불필요) |
| `BACKUPS_DIR` | `./backups` | 백업 경로 (변경 불필요) |

> `.env` 변경 후에는 반드시 서비스를 재시작해야 적용됩니다. (→ [8. 설정 변경](#8-설정-변경))

---

## 5. 개발 PC에서 빌드하기

개발 PC(Windows)에서 Docker 이미지를 빌드하고, 로컬에서 테스트한 뒤,
이미지를 파일로 내보내어 리눅스 서버로 반출하는 절차입니다.

### 5-1. 사전 확인

PowerShell 또는 명령 프롬프트를 엽니다.

| 순서 | 명령어 | 확인 사항 |
|------|--------|-----------|
| 1 | `docker --version` | 버전 번호가 출력되면 정상 |
| 2 | `docker compose version` | v2.x 이상이면 정상 |

버전이 출력되지 않으면 Docker Desktop이 실행 중인지 확인합니다.
작업 표시줄의 Docker 아이콘이 "Docker Desktop is running" 상태여야 합니다.

### 5-2. .env 파일 생성

| 순서 | 명령어 | 설명 |
|------|--------|------|
| 1 | `cd C:\AHS_Proj\smart-document-platform` | 프로젝트 폴더로 이동 |
| 2 | `copy .env.example .env` | 템플릿 복사 |
| 3 | `notepad .env` | 편집기에서 열기 |

수정할 항목:
- **OLLAMA_URL** — 로컬 Ollama: `http://host.docker.internal:11434` / GPU 서버: `http://192.168.x.x:11434`
- **PORT** — 80 포트가 사용 중이면 다른 포트로 변경 (예: `8080`)

> `host.docker.internal`은 Docker 컨테이너 안에서 호스트 PC를 가리키는 특수 주소입니다.

### 5-3. 이미지 빌드

| 순서 | 명령어 | 설명 |
|------|--------|------|
| 1 | `cd C:\AHS_Proj\smart-document-platform` | 프로젝트 폴더로 이동 |
| 2 | `docker compose build` | 이미지 2개 빌드 |

- 첫 빌드는 10~30분 소요 (Python 패키지 + AI 모델 약 500MB 다운로드)
- 두 번째 이후는 변경분만 처리하므로 빠릅니다
- 완료 시 `sdp-backend`, `sdp-nginx` 이미지 2개 생성

### 5-4. 로컬 테스트

| 순서 | 명령어 / 동작 | 확인 사항 |
|------|--------------|-----------|
| 1 | `docker compose up -d` | 백그라운드로 컨테이너 시작 |
| 2 | `docker compose ps` | 둘 다 "Up" 또는 "running"이면 정상 |
| 3 | 브라우저에서 `http://localhost` 접속 | 런처 화면이 나타나면 성공 |

백엔드는 모델 로딩에 최대 2분 소요됩니다.
`docker compose ps`에서 backend가 "starting" 상태라면 잠시 기다립니다.
이상이 있으면 `docker compose logs`로 로그를 확인합니다.

### 5-5. 기능 검증

`http://localhost`에 접속하여 아래 항목을 순서대로 확인합니다.

| 순서 | 항목 | 확인 방법 |
|------|------|-----------|
| 1 | 인증 | testbot / test1234 로그인 → 세션 유지 → 로그아웃 |
| 2 | Launcher | 메뉴 목록 노출, 가이드 페이지 열기 |
| 3 | Explorer | 웹북 열기 → 검색 → AI 채팅 (Ollama 연결 시) |
| 4 | Notebook | PDF 업로드 → 페이지 번역 → 웹뷰 |
| 5 | Verify | 문서 업로드 → 비교 → 규칙 검증 |
| 6 | 관리자 설정 | 설정 변경 → 저장 → 재접속 후 유지 확인 |

### 5-6. 보안 검증

브라우저 주소창에 직접 입력하여 확인합니다.

| URL | 기대 결과 |
|-----|-----------|
| `http://localhost/data/menu.json` | 정상 응답 (JSON) |
| `http://localhost/data/search-index.json` | 정상 응답 (JSON) |
| `http://localhost/data/glossary.json` | 정상 응답 (JSON) |
| `http://localhost/data/auth.db` | **403 Forbidden** |
| `http://localhost/data/settings.json` | **403 Forbidden** |
| `http://localhost/backend/` | **403 Forbidden** |
| `http://localhost/.env` | **403 Forbidden** |

### 5-7. 데이터 영속성 확인

| 순서 | 명령어 / 동작 | 설명 |
|------|--------------|------|
| 1 | `docker compose down` | 서비스 종료 |
| 2 | `docker compose up -d` | 서비스 재시작 |
| 3 | 브라우저에서 재접속 | 이전 계정과 업로드 문서가 유지되면 성공 |

### 5-8. 테스트 종료

```
docker compose down
```

---

## 6. 이미지 내보내기

빌드한 이미지를 파일로 저장하여 리눅스 서버로 반출합니다.

| 순서 | 명령어 | 설명 |
|------|--------|------|
| 1 | `docker save -o platform-v1.0.tar smart-document-platform-backend smart-document-platform-nginx` | 이미지를 tar 파일로 저장 |
| 2 | `dir platform-v1.0.tar` | 파일 크기 확인 (약 2.5~3GB) |

### 반출 준비물

USB 또는 네트워크로 리눅스 서버에 가져갈 파일 목록입니다.

| 파일/폴더 | 크기 | 시점 | 용도 |
|-----------|------|------|------|
| `platform-v1.0.tar` | 약 3GB | 매 버전 | Docker 이미지 |
| `docker-compose.yml` | <1KB | 변경 시 | 서비스 구성 |
| `.env.example` | <1KB | 최초 1회 | 설정 템플릿 |
| `data/` | 가변 | 최초 1회 | 초기 데이터 (계정 등) |
| `contents/` | 가변 | 최초 + 추가 시 | 웹북 콘텐츠 |
| `models/` | 약 4.4GB | 최초 1회 | AI 모델 (거의 변경 없음) |
| `backups/` | 가변 | 최초 1회 | 빈 폴더 (백업 저장소) |

> **버전 업데이트 시**: `platform-vX.X.tar`와 `docker-compose.yml`(변경 시)만 가져가면 됩니다.
> data, contents, models 등 볼륨 데이터는 서버에 이미 있으므로 다시 가져갈 필요 없습니다.

---

## 7. 리눅스 서버 최초 설치

리눅스 서버의 터미널에서 실행합니다. 최초 1회만 수행합니다.

### 7-1. Docker 확인

| 순서 | 명령어 | 확인 사항 |
|------|--------|-----------|
| 1 | `docker --version` | 20.x 이상이면 정상 |
| 2 | `docker compose version` | v2.x 이상이면 정상 |

### 7-2. 디렉토리 구성

| 순서 | 명령어 | 설명 |
|------|--------|------|
| 1 | `sudo mkdir -p /opt/smart-document-platform` | 배포 디렉토리 생성 |
| 2 | `cd /opt/smart-document-platform` | 해당 디렉토리로 이동 |

### 7-3. 파일 배치

USB 또는 네트워크에서 복사한 파일을 배포 디렉토리에 배치합니다.

| 순서 | 동작 | 설명 |
|------|------|------|
| 1 | 반출 파일을 `/opt/smart-document-platform/`에 복사 | tar, yml, data, contents, models, backups 전체 |
| 2 | `ls -la` | 파일 목록 확인 |

### 7-4. 설정

| 순서 | 명령어 | 설명 |
|------|--------|------|
| 1 | `cp .env.example .env` | 설정 템플릿 복사 |
| 2 | `nano .env` | 편집기에서 열기 (vi 등 다른 편집기도 가능) |
| 3 | `OLLAMA_URL`을 실제 GPU 서버 주소로 변경 | 예: `http://192.168.1.100:11434` |
| 4 | `PORT`를 실제 서비스 포트로 변경 (필요시) | 기본값 80. 방화벽에 등록된 포트 사용 |
| 5 | 저장 후 편집기 종료 | nano: Ctrl+O → Enter → Ctrl+X |

### 7-5. 이미지 로드 및 실행

| 순서 | 명령어 | 설명 |
|------|--------|------|
| 1 | `docker load < platform-v1.0.tar` | 이미지 등록 (수 분 소요) |
| 2 | `docker compose up -d` | 서비스 시작 |
| 3 | `docker compose ps` | 둘 다 "Up" / "running" 이면 성공 |

### 7-6. 접속 확인

| 순서 | 동작 | 확인 사항 |
|------|------|-----------|
| 1 | 브라우저에서 `http://서버주소:PORT` 접속 | 런처 화면이 나타나면 성공 |
| 2 | testbot / test1234로 로그인 | 정상 로그인되면 성공 |
| 3 | 각 서브시스템 기본 기능 확인 | Explorer, Notebook, Verify 진입 확인 |

---

## 8. 설정 변경

### 8-1. 인프라 설정 (.env 파일)

포트, Ollama 주소 등 인프라 수준의 설정입니다. 변경 후 재시작이 필요합니다.

| 순서 | 명령어 | 설명 |
|------|--------|------|
| 1 | `nano .env` | 설정 편집 |
| 2 | 원하는 값 수정 후 저장 | nano: Ctrl+O → Enter → Ctrl+X |
| 3 | `docker compose down && docker compose up -d` | 재시작하여 적용 |

### 8-2. 기능 설정 (웹 관리자 화면)

AI 모델, 검색 옵션, 번역 옵션 등은 브라우저에서 관리합니다.

| 순서 | 동작 |
|------|------|
| 1 | 브라우저에서 플랫폼 접속 |
| 2 | admin 계정으로 로그인 |
| 3 | 헤더의 설정(톱니바퀴) 메뉴 클릭 |
| 4 | 설정 변경 후 저장 |

대부분의 기능 설정은 즉시 반영됩니다.

---

## 9. 서비스 관리

리눅스 서버의 배포 디렉토리(`/opt/smart-document-platform`)에서 실행합니다.

### 9-1. 시작 / 종료 / 재시작

| 동작 | 명령어 |
|------|--------|
| 서비스 시작 | `docker compose up -d` |
| 서비스 종료 | `docker compose down` |
| 서비스 재시작 | `docker compose restart` |
| 백엔드만 재시작 | `docker compose restart backend` |

### 9-2. 상태 확인

| 동작 | 명령어 |
|------|--------|
| 컨테이너 상태 | `docker compose ps` |
| 전체 로그 (실시간) | `docker compose logs -f` (Ctrl+C로 종료) |
| 백엔드 로그만 | `docker compose logs -f backend` |
| Nginx 로그만 | `docker compose logs -f nginx` |
| 최근 100줄만 | `docker compose logs --tail 100` |

### 9-3. 컨테이너 내부 접속 (디버깅용)

| 동작 | 명령어 |
|------|--------|
| 백엔드 쉘 접속 | `docker compose exec backend bash` |
| pdf2zh 설치 확인 | `docker compose exec backend pdf2zh --version` |
| Ollama 연결 확인 | `docker compose exec backend curl -s http://GPU서버:11434/api/tags` |

---

## 10. 버전 업데이트

### 10-1. 개발 PC에서 할 일

코드를 수정한 후 새 이미지를 빌드하고 내보냅니다.

| 순서 | 명령어 | 설명 |
|------|--------|------|
| 1 | `cd C:\AHS_Proj\smart-document-platform` | 프로젝트 폴더로 이동 |
| 2 | `docker compose build` | 새 이미지 빌드 (변경분만 처리) |
| 3 | `docker save -o platform-v1.1.tar smart-document-platform-backend smart-document-platform-nginx` | 이미지 내보내기 |
| 4 | tar 파일을 USB/네트워크로 리눅스 서버에 전달 | docker-compose.yml 변경 시 함께 전달 |

### 10-2. 리눅스 서버에서 할 일

| 순서 | 명령어 | 설명 |
|------|--------|------|
| 1 | `cd /opt/smart-document-platform` | 배포 디렉토리로 이동 |
| 2 | `docker compose down` | 서비스 종료 |
| 3 | `docker load < platform-v1.1.tar` | 새 이미지 로드 |
| 4 | docker-compose.yml 변경 시 새 파일로 교체 | `cp new-docker-compose.yml docker-compose.yml` |
| 5 | `docker compose up -d` | 서비스 시작 |
| 6 | `docker compose ps` | 둘 다 "Up"이면 성공 |
| 7 | 브라우저에서 접속하여 정상 동작 확인 | 기존 데이터가 그대로 유지되어야 함 |

> **업데이트 시점**: 서비스 종료 시 진행 중이던 번역 작업은 중단되며 자동 재개되지 않습니다.
> 가능하면 번역 작업이 없는 시간대에 업데이트를 수행합니다.

---

## 11. 백업 / 복원

### 11-1. 백업

서비스를 잠시 중지하고 데이터를 압축 파일로 저장합니다.

| 순서 | 명령어 | 설명 |
|------|--------|------|
| 1 | `cd /opt/smart-document-platform` | 배포 디렉토리로 이동 |
| 2 | `docker compose down` | 서비스 중지 (DB 안전을 위해) |
| 3 | `tar czf backup-$(date +%Y%m%d).tar.gz data/ backups/` | 백업 파일 생성 (날짜 자동 포함) |
| 4 | `docker compose up -d` | 서비스 재시작 |
| 5 | `ls -lh backup-*.tar.gz` | 백업 파일 확인 |

### 11-2. 복원

백업 파일에서 데이터를 복원합니다. 기존 데이터는 안전하게 보관합니다.

| 순서 | 명령어 | 설명 |
|------|--------|------|
| 1 | `docker compose down` | 서비스 중지 |
| 2 | `mv data/ data-old/ && mv backups/ backups-old/` | 기존 데이터를 이름 변경하여 보관 |
| 3 | `tar xzf backup-20260408.tar.gz` | 백업에서 복원 (파일명은 실제 날짜로 변경) |
| 4 | `docker compose up -d` | 서비스 시작 |
| 5 | 브라우저에서 정상 동작 확인 | 확인 후 `data-old/`, `backups-old/` 삭제 가능 |

---

## 12. 웹북 콘텐츠 추가

### 방법 1: 웹 관리자에서 업로드

브라우저에서 admin 계정으로 로그인한 후, Explorer 좌측 트리 메뉴의 업로드 기능을 사용합니다.
업로드 후 검색 인덱스가 자동으로 갱신됩니다.

### 방법 2: 서버에서 직접 복사

| 순서 | 명령어 | 설명 |
|------|--------|------|
| 1 | `cp -r new-webbook/ contents/` | 콘텐츠 파일 복사 |
| 2 | `docker compose restart backend` | 백엔드 재시작 (인덱스 반영) |

또는 웹 관리자 메뉴에서 "검색 인덱스 재생성"을 실행해도 됩니다.

---

## 13. 정기 점검

| 주기 | 항목 | 확인 방법 | 기준 |
|------|------|-----------|------|
| 매일 | 서비스 정상 동작 | `docker compose ps` | 모두 "Up" 상태 |
| 매주 | 디스크 여유 공간 | `df -h` | 사용률 80% 이하 |
| 매주 | 로그 크기 | `du -sh logs/` | 비정상적 증가 여부 |
| 매월 | 데이터 백업 | [11-1. 백업](#11-1-백업) 절차 수행 | 백업 파일 생성 확인 |
| 필요 시 | 미사용 이미지 정리 | `docker image prune` | 디스크 확보 |

---

## 14. 문제 해결

### 14-1. 서비스가 시작되지 않을 때

| 순서 | 명령어 | 설명 |
|------|--------|------|
| 1 | `docker compose ps` | "Exited" 상태인 컨테이너 확인 |
| 2 | `docker compose logs backend` | 백엔드 에러 메시지 확인 |
| 3 | `docker compose logs nginx` | Nginx 에러 메시지 확인 |

자주 발생하는 원인:

| 증상 | 원인 및 해결 |
|------|-------------|
| backend "Exited" | `.env` 파일이 없거나, `models/` 폴더가 없는 경우. 파일 배치 확인 |
| nginx "Exited" | 포트 충돌. `.env`의 `PORT` 값이 이미 사용 중인지 확인 |
| nginx가 backend 대기 중 | backend 헬스체크 통과 전까지 정상. 최대 2분 대기 |

### 14-2. 페이지가 열리지 않을 때

| 순서 | 확인 사항 | 조치 |
|------|-----------|------|
| 1 | `docker compose ps`로 서비스 상태 확인 | 중지 상태면 `docker compose up -d` |
| 2 | 브라우저 주소의 포트 번호 확인 | `.env`의 `PORT` 값과 일치해야 함 |
| 3 | `docker compose logs nginx` | Nginx 에러 로그 확인 |

### 14-3. AI 기능이 동작하지 않을 때

| 순서 | 확인 방법 | 설명 |
|------|-----------|------|
| 1 | `docker compose exec backend curl -s http://GPU서버:11434/api/tags` | 모델 목록이 표시되면 연결 정상 |
| 2 | 응답이 없는 경우 | `.env`의 `OLLAMA_URL` 확인, GPU 서버 상태 확인 |

> AI 기능(채팅, 요약, Q&A)이 동작하지 않아도
> 문서 탐색, 검색, 번역, 비교 등 기본 기능은 정상 동작합니다.

### 14-4. 디스크 부족

| 순서 | 명령어 | 설명 |
|------|--------|------|
| 1 | `df -h` | 시스템 디스크 사용량 확인 |
| 2 | `docker system df` | Docker가 사용하는 디스크 확인 |
| 3 | `docker image prune -a` | 미사용 이미지 정리 (실행 중 이미지는 유지) |
| 4 | `du -sh logs/` | 로그 크기 확인, 필요시 오래된 로그 삭제 |

---

## 15. 주의 사항

아래 명령어는 데이터를 복구할 수 없게 삭제합니다. **절대 실행하지 않습니다.**

| 명령어 | 결과 |
|--------|------|
| `docker compose down -v` | 볼륨(데이터) 전부 삭제. 계정, 작업물 복구 불가 |
| `rm -rf data/` | 사용자 데이터 전부 삭제 |
| `docker system prune -a --volumes` | 모든 Docker 데이터 삭제 |
| `.env` 파일 삭제 | 설정 유실. 서비스 시작 시 기본값으로 동작 |

> `docker compose down`은 컨테이너만 제거하며 데이터(볼륨)는 유지합니다.
> **`-v` 옵션을 절대 붙이지 않습니다.**

---

## 16. 기술 참고

### 16-1. 보안 설정

Nginx가 다음 보안 정책을 자동으로 적용합니다.

| 정책 | 설명 |
|------|------|
| data/ 화이트리스트 | menu.json, search-index.json, glossary.json 3개만 외부 접근 허용. 나머지 403 |
| 백엔드 비노출 | 백엔드 포트(8000)는 외부에 노출되지 않음. Nginx가 /api/ 경로만 프록시 |
| 민감 경로 차단 | /backend/, /models/, /tools/, /backups/, /.env, /.git 접근 시 403 |
| 업로드 제한 | 파일 업로드 최대 100MB |
| 스트리밍 지원 | AI 채팅, Q&A 응답의 실시간 스트리밍(NDJSON)을 위해 프록시 버퍼링 비활성화 |

### 16-2. 알려진 제한

| 항목 | 설명 |
|------|------|
| 번역 중 재시작 | 진행 중인 번역은 중단되며 자동 재개되지 않음. 해당 페이지를 다시 번역 요청해야 함 |
| Word COM 전처리 | Windows 전용 기능(장절번호 평문화)은 Linux Docker에서 사용 불가. 기본 비활성화 상태 |
| babeldoc 초기 로딩 | 첫 번역 시 ONNX 모델 로딩에 시간이 소요될 수 있음 (이미지에 사전 포함) |

### 16-3. Docker 설정 파일 목록

| 파일 | 위치 | 설명 |
|------|------|------|
| `Dockerfile` | 프로젝트 루트 | 백엔드 이미지 (Python + tools/ + pdf2zh) |
| `docker/Dockerfile.nginx` | docker/ | 프론트엔드 이미지 (Nginx + HTML/JS/CSS) |
| `docker/nginx.conf` | docker/ | Nginx 라우팅, 프록시, 보안 설정 |
| `docker/config.docker.js` | docker/ | Docker 전용 프론트엔드 config (backendUrl 상대경로) |
| `docker-compose.yml` | 프로젝트 루트 | 서비스 오케스트레이션 |
| `.env.example` | 프로젝트 루트 | 설정 템플릿 |
| `.dockerignore` | 프로젝트 루트 | 빌드 제외 목록 |
