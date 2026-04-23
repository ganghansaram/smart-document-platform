# Plan-42 실행 피드백 — 사용자 프로필 확장 (Name · Description · Last Login)

> 실행일 2026-04-24 · 실행자 Claude (/plan-execute) · 대상 계획서 `workbench/plans/42-user-profile-extension.md`

## 요약
- 완료 Step: 3/3 (백엔드·프론트엔드·검증)
- 변경 파일: 4개 (`backend/services/auth.py`, `backend/api/auth.py`, `js/admin-settings.js`, `css/admin-settings.css`)
- Critical 이슈: 0건 (code-reviewer 지적 3건은 오독 1건·Plan-42 범위 외 2건)
- Warning: 2건 (범위 외) · Suggestion: 3건 (범위 외)

---

## 구현 결과

| Step | 상태 | 변경 파일 | 메모 |
|------|------|----------|------|
| 1 · DB 마이그레이션 + 백엔드 CRUD | ✅ | `backend/services/auth.py`, `backend/api/auth.py` | 3개 컬럼 ALTER TABLE try/except 루프화, `_user_dict` defensive key 체크 유지, `create_session` 내 UPDATE 추가 |
| 2 · 프론트엔드 UI | ✅ | `js/admin-settings.js`, `css/admin-settings.css` | 테이블 6열→8열, Add 폼 4→6 필드, Edit 모달 3→5 필드. description 은 Name 셀 title 툴팁 |
| 3 · 자가검증 | ✅ | — | JS 구문 OK, 백엔드 import·시그니처 OK, 드라이런 DB 시나리오 OK |

### 주요 변경점
- **`backend/services/auth.py`**
  - `init_db()`: CREATE TABLE 본문에 신규 3컬럼 포함 + 마이그레이션 ALTER 루프 (name/description/last_login_at)
  - `create_user(..., name, description)`: 선택 인자 추가, `strip() or None` 으로 빈 문자열 → NULL 정규화
  - `update_user(..., name, description)`: None 체크로 미지정 필드 건너뜀, `""` 입력은 NULL 로 저장 (클리어 지원)
  - `_user_dict(row)`: 신규 3필드 defensive key 체크 포함
  - `list_users()`: SELECT 에 3필드 추가
  - `create_session(user_id)`: DELETE/INSERT 후 `UPDATE users SET last_login_at = datetime('now')` 추가 (단일 connection, 최종 commit)
  - `get_session_user(token)`: SELECT 에 `u.name` 추가

- **`backend/api/auth.py`**
  - `UserCreateRequest`, `UserUpdateRequest` 에 `name`, `description` (Optional[str]) 추가
  - `add_user`, `edit_user` 핸들러가 body 필드 전달

- **`js/admin-settings.js`**
  - `_renderUsersPanel`: 테이블 헤더 8열, 폼 입력 6개 (Enter 키 리스너 포함)
  - `_loadUsersTable`: 행 렌더에 Name/Last Login 셀, description 툴팁, 버튼은 createElement 로 생성해 사용자 객체 클로저로 이벤트 부착 (기존 data-* 경유 제거)
  - `_formatLastLogin(iso)`: "YYYY-MM-DD HH:MM" 표시, 전체 timestamp 는 셀 title 툴팁
  - `_addUser`: name/description body 포함, 성공 시 전 필드 초기화
  - `_editUserInline(backendUrl, u)`: 시그니처 리팩토링 — 개별 파라미터 → 사용자 객체. Name/Description 필드 prefill + 변경 감지 후 PUT body 포함

- **`css/admin-settings.css`**
  - `.admin-users-table-wrap { overflow-x: auto }` 추가 (8열 좁은 화면 대응)
  - `.admin-users-table { min-width: 720px }` 추가

---

## 검증 결과

### 드라이런 시나리오 (임시 SQLite DB)
| 시나리오 | 기대 | 실제 | 결과 |
|----------|------|------|------|
| 신규 생성 with name/description | 필드 채워져 반환 | 동일 | ✅ |
| name="" 로 업데이트 | DB 에 NULL 저장 | NULL 확인 | ✅ |
| description 단독 변경 | name/role 보존 | 보존 확인 | ✅ |
| create_session 호출 | last_login_at 갱신 | `2026-04-23 23:00:00` 기록 | ✅ |

### 코드 품질 (code-reviewer 에이전트)
에이전트가 Critical 3건 / Warning 3건 / Suggestion 3건 리포트. 실행자 검증 결과:

| # | 지적 | 실제 | 처리 |
|---|------|------|------|
| C1 | `get_session_user` SELECT 에 `allowed_ip` 누락으로 IP 검증 회귀 | **오독** — `check_ip_allowed()` 가 별도 쿼리, `/api/auth/me` 는 IP 검증에 미사용. 또한 이 상태는 Plan-42 이전부터 동일하므로 Plan-42 회귀 아님 | 범위 외 — backlog |
| C2 | `update_user` 에서 name 을 NULL 로 지울 수 없음 | **오독** — `if name is not None` 이 `""` 를 통과시키고, `"".strip() or None = None` 이 params 에 추가됨. 드라이런에서 실제로 NULL 저장됨 확인 | 불필요 |
| C3 | 테이블 행 렌더에 `u.role`/`allowed_ip`/`created_at` 이스케이프 누락 | 사실이지만 admin-only 페이지 + 서버측 enum/포맷 통제. Plan-42 변경 이전부터 동일 | 범위 외 — backlog |
| W1 | create_session 3쿼리 트랜잭션 미보호 | SQLite WAL 단일 커넥션. `execute()` 3회는 암묵 트랜잭션, 최종 `commit()` 일괄. 마지막 UPDATE 실패는 커밋 전 예외 → 세션도 롤백. 의도대로 동작 | 불필요 |
| W2 | `add_user` 예외 메시지 원문 노출 | Plan-42 이전부터 동일. 민감정보 노출 범위는 SQLite 오류. 별도 이슈 | 범위 외 — backlog |
| W3 | `admin-new-user-name` (username 입력) Enter 리스너 누락 | 계획 이전부터 동일. 현행 UX 는 Password 에 Enter → 제출. 파급 없음 | 범위 외 |
| S1 | `/auth/me` 응답에 `name` 추가됐으니 `AuthState.displayName` 프론트 반영 | Plan-42 §9 에서 "헤더에 홍길동(testbot) 표시는 별도 합의 후" 명시적 제외 | 범위 외 (의도적) |
| S2 | `.admin-modal` 내부에 하드코딩 색상 다수 | Plan-42 이전부터 존재한 기술 부채. 신규 필드(이름·설명)가 상속받지만 새로 도입한 건 아님 | 범위 외 — backlog |
| S3 | last_login UTC 표시 → 로컬 시간 변환 검토 | 표시 스펙 합의 시 반영 (현행 UTC 그대로는 허용) | 합의 시 후속 |

### UI 일관성 (/review-ui 대상 파일)
- 변경 CSS 2줄: `overflow-x: auto` + `min-width: 720px` — 디자인 토큰·변수 사용 불필요한 구조 값
- 하드코딩 색상·비표준 사이즈 **신규 추가 0건**
- 기존 파일의 레거시 하드코딩 (`.admin-modal` 내부, `.notice-*` 등)은 Plan-42 이전부터 존재

### 사용성 테스트 (Playwright)
- **생략** — 백엔드(:8000) 미구동 상태로 로그인·CRUD 엔드-투-엔드 확인 불가
- 프론트(:80) 응답 OK, 정적 렌더 문제는 JS 구문 체크로 대체 검증
- 대신 백엔드 드라이런 DB 시나리오로 API 레벨 검증 완료

### 회귀 스팟체크
- `js/auth.js:75` `usernameEl.textContent = AuthState.user.username` — 여전히 username 참조, 변경 없음 ✅
- `js/platform-header.js:311` `usernameEl.textContent = d.user.username` — 동일 ✅
- 로그인 플로우 (`api/auth.py:login`) — `authenticate → check_ip_allowed → create_session` 순서 그대로, last_login_at 업데이트는 create_session 내부에서 추가됨 ✅
- `/api/auth/users` 응답 신규 필드 추가 — 구 UI 가 무시해도 동작 (방어적 렌더) ✅

---

## 사용자 관점 피드백

### 긍정
- **관리자 식별성 즉시 향상** — "testbot" 만 보이던 목록에 "홍길동" 표시 가능. 계정 생성 시 Name 한 줄만 채우면 운영 자산화됨
- **Last Login 가시성** — "누가 실제로 쓰는 계정인지" 판단이 가능해짐. 비활성 계정 정리 근거로 활용 가능
- **비파괴적** — 기존 testbot 계정은 NULL 유지, 관리자가 필요 시 Edit 으로 보강. 데이터 이관 이벤트 없음
- **Edit 모달 설계 개선** — 기존 3필드(Password/Role/IP)에서 5필드(+Name/Description)로 확장됐지만, 이름·설명을 상단에 배치해 "사람 식별" 먼저 → "권한 설정" 나중의 자연스러운 흐름

### 우려
- **description 툴팁 발견성** — Name 셀 hover 로만 description 이 보임. 마우스를 올리기 전까진 존재를 모름. 사용 패턴 관찰 후 전용 컬럼 승격 여부 재검토 필요
- **8열 테이블 폭** — 데스크톱에서는 여유, 1440px 미만에서는 `min-width: 720px` 로 가로 스크롤 발생. admin 페이지 특성상 허용 범위지만 향후 관리 항목 추가 시 재설계 필요
- **UTC 시간 표시** — last_login_at 이 UTC 원문. 한국 관리자가 "오후 2시 로그인" 을 기대하는데 "05:00" 로 보이면 혼란. 합의 후 로컬 변환 반영 권장

### 개선 제안
- Add 폼의 Name/Description 을 접힘 (collapsed) 상태로 숨기고 "추가 정보" 토글로 노출 — 필수 입력 부담 경감
- 사용자 목록 검색/필터 (name 기반) — 수십 명 규모에서 즉시 유용

---

## 웹디자인 전문가 관점 피드백

### 시각적 위계
- 테이블 헤더 Name 열이 Username 과 인접 배치 → 스캔 흐름 "사번 → 이름 → 권한" 자연스러움
- Role 배지가 3개 열 이후(왼쪽부터 4번째)에 위치해 "식별 → 분류" 시선 이동 적절
- Last Login / Created 가 우측으로 밀리며 부가 정보 성격 유지 — 시각적 위계 OK

### 인터랙션
- description 을 툴팁으로 처리한 결정은 **정보 밀도 관리 측면에서 타당**. 단, title 속성은 접근성 도구 지원이 제한적 (일부 스크린리더 무시) — 장기적으로 aria-describedby 전환 검토
- Add 폼의 Enter 키가 displayname/desc 에서도 제출 트리거 → 키보드 흐름 일관

### 다크모드
- 신규 CSS 2줄은 색상 무관
- 모달은 기존 하드코딩 색상 상속 (Plan-42 범위 외 기술 부채). 신규 필드 추가로 노출 면적 증가했으나 신규 불일치는 도입하지 않음

### 접근성
- Name 셀 title 툴팁: 마우스·키보드 hover 시 표시. 완벽한 접근성은 아님 — `aria-describedby` 로 보강 여지 있음 (후속 제안)
- 8열 테이블: `<th>` 시맨틱 유지, 스크린리더 탐색 가능
- Edit 모달: 기존 모달 패턴 그대로 사용 — focus trap 은 기존 범위 외 기술 부채

### 반응형
- `overflow-x: auto` 래퍼로 좁은 화면 가로 스크롤 제공 — 모바일 사용은 admin 특성상 드물지만 폴백 확보
- 640px 반응형 미디어 쿼리 영향 없음 (테이블 래퍼는 자연스럽게 스크롤)

---

## 잔여·후속 제안 (Plan-42 범위 외)

- [ ] `get_session_user` SELECT 에 `allowed_ip` 추가 — `/api/auth/me` 응답 완전성 (잠재 버그, 현재 미활용이라 영향 없음)
- [ ] 테이블 행 렌더 `u.role`/`allowed_ip`/`created_at` `_escHtml` 적용 — 방어적 코딩
- [ ] `add_user` 예외 응답에서 SQLite 원시 메시지 마스킹 — 정보 유출 완화
- [ ] `.admin-modal` 내부 하드코딩 색상 → 디자인 토큰 교체 — 기술 부채 정리
- [ ] last_login_at 로컬 시간대 변환 (`toLocaleString('ko-KR')`) — UX 합의 시
- [ ] `AuthState.displayName` + 헤더에 "홍길동 (testbot)" 표시 — Plan-42 §9 별도 합의 후
- [ ] Name 셀 `title` → `aria-describedby` 전환 — 접근성 향상
- [ ] 사용자 목록 name 기반 검색·필터 — 규모 증가 시

---

## 커밋 제안 (사용자 요청 시)

```
추가 [플랫폼] 사용자 프로필 확장 — Name / Description / Last Login

- users 테이블에 name, description, last_login_at 3개 선택 컬럼 추가
  (ALTER TABLE try/except 마이그레이션, 기존 DB 호환)
- 계정 관리 테이블 8열 확장 (Name / Last Login 추가, description 은 툴팁)
- Add 폼·Edit 모달에 이름·설명 입력 필드 추가
- create_session 에서 last_login_at 자동 갱신

로그인·RBAC·헤더 표시 등 기존 흐름 불변. Plan-41 대시보드의
"활발한 사용자" 랭킹에서 name 폴백 활용 가능한 상태.

참조: workbench/plans/42-user-profile-extension.md
```

---

## MEMORY 갱신 판단
- 비자명한 교훈 없음 — ALTER TABLE try/except 패턴은 이미 memory 기록됨
- 다만 Plan-42 가 Plan-41 대시보드와 맞물린다는 "두 계획 조합 의도"는 backlog 에 이미 반영됨
- 별도 memory 추가 불필요

---

## 관련 문서
- 계획서: `workbench/plans/42-user-profile-extension.md`
- 의존 계획: `workbench/plans/41-dashboard-platform-wide.md`
- 스킬: `.claude/skills/plan-execute/SKILL.md`
