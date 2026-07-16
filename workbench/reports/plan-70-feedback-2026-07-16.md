# Plan-70 실행 피드백 — '새 문서' 저작 기능을 Author로 교정 이전

> 실행일 2026-07-16 · 실행자 Claude (/plan-execute) · 대상 계획서 `workbench/plans/done/70-author-authoring-migration.md`

## 요약
- 완료: 교정 코어 (Phase 0~C) + code-review 지적 반영
- 변경 파일: 5개 (author.html · js/author.js · js/md-editor.js · js/app.js · css/author.css)
- code-review: Critical 0 · Warning 2 **(수정완료)** · Suggestion 3 (2 수정·1 백로그)
- 브라우저 E2E: 전 항목 통과 · 콘솔 에러: 0

## 배경 — "이관"이 아니라 "교정"
Explorer(소비 시스템)에 **잘못 구현됐던** '새 문서' 창작 편집기를 원소속인 Author(창작 시스템)로 되돌린 작업. 투기적 재배치가 아니라 설계 의도 복귀. 편집기(`MdEditor`)는 299줄 독립 오버레이라 진입점 연결 + 번들 로드 + Explorer 메뉴 제거로 완결.

**경계 (사용자 승인)**: 창작(새 문서)만 Author로 이관. **보던 .md 즉석 편집(edit-in-place)·열람·서빙렌더는 Explorer 잔류** → MdEditor 번들은 Explorer에도 남긴다(editor.js:82 openExisting 의존).

## 구현 결과

| 단계 | 상태 | 변경 파일 | 메모 |
|------|------|----------|------|
| A. 편집기 이식 | ✅ | author.html | 번들 5개 로드(CSS 2·JS 3), author.js 이전. katex·marked·purify·Monaco는 미로드(창작만, 열람 안 함) |
| A. 진입점 연결 | ✅ | js/author.js | 저작 3곳(tile-new-doc·act-new-doc·동적 new-doc 카드)→openNewDoc. synth는 comingSoon 유지 |
| A. 저장 후 갱신 | ✅ | js/author.js, js/md-editor.js | `window.onMdEditorSaved` 훅(가드드)→loadRecent. AuthState 세팅으로 작성자 프리필 |
| B. Explorer 정리 | ✅ | js/app.js | nav-new-doc-item 제거. 번들·Edit·열람은 잔류 |
| C. 검증 | ✅ | — | 아래 |

## 검증 결과

### 브라우저 E2E (Playwright, docker :80, testbot=admin)
**Author (창작):**
- 진입점 3곳 모두 편집기 오픈 ✓ (tile-new-doc·act-new-doc·동적 "＋빈 문서 작성" 카드)
- 합성 타일 `tile-new-synth`는 comingSoon 유지(편집기 안 열림) ✓
- 작성자 필드 "testbot" 자동 프리필(AuthState) ✓
- 저장 → `/api/save-markdown` 성공 → `/api/authored` 반영 → **onMdEditorSaved 훅으로 최근 문서 목록 즉시 갱신** ✓
- 편집기 닫은 뒤 페이지 정상(오버레이 display:none, 클릭 차단 없음) ✓

**Explorer 회귀 (0 회귀):**
- 헤더 '새 문서' 메뉴 부재 ✓ (Edit·Home·About·Bookmarks·Search·Login 잔존)
- MdEditor 번들 잔류 ✓ (edit-in-place 위해 유지)
- 작성 .md **열람(서빙 렌더)** 정상 ✓
- 작성 .md **edit-in-place**(Edit 버튼→openEditor→MdEditor.openExisting) 정상 — 제목 프리필·에디터 마운트 ✓
- 콘솔 에러 0 (경고 1건은 기존 index.html preload 힌트, 무관)

### 코드 품질 (code-reviewer) — 지적 반영 완료
**Warning (RBAC 게이팅 결함 — 수정완료):**
- W1: `author.html`이 `css/auth.css`(RBAC `display:none` 규칙 소재)를 로드하지 않아 `auth-editor-only` 게이팅이 무력 → viewer가 편집기를 열고 저장 시점에야 403. 백엔드 `require_editor`가 최종 방어선이라 보안사고는 아니나 UX/RBAC 결함.
  - **조치**: auth.css(옛 .main-nav 494줄 동반)는 로드하지 않고, `css/author.css`에 RBAC 규칙 1블록만 명시. Author는 platform-header 스택 첫 RBAC 사용 페이지라 이 방식이 정합.
- W2: `tile-new-doc`에 `auth-editor-only` 클래스 자체가 없어 나머지 2곳과 게이팅 불일치 → **조치**: 클래스 추가, 3곳 통일.
- **검증**: viewer 시뮬레이션(auth-editor 제거)에서 빈문서 타일·+새문서 링크·동적 카드 전부 숨김 확인. admin은 전부 노출.

**Suggestion:**
- S2(주석 stale): author.js 헤더 주석을 Plan-70 실연결 상태로 갱신 ✅
- S3(catch 침묵): 당초 `console.error` 추가했으나 **프로젝트 pre-commit 게이트가 `console.*`를 디버그 코드로 차단** → 되돌리고 "훅 실패는 저장 성공에 영향 없음, 의도적 삼킴" 주석으로 대체(게이트 우선). 리뷰어 S3는 게이트 규칙 미인지 상태의 제안이었음
- S1(lazy-load): 편집기 번들 즉시 로드 — 계획서 Acceptance "선호/후속" 항목이라 **Author 인계 백로그로 유보**

**확인된 견고성**: md-editor.js 공유 훅은 Explorer에서 항상 no-op(전역 미정의) · author.js 리스너 중복/누수 없음 · 번들 로드 순서/경로 정확 · AuthState 대입 충돌 없음(auth.js 미로드 페이지 유일 소스).

### 회귀 스팟체크 ("건드리지 않는 곳")
- Explorer 열람·서빙렌더·edit-in-place·Monaco HTML 편집·업로드 → 무변경 확인
- `js/md-editor.js` 훅은 `typeof` 가드 → Explorer 저장 흐름(loadMenuData/highlightAuthoredDoc) 무손상

### 테스트 산출물 정리
- 검증용 문서 `Plan70 검증 문서.md` 생성·검증 후 삭제, `/api/authored` 빈 목록 복구, `.gitkeep` 유지

## 검증 노트 — Playwright 실클릭 아티팩트
Playwright의 트러스티드 클릭이 이 환경(프록시 :80)에서 페이지 DOM까지 도달하지 않는 하네스 아티팩트 관측(capture/document 리스너 미발화). 제품 버그 아님을 다중 증거로 확정: 네이티브 `.click()`은 핸들러 정상 발화, `elementFromPoint`가 타일 본체 반환(가로채는 요소 없음), 오버레이 display:none. 이후 검증은 실제 제품 코드 경로(네이티브 클릭 핸들러·실 fetch)로 수행.

## UI 리뷰 해당 없음 (근거)
새 시각 컴포넌트·레이아웃·CSS를 **저술하지 않음** — 기존 `md-editor.css`/Toast UI 컴포넌트를 새 호스트에 재사용. 추가분은 번들 `<link>/<script>` 태그와 JS 배선뿐. 따라서 `/review-ui`·design-reviewer 대상 없음(신규 디자인 0). 편집기 자체 UI는 Plan-60에서 이미 검증됨.

## 사용자 관점 피드백
- 긍정: Author가 창립 목적(문서 생성)의 첫 실기능을 얻음. Explorer/Author 정체성이 동시에 깨끗해짐(소비 vs 창작).
- 우려: 기존 사용자가 Explorer '새 문서'에 익숙했다면 위치 변경 안내 필요(공지/가이드). 
- 개선: 헤더 시스템 스위처 옆 창작 퀵진입 여부는 후속 논의거리(현재 Author 홈 타일이 유일 진입).

## 잔여·후속 제안 (Author 인계 백로그 — 교정과 분리)
- [ ] 소유권(소유자·편집권·위임) — Plan-60 미완, 현재 없이 동작
- [ ] 저장 충돌 하드닝(ETag) · 표지 정책
- [ ] 작성 문서 큐레이션(삭제/개명) 위치 결정 — Author UI vs Plan-67/69
- [ ] 검색연동 소속 결정 — 읽기(소비)측이라 Explorer 몫일 수 있음
- [ ] 헤더 창작 퀵진입 여부

## 커밋 제안 (사용자 요청 시)
```
수정 [plan/70]: '새 문서' 저작 편집기를 Explorer→Author로 교정 이전

Explorer(소비)에 잘못 구현됐던 창작 편집기 진입점을 원소속 Author(창작)로
되돌린다. 편집기(MdEditor)는 독립 오버레이라 진입점 연결·번들 로드·메뉴
제거로 완결. 읽기·edit-in-place는 Explorer 잔류(번들 유지).

- author.html: 저작 편집기 번들 로드(toastui·md-editor), author.js 이전 +
  tile-new-doc 에 auth-editor-only 게이팅 추가
- js/author.js: 저작 진입점 3곳→MdEditor.openNew, 저장 후 목록 갱신 훅,
  작성자 프리필용 AuthState 세팅 (합성 타일은 comingSoon 유지)
- js/md-editor.js: 저장 성공 후 onMdEditorSaved 훅 1줄(가드드, Explorer 무영향)
- js/app.js: 헤더 nav-new-doc-item 제거
- css/author.css: RBAC 규칙(auth-editor-only 숨김) 명시 — auth.css 옛 헤더
  스타일 미동반, platform-header 스택 정합

검증: Author 진입점 3곳 오픈·저장·목록갱신·viewer 게이팅, Explorer '새 문서'
부재+열람·edit-in-place 잔류, 콘솔0 (docker :80, testbot)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
```

## MEMORY 업데이트 제안
- 비자명 교훈 없음(기존 패턴 재사용). 별도 memory 신설 불요.
