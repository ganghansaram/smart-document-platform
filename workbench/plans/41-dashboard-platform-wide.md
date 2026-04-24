# Plan-41: 대시보드 플랫폼 전체 관점 재설계

> 작성일 2026-04-24 · 상태: **진행 중** (Step 1~9/12 완료 — 대시보드 API 확장 완료) · 담당: Claude (/plan-execute)
> 의존: [Plan-42 사용자 프로필 확장](./42-user-profile-extension.md) — 머지 완료 (23c7965)

## 진행 상태

| Step | 상태 | 커밋 | 비고 |
|------|------|------|------|
| 1 · 백엔드 계측 스키마 (events subsystem/status) | ✅ | `43b5b08` | `record_event` keyword-only 인자, 세션 키 (IP, subsystem), `get_active_session_count` 신규 |
| 2 · 기존 record_event username 보강 | ✅ | `bea923c` | `get_optional_user` 헬퍼, chat/search/heartbeat/page_view 4곳 보강 |
| 3 · Translator record_event (upload/translate/summarize/notebook chat) | ✅ | (step3 commit) | `_record_translator_event` 헬퍼 + 6곳 (Notebook chat 포함), 예외 분기에도 error status 기록 |
| 4 · Compare + main.py exception handler | ✅ | (step4 commit) | Compare upload/validate/similarity 계측, 전역 예외 핸들러 + rate-limit + path→subsystem 매핑 |
| 5 · `/api/health` FAISS 최신성 체크 추가 | ✅ | (step5 commit) | search-index vs vector-index mtime 비교, 4상태 (ok/stale/missing/unknown), 빈 시스템 false-alarm 방지 |
| 6 · `seed_demo_data` 서브시스템 이벤트 확장 | ✅ | (step6 commit) | Translator/Verify/Notebook 이벤트 + 샘플 사용자 6명(testbot/emp001~005), 30일 2,377 이벤트 생성 |
| 7 · `analytics.js` `initAnalytics(subsystem)` 확장 | ✅ | (step7 commit) | IIFE `_subsystem` 캡슐화, heartbeat/page-view body 에 포함, trackPageView(url, subsystem) 2번째 인자 옵셔널 |
| 8 · 전 서브시스템 HTML analytics 로드 + initAnalytics(subsystem) | ✅ | (step8 commit) | 6페이지 (index/admin/translator/compare/launcher/login) 태그 통일: explorer/admin/translator/verify/launcher/login |
| 9 · `/api/analytics/dashboard` 응답 확장 | ✅ | (step9 commit) | by_subsystem / top_users (Plan-42 name JOIN) / recent_failures / health 4필드 추가. seed_demo_data 보강 (오늘 포함 + 비-Explorer visits) |
| 10 · 대시보드 UI (타일·활발한 사용자·실패 피드·건강 뱃지) | ⏳ | — | — |
| 11 · CSS (tokens 변수 준수, 다크모드) | ⏳ | — | — |
| 12 · 최종 검증 | ⏳ | — | — |

## 실행 중 발견 사항 (계획서 대비)

- **§4.5 수정**: `/api/health` 는 이미 `backend/main.py:183` 에 존재 (database/ollama/disk 체크). "없으면 신규"가 아닌 **FAISS 최신성만 추가**로 Step 5 수행
- **§5.3 보완**: Step 1~2 에서 `record_event` 시그니처를 keyword-only (`*, subsystem, status`) 로 확장해 기존 호출 무수정 호환 확보
- **§5.3 보완**: `chat.py`/`search.py` 엔드포인트가 `get_current_user` Depends 없이 `raw_request` 만 받는 상태 → `get_optional_user` 신규 헬퍼로 쿠키 기반 폴백 (비로그인 허용 유지)
- **§4.2 "세션" 정의 확정**: 상단 요약 카드는 `get_active_user_count()` 로 IP 유니크 유지 (기존 의미 불변), 서브시스템 타일은 `get_active_session_count(subsystem)` 로 `(IP, subsystem)` 유니크
- **§5.3/§7 수정 — analytics.js 분할 보류**: 원 계획은 `analytics-core.js` + `analytics-dashboard.js` 2파일 분리였으나, `index.html`/`admin.html` 스크립트 태그 변경 리스크 및 대시보드 렌더러 ~8KB gzipped 영향 미미 판단 → **파일명 유지 + 내부 확장** 방식으로 Step 7 수행. Step 8 에서 HTML 호출부 갱신만 진행

---

## 1. 요약

관리자 > 대시보드가 Explorer 단일 서브시스템 이벤트만 관측하는 한계를 해소한다. 플랫폼은 4개 서브시스템(Explorer, Translator, Verify, Notebook) + Launcher/Auth 공통 레이어로 구성돼 있는데, 통계 계층은 초기 Explorer 단일 앱 시절 골격이다.

본 계획서는 다음을 **단일 릴리즈**로 묶어 진행한다.
- **계측 토대** — 이벤트에 `subsystem` 태그, 전 서브시스템 heartbeat·주요 행위 기록
- **대시보드 UI 재구성** — 플랫폼 요약 스트립 + 서브시스템 타일 4개 + 활발한 사용자 + 실패 피드

이유: (a) 유지보수 연속성 불확실 — 완성도 있는 상태로 떨어뜨려 두는 게 안전, (b) `seed_demo_data` 샘플 미리보기가 빈 차트 리스크를 낮춤.

Phase 3(드릴다운)·Phase 4(APM)는 명시적으로 범위 밖.

---

## 2. 현재 상태 분석

### 2.1 관측 범위 — Explorer 편향

| 레이어 | 계측 여부 | 비고 |
|--------|-----------|------|
| Explorer (`index.html`) | O | `analytics.js` 로드, heartbeat + trackPageView + search/chat |
| Translator (`translator.html`) | X | 번역/추출/요약/Q&A 전혀 계측 없음 |
| Verify/Compare (`compare.html`) | X | 비교/유사도/규칙 판정 이벤트 없음 |
| Notebook (translator 내부 뷰) | X | 페이지 편집·AI 요약·Q&A 계측 없음 |
| Launcher (`launcher.html`) | X | 플랫폼 진입 집계 안 됨 |
| Login (`login.html`) | X | 로그인·실패 기록 없음 |
| Admin (`admin.html`) | O (로드만) | 관리자 체류가 "현재 접속"을 오염시킴 |

"현재 접속자 N명" = **최근 2분 내 Explorer/admin에서 heartbeat 보낸 IP 수**. Translator 이용자는 카운트 밖.

### 2.2 이벤트 스키마 (SQLite `events`)

```
event_type  수집 위치                      의미
──────────  ─────────────────────────────  ─────────────────────────
visit       heartbeat 최초/타임아웃 재진입   Explorer 세션 시작
page_view   /api/analytics/page-view       Explorer 웹북 문서 열람
search      /api/search (RAG)              Explorer 키워드/벡터 검색
chat        /api/chat, /api/chat/stream    Explorer RAG 챗봇 질문
```

별도 `chat_feedback` 테이블 — Explorer 챗봇 👍/👎만 저장.

`username` 컬럼은 존재하나 **대시보드가 활용하지 않음** (Top 사용자 뷰 없음).

### 2.3 대시보드 구성 (현행)

요약 카드 4종 → 접속 추이(14일) → 인기 문서 TOP 10 → 검색 키워드 TOP 10 → 챗봇 통계/추이 → 챗봇 피드백 분석 → 데모/초기화 버튼.

모든 지표가 Explorer 한정. Translator/Verify/Notebook은 아예 등장하지 않음.

### 2.4 근본 한계

1. **서브시스템 차원 부재** — 수집 시점부터 태그가 없어 후처리로도 분리 불가
2. **자원 소비 지표 부재** — 업로드 용량, 작업공간, 인덱스 크기, Ollama 호출량
3. **사용자 맥락 미활용** — events.username 있으나 대시보드 노출 없음
4. **실패 가시성 없음** — 업로드/번역/Ollama 타임아웃이 로그에만 남음

---

## 3. 설계 원칙

소규모 폐쇄망 사내 도구 운영 관점에서 대시보드가 실제로 주는 가치 3가지에만 집중:
1. **"지금 뭐가 돌아가나"** — 현재 접속자(서브시스템별), 백엔드·Ollama 건강
2. **"무엇이 많이 쓰이나"** — 서브시스템별 활성도, 상위 사용자·문서·쿼리
3. **"무엇이 실패했나"** — 업로드 실패, 번역 실패, 부정 피드백, 5xx 스파이크

APM(p95 latency, trace)은 현 규모에서 과투자. 실시간 푸시(WebSocket)도 30초 폴링으로 충분.

---

## 4. 목표 상태

### 4.1 상단: 플랫폼 요약 스트립 (현행 유지·의미 확장)

```
[ 현재 접속 N ]  [ 오늘 방문 N ]  [ 이번 주 N ]  [ 누적 방문 N ]
```
모든 서브시스템 heartbeat 합산. IP 유니크 집계 유지.

### 4.2 중단: 서브시스템 타일 4개 (신규)

```
┌─ Explorer ──────┐  ┌─ Translator ───┐  ┌─ Verify ───────┐  ┌─ Notebook ─────┐
│ 오늘 세션 N      │  │ 오늘 세션 N      │  │ 오늘 세션 N      │  │ 오늘 세션 N      │
│ 문서 열람 N      │  │ 번역 N건         │  │ 비교 N건         │  │ Q&A N건         │
│ 챗봇 N건         │  │ 실패 N건 (빨강)   │  │ 평균 유사도 N%    │  │ 요약 N건         │
│ 14일 스파크라인   │  │ 14일 스파크라인   │  │ 14일 스파크라인   │  │ 14일 스파크라인   │
└─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘
```
"세션 N"은 `(IP, subsystem)` 유니크 — 상단 요약과 중복 계산 회피.

### 4.3 하단: 랭킹 영역

- **인기 문서 TOP 10** — 서브시스템 아이콘 포함 (Explorer 웹북 + Translator 문서 + Verify 원문)
- **검색 키워드 TOP 10** — Explorer 전용 유지
- **활발한 사용자 TOP 10** (신규) — 최근 7일 events.username 빈도. Plan-42 머지 후 `name (username)` 형식, 미머지 시 username 단독

### 4.4 하단: 운영 이슈

- **챗봇 피드백 분석** — 기존 유지, subsystem 필터(Explorer/Notebook) 추가
- **최근 실패 이벤트** (신규) — 업로드 실패, 번역 실패, Ollama 타임아웃, 5xx 스파이크 최근 20건

### 4.5 최하단: 시스템 건강 뱃지

```
[ 백엔드 OK ]  [ Ollama OK ]  [ FAISS 최신 ]  [ 디스크 여유 N GB ]
```
`/api/healthz` 확장 (없으면 신규) + 30초 폴링.

---

## 5. 이벤트 모델

### 5.1 스키마 확장

```sql
ALTER TABLE events ADD COLUMN subsystem TEXT;
ALTER TABLE events ADD COLUMN status TEXT;
CREATE INDEX IF NOT EXISTS idx_events_subsystem ON events(subsystem);
```

기존 컬럼 유지. `init_db()` 의 try/except `ALTER TABLE` 패턴 재사용. 폴백: `WHERE COALESCE(subsystem, 'explorer') = ?`.

### 5.2 이벤트 타입 정의

| event_type | subsystem | metadata 예시 | 신규 여부 |
|------------|-----------|---------------|----------|
| `visit` | 전체 | — | 기존·확장 |
| `page_view` | explorer | `{url}` | 기존 |
| `search` | explorer | `{query, hits}` | 기존·metadata 확장 |
| `chat` | explorer, notebook | `{model}` | 기존·subsystem 추가 |
| `upload` | explorer, translator | `{size, ext, ok}` | 신규 |
| `translate` | translator | `{doc_id, pages, engine, ok, elapsed_ms}` | 신규 |
| `summarize` | translator | `{doc_id, mode, ok}` | 신규 |
| `compare` | verify | `{docs, rule_count, ok}` | 신규 |
| `error` | * | `{endpoint, status, msg_preview}` | 신규 |

### 5.3 계측 지점

**백엔드**
- `api/upload.py` — upload 성공/실패
- `api/translator.py` — upload, translate, summarize
- `api/compare.py` — compare
- `services/notebook_chat.py` — chat (subsystem=notebook)
- `main.py` exception handler — error

**프론트엔드**
- `analytics.js` → 분할:
  - `js/analytics-core.js` (공통 계측: heartbeat, trackPageView, subsystem 인자)
  - `js/analytics-dashboard.js` (관리자 대시보드 렌더)
- `translator.html`, `compare.html`, `launcher.html`, `login.html` 에 `analytics-core.js` 로드 + `initAnalytics('<subsystem>')`
- `index.html` 기존 호출을 `initAnalytics('explorer')`로 변경

### 5.4 보존·용량

폐쇄망 수십 명 기준 일 수천 건. SQLite 무리 없음. 60일 이상 롤업은 추후 판단.

---

## 6. 작업 구성 (단일 릴리즈)

### Step 1: 백엔드 계측 토대
- `events` 마이그레이션 (ALTER TABLE try/except)
- `record_event(event_type, ip, metadata, *, username=None, subsystem=None, status=None)` 시그니처 확장
- `record_heartbeat(ip, username, subsystem)` 확장
- Translator/Compare/Upload/Notebook chat 엔드포인트에 record_event 추가
- `main.py` 글로벌 exception handler에 error 이벤트 기록

### Step 2: 프론트엔드 계측 토대
- `analytics.js` → `analytics-core.js` + `analytics-dashboard.js` 분할
- translator/compare/launcher/login HTML 에 core 스크립트 로드 + `initAnalytics('<subsystem>')`
- `trackPageView(url, subsystem)` — subsystem 파라미터 추가, 기본 Explorer 폴백

### Step 3: 대시보드 API 확장
- `/api/analytics/dashboard` 응답에 `by_subsystem` 블록 추가:
  ```json
  {
    "summary": {...기존...},
    "by_subsystem": {
      "explorer":   { "today_sessions": N, "metrics": {...}, "trend_14d": [...] },
      "translator": { ... },
      "verify":     { ... },
      "notebook":   { ... }
    },
    "top_users":        [ { "username": "...", "name": "...", "count": N } ],
    "recent_failures":  [ { "ts": "...", "subsystem": "...", "event_type": "...", "message": "..." } ],
    "health":           { "backend": "ok", "ollama": "ok", "faiss": "stale", "disk_free_gb": 120 },
    "top_pages": [...], "top_searches": [...], "feedback": {...}
  }
  ```
- `get_top_users(days, limit)` 신규 쿼리 함수 (events.username 기반)
- `get_recent_failures(limit)` 신규 (status='error' 또는 event_type='error')
- `/api/healthz` 확장 (없으면 생성): backend/ollama/faiss/disk 상태

### Step 4: 대시보드 UI 재구성
- 서브시스템 타일 4개 렌더 (`_renderSubsystemTile`)
- 활발한 사용자 TOP 10 렌더 (name 있으면 "홍길동 (testbot)", 없으면 "testbot")
- 최근 실패 이벤트 피드
- 시스템 건강 뱃지
- 기존 인기 문서에 서브시스템 아이콘 태그

### Step 5: 데모 데이터 확장
- `seed_demo_data` — 서브시스템별 샘플 이벤트 생성:
  - Translator: upload/translate 30일치 (주중 8-15건, 일부 실패 섞음)
  - Verify: compare 30일치 (주중 3-8건)
  - Notebook: chat/summarize 30일치
  - error 샘플 소수 포함 (recent_failures 피드 미리보기용)
- 샘플 데이터가 모든 타일·피드를 채우는 게 완료 기준

### Step 6: 검증
- 로컬 실행 → admin 로그인 → 데모 데이터 생성 → 전 위젯 채워짐 확인
- Translator 번역 1건 실행 → 실제 이벤트가 타일·랭킹에 반영
- 샘플 사용자 N명 구성 → Plan-42 연동 시 `name` 노출 정상 확인 (Plan-42 머지 후)
- 초기화 → 폴백 메시지 정상 표시

---

## 7. 영향 범위

| 파일 | 변경 성격 |
|------|-----------|
| `backend/services/analytics.py` | 스키마 마이그레이션, record_* 시그니처 확장, get_top_users/get_recent_failures 신규 |
| `backend/api/analytics.py` | dashboard 응답 스키마 확장 |
| `backend/api/upload.py`, `translator.py`, `compare.py`, `chat.py`, `search.py` | record_event 호출 추가·인자 확장 |
| `backend/services/notebook_chat.py` | chat 이벤트 기록 |
| `backend/main.py` | exception handler → error 이벤트 |
| `backend/api/health.py` 또는 `main.py` | `/api/healthz` 확장 |
| `js/analytics.js` | 2개 파일로 분리 |
| `js/analytics-core.js` (신규), `js/analytics-dashboard.js` (신규) | 기존 로직 이관 |
| `translator.html`, `compare.html`, `launcher.html`, `login.html`, `index.html`, `admin.html` | 스크립트 로드·`initAnalytics(subsystem)` 호출 |
| `css/analytics.css` | 타일·뱃지·실패 피드 스타일 추가 |

## 8. 리스크

- **heartbeat 중복 집계**: 멀티탭(Explorer+Translator) 시 IP 유니크 "현재 접속"은 1명, 타일 "세션"은 `(IP, subsystem)` 유니크라 2 → UI 툴팁으로 설명
- **마이그레이션 실패**: SQLite ALTER TABLE try/except + 컬럼 없음 시 폴백 쿼리(`COALESCE`) 병용
- **시드 데이터 오염**: 기존 `seed_demo_data`와 병행. Reset → Seed 순서 권고 문구 추가
- **프라이버시**: 활발한 사용자 랭킹은 admin 전용 엔드포인트에만 노출. 일반 사용자 `/api/analytics/active-users`는 카운트만 반환 (기존 그대로)
- **Ollama 건강체크**: 폐쇄망에서 Ollama 미구동 상태가 정상 운영일 수 있음 → 관리자 설정에서 "Ollama 필수" 토글과 연동해 건강체크 결과 해석

## 9. 미포함 (의도적 제외)

- Phase 3 드릴다운 (타일 클릭 → 상세 뷰, 사용자 타임라인) — 실사용 후 판단
- Phase 4 APM (latency 분포, trace) — 규모 대비 과투자
- 외부 APM 연동 — 폐쇄망 제약
- 실시간 WebSocket 푸시 — 30초 폴링 유지
- 로그인 실패 자동 잠금 등 보안 자동화 — 별도 계획
- CSV 내보내기 — 요청 발생 시 추가

## 10. 합의가 필요한 결정

1. **Notebook 분류**: 독립 서브시스템으로 취급 (본 계획 가정) vs Translator 내부 뷰 → **독립 권장**
2. **타일 "세션" 정의**: `(IP, subsystem)` 유니크 (제안) vs username 유니크 — 비로그인 환경도 고려해 IP 기반 권장
3. **실행 시기**: 플랫폼 오픈 전 포함 (이관 안전성 ↑) vs 오픈 후 실사용 데이터 기반 (설계 정확도 ↑) → **오픈 전 포함 쪽으로 합의됨**

---

## 11. 관련 문서

- [Plan-42 사용자 프로필 확장](./42-user-profile-extension.md)
- `workbench/plans/done-32-admin-settings-reorganization.md` — 서브시스템별 설정 재편 (분류 체계 일치)
- `backend/services/analytics.py` — 현 구현
- `js/analytics.js` — 현 구현
