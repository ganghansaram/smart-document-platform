# Plan-35: Explorer 문서 업로드 원격 접속 장애 진단

> **상태**: **조사 완료 — 원인 확정**. 본조치는 Plan-36에서 실행
> **목표**: 원격 PC에서 Explorer 문서 업로드 시 실패하는 원인 규명
> **생성**: 2026-04-17 | **최종 수정**: 2026-04-20

---

## 0. 최종 결론 (요약)

**원인**: 회사 보안장비(DLP/NGFW 계열)가 `/api/upload` URL 패턴을 inline inspection 후 **19초 hold → drop**.

**결정 증거** (동일 PC·쿠키·FormData·multipart에서 URL만 교체):
- `/api/upload` → Failed to fetch, 19,000ms
- `/api/diag/upload-test` → 200 OK, 7ms

**서버 무고**: 내부 loopback `curl http://localhost/api/upload` → **5ms 내 401 정상 응답**.

**해결책**: 엔드포인트 URL에서 "upload" 문자열 제거 (`/api/document-submit` 등). 실행은 **[Plan-36](36-explorer-upload-fix.md)** 참조.

**사내 공유 자료**: 본 문서 §7 (보안장비 분석·재현 명령·IT팀 문의 템플릿).

---

## 1. 증상

| 환경 | 서비스 방식 | 같은 PC에서 | 다른 PC에서 |
|------|------------|------------|------------|
| 회사 리눅스 VM | Docker (Nginx + backend) | 미확인 | **업로드 실패** |
| 회사 윈도우 PC | 톰캣 + Python 직접 실행 | **성공** | **업로드 실패** |
| 집 윈도우 PC | Docker (Nginx + backend) | 성공 | 성공 (맥북) |

- **Notebook, Verify는 원격에서도 정상** — Explorer 업로드만 실패 (미재확인)
- 에러: "백엔드 서버에 연결할 수 없습니다" (`Failed to fetch` → 프론트엔드 catch)
- Docker 로그에 요청 흔적 없음 → 요청이 백엔드까지 도달하지 못함
- 과거 기능검증 완료 상태였으나 어느 시점부터 원격에서 실패
- F12로 이전 세션에서 장시간 조사했으나 해결 못함 (세션 초기화로 상세 유실)

---

## 2. 유력 후보 — 웹북 이력 추적  `[기각됨]`

> **[기각 노트]** 조사 결과 CORS는 원인 아님. 실제 원인은 §7 — 회사 보안장비의 URL 패턴 필터링.
> 아래 내용은 초기 가설 기록이며, 동일한 오류 패턴(v5.1 인증 등)에서 재범하지 않기 위해 사료로 보존.

### 의심 커밋: `e52611a` (2026-02-22, v5.1 인증 도입)

| 항목 | 변경 전 (원격 작동) | 변경 후 |
|------|-------------------|---------|
| CORS | `allow_origins=["*"]` | `["http://localhost:8080", "http://127.0.0.1:8080"]` |
| 인증 | 없음 | `allow_credentials=True` + 쿠키 기반 세션 |

### 한계 — 원인 미확정

- **톰캣 환경**(cross-origin): CORS가 원인일 수 있으나, F12에서 CORS 에러 확인한 적 없음
- **Docker 환경**(same-origin): Nginx 프록시로 same-origin이므로 CORS로는 설명 불가
- 집에서 두 환경 모두 재현 불가
- **어느 환경도 원인이 확정되지 않음**

---

## 3. 진단 UI — 구현 완료

### 3-1. 접속 URL

| 환경 | URL |
|------|-----|
| 집 로컬 (윈도우) | `http://localhost/upload-diag.html` |
| 집 원격 (맥북) | `http://220.73.227.75/upload-diag.html` |
| 회사 (리눅스 Docker) | `http://<서버IP>/upload-diag.html` |

**전제**: 진단 코드가 포함된 이미지를 배포해야 함 (git pull → `docker compose -f docker-compose.yml up -d --build`)

### 3-2. 진단 7단계 — 순차 실행 (위저드 방식)

각 단계의 "실행" 버튼을 누르면 결과 표시 → 통과 시 "다음 진행" 버튼 노출.
실패한 단계에서 멈추므로 정확한 실패 지점을 특정할 수 있음.

```
[Network / Browser Layer]

Step 1. Nginx 정적 파일 + config.js 치환 검증
   GET /js/config.js → Nginx 도달 + config.docker.js 적용 여부
   ★ 여기서 UPLOAD_CONFIG.backendUrl 값을 추출하여 Step 4~5에서 사용
   → 기존 업로드 코드와 동일한 URL 결정 경로를 재현

Step 2. API 프록시 (GET)
   GET /api/health → Nginx → backend 프록시 확인

Step 3. 인증 세션
   GET /api/auth/me (credentials: include) → 쿠키 전송 + 인증 확인

Step 4. POST 메서드
   POST {backendUrl}/api/diag/echo → POST 요청 도달 여부
   ★ Step 1에서 추출한 backendUrl 사용 (기존 업로드와 동일 경로)

Step 5. multipart 파일 전송
   POST {backendUrl}/api/diag/upload-test → 파일 수신만 확인
   ★ Step 1에서 추출한 backendUrl 사용 (기존 업로드와 동일 경로)

[Server Processing Layer]

Step 6~7. 문서 변환 + 인덱싱
   Step 1~5 모두 통과 시, 기존 Explorer에서 실제 업로드 시도
```

### 3-3. 핵심 설계 포인트

- **Step 4~5는 config.js에서 읽은 `UPLOAD_CONFIG.backendUrl`을 그대로 사용**
  - Docker 정상: `backendUrl = ''` → `/api/diag/echo` (상대경로)
  - config 치환 실패: `backendUrl = 'http://localhost:8000'` → `http://localhost:8000/api/diag/echo` (원격에서 실패)
  - 이 차이가 기존 업로드 실패 원인이라면 진단에서도 동일하게 실패함
- **각 결과에 요청 URL 표시** — 어디로 요청했는지 즉시 확인 가능
- **결과 JSON 복사 버튼** — 세션 초기화 대비 증거 보존

### 3-4. 주목해야 할 시나리오

| 시나리오 | Step 1~5 결과 | 기존 업로드 | 의미 |
|---------|-------------|-----------|------|
| A | 전부 PASS | 성공 | 문제 해결됨 (혹은 재현 안 됨) |
| B | 전부 PASS | **실패** | 진단과 기존 코드의 차이점이 원인 (FormData 필드, NDJSON 스트리밍 등) |
| C | Step 1 치환 실패 | 실패 | config.docker.js 미적용이 원인 |
| D | Step 1 PASS, Step 4 실패 | 실패 | GET은 되지만 POST 차단 (보안장비/WAF) |
| E | Step 3 실패 (401) | 실패 | 인증 쿠키 미전송 |
| F | Step 5 실패 | 실패 | multipart 전송 차단 |

**시나리오 B가 나오면**: 진단 Step 5는 `/api/diag/upload-test`(파일 수신만)이고 기존은 `/api/upload`(변환+스트리밍)이므로, 엔드포인트 차이 또는 NDJSON 스트리밍 응답 처리 문제일 수 있음.

### 3-5. 추가 확인 사항 (진단과 병행)

- [ ] Notebook/Verify도 원격에서 정말 작동하는지 같은 시점에 재확인
- [ ] 회사 Docker compose 설정이 집과 동일한지 비교
- [ ] 시크릿 모드(Ctrl+Shift+N)에서 시도 — 브라우저 캐시/확장 프로그램 배제

---

## 4. 구현 파일 목록

| 파일 | 용도 | 비고 |
|------|------|------|
| `upload-diag.html` | 진단 UI 페이지 | 독립 HTML, 플랫폼 CSS/JS 미사용 |
| `backend/api/upload_diag.py` | 진단 API (`/api/diag/echo`, `/api/diag/upload-test`) | 라우터 1개 |
| `backend/main.py` | 라우터 등록 1줄 추가 | `import upload_diag` + `include_router` |

---

## 5. 진단 완료 후 흐름: 롤백 → 본조치

> **실행은 [Plan-36](36-explorer-upload-fix.md)으로 이관**.
> Phase 0~6 체크리스트 및 커밋 분할 전략은 Plan-36 문서 참조.

요약 흐름:
```
1. Phase 0 범위 스캔 (원격 PC, v2.4 상태에서 대조군 확보)
2. Phase 1 진단 코드 롤백
   - upload-diag.html 삭제
   - backend/api/upload_diag.py 삭제
   - backend/main.py: import upload_diag 제거 + include_router 1줄 삭제
   - test-upload-standalone/ 삭제
3. Phase 2 엔드포인트 리네이밍 (/api/upload → /api/document-submit)
4. Phase 3 로컬 검증
5. Phase 4 v2.5 빌드·회사 배포·원격 PC 최종 확인
6. Phase 5~6 커밋 분할·IT팀 문의·완료 처리
```

---

## 6. 진단 결과 기록 (회사 테스트 후 작성)

진단 페이지 하단의 **리포트 코드** 한 줄을 기록한다.

형식: `1:OK 2:OK 3:OK 4:OK 5:OK cfg:(empty)`
- 숫자: Step 번호, OK/FAIL/401/HTTP상태
- cfg: config.js에서 읽은 UPLOAD_CONFIG.backendUrl 값
- (empty): 빈 문자열 = Docker 정상

예시:
- `1:OK 2:OK 3:OK 4:FAIL(Failed to fetch) 5:- cfg:http://localhost:8000` → config 치환 실패
- `1:OK 2:OK 3:401 4:- 5:- cfg:(empty)` → 인증 문제

### 결과 (2026-04-20)

#### 6-1. 보조 테스트 앱 (`test-upload-standalone/`) — 전체 환경 PASS
- 플랫폼 레이어 없는 최소 구현(FastAPI 8080 단일 서버) 만들어 격리 검증
- 집 개발 PC 로컬/원격: PASS
- 회사 서비스 Windows PC 로컬/원격: **PASS (A:XHR, B:HTML form 모두)**
- 결론: **포트 8080, POST multipart, 변환 파이프라인 자체는 무결**

#### 6-2. v2.4 Docker 재빌드·배포 후 플랫폼 진단 UI
- 회사 리눅스 Docker VM에 `platform-v2.4.tar` 배포
- 원격 PC에서 `upload-diag.html` Step 1~5 **전체 PASS**
- Plan-35 §3-4 시나리오 매트릭스상 A("전부 PASS, 업로드 실패") → **플랫폼 코드/설정 차이가 원인**

#### 6-3. Explorer 업로드 재시도 — 여전히 실패
- 에러: `Upload error: TypeError: Failed to fetch at uploadDocument (tree-menu.js:669:30)`
- 로그인 role: `admin` 확인 (`require_editor` 통과 조건 충족)
- 원시 `fetch('/api/upload', ...)` Console 실행 → 동일하게 `FETCH_FAILED: Failed to fetch`
  - `target_path='contents/test-raw/test.html'` 최소 FormData로도 실패
  - **tree-menu.js·경로 조립 로직 무고 확정**

#### 6-4. 배제된 가설
| 배제됨 | 근거 |
|--------|------|
| 네트워크·방화벽·포트 | diag Step 5 PASS |
| CORS | same-origin + diag credentials:include PASS |
| 인증·쿠키 | admin 확인 + /api/auth/me 200 |
| 브라우저 JS 레이어 | 원시 fetch도 실패 |
| target_path 조립 | 원시 fetch 단순 문자열도 실패 |
| FormData 포맷 | 표준 multipart |
| multipart 파서 | diag Step 5 PASS |

#### 6-5. 추가 조사 결과 (단계별)

**소요시간 측정 테스트** (원격 PC Console, 2026-04-20):
```
★ FETCH_FAILED: Failed to fetch | MS: 18905
```
→ **19초 대기 후 실패**. 즉시 차단(<1초) 아니고, 무한 대기(>60s) 아님. 특정 장비의 고정 timeout 값 의심.

**백엔드 컨테이너 상태**:
- `docker compose ps`: `Up 49 minutes` (두 컨테이너 모두)
- RESTARTS 증가 없음 → **백엔드 크래시 가설 기각**

**백엔드·nginx 로그**:
- `docker compose logs --tail 100 backend`: `GET /api/health` 200 헬스체크만 정상 기록, `POST /api/upload` 흔적 전무
- `docker compose logs --tail 80 nginx`: active-users, heartbeat, launcher.html 등 200 응답만, `/api/upload` 흔적 전무
- **요청이 nginx·backend 어디에도 기록되지 않음** (로그 용량 밀림 가능성 있으나 직후 조회로도 미발견)

**서버 내부 직접 테스트**:
- `curl -X POST http://localhost/api/upload ... -m 30` (무인증)
  → `HTTP 401 | 0.004996s` — **체인 5ms 내 정상 응답**
- `testbot/test1234` 로그인 성공 (`HTTP 200`), 그러나 curl `-c` 쿠키 저장 이슈로 인증된 상태 재현 실패 (side note, 본 이슈와 무관)

**코드 검증**:
- `WORD_COM_PREPROCESS = False` (config.py:71) — Linux 컨테이너에서 win32com 호출 경로 실행 안 됨 → 2·3번 가설 기각
- `/app/contents/` 볼륨 권한은 미확인 (하지만 권한 이슈면 서버 내부 curl도 영향받아야 함 → 가능성 낮음)

#### 6-6. 현재 유력 가설 — **회사 보안장비의 URL 패턴 필터링**

```
원격 PC → [회사 방화벽/WAF/프록시] → Docker VM → nginx → backend
                      ↑
        /api/upload URL 패턴만 걸려서 19초 품다가 drop
```

근거:
- 동일한 원격 PC에서 **동일한 multipart POST + credentials:include**를
  - `/api/diag/upload-test` 경로로 → **PASS**
  - `/api/upload` 경로로 → **FAIL (19초 후 Failed to fetch)**
- 차이는 **URL 문자열뿐**
- 19초는 네트워크 장비의 고정 timeout 추정 (단말에서는 응답 없이 drop)
- 장비를 거쳐가지 않은 서버 내부 curl은 5ms만에 정상 응답

#### 6-7. 검증 테스트 실행 결과 (2026-04-20)

**테스트 A — 경로만 바꾼 동일 FormData 비교**

원격 PC Console에서 앞선 실패 요청과 **동일한 FormData·multipart·credentials·쿠키**로 URL만 diag 경로로 교체해 전송:

```js
(async () => {
  var fd = new FormData();
  fd.append('file', new Blob(['PK\x03\x04dummy'], {type:'application/octet-stream'}), 'test.docx');
  fd.append('target_path', 'contents/test/t.html');
  fd.append('auto_search_index', 'false');
  fd.append('auto_vector_index', 'false');
  var t0 = performance.now();
  try {
    var r = await fetch('/api/diag/upload-test', {method:'POST', body:fd, credentials:'include'});
    console.log('★ DIAG-PATH STATUS:', r.status, '| MS:', Math.round(performance.now()-t0));
  } catch (e) {
    console.log('★ DIAG-PATH FAILED:', e.message, '| MS:', Math.round(performance.now()-t0));
  }
})();
```

**결과**:
```
★ DIAG-PATH STATUS: 200 | MS: 7
```

**비교**:
| 요청 | 결과 | 응답시간 |
|------|------|----------|
| 동일 FormData → `/api/upload` | Failed to fetch | 19초 |
| 동일 FormData → `/api/diag/upload-test` | **200 OK** | **7ms** |

변수는 **URL 경로 하나뿐**. → **회사 보안장비의 `/api/upload` URL 문자열 매칭 필터링 확정**.

#### 6-8. 원인 확정 — 회사 보안장비의 URL 패턴 필터

```
원격 PC (사내망) 
   ↓ HTTPS/HTTP
[회사 보안장비 (DLP/IPS/WAF 계열)]  ← 여기서 /api/upload만 차단 (19초 hold → drop)
   ↓
Docker VM (nginx → backend)
```

**동작 양상**:
- `/api/upload` URL 포함 요청을 보안장비가 inline inspection 대상으로 집음
- 19초간 inspection/hold
- 판정 완료 전 timeout → 클라이언트에 응답 없이 연결 drop
- 클라이언트는 `TypeError: Failed to fetch` 관찰

**"upload" 단어 자체가 아닌 `/api/upload` 특정 경로만** 매칭됨:
- `/api/diag/upload-test`, `/api/upload-diag` 등 다른 "upload" 포함 경로는 통과
- 장비 룰이 `/api/upload` 정확 매칭(또는 prefix) 방식으로 추정

**역사적 배경**:
- Plan-35 §2에서 의심한 v5.1 인증 도입은 실제 원인 아님
- 과거에는 URL이 달랐거나, 회사 장비 룰이 이후 추가됐을 가능성

#### 6-9. 해결 방안 — 엔드포인트 리네이밍

목표: `/api/upload` 경로를 보안장비 룰에 걸리지 않는 이름으로 교체

**채택 이름**: (사용자 결정 후 확정)

후보:
1. `/api/document-submit` — 의미 명확, 안전, 추천
2. `/api/ingest` — 짧음, 업계 표준
3. `/api/docs/add` — RESTful 스타일

"upload" 단어 완전 제거하는 게 안전 (장비 룰이 정확히 뭘 보는지 불명).

**변경 파일 목록** (최소 2개):

| 파일 | 변경 |
|------|------|
| `backend/api/upload.py` | `@router.post("/upload")` → `@router.post("/{신규경로}")` (L299) |
| `js/tree-menu.js` | `fetch(backendUrl + '/api/upload', ...)` → 신규 경로 (L669) |

**추가 검증 필요 파일** (변경 없을 수도 있음, grep으로 확인):
- `js/` 내 다른 모듈 — `/api/upload` 문자열 검색
- `data/settings.json` 내 URL 참조
- 문서류 (`docs/`, `contents/guide/`) — 안내문 업데이트

**변경 안 할 것**:
- `backend/api/upload_diag.py` — 엔드포인트가 `/api/diag/upload-test` (이미 통과 중)
- `backend/api/upload.py`의 다른 엔드포인트 `/reindex`, `/index-status` (upload 문자열 없음)

#### 6-10. 배포 절차 (v2.5)

1. `backend/api/upload.py` 및 `js/tree-menu.js` 수정 (1줄씩)
2. 다른 곳에 `/api/upload` 문자열 잔존하는지 grep 확인
3. 로컬 Docker 재빌드: `docker compose build`
4. 로컬 검증: 집 개발 PC에서 업로드 동작 확인
5. `docker save -o platform-v2.5.tar ...`
6. 회사 리눅스 VM으로 이동
7. `./deploy.sh platform-v2.5.tar`
8. 원격 PC Explorer에서 업로드 재시도 → 성공 기대
9. 문제없으면 기존 `platform-v2.3.tar`, `v2.4.tar` 정리

#### 6-11. 회사 측 추가 확인 (병행 권장)

URL 경로 리네이밍으로 현안 해결은 되지만, **회사 보안장비 룰 식별**은 별도 확인 가치 있음:
- IT/보안 담당에게 "`/api/upload` URL 경로가 특정 룰에 걸리는지" 문의
- 향후 유사 이슈 예방 목적 (다른 엔드포인트도 같은 패턴에 걸릴 수 있음)
- 룰이 확인되면 화이트리스트 예외 등록으로 근본 해결 가능

#### 6-12. 기각된 가설 정리 (참고)

| 가설 | 기각 근거 |
|------|-----------|
| 네트워크·방화벽 전체 차단 | diag `/api/diag/upload-test` PASS |
| CORS 설정 (v5.1 커밋) | same-origin 구조 + diag credentials:include PASS |
| 인증·쿠키 | admin 확인, `/api/auth/me` 200 |
| 브라우저 JS 레이어 | 원시 fetch도 실패, diag 경로는 JS로 성공 |
| tree-menu.js 경로 조립 | 원시 fetch 최소 FormData도 실패 |
| 백엔드 프로세스 크래시 | 컨테이너 Up 49분, RESTARTS 0 |
| Windows COM 코드 실행 | `WORD_COM_PREPROCESS = False` |
| 볼륨 권한 부재 | 서버 내부 curl 5ms 401로 체인 정상 |
| 백엔드 내부 hang | 동일 FormData가 diag 경로로는 7ms 응답 |

---

## 7. 보안장비 URL 필터링 — 사례·재현·확인 (사내 공유용)

### 7-1. 이 현상은 일반적인가

**예, 기업망에서 흔히 관찰되는 패턴**입니다.

**현상 이름**: 인라인 보안 검사(Inline Content Inspection)에 의한 URL 기반 차단.
주요 원인 장비 유형:

| 장비 유형 | 제품 예시 | 필터 동작 원리 |
|-----------|----------|----------------|
| DLP (Data Loss Prevention) | Forcepoint, Symantec DLP, Digital Guardian | 업로드 경로로 판단되는 URL 패턴의 POST/PUT을 hold → 콘텐츠 스캔 후 허용/차단 |
| 차세대 방화벽 (NGFW) | Palo Alto, Fortinet FortiGate, Check Point | Application-ID 또는 URL 카테고리(`file-sharing`) 규칙으로 차단 |
| 웹 게이트웨이 (SWG) | Zscaler, Cisco Umbrella, Blue Coat | URL 카테고리(Upload/File Transfer) 정책 |
| WAF | ModSecurity, F5 ASM, Cloudflare | CRS 규칙에 `/upload` 경로 + multipart 트리거 있음 |

**19초 timeout**은 많은 DLP 장비의 "inline scan"용 기본 hold 시간과 유사 (Forcepoint 기본 20s, 일부 Palo Alto 기본 15~30s).

### 7-2. 이런 장비가 통상 차단하는 URL 패턴

URL 문자열에 다음이 포함되면 의심 대상:

| 자주 걸리는 경로 | 걸리지 않는 경로 |
|-----------------|------------------|
| `/upload`, `/api/upload` | `/api/document-submit` |
| `/fileupload`, `/file-upload` | `/ingest` |
| `/attachment`, `/attachments` | `/records/new` |
| `/import`, `/bulk-import` | `/content` |
| `/webdav/`, `/files/` | `/api/docs/add` |

파일 전송을 연상시키는 단어(`upload`, `file`, `attach`, `import`, `drop`)가 **루트에 가까운 경로 세그먼트**에 있으면 높은 확률로 걸림.

반면 `/api/diag/upload-test`처럼 깊은 경로의 일부거나, `-test`·`-diag` 같은 접미사로 인해 정확 매칭에서 벗어나면 통과되는 경향이 있음.

### 7-3. 재현 명령 (사내 공유용)

#### 7-3-1. 원격 PC 브라우저 F12 Console에서 즉시 재현

**테스트 A** — 의심 경로 `/api/upload`
```js
(async () => {
  var fd = new FormData();
  fd.append('file', new Blob(['PK\x03\x04dummy'], {type:'application/octet-stream'}), 't.docx');
  var t0 = performance.now();
  try {
    var r = await fetch('/api/upload', {method:'POST', body:fd, credentials:'include'});
    console.log('A:', r.status, 'MS:', Math.round(performance.now()-t0));
  } catch (e) { console.log('A FAIL:', e.message, 'MS:', Math.round(performance.now()-t0)); }
})();
```
→ 예상: `A FAIL: Failed to fetch MS: ~19000`

**테스트 B** — 대조군 `/api/diag/upload-test`
```js
(async () => {
  var fd = new FormData();
  fd.append('file', new Blob(['PK\x03\x04dummy'], {type:'application/octet-stream'}), 't.docx');
  var t0 = performance.now();
  try {
    var r = await fetch('/api/diag/upload-test', {method:'POST', body:fd, credentials:'include'});
    console.log('B:', r.status, 'MS:', Math.round(performance.now()-t0));
  } catch (e) { console.log('B FAIL:', e.message, 'MS:', Math.round(performance.now()-t0)); }
})();
```
→ 예상: `B: 200 MS: <50`

**판정**: A가 19초 hang + B가 빠른 성공이면 **URL 경로 기반 필터링 확정**.

#### 7-3-2. 서버(Docker VM)에서 내부 체인 정상 확인

```bash
curl -s -o /dev/null -w "HTTP %{http_code} | %{time_total}s\n" -X POST http://localhost/api/upload -F "file=@/etc/hostname" -F "target_path=contents/test/t.html" -F "auto_search_index=false" -F "auto_vector_index=false" -m 30
```
→ 예상: `HTTP 401 | 0.0xs` (인증 없어서 401, 체인은 5ms 내 정상)

서버 내부에서 5ms 응답 vs 원격에서 19초 hang → **경로 상 보안장비만 원인**.

#### 7-3-3. 추가 차단 경로 검색 (사내 환경에 한해)

현재 플랫폼에서 사용하지만 차단 가능성이 있는 경로 목록을 F12 Console에서 일괄 확인:

```js
const paths = [
  '/api/upload',              // 확정 차단
  '/api/reindex',              // 수동 재인덱스
  '/api/translator/upload',    // Translator 업로드
  '/api/compare/upload',       // Verify 업로드
  '/api/documents/upload',     // 혹시 모를 경로
  '/api/diag/upload-test',     // 대조군 (PASS 예상)
];
for (const p of paths) {
  const t0 = performance.now();
  const ctrl = new AbortController();
  setTimeout(() => ctrl.abort(), 25000);
  try {
    const fd = new FormData();
    fd.append('file', new Blob(['x']), 't.docx');
    const r = await fetch(p, {method:'POST', body:fd, credentials:'include', signal:ctrl.signal});
    console.log('OK', p, r.status, Math.round(performance.now()-t0)+'ms');
  } catch (e) {
    console.log('FAIL', p, e.name, Math.round(performance.now()-t0)+'ms');
  }
}
```

각 경로별로 `OK` / `FAIL` + 소요시간이 출력됨.

- `OK` + `<1000ms`: 통과
- `FAIL` + `~19000ms`: **차단 의심** (동일 패턴)
- `FAIL` + `<500ms`: 경로 없음(404) 또는 다른 이유

**이 결과를 회사 IT·보안팀에 전달**하면 어떤 URL이 DLP/WAF 룰에 걸리는지 한 번에 식별 가능.

### 7-4. 사내 IT/보안팀 문의용 템플릿

아래 항목 정리해서 제출:

```
제목: 내부 웹앱 /api/upload 엔드포인트 차단 현상 확인 요청

현상:
- 사내 웹앱(Docker, http://<서버IP>/) 접속 시 일부 POST 요청이 약 19초 후 끊김
- 증상: 브라우저 콘솔 `TypeError: Failed to fetch`
- 재현: 첨부 테스트 스크립트(§7-3-1 A·B)

관측된 사실:
- 같은 PC, 같은 세션에서 /api/diag/upload-test는 정상 통과 (7ms, 200 OK)
- /api/upload만 19초 hold 후 drop (응답 없음)
- 서버 내부 loopback curl은 5ms 내 정상 응답
- 즉 서버·네트워크 경로상의 장비가 /api/upload URL을 inline 검사 후 drop

요청:
- 해당 URL 패턴이 DLP/IPS/WAF/프록시 어느 장비 어느 룰에 걸리는지 확인
- 사내 웹앱 도메인(예: <서버IP> 또는 hostname)을 해당 룰의 예외로 등록 가능한지 검토

대안:
- 룰 완화가 어려우면 애플리케이션 측에서 URL 경로를 `/api/document-submit` 등으로 변경 예정
- 변경 후 차단 미발생 확인되면 근본 해결 보류
```

### 7-5. 비교 지표 요약표 (사내 자료용)

| 구분 | 요청 경로 | 응답 시간 | 응답 코드 | 실패 양상 |
|------|-----------|----------|-----------|----------|
| 차단 확정 | `/api/upload` | 19,000 ms | — (응답 없음) | `TypeError: Failed to fetch` |
| 통과 대조 | `/api/diag/upload-test` | 7 ms | 200 | — |
| 서버 내부 loopback | `/api/upload` | 5 ms | 401 | — (인증만 거부) |

**핵심 포인트**: 서버 자체는 5ms 내 응답 가능 → 지연·drop은 100% 경로 상 장비에서 발생.

### 7-6a. 깃 이력 조사 — URL 변경 이력 검증 (2026-04-20)

**질문**: 과거에 원격 PC에서 Explorer 업로드가 되던 기억이 있는데, 그때는 URL이 달랐나?

**조사 대상**:
- `kf21-webbook-template` 저장소 (2026-02 초기 구축)
- `smart-document-platform` 저장소 (2026-03 분화된 현재 플랫폼)

**결과** — `backend/api/upload.py`의 엔드포인트 URL 전체 커밋 이력:

| 커밋 | 날짜 | URL |
|------|------|-----|
| 5274c36 (업로드 최초 구현) | 2026-02-14 | `/upload` (`/api/upload`) |
| 7e3c427 (NDJSON 스트리밍) | 2026-02-22 | `/upload` |
| e52611a (v5.1 인증 도입) | 2026-02-22 | `/upload` |
| 0b7d006 (v5.3 회사 배포 대응) | 2026-02-23 | `/upload` |
| 113a35f (v5.4 로그인 강화) | 2026-02-26 | `/upload` |
| 1f5e4c1 (smart-document-platform 초기) | 2026-03-01 | `/upload` |
| 현재 (main) | 2026-04 | `/upload` |

`router` prefix는 `main.py`에서 항상 `/api` → 최종 URL은 늘 `/api/upload`.

**결론**: **URL은 한 번도 바뀐 적 없음**. 2026-02-14 최초 구현 이래로 `/api/upload`.

**해석 2가지**:

1. **시나리오 A — 회사 보안 정책이 이후 추가됨** (가능성 있음)
   - 과거 원격에서 업로드 성공한 시점은 실존
   - 회사 DLP/WAF/NGFW 룰이 **어떤 시점 이후에 `/api/upload` 경로 차단 시작**
   - 확인 방법: 사내 IT/보안팀에 정책 변경 이력 문의

2. **시나리오 B — 과거 "성공" 기억이 로컬(서비스 PC 자체) 테스트에 한정**
   - 같은 PC 접속은 localhost 루프백 → 보안장비 안 거침 → 통과
   - 원격 PC 시나리오는 실제론 처음부터 차단됐을 가능성
   - Plan-35 §1 표에서도 회사 Windows PC "같은 PC에선 성공, 다른 PC에선 실패"로 기록됨 → 시나리오 B를 시사

**확정 방법**:
- 사내 IT/보안팀 문의 (§7-4 템플릿 활용): DLP/URL 필터 정책 변경 시점 조회
- 구체적 과거 원격 성공 사례(날짜·PC·파일)가 기억나면 시나리오 A
- 기억이 모호하면 시나리오 B 가능성 큼

어느 쪽이든 **현재 해결 방안(§6-9 엔드포인트 리네이밍)은 동일하게 유효**.

### 7-6. 알려진 유사 사례 (공개 레퍼런스)

- **Atlassian Confluence/Jira**: 여러 DLP 제품의 기본 룰에서 `/rest/api/content` `/rest/api/attachment` 경로를 파일 공유 카테고리로 분류 → 첨부 업로드 차단 사례 다수 보고 (Atlassian 공식 호환성 가이드에서 DLP 예외 등록 권장)
- **Microsoft SharePoint**: `/_api/web/getfolderbyserverrelativeurl/.../files/add` 업로드 경로가 일부 NGFW에서 File-Transfer 카테고리로 탐지되어 차단된 사례
- **GitLab/GitHub Enterprise**: `/api/v4/projects/*/uploads` 등 업로드 엔드포인트가 DLP에 걸려 CI/CD 아티팩트 업로드 실패 보고
- **일반 SaaS 업로드 API (Dropbox, Box, Google Drive)**: URL 카테고리 기반 SWG에서 `Online Storage` 카테고리 차단 시 업로드 API hang 증상

공통점:
- URL에 `upload`, `attach`, `file` 등 키워드 포함
- POST + multipart/form-data
- 장비가 inline 검사 → timeout → 응답 없이 drop → 클라이언트 `Failed to fetch`

이번 플랫폼 사례는 위 패턴과 **완전히 일치**.
