# Plan-43 실행 피드백 — 대시보드 UX 개선

> 실행일 2026-04-24 · 실행자 Claude (/plan-execute) · 대상 계획서 `workbench/plans/43-dashboard-ux-polish.md`

## 요약
- 완료 Step: 6/6
- 변경 파일: 4개 (`services/analytics.py`, `api/analytics.py`, `js/analytics.js`, `css/analytics.css`)
- Critical 해결: 3/3 · High 해결: 3/3 · Quick win 해결: 1/1
- Playwright Light/Dark 실데이터 검증 통과, 콘솔 에러 0건

---

## 구현 결과

| Step | 상태 | 메모 |
|------|------|------|
| 1 · "현재 접속" 의미 전환 (백엔드) | ✅ | `get_active_user_count` username 유니크, `get_active_ip_count` 신규, 응답에 `ip_count`/`active_ips` 병행 |
| 2 · 렌더 순서 재배치 (건강 상단) | ✅ | Summary → **Health** → Subsystem tiles → Charts (운영 이상 감지 우선) |
| 3 · 라벨·부제·빈상태 (프론트) | ✅ | 타일 부제 4종, 실패 뱃지 "오늘" / 피드 "(최신 N건, 기간 무관)", feedback empty 숨김 |
| 4 · 마지막 갱신 + 자동 refresh | ✅ | `🕒 HH:MM:SS 업데이트` pill, 30초 `setInterval` + DOM 분리 감지 `clearInterval` |
| 5 · CSS 보조 | ✅ | `.ad-last-update-wrap`, `.ad-tile-heading/subtitle`, `.ad-card-sub`, `.ad-section-hint`, hover `cursor: default` |
| 6 · 통합 검증 | ✅ | 실 API + Playwright 자동화 |

### 주요 변경점
- **`services/analytics.py`**:
  - `get_active_user_count()`: `username` 필터 후 유니크 집합 반환 (익명 제외)
  - `get_active_ip_count()`: 기존 IP 유니크 로직 보존 (네트워크 수준 지표)
- **`api/analytics.py`**:
  - `/api/analytics/active-users`: `{count, ip_count}` 로 확장
  - `/api/analytics/dashboard`: `active_users` (로그인) + `active_ips` (IP) 병행
- **`js/analytics.js`**:
  - `_SUBSYSTEM_LABELS` 구조 객체화 `{label, subtitle}`
  - `_subsystemLabel(key)` 헬퍼로 호출부 2곳 정리
  - `_renderDashboardHTML`: 건강 뱃지 블록 이동, 카드 라벨/툴팁/서브텍스트 확장
  - `_renderSubsystemTiles`: `.ad-tile-heading` 래퍼 + `.ad-tile-subtitle`, 실패 뱃지 "오늘" 명시
  - `_renderRecentFailures`: 섹션 타이틀에 `.ad-section-hint` 로 기간 표기
  - `_renderFeedbackSection`: empty 시 빈 문자열 반환
  - `renderAnalyticsDashboard`: 자동 refresh 진입·이탈 제어, 로딩 스피너는 최초 1회만
  - `_formatUpdateTime(Date)` 헬퍼
- **`css/analytics.css`**: Plan-43 전용 블록 + 타일 `.ad-tile-heading/subtitle`, hover cursor, 건강 뱃지 상단 간격

---

## 검증 결과

### Playwright DOM 구조 검증
```
lastUpdate:        "11:05:11 업데이트"
activeLabel:       "현재 로그인 사용자"
activeValue:       "1"
healthPosition:    [last-update-wrap, summary, health, subsystem-grid, vbar, hbar]
tileSubtitles:     [웹북 탐색, PDF 번역, 문서 비교, 지식 관리]
failBadge:         "⚠ 1 오늘"
failuresTitle:     "최근 실패 이벤트 (최신 20건, 기간 무관)"
feedbackRendered:  false   (데이터 없으면 섹션 숨김)
tileCursor:        "default"
```
모든 Plan-43 목표 충족. 자동 refresh 타임스탬프는 재촬영 시 `11:05:43` 으로 갱신되어 `setInterval` 동작 확인.

### 콘솔 에러
0건.

### Light/Dark 스크린샷
- `workbench/screenshots/plan-43/plan-43-dashboard-light.png`
- `workbench/screenshots/plan-43/plan-43-dashboard-dark.png`

---

## 사용자 관점 피드백

### 긍정
- **대시보드 진입 첫 시선에 시스템 상태 감지** — FAISS `stale` 뱃지가 Summary 바로 아래로 와서 스크롤 전에 경고 감지 가능. Plan-41 대비 가장 큰 운영 UX 개선.
- **"현재 로그인 사용자 1"** 라벨이 직관적 — "누가 쓰고 있나" 에 직접 답함. 익명 IP 카운트는 툴팁으로 보조 제공되어 정보 누락 없음.
- **서브시스템 부제로 맥락 즉시 파악** — 신규 관리자가 타일만 보고도 어떤 기능인지 이해 가능 (웹북 탐색 / PDF 번역 / 문서 비교 / 지식 관리).
- **기간 명시**로 타일/피드 숫자 불일치 혼란 해소 — "⚠ 1 오늘" 과 "(최신 20건, 기간 무관)" 이 기준 차이를 명시.
- **마지막 갱신 pill** 이 데이터 신선도 투명하게 공개 — "지금 수치인가?" 의구심 제거.
- **자동 refresh 30초** — 수동 새로고침 없이 상태 추적 가능. 대시보드 열어둔 채 다른 작업 가능.

### 우려
- **자동 refresh 중 스크롤 유지 확인 부족** — 사용자가 스크롤 내려 실패 피드 보는 중 30초마다 innerHTML 교체 시 스크롤 위치가 어떻게 되는지 실환경 테스트 필요. 현 구현은 최초 진입 시만 스피너 표시하고 갱신 시엔 스피너 생략하도록 했으나, 스크롤 리셋은 여전히 가능성 있음.
- **IP 카운트가 `로그인 사용자 + 1 이상` 일 때만 서브텍스트 노출** — 로그인 사용자 == IP 면 서브텍스트 숨김. 평소에는 깔끔하나 "왜 이번엔 없지?" 가벼운 일관성 의문.
- **자동 refresh 가 공개 페이지에도 필요한가?** — admin 대시보드 전용이므로 영향 없음. 다만 `renderAnalyticsDashboard` 가 admin 아닌 곳에서 호출될 여지 차단 필요 시 추가 가드.

### 개선 제안 (후속)
- 타임스탬프 pill 옆 수동 "새로고침" 아이콘 버튼 (즉시 갱신 원하는 경우)
- 자동 refresh pause 토글 (관리자가 긴 실패 목록 검토 중일 때)
- IP 카운트 서브텍스트를 "총 IP N (익명 M)" 로 분해 표기

---

## 웹디자인 전문가 관점 피드백

### 시각적 위계
- 건강 뱃지가 Summary 바로 아래 narrow 스트립 → **시각 리듬 무너뜨리지 않고** 중요도 상향. 타일의 28px 대형 숫자와 시각 충돌 없음.
- 마지막 갱신 pill 우상단 정렬 → 헤더 액션 버튼(초기화/저장)과 수평 맞춰져 시선 흐름 자연.
- 서브시스템 타일 `heading + subtitle` 2줄 구조 → 제목 크기 유지, 정보 추가만으로 가독성 손상 없음.

### 인터랙션
- 타일 hover cursor `default` 로 전환 → **클릭 기대 오해 제거**. border/shadow 애니메이션은 유지되어 "활성" 상태 힌트만 남김. 향후 드릴다운 복구 시 `pointer` 로 되돌리면 됨.
- 실패 뱃지 "⚠ 1 오늘" 공백 분리 → 아이콘·숫자·시간맥락 3요소 각각 독립 스캔 가능.

### 다크모드
- `color-mix` 기반 톤 자동 스케일 유지 → 건강 뱃지·실패 악센트 모두 다크에서 대비 적절.
- `.ad-last-update` pill 이 다크 배경 위에서도 `--ad-hover` 배경 + caption 텍스트로 부각되지 않고 보조 정보로 자리잡음.

### 접근성
- 🕒 이모지는 장식 성격으로 스크린리더 가치 낮음. 추후 `<span aria-hidden="true">` 로 명시 권장.
- "⚠" 기호 + "오늘" 텍스트 병행 → 색상 이외에도 실패 신호 전달.
- 마지막 갱신 pill 의 `title` 속성 ("30초마다 자동 갱신") 으로 tooltip 접근 가능.

### 반응형
- `<960px` 타일 4→2열 유지, 건강 뱃지는 기존 가로 스크롤 flexbox → 좁은 화면에서 세로 정렬 전환.
- 마지막 갱신 pill 우상단 정렬이 narrow 화면에서도 겹침 없음.

---

## 회귀 영향 분석 (사후 확인)

| 영역 | 확인 결과 |
|------|----------|
| 기존 `/api/analytics/active-users` 응답 | `count` 키 유지, 추가 `ip_count` 는 client 가 무시 가능 → 회귀 없음 |
| `_pollActiveUsers` 상태바 폴링 | `data.count` 참조하는데 값 의미만 변경 (IP→로그인). 관리자 상태바에 표시되는 숫자가 달라짐 (작아짐). 라벨이 변경되어 사용자 혼동 없음 |
| Plan-41 시각화 | 타일·활발한 사용자·실패 피드·건강 뱃지 모두 렌더 정상 (Playwright 확인) |
| Plan-42 `name` JOIN | 활발한 사용자 위젯에서 `name` 폴백 동작 (스크린샷: testbot/admin name 은 NULL 이라 username 단독 표시) |
| 이벤트 스키마·record_event | 무변경 |
| seed_demo_data | 무변경 |

---

## 잔여·후속 제안 (Plan-43 범위 외)

- [ ] **2-column 대시보드 레이아웃** — 세로 스크롤 길이 추가 단축 (Plan-44 후보)
- [ ] **시간 범위 필터** — 7/14/30일 드롭다운, 다수 쿼리 `days` 파라미터 연동
- [ ] **Phase 3 드릴다운** — 타일 클릭 → 서브시스템 상세, 사용자 행 → 타임라인
- [ ] **자동 refresh pause 토글** — 관리자가 피드 검토 중 멈출 수 있는 UX
- [ ] **수동 새로고침 버튼** — pill 옆 🔄 아이콘
- [ ] **`aria-hidden` / 스크린리더 라벨** — 접근성 감사 별도 계획

---

## 커밋 제안

```
추가 [Plan-43] 대시보드 UX 개선 — 건강 뱃지 상단 / 로그인 사용자 / 자동 갱신

Plan-41 후속 사용자 관점 피드백 반영. 대시보드가 "한눈에 상태
파악" 이라는 업계 표준에 더 가까워짐.

핵심 개선 (Critical 3 · High 3 · Quick win 1):
  - 시스템 건강 뱃지 Summary 직후 배치 (스크롤 없이 경고 감지)
  - "현재 접속" → "현재 로그인 사용자" username 유니크 전환,
    IP 유니크는 get_active_ip_count 로 보존 + 응답 ip_count 병행
  - 타일 실패 뱃지 / 피드 타이틀에 기간 명시
  - 서브시스템 4종 부제 (웹북 탐색 / PDF 번역 / 문서 비교 / 지식 관리)
  - 마지막 갱신 pill + 30초 자동 refresh (DOM 분리 감지 clearInterval)
  - 챗봇 피드백 empty 시 섹션 숨김 (공간 낭비 제거)
  - 타일 hover cursor default (드릴다운 미구현 오해 방지)

영향 범위:
  - backend/services/analytics.py: get_active_user_count 의미 변경,
    get_active_ip_count 신규
  - backend/api/analytics.py: active-users/dashboard 응답에 IP 카운트 병행
  - js/analytics.js: 렌더 순서, _SUBSYSTEM_LABELS 객체화,
    자동 refresh 제어, _formatUpdateTime 헬퍼
  - css/analytics.css: .ad-last-update, .ad-tile-heading/subtitle,
    .ad-card-sub, .ad-section-hint, hover cursor default

검증: Playwright DOM 7항목 전수 통과, Light/Dark 스크린샷, 콘솔 0건.
30초 refresh 재촬영에서 타임스탬프 갱신 확인.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

## 관련 문서
- 계획서: `workbench/plans/43-dashboard-ux-polish.md`
- 선행 완료: `workbench/plans/done-41-dashboard-platform-wide.md`, `done-42-...` (Plan-42)
- 이전 피드백: `workbench/reports/plan-41-feedback-2026-04-24.md`
- 스크린샷: `workbench/screenshots/plan-43/`
