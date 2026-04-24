# Plan 44: Ollama 동시성·안정성 강화

최종 수정: 2026-04-24 (v4 — L1 완료, L2 사전 착수 전환: 100명 오픈 3주 내)

---

## 📋 진행 현황 대시보드

> 상태 표기: ⬜ 미착수 / 🟨 진행 중 / ✅ 완료 / ⏸ 보류(트리거 대기)
> 착수·완료 시 체크박스와 상태 아이콘 함께 갱신.

### L1 — 즉시 실행 (목표: 4~5일, 지표·증상 없어도 이득)

**Phase 1: Ollama 서버 설정** ✅ (5 / 5)
- [x] 1-1. `nvidia-smi` 로 피크 VRAM 실측 절차 문서화 (실제 실측은 운영자 영역)
- [x] 1-2. `.env.example` 권장값 반영 (`NUM_PARALLEL=2`, `MAX_QUEUE=64`, `KEEP_ALIVE=30m`, `MAX_LOADED_MODELS=2`, `FLASH_ATTENTION=1`)
- [x] 1-3. `docker-compose.yml` 주석 + `docs/03-DOCKER-OPERATIONS.md §2-2-A` 섹션 신설 (systemd override 예시 포함)
- [x] 1-4. 스트리밍 슬롯 점유 특성 docs 에 명시 (`num_parallel` 슬롯은 스트림 종료까지 점유)
- [x] 1-5. 검증 스크립트(`/api/ps` / 동시요청 / `nvidia-smi` / 503 재현) 문서화

**Phase 3: 503→429 변환 + 백오프** ✅ (3 / 3)
- [x] 3-1. `services/llm_retry.py` — `LLMQueueFullError` + `call_with_retry_async/sync` (지수 백오프, jitter, 최대 3회, 503/ConnectError/ReadTimeout 대상)
- [x] 3-2. `main.py` 에 `@app.exception_handler(LLMQueueFullError)` 등록 — 429 + `Retry-After` 헤더 + `retry_after` body
- [x] 3-3. 호출부 5곳 적용 (`llm_provider.OllamaProvider.generate/stream`, `OpenAICompatProvider.generate/stream`, `translator_service.ai_selection_query`, `compare_service._call_ollama_classify`, `query_rewriter` 503 로그 구분)

**Phase 4: 프론트 RequestGuard** ✅ (4 / 4)
- [x] 4-1. `js/request-guard.js` 신설 — `fetchWithRetry` (429 자동 재시도, Retry-After 헤더 + 대기 중 abort 감지). `guard()` 계열 미사용 확인 후 YAGNI 제거 (simplify 리뷰)
- [x] 4-2. LLM fetch 4곳 이식 (`ai-chat.js:/api/chat` + `/api/chat/stream`, `translator.js:/ai/selection`, `compare.html:/compare/ai-classify`)
- [x] 4-3. `js/toast.js` 에 `showRetryToast(sec)` 추가 — 카운트다운 + warning 색, showToast 와 타이머 공유
- [x] 4-4. 페이지 이탈·탭 전환 시 중단은 브라우저 fetch 기본 동작으로 처리 (각 호출부의 개별 AbortController + 429 재시도 중 signal.aborted 감지로 충분; 별도 abortAll 훅은 YAGNI 로 제거)

**Phase 5: 헬스·지표 + 관리자 대시보드 섹션 (디자인 시스템 준수)** ✅ (5 / 5)
- [x] 5-1. `/api/health` 에 `ollama_latency_ms`, `ollama_503_last_hour` 필드 추가 (overall 판정 제외 처리)
- [x] 5-2. `/api/metrics/ai-status` 신설 — 4지표 + 임계값 + 트리거 상태(`normal`/`warning`/`fired`) 노출
- [x] 5-3. `services/ai_metrics.py` — 1h 롤링 버퍼 + L2/L3 임계값 판정 + `snapshot_loop` (lifespan task, 1시간 주기 `analytics_events` 저장) + llm_retry 에 `record_llm_call` 훅 + generate_stream 에 `mark_stream_start/end`
- [x] 5-4. `admin.html` 대시보드 "AI 동시성 상태" 섹션 — `_renderAIStatus` 신규 (health 뱃지 뒤·서브시스템 타일 앞), `analytics.css` 에 `.ad-ai-*` 토큰 기반 스타일 (반응형 3단계, 다크모드 자동, p95 는 s 로 자동 단위 변환), 대시보드 응답에 `ai_status` 통합
- [x] 5-5. L2 트리거 배너 `.ad-alert.ad-alert-warning` + 24h dismiss (localStorage) — `_renderL2Banner` 최상단 삽입, `data-dismiss-banner` event delegation, `require_admin` 경유 자동 auth 가드

### L2 — 사전 준비 (100명 실 오픈 3주 내 예정 · 필수)

> **착수 근거 (v4)**: 2026-04-24 시점에 실 운영 조건이 변경됨 — 현재 15명 내부 테스트(동시 2~3명) 단계이며, 2~3주 내 실(100명+) 전체 오픈 예정.
> 100명 중 10%만 업무 시간대에 동시 사용해도 10명 동접 → 기존 "트리거 발동 후 착수" 원칙으론 오픈 후 대응 불가.
> **관찰 → 착수 → 튜닝** 순서가 불가능하므로, **오픈 전 선제 구축 + 부하 테스트 기반 튜닝** 으로 전환.

**Phase 2a: 부하 무관 선행 개선 (Week 1 전반, ~2일)** ✅ (3 / 3)
- [x] 2a-1. `llm_provider.py` httpx.AsyncClient 싱글턴화 (`_get_shared_client` + `_shared_client` 모듈 싱글턴 + `Limits(max_connections=50, max_keepalive_connections=20)`) + `aclose_shared_client()` main.py lifespan shutdown 훅 + `/api/health` 도 공유 client 경유(code-reviewer 지적 반영)
- [x] 2a-2. `ai_summary.py` 2곳의 `OllamaProvider()` 직접 생성 제거 → `get_provider(model_override=...)` 호출로 통일. `get_provider` 시그니처 확장 (`model_override: Optional[str]`, 빈 문자열·공백 자동 정규화로 호출자 부담 제거)
- [x] 2a-3. **보류** — `query_rewriter.rewrite_query` 는 `chat.py:205` 에서 이미 `asyncio.to_thread` 로 스레드 풀 실행 중. 이벤트 루프 블로킹 없음 → async 전환 실익 없음. 보류 근거 문서화로 완료.

**Phase 2b: LLM Gateway 본체 (Week 1 후반, ~3~5일)** 🟨 (0 / 5)
- [ ] 2b-1. `services/llm_gateway.py` 신설 — 글로벌 Semaphore + 스트림 전용 슬롯 + 용도별 weight (chat=1 / translation=2 / summary=2 / qa_stream=1)
- [ ] 2b-2. 호출부 이식 (`ai_summary`, `query_rewriter`, `translator_service.ai_selection_query`, `compare_service._call_ollama_classify`, `notebook_chat` 스트림)
- [ ] 2b-3. 기존 `_translation_semaphore` → Gateway weight 슬롯 재구현 (기존 409 UX 계약 유지)
- [ ] 2b-4. Settings GUI: `LLM_GATEWAY_MAX_CONCURRENT` / `MAX_QUEUE` / `STREAM_SLOTS` 노출 (런타임 반영)
- [ ] 2b-5. `LLM_GATEWAY_ENABLED=false` 롤백 플래그 — 1주 shadow 운영용

**Phase 2c: 부하 테스트 (Week 2, ~1.5일) — 용도 분리 필수** 🟨 (0 / 3)
- [ ] 2c-1. **개발 PC 스모크** — locust 등으로 100 가짜 동시 요청, deadlock·메모리 누수·429 경로·프론트 재시도 **구조 검증** (GPU 없이도 가능. 숫자 튜닝은 아님)
- [ ] 2c-2. **회사 VM 실 로드** — 50명 시뮬레이션 (GPU+Ollama 실 환경), p95 지연·VRAM 피크·큐 대기시간 **실측** → Semaphore/큐 임계값 결정
- [ ] 2c-3. 실측 결과를 `.env` / Settings GUI 초기값으로 반영, 대시보드 임계값(L2 발동선) 현실화

**Phase 2d: 대시보드 Gateway 지표 (Week 2 후반, 반나절)** 🟨 (0 / 1)
- [ ] 2d-1. `.ad-ai-status` 하단 2차 그리드 추가 — 슬롯 사용률 / 대기열 길이 / 용도별 sparkline / 429 발생률 (기존 `.ad-tile-spark`·`.ad-hbar` 재사용)

**Phase 2e: 오픈 후 안정화 (Week 3 이후)** 🟨 (0 / 1)
- [ ] 2e-1. 100명 오픈 후 1주 운영 관찰 → 필요 시 Settings 값 재조정 → 안정 확인 후 `LLM_GATEWAY_ENABLED` 플래그 제거 (`backlog.md` 이관)

### L3 — 전환 보류 (Ollama + 튜닝으로 100명/동시 10~15명까지 감당 가능 전제)

> **판단**: vLLM 전환은 200+ 동시 사용자 또는 L2 튜닝 후에도 지표 지속 초과 시 착수. 현 규모에선 과투자.

- [ ] **L3 트리거 지표 확인** (p99 > 20s 2주 연속 or 동접 > 15명 지속 or 503 > 10/h) ⏸
- [ ] vLLM / TGI POC 계획서 작성 (별도 Plan 번호) ⏸
- [ ] 모델 호환성 + 폐쇄망 배포 + 운영자 학습 비용 평가 ⏸

### 전체 요약

| 레이어 | 진척 | 총 항목 | 상태 |
|--------|------|---------|------|
| L1 (즉시) | **17 / 17** | 17 | ✅ 전체 완료 (2026-04-24) |
| L2 (사전 준비) | **3 / 13** | 13 | 🟨 Phase 2a ✅ 완료, Phase 2b 진행 예정 |
| L3 (전환) | **0 / 3** | 3 | ⏸ 200+ 동시 또는 L2 튜닝 후 지표 지속 초과 시 |

---

## Context

현재 플랫폼은 Explorer RAG 채팅, Translator 페이지 번역(pdf2zh), 웹뷰 번역(babeldoc),
AI 요약(Map-Reduce), Q&A 스트리밍, 쿼리 재작성, Compare AI 분류, 임베딩(검색·인덱싱) 등
**최소 8개 경로가 같은 Ollama 인스턴스를 공유**한다. 실사용 관점에서 "여러 사용자가 동시에
복합 요청을 보내는 상황"에 대한 방어선이 **번역 Semaphore(4) 하나로 편중**되어 있고,
나머지 경로는 도달량 제한 없이 Ollama 로 직행하고 있음을 확인했다.

### Ollama 본질적 특성 (공식 문서 + 업계 벤치마크 실조사, 2026-04-24)

본 계획은 **Ollama 를 튜닝하여 수용 능력을 높이는 것**이 목표이되, 다음 한계를 전제한다.

| 특성 | 값/동작 | 출처 |
|------|---------|------|
| `OLLAMA_NUM_PARALLEL` 기본값 | 가용 메모리 보고 1 또는 4 자동 선택 | 공식 FAQ |
| `OLLAMA_MAX_QUEUE` 기본값 | 512, 초과 시 **503 Service Unavailable** | 공식 FAQ |
| `OLLAMA_MAX_LOADED_MODELS` 기본값 | 3 × GPU 수 | 공식 FAQ |
| 컨텍스트 KV 캐시 확장 | `num_parallel=N` 이면 실효 컨텍스트 **N배로 VRAM 소모** | 공식 FAQ |
| 스트리밍 슬롯 점유 | `num_parallel` 슬롯은 **스트림 종료까지 계속 점유** (FIFO 큐) | Glukhov 운영 블로그 |
| 0.2+ 기본 동작 | concurrency 기본 활성화 (우리는 이미 혜택 중일 가능성 높음) | Ollama 공식 공지 |
| production 적합성 | **설계상 소수 사용자용**. 5명 이상 상시 동접은 vLLM/TGI 권장이 업계 정설 | Red Hat Dev 벤치 |
| 실측 비교 (Llama 3.1 70B, Blackwell) | **vLLM 8,033 TPS vs Ollama 484**, 3.23× at 128 concurrency | Red Hat Dev |
| 실측 OOM (Llama 3.1 8B, H100 80GB) | **Ollama ~40 동접 / vLLM 180+** | Red Hat Dev |

**결론**: Ollama 튜닝은 "소규모 팀(~5명) 구간의 스위트 스팟을 유지"하는 것이지,
"확장성 문제를 해결"하는 것이 아니다. 이 구분을 Phase 우선순위와 vLLM 트리거 설계에 반영한다.

### 검증된 현황 (2026-04-24 코드 실측)

| 경로 | 제어 | 코드 포인트 | 평가 |
|------|------|------------|------|
| PDF 페이지 번역 | `asyncio.Semaphore(TRANSLATOR_MAX_CONCURRENT=4)` + 문서당 1개 락 | `translator_service.py:21-29, 917-920, 943-950` | ✅ 잘 됨 |
| Translator 웹뷰 번역 | `_web_active_tasks` 문서당 1개 | `translator_service.py:1300, 1316` | ✅ 의도적 |
| Translator 요약 | 사용자+문서당 1개 락만 | `translator_service.py:1832, 1853, 1876` | ⚠️ Ollama 호출 N회 병렬 제어 없음 |
| 멀티턴 세션 | `threading.Lock` + LRU(100) | `conversation.py:42-77` | ✅ 메모리 보호 OK |
| 임베딩 인덱싱 | `EMBEDDING_OLLAMA_BATCH=256` 청크 분할 | `embedding_client.py:120-133` | ✅ 적절 |
| 임베딩 런타임 | 로컬 CPU 기본 | `embedding_client.py` `_DEFAULT_BACKEND_BY_PURPOSE` | ✅ Plan-40 설계 |
| Explorer RAG 채팅 | ❌ 없음 (`get_provider()` → `httpx.AsyncClient` 매 호출 생성) | `llm_provider.py:68-113, 227-259` | ⚠️ 무방비 |
| Translator Q&A 스트리밍 | ❌ 없음 | `notebook_chat.py:175-178` (timeout=180) | ⚠️ 무방비 |
| Translator 선택 번역/요약 | ❌ 없음 (`asyncio.to_thread` → 동기 `requests.post`) | `translator_service.py:683-696` | ⚠️ 스레드 풀 포화 가능 |
| Compare AI 분류 | 배치 20 + 재시도 1회 | `compare_service.py:789-879` | ⚠️ 배치 간 대기 없음 |
| 쿼리 재작성 | timeout=15s + 키워드 결합 폴백 | `query_rewriter.py:84-107` | ✅ 폴백 양호 |
| AI 요약 LLM 호출 | **매번 `OllamaProvider()` 신규 생성** | `ai_summary.py:239, 294` | ⚠️ 제공자 싱글턴마저 우회 |
| Ollama 서버 env | 미설정 (`OLLAMA_NUM_PARALLEL`/`MAX_QUEUE`/`KEEP_ALIVE`/`MAX_LOADED_MODELS` 없음) | `.env`, `docker-compose.yml` | ⚠️ 기본값 의존 |
| 헬스체크 | `/api/tags` 200 OK 확인만 | `main.py:241-263` | ⚠️ 지연·큐 가시성 없음 |
| 프론트 중복 요청 가드 | 일관성 없음 (`isLoading` 플래그 2곳, `AbortController` 산발적) | `ai-chat.js:8, 474, 517, 1227`, `translator.js:1994, 2034` | ⚠️ 서브시스템별 제각각 |

### 제약 조건

- Vanilla Python + 표준 라이브러리 우선 (외부 패키지 추가 최소화 — 폐쇄망)
- Ollama 가 유일한 LLM 백엔드 전제 (단, 이미 `OpenAICompatProvider`가 있으므로 추상화 유지)
- 기존 기능 0 회귀 — Semaphore(4) 번역 로직은 내부 구현 바꿔도 외부 계약(409 Conflict,
  "번역 대기 중…") 유지
- **"과도한 엔지니어링 금지"** (CLAUDE.md) 원칙을 Phase 2 우선순위 결정에 반영

---

## 우선순위 레이어 — 실행 전략

업계 관행·코드 실측·플랫폼 특성·**운영 로드맵** 을 종합해 Phase 를 **3단계**로 분리한다.

| 레이어 | 구성 | 공수 | 무게 영향 | 실행 조건 (v4) |
|--------|------|------|----------|-------------------|
| **L1: 즉시 실행** | Phase 1 + 3 + 4 + 5(최소) | 4~5일 | 미미 | ✅ **2026-04-24 완료** |
| **L2: 사전 준비** | Phase 2a/2b/2c/2d (LLM Gateway + 부하 테스트) | 6~9일 | 중 (SPOF 전환, 부하 테스트로 완화) | 🟨 **100명 실 오픈 3주 내** 필수 (현재 단계) |
| **L3: 전환** | vLLM POC (별도 계획서) | 별도 | 대 | ⏸ 200+ 동시 또는 L2 튜닝 후 지속 초과 시 |

### 운영 로드맵 (v4 추가)

| 시점 | 전체 사용자 | 동시 사용 추정 | 대응 |
|------|-----------|--------------|------|
| 현재 (2026-04-24) | 15명 내부 테스트 | 2~3명 | ✅ L1 만으로 충분 |
| **~2026-05-15** (D-21) | 여전히 15명 | 2~3명 | 🟨 **L2 구축 + 부하 테스트 기간** |
| **~2026-05-15 오픈** | 100명+ 실 전체 | 피크 10~15명 추정 (업무 시간 몰림) | 운영 (L2 적용 상태, 대시보드 상시 모니터링) |
| 오픈 후 1~2주 | — | 실측 피크 확인 | Phase 2e 안정화, 롤백 플래그 제거 |

### L2/L3 지표 — 의미 재정의 (v4)

기존엔 "**L2 착수 판단용 트리거**" 였다면, v4 부터는:

- **L2 지표** = **오픈 후 상시 모니터링용 경계선**. 초기값은 Phase 2c 실 부하 테스트 결과로
  갱신됨 (현재 임계값은 업계 벤치 + 추정치 기반이며 튜닝 대상). 오픈 후 `fired` 지속 시
  Settings 값 재조정.
- **L3 지표** = **vLLM 전환 판단용 트리거**. L2 적용 후에도 지표 지속 초과 시에만 의미.

**L2 경계선 (초기값, Phase 2c 로 검증)**:
- `ollama_503_rate > 5 회/시간`
- `llm_p95_latency > 8s`
- `peak_concurrent_users > 7 명`
- `기능별 호출자가 느끼는 대기시간 불만` (정성적 피드백)

**L3 트리거 (Phase 2 적용 후에도)**:
- `ollama_503_rate > 10 회/시간` 2주 연속
- `peak_concurrent_users > 15 명` 지속
- `p99_latency > 20s`
- 조직 SLA 가 Ollama 한계를 명시적으로 초과

### 왜 L2 를 지금(v4) 착수하나

- v2~v3 당시엔 "실수요 없이 만들면 임계값 자의적 → 관찰 후 착수" 원칙이었음.
- v4 시점: **3주 내 실 오픈 확정** → 관찰 시간(1~2주)과 오픈 시점이 겹침. 오픈 후 착수 시
  사용자는 이미 체감 지연을 겪고 있음.
- **임계값 자의성 문제는 Phase 2c 부하 테스트로 해소** (개발 PC 스모크 + 회사 VM 실측).
- Phase 2 를 쪼개 **2a(부하 무관 개선)** 먼저 진행 후 **2b(Gateway 본체)** 착수하므로,
  2a 단계까지는 구조적 리스크(SPOF 전환) 도 발생하지 않음 — 점진 적용.
- **L3 (vLLM) 은 여전히 보류**. Ollama + L2 튜닝으로 100명/동시 10~15명은 감당 가능.

---

## Phase 1: Ollama 서버 설정 명시화 (L1 — 즉시)

> **가장 가성비 높은 조치.** 코드 변경 없이 env 로 체감 안정성 상승.

### 1-1. VRAM 예산 계산 (착수 전 필수 확인)

`num_parallel=N` 은 모델별 KV 캐시를 N배로 확장한다. 회사 리눅스 VM (가정: L40 48GB, 1장)
기준 대략적인 예산:

| 항목 | VRAM (N=2) | VRAM (N=4) |
|------|-----------|-----------|
| TRANSLATOR_MODEL (8B Q4, ctx 8K) | 5 GB | 5 GB |
| TRANSLATOR_MODEL KV (8K × N) | 2 GB | 4 GB |
| gemma3:4b (ctx 8K) | 3 GB | 3 GB |
| gemma3:4b KV (8K × N) | 1 GB | 2 GB |
| bge-m3 (임베딩, 인덱싱 시에만) | 2 GB | 2 GB |
| bge-reranker-v2-m3 | 1 GB | 1 GB |
| OS/CUDA 리저브 | 5 GB | 5 GB |
| **합계** | **19 GB** | **22 GB** |

실측 수치로 교체할 것(위 값은 보수적 추정). 확인 절차:
```bash
nvidia-smi --query-gpu=memory.used,memory.free --format=csv -l 2  # 30초 모니터
# 동시에: 번역 2개 + 채팅 3개 시나리오 재현 후 피크 측정
```

### 1-2. `.env.example` 권장값 (**보수 진입값**)

```bash
# ── Ollama 서버 튜닝 (동시성·큐) ──
# 1차 진입값 (VRAM 실측 전). 안전 마진 우선.
OLLAMA_NUM_PARALLEL=2             # 한 모델 내 동시 처리 슬롯 (KV 캐시 N배 주의)
OLLAMA_MAX_QUEUE=64               # 대기 요청 최대 수 (초과 시 503)
OLLAMA_KEEP_ALIVE=30m             # 모델 idle 유지 시간 (스왑 방지)
OLLAMA_MAX_LOADED_MODELS=2        # 동시 상주 모델 수 (TRANSLATOR + gemma3)
OLLAMA_FLASH_ATTENTION=1          # KV 메모리 절감 (지원 GPU만)

# 2차 상향값 — nvidia-smi 실측 후 여유 확인되면 적용:
# OLLAMA_NUM_PARALLEL=4
# OLLAMA_MAX_LOADED_MODELS=3
```

> **주의**: 이전 버전(v1)에서 권장한 `NUM_PARALLEL=4 / MAX_LOADED_MODELS=3` 은 VRAM
> 실측 없이 제안된 값이었음. v2 에서 보수화했고, 2차 상향은 실측 기반 조건부 적용.

### 1-3. `docker-compose.yml` Ollama 외부 참조 문서화

- 현재 Ollama 는 컨테이너 외부(호스트)에서 실행 중 → `docker-compose.yml` 에는 백엔드
  전달만 있음. Ollama 가 별도 서비스가 아님을 명시하는 주석 추가
- 회사 리눅스 VM 의 Ollama 기동 스크립트 / systemd unit 에 위 env 적용 지침을
  `docs/03-DOCKER-OPERATIONS.md` 에 섹션 추가

### 1-4. 스트리밍 슬롯 점유 특성 문서화

`num_parallel` 슬롯은 **스트림 종료까지 계속 점유**된다. 즉 num_parallel=2 환경에서
긴 Q&A 스트림 2 개가 30초간 응답 중이면, 그동안 다른 채팅은 대기. 이 특성은:

- Phase 1 만으로는 해결 불가 — 슬롯을 늘리거나(VRAM 한계) Phase 2 에서 용도별 슬롯 분리 필요
- Phase 5 지표에 `long_stream_blocking_events` 별도 추적 — L2 트리거 근거로 활용

### 1-5. 검증

- `curl http://ollama-host:11434/api/ps` 에 `expires_at` 이 30m 로 조정되는지
- 4 개 동시 요청(`seq 4 | xargs -P4 -I{} curl …`)에서 2 개 즉시 + 2 개 큐잉 확인
- `num_parallel=2` 상태에서 VRAM 여유가 5GB 이상인지 `nvidia-smi`
- 큐 초과 시 503 응답을 백엔드가 어떻게 포워딩하는지 로그 확인 (Phase 3 에서 처리)

---

## Phase 3: 503→429 변환 + 백오프 (L1 — 즉시, Phase 2 비의존)

> Ollama 가 이미 `MAX_QUEUE` 와 503 을 지원하므로, Gateway 없이도 단독 실행 가능.
> Phase 2 를 미루더라도 이 Phase 만으로 "큐 포화 시 사용자에게 적절한 피드백"을 확보한다.

### 3-1. 공통 재시도 정책

- `services/llm_retry.py` (또는 기존 모듈 내부 헬퍼) 신설
- 지수 백오프 (`delay = base * 2^n + jitter`, base=0.5s, 최대 3회)
- 대상 에러: `httpx.ConnectError`, `httpx.ReadTimeout`, Ollama 503(큐 포화), 5xx
- 대상 아님: 4xx(요청 문제), 타임아웃 구성상 너무 짧은 경우(`timeout<5s`)

### 3-2. 큐 포화 HTTP 응답 변환

- Ollama 503 → **FastAPI 공통 예외 핸들러**에서 **429 + `Retry-After: N`** 헤더로 변환
- `main.py` 에 핸들러 추가 (기존 `HTTPException` 흐름과 별개, 2~3곳 래퍼)

### 3-3. 적용 대상 (Phase 2 없이도 가능한 최소판)

| 호출부 | 변경 |
|--------|------|
| `llm_provider.OllamaProvider.generate/generate_stream` | httpx 예외 → `LLMQueueFullError` 매핑 |
| `query_rewriter.py` | 503 감지 시 기존 폴백 경로 사용 (이미 있음, 확장만) |
| `translator_service.ai_selection_query` | 503 → 사용자 친화적 오류 메시지 |
| `compare_service._call_ollama_classify` | 503 → 배치 지연 후 재시도 (기존 재시도 로직 확장) |

---

## Phase 4: 프론트엔드 RequestGuard 일관화 (L1 — 즉시)

### 4-1. `js/request-guard.js` 신설 (공용 유틸)

```javascript
window.RequestGuard = {
  run(key, factory, { timeoutMs = 0 } = {}) {
    // key 기반 inFlight Map — 동일 key 진행 중이면 reject 또는 기존 promise 재사용
    // AbortController 자동 생성 → factory(signal) 로 전달
    // timeoutMs > 0 이면 자동 abort
    // finally 에서 inFlight 해제
  },
  abort(key),
  isBusy(key),
};
```

### 4-2. 적용 대상

| 파일 | 현재 | 변경 |
|------|------|------|
| `js/ai-chat.js` | `AIChatState.isLoading` + 산발적 AbortController | RequestGuard.run('chat.rag', …) |
| `js/translator.js` | `_aiAbortController` 1개 변수 | RequestGuard.run('tr.selection', …) + `'tr.summary'` + `'tr.qa'` |
| `compare.html` | `validateState.isLoading` + 여러 `disabled` | RequestGuard.run('cmp.ai', …) |
| `index.html` 업로드·reindex | `reindexBtn.disabled` 수동 | RequestGuard.run('explorer.reindex', …) |

### 4-3. 429 공통 처리

- `js/toast.js` 에 `showRetryToast(secondsUntil)` 추가 — "AI 사용량이 많습니다. N초 후 자동
  재시도" + 카운트다운
- RequestGuard 안에서 429 응답 자동 감지 → `Retry-After` 만큼 대기 후 1회 자동 재시도

### 4-4. 페이지 이탈·탭 변경 시 abort

- `beforeunload` / Translator 문서 전환 / Explorer 섹션 변경 시 해당 key 의 스트림 강제
  abort — 서버 리소스 조기 해제

---

## Phase 5: 헬스·모니터링 지표 + 관리자 대시보드 패널 (L1 — 즉시)

> **설계 원칙**: "개발자가 주기적으로 `/api/health` 를 수동 확인"은 현실에서 작동하지
> 않는다. 관리자 대시보드(Plan-41/43)에 가시화하여 **누구든 접속만으로 현재 상태를
> 파악**할 수 있게 하고, 트리거 발동 시 **배너로 자동 알림**한다.

### 5-1. `/api/health` 최소 필드 추가

```json
{
  "ollama": "ok",
  "ollama_latency_ms": 42,
  "ollama_503_last_hour": 0
}
```
- 503 카운트는 Phase 3 의 예외 핸들러에서 인메모리 링버퍼로 집계
- 1시간 고정 윈도우, 타임스탬프 기반 자동 퇴거

### 5-2. `/api/metrics/ai-status` 신설 (트리거 판단용)

```json
{
  "indicators": {
    "p95_latency_ms": 1240,
    "ollama_503_per_hour": 0,
    "peak_concurrent_users_1h": 3,
    "active_streams": 1
  },
  "triggers": {
    "l2_status": "normal",        // normal | warning | fired
    "l2_fired_indicators": [],
    "l3_status": "normal",
    "l3_fired_indicators": []
  },
  "last_updated": "2026-04-24T10:30:00Z"
}
```

**트리거 상태 판정 규칙** (백엔드 인메모리):
- `normal` — 모든 지표가 임계값 이하
- `warning` — 임계값의 70% 이상 접근 (사전 경고)
- `fired` — 임계값 1주 연속 초과 (L2/L3 착수 조건 충족)

### 5-3. 지표 수집·판정 로직 (백엔드)

`services/ai_metrics.py` 신설:
- 인메모리 롤링 버퍼 (1시간 윈도우, 타임스탬프 기반 퇴거)
- `record_llm_call(purpose, duration_ms, status)` — Phase 3 의 재시도 핸들러·
  Ollama 호출부에서 훅
- `get_indicators()` → 4지표 + 트리거 상태 계산 (임계값의 70% → warning, 100% 1주 → fired)
- 1주 연속 판정은 SQLite `analytics_events` 테이블에 `ai_indicator_snapshot` 일별
  집계 저장 (Plan-41 계측 인프라 재사용, 별도 테이블 추가 없음)

### 5-4. 관리자 대시보드 — AI 동시성 상태 섹션

> **위치**: `admin.html` 의 관리자 대시보드 (Plan-41/43 의 `_renderDashboardHTML`).
> `launcher.html` 이 아니라 관리자 analytics 대시보드임에 유의.

#### 5-4-1. 삽입 위치 (기존 렌더 순서 보존)

Plan-43 에서 "건강 뱃지가 최상단 근처에 와야 운영 경고를 먼저 본다"는 원칙 확립. 같은 논리
로 AI 상태 섹션도 운영 영역에 배치:

```
0. ad-last-update-wrap
1. ad-summary (4 카드)
2. ad-health  ← Plan-43 상단 이동
3. ad-ai-status  ← 신규 삽입 (건강 뱃지 직후, 서브시스템 타일 직전)
4. ad-subsystem-grid (서브시스템 타일)
5. ad-vbar-chart (접속 추이)
...
```

`_renderDashboardHTML` 에 `html += _renderAIStatus(data.ai_status)` 한 줄 추가.

#### 5-4-2. 마크업 구조 (기존 디자인 언어 준수)

```html
<section class="ad-ai-status" role="region" aria-labelledby="ad-ai-title">
  <div class="ad-section-title" id="ad-ai-title">
    AI 동시성 상태
    <span class="ad-section-hint">(Ollama · 30초 갱신)</span>
    <span class="badge badge-success" id="ad-ai-overall" aria-live="polite">정상</span>
  </div>

  <div class="ad-ai-metrics">
    <div class="ad-ai-metric" data-state="ok">
      <div class="ad-ai-metric-label">p95 응답 지연</div>
      <div class="ad-ai-metric-value">1.24<span class="ad-ai-metric-unit">s</span></div>
      <div class="ad-ai-metric-threshold">임계 8.00s</div>
      <span class="badge badge-success" aria-label="정상">정상</span>
    </div>
    <!-- 503/h, 피크 동접 1h, 활성 스트림 3개 동일 구조 -->
  </div>

  <div class="ad-ai-footer">
    <span class="ad-ai-trigger-label">Phase 2 착수 조건:</span>
    <span class="ad-ai-trigger-status">미충족 <span class="ad-ai-trigger-hint">(안정 운영 중)</span></span>
  </div>
</section>
```

**설계 근거**:
- `.ad-section-title` / `.ad-section-hint` — 기존 섹션 패턴 재사용 (제목 톤 일관)
- `.badge .badge-success/warning/error` — CLAUDE.md 디자인 시스템 표의 공통 클래스 사용
  (새 이모지 색 규칙 만들지 않음, 색약 배려로 텍스트 라벨 동반)
- `data-state="ok|warning|fired"` — CSS 에서 좌측 보더·배경 톤 차등
- `aria-live="polite"` — 상태 뱃지가 바뀔 때 스크린리더 알림
- `role="region"` + `aria-labelledby` — 랜드마크 접근성

#### 5-4-3. CSS 신규 토큰 (analytics.css 확장)

```css
.ad-ai-status { background:var(--ad-bg-card); border:1px solid var(--ad-border);
                border-radius:var(--radius-md); padding:var(--space-lg);
                margin-bottom:var(--space-lg); }

.ad-ai-metrics { display:grid; grid-template-columns:repeat(4,1fr);
                 gap:var(--space-md); margin-top:var(--space-md); }

.ad-ai-metric { position:relative; padding:var(--space-md);
                border-left:3px solid var(--ad-success);
                background:color-mix(in oklab, var(--ad-success) 6%, transparent);
                border-radius:var(--radius-sm); }
.ad-ai-metric[data-state="warning"] { border-left-color:var(--ad-warning);
                background:color-mix(in oklab, var(--ad-warning) 8%, transparent); }
.ad-ai-metric[data-state="fired"]   { border-left-color:var(--ad-danger);
                background:color-mix(in oklab, var(--ad-danger) 10%, transparent); }

.ad-ai-metric-label     { font-size:.85rem; color:var(--ad-text-secondary); }
.ad-ai-metric-value     { font-size:1.75rem; font-weight:600; color:var(--ad-text);
                          line-height:1.1; margin-top:var(--space-xs); }
.ad-ai-metric-unit      { font-size:1rem; font-weight:400; color:var(--ad-text-secondary);
                          margin-left:2px; }
.ad-ai-metric-threshold { font-size:.75rem; color:var(--ad-text-secondary);
                          margin:var(--space-xs) 0; }

.ad-ai-footer { margin-top:var(--space-md); padding-top:var(--space-sm);
                border-top:1px dashed var(--ad-border);
                font-size:.85rem; color:var(--ad-text-secondary); }
.ad-ai-trigger-hint { color:color-mix(in oklab, var(--ad-text-secondary) 80%, transparent); }

/* 반응형 — Plan-41 step 11 기준 동일 break */
@media (max-width:960px) { .ad-ai-metrics { grid-template-columns:repeat(2,1fr); } }
@media (max-width:700px) { .ad-ai-metrics { grid-template-columns:1fr; } }
```

**주의사항**:
- `--ad-*` 네임스페이스 유지 (tokens.css 변수 경유 — 다크모드 자동)
- `color-mix(in oklab, ...)` 로 상태 계열 톤 생성 (기존 Plan-41 패턴)
- 하드코딩 색상 금지 (CLAUDE.md 준수)
- 신규 CSS 는 analytics.css 에 병합, 별도 파일 만들지 않음
- Plan-43 의 "타일 클릭 커서 제거" 원칙 준수 — 드릴다운 미구현 시 `cursor:default`

### 5-5. L2 트리거 발동 시 배너 알림 (최상단 스트립)

#### 5-5-1. 위치 및 노출 조건

- `ad-last-update-wrap` 바로 아래 (대시보드 최상단)
- `auth-admin` 역할에만 렌더 (`body.auth-admin` 가드)
- `triggers.l2_status === "fired"` 이고 localStorage `ad-ai-banner-dismissed` 미만료

#### 5-5-2. 마크업 (접근성 포함)

```html
<div class="ad-alert ad-alert-warning" role="alert" aria-live="assertive"
     data-banner="ai-l2-trigger">
  <span class="ad-alert-icon" aria-hidden="true">⚠</span>
  <div class="ad-alert-body">
    <strong class="ad-alert-title">AI 동시성 부담 증가</strong>
    <span class="ad-alert-desc">Phase 2(LLM Gateway) 착수 조건이 1주 연속
      충족되었습니다. 계획서 44 를 확인하세요.</span>
  </div>
  <div class="ad-alert-actions">
    <a class="btn btn-sm btn-secondary" href="#ad-ai-title">상세 지표로 이동</a>
    <button class="btn btn-sm btn-ghost" data-dismiss-banner aria-label="24시간 닫기">
      24시간 닫기
    </button>
  </div>
</div>
```

#### 5-5-3. CSS

```css
.ad-alert { display:flex; align-items:flex-start; gap:var(--space-md);
            padding:var(--space-md) var(--space-lg);
            border-radius:var(--radius-md);
            border:1px solid var(--ad-warning);
            background:color-mix(in oklab, var(--ad-warning) 12%, var(--ad-bg-card));
            margin-bottom:var(--space-md); }
.ad-alert-warning .ad-alert-icon { color:var(--ad-warning); font-size:1.25rem;
            flex-shrink:0; margin-top:2px; }
.ad-alert-body { flex:1; display:flex; flex-direction:column; gap:var(--space-xs); }
.ad-alert-title { color:var(--ad-text); }
.ad-alert-desc  { color:var(--ad-text-secondary); font-size:.9rem; }
.ad-alert-actions { display:flex; gap:var(--space-sm); flex-shrink:0; }

@media (max-width:700px) {
  .ad-alert { flex-direction:column; }
  .ad-alert-actions { width:100%; justify-content:flex-end; }
}
```

#### 5-5-4. Dismiss 동작

- `data-dismiss-banner` 클릭 → `localStorage.setItem('ad-ai-banner-dismissed',
  Date.now() + 24*3600*1000)`, 배너 제거
- 30초 자동 갱신 사이클에서도 만료되지 않았으면 재노출 안 함
- 만료 후 `fired` 상태 지속 시 다시 노출

### 5-6. L2 착수 시 패널 확장

Gateway 도입되면 `ad-ai-metrics` 하단에 **두 번째 그리드** 추가:
- Gateway 슬롯 사용률 바 (`active / max_concurrent`)
- 대기열 길이 (`queue_length / queue_max`)
- 용도별 호출 빈도 sparkline (chat / summary / qa_stream / classify)
- 429 발생률 (자동 재시도 성공/실패 구분 도넛)
- 공통 스타일: 기존 `.ad-tile-spark` / `.ad-hbar` 재사용

---

## Phase 2: LLM Gateway (L2 — 사전 준비, 100명 오픈 3주 내 필수)

> ✅ **v4 전환**: 기존의 "트리거 발동 후 착수" 원칙은 100명 오픈 일정(3주 내) 과 맞지 않음.
> Phase 2 를 **2a (부하 무관) → 2b (Gateway 본체) → 2c (부하 테스트) → 2d (대시보드 확장)
> → 2e (안정화)** 로 쪼개 점진 적용. 임계값 자의성 문제는 Phase 2c 부하 테스트로 해소.

### 주차별 타임라인

| 주차 | 목표 | 결과물 |
|------|------|--------|
| Week 1 전반 (~2일) | Phase 2a 부하 무관 개선 | httpx 싱글턴, ai_summary 정상화, query_rewriter async |
| Week 1 후반 (~3~5일) | Phase 2b Gateway 본체 | llm_gateway.py, 호출부 이식, Settings 연동, 롤백 플래그 |
| Week 2 전반 (~1.5일) | Phase 2c 부하 테스트 | 개발 PC 스모크 → 회사 VM 실측 → 임계값 확정 |
| Week 2 후반 (~반나절) | Phase 2d 대시보드 확장 | .ad-ai-status 하단 Gateway 2차 그리드 |
| Week 3 | **100명 실 오픈** + 모니터링 | 실시간 대시보드 감시 + 필요 시 튜닝 조정 |
| Week 3 이후 | Phase 2e 안정화 | 롤백 플래그 제거, backlog 이관 |

### 2-0. Phase 2 의 가치 (v4)

Phase 2 의 가치는 사용자 규모에 따라 달라진다. 100명 규모 대비:

- ✅ **`httpx.AsyncClient` 싱글턴 + 연결 풀** — TCP 재사용으로 동시 10+명에서 백엔드 부하 감소
- ✅ **스트림 전용 슬롯 분리** — `num_parallel=2` 환경에서 긴 Q&A 스트림 2개로 짧은 채팅이 굶는 문제 해소 (100명 규모 체감 큼)
- ✅ **용도별 weight / 우선순위** — Ollama FIFO 큐의 평등 처리를 interactive 우선으로 전환
- ✅ **앱 레이어 Semaphore + MAX_QUEUE** — Ollama 도달 전 조기 차단, 429+Retry-After 로 사용자 친화
- ✅ **관측 통합** — 대시보드 지표 신뢰도 향상
- ✅ **ai_summary.py 싱글턴 우회 제거** — 이미 식별된 버그성 패턴 정상화 (Phase 2a 에서 선행)

### 2-1. `backend/services/llm_gateway.py` 신설

역할:
- 모든 Ollama / OpenAI-compat 호출의 **유일한 진입점**
- 전역 `asyncio.Semaphore` 로 동시 호출 수 제한 (`LLM_GATEWAY_MAX_CONCURRENT`, 기본=Ollama NUM_PARALLEL 과 연동)
- 대기열 길이 제한 (`LLM_GATEWAY_MAX_QUEUE`) — 초과 시 `LLMQueueFullError` → 429
- `httpx.AsyncClient` 싱글턴 (`Limits(max_connections=50, max_keepalive=20)`)
- **스트림 전용 슬롯 풀** (`LLM_GATEWAY_STREAM_SLOTS`, 별도) — 단발 호출과 분리
- 용도별 weight: translation=2, summary=2, chat=1, classify=1, rewrite=1, qa_stream=1(스트림 풀)
- 큐 위치·진입 시각 추적 (사용자에게 "N번째 대기" 표시용)

공개 API (드래프트):
```python
async def llm_generate(prompt, *, system=None, purpose="chat", **opts) -> str: ...
def llm_stream(prompt, *, system=None, purpose="qa_stream", **opts) -> AsyncIterator[str]: ...
def get_queue_position(ticket_id) -> int | None: ...
async def shutdown(): ...  # 진행 중 호출 대기 → 풀 정리
```

### 2-2. 기존 호출부 이식

| 파일 | 변경 |
|------|------|
| `llm_provider.py` | `OllamaProvider.generate/generate_stream` 내부를 `llm_gateway` 클라이언트 사용으로 교체 (외부 API 유지) |
| `ai_summary.py:239, 294` | `OllamaProvider()` 직접 생성 제거 → `llm_generate(prompt, purpose="summary")` |
| `query_rewriter.py:85-94` | 동기 `requests.post` → `await llm_generate(prompt, purpose="rewrite", timeout=15)` |
| `translator_service.py:683-696` | `ai_selection_query` 동기 `requests.post` → `await llm_generate(...)`; 상위 래퍼를 async 로 승격 |
| `compare_service.py:789-815` | `httpx.AsyncClient()` 매 호출 → `llm_generate(..., purpose="classify")` |
| `notebook_chat.py:175-178` | `provider.generate_stream` → `llm_stream(..., purpose="qa_stream")` |
| `translator_service.py` PMT | 외부 프로세스(subprocess)라 Gateway 우회, 대신 **Semaphore 공유 연동**(아래 2-3) |

### 2-3. Semaphore 구조 재설계

- 기존 `_translation_semaphore (4)` 를 Gateway 의 `purpose="translation"` 슬롯(weight=2) 로
  재구현 — GPU 예약을 Gateway 가 일원화
- 문서당 1개 제약은 **상위 레이어(translator_service)** 에 유지 — UX 계약 보존
- 런타임 설정 변경 가능, `settings_service.apply_to_config` 연동
- Semaphore 재생성 시 "기존 대기 요청은 새 한도로 흡수" 정책 명시

### 2-4. 후진 호환·롤백

- `LLM_GATEWAY_ENABLED=false` 환경변수로 **전체 우회 가능** (기존 경로로 폴백)
- 기본값 `true` 는 Phase 2 완료 후 **1주 관찰** 뒤 확정
- **롤백 플래그 제거 기한**: 2e 단계에서 운영 안정 확인 후 2 릴리즈 이내 (CLAUDE.md 의
  "죽은 호환 코드 유지 금지" 준수). 이 기한을 backlog.md 에 이관 항목으로 기록.

### 2-5. Phase 2c 부하 테스트 — 용도 분리 (v4 신설)

일반 개발 관행상 부하 테스트는 Staging 환경에서 수행하는 것이 정석이지만, 우리 환경엔
별도 Staging 이 없다 (개발 PC ↔ 회사 VM). 그래서 **용도를 엄격 분리**:

#### 2c-1. 개발 PC 스모크 (버그 사냥용)

- **도구**: `locust` (Python, 폐쇄망 설치 가능) 또는 간단 `aiohttp` 스크립트
- **대상 엔드포인트**: 전 LLM 경유 API + Gateway 내부 경로
- **시나리오**:
  - 100 가짜 사용자가 동시에 채팅/요약/번역/분류 무작위 호출 (60초간)
  - LLM 응답을 mock (또는 `time.sleep(randint(500, 3000))` delay) 으로 대체 — **GPU 없이 실행**
- **검증 목표 (성능 숫자 아님)**:
  - Semaphore deadlock 발생하지 않는가
  - 롤백 플래그(`LLM_GATEWAY_ENABLED`) 전환 시 인플라이트 요청 정상 처리되는가
  - 메모리 / asyncio Task 누수 없는가 (`htop`, Python `tracemalloc`)
  - 429 응답 + `Retry-After` 형식 정확한가
  - 프론트 RequestGuard 가 실제 429 수신 시 카운트다운·자동 재시도 동작하는가
- **소요**: 2~3시간
- **산출물**: `workbench/reports/plan-44-phase2c-smoke-<ts>.md`

#### 2c-2. 회사 VM 실 로드 (숫자 튜닝용)

- **도구**: locust (VM 에 사전 설치) — 운영자 협조 필요
- **대상**: 실 Ollama + GPU (L40 48GB), L1 적용된 상태에서 L2 추가 후 비교
- **시나리오 (단계별)**:
  - ① 5명 동시 — baseline p95 확인
  - ② 20명 동시 (피크 추정치) — Semaphore·큐 거동 관찰
  - ③ 50명 동시 (상한 테스트) — 한계점·회복 시간 확인
- **측정 지표**:
  - p95 / p99 응답 시간 (기능별: 채팅·요약·번역·분류)
  - `nvidia-smi` VRAM 피크 사용량 (`num_parallel=2` / `=4` 두 시나리오)
  - Ollama 큐 대기 시간 분포
  - 429 발생률 + 재시도 성공률
- **결과 활용**:
  - `LLM_GATEWAY_MAX_CONCURRENT` / `MAX_QUEUE` / `STREAM_SLOTS` **초기값 확정**
  - 대시보드 L2 경계선 (현재 `p95_latency_ms>8000` 등) 현실화
  - 필요 시 `OLLAMA_NUM_PARALLEL` 2차 상향 (2→4) 판단
- **소요**: 반나절 ~ 1일 (VM 예약·설치 포함)
- **산출물**: `workbench/reports/plan-44-phase2c-vm-load-<ts>.md` + 수치 기반 Settings 권장값

### 2-6. Phase 2e 오픈 후 안정화 (v4 신설)

- 실 오픈 후 1주: 관리자 대시보드 매일 점검, `fired` 상태 발생 시 Settings 즉시 조정
- 오픈 후 2주: 피크 사용 패턴 안정화 확인 → `LLM_GATEWAY_ENABLED=true` 확정
- 오픈 후 3~4주: 롤백 경로(`=false`) 제거 커밋, `backlog.md` 에서 해당 항목 정리
- L3 (vLLM) 판단 보류 — L2 튜닝으로 충분한지 2~4주 관찰 후 결정

---

## 리스크 및 고려사항

### L1 범위 리스크

| 리스크 | 완화 |
|--------|------|
| `num_parallel=2` 가 실제 부하에 부족 (대기 체감) | Phase 5 지표로 감지, 2차 상향 조건부 적용 |
| VRAM 실측과 추정값 괴리 | 1-1 의 `nvidia-smi` 모니터링 선행, 실값으로 env 확정 |
| 프론트 RequestGuard 도입 중 UX 회귀 | 서브시스템별 순차 마이그레이션, 각 단계에서 수동 QA |
| 503 카운트 롤링 버퍼 메모리 성장 | 1시간 고정 윈도우, 타임스탬프 기반 자동 퇴거 |

### L2 도입 시 발생하는 구조적 리스크 (Phase 2 착수 전 재검토)

| 리스크 | 설명 | 완화 |
|--------|------|------|
| **실패 모드 전환 (fan-out → SPOF)** | 현재: 채팅 죽어도 번역 살아있음. Gateway 후: Gateway 버그면 전체 AI 먹통 | `LLM_GATEWAY_ENABLED=false` 즉시 롤백, health 체크에 Gateway 자체 헬스 필드 |
| **Ollama 진화 중복·간섭** | Ollama 가 native priority queue 넣으면 우리 Gateway 로직이 잉여·간섭 | Gateway 로직 최소화 (Ollama 에 맡길 수 있는 건 맡김), 릴리스 노트 추적 |
| **스트림 취소 부정확** | 프론트 abort → 백엔드 Gateway 는 Ollama 생성 중단 보장 X | HTTP 연결 종료에 의존, 로그로 "취소 후에도 토큰 생성" 이벤트 추적 |
| **동시성 버그의 지연 발현** | Semaphore deadlock, inFlight 맵 누수 등은 1~2 달 후 희귀 케이스로 터짐 | 부하 테스트 인프라 별도 구축 (locust 또는 커스텀), 최소 2주 shadow 운영 |
| **런타임 설정 변경 복잡도 증가** | Semaphore 는 생성 시 한도 고정 → 런타임 변경 시 "기존 대기 요청 처리" 설계 필요 | 2-3 의 정책 명시, Settings GUI 에 "변경 후 N초 반영" 안내 |
| **로그 볼륨 폭증** | Gateway 진입/퇴장 로그 분당 수백 줄 | Plan-22 RotatingFileHandler 정책 재조정, 샘플링(1/N) 옵션 |
| **롤백 플래그 부채** | `LLM_GATEWAY_ENABLED` 가 장기 잔존하면 두 코드 경로 공존 (CLAUDE.md 위배) | 2-4 의 제거 기한 명시, backlog 이관 |

### 외부 subprocess 와의 경계

- pdf2zh / babeldoc 등 외부 프로세스는 Gateway 바깥 → Ollama 직접 타격
- Phase 1 의 `OLLAMA_MAX_QUEUE` 가 서버 측에서 최종 방어선 역할
- 향후 외부 프로세스 호출도 Ollama 로 직행하지 않고 Gateway 경유하도록 리팩토링 가능
  (범위 외, Plan-44 후속 후보)

---

## 성공 기준

### L1 완료 기준 — ✅ 전체 달성 (2026-04-24)
- [x] Ollama env 5종 `.env.example` + 운영 가이드 반영 (NUM_PARALLEL=2, MAX_QUEUE=64, KEEP_ALIVE=30m, MAX_LOADED_MODELS=2, FLASH_ATTENTION=1)
- [x] `nvidia-smi` 실측 절차 docs 에 명시 (실제 실측은 운영자 영역)
- [x] 공통 예외 핸들러로 Ollama 503 → HTTP 429 + `Retry-After` 변환
- [x] `js/request-guard.js` 배포, 서브시스템 4곳 이식
- [x] 429 응답 시 프론트 자동 재시도 + 카운트다운 토스트 작동
- [x] `/api/health` 에 `ollama_latency_ms`, `ollama_503_last_hour` 필드 노출
- [x] 관리자 대시보드 "AI 동시성 상태" 섹션 + L2 트리거 배너 (Playwright 검증 완료)
- [x] 기존 기능 회귀 0건 (code-reviewer + /review-ui + /simplify 통과)

### L2 착수 기준 (v4) — 운영 일정 기반
- [x] 실 오픈 예정일(D-21) 확정 — **2026-05-15 전후 100명 오픈**
- [ ] Phase 2a 부하 무관 개선 완료
- [ ] Phase 2b Gateway 본체 완료
- [ ] Phase 2c 부하 테스트 완료 (개발 PC 스모크 + 회사 VM 실 로드)

### L2 완료 기준 (오픈 전 충족 필수)
- [ ] 개발 PC 스모크 테스트 통과 — 100 동시 가짜 요청에서 deadlock/누수/예외 0건
- [ ] 회사 VM 실 로드 테스트 통과 — 20명 동시(피크 추정) 에서 p95 ≤ 8s, 50명 상한 테스트에서 graceful degradation (429 재시도로 복구)
- [ ] VRAM 피크 여유 5GB 이상 (`nvidia-smi` 실측)
- [ ] 스트림 전용 슬롯 분리로 "긴 스트림 중 짧은 채팅 기아" 재현 없음
- [ ] `/api/metrics/ai-status` 에 Gateway 상태(슬롯/큐) 노출, 대시보드에 2차 그리드 표시
- [ ] `LLM_GATEWAY_ENABLED=false` 로 롤백 시 L1 상태 기능 100% 복원
- [ ] `ai_summary.py` 의 OllamaProvider() 직접 생성 0곳 (Phase 2a 완료)
- [ ] 기존 기능 회귀 0건 (L1 체크리스트 재검증)

### 오픈 후 (Phase 2e)
- [ ] 1주 관찰 — 대시보드 `fired` 발생률, 사용자 피드백 수집
- [ ] 2주 관찰 — 롤백 플래그 제거 승인 판단
- [ ] 4주 관찰 — L3 (vLLM) 착수 필요 여부 결정

---

## 후속 이관 후보 (L3 및 범위 외)

- **vLLM / TGI 전환 POC** — 상기 L3 트리거 지표 초과 시 별도 계획서 기동.
  PagedAttention·continuous batching 기반으로 H100 80GB 에서 Llama 3.1 8B 180+ 동접
  지원 가능(Red Hat 벤치). 단, 폐쇄망 + 모델 호환성 + 운영자 학습 비용 사전 평가 필요.
- **사용자별 token bucket** — 현재는 인스턴스 단위 제한만. 다수 사용자 시 형평성 문제
  발생하면 `userId` 기반 leaky bucket 추가
- **요청 우선순위 큐 고도화** — Gateway 의 weight 를 priority queue 로 승격
- **회로 차단기(Circuit Breaker)** — Ollama 장애 시 일정 시간 전체 AI 기능 비활성화 +
  사용자 친화적 안내 배너
- **외부 프로세스(pdf2zh/babeldoc) 의 Gateway 경유** — GPU 사용 일원화

## 참고 파일

- `backend/services/translator_service.py:21-29, 683-696, 917-950, 1300-1337, 1832-1876`
- `backend/services/llm_provider.py:41-121, 227-266`
- `backend/services/ai_summary.py:239, 294`
- `backend/services/notebook_chat.py:14, 175-178`
- `backend/services/query_rewriter.py:84-107`
- `backend/services/embedding_client.py:99-147`
- `backend/services/compare_service.py:768, 789-879`
- `backend/services/conversation.py:42-77`
- `backend/main.py:241-263`
- `js/ai-chat.js:8, 327-357, 474-478, 517-521, 1227-1273`
- `js/translator.js:1994, 2034-2035`
- `compare.html:2298-2336, 5332-5393, 5864-5959`

## 관련 계획서·메모

- `done-22-operational-stability.md` — 원자 쓰기·shutdown·로깅·헬스체크 기반 마련
- `done-40-embedding-backend-split.md` — 임베딩 용도별 분리 (이번 계획과 상보적)
- `done-41-dashboard-platform-wide.md` / `done-43-dashboard-ux-polish.md` — Phase 5 지표를
  노출할 대시보드 인프라
- `memory/feedback_docker_verification.md` — HTTP 200 만으로 불충분한 검증 원칙 (Phase 1·5 검증 시 유의)

## 변경 이력

- **v1 (2026-04-24)**: 초안. 5 Phase 일괄 실행 전제.
- **v2 (2026-04-24)**: 운영 실조사 반영.
  - Ollama 본질적 특성 섹션 추가 (공식 FAQ + Red Hat 벤치)
  - Phase 1 권장값 보수화 (`NUM_PARALLEL=4→2`, `MAX_LOADED_MODELS=3→2`, `MAX_QUEUE=128→64`, `FLASH_ATTENTION=1` 추가)
  - VRAM 예산 계산 섹션 신설
  - 스트리밍 슬롯 점유 특성 명시
  - 우선순위 레이어 (L1/L2/L3) 도입 — Phase 2 를 조건부로 격하
  - L2/L3 트리거 지표 정의
  - Phase 2 가치 재정의 (병목 해소 → 스트림 슬롯 분리·관측 통합 중심)
  - 구조적 리스크 섹션 확장 (fan-out→SPOF, Ollama 진화, 동시성 버그 지연 발현 등 7종)
  - vLLM 이관을 "범위 외"에서 "L3 트리거"로 격상
- **v3 (2026-04-24)**: 추적·가시화·디자인 시스템 반영.
  - 최상단 "진행 현황 대시보드" 신설 (L1 17 / L2 8 / L3 3, 체크박스 기반)
  - 트리거 지표를 관리자 수동 확인 → **관리자 analytics 대시보드 가시화**로 전환
  - Phase 5 확장: `admin.html` (`_renderDashboardHTML`)에 `.ad-ai-status` 섹션 + `.ad-alert` 배너
  - 디자인 시스템 준수 명세 — `--ad-*` 토큰 재사용, `color-mix(in oklab, ...)`, `.badge`/`.btn` 공통 컴포넌트, 반응형 3단계(<960/<700), 다크모드 자동, `role`/`aria-*` 접근성
  - 백엔드 지표 계측을 `services/ai_metrics.py` + Plan-41 `analytics_events` 재사용으로 설계 (별도 테이블 추가 없음)
  - Phase 5 섹션 번호 재정렬 (기반→UI→알림 순서: 5-1 health / 5-2 metrics API / 5-3 백엔드 지표 / 5-4 대시보드 섹션 / 5-5 배너 / 5-6 L2 확장)
- **v4 (2026-04-24)**: L1 완료 + 운영 로드맵 반영 → L2 사전 착수 전환.
  - **L1 전체 완료** (17/17, 커밋 9건, Playwright 검증 완료)
  - 운영 로드맵 공개: 현재 15명 내부 테스트 → **2026-05-15 전후 100명 실 오픈**. 피크 동시 사용 10~15명 추정
  - L2 "트리거 발동 후 착수" 원칙 폐기 — 관찰 기간과 오픈 시점이 겹침. **오픈 전 선제 구축 + 부하 테스트 기반 튜닝**으로 전환
  - Phase 2 를 **2a/2b/2c/2d/2e** 로 쪼갬:
    - 2a (부하 무관 선행) — httpx 싱글턴, ai_summary 싱글턴 우회 정상화, query_rewriter async 전환 (~2일)
    - 2b (Gateway 본체) — llm_gateway.py, 호출부 이식, Settings GUI, 롤백 플래그 (~3~5일)
    - 2c (부하 테스트) — **용도 분리 신설**: 개발 PC 스모크(버그 사냥) + 회사 VM 실 로드(숫자 튜닝)
    - 2d (대시보드 Gateway 2차 그리드)
    - 2e (오픈 후 안정화, 롤백 플래그 제거)
  - L2 총 항목 8 → 13 (부하 테스트 3건 + 안정화 1건 + 2a 3건 추가, 2b 내부 정리)
  - L2 지표 의미 재정의: "착수 판단용 트리거" → "오픈 후 상시 모니터링 경계선" (초기값은 2c 실측으로 갱신)
  - L3 (vLLM) 은 여전히 보류 — Ollama+L2 튜닝으로 100명/동시 10~15명 감당 가능 전제. 200+ 동시 또는 L2 튜닝 후 지표 지속 초과 시에만 착수
  - 성공 기준 섹션을 L1 달성 표시 + L2 착수/완료 기준 재작성 + 오픈 후 운영 기준 신설
  - 주차별 타임라인 표 추가 (Phase 2 본문 상단)
