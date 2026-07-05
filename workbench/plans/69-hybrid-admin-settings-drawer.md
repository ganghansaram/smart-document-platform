# Plan-69 — Gmail식 하이브리드 관리자 설정 (빠른 설정 드로어 + 콘솔 페이지 유지)

> 상태: 🔵 draft (협의 대기) — 방향 확정, 착수 전 경량 설정 후보 선별·진입점 협의 필요
> 작성: 2026-07-05 · owner: 솔로 + Claude Code
> 트리거: 각 시스템(Explorer/Notebook/Verify/Author) 작업 중 그 시스템 설정 하나 바꾸려 `admin.html` 풀페이지로 튕겨나가는 맥락 단절
> 설계 근거: design-review (agentId `a501665a54082b791`) — 코드 근거로 "통짜 오버레이 비권장 / 하이브리드 조건부 권장" 판정

---

## 📊 진행 현황 요약

> 읽는 법: 이 계획은 **"페이지 교체"가 아니라 "가벼운 진입로 추가"** — 기존 `admin.html` 콘솔은 그대로 둔다.
> 범례: ✅ 완료 · 🟡 진행 중 · ⬜ 시작 전 · 🔵 draft

| Phase | 내용 | 예상 공수 | 상태 |
|-------|------|:-------:|:----:|
| Phase 0 | **선결 리팩토링** — `renderAdminSettings` 의 `#main-content` 하드코딩 → 컨테이너 인자 (admin.html 회귀 0) | 0.5일 | ⬜ |
| Phase 1 | **드로어 프로토타입** — 한 시스템(Notebook 후보)에 우측 빠른설정 드로어 + 경량 스키마 필드 + "전체 설정 열기 →" | 1일 | ⬜ |
| Phase 2 | **확장** — Explorer·Verify·Author 로 드로어 전개 + 각 헤더 진입점(admin 전용) | 1일 | ⬜ |
| Phase 3 | **하드닝·회귀** — ESC/포커스트랩·teardown·RBAC·다크·반응형 + admin.html 회귀 검증 | 0.5일 | ⬜ |
| **합계** | — | **~3일** | draft |

---

## Context

관리자 설정은 현재 `admin.html` 단일 페이지(폭 1060px 2컬럼 콘솔, `css/admin-settings.css:48`)에 계정관리·대시보드·시스템별 설정·메뉴편집·올클린 초기화가 모두 모여 있다. 각 서브시스템(Explorer=`index.html`, Notebook, Verify=`compare.html`, Author=`author.html`)에서 설정을 열려면 **풀페이지 전환**이 일어나 작업 맥락이 끊긴다. 사용자의 실질 페인은 "번역/비교 작업 중 **그 시스템의 토글 하나** 바꾸려 페이지를 떠나는 것"이다.

design-review 결과, **전체 콘솔을 통짜 팝업/오버레이로 옮기는 것은 비권장**이다. 근거(코드 확인): ①1060px 콘솔은 오버레이로 띄우면 배경을 다 가려 "맥락 유지" 이점 소멸, ②`renderAdminSettings` 가 `#main-content` 를 하드타겟(`admin-settings.js:362`)하는데 Explorer 도 같은 ID 를 문서 뷰어로 사용 → drop-in 시 충돌, ③설정 내부에 이미 2차 오버레이 3곳(`_openDocDeleteModal`·`_explorerAllCleanModal`·`_openEditUserModal`)+네이티브 confirm 3곳 → 설정이 팝업이면 **팝업 위 팝업**, ④대시보드(`initAnalytics('admin')` 태깅)·메뉴 트리 편집기는 오버레이에 부적합.

**업계 표준은 "무게로 이분화"** 한다: 가벼운 맥락적 설정 = 드로어/오버레이(Gmail 톱니·Figma·Notion), 무거운 관리 콘솔 = 전용 페이지(GitHub Org·Stripe·AWS). 따라서 **Gmail 방식 하이브리드** — 빠른 설정은 우측 드로어, 무거운 관리는 `admin.html` 페이지 유지 — 를 채택한다.

---

## Scope

### 포함
- **Phase 0**: `renderAdminSettings(container, opts)` 로 시그니처 확장 — `#main-content` 하드코딩 제거, 기본값으로 admin.html 호출부 무변경 동작. `opts.only=['notebook']` 식 부분 렌더 지원.
- **드로어 UI**: 각 시스템 헤더에 **admin 전용 톱니 진입점**(`auth-admin-only`) → 우측 슬라이드 **빠른 설정 드로어**. 내용 = 그 시스템의 **경량 스키마 필드** + 공통 경량 몇 개(협의로 후보 확정).
- **"전체 관리자 설정 열기 →"** 링크 — 드로어 하단에서 기존 `admin.html` 로 이동(무거운 관리의 홈).
- 드로어 저장/적용/재시작-필요 배너 동작(기존 스키마 저장 경로 재사용).
- 드로어 재료 = `css/modal.css` 공용 오버레이의 **우측 정렬 변형**(z-index 2000 단일 계층). ESC 닫기·배경클릭 닫기·포커스 트랩·명시적 teardown.

### 의도적 제외 (OUT)
- **계정관리·대시보드·메뉴트리 편집·올클린 초기화의 드로어 이식** — 무거워서 `admin.html` 페이지에 그대로 유지 (딥링크·공간·모달중첩 이유).
- **전체 콘솔 통짜 오버레이 / iframe 팝업** — design-review 비권장.
- **admin.html 재설계·제거** — 무거운 관리의 홈으로 존치.
- **모달 라이브러리 도입** — Vanilla·무빌드 제약.
- **비-admin 사용자용 설정 노출** — 드로어 진입점은 admin 전용, 백엔드 `require_admin` 최종 방어.

---

## Tasks

### A. Phase 0 — 선결 리팩토링 (저리스크)
- [ ] A1. `renderAdminSettings` 시그니처 → `renderAdminSettings(container = document.getElementById('main-content'), opts = {})`. `#main-content` 하드참조 전수 제거.
- [ ] A2. `opts.only` (렌더할 system id 배열) + `opts.mode`('page'|'drawer') 지원 — drawer 모드는 사이드바 네비 숨김, 지정 시스템 탭만.
- [ ] A3. admin.html 호출부(`admin.html:50` 부근) 무변경 동작 확인 — 회귀 0 (계정·대시보드·전체 탭 정상).

### B. Phase 1 — 드로어 프로토타입 (한 시스템)
- [ ] B1. `.settings-drawer` (우측 슬라이드) — `css/modal.css` 오버레이 변형. 열림/닫힘 트랜지션, z-index 2000, 배경 딤.
- [ ] B2. Notebook(후보) 헤더에 톱니 진입점(`auth-admin-only`) → 드로어 open → `renderAdminSettings(drawerBody, {only:['notebook'], mode:'drawer'})`.
- [ ] B3. 드로어 하단 **"전체 관리자 설정 열기 →"** → `admin.html`.
- [ ] B4. 저장·적용·재시작 배너 동작 검증 (경량 필드 몇 개로 왕복 테스트).
- [ ] B5. **경량 설정 후보 선별** — 어떤 필드를 드로어에 노출할지 확정 (협의 필요).

### C. Phase 2 — 확장
- [ ] C1. Explorer(`index.html`)·Verify(`compare.html`)·Author(`author.html`) 헤더 진입점 + 드로어 배선.
- [ ] C2. 시스템별 `only` 매핑 확정 (각 페이지 = 자기 시스템 탭 + 공통 경량).
- [ ] C3. 진입점 공통화 검토 — `platform-header` 계열에 재사용 가능한지 (중복 코드 최소화).

### D. Phase 3 — 하드닝·회귀
- [ ] D1. ESC·포커스 트랩·배경클릭 닫기, 드로어 close 시 **모듈 전역 상태 teardown**(`_menuEditorData`·`_pendingRestartItems` 등 잔여 방지).
- [ ] D2. **모달-온-모달 원천 차단** — 드로어 안에서 2차 오버레이 금지. 확인이 필요하면 **인라인 확인 행**으로.
- [ ] D3. RBAC — 진입점 `auth-admin-only`, 드로어 코드 lazy-load(비-admin 페이지에 admin 코드 상주 최소화) 여부 결정.
- [ ] D4. 다크모드·반응형(작은 화면=거의 전폭) 확인. 중복 로딩(스크립트 전역 오염) 점검.
- [ ] D5. admin.html 풀 콘솔 **회귀 0** 최종 검증.

---

## Acceptance

### 필수
- 각 시스템에서 **페이지 전환 없이** 그 시스템의 경량 설정을 드로어로 조정·저장 가능
- 드로어에서 **"전체 설정 열기 →"** 로 기존 admin.html 진입 가능
- `admin.html` 풀 콘솔(계정·대시보드·메뉴편집·초기화) **무손상** — 딥링크·새로고침·북마크 유지
- 드로어에 **2차 오버레이 없음**(모달-온-모달 0), ESC/포커스 트랩 동작
- 회귀 0 — 기존 설정 저장·재시작 배너·RBAC 무손상

### 선호
- 진입점·드로어 셸 공통화로 시스템별 중복 최소화
- 드로어 코드 lazy-load 로 비-admin 페이지 부담 0

---

## 미해결 / 협의 필요
- **경량 설정 후보 선별** (B5) — 각 시스템에서 "자주 만지는 가벼운 것"이 무엇인가? (드로어에 넣을 필드 목록 = 이 plan 의 핵심 협의 지점)
- **드로어 코드 로딩 전략** — 각 시스템 페이지에 `admin-settings.js` 상시 포함 vs 톱니 클릭 시 lazy-load. 폐쇄망·중복로딩 고려.
- **진입점 위치** — 각 시스템 헤더 어디에 톱니를? (기존 "Switch system"·테마 토글 옆)
- **Notebook 실제 진입 파일** — Notebook 시스템의 호스트 HTML 확정 필요.
- **참조 확인** — csrm-workbench 팝업이 "경량 드로어"였는지 "풀 콘솔"이었는지(사용자 확인 시 방향 보정).

## 산출물
- 코드: `js/admin-settings.js`(컨테이너 파라미터화·drawer 모드), `css/admin-settings.css` 또는 신규 `css/settings-drawer.css`, 각 시스템 HTML(`index.html`·`compare.html`·`author.html`·Notebook 호스트) 헤더 진입점, (선택) `platform-header` 계열 공통화
- 문서: 본 plan 갱신, 필요 시 `workbench/reports/` 회귀 노트

## Notes
- **성격 = 교체 아닌 "추가".** admin.html 은 그대로, 가벼운 진입로만 신설 → 회귀면 최소.
- **업계 표준 정합**: 무게 이분화(경량=드로어 Gmail/Figma/Notion · 무거운 콘솔=페이지 GitHub/Stripe/AWS). 통짜 팝업은 표준 아님.
- Phase 0(컨테이너 파라미터화)은 **어떤 최종안이든 여는 열쇠** — 이것만 해도 향후 유연성 확보.
- 폐쇄망·Vanilla·무빌드·모놀리식 제약 유지. 모달 라이브러리 금지.
- design-review 원문 근거: `admin-settings.js:362`(#main-content), `:1200`·`:902`·`:1545`(2차 오버레이), `css/admin-settings.css:48`(1060px), admin.html 이 `css/modal.css` 미로드(공용 오버레이와 admin 자체 오버레이 별개).

## Progress Log
- 2026-07-05 — plan 생성. design-review(agentId `a501665a54082b791`) 로 컨셉 검증 → "통짜 오버레이 비권장, Gmail식 하이브리드 조건부 권장" 판정 반영. Phase 0(선결 파라미터화)~Phase 3(하드닝) 구조화. 핵심 협의 지점 = 경량 설정 후보 선별. **착수 전 사용자 검토 대기.**
