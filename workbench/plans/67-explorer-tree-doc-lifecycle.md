# Plan-67 — Explorer 트리·문서 생애주기 관리 개선 (삭제 cascade·인덱스 정합·detach·재시작 audit) — v1.1

> 작성일: 2026-06-30 (v1) / 2026-06-30 갱신 (v1.1 — plan-advisor 사전 검토 반영: authored 통합 삭제 + 동시성 락 + 중복노드 + 5e 격하)
> 대상 시스템: Explorer (`index.html` + `js/tree-menu.js` + `js/admin-settings.js` + `backend/api/` + `backend/services/vector_search.py`)
> 변경 범위: 삭제 코어 서비스(휴지통 이동 + 벡터/검색 인덱스 제거) + Explorer 문서 삭제 API 신설 + 메뉴 노드 cascade 삭제 + 문서 detach + admin UX(영향 미리보기 모달) + 재시작 폴리시 audit(곁가지)
> 상태: ✅ 구현·검증 완료 (7/7) — done 이관·커밋 대기

---

## 진행 현황 요약

| Phase | 내용 | 예상 공수 | 상태 |
|-------|------|---------|------|
| Phase 0 | 영향성·baseline — 현 삭제 경로 전수 추적, 인덱스 정합 baseline 캡처 | 0.5일 | ✅ |
| Phase 1 | 삭제 코어 서비스 — `remove_documents` + 휴지통 이동 + 동시 쓰기 락 + 문서종류 분기 | 2일 | ✅ |
| Phase 2 | 삭제 API(`require_admin`) + 메뉴 cascade + authored 경로 + 중복 url 처리 | 1일 | ✅ |
| Phase 3 | 문서 detach (노드 유지 + 문서만 제거) | 0.5일 | ✅ |
| Phase 4 | admin UX — 영향 미리보기 모달 + dirty-guard + 즉시 반영 + 토스트 | 1일 | ✅ |
| Phase 5 | 재시작 폴리시 audit (곁가지) — 배너 7항목만, 결론=이미 표준 | 0.5일 | ✅ |
| Phase 6 | 검증·회귀·보고서 — 단위 + 실서버 e2e + code-review 반영 + 보고서 | 1일 | ✅ |
| **합계** | — | **6.5일** | **7/7 (done 이관 대기)** |

> 상태 표기: ⬜ 대기 · 🟡 진행 중 · ✅ 완료 · ❌ 보류/롤백

---

## Context

Explorer 좌측 문서 트리·업로드는 **표시·편집·즉시반영**은 양호하나, **문서 생애주기(삭제·정합성) 관리가 비어 있다**. 운영 관점에서 사고가 나는 지점이다.

조사로 확인한 현 상태 (2026-06-30):

1. **삭제 cascade 부재 (핵심 결함)** — 관리자가 메뉴 노드를 제거하면 `js/admin-settings.js:1035` `_menuDeleteByPath()` 가 **메뉴 배열에서 노드만 빼고**, 디스크 파일·인덱스는 손대지 않는다. 코드에 `"(디스크의 파일은 삭제되지 않습니다)"` 가 명시돼 있다. 결과: `contents/` 변환 HTML·`search-index.json`·`vector-index.faiss` 항목이 **전부 고아(orphan)로 잔존** → 지운 문서가 검색·RAG 채팅에 계속 노출된다.

2. **Explorer 문서 삭제 API 자체가 없음** — 백엔드에 `/reindex`(전체 재빌드)만 있고 단건 문서 삭제 엔드포인트가 없다 (`backend/api/upload.py`). Translator 는 자체 삭제(`translator_service.py:825 delete_document`, `:270 _remove_from_search_index`)를 가지나 별개 워크스페이스다. → **그린필드**, 레거시 충돌 없음.

3. **벡터 인덱스 삭제 가능성 = 해소됨** — `vector_search.py` 의 인덱스는 `IndexFlatL2`(`:115`), 메타데이터는 위치 기반 리스트(행 N ↔ `metadata[N]`, `:69-72`·`:126-133`). FAISS `IndexFlatL2.remove_ids()` 는 **남은 행의 순서를 보존하며 압축**하므로, 같은 위치를 메타데이터에서 동일 필터링하면 정합이 유지된다. **인덱스 타입 변경·재임베딩·새 자료구조 불필요** — 기존 증분 `append_documents`(`:95`)의 대칭쌍.

4. **detach(노드 유지+문서만 제거) 부재** — 편집에서 `url` 만 null 로 비울 수 있으나 파일·인덱스는 그대로. 의도된 "문서만 떼기" 기능 없음.

5. **(곁가지) 재시작 폴리시** — 트리(`menu.json`) 수정은 이미 즉시 반영되고 재시작 배너도 안 뜬다(파일 기반, `tree-menu.js:790`). 배너는 `restart_needed` 분류 항목(Ollama URL·embedding_model·login_required·cors_origins 등) 저장 시에만 뜬다(이미 조건부). 다만 그 분류가 *정말* 재시작이 필요한지 전수 점검 여지가 있다(업계 표준 = config 핫리로드).

방향성: **특화 없이 업계 표준대로.** 삭제 정책은 **하드 삭제 + cascade + 휴지통 폴더 이동**(언링크 대신 `data/trash/` 이동 — 업로드 시 `.bak` 백업 습관 `upload.py:345` 과 일관, 복구 여지 확보). 인덱스는 **증분 추가 + 증분 삭제 + 전체 재빌드(안전망)** 교과서 3단 구성으로 완성한다.

### plan-advisor 사전 검토 반영 (2026-06-30, v1.1)
4대 기술 전제(벡터 `remove_ids` 순서보존·메타 정합·삭제 API 부재·cascade 부재)는 코드로 **전부 검증됨** — 토대 견고. 추가 반영 3건:
- **(Critical) authored 저작 문서 통합** — `contents/authored/*.md`(Plan-60)는 `menu.json` 에 없고 가상 "작성 문서" 폴더로 동적 삽입(`tree-menu.js:72-93`), 검색·벡터 인덱스에도 **0건**. 메뉴 cascade 가 닿지 않는다. **개발책임자 결정: 삭제는 Plan-67 이 전부 소유**(일반+authored) — 트리 일관성(보이면 다 지움) 확보. authored 삭제 경로 = **파일 휴지통 이동 + 가상폴더 새로고침(인덱스 cascade 생략)**. Plan-60 은 저작+큐레이션(개명·노출관리)만 보유, **삭제 로직 분산 방지**.
- **(Warning) 동시 쓰기 락** — `append_documents`/`remove_documents`/`_run_vector_reindex` 동시 실행 시 FAISS 인덱스·메타 파일 손상 위험. 인덱스 쓰기 구간에 직렬화 락 필요.
- **(Warning) 중복 url 노드** — 같은 url 을 가리키는 메뉴 노드가 둘 이상이면 파일·인덱스 삭제 후 나머지 노드가 깨진 링크가 됨 → 영향 미리보기에 **참조 노드 수** 노출 + 일괄 처리.
- **(비해당) 멀티워커 캐시 불일치** — 현재 **단일 워커** 배포라 `_faiss_index` 캐시 불일치 우려는 해당 없음 → 격하(아래 Notes).

## Scope

### 포함
- 삭제 코어 서비스 `remove_documents(url)` — 벡터 `remove_ids` + 검색 인덱스 항목 제거 + 메타 정합 유지 + **인덱스 쓰기 직렬화 락**
- 휴지통 폴더 이동 헬퍼 (`data/trash/<타임스탬프>/...`, 원본 경로 보존)
- Explorer 문서 삭제 API 신설 (`require_editor`) — **일반 업로드 문서 + authored 저작 문서 양쪽**
- **authored 삭제 경로** — `contents/authored/*.md` 파일 휴지통 이동 + 가상 "작성 문서" 폴더 새로고침 (인덱스 cascade 생략 — 미인덱싱이므로)
- 메뉴 노드 삭제 → cascade(영향 미리보기 → 파일 휴지통 이동 + 인덱스 제거 → 메뉴 노드 제거) + **중복 url 노드 일괄 처리**
- 문서 detach (노드 유지 + 문서/인덱스 제거 + `url` null)
- admin 메뉴 관리 UX — 삭제/detach 영향 미리보기 모달(참조 노드 수·섹션 수 표기) + 즉시 반영
- 기존 `/reindex` 전체 재빌드를 "정합성 재구축" 안전망으로 admin 에 노출(있으면 라벨만 정리)
- (곁가지) `restart_needed` 분류 audit — 핫리로드 가능 항목 목록화 (구현은 별 plan 으로 분리 가능)

### 의도적 제외 (OUT)
- **휴지통 비우기/복구 UI** — 이번엔 폴더 이동까지만. 복구는 수동 파일 되돌리기로 충분 (UI 는 후속, YAGNI)
- **authored 문서 개명·노출 큐레이션** — Plan-60 의 "admin 큐레이션/관리" 잔여로 분리. **삭제만 Plan-67 이 소유**(개명/관리 ≠ 삭제)
- **레이블경로 → id 기반 매핑 전환** — 큰 별건 사안. 인지만 하고 분리
- **재시작 폴리시 실제 핫리로드 구현** — Phase 5 는 audit·문서화까지. 구현은 audit 결과 보고 별 plan
- **Translator 삭제 경로 변경** — 별개 워크스페이스, 무관

## Tasks

### A. 삭제 코어 (Phase 1)
- [x] A1. `vector_search.py` `remove_documents(url)` — remove_ids + 메타 동일 필터, 캐시 갱신 ✅
- [x] A2. 검색 인덱스 제거 — `document_delete_service.remove_from_search_index(url)` (url 필터 + BM25 무효화) ✅
- [x] A3. 휴지통 이동 헬퍼 — `_move_to_trash` (`data/trash/<ts>/<원경로>`, shutil.move) ✅
- [x] A4. 오케스트레이터 `delete_document_by_url(url)` — 휴지통+인덱스 묶음, 파일 우선 ✅
- [x] A5. **인덱스 쓰기 직렬화 락** — `INDEX_WRITE_LOCK` (append/remove/reindex 공유) ✅
- [x] A6. **authored 분기** — `classify_kind`/`files_for_url` 경로 prefix 판별, 인덱스 생략 ✅

### B. API + cascade (Phase 2)
- [x] B1. 삭제 엔드포인트 `POST /api/document-delete` — **require_admin**(menu.json 수정 → 게이트 일치, 계획 require_editor 에서 상향), url traversal 차단 ✅
- [x] B2. `POST /api/document-impact` — 파일·검색섹션·벡터섹션·참조노드 수 산출 ✅
- [x] B3. 메뉴 노드 cascade — `menu.remove_or_detach_urls` ✅
- [x] B4. **중복 url 노드 일괄 처리** — `remove_or_detach_urls` 전 노드 순회, 깨진 링크 0 (단위·e2e 검증) ✅

### C. detach (Phase 3)
- [x] C1. `keep_nodes=true` 경로 — 파일/인덱스 제거 후 노드 유지, url 분리 ✅
- [x] C2. admin 노드 액션 "문서만 제거(⊘)" 버튼 (`_menuDetachByPath`) ✅

### D. admin UX (Phase 4)
- [x] D1. `_menuDeleteByPath()` 분기 — 가짜 경고 제거, 문서 보유 시 영향 미리보기 모달 + cascade ✅
- [x] D2. detach 액션 + 미리보기 모달 (`_openDocDeleteModal`) ✅
- [x] D3. 즉시 반영 — `_menuFetchData` 재동기화 + `loadMenuData` + 토스트, dirty-guard ✅

### E. 재시작 audit (Phase 5, 곁가지)
- [x] E1. `restart_needed` 전수 분석 — 배너 유발 7항목만(나머지 ~60개 즉시반영). 표는 보고서 ✅
- [x] E2. 결론 = 이미 업계표준(대부분 핫리로드, 소수 재시작). CORS·게이트웨이는 정당, 잔여는 보수적. 메뉴/트리 편집은 배너 무관 ✅

### F. 검증·회귀 (Phase 6)
- [x] F1. 직접 경로 검증 — 실서버 HTTP e2e: impact(2/2/1)→delete→휴지통 이동·검색/벡터/메뉴 무잔존(360·436·노드제거) ✅
- [x] F2. 메타 정합 검증 — remove_ids 순서보존 + 행↔메타 정합 단위 검증, 복원 후 ntotal==meta ✅
- [x] F3. 회귀 — sim 게이트 PASS, 벡터 인덱스 로드 정합, 실데이터 백업→복원 무손상 ✅
- [ ] F4. 보고서 작성 + done 처리(README 이동) — 진행 중

## Acceptance

### 필수
- 메뉴 노드(문서 포함) 삭제 시: 변환 HTML 이 `data/trash/` 로 **이동**(원위치에서 사라짐), 벡터 인덱스에서 해당 url 제거(`ntotal` 감소), search-index 에서 제거, 메뉴에서 노드 제거 — **4가지 동시**
- 삭제·detach 후 해당 문서가 **검색·RAG 채팅 결과에 나타나지 않음** (고아 0)
- 벡터 메타데이터 행↔meta 정합 유지 (삭제 후 검색 결과의 title/url 어긋남 0)
- detach: 노드는 트리에 남고 url 만 비며, 파일·인덱스는 제거됨
- **authored 저작 문서**("작성 문서" 폴더)도 삭제 가능 — 파일 휴지통 이동 + 폴더에서 사라짐 (인덱스는 원래 0건이라 무관)
- 삭제 전 영향 미리보기 모달이 정확한 수치(파일 / 검색 섹션 N / 벡터 섹션 N / 참조 노드 수) 표시
- **중복 url** 노드 삭제 시 깨진 링크 0 (참조 노드 일괄 정리)
- **동시성** — 삭제와 업로드(증분 추가)/재빌드가 겹쳐도 인덱스·메타 손상 0
- 회귀 0 — 업로드·검색·채팅·기존 메뉴 편집(추가/수정/이동) 정상

### 선호
- 부분 실패(예: 벡터 제거 실패) 시 명확한 로깅과 사용자 안내, "정합성 재구축"(전체 재빌드) 안내
- `restart_needed` audit 표 완성 + 핫리로드 후보 식별

## 미해결 / 협의 필요
- 삭제 API 형태 — `DELETE /api/document?url=` vs `POST /api/document-delete` (기존 `upload.py` 컨벤션에 맞춰 결정, Phase 2 착수 시)
- 휴지통 보존 기간/자동 정리 — 무기한 보존 vs N일 후 자동 삭제(고아 `.docx_1` 24h 정리 선례 있음). 1차는 무기한, backlog 후보
- 영향 미리보기 수치 산출 비용 — 매 호출 산출 vs 캐시. 소규모(수백 섹션)라 매 호출로 충분할 듯

## 결정됨 (협의 완료)
- ✅ **삭제 정책** = 하드 삭제 + cascade + 휴지통 폴더 이동 (사용자 승인 2026-06-30)
- ✅ **authored 삭제 소유권** = Plan-67 이 일반+authored 삭제 전부 소유, Plan-60 은 개명·큐레이션만 (개발책임자 제안 → 사용자 승인 2026-06-30)
- ✅ **삭제 통합 방식 = 1번(즉시 분리 액션)** (사용자 승인 2026-06-30) — 문서 보유 노드 삭제 = 영향 미리보기 모달 → 확인 → 즉시 백엔드 cascade(파일 휴지통 + 인덱스 제거 + menu.json 노드 제거 atomic) → 편집기·트리 재동기화. 빈 카테고리 제거는 기존 스테이징 유지. 삭제 전 미저장 구조편집 있으면 먼저 저장/취소 안내(dirty-guard)
- ✅ **API 형태** = `POST /api/document-impact`(미리보기) + `POST /api/document-delete`(cascade) — 채택
- ✅ **휴지통 이동 단위** = content: `.html` + 동명 `_images/` 형제 / authored: `.md` 단일. `data/trash/<ts>/<원경로>` 보존. 무기한(자동정리 backlog)
- ✅ **린치핀 실측** = `IndexFlatL2.remove_ids([1,3])` → 생존행 0,2,4,5 순서보존 압축 확인 (2026-06-30)

## 산출물
- 코드: `vector_search.py`(remove_documents) · 검색 인덱스 제거 헬퍼 · 휴지통 헬퍼 · 삭제 API · cascade · detach · `admin-settings.js` UX
- 테스트: 삭제 정합 단위 + 직접 경로 검증 기록
- 보고서: `workbench/reports/plan-67-feedback-2026-MM-DD.md` (재시작 audit 표 포함)

## Notes

### 결정
- **삭제 정책 = 하드 삭제 + cascade + 휴지통 폴더 이동** (순수 언링크·풀 소프트삭제 모두 기각 — 전자는 복구 0, 후자는 내부 도구에 과투자)
- **벡터 삭제 = `IndexFlatL2.remove_ids` + 메타 동일 필터** (인덱스 타입 변경·재임베딩 없음). `IndexIDMap2` 마이그레이션은 특화 과공학으로 기각
- **3단 인덱스 구성 = 증분 추가(기존) + 증분 삭제(신규) + 전체 재빌드(기존 `/reindex`, 정합성 안전망)** — 업계 표준 그대로
- 재시작 폴리시는 **곁가지** — 메인은 문서 생애주기. audit 까지만, 구현 분리
- **authored 삭제 = Plan-67 소유**(트리 일관성: 보이면 다 지움) — 삭제 로직을 두 계획에 분산시키지 않음. Plan-60 은 개명·큐레이션만
- **멀티워커 캐시 불일치는 비해당** — 현재 단일 워커 배포. 향후 멀티워커 전환 시 `_faiss_index` 캐시 무효화 신호(파일 mtime watch 등) 재검토 — 그때의 별 사안

### 트레이드오프
- url 기반 매핑(레이블경로 매핑의 하위)이라 동일 url 중복 노드가 있으면 detach/삭제가 모든 참조에 영향 — 영향 미리보기에서 참조 노드 수 노출 + 일괄 정리로 완화
- 휴지통 무기한 보존 시 디스크 증가 — 자동 정리는 backlog
- authored/일반 삭제 경로 분기 — 코드에 `kind` 판별 1곳 추가(경로 prefix). 분기 비용보다 트리 일관성 이득이 큼

## Progress Log
- 2026-06-30 — plan 생성. 사전 조사(벡터 삭제 가능성·삭제 정책) 완료, 휴지통 폴더 이동 방식으로 결정.
- 2026-06-30 — plan-advisor 사전 검토 완료 → v1.1. 4대 전제 코드 검증 통과. authored 통합 삭제(Critical) 채택·동시성 락·중복 url 노드·미리보기 섹션수 표기 반영, 5e 멀티워커 비해당 격하. 공수 6→6.5일. **착수 가능(조건부 해소).**
- 2026-06-30 — /run-plan 수행 완료 (Phase 0~6, 7/7). 삭제 통합방식=1번(즉시 분리 액션) 승인. 린치핀 실측(remove_ids 순서보존)→삭제 코어·API·detach·admin UX 구현. **검증: 단위 6/6 + 실서버 HTTP e2e(백업→삭제→복원) 2회 PASS + sim 게이트 PASS, 실데이터 무손상.** code-review Critical 3/Warning 6/Suggestion 4 → 타당 5건 수정·오탐 4건 근거 기각(C1 `remove_ids` 미지원 주장은 e2e로 반증). 재시작 audit=배너 7항목만, 이미 표준 결론. 보고서 `reports/plan-67-feedback-2026-06-30.md`. **done 이관·커밋 대기.**
