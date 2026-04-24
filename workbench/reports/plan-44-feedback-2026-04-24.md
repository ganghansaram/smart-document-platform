# Plan-44 실행 피드백 — Ollama 동시성·안정성 강화 L1

> 실행일 2026-04-24 · 실행자 Claude (/plan-execute) · 대상 계획서 `workbench/plans/44-ollama-concurrency-hardening.md`
> 범위: L1 (Phase 1 + 3 + 4 + 5), L2·L3 는 트리거 지표 수집 후 판단

## 요약

- 완료 Step: **17 / 17** (L1 전체) ✅
- 변경 파일: **19개** (신규 3 + 수정 16)
- 커밋: **6개** (fb13951, 2036f6b, a220f39, f5df1ec, 1d69ded, 7c296de)
- Critical 이슈: **2건 → 모두 수정 완료**
- Warning 이슈: **3건 → 내 추가분 1건 수정, 기존 코드 2건 기록만**
- Suggestion: **3건 → 본 보고서에 기재**

## 구현 결과

| Phase | 상태 | 커밋 | 주요 변경 |
|-------|------|------|----------|
| 1 · Ollama 서버 설정 | ✅ | fb13951 | `.env.example` 권장값 블록, `docker-compose.yml` 주석, `docs/03-DOCKER-OPERATIONS.md §2-2-A` 신설 (systemd override, VRAM 예산, 스트리밍 슬롯 점유 특성, 검증 스크립트 4종) |
| 3 · 503→429 + 백오프 | ✅ | 2036f6b | `services/llm_retry.py` 신설 (LLMQueueFullError + async/sync retry), `main.py` 예외 핸들러, 호출부 5곳 적용 |
| 5-백엔드 · 지표 수집 | ✅ | a220f39 | `services/ai_metrics.py` 신설, `/api/health` 확장, `/api/metrics/ai-status` 신설, lifespan snapshot_loop |
| 4 · 프론트 RequestGuard | ✅ | f5df1ec | `js/request-guard.js` 신설, `showRetryToast`, LLM fetch 4곳 이식, HTML 4파일 script 로드 |
| 5-UI · 대시보드 섹션 | ✅ | 1d69ded | `_renderAIStatus`, `_renderL2Banner`, analytics.css `.ad-ai-*`/`.ad-alert*` 스타일 |
| 코드 리뷰 수정 | ✅ | 7c296de | ai-status 인증, retry try/finally, 리스너 중복 바인딩 방어 |

## 검증 결과

### 코드 품질 (code-reviewer)

**Critical — 수정 완료**
1. ✅ `/api/metrics/ai-status` 인증 누락 → `Depends(require_admin)` 추가 (7c296de)
2. ✅ `llm_retry` CancelledError 경로에서 `_record` 누락 → try/finally + recorded 플래그 (7c296de)

**Warning — 1건 수정, 2건 기록**
1. 🟡 `css/analytics.css:466` 하드코딩 색상 — **Plan-41 기존 코드**, 본 범위 외 (별도 이슈로 남김)
2. 🟡 `--ad-text` 로컬 토큰 중복 정의 — **Plan-41 기존 설계**, 본 범위 외
3. ✅ `analytics.js` dismiss 리스너 중복 바인딩 방어 → `_adBannerDismissBound` 플래그 (7c296de)

**Suggestion — 후속 개선 후보**
1. `ai_metrics.py:81-84` p95 계산 fallback 명료화 (기능 무영향, 코드 가독성)
2. `request-guard.js:33` 429 대기 시작 전 signal.aborted 선확인 (조기 중단)
3. `ai_metrics.py` lock 획득 순서 주석 추가 — **커밋에 주석 반영 완료**

### 자가검증 (서버 미기동)

- ✅ 모든 Python 모듈 import 성공 (llm_retry, ai_metrics, llm_provider, translator_service, compare_service, query_rewriter, main, api.analytics)
- ✅ FastAPI 라우트 등록 확인: `/api/health`, `/api/metrics/ai-status`, `/api/analytics/dashboard`
- ✅ `LLMQueueFullError` 전용 예외 핸들러 등록 확인
- ✅ `ai-status` 엔드포인트 `require_admin` dependency 등록 확인
- ✅ `ai_metrics.get_ai_status()` 실행 — p95 7500ms 입력 시 `l2_status='warning'` (지표 `p95_latency_ms` 임계값 70% 초과) 판정 정상
- ✅ JS syntax 검사: `request-guard.js`, `toast.js`, `analytics.js` 모두 통과

### 브라우저 검증 (Playwright) — 미수행

개발 서버 기동이 필요하므로 **사용자 환경에서 수동 검증** 요망:

```bash
cd backend && python main.py              # 백엔드 (port 8000)
python -m http.server 8080                # 프론트 (port 8080)
# → admin.html 접속, 로그인(testbot/test1234) → 관리자 대시보드
# → 확인: "AI 동시성 상태" 섹션이 "시스템 건강" 뒤에 노출되는지
# → 확인: 라이트/다크 테마 전환 시 색상 자동 반영
# → 확인: 브라우저 폭 960/700 축소 시 4열→2열→1열 전환
# → 확인: (선택) force LLM 호출 많이 하여 l2_status='fired' 진입 시 상단 배너 표시
```

### 회귀 영향 스팟체크

계획서 "건드리지 않는 곳" 샘플 확인:

- ✅ Translator 페이지 번역 Semaphore(4) — `translator_service.py:21-29` 변경 없음
- ✅ Embedding 호출 경로 (`embedding_client.py`) — Phase 3 retry 우회, Phase 40 설계 보존
- ✅ Plan-41 analytics_events 스키마 — 신규 테이블 0건, 기존 `event_type` 확장만
- ✅ Plan-41 `_renderHealthBadges` / `_renderSubsystemTiles` 렌더 순서 변경 없음 (AI 상태는 그 사이에 삽입)

## 사용자 관점 피드백

**긍정**
- 4-5일 예상 대비 집중 작업으로 당일 완료. Phase 2(LLM Gateway) 진입 없이도 체감 운영 안정성 확보
- 관리자 대시보드 1개 섹션으로 "Ollama 상태 + 트리거" 를 한 번에 파악 가능해짐
- `.env.example` + `docs/03-DOCKER-OPERATIONS.md` 의 VRAM 예산 표가 운영자 의사결정에 바로 쓸 수 있는 수준

**우려**
- **실제 운영 데이터 없이 임계값(p95 8s, 503 5/h, 동접 7명) 설정**. 초기 튜닝 필요 가능성 — 1~2주 관찰 후 재조정
- **Phase 4 RequestGuard 가 LLM fetch 4곳에만 적용**. 나머지 Ollama 간접 호출(인덱싱/임베딩)은 429 경로 밖 — 현재 설계상 큰 영향 없지만 확산 여지
- **스트림 중간 끊김 시 재시도 불가** — 이는 의도적 결정 (토큰 파손 방지), 계획서에 명시됨

**개선 제안**
- Phase 2 트리거 지표가 1주 동안 모두 normal 이면 계획서 캐비닛 이관 + `backlog.md` 로 격하 고려
- `ai_metrics` 스냅샷이 `analytics_events` 에 쌓이기 시작하면 대시보드에 "최근 7일 지표 추이" 그래프 추가 가치 있음 (L2 착수 시 Phase 5 확장 일부)

## 웹디자인 전문가 관점 피드백

**시각적 위계**
- AI 상태 섹션이 `.ad-health` 뒤·서브시스템 타일 앞에 배치되어 Plan-43 의 "운영 경고 최상단" 원칙 준수
- 4개 지표 카드의 `.ad-ai-metric-value` 크기(1.6rem)가 서브시스템 타일(`.ad-tile-num`, 2rem) 보다 약간 작아 **위계 관계 적절** (종합 대시보드 → 서브시스템 → AI 지표)

**인터랙션**
- `.ad-ai-metric[data-state]` 좌측 3px 보더 + 배경 톤으로 상태 즉각 인식 (색약 배려: `.badge` 의 "정상/주의/발동" 텍스트 라벨 병행)
- L2 트리거 배너는 `role="alert"` + `aria-live="assertive"` 로 스크린리더가 즉시 안내
- Dismiss 버튼은 `.btn-ghost` 스타일이라 과도하게 강조되지 않음 — 배너 주액션(상세 지표 이동) 우선

**다크모드**
- `css/analytics.css` 의 `--ad-*` 토큰이 라이트/다크 분기에서 자동 전환되도록 설계됨 (tokens.css 경유)
- `color-mix(in oklab, ...)` 사용으로 다크 배경에서도 상태 틴트가 자연스러움

**접근성**
- ✅ `role="region"` + `aria-labelledby` — AI 상태 섹션 랜드마크
- ✅ `aria-live="polite"` / `"assertive"` — 상태 뱃지/배너 실시간 알림
- ✅ `aria-hidden="true"` — 장식 이모지(⚠)
- ✅ `aria-label` — dismiss 버튼 "24시간 닫기"
- 💡 **보완 제안**: `.ad-ai-metric` 에 `aria-describedby` 로 "임계 XXX" 연결하면 더 완전

## 잔여·후속 제안

- [ ] 운영 서버 기동 후 Playwright 시각 검증 (사용자 수동)
- [ ] 1주 관찰 — 관리자 대시보드에서 지표 실측값 확인, 임계값 재조정 여지 판단
- [ ] L2 트리거 발동 시 자동 Slack/이메일 알림 (현재는 대시보드 접속 시에만 확인 가능) — Phase 5 확장 시 고려
- [ ] `ai_metrics.save_hourly_snapshot` 이 쌓은 이력으로 "최근 7일 추이 sparkline" 추가 (L2 착수 시)
- [ ] Translator 페이지 번역 같이 서버 내부 Ollama 접근도 `record_llm_call` 훅에 넣으면 더 정확한 지표 (현재는 HTTP 요청 경유만 계측)
- [ ] Plan-41 `.ad-btn-danger:hover` 하드코딩 색상 — 별도 작은 수정 계획으로 처리

## 교훈 (memory 후보)

1. **"운영 지표 엔드포인트는 기본 admin 가드"** — code-reviewer 첫 지적. 유틸 엔드포인트라도 노출 기본값은 admin. 추후 `/api/metrics/*` 컨벤션 문서화 권장
2. **재시도 래퍼는 반드시 try/finally** — CancelledError 는 `except Exception` 에 안 잡히므로 계측 누락. 기본 패턴으로 기억
3. **대시보드 클릭 리스너는 document 레벨 플래그 가드** — IIFE 가 여러 HTML 에서 로드될 가능성 있는 공용 JS 는 중복 바인딩 위험

## 커밋 제안 — 이미 수행 완료

```
fb13951  문서 [Plan-44/P1] Ollama 동시성 튜닝 가이드 추가
2036f6b  추가 [Plan-44/P3] Ollama 503 → HTTP 429 변환 + 지수 백오프 재시도
a220f39  추가 [Plan-44/P5 백엔드] AI 지표 수집·판정 + /api/metrics/ai-status
f5df1ec  추가 [Plan-44/P4] 프론트 RequestGuard — 429 자동 재시도 + 카운트다운 토스트
1d69ded  추가 [Plan-44/P5 UI] 관리자 대시보드 AI 동시성 상태 섹션 + L2 트리거 배너
7c296de  버그 [Plan-44] code-reviewer 지적 Critical 2건 + Warning 1건 수정
```

## 결론

**L1 완료. 계획서 진행 대시보드 17/17 ✅.** Phase 2(LLM Gateway) 는 **트리거 지표 발동 전까지 착수 금지** 상태로 캐비닛 보관. 1~2주 관찰 후 `l2_status='fired'` 발동 시 재검토.
