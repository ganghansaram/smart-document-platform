# Plan-61 — Author 셸("빈 방") 구축

> **상태: ✅ 완료 (2026-06-22) — 셸·진입 홈 구현·검증 통과.** 실제 저작/합성 기능은 후속 Phase. (프로덕션 tar 이미지 반영 = `docker compose build nginx` 재빌드 시점에 — `COPY *.html` 자동 포함)
> 작성: 2026-06-20 · 갱신: 2026-06-21 (Claude Design 시안 v2 기준 확정) · 트리거: Author 컨셉 합의(시나리오 B 채택) → "생산 허브" 구축의 1단계 = 빈 방 짓기
> **🎨 레이아웃 확정본: `workbench/reports/claudedesign_260621/Author Home v2.dc.html` + 핸드오프 `author-home-handoff.md`** (Claude Design 산출, 우리 `tokens.css`·`components.css`·`platform-header.css` verbatim 소비 확인). ⚠️ `.dc.html`은 React 런타임 의존 **스펙**이지 코드 아님 — 바닐라 3파일로 이식.
> 근거 문서: `workbench/reports/author-concept-research-2026-06-18.md` (v0.2, 시나리오 B) · `workbench/reports/author-home-mockup-v2.html` (자작 시안, 이력) · `workbench/plans/icebox/24-author-system.md` (합성 원안) · `workbench/plans/60-doc-authoring-export.md` (저작 자산 출처)
>
> **📌 위치**: Author 이니셔티브의 **Phase 1**. 컨셉 문서 §10 의 5단계 중 "Phase 1 — Author 셸 신설"에 해당. 이관(Plan-60 편집기)·합성(Plan-24)은 본 계획 범위 밖(후속).

## 🧭 현황 한눈에 (Status Dashboard)

> **핵심 성격 = "방만 짓는다".** 화면·테마·네비·인증·푸터는 완성도 있게, 실제 가구(글쓰기·합성 동작)는 비워두되 "곧 제공" 자리표시. 빈 껍데기지만 **싸구려로 안 보이게** 하는 것이 이 단계의 목표.

| 핵심 결정 | 값 |
|------|------|
| 레이아웃 | **Claude Design 시안 v2 확정 채택** (`claudedesign_260621/Author Home v2.dc.html`) — "생산 허브 홈" 패턴 |
| 아이콘 | **인라인 라인 SVG**(stroke=currentColor) — 이모지 금지 (헤더 SVG 체계 정합) |
| 상태 모델 | **작성 문서 = 상태칩 없음**(이 플랫폼엔 발행/검토 라이프사이클 없음 → 제목·작성자·수정일만). 합성 카드만 단색 단계칩 1종 |
| 테마 | `tokens.css` 변수 **소비만** — 시안이 우리 토큰을 verbatim 소비 확인. 색 100% `var()` |
| 셸 무게 | 가볍게 — 편집기 번들(TUI/marked/katex) **로드 안 함**(이관 단계로 이월) |
| 작성문서 목록 | **실데이터** — 기존 `GET /api/authored` 연동(거의 공짜, 생동감). 카드/리스트 뷰 토글 |
| 모드 카드 액션 | **자리표시("곧 제공")** — 실연결은 후속 Phase(Strangler 순서 유지) |
| 정직한 빈 상태 | resume 바·합성 카드는 시안상 **목** → 셸 출시 시 **목 비노출**(resume OFF·합성 empty-state). "가짜로 채운" 느낌 회피 |
| 활성화 | 런처 카드 + 헤더 스위처 **동시** 잠금 해제 |

## 📋 진행 상태 (Progress Tracker) — ✅ 전 항목 완료 (2026-06-22)

- [x] **A. 런처 카드 활성화** (2026-06-22) — `launcher.html` `card-author` `disabled`·뱃지 제거 + `href=author.html` + fade-out 전환 핸들러
- [x] **B. 헤더 스위처 활성화** (2026-06-22) — `js/platform-header.js` `systems[]` author 항목 `disabled`/`badge`/`badgeClass` 제거 + `href=author.html`
- [x] **C. `author.html` 셸 신설** (2026-06-22) — CSS 로드(tokens→scrollbar→toast→components→platform-header→author→platform-footer) + `visibility:hidden` 가드 + 본문 골격(§4) + 푸터
- [x] **D. `css/author.css` 신설** (2026-06-22) — 시안 인라인 → 클래스 이식, `tokens.css` 변수 소비. **하드코딩 색 = `#fff` 1건뿐**(accent 위 텍스트, platform-header.css 관례). 다크/반응형(880·560)
- [x] **E. `js/author.js` 신설** (2026-06-22) — `authRequired:true`(미로그인→login) + onAuth RBAC 바디클래스 + 테마(localStorage `theme`) + 작성문서 실연동(`/api/authored`, 카드/리스트 토글 `author-view`) + 진입타일/새문서 "곧 제공" 토스트 + 합성 empty-state + Explorer 딥링크(`index.html?page=`)
- [x] **G. Docker 통합** (2026-06-22) — `docker-compose.override.yml` 에 `./author.html` 마운트 추가(개별 HTML 마운트 방식). 프로덕션 `docker/Dockerfile.nginx` 는 `COPY *.html` 라 재빌드 시 자동 포함(수정 불요)
- [x] **F. 검증** (2026-06-22) — Playwright(docker `:80`, testbot=admin): 인증게이트(author→login 리다이렉트)·로그인후 렌더·다크전환(토큰 자동)·카드/리스트 토글·작성문서 실데이터·**카드클릭→Explorer 딥링크 열람 end-to-end(읽기 seam)**·"곧 제공" 토스트·반응형 760·**콘솔 0 에러**. 하드코딩 색 grep=#fff만

---

## 0. 한 줄 요약

**런처에서 Author 카드를 누르면 열리는, 우리 플랫폼 테마(네이비 헤더·통일 블루·라이트/다크)를 그대로 물려받은 깔끔한 "생산 허브 홈" 화면을 만든다. 방만 짓고, 글쓰기·합성 가구는 다음 단계에 넣는다.**

---

## 1. 범위 — 이번에 하는 것 / 안 하는 것

| ✅ 이번 (셸) | ⏭️ 후속 Phase |
|---|---|
| 런처 Author 카드 활성화 | 빈 문서 작성 **실제 동작** (= Plan-60 편집기 이관, Strangler) |
| 헤더 시스템 스위처 Author 활성화 | 합성 워크벤치 (Plan-24: 소스→추출→매트릭스→AI 초안) |
| `author.html` 셸 + 진입 홈 레이아웃 | 합성 백엔드 API (`/api/author/*`) |
| `css/author.css` (토큰 정합) | Verify 검증 연계 |
| `js/author.js` (셸 로직·인증·테마·목록) | Explorer/Notebook 소스 가져오기 |
| 라이트/다크·반응형·접근성·푸터·RBAC | |

> **읽기/쓰기 분할 원칙(컨셉 §4.3)**: 작성된 `.md` **열람은 Explorer 잔류**. Author 홈의 "작성 문서" 카드 클릭 → **`index.html?page=` + `encodeURIComponent(url)`** 딥링크로 Explorer 뷰어 오픈(Explorer는 외부 문서를 `?page=`로만 연다 — `app.js:579`). 쓰기만 Author, 읽기는 Explorer.

---

## 2. 설계 철학 (UI/UX · 웹디자인 전문가 관점)

**① 테마 정합 — 재정의 금지, 소비만**
Claude Design 시안은 우리 `tokens.css`·`components.css`·`platform-header.css`를 **verbatim 링크해 작성**됐다(대조 확인). 색은 100% `var()`. 단 시안 본체는 인라인 `style="..."`라, 실제 `css/author.css`는 **의미 단위로 클래스화**하되 값은 1:1 토큰 매핑한다. 색 하드코딩 0 (CLAUDE.md 하드룰). 다크모드는 토큰이 자동 처리 → 우리가 다크 색을 직접 적지 않는다.

**② 트렌드 레이아웃 — "생산 허브 홈" 패턴**
시안 구성(이어서 작업 → "새로 만들기" 진입 타일 2개 → 최근 문서 → 합성 프로젝트)은 Notion·Confluence·Google Docs 홈이 수렴한 2026 표준이다: "무엇을 만들까"를 먼저 묻고(action-first), 빈 문서 vs 합성을 큰 타일로, 그 아래 최근 작업을 그리드로. **이 v2를 설계 확정본으로 채택.**

**③ 아이콘 — 라인 SVG, 이모지 금지**
모든 아이콘은 인라인 라인 SVG(`stroke=currentColor`, 헤더·스위처와 동일 체계). 이모지(✏️🧩📄)는 "AI 급조" 인상의 주범 → 금지. (자작 v1 시안의 이모지를 v2가 SVG로 교체한 것이 핵심 개선.)

**④ 상태 모델 — 작성 문서엔 상태칩 없음**
이 플랫폼엔 **발행/배포/검토 라이프사이클이 없다**(작성 → 저장 → DOCX 내보내 워드에서 다듬어 제출). 따라서 작성 문서 카드 = **제목 · 작성자 · 수정일**만. "발행됨/검토중/초안" 같은 필드는 존재하지 않으므로 만들지 않는다. **합성 카드만** 실제 라이프사이클(소스→추출→매트릭스→선별→초안)이 있어 **단색(브랜드 악센트) 단계칩 1종** 허용. 무지개 다색 상태칩 금지.

**⑤ 미니멀·정돈**
최대폭 컨테이너(1160px) 중앙 정렬, 넉넉한 여백, 카드 호버 시 `translateY` + `box-shadow`, 진입 타일은 `--panel-shadow` 깊이, 네이비 그라데이션 헤더 계승.

**⑥ 빈 상태(empty state) 우선 — 정직하게**
합성 프로젝트·resume는 백엔드가 없어 시안에선 **목**이다. 셸 출시 시 목을 그대로 띄우면 "가짜로 채운" 인상(없애려던 그 느낌)이 재발 → **resume OFF·합성 empty-state**로 정직하게 시작. 합성 진입 타일엔 **"개발 예정" 단색 뱃지**(런처 카드 관례)만.

**⑦ 접근성·반응형**
시안의 `@media(max-width:880px)` 계승(진입 타일 2→1열, 그리드 3→2열, 560px 이하 1열), 헤딩 시맨틱, 테마 토글·스위처 `aria-label`, 뷰 토글 `aria-pressed`, `tokens.css :focus-visible` 포커스 링.

---

## 3. 파일별 변경

### A. `launcher.html` (수정)
- `card-author`: `class`에서 `disabled` 제거, `href="#"` → `href="author.html"`, 뱃지 `개발 예정`(`badge-info`) 제거(또는 `신규`로 교체).
- 클릭 핸들러: 다른 카드와 동일한 fade-out 전환(`document.body.classList.add('fade-out')` → `author.html`).

### B. `js/platform-header.js` (수정, L93 근처)
- `systems[]`의 `author` 항목에서 `disabled:true` 제거, `badge:'개발 예정'`·`badgeClass:'planned'` 제거.
- → 모든 페이지의 시스템 스위처 드롭다운에서 Author 이동 가능. **A와 반드시 동시** (한쪽만 켜면 불일치).

### C. `author.html` (신규) — 기존 서브시스템 컨벤션 그대로
- CSS 로드 순서(index.html 패턴 정합): `tokens → scrollbar → toast → components → platform-header → author.css → platform-footer`
  - `toast.css`/`toast.js` 필요 — 진입 타일 "곧 제공" 토스트 안내에 사용.
  - 셸엔 **무거운 번들 로드 안 함** (TUI/marked/katex는 이관 Phase에서).
- `<body style="visibility:hidden">` (인증 전 콘텐츠 플래시 방지).
- 본문(시안 v2 구조, 위→아래): **[이어서 작업 바(셸=OFF)] → "새로 만들기"(진입 타일 2개: 빈 문서 작성 / 합성 프로젝트[개발 예정]) → "최근 문서"(카드/리스트 토글 + 새 문서 + 전체 보기) → "합성 프로젝트"(셸=empty-state)**.
- 스크립트: `config.js → platform-header.js → auth.js → toast.js → platform-footer.js → analytics.js → author.js`.
- `initPlatformHeader({ title:'Author', currentSystem:'author', showThemeToggle:true, onAuth:... })` + `initPlatformFooter('author-footer')`.

### D. `css/author.css` (신규)
- 시안 **인라인 `style="..."` → 의미 단위 클래스로 이식**. 진입 타일·최근문서 카드/리스트 행·뷰 토글(segmented)·합성 카드(소스 핀·매트릭스 미니바)·이어서 작업 바.
- 값은 `tokens.css` 변수 1:1 매핑. **오프스케일 리터럴 정규화**: 시안의 일부 타이포(17/13.5/12.5/11.5px)·간격(22/11px)·둥글기(5px)는 우리 5단계 폰트 스케일·간격 스케일에서 벗어남 → 가까운 토큰으로 흡수하거나 의식적으로만 예외 허용.
- 배지·미니바가 `components.css`(`.badge`)로 대체 가능한지 점검 후 중복 최소화.

### E. `js/author.js` (신규) — 셸 로직만
- `onAuth(user)` → `document.body.style.visibility='visible'`, `initAnalytics('author')`, RBAC 바디 클래스(작성/합성 시작 버튼은 `auth-editor-only`로 게이팅).
- **작성 문서 섹션 = 실데이터**: `GET /api/authored`(공개·인증 불요, `document.py:227`) → `{documents:[{label, author, url, modified}]}`. 렌더 = **`label` · `author` · `modified`** (필드명 `label`임 — `title` 아님 · 상태칩 없음). 카드/리스트 뷰 토글(`localStorage` 지속). 클릭 → `index.html?page=` + `encodeURIComponent(url)` 로 Explorer 열람.
  - 목록은 공개라 **viewer도 봄**(읽기). RBAC는 *작성/합성 시작 액션*만 게이팅(`auth-editor-only`) — 목록 자체는 비게이팅.
  - 빈 응답(첫 사용·문서 0건) → 작성 문서 섹션도 empty-state("아직 작성한 문서가 없습니다 · + 빈 문서 작성").
- 시안 prop을 셸 분기로: `synthesisStatus`(셸=`beta`, "개발 예정" 뱃지) · `defaultView`(`cards`) · `showResume`(셸=`false`, 백엔드 없음).
- 진입 타일 2개 + "새 문서" → 현재는 **"곧 제공됩니다" 토스트/안내**(후속 Phase 연결 지점).
- 합성 섹션 → **empty-state CTA**(목 카드 비노출).

---

## 4. 홈 화면 구성 (확정 레이아웃 — Claude Design 시안 v2)

> 정본: `workbench/reports/claudedesign_260621/Author Home v2.dc.html`. 아래는 구조 요약(셸 출시 상태 표기).

```
┌─ 플랫폼 헤더: Author · 시스템 스위처 · testbot | Logout · 테마토글 ─┐
├────────────────────────────────────────────────────────────────────┤
│  [이어서 작업 바]  ← 시안엔 있으나 셸=OFF(백엔드 없음, showResume=false)│
│                                                                    │
│  새로 만들기                                                        │
│  ┌── ✎ 빈 문서 작성 ──────┐   ┌── ⬡ 합성 프로젝트 [개발 예정] ──┐   │
│  │ 통일 양식·MD↔WYSIWYG  │   │ 다중 소스→공통·충돌→AI 초안     │   │
│  │ 칩: SSOT·프리필·DOCX  │   │ 칩: 합성·매트릭스·Verify        │   │
│  └───────────────────────┘   └─────────────────────────────────┘   │
│                                                                    │
│  최근 문서           [▦ 카드 | ☰ 리스트]  [+ 새 문서]  [전체 보기]  │
│  ← 실데이터(GET /api/authored) · 카드 = 제목·작성자·수정일(상태칩 X) │
│  ┌──────┐┌──────┐┌──────┐   (또는 리스트: 문서명│작성자│수정일)     │
│                                                                    │
│  합성 프로젝트       [+ 새 합성]  [전체 보기]                       │
│  ← 셸=empty-state CTA ("첫 합성 프로젝트를 시작해보세요")           │
│     (시안의 목 카드: 소스 핀 + 매트릭스 미니바 = 합성 Phase에서 실연동)│
└────────────────────────────────────────────────────────────────────┘
아이콘 전부 라인 SVG · 합성 매트릭스 미니바 = 시맨틱 토큰(공통/부분/충돌/단일)
```

---

## 5. "얼마나 살아있게" — 조절 손잡이 (결정)

시안 v2는 3개 prop으로 상태를 분기한다(`synthesisStatus`/`defaultView`/`showResume`). 셸 출시 값:

- **작성 문서 목록 = 실연동** (`/api/authored` 이미 존재 → 거의 공짜, 방이 살아있어 보임) → **채택**. `defaultView=cards`.
- **모드 타일 액션 = 자리표시("곧 제공")** — "빈 문서 작성"을 지금 기존 편집기에 바로 연결할 수도 있으나, 그것은 **이관(Strangler)의 일부**라 다음 Phase로 미루는 것이 순서상 깔끔 → **자리표시 채택** (변경 가능).
- **합성 진입 = `synthesisStatus:'beta'`** ("개발 예정" 단색 뱃지). 합성 *섹션*은 목 카드 대신 **empty-state**.
- **이어서 작업 바 = `showResume:false`** — "최근 편집 1건" 백엔드 신호가 아직 없어 목이 되므로 셸에선 끈다(정직한 빈 상태). 백엔드 생기면 켠다.

---

## 6. 리스크 · 주의

| 항목 | 완화 |
|------|------|
| **시안 `.dc.html`은 코드 아님** (React 런타임 의존) | **스펙으로만** 다루고 바닐라 3파일로 손이식. 마크업 복붙 금지 — 핸드오프 §1 지침 준수 |
| **오프스케일 리터럴** (타이포 17/13.5px·둥글기 5px 등) | 색은 하드룰(통과). 타이포·간격은 이식 시 토큰 스케일로 정규화하거나 의식적 예외만 |
| **시안 목 데이터 그대로 노출** → "가짜" 인상 재발 | resume OFF·합성 empty-state로 정직하게(§5). 목 카드 미노출 |
| 런처/스위처 비동기 활성화 → 불일치 | A·B를 한 커밋에 동시 처리 |
| 셸에 편집기 번들 로드 → 무거움 | TUI/marked/katex 미로드, 셸은 경량 유지 |
| "개발 예정" 해제 → 완성 기대 | 진입 타일 자리표시 문구로 "작성/합성 준비 중" 명시(기대 관리) |
| 테마 지속성 불일치 | 타 서브시스템 테마 저장 방식(localStorage 키·`data-theme`) 점검 후 동일 적용 |
| `team_logo.svg` 시안본이 우리 것과 다름(placeholder) | 우리 실제 `css/images/team_logo.svg` 사용 |

---

## 7. 검증 (Playwright + grep)
- 런처 카드 클릭 → `author.html` 전환 · 헤더 스위처 왕복 이동
- 라이트/다크 전환 · 880px 반응형(2→1열, 3→2열)
- 작성 문서 목록 렌더(실데이터) · 클릭 시 Explorer 열람
- 인증 가드(미로그인 → login) · RBAC(viewer는 작성/합성 액션 숨김)
- 콘솔 0 에러 · 푸터 렌더
- **하드코딩 색/간격 grep 0** · CSS 로드 순서 확인

---

## 8. 다음 단계 (이 셸 이후 — Author 이니셔티브 로드맵)
- **Phase 2 — 빈 문서 작성 이관(Strangler)**: Plan-60 편집기·API·양식을 Author 셸로 재배치. Explorer "새 문서" 입구는 **alias로 한동안 유지** 후 폐기. 읽기→편집 핸드오프(URL 방식) 확정. (컨셉 §4.3, seam 3종 해소)
- **Phase 3 — 합성 워크벤치 MVP**: Plan-24 Phase 1(소스 업로드 → 구조화 추출 → 비교 매트릭스 → AI 초안). 진짜 고유 가치.
- **Phase 4 — 연동**: Explorer/Notebook 소스 가져오기, Verify 검증 왕복.

---

## 부록 — 근거 파일
- **`workbench/reports/claudedesign_260621/Author Home v2.dc.html`** (★ 레이아웃 확정본, Claude Design)
- **`workbench/reports/claudedesign_260621/author-home-handoff.md`** (★ 구현 핸드오프 — prop→로직 매핑·규칙)
- `workbench/reports/author-concept-research-2026-06-18.md` (컨셉 v0.2, 시나리오 B)
- `workbench/reports/author-home-mockup-v2.html` (자작 시안 — 이력, 시안 비교용)
- `workbench/plans/icebox/24-author-system.md` (합성 원안, Phase 3 입력)
- `workbench/plans/60-doc-authoring-export.md` (저작 자산 — Phase 2 이관 대상)
- `js/platform-header.js` L84~97 (시스템 스위처 `systems[]`, author 잠금 위치)
- `launcher.html` L218~222 (Author 카드 잠금 위치)
- `css/tokens.css`, `CLAUDE.md` (디자인 토큰·제약)
