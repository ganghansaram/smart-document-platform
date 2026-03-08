# Smart Document Platform 중간점검 계획서

> 작성일: 2026-03-08
> 최종 수정: 2026-03-08
> 목적: 코드 구조 점검, UI/UX 테마 표준화, 확장 준비를 위한 중간점검 로드맵
> 진행: `feature/platform-review` 브랜치에서 Phase별 작업 → 검토 → 커밋 → 다음 Phase
>
> ## 진행 현황
> | Phase | 상태 | 비고 |
> |-------|------|------|
> | Phase 1 | ✅ 완료 | theme-guide.md 작성 + 정비, /review-ui 스킬 생성, 프로토타입 삭제 |
> | Phase 2 | ✅ 완료 | tokens.css 분리 + 토큰 통합 |
> | Phase 3 | ✅ 완료 | 헤더/푸터/login 하드코딩 색상 → 토큰 변수화, 다크 오버라이드 6개 제거 |
> | Phase 4 | ✅ 완료 | Explorer 14개 CSS: 하드코딩 색상→토큰, 불필요 다크 오버라이드 제거, 시맨틱 색상 통일 |
> | Phase 5 | ✅ 완료 | 인라인 CSS 1,435줄→css/translator.css 분리, ~115건 토큰화, --text-color 수정, 다크 오버라이드 18건 제거, --color-success-btn 토큰 신설 |
> | Phase 6 | ✅ 완료 | admin-settings.css --as-* 20→7개로 통합, analytics.css --ad-* 다크 오버라이드 5개 제거, 포커스 링·헤더·스피너 토큰화 |
> | Phase 7 | 🔲 대기 | (선택) |
> | Phase 8 | 🔲 대기 | (선택) |

---

## 1. 현황 진단

### 1.1 프로젝트 이력

Explorer(웹북) → 플랫폼 통합(Launcher) → Translator 추가로 점진적으로 성장한 프로젝트입니다. 처음부터 설계된 구조가 아니기 때문에, 각 단계에서 기능 우선으로 개발되면서 다음과 같은 기술 부채가 누적되었습니다.

### 1.2 코드 분석 요약

#### 프론트엔드

| 항목 | 현황 | 심각도 |
|------|------|--------|
| **translator.html 비대화** | 4,027줄 (CSS 1,436줄 + JS 2,428줄 인라인), CSS 클래스 ~130종 | 높음 |
| **CSS 변수 중복** | main.css(12개) / admin-settings.css(23개 `--as-*`) / analytics.css(12개 `--ad-*`)가 각각 독립 네임스페이스로 동일 색상(`#0066cc`, `#5ba3f5` 등) 재정의 | 높음 |
| **하드코딩 색상** | translator.html: `#0066cc`×26, `#58a6ff`×21, `#dde4e8`×20, `#238636`×10 등 | 높음 |
| **컴포넌트 파편화** | 버튼 7종, 오버레이 5종, 폼 입력 3종, 카드 3종이 각각 독립 구현 | 중간 |
| **다크모드 불균일** | login.html/launcher.html 미지원, translator.html 인라인 하드코딩, SVG data-URI 색상 고정 | 중간 |
| **타이포그래피 미준수** | typography.md 기준표 존재하나 실제 코드에서 10px~48px 18종 사이즈 혼용 | 중간 |
| **스페이싱/라운딩 토큰 부재** | padding 임의값, border-radius 10종(3~12px+50%) 혼용 | 중간 |
| **z-index 비체계** | 2~20000까지 산발적 할당 (20000 login-gate, 10000 switcher/glossary, 5000 toast 등) | 낮음 |

#### 백엔드

| 항목 | 현황 | 심각도 |
|------|------|--------|
| **API 구조** | Router 8개 분리, Depends 패턴 일관 (양호) | - |
| **에러 처리** | HTTPException 일관 사용 (양호), 구조화된 로깅 부재 | 낮음 |
| **translator_service.py** | 1,087줄 단일 파일, 클래스 구조 없음 | 낮음 |
| **PDF 로직 중복** | translator_service.py와 text_translator.py 간 유사 패턴 | 낮음 |

**종합**: 백엔드는 비교적 양호합니다. **프론트엔드 CSS/테마 통합이 최우선 과제**입니다.

### 1.3 페이지별 현황

| 페이지 | 인라인 CSS | 인라인 JS | 외부 CSS | 외부 JS | 다크모드 |
|--------|-----------|----------|---------|--------|---------|
| **login.html** | 210줄 | 77줄 | 없음 | config.js만 | 미지원 (고정 다크 배경) |
| **launcher.html** | 174줄 | 40줄 | 2개 (header, footer) | 3개 | 미지원 (고정 그라디언트) |
| **index.html** | 0줄 | 0줄 | 14개 | 16개 | 지원 |
| **translator.html** | 1,436줄 | 0줄 (별도 블록 2,428줄) | 3개 (header, footer, tree-menu) | 4개 | 부분 지원 |
| **admin.html** | 0줄 | 35줄 | 4개 | 5개 | 지원 |

### 1.4 기존 Claude Code 스킬

| 스킬 | 파일 | 용도 |
|------|------|------|
| `/commit` | `.claude/skills/git-commit/SKILL.md` | 한국어 커밋 메시지 규칙 |
| `/test-backend` | `.claude/skills/test-backend/SKILL.md` | FastAPI API 일괄 테스트 |
| `/update-docs` | `.claude/skills/update-docs/SKILL.md` | 코드 변경 → 문서 자동 갱신 |

---

## 2. Q&A

### 웹 템플릿/테마 사이트 활용

**결론: 참고는 하되, 직접 도입은 비권장**

| 방식 | 장점 | 단점 |
|------|------|------|
| **템플릿 구매/적용** (AdminLTE, Metronic 등) | 완성도 높은 UI 즉시 사용 | Bootstrap/React 의존 → 폐쇄망 Vanilla JS 제약 위반 |
| **참고 사이트 지정** | 시각적 방향성 설정에 유용 | 구현은 직접 해야 함 |
| **디자인 토큰 문서 작성** (권장) | 제약 준수, 점진적 적용 | 초기 작성 비용 |

참고하고 싶은 사이트 URL/스크린샷/키워드("GitHub 스타일", "깔끔한 대시보드" 등)를 공유해 주시면 **디자인 언어만 추출**하여 테마 기준 문서에 반영합니다.

### 서브에이전트 vs 기준 문서

**결론: 기준 문서 + 스킬 조합이 최적**

클로드코드의 서브에이전트는 대화 중 임시로 생성되는 작업자이며, 영구 저장이 안 됩니다. 대신 **스킬**(`.claude/skills/*.md`)과 **기준 문서**(`memory/*.md`)를 조합하면 동일한 효과를 영구적으로 얻을 수 있습니다.

```
기준 문서 (memory/theme-guide.md) = 규칙 정의 ("무엇을" 지켜야 하는지)
스킬 (.claude/skills/*)           = 작업 절차 ("어떻게" 실행하는지)
```

Phase 1에서 `/review-ui` 스킬을 만들었습니다. `/check-theme`는 Phase 2+ 시점에 필요 시 생성합니다.

---

## 3. 단계별 실행 계획

### 진행 순서 요약

```
Phase 1: 기준 문서 & 스킬 작성          ✅ 완료
Phase 2: CSS 토큰 통합 (main.css :root) ← 전체 변수 시스템 구축
Phase 3: 플랫폼 공통 (login, launcher)  ← 가장 작은 범위부터
Phase 4: Explorer                      ← 가장 큰 시스템
Phase 5: Translator                    ← 인라인 CSS 분리 포함
Phase 6: 관리자 설정                    ← 독립적 스타일 정리
Phase 7: JS 구조 개선 (선택)            ← 동작 문제 없으면 후순위
Phase 8: 백엔드 경량 리팩토링 (선택)     ← 확장 시점에 진행
```

---

### Phase 1: 테마 기준 문서 & 스킬 작성 ✅

> **목표**: 모든 후속 Phase의 기준점이 되는 문서와 반복 작업용 스킬을 작성한다.
> **산출물**: `memory/theme-guide.md`, `.claude/skills/review-ui/SKILL.md`
> **영향 파일**: 없음 (문서 작성만)
> **완료일**: 2026-03-08
>
> **완료 내역:**
> - `memory/theme-guide.md` 작성 (14개 섹션, Claude memory 경로)
> - `.claude/skills/review-ui/SKILL.md` 생성 (7개 점검 항목)
> - `memory/typography.md` → theme-guide.md로 흡수 후 삭제
> - 프로토타입 3개 삭제 (theme-preview-*.html)
> - `/check-theme` 스킬은 Phase 2+ 시점으로 이연
>
> **1차 정비 결정 사항:**
> - A1: border-radius 12종 → 5종 (sm:4 / md:6 / lg:8 / xl:12 / pill:50%)
> - A2: 포커스 링 3종 → 1종 (`0 0 0 2px rgba(0,102,204,0.15)`)
> - A3: 오버레이 배경 → `rgba(0,0,0,0.5)` + `blur(4px)` 통일 (login gate 예외)
> - A4: 시맨틱 색상 변수명 확정 (`--color-success/warning/error/info`)
> - B1: box-shadow 7종 → 4종 (sm/md/lg/xl) 확정
> - B2: 채팅 입력 24px pill 유지 (메신저 맥락)
> - B3: 퀵 버튼 16px pill 유지 (B2와 연동)

#### 작업 지시

```
Phase 1을 진행해줘.

1) memory/theme-guide.md 작성
   현재 코드베이스를 분석하여 아래 항목을 정리해줘.
   기존 memory/typography.md 내용을 흡수·통합하고, typography.md는 삭제해.

   - 색상 팔레트
     · Primary, Secondary, Semantic(success/warning/danger/info), Neutral 계열
     · 라이트/다크 모드 매핑 (현재 main.css 기준 + 누락 색상 추가)
     · CSS 변수 네이밍 컨벤션: --color-*, --bg-*, --text-*, --border-* 형태로 통일
   - 타이포그래피 (typography.md 흡수)
     · 9단계 사이즈 스케일 (XL~Micro)
     · 웨이트 규칙, 행간
     · 헤더 바 표준
   - 스페이싱 스케일
     · 4px 기반: xs(4), sm(8), md(16), lg(24), xl(32), 2xl(48)
   - border-radius 스케일
     · sm(4), md(6), lg(8), xl(12), full(50%)
   - box-shadow 스케일
     · sm, md, lg, focus-ring (라이트/다크 각각)
   - z-index 체계
     · 레이어별 범위 할당 (base, dropdown, sticky, overlay, modal, toast, gate)
   - 트랜지션 표준
     · fast(0.15s), normal(0.2s), slow(0.3s)
   - 컴포넌트 규격
     · 버튼: primary, secondary, ghost, danger, icon-only (padding, radius, 색상)
     · 입력 필드: text, select, textarea, toggle (padding, radius, focus 스타일)
     · 카드: padding, radius, shadow, border
     · 오버레이/모달: 배경색, blur, radius, shadow
     · 토스트: 위치, 색상, 애니메이션
     · 배지/태그: padding, radius, 색상 매핑
     · 툴바: 높이, 간격, 버튼 크기
   - 레이아웃 규칙
     · 헤더 60px, 사이드바 너비, 패널 간격
   - 다크모드 전환 규칙
     · 셀렉터: body[data-theme="dark"]
     · SVG 아이콘 처리 방식 (filter vs 별도 파일)
   - View Transition 규칙 (기존 typography.md에서 이관)

2) .claude/skills/review-ui/SKILL.md 작성
   지정된 HTML/CSS 파일을 memory/theme-guide.md 기준으로 점검하는 스킬.
   점검 항목: 하드코딩 색상, 비표준 사이즈, 비표준 radius/shadow, z-index 범위 위반,
   다크모드 누락, 컴포넌트 클래스 미사용.
   결과를 테이블로 출력하는 형식.

3) .claude/skills/check-theme/SKILL.md 작성
   전체 CSS 파일을 스캔하여 theme-guide.md 위반 사항을 요약 리포트로 출력하는 스킬.
   위반 건수, 파일별 분포, 우선 수정 대상 순으로 정리.

4) memory/MEMORY.md 업데이트
   theme-guide.md 참조 라인 추가.

5) memory/typography.md 삭제 (theme-guide.md로 통합됨)

완료 후 변경 파일 목록과 theme-guide.md의 목차를 보여줘.
```

---

### Phase 2: CSS 토큰 분리 및 통합

> **목표**: main.css에서 `:root` 변수를 `css/tokens.css`로 분리하여 전 페이지 공유 가능하게 하고, 시맨틱 색상·그림자·포커스 링 토큰을 추가한다. 다른 CSS 파일의 중복 변수를 `:root` 참조로 교체한다.
> **영향 파일**: 새 파일 `css/tokens.css`, `css/main.css`, `css/admin-settings.css`, `css/analytics.css`, 전 HTML 파일 (link 추가)
> **위험도**: 낮음 (변수 분리만, 값 변경 없음)

#### 현재 문제

```
main.css         → :root 12개 변수 + Explorer 전용 레이아웃 혼재
admin.html       → main.css 미로드 → :root 변수 참조 불가
translator.html  → main.css 미로드 → :root 변수 참조 불가
                 → 멀티 페이지에서 공유 변수를 사용할 수 없는 구조
```

#### 작업 지시

```
Phase 2를 진행해줘. theme-guide.md를 참조해서 작업해.

1) css/tokens.css 생성
   main.css의 :root 블록과 body[data-theme="dark"] 변수 블록을 tokens.css로 이동.
   기존 12개 변수는 이름 그대로 유지.
   추가 변수:
   - 시맨틱 색상: --color-success, --color-warning, --color-error, --color-info
   - 그림자: --shadow-sm, --shadow-md, --shadow-lg, --shadow-xl
   - 포커스 링: --focus-ring
   스페이싱/라운딩/트랜지션은 변수화하지 않음 (기준서에 기준값으로만 기록).

2) main.css에서 :root 블록 제거
   tokens.css로 이동한 변수 블록을 main.css에서 제거.
   main.css는 Explorer 레이아웃 + 컴포넌트만 남김.

3) 전 HTML 파일에 tokens.css 로드 추가
   모든 HTML 파일(index.html, admin.html, translator.html, launcher.html, login.html)의
   CSS 링크 최상단에 <link rel="stylesheet" href="css/tokens.css"> 추가.

4) admin-settings.css 변수 교체
   --as-primary → var(--active-color), --as-toggle-on → var(--active-color) 등
   :root와 동일한 값을 참조로 교체. 다크 블록에서 자동 해결되는 변수 제거.
   admin 고유 변수(--as-tab-bg, --as-restart-* 등)는 유지.
   danger/success/warning은 shade가 다르므로 유지 (Phase 6에서 육안 확인 후 결정).

5) analytics.css 변수 교체
   --ad-primary → var(--active-color), --ad-success → var(--color-success) 등
   :root와 동일한 값을 참조로 교체. 다크 블록에서 자동 해결되는 변수 제거.
   analytics 고유 변수(--ad-bar-color, --ad-bar-chat 등)는 유지.

6) 전 페이지 브라우저 테스트
   모든 페이지를 라이트/다크로 열어 시각적 변화 없는지 확인.

완료 후:
- tokens.css 변수 목록
- 변경된 파일 목록과 각 파일의 변경 줄 수
- 제거된 중복 변수 수
- 남아있는 고유 변수 목록
```

---

### Phase 3: 플랫폼 공통 (헤더/푸터, login, launcher) — 하드코딩 색상 → 토큰 변수화

> **목표**: 플랫폼 공통 CSS와 독립 페이지의 하드코딩 색상을 tokens.css 변수로 교체하여 유지보수성을 확보한다.
> **영향 파일**: `css/platform-header.css`, `css/platform-footer.css`, `login.html`, `launcher.html`
> **위험도**: 낮음 (독립 페이지 + 공통 헤더/푸터, 기능 변경 없음)
> **방침**: 공유 컴포넌트 클래스(.btn, .overlay 등)는 이 단계에서 만들지 않는다. Phase 4(Explorer) 진행 시 실제로 필요해지는 시점에 생성한다. 사용처 없는 범용 클래스를 미리 만드는 것은 과도한 엔지니어링이다.

#### 현재 문제

```
platform-header.css → 하드코딩 색상 다수 (#fff, #e2e8f0, rgba 등)
platform-footer.css → 하드코딩 색상 있을 수 있음
login.html          → 210줄 인라인 CSS, 하드코딩 색상 15종 (고정 다크 배경, 테마 전환 불필요)
launcher.html       → 174줄 인라인 CSS, 하드코딩 색상 7종 (고정 다크 배경, 테마 전환 불필요)
```

#### 작업 지시

```
Phase 3를 진행해줘. theme-guide.md를 참조해서 작업해.
공유 컴포넌트 클래스 생성은 하지 않는다 (Phase 4에서 필요 시 생성).

[3-1] platform-header.css 점검
   - 하드코딩 색상을 tokens.css CSS 변수로 교체
   - 시스템 스위처 드롭다운의 z-index를 theme-guide.md 체계에 맞게 조정
   - SVG data-URI 아이콘의 다크모드 처리 방식 검토 및 개선

[3-2] platform-footer.css 점검
   - 하드코딩 색상을 CSS 변수로 교체 (있는 경우)

[3-3] login.html 정리
   - 인라인 CSS에서 하드코딩 색상을 tokens.css 변수로 교체
   - login은 항상 다크 배경이므로 테마 전환 불필요,
     다만 색상값은 CSS 변수로 교체하여 유지보수성 확보
   - 인라인 CSS는 유지 (login은 독립 페이지이므로 외부 분리 불필요)

[3-4] launcher.html 정리
   - 인라인 CSS에서 하드코딩 색상을 CSS 변수로 교체
   - 카드 스타일에 공통 토큰(radius, shadow, transition) 적용
   - launcher도 고정 그라디언트 배경이므로 테마 전환 불필요,
     색상값만 CSS 변수 기반으로 정리
   - 인라인 CSS는 유지

완료 후:
- 각 파일별 변경 요약 (교체한 하드코딩 색상 수)
- 브라우저에서 확인할 페이지: login.html, launcher.html
- Playwright 스크린샷 촬영 (login, launcher)
```

#### [추가] Phase 3+: 로그인 화면 2-컬럼 레이아웃 + CSS 애니메이션 소개

> **시점**: Phase 3 완료 후, 테마가 확정된 상태에서 진행
> **상세 구현안은 해당 단계 도래 시 협의**

현재 login.html은 중앙 카드형 단일 레이아웃입니다.
이를 **좌측 소개 영역 + 우측 로그인 폼**의 2-컬럼 구조로 개편합니다.

- **좌측**: CSS 애니메이션 기반의 시스템 소개/특징 시각화
  - Claude AI 로그인 화면처럼 역동적인 CSS 모션으로 플랫폼 기능을 표현
  - 실제 영상(mp4) 없이 순수 CSS 애니메이션 + HTML로 구현 (폐쇄망 호환)
  - 예: 기능별 카드가 순차 등장, 아이콘 모션, 텍스트 타이핑 효과 등
- **우측**: 기존 로그인 폼 (Phase 3에서 정리된 상태)
- 반응형: 좁은 화면에서는 소개 영역 숨김, 로그인 폼만 표시

---

### Phase 4: Explorer

> **목표**: Explorer(index.html)의 14개 외부 CSS 파일을 점검하고, Phase 2 토큰을 적용한다. 필요 시 공유 컴포넌트 클래스(.btn, .overlay 등)를 tokens.css에 생성한다.
> **영향 파일**: `css/main.css`(레이아웃), `css/tree-menu.css`, `css/content.css`, `css/ai-chat.css`, `css/editor.css`, `css/figure-popup.css`, `css/bookmarks.css`, `css/glossary.css`, `css/auth.css`, `css/search관련(main.css 내)`
> **위험도**: 중간 (가장 많은 CSS 파일, 점진적 교체 필요)

#### 현재 문제

```
css/ 디렉토리 13개 파일, 총 ~7,500줄
- 오버레이 5종 각각 독립 구현 (search, bookmarks, figure-popup, glossary, shortcuts)
- 버튼 스타일 .panel-action-btn, .toggle-btn 등 개별 정의
- 다크모드: 대부분 지원하나 SVG data-URI 아이콘(main.css 572-595줄)이 하드코딩
- 폼 입력: tree-search, ai-chat input 등 스타일 불일치
```

#### 작업 지시 (소단계 분할)

```
Phase 4를 진행해줘. theme-guide.md를 참조하고, /review-ui 스킬로 점검하면서 작업해.
아래 소단계를 순서대로 진행해줘.

[4-1] 3-패널 레이아웃 & 공통 요소 (main.css)
   대상: css/main.css의 레이아웃, 패널, 리사이즈 핸들, 토스트, 단축키 오버레이
   작업:
   - 하드코딩 색상 → CSS 변수 교체
   - 오버레이 패턴(.search-overlay 등) → .overlay 기본 클래스 활용
     (기존 클래스명은 유지하되, 공통 속성은 .overlay에서 상속)
   - border-radius, box-shadow → 토큰 변수 교체
   - SVG data-URI 아이콘 다크모드 처리 개선
     (CSS filter 방식 또는 별도 dark 변수 사용)
   - z-index → theme-guide.md 체계에 맞게 조정

[4-2] 트리 메뉴 (tree-menu.css)
   대상: css/tree-menu.css (796줄)
   작업:
   - 하드코딩 색상 → CSS 변수 교체
   - 트리 검색 입력란 → .form-input 토큰 활용
   - 트리 노드 hover/active 색상 통일
   - 다크모드 하드코딩 값 → 변수 교체

[4-3] 콘텐츠 영역 (content.css)
   대상: css/content.css (868줄)
   작업:
   - 하드코딩 색상 → CSS 변수 교체
   - content-visibility 관련 스타일은 건드리지 않음 (성능 최적화)
   - 인쇄 스타일(@media print) 유지

[4-4] AI 채팅 (ai-chat.css)
   대상: css/ai-chat.css (574줄)
   작업:
   - 하드코딩 색상 → CSS 변수 교체
   - FAB 버튼, 입력란 → 토큰 활용
   - 메시지 버블 스타일 통일
   - border-radius, shadow → 토큰

[4-5] 에디터 (editor.css)
   대상: css/editor.css (583줄)
   작업:
   - 하드코딩 색상 → CSS 변수 교체
   - 에디터 모달/오버레이 → .overlay 패턴 활용
   - 툴바 버튼 → 토큰 활용

[4-6] 팝업·오버레이 (figure-popup.css, bookmarks.css, glossary.css)
   대상: 3개 파일 (194 + 162 + 496줄)
   작업:
   - 각 오버레이의 공통 패턴(fixed, inset:0, 배경, 트랜지션) → .overlay 활용
   - 모달 컨테이너 → .modal 토큰 활용
   - 하드코딩 색상 → CSS 변수 교체
   - z-index → 체계에 맞게 조정

[4-7] 인증 UI (auth.css)
   대상: css/auth.css (473줄)
   작업:
   - 하드코딩 색상 → CSS 변수 교체
   - 로그인 게이트, 인증 모달 → 토큰 활용
   - z-index (20000, 10002 등) → 체계에 맞게 조정

완료 후:
- /check-theme 스킬로 Explorer 관련 CSS 전체 점검 결과 출력
- 각 소단계별 변경 파일과 줄 수
- 브라우저에서 확인할 화면: Explorer 홈, 문서뷰, 검색 오버레이, AI 채팅,
  용어집 팝업, 그림 팝업, 북마크, 에디터 (각각 라이트/다크)
```

---

### Phase 5: Translator

> **목표**: translator.html의 1,436줄 인라인 CSS를 `css/translator.css`로 분리하고, 토큰·공유 클래스를 적용한다.
> **영향 파일**: `translator.html`, 새 파일 `css/translator.css`
> **위험도**: 높음 (가장 큰 단일 변경, 인라인 CSS 전체 이동)

#### 현재 문제

```
translator.html 인라인 CSS 1,436줄:
- CSS 클래스 ~130종 정의
- 하드코딩 색상: #0066cc×26, #58a6ff×21, #dde4e8×20, #238636×10, #f85149×8 등
- 다크모드: [data-theme="dark"] 하드코딩 색상으로 처리
- 컴포넌트: 카드(.doc-card), 버튼(.card-btn, .translate-page-btn),
  뷰어 툴바, 마킹 시스템, AI 결과 popover, 트리 패널, 폴더 피커,
  컨텍스트 메뉴, 플로팅 위젯 등 다수
```

#### 작업 지시 (소단계 분할)

```
Phase 5를 진행해줘. theme-guide.md를 참조해서 작업해.

[5-1] 인라인 CSS → css/translator.css 분리
   - translator.html의 <style> 블록 전체를 css/translator.css로 이동
   - translator.html에 <link rel="stylesheet" href="css/translator.css"> 추가
   - <style> 블록 제거
   - 이 단계에서는 내용 변경 없이 순수 분리만 수행
   - 분리 후 브라우저에서 정상 동작 확인

[5-2] 홈 화면 상단 배너 추가
   대상: translator.html 문서 목록 화면(.view-list) 상단
   작업:
   - Explorer 홈의 배너 슬라이드쇼(js/banner.js)와 동일한 패턴으로
     Translator 홈 상단 1/3 영역에 이미지 배너 슬라이드 추가
   - 배너 내용: Translator 주요 기능/특징 소개
     (예: "PDF 원문 구조 보존 번역", "듀얼 패널 뷰어", "AI 텍스트 선택 메뉴" 등)
   - 배너 이미지는 Playwright 스크린샷 또는 placeholder로 우선 구성
   - 다크모드 대응
   - 상세 구현안은 해당 단계 도래 시 협의

[5-3] 문서 목록 화면 (카드 그리드)
   대상: .upload-zone, .doc-grid, .doc-card, .doc-card-* 관련 스타일
   작업:
   - 하드코딩 색상 → CSS 변수 교체
   - .doc-card → .card 토큰 활용 (radius, shadow, border)
   - .card-btn → .btn 계열 클래스 병행 또는 토큰 적용
   - 업로드 존 드래그 상태 색상 → 변수 교체

[5-4] 뷰어 툴바
   대상: .viewer-toolbar, .pn-btn, .translate-page-btn, .range-translate-btn,
         .engine-radio, .font-scale-btn, .zoom-btn, .scroll-sync-btn
   작업:
   - 버튼 스타일 → 토큰 활용 (padding, radius, 색상)
   - 하드코딩 색상 → CSS 변수 교체
   - select 요소 → .form-select 토큰 활용

[5-5] 듀얼 패널 뷰어
   대상: .viewer-panels, .viewer-panel, .panel-label, .pdf-page-container,
         .text-layer, .annotation-layer
   작업:
   - 하드코딩 색상 → CSS 변수 교체
   - 패널 구분선, 라벨 색상 → 변수 교체

[5-6] 마킹 시스템
   대상: .highlight, .highlight-group, .margin-marker, .marking-action-bar,
         .marking-popover, .color-palette, .memo-display, .marking-float
   작업:
   - 마킹 색상(yellow, green, red, blue)은 기능 고유 색상이므로 유지
   - UI 프레임(popover 배경, 버튼, 테두리) → 토큰 교체
   - .marking-popover → .modal 토큰 참조
   - .marking-float 드롭다운 → shadow, radius 토큰

[5-7] AI 결과 팝오버 & 컨텍스트 메뉴
   대상: .ai-result-popover, .ai-skeleton, .tp-context-menu
   작업:
   - 하드코딩 색상 → CSS 변수 교체
   - shadow, radius → 토큰
   - 스켈레톤 애니메이션은 유지

[5-8] 트리 패널 & 폴더 피커
   대상: .tree-panel-overlay, .tree-panel-trigger, .folder-picker-overlay,
         .folder-picker, .folder-picker-item
   작업:
   - 오버레이 → .overlay 패턴 참조
   - 하드코딩 색상 → CSS 변수 교체
   - 폴더 피커 모달 → .modal 토큰

[5-9] 다크모드 통합
   - translator.css의 모든 [data-theme="dark"] 블록에서
     하드코딩 색상을 CSS 변수 다크 값으로 교체
   - 불필요한 다크모드 재정의 제거 (변수 기반이면 자동 전환)

완료 후:
- /check-theme 스킬로 translator.css 점검
- translator.html의 총 줄 수 변화 (Before/After)
- 브라우저에서 확인할 화면: 문서 목록, 듀얼 뷰어, 마킹 팝오버,
  AI 결과, 트리 패널 (각각 라이트/다크)
```

---

### Phase 6: 관리자 설정 & 통계

> **목표**: admin-settings.css·analytics.css의 커스텀 변수를 tokens.css로 최대한 통합하고, 하드코딩 색상을 변수로 교체한다.
> **영향 파일**: `css/admin-settings.css`, `css/analytics.css`
> **위험도**: 중간 (변수 통합 시 색상 미세 변화 수반, 모달 스코프 제약 존재)
>
> **방침**:
> - 공유 컴포넌트 클래스(.btn, .card 등)는 생성하지 않음 — 사용처가 admin 1곳뿐이라 과도한 엔지니어링
> - 모달이 `document.body`에 appendChild되는 스코프 버그(Phase 4에서 발견)는 JS 수정이 필요하므로 Phase 7로 이연. 모달 전용 하드코딩은 현 상태 유지
> - `--as-*` / `--ad-*` 색상 차이는 비의도적이므로 tokens.css 변수로 통합

#### 현재 문제 (재분석)

```
admin-settings.css (1,208줄):
- --as-* 커스텀 변수 20개 중 토큰 참조는 3개(15%)뿐
- --as-text(#1a1a2e) ≠ --text-dark(#2c3e50) 등 비의도적 색상 차이 다수
- --as-tab-bg = --as-border-light (중복), --as-tab-text = --as-text-sub (중복)
- 변수 블록 외 하드코딩 색상 ~45건 (헤더, 토스트, 스피너, 역할 배지 등)
- 모달 입력 필드: Phase 4 스코프 버그 우회로 하드코딩 (유지)
- 포커스 링 --focus-ring 토큰 미사용 (3곳 하드코딩)

analytics.css (495줄):
- --ad-* 변수 10개 중 4개(40%)가 토큰 참조 (상대적으로 양호)
- 하드코딩 색상 1건 (#fff)
- 모달에서 변수 재선언 패턴 (동일 스코프 이슈)
```

#### 작업 지시

```
Phase 6를 진행해줘. theme-guide.md를 참조해서 작업해.

[6-1] admin-settings.css 변수 통합
   --as-* 변수를 tokens.css 변수로 교체:
   - --as-text → var(--text-dark)          (비의도적 차이, 통일)
   - --as-text-sub → var(--text-light)     (비의도적 차이, 통일)
   - --as-text-light → 제거 (--as-text-sub과 역할 중복)
   - --as-bg → var(--bg-gray)              (거의 동일)
   - --as-bg-card → var(--white)           (동일값)
   - --as-border → var(--border-color)     (거의 동일)
   - --as-tab-active → var(--white)        (동일값)
   - --as-input-bg → var(--white)          (동일값)
   - --as-danger → var(--color-error)      (톤 통일)
   - --as-success → var(--color-success)   (톤 통일)
   - --as-warning → var(--color-warning)   (톤 통일)
   유지할 고유 변수:
   - --as-primary-hover, --as-danger-hover (호버 색상, 토큰 없음)
   - --as-border-light / --as-tab-bg (내부 중복 정리 후 1개만 유지)
   - --as-input-border / --as-toggle-off (동일값, 1개로 통합)
   - --as-restart-* 3개 (고유 알림 패턴)
   다크 변수 블록에서 토큰으로 대체된 변수의 오버라이드 제거.

[6-2] admin-settings.css 하드코딩 색상 교체
   - 헤더 border #001f3f → var(--primary-navy)
   - H1 color #001f3f → var(--primary-navy), 다크 #5ba3f5 → var(--active-color)
   - 토스트 색상 → var(--color-success), var(--color-error), var(--color-warning)
   - 스피너 #0066cc → var(--active-color)
   - 포커스 링 → var(--focus-ring) 토큰
   - 역할 배지 색상은 시맨틱 고유값이므로 유지
   - 모달 내부 하드코딩은 유지 (Phase 4 스코프 버그 우회, Phase 7에서 JS 수정과 함께 해결)
   불필요 다크 오버라이드 제거.

[6-3] analytics.css 변수 통합
   - --ad-text → var(--text-dark)
   - --ad-text-secondary → var(--text-light)
   - --ad-bg-card → var(--white)
   - --ad-border → var(--border-color)
   - --ad-hover → var(--hover-bg) 또는 var(--light-gray)
   - --ad-primary-light → 고유 유지 (tokens에 없는 accent 배경)
   - --ad-bar-color, --ad-bar-chat → 고유 유지 (차트 색상)
   모달 변수 재선언도 스코프 이슈이므로 유지, Phase 7에서 해결.
   다크 변수 블록에서 토큰 대체된 항목 제거.

[6-4] 브라우저 검증 & /review-ui 점검
   - 관리자 설정: 각 탭(일반/AI/업로드/사용자) × 라이트/다크
   - 접속 통계: 메인 + 모달 × 라이트/다크
   - /review-ui css/admin-settings.css css/analytics.css

완료 후:
- 변경 파일별 줄 수 변화
- 제거/통합된 --as-*, --ad-* 변수 수
- 남은 고유 변수 목록과 존재 이유
```

---

### Phase 7: JS 구조 개선 (선택)

> **목표**: 페이지 간 공유 가능한 유틸리티를 추출하고, translator.html 인라인 JS를 외부 파일로 분리한다.
> **영향 파일**: 새 파일 `js/utils.js`, `translator.html`, 기존 JS 파일들
> **위험도**: 중간 (전역 함수 참조 변경, 로드 순서 주의)

#### 현재 문제

```
- showToast(): app.js에만 정의, admin-settings.js와 translator.html에서 폴백 재구현
- scrollToElementReliably(): app.js에만 정의, Explorer 6곳에서 사용
- handleApiUnauthorized(): auth.js에 정의, 3개 파일에서 typeof 체크 후 호출
- translator.html: 2,428줄 인라인 JS (별도 <script> 블록)
- 각 페이지의 JS 로드:
  · index.html: 16개 외부 JS
  · translator.html: 4개 외부 + 인라인 2,428줄
  · launcher.html: 3개 외부 + 인라인 40줄
  · login.html: 1개 외부 + 인라인 77줄
  · admin.html: 5개 외부 + 인라인 35줄
```

#### 작업 지시

```
Phase 7을 진행해줘.

[7-1] js/utils.js 생성 (공유 유틸리티)
   app.js에서 다음 함수를 utils.js로 이동:
   - showToast(message, type) — 토스트 알림
   - scrollToElementReliably(el) — content-visibility 대응 스크롤

   app.js에서 해당 함수 제거하고, app.js 상단에 주석으로 "utils.js 필요" 명시.
   admin-settings.js의 showToast 폴백 코드 제거.

   utils.js는 다른 JS보다 먼저 로드되어야 함.

[7-2] 각 HTML에 utils.js 추가
   - index.html: config.js 다음, auth.js 전에 <script src="js/utils.js"> 추가
   - translator.html: config.js 다음에 추가
   - admin.html: config.js 다음에 추가
   - launcher.html, login.html: showToast 사용하지 않으면 불필요

[7-3] translator.html 인라인 JS → js/translator.js 분리
   - 인라인 <script> 블록의 JS를 js/translator.js로 이동
   - translator.html에 <script src="js/translator.js"> 추가
   - 인라인 <script> 블록 제거
   - 변수/함수 스코프 충돌 확인

[7-4] 동작 검증
   - 각 페이지에서 주요 기능 동작 확인:
     · index.html: 토스트, 검색, AI 채팅, 북마크, 에디터
     · translator.html: 문서 목록, 뷰어, 번역, 마킹
     · admin.html: 설정 저장, 통계
     · launcher.html: 카드 클릭, 시스템 전환
     · login.html: 로그인

완료 후:
- 파일별 줄 수 변화 테이블
- translator.html Before/After 줄 수
- JS 의존성 로드 순서 다이어그램
```

---

### Phase 8: 백엔드 경량 리팩토링 (선택)

> **목표**: translator_service.py 분할, 공유 유틸리티 추출, 로깅 표준화.
> **영향 파일**: `backend/services/translator_service.py`, `backend/services/text_translator.py`, 새 파일들
> **위험도**: 낮음 (내부 리팩토링, API 인터페이스 변경 없음)

#### 작업 지시

```
Phase 8을 진행해줘.

[8-1] translator_service.py 분할
   현재 1,087줄의 단일 파일을 기능별로 분리:
   - translator_service.py — 메인 서비스 (API 호출 진입점, 문서 CRUD)
   - translator_pmt.py — PMT 번역 실행 로직 (subprocess 관리)
   - translator_workspace.py — 파일 I/O, 경로 구성, 메타 관리

   기존 API(translator.py)의 import 경로만 변경, 함수 시그니처는 유지.

[8-2] 공유 PDF 유틸리티
   translator_service.py와 text_translator.py에서 공통 패턴 추출:
   - 사용자 작업 디렉토리 경로 구성
   - PDF 파일 존재 확인/에러 처리
   - meta.json 읽기/쓰기
   → backend/services/pdf_utils.py로 추출

[8-3] 로깅 표준화
   - backend/log_config.py 생성
   - logging.getLogger(__name__) 패턴 표준화
   - 파일 핸들러(logs/ 디렉토리) + 콘솔 핸들러 설정
   - 기존 print() 호출을 logger.info/error로 교체

[8-4] 동작 검증
   - /test-backend 스킬로 API 전체 테스트
   - 번역 기능 수동 테스트 (페이지 번역 요청 → 결과 확인)

완료 후:
- 분할된 파일 구조 트리
- 각 파일의 줄 수
- API 테스트 결과 테이블
```

---

## 4. 브랜치 전략

```
main (안정)
  └── feature/platform-review
        ├── Phase 1 커밋: "리팩토링 [플랫폼] 테마 기준 문서 및 스킬 작성"
        ├── Phase 2 커밋: "리팩토링 [플랫폼] CSS 디자인 토큰 통합"
        ├── Phase 3 커밋: "리팩토링 [플랫폼] login/launcher/헤더 정리"
        ├── Phase 4 커밋: "리팩토링 [Explorer] CSS 토큰 적용"
        ├── Phase 5 커밋: "리팩토링 [Translator] 인라인 CSS 분리 + 토큰 적용"
        ├── Phase 6 커밋: "리팩토링 [Admin] 설정/통계 CSS 정리"
        ├── Phase 7 커밋: "리팩토링 [플랫폼] JS 유틸리티 추출 + translator.js 분리"
        └── Phase 8 커밋: "리팩토링 [Backend] translator_service 분할 + 로깅"
```

각 Phase 완료 후 브라우저/Playwright로 시각 확인 → 승인 → 커밋 → 다음 Phase.
전체 완료 후 `feature/platform-review` → `main` 머지.

---

## 5. 작업 흐름

```
1. 사용자: 이 계획서에서 Phase N의 "작업 지시" 블록을 복사하여 붙여넣기
2. Claude: 해당 Phase 작업 수행
3. Claude: 완료 후 변경 요약 + 확인 포인트 안내
4. 사용자: 브라우저/Playwright로 시각 확인
5. 사용자: 피드백 → 조정 (필요시 반복)
6. 사용자: "커밋해줘" → Phase 커밋
7. 다음 Phase로 이동
```

---

## 6. 기대 효과

| 항목 | Before | After |
|------|--------|-------|
| **새 서브시스템 추가** | 매번 "스타일 맞춰줘" 반복 | theme-guide.md + 공유 클래스로 일관된 UI 즉시 구현 |
| **CSS 유지보수** | 색상 변경 시 4개 파일 수정 | `:root` 변수 1곳만 수정 |
| **translator.html** | 4,027줄 모놀리식 | HTML ~1,600줄 + translator.css + translator.js |
| **다크모드** | 페이지별 지원 수준 상이 | 전 페이지 CSS 변수 기반 자동 전환 |
| **컴포넌트 일관성** | 버튼 7종, 오버레이 5종 파편화 | 공유 클래스 5종(btn, overlay, modal, form-input, card) |
| **CSS 코드량** | ~9,300줄 (인라인 포함) | 중복 제거 ~20% 감소 예상 |
| **개발 커뮤니케이션** | "느낌 맞춰줘" | ".btn--primary 적용해줘", "/review-ui로 점검해줘" |
| **코드 점검** | 수동 요청 | /review-ui, /check-theme 스킬로 자동화 |
