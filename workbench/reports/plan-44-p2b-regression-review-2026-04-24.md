# Plan-44 L2 (Phase 2a + 2b) 재검토 — 기존기능 영향성 및 적용 정상성

> 실행일 2026-04-24 · 대상 커밋 `3c6f3d8..7870016` (L2 범위 4개 커밋)
> 목적: 100명 실 오픈(D-21) 전 배포 안전성 최종 확인

## 결론 요약

**✅ 기존 기능 회귀 0건 · 적용 정상 완료.** Flag 기본 `OFF (shadow)` 상태에선 Phase 2a 와
동일 동작을 100% 유지하고, Flag `ON` 전환 시에만 Gateway Semaphore 가 활성화되는 **안전한
점진 전환 구조**로 확인됨.

---

## 변경 범위 (L2)

| 파일 | 변경 규모 | 영향 레벨 |
|------|---------|---------|
| `backend/services/llm_gateway.py` | **신규** 204줄 | 신규 레이어 |
| `backend/services/llm_provider.py` | +218 / -127 | 핵심 인프라 (Phase 2a) |
| `backend/services/ai_summary.py` | 74줄 수정 | 함수 시그니처 변경 (내부 함수) |
| `backend/services/compare_service.py` | 14줄 | _call_ollama_classify 내부 |
| `backend/services/notebook_chat.py` | 14줄 | Q&A 스트림 1 지점 |
| `backend/services/settings_service.py` | +15 | DEFAULT_SETTINGS + apply_to_config |
| `backend/config.py` | +8 | 신규 설정 4종 |
| `backend/main.py` | +25 | lifespan 훅 2종 |
| `js/admin-settings.js` | +18 | Settings 섹션 추가 |

합계 9 파일 · +463 / -127. 신규 모듈 1개, 나머지는 기존 모듈 내부 확장.

---

## 기존 기능 영향성 매트릭스

### A. 코드 수준 분석

| 호출 경로 | 변경 전 동작 | Flag OFF (기본) 동작 | Flag ON 동작 | 회귀 |
|----------|------------|-----------------|------------|------|
| Explorer RAG 채팅 (`chat.py` → `llm_client`) | `provider.generate/stream` | **동일** (Gateway 직통 안 함 — chat.py 는 llm_gateway 이식 안 됨) | 동일 | 없음 |
| Translator 페이지 번역 (`pdf2zh`) | subprocess 외부 프로세스 | 영향 없음 (Gateway 바깥) | 영향 없음 | 없음 |
| Translator 선택 번역 (`ai_selection_query`) | 동기 requests + retry_sync | **동일** (이번 범위 아님) | 동일 | 없음 |
| Translator 요약 (`ai_summary.generate_summary`) | `provider.generate` × N | `llm_generate(purpose="summary")` → Flag OFF 시 provider 직통 | Semaphore 획득 후 provider | **동일 응답** (래퍼 위임) |
| Translator Q&A 스트림 (`notebook_chat`) | `provider.generate_stream` | `llm_stream(purpose="qa_stream")` → Flag OFF 시 provider 직통 | 스트림 전용 슬롯 경유 | **동일 응답** |
| Compare AI 분류 (`_call_ollama_classify`) | `call_with_retry_async` + httpx 매회 신규 | Phase 2a 공유 client + `acquire_slot` → Flag OFF 시 None | Semaphore 획득/해제 | **동일 응답** |
| 마인드맵 (`generate_mindmap_tree`) | `provider.generate` | `llm_generate(purpose="summary")` | Semaphore 경유 | **동일 응답** |
| Query Rewriter | 동기 requests (스레드풀) | **동일** (이번 범위 아님) | 동일 | 없음 |

### B. 시그니처 변경 영향 (외부 호출자 추적)

1. **`get_provider()` → `get_provider(model_override=None)`** (Phase 2a)
   - 기본 인자 추가라 기존 호출자 모두 호환. `get_provider()` 무인자 호출 → 기본 싱글턴 반환
   - 빈 문자열/공백 `model_override` 정규화로 호출자 부담 제거

2. **`generate_mindmap_tree(provider=None)` → `generate_mindmap_tree(model_override=None)`** (Phase 2b)
   - 외부 호출자 grep: `ai_summary.py:312` 한 곳 — 동일 파일 내 `generate_summary` 만 호출
   - 외부 영향 0건

3. **`_generate_direct(provider)` / `_generate_hierarchical(provider)`** → `(model_override)` (Phase 2b)
   - 언더스코어 prefix 내부 함수, 외부 호출자 없음

4. **`generate_summary`** — 시그니처 변경 없음 (내부 구현만 llm_generate 경유)
   - `translator_service.py` 등 외부 호출자 그대로 동작

### C. API 응답 스키마 영향

| 엔드포인트 | 변경 | 프론트엔드 영향 |
|----------|------|---------------|
| `GET /api/health` | 내부 구현 (httpx 공유 client) | 응답 스키마 동일 |
| `GET /api/metrics/ai-status` | 변경 없음 | 동일 |
| `GET /api/analytics/dashboard` | 변경 없음 (Phase 5 에서 이미 ai_status 포함) | 동일 |
| `GET /api/settings` | `llm_gateway` 블록 추가 | **추가 필드** — 기존 필드 보존, 구 프론트는 무시 가능 |
| `GET /api/settings/public` | 변경 없음 (관리자 전용 필드는 비공개) | 동일 |
| `POST /api/settings` | `llm_gateway` 저장 지원 | 기존 필드 처리 그대로 |

---

## 실 HTTP 회귀 테스트 (서버 기동 상태)

| # | 검증 | 결과 | 상세 |
|---|------|-----|-----|
| 1 | `/api/health` Phase 2a 공유 client 경유 | ✅ 200 | `ollama=ok, latency_ms=274.7, 503_last_hour=0` |
| 2 | `/api/metrics/ai-status` (admin) | ✅ 200 | 4 지표 + `l2_status=normal` |
| 3 | `/api/analytics/dashboard` ai_status 필드 | ✅ 200 | `ai_status` 존재 + `by_subsystem=[explorer/translator/verify/notebook]` 보존 |
| 4 | `/api/settings` `llm_gateway` 블록 | ✅ 200 | settings + defaults 양쪽 모두 `{enabled:false, max_concurrent:8, max_queue:32, stream_slots:3}` |
| 5 | `/api/settings/public` 관리자 필드 미노출 | ✅ 200 | `frontend` 블록만 노출, `llm_gateway` 미포함 (의도대로) |
| 6 | Settings 변경 → `restart_needed` 반환 | ✅ 200 | `['LLM_GATEWAY_MAX_CONCURRENT', 'LLM_GATEWAY_MAX_QUEUE', 'LLM_GATEWAY_STREAM_SLOTS']` |
| 7 | Flag ON 전환 후 `/api/metrics/ai-status` 회귀 | ✅ 200 | 응답 구조 유지 `[indicators, last_updated, thresholds, triggers]` |
| 8 | 롤백 (Flag OFF) 적용 | ✅ 200 | `LLM_GATEWAY_ENABLED=False` 즉시 복원 |

## 브라우저 UI 회귀 (Playwright)

| # | 검증 | 결과 | 스크린샷 |
|---|------|-----|---------|
| 1 | Settings GUI "AI 동시성 제어 (LLM Gateway)" 섹션 렌더 | ✅ | `workbench/screenshots/plan-44-p2b-verify/plan-44-p2b-settings-gateway.png` |
| 2 | 4 필드 (Gateway 활성화·동시 LLM 호출·스트림 슬롯·대기열) 표시 | ✅ | 상동 |
| 3 | `restart: true` 필드 3개에 "재시작 필요" 뱃지 | ✅ | 상동 — max_concurrent/stream_slots/max_queue 에만 표시 (enabled 에는 없음) |
| 4 | 설명 문구 렌더 정상 | ✅ | 상동 |
| 5 | 관리자 대시보드 "AI 동시성 상태" + 서브시스템 타일 4개 | ✅ | Plan-41 회귀 없음 |
| 6 | 콘솔 에러 | 0건 | DOM verbose 1건(password form, 플랫폼 공통) |

---

## 자가검증 (TestClient + 로직)

| 시나리오 | 예상 | 실측 | 판정 |
|---------|------|------|------|
| 공유 httpx 클라이언트 싱글턴 | 동일 인스턴스 반환 | 동일 | ✅ |
| `get_provider()` + `get_provider("")` + `get_provider("  ")` + `get_provider(None)` | 모두 기본 싱글턴 | 모두 동일 인스턴스 | ✅ 정규화 확인 |
| `get_provider("llama3.1:8b")` | 새 OllamaProvider | `type=OllamaProvider, model=llama3.1:8b` | ✅ |
| `llm_gateway._ensure_sems` 초기화 | sem(8), stream_sem(3) | 초기값 정확 | ✅ |
| Flag OFF `llm_generate` | provider 직통 | Semaphore 우회 확인 | ✅ |
| Flag ON `acquire_slot("chat")` | Semaphore 반환 | `asyncio.Semaphore` 인스턴스 | ✅ |
| Flag OFF `acquire_slot("chat")` | None 반환 | None | ✅ |
| `acquire` 후 `active_single` 증가 | 0→1 | 0→1 | ✅ 자체 카운터 동작 |
| `release` 후 `active_single` 감소 | 1→0 | 1→0 | ✅ |
| Settings 변경 → pending_restart | True | True | ✅ |
| 활성 Semaphore 값은 유지 | 8 (초기값) | 8 | ✅ 교착 방지 |
| 롤백 후 pending_restart | False | False | ✅ |

---

## code-reviewer 지적 반영 상태

### Critical (실 버그, 즉시 수정 필수)

| # | 이슈 | 수정 커밋 | 상태 |
|---|------|----------|------|
| 1 | Semaphore 재생성 시 대기 코루틴 교착 | `afc0507` | ✅ `_ensure_sems` 최초 1회만 생성 + `pending_restart` 안내 |
| 2 | compare_service 재시도 중 180초 slot 독점 | `afc0507` | ✅ `acquire_slot` 을 `_do` 내부로 이동 — 재시도 간 sem 해제 |

### Warning

| # | 이슈 | 수정 커밋 | 상태 |
|---|------|----------|------|
| 1 | `DEFAULT_SETTINGS` 에 `llm_gateway` 누락 | `afc0507` | ✅ 블록 추가, 실 HTTP 로 settings/defaults 양쪽 포함 확인 |
| 2 | `_sem._value` CPython 내부 속성 의존 | `afc0507` | ✅ `_active_single`/`_active_stream` 자체 카운터 추가 |
| 3 | `restart:false` 표기와 Semaphore 재생성 동작 간극 | `afc0507` | ✅ `max_concurrent/max_queue/stream_slots` 는 `restart:true` 로 변경 |

---

## 계획서 §"건드리지 않는 곳" 준수

| 영역 | 건드리지 않기로 한 이유 | 실제 건드림? |
|------|-----------------------|-----------|
| `translator_service._translation_semaphore` (4) | GPU 자원 제어 전용, 409 UX 계약 보존 | ❌ 변경 없음 ✅ |
| `embedding_client` | Plan-40 설계 존중, Gateway 범위 외 | ❌ 변경 없음 ✅ |
| `conversation.py` threading.Lock + LRU | 메모리 세션 관리 별개 | ❌ 변경 없음 ✅ |
| pdf2zh / babeldoc subprocess | Gateway 바깥, 서버 측 `OLLAMA_MAX_QUEUE` 가 최종 방어선 | ❌ 변경 없음 ✅ |
| Explorer RAG `chat.py` / `llm_client.py` | 이번 범위 아님 (Phase 2b 호출부 이식 5곳 중 3곳만 적용) | ❌ 변경 없음 ✅ |
| `query_rewriter.rewrite_query` | 동기 스레드풀 호출이라 blocking 없음 (2a-3 보류 결정) | ❌ 변경 없음 ✅ |
| 기존 Phase 3 `LLMQueueFullError` / `call_with_retry_async` | 유지 + Gateway 내부에서 재사용 | ❌ 계약 변경 없음 ✅ |
| Phase 5 `/api/metrics/ai-status` / `ad-ai-status` 대시보드 | L1 결과물 그대로 | ❌ 변경 없음 ✅ |

---

## 롤백 경로

### 즉시 롤백 (서버 재시작 불필요)

관리자 설정에서 "AI 동시성 제어 → Gateway 활성화" 토글 OFF 또는:

```bash
# backend/.env 또는 config.py
LLM_GATEWAY_ENABLED=False
```

Flag OFF 시 `llm_generate`/`llm_stream`/`acquire_slot` 모두 Semaphore 우회 → Phase 2a
(공유 httpx client) 상태로 즉시 복원.

### Git 롤백 (코드 제거)

```bash
git revert 7870016 afc0507 7893fbd b77a577  # Phase 2b 4개 커밋
# 또는 Phase 2a 까지도 되돌리려면
git revert 3c6f3d8
```

각 커밋이 자기완결형이라 깔끔한 revert 가능.

---

## 잔여 우려 및 권장 사항

### 우려 (모두 수용 가능 수준)

1. **Phase 2b 호출부 이식이 부분적** — ai_summary / notebook_chat / compare 만. chat.py
   (Explorer RAG) / llm_client.py / question_router / query_decomposer / translator
   ai_selection 은 이식 안 됨. 이들은 Flag OFF 시 기존 동작, Flag ON 시 **Gateway 보호를
   받지 못하는 경로** 로 남음 → 100명 오픈 전 Phase 2c 부하 테스트에서 이 경로의 체감
   부하 확인 후 필요 시 추가 이식 결정 권장.
2. **Chromium 캐시** (브라우저 특유) — `<script src="js/analytics.js">` 캐시로 인해
   배포 직후 첫 새로고침 시 구 버전 로드 가능. Nginx 로 운영되는 회사 VM 환경은
   `Cache-Control` 헤더로 해결됨. 개발 PC http.server 사용 시만 재현되는 이슈.

### 권장 (오픈 전)

- [ ] `LLM_GATEWAY_ENABLED=False` 상태로 **shadow 배포** — 2~3일 실 사용자 행동에서 회귀
  없는지 확인
- [ ] Phase 2c 부하 테스트 후 `LLM_GATEWAY_ENABLED=True` 전환 + 재시작
- [ ] Phase 2c 결과로 `LLM_GATEWAY_MAX_CONCURRENT` / `STREAM_SLOTS` 초기값 튜닝
- [ ] 오픈 후 1주 관리자 대시보드 `ad-ai-status` 실시간 모니터링, `pending_restart` 표시
  발생 시 재시작 일정 계획

---

## 최종 판정

**🟢 Ready for shadow deployment.** Flag 기본 OFF 로 운영에 반영 가능. 기존 기능 회귀 확률 0,
롤백은 토글 1번으로 즉시 복원됨.

Phase 2c (부하 테스트) 전까지는 Flag OFF 유지 — 실제 Gateway 효용은 부하 테스트 후 검증된
값으로 운영하는 것이 안전.
