# Plan-68 Phase 0 — 진단·증거수집 (회사 리눅스 VM 현장)

> 수집일: 2026-07-02 (회사 리눅스 VM 터미널 직접 접근)
> 대상 컨테이너: `sdp-backend`(Explorer 백엔드), `sdp-nginx`(프론트 서빙)
> Ollama: 별도 서버(`http://xxx.xxx.xxx.179:11434`, 리눅스 네이티브 설치)

## 컨테이너 현황
- `sdp-nginx: Up 9h`, `sdp-backend: Up 9h` (그 외 csrm-*, webreader-tts 는 타 프로젝트, 무관)

## A2 — 임베딩 GPU 경로 ✅ 원인 확정

**결정적 발견: 배포 환경에 레거시 `EMBEDDING_BACKEND=local` 이 설정됨.**

- `docker exec sdp-backend env` 실측:
  - `EMBEDDING_BACKEND=local`  ← 문제
  - `OLLAMA_URL=http://xxx.xxx.xxx.179:11434`
  - `EMBEDDING_BACKEND_INDEX` / `_RUNTIME` = **없음(미설정)**
- `embedding_client._resolve_backend()`(`embedding_client.py:62-73`) 해석 순서:
  1. `EMBEDDING_BACKEND_INDEX` 미설정 → 건너뜀
  2. 레거시 `EMBEDDING_BACKEND=local` → **index·runtime 둘 다 `local` 반환**
  3. (코드 기본값 index=ollama 에 **도달하지 못함**)
- ⇒ **인덱싱 임베딩이 GPU Ollama 가 아니라 컨테이너 내부 CPU(sentence-transformers)로 실행 중.**
- 메모리 실측: 358섹션 CPU 575.7s vs GPU 18.5s (31배). 문서 증가 시 벡터 전체 재빌드가 **600초 타임아웃** 초과 → 사용자 보고 "수십 분 후 실패" 와 정합. "GPU 옵션이 안 보여"의 정체이기도 함.

**전환 안전성 확인 (Ollama 서버 실측):**
- 백엔드→Ollama 도달 OK (`/api/tags` count=6)
- `bge-m3:latest` 모델 존재 ✅
- `/api/embed` 실호출: `status 200`, `dim 1024` ✅ (end-to-end 동작)

**현장 추가 확인 (반영 방법 확정):**
- VM `.env` 에는 EMBEDDING 줄 **없음**. 값 `local` 의 출처는 **VM `docker-compose.yml:14` `EMBEDDING_BACKEND=${EMBEDDING_BACKEND:-local}`** — 즉 기본값이 `local` 로 박힘.
- ⚠️ **VM compose 는 리포지토리보다 구버전.** 리포(현재)는 `EMBEDDING_BACKEND`(기본 빈값) + `EMBEDDING_BACKEND_INDEX`/`_RUNTIME` 3줄(Plan-40). VM 은 레거시 1줄만, `env_file` 미사용. ⇒ `.env` 로는 `EMBEDDING_BACKEND` 만 컨테이너에 전달됨(compose 가 `${EMBEDDING_BACKEND_INDEX}` 를 참조하지 않으므로 `.env` 에 넣어도 무효).
- **VM 배포 코드는 신버전** — `docker exec sdp-backend python -c "...'EMBEDDING_BACKEND_INDEX' in open(embedding_client.__file__).read()"` → **True** (용도별 변수 지원). ⇒ 이미지 재빌드 불필요.

**처방(확정):** VM `docker-compose.yml` 의 `environment:` 에 `- EMBEDDING_BACKEND_INDEX=ollama` **한 줄 추가** → `docker compose up -d`(recreate).
- 코드가 per-purpose 를 먼저 보므로 **index=ollama(GPU), runtime=local 유지**(부작용 없음). (대안: `.env` 에 `EMBEDDING_BACKEND=ollama` → index·runtime 둘 다 ollama, 검색이 Ollama 의존.)
- 기대: 재빌드 ~575s → ~18.5s. Ollama 가용·bge-m3·dim1024 확인됨.
- **현장 반영은 사용자 요청으로 보류** — 편집·검증(grep 두 줄 정상)까지 완료, `up -d` 만 미실행. `docker-compose.yml.bak` 백업 있음.
- Ollama 실패 시 CPU 폴백 없음(`raise_for_status`)은 별도(Plan-68 C4 정책).

## A1 — 업로드 실패 (`Unexpected token '<'`) ✅ 원인 확정

**실패 문서 크기 = 283,670 KB ≈ 277 MB. nginx `client_max_body_size 100m` 초과.**

- nginx 는 `Content-Length` 헤더만 보고 100MB 초과 시 **본문 수신 전 즉시 `413` HTML 에러 페이지** 반환 → 프론트가 JSON 파싱 시도 → `Unexpected token '<'`(`<`=`<html>`). 요청이 백엔드에 **도달 안 함** → 서버 로그 무흔적.
- 설계검토 가설(변환기 예외 아님, 앞단 인프라 원인) 정확히 일치. "특정 문서"만 실패한 이유(그 문서만 대용량) 설명됨.
- nginx 제한 = 100m 실측(명령 ⑥). 소스: `docker/nginx.conf:6`, `docker/nginx.dev.conf:27` **두 곳 모두** `client_max_body_size 100m;`.

**결정(사용자): 대용량 업로드 지원 필요 → 제한 상향.**

**반영 경로 (리포 조사로 확정):**
- nginx 제한은 `docker/Dockerfile.nginx:7` 이 `docker/nginx.conf` 를 이미지에 **COPY(구움)** → 상향하려면 **nginx 이미지 재빌드 + tar 재배포** 필요(바인드마운트 아님). 프론트 자산도 이 이미지에 구워짐 → B1/B2 프론트 변경도 동일 재빌드 대상.
- 배포 방식 = **tar 이미지** (CLAUDE.md/메모리, `deploy.sh`).

**⚠️ 구체적 다운스트림 위험 (코드 근거):**
- `upload.py:340 contents = await file.read()` — **크기 체크(341) 전에 파일 전체를 메모리로 읽음** + temp 기록(359). 277MB 통째 RAM 적재.
- 리포 `docker-compose.yml` 백엔드 서비스에 **메모리 제한 없음** → VM **호스트 RAM 에 의존**. docx 변환(python-docx)은 이미지 많은 문서에서 메모리 수배 증가 가능. ⇒ 제한만 올리면 OOM 위험.
- **VM 호스트 RAM ≈ 24GB (사용자 확인).** 단일 277MB docx 처리(적재 277MB + 변환 수배)는 24GB 대비 여유 있음. ⚠️ 단 (a) VM 은 ~7개 컨테이너 공유(csrm-*, webreader-tts, sdp-* 등) → 순간 available 은 24GB 보다 작음, (b) 277MB docx 변환 메모리 실측 없음(추정), (c) 동시 대용량 업로드 시 위험. ⇒ **"방어적 구현하면 지원 가능" 수준**(무제한 500MB 개방은 신중).

**처방(집에서, Phase 1 세트, 전부 이미지 재빌드+tar):**
1. `docker/nginx.conf` + `docker/nginx.dev.conf` `client_max_body_size` 상향 (상한 협의).
2. 업로드를 **청크 스트리밍으로** 개선(277MB 를 RAM 통째 적재 회피) — `await file.read()` → 스트리밍 기록.
3. B1/B2 — 초과·비-JSON 응답 시 "파일이 너무 큼(최대 NNNmb)" 안내(`Unexpected token '<'` 소멸) + 클라이언트 사전 크기 체크.
- 참고: 백엔드 자체 상한 `MAX_FILE_SIZE=500MB`(`upload.py:33`, 최초 커밋부터) — nginx 상향 시 이 값과 정합 맞추기.

## A3 — /api/reindex 소요·실패 지점
- A2(레거시 `EMBEDDING_BACKEND=local` → CPU 임베딩)로 "수십 분 후 실패" 근본 규명 완료. 별도 재빌드 로그 캡처는 생략 가능(원한다면 사후 확인).

## A4 — OS 직접삭제 고아 항목 수
- **보류(생략).** 설계검토(v1.1)에서 `scan_html_files` 파일시스템 스캔 재구성으로 검색 인덱스 고아는 전체 재빌드 시 자동 배제·자가치유됨이 확인되어 정량화 가치 낮음. Phase 3 은 이미 빈 폴더 정리(D4)로 축소됨. 필요 시 사후 `data/search-index.json` url 대조로 산출 가능.

## A5 — "항목 추가 불가" 재현 + 401 여부
- **보류(현장 재현 어려움).** 30분 세션 TTL 만료 → 401 권한강등 가설. 버그 재현 시 브라우저 F12 → Network 에서 **401 요청 존재 여부**만 캡처하면 확정. 다음 발생 시 기회 포착.

---

## 결론 — Phase 0 게이트 통과
두 헤드라인 이슈(**A1 업로드·A2 인덱싱**) 원인 확정 + 안전한 처방 확보. Phase 1(업로드)·Phase 2(성능=GPU 전환) 착수 가능. A4·A5 는 저가치/재현난이로 보류.

**우선순위:**
1. **Phase 2 GPU 전환 (최우선, 저위험·고효과) — 회사 VM 현장 `.env` 교정. 코드 아님.**
   - `docker-compose.yml:19` 이 `${EMBEDDING_BACKEND:-}` 로 `.env` 를 읽음 → VM `.env` 의 `EMBEDDING_BACKEND=local` 이 원인.
   - 교정: VM `.env` 에서 `EMBEDDING_BACKEND=local` 제거(또는 주석) + `EMBEDDING_BACKEND_INDEX=ollama` + `EMBEDDING_BACKEND_RUNTIME=local` 추가 (`.env.example:46-47` 권장값).
   - 반영: `docker compose up -d`(env 는 컨테이너 **생성 시** 주입 → `restart` 아님, **recreate 필요**). 검증: 관리자 재빌드 실행 → Ollama 서버 `nvidia-smi` VRAM 상승 + 소요 급감 확인.
   - 관측 UI(C1)·Ollama 실패 명확화(C2)·CPU 폴백 정책(C4)은 별도 코드작업(집).
2. **Phase 1 업로드 (집 코드작업)** — `docker/nginx.conf`+`nginx.dev.conf` `client_max_body_size` 상향 + 백엔드 대용량 감당 검증(OOM/타임아웃) + B1/B2 친절 오류.
