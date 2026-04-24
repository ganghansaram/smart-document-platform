# Plan-42: 사용자 프로필 확장 (Name · Description · Last Login)

> 작성일 2026-04-24 · 상태: **✅ 완료** · 담당: Claude (/plan-execute) · 구현 커밋 `23c7965`
> 관계: [Plan-41 대시보드 재설계](./done-41-dashboard-platform-wide.md) — 상호 독립, 머지 순서 자유
> 피드백: [plan-42-feedback-2026-04-24.md](../reports/plan-42-feedback-2026-04-24.md)

## 1. 요약

계정 관리에서 현재는 **username(사번)** 만 식별자로 쓴다. 폐쇄망 내부 플랫폼에서 관리자가 사용자 목록을 보거나 대시보드의 "활발한 사용자"를 볼 때 `testbot` · `a12345` 같은 사번만으로는 **"누구인지"** 즉시 식별하기 어렵다.

본 계획은 다음 3개 선택 컬럼을 users 테이블에 추가한다.

- `name` — 표시용 이름 (예: "홍길동")
- `description` — 부서·비고 (예: "체계개발팀 / FY1 담당")
- `last_login_at` — 마지막 로그인 시각 (운영 판단용)

**필수값 아님**. 기존 계정·로그인·RBAC 흐름을 건드리지 않고, 관리자가 계정 생성 시 선택적으로 입력한다. Plan-41 대시보드의 "활발한 사용자 TOP 10"에서 `name` 이 있으면 우선 표시, 없으면 `username` 폴백.

---

## 2. 현재 상태

### 2.1 DB 스키마 (`backend/services/auth.py:32-46`)

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'admin',
    allowed_ip TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

`allowed_ip` 는 사후 `ALTER TABLE` 마이그레이션으로 추가된 패턴이 이미 존재 (auth.py:48-52). 동일 패턴으로 확장 가능.

### 2.2 백엔드 API (`backend/api/auth.py`)

- `UserCreateRequest`: username, password, role, allowed_ip
- `UserUpdateRequest`: 각 필드 Optional
- `list_users()`, `create_user()`, `update_user()` — auth.py 의 CRUD 헬퍼
- `_user_dict(row)` 가 프론트엔드 응답 직렬화 담당 (auth.py:145-150)
- `get_session_user(token)` — 세션 조회. 현재 id/username/role/created_at 만 반환 (auth.py:189-193)

### 2.3 프론트엔드

- `AuthState.user` — 전역. `{id, username, role, ...}` 구조 (`js/auth.js`)
- 헤더 표시: `usernameEl.textContent = AuthState.user.username` (`platform-header.js:311`)
- 계정 관리 테이블 열: ID / Username / Role / IP / Created / Actions (`admin-settings.js:1164`)
- Add 폼: Username / Password / Role / 허용 IP (admin-settings.js:1171-1179)
- Edit 모달: Password / Role / 허용 IP (admin-settings.js:1281-1303)

### 2.4 영향받지 않는 것

- 로그인 플로우 (`/api/auth/login`) — username+password 검증, 변경 없음
- 세션 생성·만료 — 변경 없음 (last_login_at 업데이트만 1 쿼리 추가)
- RBAC (viewer/editor/admin) — 변경 없음
- IP 화이트리스트 — 변경 없음
- `AuthState.user.username` 참조 코드 — **모두 유지**. 헤더·분석·RBAC 검사가 username 에 의존하므로 리네임 안 함

---

## 3. 설계 원칙

1. **비파괴적 확장** — 기존 컬럼·필드·API·UI 동작을 모두 유지하고, 새 컬럼·선택 입력만 추가
2. **폴백 우선** — UI 어디에서든 `name` 이 없으면 `username` 을 그대로 표시. 빈 칸 아님
3. **마이그레이션 자동** — 기동 시 `ALTER TABLE ADD COLUMN` try/except (allowed_ip 패턴 재사용). 기존 DB 대응
4. **권한 변경 없음** — Name/Description 열람·수정은 admin 전용 (기존 `/auth/users` 엔드포인트 권한 유지)

---

## 4. 변경 내역

### 4.1 DB 스키마

```sql
ALTER TABLE users ADD COLUMN name TEXT;           -- NULL 허용
ALTER TABLE users ADD COLUMN description TEXT;    -- NULL 허용
ALTER TABLE users ADD COLUMN last_login_at TEXT;  -- NULL 허용
```

- `auth.py:init_db()` 의 try/except 블록을 3회로 확장 (또는 리스트 순회)
- `CREATE TABLE` 신규 스키마에도 3개 컬럼 포함 (새 DB 생성 시)
- NULL 허용 — 기존 계정에 영향 없음, 관리자가 사후 편집 가능

### 4.2 백엔드

**`services/auth.py`**
- `create_user(username, password, role, allowed_ip, name=None, description=None)` — 선택 인자 추가
- `update_user(user_id, ..., name=None, description=None)` — 선택 인자 추가, None 이 아닐 때만 UPDATE 절에 포함
- `list_users()` SELECT 에 `name, description, last_login_at` 추가
- `_user_dict(row)` 확장:
  ```python
  return {
      "id": row["id"], "username": row["username"], "role": row["role"],
      "allowed_ip": row["allowed_ip"] if "allowed_ip" in row.keys() else "",
      "name": row["name"] if "name" in row.keys() else None,
      "description": row["description"] if "description" in row.keys() else None,
      "last_login_at": row["last_login_at"] if "last_login_at" in row.keys() else None,
      "created_at": row["created_at"],
  }
  ```
- `create_session(user_id)` 내부에 `UPDATE users SET last_login_at = datetime('now') WHERE id = ?` 추가 (기존 트랜잭션과 묶음)
- `get_session_user(token)` SELECT 에 `u.name` 추가 — 헤더에서 차후 "홍길동 (testbot)" 표시 활용 여지 남김 (현재 UI 변경은 범위 밖)

**`api/auth.py`**
- `UserCreateRequest` 에 `name: Optional[str] = None`, `description: Optional[str] = None` 추가
- `UserUpdateRequest` 에 동일 추가
- `add_user`, `edit_user` 핸들러에서 body.name/body.description 전달

### 4.3 프론트엔드 — 계정 관리 UI

**`js/admin-settings.js`**

_렌더_
- 테이블 헤더 확장:
  ```
  ID | Username | Name | Role | IP | Last Login | Created | Actions
  ```
- `_loadUsersTable` 행 렌더에 `u.name`, `u.last_login_at` 셀 추가 (없으면 `-` 표시)
- description 은 행에 직접 표시하지 않고 Name 셀 `title` 속성으로 툴팁 표시 (행 폭 절약). 또는 Edit 모달에서만 노출 — 표시 정책은 작업 중 확정

_추가 폼_
- 기존 `admin-users-add-form` 에 Name / Description 입력 2개 추가
  ```html
  <input type="text" id="admin-new-user-displayname" placeholder="Name (선택)">
  <input type="text" id="admin-new-user-desc" placeholder="Description (선택)">
  ```
- `_addUser` body 에 name/description 포함
- CSS: 폼이 길어지므로 줄바꿈 레이아웃 확인 필요 (`css/admin-settings.css`)

_Edit 모달_
- Name / Description 필드 추가 (Password 아래)
- 현재값 prefill, 변경 시에만 PUT body 포함

### 4.4 프론트엔드 — 대시보드 연동 (Plan-41과 접점)

- Plan-41 `top_users` 응답의 각 항목에 `name` 포함 (백엔드가 users 테이블 JOIN)
- 대시보드 렌더:
  ```
  홍길동 (testbot)        ← name 있음
  a12345                  ← name 없음 (username 단독)
  ```
- Plan-42 없이 Plan-41 이 먼저 머지돼도 동작 (name 필드가 없으면 username 만 표시)

### 4.5 기타

- `platform-header.js` 는 **변경 안 함** — 헤더 공간 좁아서 사번 단독 유지. Name 추가 표시는 별도 합의 후.
- `js/auth.js` — `AuthState.user` 에 name 이 추가되지만, 기존 코드는 username 참조라 무변화

---

## 5. 영향 분석

| 영역 | 기존 동작 | 변경 후 |
|------|-----------|---------|
| 로그인 | username+password | 동일 (+ last_login_at 갱신 1쿼리) |
| 세션 | httpOnly 쿠키 | 동일 |
| RBAC | role 기반 | 동일 |
| 헤더 사용자 표시 | username | 동일 |
| 기존 계정 | 전 필드 채워짐 | name/description/last_login_at = NULL 허용 |
| `/auth/me` 응답 | id/username/role/created_at | + name (세션 조회 확장) |
| `/auth/users` 응답 | 6필드 | + name/description/last_login_at |
| 계정 관리 테이블 | 6열 | 8열 (Name, Last Login 추가) |
| Add 폼 | 4필드 | 6필드 |
| Edit 모달 | 3필드 | 5필드 |
| Plan-41 top_users | username | name 우선 + username 폴백 |

### 호환성

- **기존 `settings.json` / DB 보존**: 컬럼 추가만, DELETE/DROP 없음
- **구 프론트엔드가 새 백엔드 호출**: 응답에 새 필드 추가돼도 무시 → 문제 없음
- **새 프론트엔드가 구 백엔드 호출**: 해당 없음 (동시 배포)
- **users.json 등 파일 기반 저장 부재**: auth DB 단일 소스라 DB 마이그레이션으로 끝남

### 데이터 이관

- 기존 계정의 name/description 은 NULL 유지. 관리자가 Edit 으로 채움.
- last_login_at 은 Plan-42 머지 이후 첫 로그인부터 기록됨. 소급 안 함.

---

## 6. 작업 구성 (단일 릴리즈)

### Step 1: DB 마이그레이션
- `auth.py:init_db()` 에 3개 `ALTER TABLE ADD COLUMN` try/except 추가
- `CREATE TABLE` 정의에도 컬럼 포함 (신규 DB)

### Step 2: 백엔드 헬퍼·API
- `create_user`, `update_user`, `_user_dict`, `list_users` SELECT 확장
- `create_session` 내부에 last_login_at UPDATE 추가
- `get_session_user` SELECT 에 name 추가 (description/last_login_at 은 세션 응답 제외 — 불필요)
- `UserCreateRequest`, `UserUpdateRequest` 에 name/description 추가
- 단위 테스트: create/update/list 3케이스

### Step 3: 계정 관리 UI
- 테이블 렌더 확장 (헤더·행·콜스팬)
- Add 폼 확장
- Edit 모달 확장 + prefill
- description 표시 정책: 초기 툴팁(Name 셀 `title`), 사용 피드백 후 열로 승격 고려

### Step 4: Plan-41 top_users 연동 (선택)
- Plan-41 머지 후라면 `get_top_users` 에 users JOIN 추가
- Plan-41 먼저 머지된 경우 본 Step 에서 후속 커밋

### Step 5: 검증
- 기존 testbot 계정: name/description NULL 상태로 목록·에디트 정상 동작
- 신규 계정 생성: name 채워서 생성 → 테이블·대시보드 표시 확인
- Edit: name/description 변경 저장 → 재조회 일치
- 로그인: last_login_at 갱신 확인
- Plan-41 연동 시: 활발한 사용자 위젯에서 name 폴백 동작

---

## 7. 영향 범위 (파일)

| 파일 | 성격 |
|------|------|
| `backend/services/auth.py` | 스키마 ALTER, create/update/list/_user_dict/create_session/get_session_user 확장 |
| `backend/api/auth.py` | UserCreateRequest/UserUpdateRequest 확장, 핸들러 인자 전달 |
| `js/admin-settings.js` | _renderUsersPanel / _loadUsersTable / _addUser / _editUserInline 확장 |
| `css/admin-settings.css` | 추가 입력 필드 레이아웃 (필요 시) |

**건드리지 않음**: `js/auth.js`, `js/platform-header.js`, `login.html`, `launcher.html`, 서브시스템 HTML 들

## 8. 리스크

- **마이그레이션 실패**: 기존 DB 에서 `ALTER TABLE` 실패 시 서버 기동 막힘 → try/except 필수 (기존 allowed_ip 패턴 재사용)
- **동시 로그인 last_login_at 경합**: 동일 사용자 동시 로그인 시 UPDATE race — SQLite WAL 단일 트랜잭션으로 안전. 손실돼도 의미 없는 수준
- **사번 이외 개인정보 저장 부담**: name 은 이름·별명 수준이면 사내 폐쇄망 기준 문제 없음. description 이 부서·연락처 같은 개인정보 포함 여부는 운영 정책으로 판단 (자유 텍스트라 강제 불가)
- **테이블 폭 증가**: 8열이 되면 좁은 화면에서 가로 스크롤 → description 툴팁 처리로 완화
- **last_login_at 만 보고 비활성 계정 판단 주의**: Plan-42 이전 로그인은 기록 안 됨. "최근 N일 미접속" 필터는 Plan-42 머지 후 N일 경과 시점부터 신뢰 가능

## 9. 미포함 (의도적 제외)

- 헤더에 "홍길동 (testbot)" 표시 — 별도 합의 후
- 프로필 이미지·이메일·전화번호 — 폐쇄망 내부 도구 범위 초과
- Active Directory / LDAP 연동 — 해당 없음 (폐쇄망 독립)
- 사용자 셀프 프로필 편집 — admin 전용 유지 (셀프 비밀번호 변경도 현재 없음, 별도 계획)
- 소급 last_login_at (auth DB 로부터 유추 불가)
- 감사 로그 (로그인 이력 전체) — 필요 시 별도 테이블. 본 계획은 "마지막 1건" 한정

## 10. 합의가 필요한 결정

1. **description 표시 위치**: 테이블 열 추가 vs Name 셀 툴팁 vs Edit 모달 전용 → **Name 툴팁 + Edit 모달**(제안)
2. **마지막 접속일 시각 포맷**: ISO 원문 vs "N분 전" 상대 표기 → 목록은 YYYY-MM-DD, 툴팁에 전체 timestamp (제안)
3. **Plan-42 머지 시점**: Plan-41 이전 vs 이후 → **Plan-41 직전 권장** (대시보드 머지 시 name 즉시 활용 가능)
4. **기존 testbot 계정 이름**: NULL 유지 vs 초기값(name="테스트봇") 채움 → **NULL 유지, 관리자가 사후 편집**

---

## 11. 관련 문서

- [Plan-41 대시보드 재설계](./41-dashboard-platform-wide.md)
- `backend/services/auth.py` — 현 구현
- `backend/api/auth.py` — 현 구현
- `js/admin-settings.js:1154-1364` — 현 계정 관리 패널
