# Plan-68 — Explorer 안정화·성능 복원·관리자 올클린 (진단→회귀복구→성능→정합→초기화→UX→표준화)

> 작성일: 2026-07-02 (v1) / 2026-07-02 갱신 (v1.1 — design-reviewer 검토 반영: 업로드500 기전·고아 가설 정정, Phase 2↔3 재배분)
> 대상 시스템: Explorer (`index.html` + `backend/api/` + `backend/services/` + `js/admin-settings.js` + `js/tree-menu.js` + 인덱스 빌더)
> 변경 범위: 업로드 예외 처리 · 벡터 인덱싱 성능/관측 · 인덱스-파일시스템 정합(고아 정리) · 관리자 올클린 초기화 신설 · 메뉴 알림 UX(토스트) · 업계표준 비교
> 상태: ⬜ draft (협의 대기) — **Phase 0 진단으로 원인 확정 전 Phase 1+ 착수 금지**
> 선행 인지: Plan-40(임베딩 백엔드 분리), Plan-67(GUI 삭제 cascade) — 본 계획은 그 **사각지대(OS 직접삭제 고아·관측성·회귀)** 를 메운다

---

## 진행 현황 요약

| Phase | 내용 | 예상 공수 | 상태 |
|-------|------|---------|------|
| Phase 0 | **진단·증거수집** — 원인 확정 (해법 착수 전제) | 0.5일 | ⬜ |
| Phase 1 | 회귀복구 — 업로드 예외 → 구조화 JSON 오류 + 인덱싱 실패 원인 제거 | 1일 | ⬜ |
| Phase 2 | 성능복원 — **벡터 600초 타임아웃 근본(CPU-Ollama 지연)** + 백엔드/GPU 관측 UI + Ollama 실패 명확화 + 증분화 | 2일 | ⬜ |
| Phase 3 | 정합성 — 빈 폴더 정리 + 벡터메타 관측 (⚠️ 고아 재빌드실패 가설 반증 → **축소**) | 0.5일 | ⬜ |
| Phase 4 | 관리자 올클린 초기화 (가이드 보존 + 2단 확인) | 1일 | ⬜ |
| Phase 5 | UX — 메뉴 알림 토스트 전환 + "항목 추가 불가" 버그 | 1일 | ⬜ |
| Phase 6 | 업계표준 비교·추가 식별 개선안 (문서) | 0.5일 | ⬜ |
| **합계** | — | **~6.5일** | **0/7** |

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
- [ ] A1. 실패하는 "특정 문서" 업로드 재현 + **서버 로그에서 실제 예외 스택 캡처** (어느 converter/preprocess 단계, 어느 예외)
- [ ] A2. 현장 `.env`/`data/settings.json` 의 `EMBEDDING_BACKEND_INDEX/_RUNTIME` **실측값** + Ollama `/api/tags` 도달성 + `nvidia-smi`/`/api/ps` 로 임베딩이 **GPU에서 도는지** 확인
- [ ] A3. `/api/reindex` 가 전체 재빌드임을 재확인 + 실제 소요/실패 지점(로그) — 벡터 타임아웃(600s)인지 예외인지
- [ ] A4. `search-index.json` vs `contents/` 실제 파일 **대조 → 고아 항목 수** 산출 (OS 직접삭제 잔재 정량화)
- [ ] A5. 메뉴 저장 시 "재시작 후 적용" 경고 **재현 경로 특정** (메뉴 vs 설정 혼선인지 실제 버그인지) + "항목 추가 불가" 재현 순서 기록
- [ ] A6. Phase 0 결과를 `reports/` 에 요약 → Phase 1~ 범위 확정

### B. Phase 1 — 회귀복구
- [ ] B1. `run_converter()` 일반 `Exception` catch → 로깅 + 구조화 오류 반환 (프론트가 JSON으로 파싱 가능한 형태, HTML 500 제거)
- [ ] B2. 업로드 프론트: 오류 응답을 사용자 메시지로 표시(어느 문서·왜 실패) — `Unexpected token` 소멸 확인
- [ ] B3. (A1 결과) 실패 문서의 근본 변환 예외가 **회귀**면 원인 커밋 역추적 후 수정, **문서 고유 결함**이면 방어적 처리

### C. Phase 2 — 성능복원·관측
- [ ] C1. 관리자 화면에 **인덱싱 상태 카드**: index/runtime 백엔드, Ollama 도달성, 마지막 재빌드 소요·섹션수. **GPU 여부 소스 주의**: index=ollama 일 때 GPU 사용은 **Ollama `/api/ps`** 로만 확인 가능(`embedding_client._cuda_available()` 는 로컬 torch 프로세스만 반영 → 오지정 금지)
- [ ] C2. Ollama 실패 시 재인덱싱 오류를 **원인 명확화**(연결 실패/타임아웃/모델 미로드 구분) — 조용한 실패 금지
- [ ] C3. (검토) 관리자 "인덱싱" 버튼을 **증분 우선**으로: 전체 재빌드는 "정합성 재구축" 안전망으로 분리 라벨링
- [ ] C4. (선택) CPU 폴백 정책 결정 — 자동 폴백 vs 명시적 실패. **개발책임자 결정 필요** (Notes)

### D. Phase 3 — 정합성 (⚠️ 설계검토로 축소 — 고아 재빌드 실패 가설 반증됨)
- [ ] ~~D1. 빌드 스크립트 원본 부재 항목 스킵/제거~~ — **취소**: `scan_html_files` 가 파일시스템 스캔 재구성이라 검색 인덱스엔 불필요 (Context #4 참조)
- [ ] D2. (경량화) `vector-index_meta` 잔재 점검 — 증분만 돈 벡터 메타와 `contents/` 대조해 고아 유무만 리포트 (정리는 전체 재빌드로 자가치유되므로 선택)
- [ ] D3. `index_status` 에 파일 존재/고아 수 반영 (mtime만 비교 → 정합 상태 노출) — 관측 개선
- [ ] D4. `_move_to_trash` 후 **빈 부모 폴더 정리**(시스템 폴더 제외) — 삭제 후 폴더 잔존 해소 **(Phase 3 핵심 유효 항목)**

### E. Phase 4 — 관리자 올클린 초기화
- [ ] E1. 보존 대상 확정: `contents/home.html` + `contents/guide/` + `menu.py` `SYSTEM_LABELS`(가이드 카테고리). 삭제 대상: 그 외 `contents/*` + `search-index.json` + `vector-index*` + `menu.json` 사용자 항목 + 부수 정리(BM25 캐시·conversation 세션·`backups/`). ⚠️ **`analytics.db`/`auth.db` 는 파일 이동 금지** — 서버가 연 SQLite 는 Windows 락·손상 위험 → 지우려면 **테이블 TRUNCATE(SQL)**. 기본 방침 = **통계·계정 보존**(협의)
- [ ] E2. 백엔드 올클린 엔드포인트(`require_admin`) — 삭제 대신 **휴지통 이동**(복구여지) + 인덱스 재생성(가이드만) + 메뉴를 시스템 항목만으로 리셋
- [ ] E3. 프론트 관리자 버튼 + **2단 확인**(경고 모달 + 확인 문구 타이핑) + 완료 토스트
- [ ] E4. 실행 후 Explorer가 가이드만 남고 정상 동작(검색/트리/RAG) 확인

### F. Phase 5 — 메뉴 알림 UX + 버그
- [ ] F1. 메뉴 저장 알림 상단 배너 → `showToast(...)` 하단 토스트 전환(저장완료=success, 경고=warning) — `admin-settings.js:1264` 등
- [ ] F2. (A5 결과) 메뉴에서 "재시작 후 적용" 경고가 뜨는 게 버그면 제거/정정 (메뉴는 런타임 반영)
- [ ] F3. "항목 추가 불가" — 저장 후 스냅샷 재동기화(dirty 꼬임 해소). ⚠️ `POST /api/menu` 는 `{success:true}` 만 반환(`menu.py:151`, 재조립 트리 미반환) → **응답 기반 재동기화 불가**. **저장 성공 시 `loadMenuData` 재조회**로 `_menuEditorOriginal` 갱신하거나, 엔드포인트가 full menu 를 반환하도록 확장
- [ ] F4. 설정 저장 알림도 토스트 정합(선택) — 스크롤 중 안 보이는 문제 해소

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
- 2026-07-02 — plan 생성. 사전 조사 3건(인덱싱/업로드·삭제/관리자·메뉴·토스트) 완료, 원인 가설 코드근거까지 확보. Phase 0 진단 게이트 설정.
- 2026-07-02 (v1.1) — **design-reviewer 검토 반영.** 두 "확정 사실" 정정: ①업로드는 StreamingResponse라 converter 예외가 전체 HTML 500을 못 만듦 → 진짜 원인은 스트리밍 이전 구간/프론트 인프라, **A1에서 실제 응답 본문 캡처 필수** ②`scan_html_files` 파일시스템 스캔 재구성이라 **OS 삭제 고아는 재빌드를 죽이지 않음(가설 반증)** → Phase 3 축소. "수십분 실패"=**벡터 600초 타임아웃(CPU-Ollama 지연)** 로 재귀속 → Phase 2 확대. 부수 정정: analytics/auth.db는 TRUNCATE(파일이동 금지), GPU관측=Ollama /api/ps, F3=loadMenuData 재조회, "604초"→600초.
