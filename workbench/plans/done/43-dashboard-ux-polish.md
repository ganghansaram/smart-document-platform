/# Plan-43: 대시보드 UX 개선 — 건강 뱃지 위치·"현재 접속" 의미·기간 표기·갱신 표시

> 작성일 2026-04-24 · 상태: **✅ 완료** (Step 1~6/6) · 담당: Claude (/plan-execute)
> 전제: Plan-41 완료 (`done-41-dashboard-platform-wide.md`, commit `97e8bd1`)
> 관련 피드백: `workbench/reports/plan-41-feedback-2026-04-24.md`
> 본 계획 피드백: [plan-43-feedback-2026-04-24.md](../reports/plan-43-feedback-2026-04-24.md)

## 1. 요약

Plan-41 직후 사용자·UI 전문가 관점 검토에서 발견된 **관리자 일상 사용성 이슈 7건** 을 해소한다. 기능 추가가 아닌 **기존 위젯의 배치·라벨·의미 명확화** 중심 개선.

범위:
- 🔴 **Critical 3건**: 건강 뱃지 위치·"현재 접속" 의미·기간 표기 불일치
- 🟠 **High 3건**: 빈 섹션 숨김·마지막 갱신 표시·서브시스템 부제
- 🟢 **Quick win 1건**: 타일 클릭 커서 제거 (드릴다운 미구현 상태에서 오해 방지)

의도적 제외 (Plan-43 범위 외):
- 2-column 레이아웃 재설계 (대규모 구조 변경 → 별도 계획)
- 시간 범위 필터 (7/14/30일) — API + 다수 쿼리 변경 필요, Plan-44 후보
- Phase 3 드릴다운 (타일·사용자 클릭 → 상세)
- 업로드 일별 큰 차트

---

## 2. 현재 상태 분석

### 2.1 실제 렌더 순서 (L184~ `_renderDashboardHTML`)
```
1. Platform Summary (4 cards: 현재 접속 / 오늘 / 이번 주 / 누적)
2. 서브시스템 타일 4개                  ← 신규
3. 접속 추이 14일
4. 인기 문서 TOP 10
5. 검색 키워드 TOP 10
6. 활발한 사용자 TOP 10 (7일)            ← 신규
7. 챗봇 사용 통계
8. 챗봇 피드백 분석                      ← empty 시 공간 낭비
9. 최근 실패 이벤트                      ← 신규
10. 시스템 건강 뱃지                     ← 신규, 위치 잘못
11. Action 버튼
```

### 2.2 "현재 접속" 의미 분석
- 구현 (`services/analytics.py:125-129`): `len({ip for (ip, _sub) in _active_users.keys()})` — **IP 유니크**
- 포함 범위: 로그인 사용자 + `login.html` 체류자 + 익명 접근자 + NAT IP 충돌자
- 라벨 "현재 접속" 은 3가지 해석이 가능해 모호: (a) IP 수 (b) 로그인 사용자 수 (c) 세션 수
- Plan-42 `name` 필드 머지로 이제 사용자 식별 가능 → 더 직관적인 "로그인 사용자" 중심 지표로 전환 가능

### 2.3 타일 "실패" vs 피드 "실패" 기간
- 타일 `failures_today`: `services/analytics.py:280-286` — `date(timestamp)=date('now','localtime')` (오늘만)
- 피드 `recent_failures(20)`: 기간 무관 최신 20건
- 렌더 라벨에 기간 명시 없음 → 관리자 혼동 원천

### 2.4 건강 뱃지 위치 문제
- 현재: `_renderDashboardHTML` 10번째 블록 (Actions 앞)
- 관찰: 스크린샷 세로 길이의 ~90% 지점 — 스크롤 필수
- 운영 관점: FAISS stale 같은 경고가 가장 먼저 보여야 함 (업계 표준)

### 2.5 영향 범위 사전 조사

| 변경 | 기존 참조처 | 영향도 |
|------|------------|--------|
| `get_active_user_count()` 의미 변경 | `/api/analytics/active-users` 공개 엔드포인트, 대시보드 카드 | 중 |
| 타일/피드 라벨 변경 | `js/analytics.js` 렌더러만 | 저 |
| 건강 뱃지 위치 변경 | `_renderDashboardHTML` 블록 순서만 | 저 |
| 빈 섹션 숨김 | `_renderFeedbackSection` 조건 분기 | 저 |
| 마지막 갱신 표시 | 헤더 삽입, 기존 요소 영향 없음 | 저 |
| 서브시스템 부제 | `_SUBSYSTEM_LABELS` 확장 | 저 |
| 타일 hover cursor | CSS 속성 1개 | 저 |

**주요 리스크**: `get_active_user_count()` 변경이 공개 엔드포인트 응답 의미를 바꿈. 다행히 현재 호출자는 `analytics.js:_pollActiveUsers()` 1곳 (관리자 상태바) 뿐 → 호환 가능.

---

## 3. 목표 상태

### 3.1 건강 뱃지 상단 이동
```
[Summary 4 cards]
[건강 뱃지 스트립]   ← 이동
[서브시스템 타일]
...
```

### 3.2 "현재 접속" 의미 명확화 (B안 채택)
- 기본 지표: **로그인 사용자 수 (username 유니크)**
- 라벨: `현재 로그인 사용자`
- 툴팁: `최근 2분 내 활동 · username 기준 유니크 · 익명/로그인 페이지 체류 제외`
- `get_active_user_count()` 로직 변경 + 기존 익명 IP 집계는 별도 함수 `get_active_ip_count()` 로 보존 (필요 시 확장)

### 3.3 기간 표기 명시
- 타일 실패 뱃지: `⚠ 1` → `⚠ 1 (오늘)`
- 피드 섹션 타이틀: `최근 실패 이벤트 (20)` → `최근 실패 이벤트 (최근 20건, 기간 무관)`

### 3.4 빈 섹션 숨김
- 챗봇 피드백 분석: 데이터 없을 시 섹션 자체 숨김 (현재는 빈 메시지 표시)

### 3.5 마지막 갱신 표시
- `analytics-dashboard` 컨테이너 상단에 `<span class="ad-last-update">10:45:23 업데이트</span>` 삽입
- 30초 자동 갱신 시 `setInterval` 추가 (기존 대시보드는 수동 새로고침만)

### 3.6 서브시스템 부제
- 타일 제목 아래 `<div class="ad-tile-subtitle">` 1줄:
  - Explorer — 웹북 탐색
  - Translator — PDF 번역
  - Verify — 문서 비교
  - Notebook — 지식 관리

### 3.7 타일 hover cursor
- `.ad-tile` 의 hover 시 `cursor: default` 유지 (현재는 `cursor: pointer` 암시하는 border/shadow 효과 때문에 클릭 기대 유발)
- Phase 3 드릴다운 구현 시 `cursor: pointer` 복원

---

## 4. 작업 구성 (단일 릴리즈)

### Step 1: "현재 접속" 의미 전환 (백엔드)
- `services/analytics.py`:
  - `get_active_user_count()` 로직: username 기준 유니크로 변경
  - `get_active_ip_count()` 신규 함수 (IP 유니크 — 기존 로직 보존)
- `api/analytics.py`:
  - `/api/analytics/active-users` 응답 구조 확장: `{count, ip_count}` 로 혼용 가능
  - dashboard 응답: `active_users` (로그인), `active_ips` (IP) 2필드
- 하위 호환: 기존 `active_users` 키는 유지, 의미만 변경 (로그인 사용자 수)

### Step 2: 대시보드 렌더 순서 재배치 (프론트엔드)
- `_renderDashboardHTML` 블록 순서:
  - Summary → **건강 뱃지 (이동)** → 서브시스템 타일 → (이하 기존)
- 건강 뱃지가 Summary 바로 아래 narrow 라인으로 표시

### Step 3: 라벨·부제·빈 상태·커서 (프론트엔드)
- `_SUBSYSTEM_LABELS` 구조 확장 `{label, subtitle}` 객체로 변경
- `_renderSubsystemTiles`: subtitle 렌더 추가, `failures_today` 뱃지 텍스트에 "(오늘)" 추가
- `_renderRecentFailures`: 섹션 타이틀 문구 변경
- `_renderFeedbackSection`: 데이터 없으면 빈 문자열 반환
- Summary 카드 "현재 접속" → "현재 로그인 사용자" 라벨, 툴팁 추가

### Step 4: 마지막 갱신 + 자동 갱신
- `renderAnalyticsDashboard` 진입 시 컨테이너 상단에 업데이트 타임스탬프 렌더
- `setInterval(renderAnalyticsDashboard, 30000)` 추가 (기존 `_pollActiveUsers` 30초 주기와 동기)
- admin 페이지 떠날 때 `clearInterval`

### Step 5: CSS 보조 (빈 섹션 숨김·hover cursor·갱신 라벨)
- `.ad-tile` hover cursor 속성 조정
- `.ad-tile-subtitle` 스타일 (12px, 보조 텍스트)
- `.ad-last-update` 스타일 (우상단 정렬, caption 크기)
- 건강 뱃지 상단 이동 시 간격 조정

### Step 6: 검증
- Playwright E2E: admin 로그인 → 대시보드 → 각 개선 항목 확인
- Light/Dark 스크린샷 재촬영
- 기존 카운트 표기와 신규 표기 모두 합리적 숫자인지 검증 (`active_users` vs `active_ips`)

---

## 5. 영향 범위

| 파일 | 성격 |
|------|------|
| `backend/services/analytics.py` | `get_active_user_count()` 재정의, `get_active_ip_count()` 신규 |
| `backend/api/analytics.py` | dashboard 응답에 `active_ips` 추가, active-users 응답 확장 |
| `js/analytics.js` | 렌더 순서, 라벨, subtitle, 갱신 표시, 자동 refresh |
| `css/analytics.css` | subtitle·갱신 라벨·hover·건강 뱃지 상단 스타일 |

**영향 받지 않음**: Plan-41 이벤트 스키마·record_event·계측 흐름·seed_demo_data·백엔드 쿼리 함수 대부분.

## 6. 리스크

| 리스크 | 완화 |
|--------|------|
| `get_active_user_count()` 의미 변경이 외부 모니터링·API 호출자에 영향 | 현재 호출자 1곳만 확인, 응답 스키마에 `ip_count` 병행 추가로 계속 접근 가능 |
| 자동 30초 refresh 가 서버 부담 증가 | 관리자 대시보드 동시 접속자 소수 가정, 기존 `/active-users` 30초 폴링 대비 API 1개 추가뿐 |
| 빈 섹션 숨기면 데이터 발생 시점에 UI 점프 | 챗봇 피드백 데이터 발생 빈도 낮음, 자연스러움 |
| 건강 뱃지 상단 이동이 Summary 리듬 깨뜨림 | narrow 스트립(pill 4개)으로 Summary 카드 4개와 시각 균형 유지 |

## 7. 의도적 제외

- **2-column 레이아웃** — 반응형 재설계 리스크 큼, Plan-44 로 분리 검토
- **시간 범위 필터 (7/14/30일)** — 다수 백엔드 쿼리 파라미터 변경 필요, Plan-44 또는 45
- **Phase 3 드릴다운** — 타일 클릭, 사용자 행 클릭 → 상세 뷰
- **차트 색상 의미 체계** — 주관적, 별도 디자인 검토 필요
- **접근성 키보드 네비·ARIA** — 별도 접근성 감사 계획 권장

## 8. 합의 필요 결정

1. **"현재 접속" 의미 전환 스코프**:
   - A) 완전 전환 (username 유니크만 표시)
   - B) 병행 (`active_users 1 · IP 2` 한 카드에 함께)
   - C) 카드 분할 (2개 카드: 로그인 / IP)

   → **A안 제안** (라벨 명확, 간결)

2. **자동 refresh 주기**:
   - 30초 (기존 `_pollActiveUsers` 와 동일)
   - 60초 (부하 절감)

   → **30초 제안** (기존 일관성)

3. **서브시스템 부제 문구 확정**:
   - Explorer — 웹북 탐색 / PDF 번역 / 문서 비교 / 지식 관리

   → 위 문구 제안, 기호 ` — ` (em-dash) 사용

---

## 9. 관련 문서

- 완료 계획: `workbench/plans/done-41-dashboard-platform-wide.md`
- 피드백: `workbench/reports/plan-41-feedback-2026-04-24.md`
- 스킬: `.claude/skills/plan-execute/SKILL.md`
