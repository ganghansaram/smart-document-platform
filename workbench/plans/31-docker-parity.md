# Plan-31: Docker Parity — 로컬 개발 ↔ 도커 이미지 일관성 확보

> **목표**: 로컬(Windows) 개발 환경에서 구현·검증한 내용이 Docker 이미지에도 자동으로 동일하게 반영되도록 한다.
> **배경**: Plan-27로 도커 전환은 완료됐으나, 로컬↔도커 사이에 수동 동기화 지점(특히 `config.docker.js`)이 남아 있어 divergence가 실제로 발생하고 있다.
> **제약**: 폐쇄망, Vanilla JS, 빌드 시스템 없음, 단일 개발자

## 진행 상태

| Phase | 상태 | 요약 |
|---|---|---|
| **Phase 1** bind mount | ✅ **완료** (2026-04-11) | override·dev nginx·스크립트 방어선까지 구축. 실측으로 환경 오염까지 제거. |
| Phase 2 COPY 블랙리스트 | 대기 | 필요성 느낄 때 진행 |
| Phase 3 config 단일화 | 대기 | divergence 근본 해결 단계 |
| Phase 4 parity 체크 스크립트 | 대기 | Phase 2·3 완료 후 |

---

## 0. 현황과 문제

### 측정된 divergence

- `js/config.js` = **118줄**
- `docker/config.docker.js` = **71줄**
- **47줄 차이** — 로컬에 추가된 설정(프롬프트, 옵션 등)이 도커에 반영 안 됨

### 현재 구조의 문제점

| 문제 | 위치 | 증상 |
|---|---|---|
| 설정 이중화 | `js/config.js` ↔ `docker/config.docker.js` | 한쪽만 수정하면 도커에서만 기능 누락/버그 |
| 화이트리스트 COPY | `docker/Dockerfile.nginx:11-21` | 새 폴더/파일 추가 시 Dockerfile 수정 누락 |
| 재빌드 강제 | 모든 프론트 수정 | 로컬에서 고친 걸 도커에서 보려면 매번 `docker compose build` |
| 검증 부재 | — | divergence를 사람이 수동 점검해야 함 |

### 영향 시나리오 예시

1. `js/config.js`에 `MAX_UPLOAD_SIZE = 1GB` 추가 → 로컬 테스트 통과 → 도커 배포 후 500MB 제한 유지 → "왜 안 되지?" 디버깅 낭비
2. `assets/icons/` 폴더 추가 → 로컬 정상 → 도커 빌드 후 아이콘 404
3. `requirements.txt` 갱신 없이 `pip install` → 로컬 정상 → 도커 빌드 후 ImportError

---

## 1. 목표

- **로컬에서 수정 → 도커에서 즉시 확인** (재빌드 최소화)
- **config 단일 소스** — `config.js`만 관리하면 도커도 자동 반영
- **Dockerfile COPY 자동화** — 프론트 폴더 추가 시 Dockerfile 건드리지 않음
- **divergence 사전 감지** — 커밋 전 자동 검증

---

## 2. 4단계 접근

효과·리스크·노력을 기준으로 단계를 분리. 각 단계는 독립적이며 앞 단계가 뒤 단계의 전제는 아니다.

### Phase 1 — `docker-compose.override.yml` bind mount (최우선)

**효과**: 로컬 수정이 컨테이너에 즉시 반영 → 재빌드 불필요
**노력**: 30분
**리스크**: 낮음 (개발 전용 파일, 프로덕션 배포는 영향 없음)

#### 작업

1. `docker-compose.override.yml` 신규 작성 (루트)
   ```yaml
   # 개발 전용 — docker compose가 자동으로 docker-compose.yml에 병합
   # 프로덕션 배포 시엔 `docker compose -f docker-compose.yml up`으로 override 무시
   services:
     nginx:
       volumes:
         - ./css:/app/frontend/css:ro
         - ./js:/app/frontend/js:ro
         - ./docs:/app/frontend/docs:ro
         - ./launcher.html:/app/frontend/launcher.html:ro
         - ./login.html:/app/frontend/login.html:ro
         - ./index.html:/app/frontend/index.html:ro
         - ./translator.html:/app/frontend/translator.html:ro
         - ./compare.html:/app/frontend/compare.html:ro
         - ./favicon.svg:/app/frontend/favicon.svg:ro
     backend:
       volumes:
         - ./backend:/app/backend
   ```

2. `.gitignore`에 추가할지 여부 결정
   - **추적 O (권장)**: 팀 전체가 동일 override 사용
   - 추적 X: 개인별 override 자유도

3. `docs/13-DOCKER-OPERATIONS.md`에 사용법 추가
   - 개발: `docker compose up -d` (override 자동 적용)
   - 프로덕션: `docker compose -f docker-compose.yml up -d`

#### 기능 영향성
- **0건**. override는 기존 이미지 위에 bind mount만 추가. 실행 로직 변경 없음.
- 프로덕션 배포 명령에 `-f docker-compose.yml`만 명시하면 override 무시됨. 배포 가이드 업데이트 필요.
- 주의: bind mount는 컨테이너 내부 경로를 덮어쓰므로, 이미지 내 파일이 아니라 호스트 파일이 서빙됨. 개발 중 의도된 동작.

#### Phase 1 실행 결과 (2026-04-11)

##### 구현 산출물
- `docker-compose.override.yml` 신규 — 7개 HTML + favicon + css/js/docs + docker/config.docker.js + docker/nginx.dev.conf + backend/tools bind mount
- `docker/nginx.dev.conf` 신규 — `sendfile off`, `open_file_cache off`, `expires -1`, `no-store` (WSL2 bind mount 호환)
- `docs/13-DOCKER-OPERATIONS.md § 6-7` 추가 — 개발 모드 사용법 및 프로덕션 배제 지침

##### 계획 외 추가 작업 (검증 과정에서 필수로 드러남)

**(1) 유령 dockerd 제거** — 검증 중에 WSL2 Ubuntu 네이티브 `dockerd`가 Docker Desktop과 병존하면서 `sdp-nginx`/`sdp-backend` 옛 컨테이너(2026-04-09자)를 계속 실행, **port 80을 독점 선점**해오던 사실 발견. 이로 인해 Plan-27 이후 모든 `http://localhost` 접속이 최신 이미지가 아닌 옛 컨테이너로 연결되고 있었음.
- 조치: `sudo systemctl stop+disable docker docker.socket`로 네이티브 dockerd 완전 비활성화
- 유틸 스크립트 보존: `scripts/ghost-dockerd-snapshot.sh`, `scripts/ghost-dockerd-disable.sh`
- 재부팅 후에도 자동 시작되지 않음 확인

**(2) 프로덕션 배포 스크립트 안전장치 + 잠복 버그 수정**

| 파일 | 변경 | 심각도 |
|---|---|---|
| `deploy.sh` | `export COMPOSE_FILE=docker-compose.yml` 고정 + override 감지 경고 | High (Phase 1 부작용 방지) |
| `patch-apply.sh` | `export COMPOSE_FILE` 고정 | Medium |
| `patch-apply.sh` | nginx.conf 목적지 `/etc/nginx/nginx.conf` → `/etc/nginx/conf.d/default.conf` | **Critical** (잠복 버그 — nginx 기동 실패 유발) |
| `patch-apply.sh` | config.docker.js 목적지 `/app/frontend/js/config.js` → `/app/docker/config.docker.js` | **High** (잠복 버그 — 무음 실패) |
| `patch-apply.sh` | `docker cp` 디렉터리 복사 시 `src/.` + `dst/` 패턴 적용 | Medium (중첩 디렉터리 방지) |

##### 검증 결과

| 항목 | 결과 |
|---|---|
| override 자동 병합 | ✅ `docker compose config` 기준 volumes 21개(dev) / 7개(prod) 정확 분기 |
| bind mount 실시간 반영 | ✅ echo로 추가한 마커가 재빌드 없이 HTTP 응답에 즉시 반영 |
| 컨테이너 내부 파일 MD5 == 호스트 파일 MD5 | ✅ `46cf3ad2...` 일치 |
| `sendfile off`, `open_file_cache off` 로드 | ✅ `nginx -T`로 확인 |
| 유령 nginx PID 672 소멸 | ✅ 프로세스 목록에서 사라짐 |
| port 80이 **우리 sdp-nginx**로 교체 | ✅ 액세스 로그에 port 80 요청이 **처음으로** 기록됨 |
| 응답 헤더가 dev 모드 패턴 | ✅ `Cache-Control: no-store, no-cache, must-revalidate` |
| HTTP 스모크 테스트 | ✅ 12/12 PASS — 5개 HTML, CSS/JS, config.js alias, 2개 API, 보안 403 2건 |

##### 사용자 관점 중요 변화
- 이 Phase 1 이전까지 `http://localhost`로 본 모든 화면은 사실상 **2026-04-09 시점의 옛 sdp-nginx** 가 서빙한 결과였음
- Phase 1 완료 시점부터 비로소 실제 최신 이미지/소스가 브라우저에 표시됨
- 브라우저 첫 방문 시 Ctrl+F5 권장 (브라우저 자체 캐시 제거)

##### 디스크에만 남은 잔여물 (긴급 아님, 참고용)
- `/var/lib/docker/containers/` 아래 유령 컨테이너 3개 디렉터리 (open-webui 정지본 포함)
- `/var/lib/docker/image/` 아래 옛 `sdp-*` 이미지 레이어, open-webui 이미지 레이어
- 추후 디스크 정리 필요 시 `sudo rm -rf /var/lib/docker` 로 일괄 제거 가능 (Docker Desktop은 별도 경로라 영향 없음)

---

### Phase 2 — Dockerfile.nginx COPY 블랙리스트 전환

**효과**: 새 폴더 추가 시 Dockerfile 수정 불필요
**노력**: 1시간
**리스크**: 중간 (`.dockerignore` 누락 시 불필요 파일이 이미지에 들어갈 수 있음)

#### 작업

1. `.dockerignore`에 프론트 제외 항목 추가 검토
   현재 이미 제외 중: `.git/`, `backend/packages/`, `tests/`, `workbench/`, `.claude/`, `data/`, `contents/`, `models/`, `backups/`, `logs/`, `*.tar`, `.env`, `README.md`, `CLAUDE.md`
   추가 검토 대상: `memory/`(없음), `.mcp.json`, `.playwright-mcp/`(이미 제외), `Dockerfile*`, `docker-compose*.yml`, `scripts/`(백엔드용), `tools/__pycache__`(이미 제외)

2. `Dockerfile.nginx` COPY 블록 교체
   ```dockerfile
   # 이전 (화이트리스트)
   COPY *.html      /app/frontend/
   COPY favicon.svg /app/frontend/
   COPY css/        /app/frontend/css/
   COPY js/         /app/frontend/js/
   COPY docs/       /app/frontend/docs/

   # 이후 (블랙리스트, .dockerignore 의존)
   COPY . /app/frontend/
   ```

3. 빌드 후 이미지 내부 검증
   ```bash
   docker run --rm smart-document-platform-nginx:latest ls -la /app/frontend/
   ```
   → 프론트 파일만 있고 backend/, workbench/ 등이 없어야 함

#### 기능 영향성
- `.dockerignore` 완전성에 의존. 누락 시 이미지에 불필요 파일 포함 → 이미지 크기 증가
- 파일 권한/소유자는 현재와 동일 (nginx 사용자)
- 런타임 동작 0 변경

---

### Phase 3 — `config.docker.js` 제거 (단일 소스)

**효과**: 가장 빈번한 divergence 원흉 제거
**노력**: 2~3시간
**리스크**: 중간 (런타임 주입 테스트 필요)

#### 현재 상태

두 파일의 실제 차이는 **단 2개 값**뿐이다:
| 키 | 로컬 `config.js` | 도커 `config.docker.js` |
|---|---|---|
| `backendUrl` | `'http://localhost:8000'` | `''` (상대경로) |
| `ollamaUrl` | `'http://localhost:11434'` | `''` (Nginx 경유) |

나머지는 **동일해야 하는데 수동 동기화 실패로 47줄이 벌어진 상태**.

#### 해결책 — 환경 감지 + 상대경로 기본값

```javascript
// js/config.js (단일 파일로 통합)
// 도커/프로덕션 환경 감지 — 포트가 없거나 80/443이면 상대경로 사용
const _isRelative = !window.location.port ||
                    window.location.port === '80' ||
                    window.location.port === '443';

const AUTH_CONFIG = {
    enabled: true,
    loginRequired: true,
    backendUrl: _isRelative ? '' : 'http://localhost:8000',
};

const AI_CONFIG = {
    enabled: true,
    useBackend: true,
    backendUrl: _isRelative ? '' : 'http://localhost:8000',
    ollamaUrl: _isRelative ? '' : 'http://localhost:11434',
    // ... 나머지 (단일 소스, 한 번만 작성)
};

// EDITOR_CONFIG, UPLOAD_CONFIG도 동일 패턴
```

#### 작업

1. `js/config.js`에 `_isRelative` 감지 로직 추가
2. 모든 `backendUrl`/`ollamaUrl` 기본값을 조건부로 변경
3. `docker/config.docker.js` **삭제**
4. `docker/nginx.conf`에서 `/js/config.js` alias 블록 **제거** (18-21줄)
5. `docker/Dockerfile.nginx`에서 `COPY docker/config.docker.js ...` 라인 제거
6. 로컬(8080 포트) + 도커(80 포트) 양쪽에서 로그인, API 호출, 챗봇 동작 확인

#### 기능 영향성 — 이 플랜에서 유일하게 주의 필요한 단계

- **영향 범위**: 모든 페이지 (AUTH/AI/EDITOR/UPLOAD 전 기능이 `backendUrl` 사용)
- **위험 시나리오**: 포트 감지 로직 오류 시 `backendUrl`이 잘못 설정되어 API 호출 전부 실패
- **완화**:
  - Phase 1 bind mount 환경에서 테스트 (재빌드 없이 즉시 검증 가능)
  - `window.location.origin`도 백업 감지 로직으로 추가 가능
  - 실패 시 롤백은 `git revert` 한 번으로 끝 (파일 단위 변경만)
- **테스트 체크리스트**:
  - [ ] 로컬 `python main.py` + `http.server 8080` 환경 → 로그인, 챗봇, 업로드 정상
  - [ ] 도커 `compose up` 환경 → 로그인, 챗봇, 업로드, 번역 정상
  - [ ] Playwright MCP로 양쪽 환경 스모크 테스트 자동화

---

### Phase 4 — Parity 체크 스크립트 + Pre-commit 훅 (안전망)

**효과**: 사전 감지 — 커밋 전 divergence 차단
**노력**: 1시간
**리스크**: 없음 (검증만, 코드 수정 없음)

#### 작업

1. `scripts/check-docker-parity.py` 신규 작성
   검사 항목:
   - 루트 HTML 파일 존재 여부 (새 HTML 파일이 Dockerfile에 누락됐는지)
   - `requirements.txt` 수정 여부 + Dockerfile 해시 재계산 필요성 경고
   - Phase 3 이후: `docker/config.docker.js`가 다시 나타나지 않았는지
   - `.dockerignore`와 Dockerfile COPY 패턴의 일관성

2. `.claude/skills/docker-build/SKILL.md`에 "0단계: 사전 점검" 추가
   ```markdown
   ### 0. 사전 점검 (Parity Check)
   wsl bash -c "cd ... && python scripts/check-docker-parity.py"
   경고/에러 있으면 사용자에게 확인 후 진행
   ```

3. (선택) Git pre-commit 훅
   `.githooks/pre-commit` — 같은 스크립트를 커밋 전에 실행

#### 기능 영향성
- **0건**. 검증 스크립트는 파일을 읽기만 함

---

## 3. 전체 기능 영향성 요약

| Phase | 사용자 노출 기능 영향 | 롤백 난이도 |
|---|---|---|
| 1 bind mount | **없음** (개발 전용) | 파일 삭제 |
| 2 COPY 블랙리스트 | **없음** (.dockerignore 잘 관리하면) | Dockerfile revert |
| 3 config 단일화 | **조건부 경로 로직 1개 추가** — 테스트 필수 | git revert |
| 4 parity 체크 | **없음** (읽기 전용 검증) | 스크립트 삭제 |

**결론**: Phase 1·2·4는 기능 영향 0건. Phase 3만 검증 필요하며, 검증은 Phase 1 bind mount 환경에서 재빌드 없이 빠르게 반복 가능.

---

## 4. 권장 진행 순서

1. **Phase 1만 먼저** — 즉시 체감 효과, 리스크 0. 이 단계만으로도 개발 생산성 대폭 향상
2. Phase 1 사용해보고 안정되면 Phase 2 (프로젝트 구조 변경 시점에)
3. Phase 3은 Phase 1 환경에서 안전하게 테스트하며 진행
4. Phase 4는 Phase 3 완료 직후 (검증 대상이 확정된 후)

**Phase 1만 해도** "로컬에서 고친 걸 도커에 반영하려면 매번 재빌드" 고통이 대부분 해결된다. 나머지는 선택.

---

## 5. 열려 있는 결정 사항

- [ ] `docker-compose.override.yml`을 git 추적할 것인가? (팀 공유 vs 개인 자유도)
- [ ] Phase 3의 포트 감지 로직을 `_isRelative` 말고 `window.location.origin`만으로 할 것인가?
- [ ] Phase 4 parity 스크립트를 Git pre-commit까지 걸 것인가, `docker-build` 스킬에만 둘 것인가?

---

## 6. 참고

- 12-Factor App Dev/Prod Parity — https://12factor.net/dev-prod-parity
- Docker Compose override files — https://docs.docker.com/compose/how-tos/multiple-compose-files/extends/
- `.dockerignore` files — https://docs.docker.com/build/building/context/#dockerignore-files
- 선행 계획: `done-27-docker-migration.md` (Phase 1~5 도커 전환 완료)
- 연관 계획: `done-30-docker-settings-cleanup.md` (설정 우선순위 확립, AI 모델 전역화)
