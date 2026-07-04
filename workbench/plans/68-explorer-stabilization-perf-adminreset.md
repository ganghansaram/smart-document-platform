# Plan-68 — Explorer 안정화·성능 복원·관리자 올클린 (진단→회귀복구→성능→정합→초기화→UX→표준화)

> 작성일: 2026-07-02 (v1) / 2026-07-02 갱신 (v1.1 — design-reviewer 검토 반영: 업로드500 기전·고아 가설 정정, Phase 2↔3 재배분)
> 대상 시스템: Explorer (`index.html` + `backend/api/` + `backend/services/` + `js/admin-settings.js` + `js/tree-menu.js` + 인덱스 빌더)
> 변경 범위: 업로드 예외 처리 · 벡터 인덱싱 성능/관측 · 인덱스-파일시스템 정합(고아 정리) · 관리자 올클린 초기화 신설 · 메뉴 알림 UX(토스트) · 업계표준 비교
> 상태: 🟡 진행 중 — P0 진단 완료 · P1 코드완료(배포대기) · P2 코드완료(배포대기) · **P4 완료(2026-07-04 E2E)** · P5 부분(F1·F2·F4) / F3·P3·P6 미착수
> 선행 인지: Plan-40(임베딩 백엔드 분리), Plan-67(GUI 삭제 cascade) — 본 계획은 그 **사각지대(OS 직접삭제 고아·관측성·회귀)** 를 메운다

---

## 진행 현황 요약

| Phase | 내용 | 예상 공수 | 상태 |
|-------|------|---------|------|
| Phase 0 | **진단·증거수집** — 원인 확정 (해법 착수 전제) | 0.5일 | 🟡 A1·A2·A3·A6 완료(회사 VM 현장, `reports/plan-68-phase0-diagnosis-2026-07-02.md`) / A4·A5 보류 |
| Phase 1 | 업로드 대용량 지원 — nginx 500m·청크 스트리밍·413 친절오류 (A1 근본원인=크기초과에 맞춰 재구성) | 1일 | 🟡 코드·정적검증·코드리뷰 통과 + **Docker 스모크(nginx 120MB통과/550MB 413) ✅** / 인증 e2e·tar 배포 대기 |
| Phase 2 | 성능복원 — **벡터 600초 타임아웃 근본(CPU-Ollama 지연)** + 백엔드/GPU 관측 UI + Ollama 실패 명확화 + 증분화 | 2일 | 🟡 코드 완료(C1·C2·C3·C4, 집 Docker 검증) / 배포=.env+이미지 재빌드 대기 |
| Phase 3 | 정합성 — 빈 폴더 정리 + 벡터메타 관측 (⚠️ 고아 재빌드실패 가설 반증 → **축소**) | 0.5일 | ⬜ |
| Phase 4 | 관리자 올클린 초기화 (가이드 보존 + 2단 확인) | 1일 | ✅ 완료(집 Docker E2E 검증) / 배포=프론트 이미지 재빌드 대기 |
| Phase 5 | UX — 메뉴 알림 토스트 전환 + "항목 추가 불가" 버그 | 1일 | 🟡 F1·F2·F4 완료·검증·커밋(`f1e1ada`) / F3 미해결 |
| Phase 6 | 업계표준 비교·추가 식별 개선안 (문서) | 0.5일 | ⬜ |
| **합계** | — | **~6.5일** | **P0 진단 완료 · P1 코드완료(배포대기) · P5 부분 / 나머지 P2·P3·P4·P6 대기** |

> 상태 표기: ⬜ 대기 · 🟡 진행 중 · ✅ 완료 · ❌ 보류/롤백
> Phase 우선순위 (⚠️ 설계검토 후 조정) = **2(성능=실패 근본, 벡터 600초 타임아웃)** > 1(회귀=업로드, A1 응답본문 확정 선행) > 5(UX) > 4(초기화) > 3(정합=경량) > 6(문서). 협의 후 조정.

---

## Context

사용자가 회사 리눅스 VM 운영 중 식별한 Explorer 이상 6건 + 개선요구 1건. 조사 3건(인덱싱 파이프라인 / 업로드·삭제 정합 / 관리자·메뉴·토스트)으로 **원인 가설을 코드 근거까지 좁혔다.** 다만 일부는 서버 로그·현장 설정값이 있어야 확정되므로 **Phase 0(진단)을 별도로 두고, 그 결과 위에 해법을 쌓는다.**

### 조사로 확정된 사실 (코드 근거)

1. **업로드 실패 (회귀)** — `run_converter()` 가 `ImportError` 만 catch(`upload.py:149`)하는 건 사실이나, ⚠️ **설계검토 정정**: 업로드는 `StreamingResponse` 라 `run_converter` **이전에** 이미 200 + 첫 NDJSON 라인을 방출한다(`upload.py:366→368`). 따라서 converter 내부 예외는 **스트림 중간 절단**일 뿐, 응답 **전체가 HTML** 인 500(→ `Unexpected token '<'`)을 만들지 못한다. `Unexpected token '<'`(전체 HTML 응답)의 진짜 원인은 **스트리밍 이전 구간**(파일 읽기·백업·temp 저장) 또는 **프론트 인프라 오류 페이지**(Tomcat/Nginx의 413/502 등)일 가능성이 크다. ⇒ **A1 에서 실제 실패 응답 본문(status·헤더·body)을 반드시 캡처**해야 원인 확정. `run_converter` general catch(B1)만으론 증상이 안 사라질 수 있음.

2. **인덱싱 "버튼" = 전체 재빌드** — `/api/reindex`(`upload.py:441`) → 검색 재빌드(600초) → 벡터 재빌드(600초) **순차**(`upload.py:184,251`) → `build-vector-index.py` 서브프로세스. 업로드 경로는 증분(`vector_search.append_documents`)이라 빠르지만, 관리자 버튼은 매번 전량 재계산. **순차 600+600 = 최대 ~20분** → 사용자의 "수십 분 후 실패" 와 정합(고아 때문이 아니라 **벡터 임베딩 600초 타임아웃**).

3. **임베딩 백엔드(Plan-40)** — `embedding_client._resolve_backend()`: index→**ollama(GPU)**, runtime→local 이 코드 기본값. **즉 "GPU 옵션"은 코드에 살아있다.** 그러나 **(a) Ollama 실패 시 CPU 폴백 없음**(`raise_for_status`, 그냥 에러) **(b) 실제 어느 백엔드가/GPU가 쓰이는지 볼 관측 수단이 없음** — 이것이 사용자의 "GPU 옵션이 안 보여"의 정체. Ollama HTTP 120초/호출, 배치 256.

4. **OS 직접삭제 고아** — ⚠️ **설계검토 대폭 정정**: `build-search-index.py:369` `scan_html_files()` 는 `CONTENTS_DIR.rglob('*.html')` 로 **파일시스템을 스캔해 search-index 를 전량 재구성**한다. 즉 OS 로 지운 파일은 **다음 검색 재빌드에서 자동 배제**되고, 벡터 재빌드(`build-vector-index.py:110`)는 그 갱신된 search-index 를 쓰므로 **고아는 벡터 임베딩에 도달하지 못하며 전체 재빌드를 죽이지 않는다.** ⇒ 앞선 "고아가 재빌드를 죽인다" 가설은 `/api/reindex`(검색→벡터 순) 경로에서 **성립하지 않음.** 실제 잔재는 **전체 재빌드 없이 증분만 돈 `vector-index_meta`** 에 국한되며, 전량 재빌드로 자가치유된다. `index_status`(`upload.py:572`)가 mtime만 비교해 고아 상태를 못 보는 것은 사실(관측 개선 여지). **⇒ Phase 3 비중 대폭 축소** — 삭제 후 빈 폴더 정리(D4)와 관측(D3)만 유효, D1(빌드 스크립트 존재검증)은 **검색 인덱스엔 불필요**.

5. **삭제 후 빈 폴더 잔존** — `document_delete_service._move_to_trash()` 가 파일+`<stem>_images/` 만 휴지통 이동, **부모 폴더는 남김**. 준(準)의도(파일만 이동) + 빈 폴더 정리 로직 부재.

6. **관리자 올클린 부재** — 현재 `/api/settings/reset`(설정만 초기화)만 존재. **콘텐츠 일괄 초기화 없음.** 플랫폼 가이드 = `contents/home.html` + `contents/guide/` + `menu.py` `SYSTEM_LABELS`(자동 보존). 올클린 = 그 외 콘텐츠 + `search-index.json` + `vector-index*` + `analytics.db` 정리.

7. **메뉴 알림 UX** — 메뉴 저장(`POST /api/menu`)은 **런타임 반영이라 원래 "재시작 필요" 경고가 없어야** 함(`admin-settings.js:1264` `_showNotice('ok', ...)` = **상단 배너**). 사용자가 본 "서버 재시작 후 적용됩니다: ~~" 는 **설정 저장 경로의 경고와 얽혔거나 별도 버그** → 재현·규명 대상. "몇 번 후 항목 추가 불가" = `_menuEditorOriginal` 스냅샷 ↔ 서버 `menu.json` 상태 불일치(동시편집/미새로고침) 의심. 토스트(`showToast(msg, type, duration)`, 하단중앙)는 이미 존재.

방향성: **특화 없이 업계 표준.** 예외는 구조화 오류로, 인덱스는 파일시스템을 SSOT로 두고 고아를 정리, 관측성을 노출, 위험작업은 2단 확인.

---

## Scope

### 포함
- **Phase 0** 진단: 업로드 예외 로그 캡처, 현재 `EMBEDDING_*` 실측값·Ollama 도달성·GPU 사용여부, 인덱싱 버튼 전체/증분 재확인, 고아 인덱스 정합 점검, 메뉴 재시작경고 재현
- **Phase 1** 업로드 실패 응답 본문 확정(A1) 후 원인 제거 — `run_converter` 일반 예외 catch → 구조화 오류 + 프론트 메시지. 스트리밍 이전 구간/인프라 원인이면 해당 지점 수정
- **Phase 2** 벡터 600초 타임아웃 근본(CPU-Ollama 지연) 해소 + 관리자 화면에 **인덱싱 백엔드·상태 노출**(index/runtime 백엔드, Ollama 도달성·GPU=/api/ps, 마지막 재빌드 소요·건수) + Ollama 실패 명확화 + 증분 재빌드 우선 전략
- **Phase 3** (⚠️ 축소) 삭제 후 **빈 폴더 정리** + `vector-index_meta` 잔재 관측(정리는 전체 재빌드 자가치유) + `index_status` 정합상태 노출
- **Phase 4** 관리자 **올클린 초기화** — 가이드/시스템 보존, 콘텐츠+검색/벡터 인덱스 비우기(analytics/auth.db는 보존·필요시 TRUNCATE), **2단 확인**(문구 입력 등) + 휴지통 이동(복구여지)
- **Phase 5** 메뉴 저장 알림 **상단 배너 → 하단 토스트** 전환(저장완료·경고) + "항목 추가 불가" 버그 수정(스냅샷/새로고침 정합)
- **Phase 6** Explorer 인덱싱·정합·관측을 업계 표준과 비교한 **개선안 문서** + 추가 식별 이슈 정리

### 의도적 제외 (OUT)
- **RAG 검색 품질/알고리즘 변경** — 본 계획은 안정성·성능·정합·운영. 검색 품질은 별개
- **Ollama 동시성 게이트웨이(L2)** — Plan-44 트리거 영역, 무관
- **휴지통 비우기/복구 UI** — Plan-67과 동일하게 폴더 이동까지만 (복구는 수동)
- **재시작 폴리시 핫리로드 실제 구현** — Plan-67 Phase 5 audit 연장선, 별 plan
- **Translator/Notebook 인덱싱 경로** — 별 워크스페이스, 무관

---

## Tasks

### A. Phase 0 — 진단·증거수집 (해법 착수 전제)
- [x] A1. 업로드 실패 원인 확정 → **실패 문서 277MB > nginx `client_max_body_size 100m` → 413 HTML → `Unexpected token '<'`**. 요청이 백엔드 미도달(서버 로그 무흔적). nginx 100m 은 `docker/Dockerfile.nginx:7` 로 이미지에 구움(2026-04-07, Plan-27). 백엔드 상한 500MB(`upload.py:33`)는 무관.
- [x] A2. **레거시 `EMBEDDING_BACKEND=local`(VM `docker-compose.yml:14` 기본값) → 인덱싱이 GPU 아닌 컨테이너 CPU**. Ollama 서버(`xxx.179`) 도달·`bge-m3`·`/api/embed` dim1024 정상 확인. VM 코드는 per-purpose 지원(True) → 이미지 재빌드 없이 compose 한 줄(`EMBEDDING_BACKEND_INDEX=ollama`)로 해결 가능(staged, `up -d` 보류).
- [x] A3. A2 로 "수십 분 후 실패"=**CPU 임베딩 전량 재빌드 600초 타임아웃** 규명(메모리 358섹션 CPU 575.7s). 업로드는 증분(`_run_vector_incremental`)이라 빨랐음. 별도 재빌드 로그 캡처는 생략.
- [ ] A4. **보류** — 설계검토(`scan_html_files` 파일시스템 재구성)로 검색 고아 자가치유 확인, 정량화 저가치.
- [ ] A5. **보류(현장 재현 어려움)** — "항목 추가 불가" = 세션 30분 TTL 만료 → 401 강등 가설. 다음 회사 재현 시 F12 Network 401 여부 캡처.
- [x] A6. Phase 0 결과 `reports/plan-68-phase0-diagnosis-2026-07-02.md` 작성 → Phase 1(업로드)·Phase 2(GPU) 범위 확정.

### B. Phase 1 — 업로드 대용량 지원 (A1 근본원인=nginx 100m 초과 413 에 맞춰 재구성)
> Phase 0 확정: `Unexpected token '<'` = 변환기 예외 아님 = nginx 413 HTML. 원안 B1/B3(변환기 예외 경로)은 본 버그와 무관 → 미적용.
- [x] B0. nginx `client_max_body_size` **100m → 500m** (`docker/nginx.conf`·`nginx.dev.conf`). 백엔드 `MAX_FILE_SIZE`·프론트 `UPLOAD_CONFIG.maxFileSize` 와 500MB 정합.
- [x] B0b. 백엔드 업로드 수신 **전체 메모리 적재 → 4MB 청크 스트리밍**(`upload.py`) + 크기 가드 + temp 누수 방지(백업/mkdir 실패 포함 단일 try).
- [x] B2. 프론트 **413/비-JSON 응답 방어** + 업로드 전 크기 사전 체크 (`tree-menu.js`) — `Unexpected token '<'` → "파일이 너무 큽니다(최대 500MB)".
- [~] B1/B3. **N/A** — 근본원인이 크기초과라 변환기 예외 경로 수정 불필요. (필요 시 후속 방어적 catch 는 별건)
- [~] B-deploy. Docker 스모크(로컬 dev) **일부 완료** — nginx 500m 기능검증(120MB통과·550MB 413)·backend healthy. 남음: 인증 e2e(실 docx) + **nginx·backend 이미지 재빌드 → tar 배포**(회사).

### C. Phase 2 — 성능복원·관측
- [x] C1. 관리자 대시보드에 **인덱싱 상태 카드**: index/runtime 백엔드, Ollama 도달성·GPU, 마지막 재빌드 소요·건수. GPU 는 Ollama `/api/ps`(`get_ollama_ps()`, `size_vram>0`)로만 판정 — `_cuda_available()` 미사용. 구현: `embedding_client.get_backend_info/get_ollama_ps` + `upload.get_indexing_status`+`index-meta.json` + `analytics.py` payload + `analytics.js` 카드. 집 Docker 실 Ollama 로 GPU 감지(on_gpu:true)·카드 렌더·콘솔0 검증.
- [x] C2. Ollama 실패 원인 **명확화** — `EmbeddingBackendError(reason)` 연결/타임아웃/모델/HTTP 구분. 서브프로세스 stderr 는 `_extract_embedding_error()` 로 원인 한 줄 추출. 조용한 실패 제거.
- [x] C3. (라벨) 재빌드 버튼 툴팁 정직화 — "전체 재구축=정합성 안전망 · 평소 업로드·삭제는 자동 증분". 별도 증분 버튼 신설은 후속(범위).
- [x] C4. CPU 폴백 정책 = **명시적 실패**(자동 CPU 폴백 반대 — 600초 타임아웃 조용한 재발 방지). 타임아웃 메시지에 "index=ollama(GPU) 확인 권장" 안내.

### D. Phase 3 — 정합성 (⚠️ 설계검토로 축소 — 고아 재빌드 실패 가설 반증됨)
- [ ] ~~D1. 빌드 스크립트 원본 부재 항목 스킵/제거~~ — **취소**: `scan_html_files` 가 파일시스템 스캔 재구성이라 검색 인덱스엔 불필요 (Context #4 참조)
- [ ] D2. (경량화) `vector-index_meta` 잔재 점검 — 증분만 돈 벡터 메타와 `contents/` 대조해 고아 유무만 리포트 (정리는 전체 재빌드로 자가치유되므로 선택)
- [ ] D3. `index_status` 에 파일 존재/고아 수 반영 (mtime만 비교 → 정합 상태 노출) — 관측 개선
- [ ] D4. `_move_to_trash` 후 **빈 부모 폴더 정리**(시스템 폴더 제외) — 삭제 후 폴더 잔존 해소 **(Phase 3 핵심 유효 항목)**

### E. Phase 4 — 관리자 올클린 초기화 (✅ 완료 2026-07-04)
- [x] E1. 보존 경계 확정 = **allowlist** `_ALLCLEAN_PRESERVE`(home.html·about.html·guide·banner_images·authored). 사용자 결정으로 **Explorer 사용자 업로드/작성 문서만** 삭제, 계정·통계·설정·backups 무접촉. ⚠️ 초기 "home+guide만" 에서 조사로 about·banner(화면 데코) 보존 추가. 판별 근거 `reports/plan-68-phase4-scope-2026-07-04.md`. (analytics.db/auth.db TRUNCATE 는 **보존 결정으로 불필요** — 무접촉이 가장 안전)
- [x] E2. `POST /api/explorer/all-clean`(require_admin, NDJSON) — `document_delete_service.all_clean_explorer()`(휴지통 이동) + `menu.reset_menu_to_system()` + 검색·벡터 재빌드. 기존 `_move_to_trash`·reindex 헬퍼 재사용.
- [x] E3. `admin-settings.js` 콘텐츠 탭 위험 섹션 + 2단 확인 모달("초기화" 타이핑 게이트) + 스트리밍 진행 + 완료 토스트.
- [x] E4. 실행 E2E 검증: contents 9→5(보존만)·삭제4→휴지통·메뉴10→3·인덱스360→124·Explorer 가이드만·About 200·삭제 404·계정/통계 무접촉·RAG 정상. 피드백 `reports/plan-68-phase4-feedback-2026-07-04.md`.

### F. Phase 5 — 메뉴 알림 UX + 버그
- [x] F1. 메뉴 탭 알림 전부 하단 토스트로 전환(저장완료·실패·삭제/제거·"저장 안 됨" 경고) — `admin-settings.js`. ✅ 실브라우저 검증(하단 success 토스트, 상단 배너 미표시)
- [x] F2. (A5 결과) **메뉴 경로엔 재시작 경고 코드 없음** — 사용자가 본 경고는 이전 설정 저장의 `_pendingRestartItems` 배너가 재렌더마다 복원돼 지속 노출된 것(메뉴 버그 아님). 실측 확정
- [ ] F3. "항목 추가 불가" — ⚠️ **미해결**. 실브라우저에서 `_menuAddTopLevel` 정상 동작 확인(추가 함수 자체 이상 없음). 유력 원인 **세션 만료(30분 TTL)로 권한 강등** 추정 → 회사 재현 시점의 콘솔/네트워크(401 여부) 캡처 후 확정
- [x] F4. 설정 저장도 토스트로 — 성공=success 토스트, 재시작-필요=warning 토스트(즉시 가시성) + 상단 배너(무엇을 재시작할지 지속 리마인더) 병행. ✅ 실브라우저 검증

### G. Phase 6 — 업계표준 비교·추가 식별
- [ ] G1. Explorer 인덱싱/정합/관측을 업계 표준(증분 인덱싱, 파일시스템=SSOT 재조정, watch/reconcile, 관측성)과 비교 표
- [ ] G2. 조사 중 추가 식별된 이슈 정리(예: 다중 워커 시 캐시 정합, 재빌드 락 경쟁, 대용량 배치 타임아웃 튜닝)
- [ ] G3. 후속 plan 후보 도출

---

## Acceptance

### 필수
- 실패하던 특정 문서 업로드가 **명확한 오류 메시지**로 처리(`Unexpected token '<'` 소멸) — 성공 복구 또는 근거 있는 실패 안내
- 벡터 전체 재빌드가 **600초 타임아웃으로 실패하지 않음** (성능 복원 = Phase 2 핵심) — GPU 임베딩 정상 or 소요 단축
- 관리자가 **현재 인덱싱 백엔드·상태**를 화면에서 확인 가능
- 관리자 **올클린 초기화**로 가이드만 남기고 안전하게 비우기 가능(2단 확인, 휴지통 복구여지)
- 메뉴 저장 알림이 **하단 토스트**로 표시 + "항목 추가 불가" 재현 불가
- 회귀 0 — 정상 문서 업로드/검색/RAG/트리/편집 무손상

### 선호
- 관리자 인덱싱 버튼 증분 우선화로 체감 속도 개선
- 삭제 후 빈 폴더 자동 정리
- 업계표준 비교 문서로 후속 로드맵 명확화

---

## 미해결 / 협의 필요
- **CPU 폴백 정책** (C4): Ollama 불가 시 CPU local 자동 폴백(느리지만 성공) vs 명시적 실패(빠른 인지). 개발책임자 결정 필요
- **올클린 삭제 범위** (E1): `analytics.db`(대시보드 통계)·업로드 이력·사용자 계정(`auth.db`)까지 지울지 — 기본은 **콘텐츠+인덱스만**, 계정/설정 보존 권장
- **"수십 분 후 실패" 실제 원인** — 설계검토 결과 **고아 가설 반증**, 유력 원인은 **CPU-Ollama 임베딩 지연으로 벡터 600초 타임아웃**(MEMORY: 358섹션 CPU 575초, 문서 증가 시 초과). A2(Ollama GPU 여부)/A3(재빌드 로그)로 확정. ⇒ **Phase 2(성능) 확대, Phase 3(정합) 축소** 재배분
- Phase 0 결과에 따라 Phase 순서/공수 재산정

## 산출물
- 코드: `backend/api/upload.py`, `backend/api/menu.py`, `backend/api/settings.py`(또는 신규 admin 엔드포인트), `backend/services/embedding_client.py`, `backend/services/document_delete_service.py`, `build-search-index.py`, `build-vector-index.py`, `backend/services/vector_search.py`, `js/admin-settings.js`, `js/tree-menu.js`
- 문서: `reports/plan-68-phase0-diagnosis-YYYY-MM-DD.md`(진단), `reports/plan-68-industry-standard-compare-YYYY-MM-DD.md`(Phase 6)

## Notes
- **진단 우선 원칙**: 원인 미확정 상태에서 해법 코딩 금지 — Phase 0 게이트
- Plan-40 은 이미 index=ollama 기본값을 넣었으므로 Phase 2는 **재구현이 아니라 관측성·폴백 명확화** 중심
- ⚠️ **Phase 3 축소 근거(v1.1)**: `scan_html_files` 파일시스템 스캔으로 OS 삭제 고아가 검색 재빌드에서 자동 배제 → "고아가 재빌드를 죽인다" 가설 반증. Plan-67(GUI 삭제 cascade)과의 대칭 보완이라던 애초 정당화가 약해짐. Phase 3은 **빈 폴더 정리(D4)** 위주로만 유효
- 위험작업(올클린)은 반드시 휴지통 이동 경유 — Plan-67 `data/trash/` 관례 재사용
- 폐쇄망·Vanilla·무빌드 제약 유지

## Progress Log
- 2026-07-04 — **Phase 4 완료(집 Docker, 실행 E2E).** 관리자 올클린 초기화 신설. 사용자 결정으로 범위=Explorer 사용자 업로드/작성 문서만, 계정·통계·설정·backups 무접촉. 보존경계=allowlist(조사로 about·banner 화면데코 추가, `reports/plan-68-phase4-scope-...md`). `POST /api/explorer/all-clean`(휴지통 이동+메뉴 시스템리셋+인덱스 재빌드) + admin-settings.js 위험섹션+2단확인("초기화" 타이핑). 실행검증: contents 9→5·삭제4→휴지통(복구가능)·메뉴10→3·인덱스360→124·Explorer 가이드만·About 무손상·계정/통계 보존·RAG 정상·콘솔0. 잔여=프론트 이미지 재빌드(배포). 피드백 `reports/plan-68-phase4-feedback-2026-07-04.md`.
- 2026-07-04 — **Phase 2 코드 완료(집 Docker).** 성능복원의 본질=관측성으로 규명(GPU 전환은 Phase 0 확정대로 .env 한 줄, 코드 아님). C1 인덱싱 관측 카드(백엔드/GPU=Ollama `/api/ps`/재빌드 통계) + C2 `EmbeddingBackendError` 원인 구분(연결/타임아웃/모델/HTTP) + C3 재빌드 버튼 툴팁 정직화 + C4 CPU 폴백=명시적 실패 결정. 변경 5파일(embedding_client·upload·analytics.py·analytics.js·index.html). 실 Ollama 관통 검증(GPU on_gpu:true·C2 분류·메타 왕복)·Playwright 카드 렌더·콘솔0. 자체리뷰 async 블로킹 1건 즉시 수정(`asyncio.to_thread`). **잔여=배포**: 회사 VM `.env` 교정(recreate) + 프론트 nginx 이미지 재빌드+tar(Phase 1과 함께). 피드백 `reports/plan-68-phase2-feedback-2026-07-04.md`.
- 2026-07-02 — plan 생성. 사전 조사 3건(인덱싱/업로드·삭제/관리자·메뉴·토스트) 완료, 원인 가설 코드근거까지 확보. Phase 0 진단 게이트 설정.
- 2026-07-02 — **Phase 5 부분 완료·커밋·푸시(`f1e1ada`).** F1(메뉴 탭 알림 전부 하단 토스트)·F2(재시작 경고=메뉴 버그 아님, 설정 배너 복원 현상으로 규명)·F4(설정 저장 토스트+지속 배너 병행) 구현 + 실브라우저(testbot/admin) 검증 통과. **F3(항목 추가 불가) 미해결** — 추가 함수 자체는 정상 확인, 세션만료 추정, 회사 재현 로그 대기. Phase 0·1·2·3·4·6 은 회사 VM(업로드 로그·Ollama GPU) 필요로 미착수.
- 2026-07-03 — **Phase 1 구현 완료(집, 코드).** 업로드 대용량 지원: nginx 100m→500m(2곳)·백엔드 4MB 청크 스트리밍+크기가드·프론트 413/비-JSON 친절오류+사전 크기체크. 상한 500MB(사용자 결정, nginx·백엔드·프론트 3자 정합). `/code-review` 실결함 1건(백업 실패 시 temp 누수) 수정. py_compile·정적검증·회귀 스팟체크 통과. **미검증=Docker e2e**, **배포=이미지 재빌드+tar 대기(회사).** 원안 B1/B3(변환기 예외)는 A1 근본원인(크기초과)과 무관 판명→미적용. 피드백 `reports/plan-68-phase1-feedback-2026-07-03.md`.
- 2026-07-02 — **Phase 0 진단 완료(회사 리눅스 VM 현장).** A1·A2·A3·A6 확정, A4·A5 보류. 두 헤드라인 원인 확정: **①A2 업로드 인덱싱 CPU** — 레거시 `EMBEDDING_BACKEND=local`(VM compose 기본값)이 인덱싱을 GPU 대신 컨테이너 CPU 로 강제 → 전량 재빌드 600초 타임아웃("수십 분 후 실패"). Ollama GPU 경로 정상 확인, VM 코드 per-purpose 지원 → compose 한 줄로 해결(staged, 반영 보류). **②A1 업로드 실패** — 277MB docx > nginx 100m(이미지에 구움) → 413 → `Unexpected token '<'`. 다운스트림 위험: `upload.py:340` 파일 전체 RAM 적재 + docx 변환 메모리 증가, VM RAM 24GB(방어적 구현 시 지원 가능). 열람 경로는 nginx 정적 서빙이라 무관. **다음: 집에서 Phase 1(nginx 상향+청크 스트리밍+친절오류, 이미지 재빌드+tar) / Phase 2 는 VM compose `up -d`.** 상세 `reports/plan-68-phase0-diagnosis-2026-07-02.md`.
- 2026-07-02 (v1.1) — **design-reviewer 검토 반영.** 두 "확정 사실" 정정: ①업로드는 StreamingResponse라 converter 예외가 전체 HTML 500을 못 만듦 → 진짜 원인은 스트리밍 이전 구간/프론트 인프라, **A1에서 실제 응답 본문 캡처 필수** ②`scan_html_files` 파일시스템 스캔 재구성이라 **OS 삭제 고아는 재빌드를 죽이지 않음(가설 반증)** → Phase 3 축소. "수십분 실패"=**벡터 600초 타임아웃(CPU-Ollama 지연)** 로 재귀속 → Phase 2 확대. 부수 정정: analytics/auth.db는 TRUNCATE(파일이동 금지), GPU관측=Ollama /api/ps, F3=loadMenuData 재조회, "604초"→600초.
