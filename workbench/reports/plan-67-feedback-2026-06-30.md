# plan 67 실행 피드백 — Explorer 트리·문서 생애주기 관리 (삭제 cascade·인덱스 정합·detach·재시작 audit)
> 실행일 2026-06-30 · 실행자 Claude(/run-plan) · 대상 `workbench/plans/67-explorer-tree-doc-lifecycle.md`

## 요약
- 완료 Task **24/25** (F4 보고서=본 문서, done 이관 대기) · 변경 파일 **5** (백엔드 4 + 프론트 1, 신규 1)
- code-review: Critical 3 / Warning 6 / Suggestion 4 → **타당 5건 수정, 오탐 4건 근거 기각**
- 검증: 단위 6/6 · 실서버 HTTP e2e 2회(수정 전·후) PASS · sim 게이트 PASS · 실데이터 백업→복원 무손상

## 구현 결과

| 영역 | 상태 | 변경 파일 | 메모 |
|------|------|----------|------|
| A 삭제 코어 | ✅ | `backend/services/vector_search.py`, `backend/services/document_delete_service.py`(신규) | `remove_documents`(remove_ids+메타 동일필터), 휴지통 이동, 검색인덱스 제거, `INDEX_WRITE_LOCK`, authored 분기 |
| B API+cascade | ✅ | `backend/api/upload.py`, `backend/api/menu.py` | `POST /document-impact`·`/document-delete`(require_admin), `remove_or_detach_urls`(중복 url 일괄) |
| C detach | ✅ | `js/admin-settings.js` | `keep_nodes=true` → 노드 유지·url 분리, "문서만 제거(⊘)" 버튼 |
| D admin UX | ✅ | `js/admin-settings.js` | 영향 미리보기 모달, dirty-guard, 즉시 재동기화+토스트, 가짜 경고 제거 |
| E 재시작 audit | ✅ | (보고서) | 아래 §audit |
| F 검증 | ✅ | — | 단위+실서버 e2e |

### 핵심 설계 (업계 표준 준수)
- **삭제 정책** = 하드삭제 + cascade + **휴지통 폴더 이동**(`data/trash/<ts>/<원경로>`, unlink 금지) — 탐색기·Drive·Notion 표준
- **벡터 삭제** = `IndexFlatL2.remove_ids` + 메타 동일 필터 (인덱스 타입 변경·재임베딩 0). 순서보존 압축 **실측 확인**
- **인덱스 3단** = 증분추가(기존) + 증분삭제(신규) + 전체재빌드(기존 `/reindex`, 안전망)
- **통합 삭제** = 일반 업로드 문서 + authored 저작 문서(.md, 파일+가상폴더만, 인덱스 생략) 양쪽

## 검증 결과
- **게이트**: `tests/sim_label_consistency.sh` PASS (무관 영역 무회귀) · JS `node --check` OK · 백엔드 import OK · IDE 진단 미연결(대체 수단으로 커버)
- **단위 (실데이터 무손상, 임시 인덱스)**: ① remove_documents 중복url 3섹션 제거·순서보존·행↔메타 정합 ② 검색인덱스 url 제거 ③ classify_kind/traversal 차단 ④ 중복노드 일괄제거·시스템 무손상 ⑤ detach
- **실서버 HTTP e2e** (testbot=admin, 백업→합성주입→실삭제→디스크검증→복원): impact(파일2·검색2·벡터2·참조1) → delete(success, 양쪽 휴지통 이동, 검색2·벡터2 제거, 노드1) → **menu/search/vector 무잔존**(360·436) → 파일 `data/trash/` 이동 확인. **수정 전·후 2회 PASS**
- **회귀**: 복원 후 벡터 인덱스 로드 정합(ntotal 436==meta 436) · 데이터 4파일 git 무변경(클린 복원)

## code-review 트리아지
**오탐 4건 (근거 기각):**
- 🔴C1 "`IndexFlatL2.remove_ids` 미지원" → **기각.** 실측 2회 반증: 린치핀 단위테스트(행1,3 삭제→0,2,4,5 순서보존) + 실서버 e2e에서 실제 인덱스 2벡터 제거 성공(ntotal 438→436). 이 faiss 버전에서 FlatL2 삭제 동작 확정
- 🔴C2 "재빌드 중 락 무의미" → **기각.** subprocess는 락 미공유지만 다른 인프로세스 writer(append/remove)가 **같은 락 acquire** → 재빌드가 락 보유 동안 대기. 현실적 경쟁 전부 차단
- 🟡W4(Windows case), W5(confirm) → 기존 `validate_target_path`·`_deleteUser` 패턴과 동일, 일관성상 유지

**타당 5건 (수정 완료):**
- 🔴C3 다중 url 부분실패 → `validate_url` 전수 사전검증 후 변경 시작
- 🟡W1 휴지통 stamp 충돌 → `%f` 마이크로초 추가 (e2e 확인)
- 🟡W2 모달 숫자 비이스케이프 → `Number()` 강제변환
- 🟡W3 url 상한 없음 → strip + 최대 100 cap
- 🟡W6 menu load↔save 경쟁 → `_MENU_LOCK` (cascade + 기존 POST /menu 양쪽 보호)

## 재시작 폴리시 audit (E1/E2)
`settings_service.apply_to_config` 분석 — 배너(`restart_needed`) 유발 항목은 **단 7개**, 나머지 ~60개 설정 + **메뉴/트리 편집 전부 즉시반영**(`immediate=True`).

| restart 항목 | 판정 | 근거 |
|---|---|---|
| `CORS_ORIGINS` | **재시작 정당** | CORSMiddleware가 앱 시작 시 origins 고정 — config 변경으로 갱신 불가 |
| `LLM_GATEWAY_max_concurrent/queue/stream_slots` | **재시작 정당** | Semaphore 재생성이 대기요청 교착 유발(코드 주석 명시된 Critical 결정) |
| `EMBEDDING_MODEL` | 보수적(정당) | 모델 교체 시 기존 벡터 인덱스 불일치 → 어차피 전체 재빌드 필요 |
| `SESSION_EXPIRY_HOURS` | 핫리로드 후보(경미) | 세션 생성 시 라이브 참조면 즉시 가능 — 안전 확인 시 backlog |
| `LOGIN_REQUIRED` | 보수적 유지 | 보안 게이트 실시간 토글은 위험 — 재시작 유지 권장 |

**결론**: 배너는 **이미 업계표준**(대부분 핫리로드, 소수만 재시작)을 따른다. "해당 없는 수정에도 뜬다"는 인상은 코드상 사실 아님 — 트리·메뉴 편집은 배너와 무관. 추가 핫리로드화는 ROI 낮음(CORS·게이트웨이는 정당, 임베딩은 재빌드 동반). `SESSION_EXPIRY_HOURS` 1건만 안전한 경미 후보 → backlog.

## 5관점 피드백
- **개발책임자**: 그린필드라 회귀 표면 최소. 기존 자산(`_menuCollectUrls`·`validate_target_path`·`reloadTreeMenuAndLoad`·`_remove_from_search_index` 선례) 재사용으로 신규 표면 압축. 락·전수검증으로 부분실패/경쟁 방어
- **코드전문가**: url 단일키 3곳(메뉴/검색/벡터) 일치 → 삭제 코어 1함수 대칭. `append_documents`/`remove_documents` 대칭쌍. 락은 임베딩(느림) 밖, 인덱스 IO만 안
- **UI/UX**: `confirm()` 텍스트 → 영향 미리보기 모달 승급, dirty-guard로 스테이징 충돌 차단. 휴지통=복구가능 1줄 고지
- **웹디자인**: 기존 `admin-modal-overlay`/`.btn-danger`/`.spinner-sm`/`var(--color-error)` 재사용, 신규 색·간격 하드코딩 0
- **사용자**: "트리에 보이면 다 지움"(일반+authored) 일관성. detach로 "노드는 두고 문서만" 가능

## 업계표준 재검토
- 삭제: 즉시확인+휴지통(탐색기/Drive/Notion/Gmail) — 채택. 풀 소프트삭제·복구UI는 내부 단일운영자엔 과투자(YAGNI)로 제외
- 벡터 삭제: 소규모(수백 섹션)는 remove_ids 증분이 표준. `IndexIDMap2` 마이그레이션은 특화 과공학으로 기각
- 수용한 한계: 휴지통 무기한 보존(자동정리 backlog) · 복구는 수동 파일 되돌리기 · 멀티워커 캐시 무효화는 단일워커라 비해당(전환 시 재검토)

## 잔여·후속 제안 (backlog 후보)
- 휴지통 비우기/복구 UI · N일 자동정리
- `SESSION_EXPIRY_HOURS` 핫리로드화(경미)
- authored 개명·노출 큐레이션(Plan-60 소유)
- 레이블경로→id 매핑 전환(별건 대형)

## 커밋 제안 (요청 시)
```
구현 [Explorer] 문서 삭제 cascade — 휴지통 이동·인덱스 정합·detach (Plan-67)

- 삭제 코어: vector_search.remove_documents(remove_ids+메타 동일필터, 순서보존 실측)
  + document_delete_service(휴지통 이동·검색인덱스 제거·authored 분기) + INDEX_WRITE_LOCK
- API: POST /document-impact·/document-delete(require_admin) + menu.remove_or_detach_urls(중복 url 일괄)
- admin UX: 영향 미리보기 모달·detach 버튼·dirty-guard·즉시 재동기화, 가짜 경고 제거
- code-review 5건 반영(전수 사전검증·휴지통 마이크로초·숫자 강제변환·url cap·menu 락)
- 검증: 단위 6/6 + 실서버 HTTP e2e(백업→삭제→복원) PASS

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
```

## 교훈 (비자명)
- **FAISS `IndexFlatL2.remove_ids` 는 이 버전에서 동작하며 남은 행 순서를 보존 압축**한다 — 위치기반 메타 리스트를 동일 인덱스로 필터링하면 정합 유지. "일반 지식상 미지원" 통념과 반대이므로 실측이 SSOT (e2e 증거 보존). → plan Notes 에 반영됨
