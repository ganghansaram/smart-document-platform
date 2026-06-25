# Plan-62 실행 피드백 — 공통 진입 카드(`.entry-card`) 추출 + Verify 허브 현대화

> 실행일 2026-06-25 · 실행자 Claude (/plan-execute) · 대상 `workbench/plans/62-shared-entry-card.md`

## 요약
- 완료 Step: 4 / 4 (+ 문서 갱신)
- 변경 파일: 6개 (`css/components.css`, `compare.html`, `css/compare.css`, `author.html`, `css/author.css`, `CLAUDE.md`)
- Critical 이슈: **0건** · Warning: 3건(전부 해소/후속) · Suggestion: 3건(후속)

## 구현 결과
| Step | 상태 | 변경 파일 | 메모 |
|------|------|----------|------|
| 1 `.entry-card` 정의 | ✅ | components.css | 파일 끝에 공통 스킨(배경·테두리·둥글기·panel-shadow·호버 들림) + `:hover,:focus-visible` |
| 2 Verify 채택 | ✅ | compare.html (145·157·169), compare.css | 허브 카드 3개 `entry-card verify-hub-card`, `.verify-hub-card`에서 background/border/radius/transition/`:hover` 제거(상속), 태그 `--white`→`--bg-gray`, 다크 카드 배경·호버 오버라이드 제거 |
| 3 Author 베이스 전환 | ✅ | author.html (59·72), author.css | 타일 2개 `entry-card au-tile`, `.au-tile`에서 스킨 제거(상속), 레이아웃만 잔존. 시각 무변 |
| 4 검증·문서 | ✅ | CLAUDE.md | 공통 컴포넌트 표에 `.entry-card` 등재. `:active` 로드순서 주석 추가 |

## 검증 결과

### 코드 품질 (code-reviewer) — Critical 0 / Warning 3 / Suggestion 3
- **W1 button border 리셋** → **해소**. `.btn`도 `border:none`만 쓰고 appearance 미사용이 코드 컨벤션. `.entry-card`가 `border:1px solid` 명시 override → UA button 테두리 덮음(.btn과 동일 패턴). 별도 조치 불요.
- **W2 transition 범위 축소** → 현재 기능 손실 없음(두 컴포넌트에 color/opacity 트랜지션 없었음). entry-card 주석에 "스킨만" 명시로 추후 혼란 방지.
- **W3 `:active` vs `:hover` transform 로드순서 의존** → **주석 추가 완료**(compare.css).
- **S1 `:focus-visible`가 focus-ring을 shadow-md로 덮음** → 기존 `.au-tile` 동작과 동일(시각 무변 유지 위해 미변경). **a11y 후속**.
- **S2 허브 `<a>`에 href 없음 → 키보드 포커스 불가** → 기존 구조(Plan-62 도입 아님). **a11y 후속**.

### 사용성·디자인 (design-reviewer) — Critical 0 (완료 기준 충족)
- elevation 통일 ✅ · 모드 3색 아이콘 보존 ✅ · 시각 위계 자연 ✅ · Author 회귀 0 ✅
- 라이트 보조텍스트(태그·desc) 대비 AA 3.0~3.3:1 미달 → 전역 `--text-light` 토큰 한계, **Plan-62 결함 아님**. 별건 후속.
- **가운데 카드 파란 테두리 = 선택 상태 아님**. CSS 규칙 분석(브루트포스) + 새 탭 휴지 캡처로 확정: 3장 모두 휴지 시 `border-color:--border-color`(회색) 동일. 파랑은 `.entry-card:hover` 표현이며, 헤드리스 Chromium의 고착 `:hover` 아티팩트로 가운데에 머물렀던 것.

### 사용성 테스트 (Playwright)
- 컴퓨티드 검증: Verify/Author 카드 = `entry-card *`, bg `#fff`(다크 `#22223a`), 1px border, panel-shadow, 태그 `--bg-gray` ✓
- 휴지 상태(새 탭): 허브 3장 `hover:false` + 회색 테두리 균일 ✓
- 스크린샷: `workbench/screenshots/p62-verify-{light,dark,rest}.png`, `p62-author-{light,dark}.png`
- 콘솔 에러: **0** (compare.html · author.html)
- 하드코딩 색: **0** (잔존 rgba 2건은 기존 다크 태그 틴트)

### 회귀 스팟체크 ("건드리지 않는 곳")
- `.entry-card` 사용처 grep = components.css(정의) + compare.html(3) + author.html(2)뿐 → Notebook/Explorer 등 **타 시스템 무영향** ✓
- `.au-card.new` 대시 타일(범위 밖) 무변경 ✓

## 사용자 관점 피드백
- **긍정**: Verify 허브가 평평한 회색 → 떠 있는 카드로 즉시 현대화. Author와 한 언어. 모드 색코딩·레이아웃은 그대로라 학습비용 0.
- **우려**: 없음(시각 무변·회귀 0).

## 웹디자인 전문가 관점 피드백
- **시각 위계**: 평상시 elevation 부여로 "선택 가능한 카드"임이 명확해짐.
- **다크모드**: 토큰 자동 전환으로 카드가 반투명 → 솔리드 패널로 개선(Author와 정합).
- **접근성(후속)**: 허브 `<a>` href/tabindex 부재 + entry-card focus-ring을 shadow-md가 덮는 점은 키보드 사용자 대상 개선 여지. 라이트 보조텍스트 대비도 전역 토큰 차원 과제.

## 잔여·후속 제안 (전부 Plan-62 범위 밖)
- [ ] a11y: 허브 카드 `<a>`에 `tabindex="0"`/`href="#"` + entry-card `:focus-visible`에 focus-ring 합성
- [ ] 전역 `--text-light` 라이트 대비 AA 상향(플랫폼 전역 영향 → 별도 계획)

## 커밋 제안 (사용자 요청 시)
```
스타일 [Platform] 공통 진입 카드(.entry-card) 추출 — Verify 허브 현대화 (Plan-62)

Author .au-tile·Verify .verify-hub-card 가 중복으로 갖던 진입 카드 스킨
(배경·테두리·둥글기·평상시 elevation·호버 들림)을 components.css 공통
.entry-card 로 추출. 두 시스템은 스킨 상속 + 레이아웃만 자체 유지.

- components.css: .entry-card + :hover/:focus-visible 신규
- compare.html/css: 허브 카드 3개 entry-card 채택, .verify-hub-card 스킨 중복 제거,
  태그 배경 흰→회색(대비), 다크 카드 오버라이드 제거(토큰 자동전환 위임)
- author.html/css: 타일 2개 entry-card 채택, .au-tile 스킨 제거(시각 무변)
- CLAUDE.md: 공통 컴포넌트 표에 .entry-card 등재
- 검증: 라이트/다크 elevation 통일·모드 3색 아이콘 보존·Author 회귀 0·콘솔 0

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
```
