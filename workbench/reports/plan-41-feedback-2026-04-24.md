# Plan-41 실행 피드백 — 대시보드 플랫폼 전체 관점 재설계

> 실행일 2026-04-24 · 실행자 Claude (/plan-execute) · 대상 계획서 `workbench/plans/41-dashboard-platform-wide.md`

## 요약
- 완료 Step: **12/12**
- 변경 파일: 15개 (백엔드 7, 프론트엔드 8)
- 커밋: 10개 (43b5b08~30b89fa)
- Critical 이슈: 0건 · Warning: 모두 반영 또는 범위 외 · Suggestion: 범위 외

---

## 구현 결과

| Step | 상태 | 커밋 | 핵심 |
|------|------|------|------|
| 1 · 이벤트 스키마 (subsystem/status) | ✅ | `43b5b08` | `record_event` keyword-only, 세션 키 `(IP,subsystem)`, `get_active_session_count` 신규 |
| 2 · record_event username 보강 | ✅ | `bea923c` | `get_optional_user` 헬퍼, chat/search/heartbeat/page_view 4곳 |
| 3 · Translator/Notebook 계측 | ✅ | `441508f` | `_record_translator_event` + 6곳, 예외 분기 error status |
| 4 · Verify + 500 예외 핸들러 | ✅ | `c98aaff` | Compare upload/validate/similarity, rate-limit, path→subsystem 매핑 |
| 5 · `/api/health` FAISS 최신성 | ✅ | `3b452e2` | search vs vector-index mtime, 빈 시스템 false-alarm 방지 |
| 6 · `seed_demo_data` 확장 | ✅ | `0107dd4` | 4 서브시스템 이벤트 + 샘플 사용자 6명 (testbot/emp001~005) |
| 7 · `analytics.js` `initAnalytics(subsystem)` | ✅ | `12a4eec` | IIFE `_subsystem`, heartbeat/page-view body |
| 8 · 6페이지 HTML 계측 활성화 | ✅ | `5f352b7` | index/admin/translator/compare/launcher/login 전부 |
| 9 · `/api/analytics/dashboard` 응답 확장 | ✅ | `f7868cd` | by_subsystem/top_users/recent_failures/health 4필드, Plan-42 name JOIN |
| 10 · 대시보드 UI 렌더러 | ✅ | `51b8395` | 4 위젯 — 타일/활발한 사용자/실패 피드/건강 뱃지 |
| 11 · CSS 스타일링 | ✅ | `30b89fa` | `color-mix` 톤, `var(--ad-*)` 변수, 반응형 3단계 |
| 12 · 최종 검증 | ✅ | 본 보고서 | Playwright Light/Dark 통합 확인 |

---

## 검증 결과

### 코드 품질 (code-reviewer 누적)
- Step 2~11 각 단계마다 에이전트 리뷰 수행
- **Critical 전건 반영** — Starlette 예외 가로채기 방지, SQL 바인딩, 민감정보 유출 방지, name NULL 클리어 확인
- Warning 대부분 반영, Suggestion 은 범위·성능 부담 고려 선별
- 지속적 지적: 파일 내 하드코딩 색상 (Plan-41 이전부터 존재, 범위 외)

### UI 일관성 (/review-ui)
- `css/analytics.css` 신규 블록: 하드코딩 색상 **0건**, 모든 색상 `var(--ad-*)` 기반
- 비표준 사이즈 3건 (28px 대형 숫자, 11px 모노 배지, 14px 불릿) — 모두 디자인 의도
- 비표준 radius 2건 (3px 미니 배지, 999px pill, 2px 2px 0 0 스파크라인 막대) — 디자인 요구
- 다크모드: `.analytics-dashboard` 스코프 `--ad-*` 자동 전환, 별도 오버라이드 불필요

### 통합 테스트 (Playwright)
- **시나리오**: testbot 로그인 → admin.html 대시보드 → 데모 데이터 생성 → 전 위젯 렌더 확인
- **스크린샷**:
  - `workbench/screenshots/plan-41/plan-41-dashboard-light.png` (Light)
  - `workbench/screenshots/plan-41/plan-41-dashboard-dark.png` (Dark)
- **렌더 검증**:
  - 서브시스템 타일 4개 (Explorer 12 / Translator 6 / Verify 3 / Notebook 3 오늘 세션) ✅
  - Translator 실패 뱃지 (⚠ 1) ✅
  - 활발한 사용자 TOP 7명 (testbot 231 → emp005 44) ✅
  - 최근 실패 이벤트 20건, 좌측 빨간 악센트 ✅
  - 건강 뱃지 4개: 백엔드 DB ok / Ollama ok / **FAISS stale** / 디스크 317.2GB ✅
  - 14일 스파크라인 + 접속 추이 차트 ✅
- **콘솔 에러**: 0건
- **다크모드**: 모든 위젯 가독성 유지, 대비 적절

### 회귀 스팟체크
- 기존 대시보드 위젯(Summary/접속 추이/인기 문서/검색 키워드/챗봇 피드백) 동작 유지
- 로그인 플로우 / 세션 / RBAC 불변 (Plan-42 `name=null` 폴백 정상)
- `/api/health` 기존 응답 필드(database/ollama/disk) 유지 + `faiss` 추가
- 기존 `record_event` 호출 4곳(chat×2/search/page_view) username 전달 경로 추가, 기존 시그니처 호환

---

## 사용자 관점 피드백

### 긍정
- **플랫폼 전체 가시성 확보** — 기존 Explorer 단독 집계 → 4 서브시스템 독립 집계. Translator 이용자가 드디어 "활발한 사용자 TOP" 에 등장
- **타일 UX 직관적** — "오늘 세션 N" 대형 숫자 한눈에, 지표 2개로 보조, 14일 스파크라인으로 추세 파악
- **실패 피드 운영 가치** — 좌측 빨간 악센트 + 타임스탬프 + detail (doc_id/endpoint/filename) 로 "무엇이 실패했는가" 명확
- **건강 뱃지 상태 한눈 파악** — FAISS stale 같은 비자명 문제도 즉시 감지 가능
- **샘플 데이터 미리보기** — `데모 데이터 생성` 버튼으로 빈 차트 없이 전 위젯 확인 가능 — 실사용 전에도 UI 완성도 확인

### 우려
- **실패 피드 20건 고정** — 장기 운영 시 오래된 실패가 피드를 채우면 "최근" 의미 퇴색. 필터 (24h/7d) 또는 resolved 플래그 필요
- **타일 trend 스파크라인 작음** — 28px 높이로 추세 파악 제한적. 타일 클릭 → 확대 보기 (Phase 3 드릴다운)이 자연스러운 다음 스텝
- **heartbeat 중복 집계 멀티탭 케이스** — 동일 IP 로 Explorer + Translator 동시 접속 시 "현재 접속 1" vs 타일 "Translator 세션 1 + Explorer 세션 1" 이 혼란 가능. 툴팁 추가 여지

### 개선 제안
- 활발한 사용자 행 클릭 → 해당 사용자 최근 활동 타임라인 (Phase 3)
- 타일 "오늘" 대신 시간 필터 드롭다운 (7d/30d)
- 시스템 건강 뱃지 클릭 → 상세 설명·권장 조치 툴팁

---

## 웹디자인 전문가 관점 피드백

### 시각적 위계
- Summary 4 카드(1열) → 타일(2열 실제로는 4열) → 시계열 차트 → 랭킹(2열) → 피드 → 건강(1열) → Action 순 — "요약 → 분해 → 상세" 흐름 자연스러움
- 타일 28px 숫자가 시선 끌림 (안티패턴 아님, 핵심 메시지 강조)

### 인터랙션
- 타일 hover: border-color + shadow — Clickable 암시 (실제 Phase 3 에서 드릴다운 연결 예정)
- 뱃지 hover 반응 없음 — 순수 정보성, 의도됨
- Action 버튼 `데모 데이터 생성` 이 여전히 프로덕션 노출 — 배포 시 `debug.demo_seed_enabled` 플래그 분기 필요 (후속)

### 다크모드
- `color-mix(in srgb, var(--ad-*) X%, transparent)` 으로 계열 톤 생성 → Light/Dark 자동 스케일
- 실패 피드 좌측 `3px --ad-danger` 악센트 다크에서도 선명
- 건강 뱃지 pill 배경이 살짝 어두워 대비 유지

### 접근성
- Tile 은 `<div>` 기반 (클릭 동작 없음, OK) — Phase 3 드릴다운 시 `role="button"` + `tabindex=0` 필요
- 색상만으로 상태 전달하지 않음: 텍스트 "OK"/"stale" + 색 병행 ✅
- 실패 피드 가로 스크롤 `overflow-y: auto` → 스크롤바 표시 → 더보기 암시 ✅

### 반응형
- `<960px`: 타일 4→2열 — iPad 세로 등에서 자연
- `<700px`: 타일 1열, 뱃지 세로 정렬 — 모바일 admin 드물지만 폴백 확보

---

## 운영 관찰 (실 데이터 기반)

데모 생성 직후 대시보드 관찰:
- 4 서브시스템 모두 today_sessions 0 아닌 값 (oldest Explorer 12 → newest Notebook 3) — seed 분포 자연스러움
- 실패 이벤트 20건이 Translator 10+ / Verify 3+ / 500 에러 1~2 혼합 — metadata 필드 다양성 확인
- **FAISS stale** 실 감지 — 개발 머신에서 벡터 인덱스 미구축 상태를 대시보드가 즉시 알려줌 (Step 5 효과 증명)

---

## 잔여·후속 제안 (Plan-41 범위 외)

- [ ] **Phase 3 드릴다운** — 타일 클릭 → 해당 서브시스템 상세, 사용자 행 클릭 → 타임라인
- [ ] **실패 피드 필터** — 기간(24h/7d), resolved 토글
- [ ] **타일 "오늘" 시간 필터** — 7d/30d 드롭다운
- [ ] **heartbeat 중복 툴팁** — 상단 요약 vs 타일 세션 차이 설명
- [ ] **debug.demo_seed_enabled 플래그** — 프로덕션 배포 시 데모 버튼 숨김
- [ ] **활발한 사용자 name NULL 개선** — admin 계정 기본값, Plan-42 Edit 모달에서 보강 유도
- [ ] **translator 완료 이벤트** — 현재 started 만 기록, services/translator_service.py 에서 완료 emit
- [ ] **Phase 4 APM** — 여전히 보류 (규모 대비 과투자)

---

## 설계 변경 기록 (계획서 대비)

1. **`/api/health` 신규 생성 → 확장**: 이미 존재, FAISS 체크만 추가
2. **`record_event` username 보강** — 계획서에 없던 블로커성 작업, Step 2 에 포함
3. **`analytics.js` 파일 분리 → 유지** — `analytics-core.js` + `analytics-dashboard.js` 분리 보류, HTML 스크립트 태그 변경 리스크 회피 (~8KB gzipped 영향 미미)
4. **세션 정의 확정** — 상단 카드는 IP 유니크(기존 의미), 타일은 `(IP, subsystem)` 유니크

---

## MEMORY 갱신 판단

- 비자명한 교훈 3건 기록 가치 있음:
  - **SQLite 마이그레이션 순서**: `CREATE INDEX` 를 `executescript` 안에 두면 기존 DB 의 누락 컬럼 참조 시 실패. ALTER TABLE 루프 뒤로 분리 필수
  - **FastAPI 전역 `@app.exception_handler(Exception)`**: Starlette `HTTPException` 명시 제외 없으면 404/401 응답 가로챔
  - **`color-mix(in srgb, var(--token) X%, transparent)`**: Light/Dark 양쪽에서 자동 스케일되는 파스텔 톤 생성의 정석 — 신규 CSS 에서 재사용 가치

필요 시 `memory/feedback_plan41_learnings.md` 신규 작성 검토 (현재는 본 보고서에 기록).

---

## 커밋 제안 (최종 정리)

Plan-41 은 단일 릴리즈 원칙이지만 커밋 분할 전략으로 11개 Step × 1~2 커밋 = 10 커밋 이미 완료. 추가 커밋 없음.

완료 계획서 이름 변경 제안:
- `workbench/plans/41-dashboard-platform-wide.md` → `workbench/plans/done-41-dashboard-platform-wide.md`
- Plan-39/40 선례 따른 `done-` 접두어
- 백로그에서도 자연 이탈

---

## 관련 문서
- 계획서: `workbench/plans/41-dashboard-platform-wide.md`
- 의존 계획: `workbench/plans/42-user-profile-extension.md`
- 스크린샷: `workbench/screenshots/plan-41/`
- 관련 스킬: `.claude/skills/plan-execute/SKILL.md`
