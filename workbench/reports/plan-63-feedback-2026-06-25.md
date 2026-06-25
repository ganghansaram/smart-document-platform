# Plan-63 실행 피드백 — Notebook 문서 카드를 Author 카드 언어로 정합 (`.content-card` 추출)

> 실행일 2026-06-25 · 실행자 Claude (/plan-execute) · 대상 `workbench/plans/done/63-notebook-doc-card-alignment.md`

## 요약
- 완료 Step: 4 / 4 (+ 문서 갱신)
- 변경 파일: 6개 (`css/components.css`, `css/author.css`, `js/author.js`, `css/translator.css`, `js/translator.js`, `CLAUDE.md`)
- Critical 이슈: **0건** · Warning: 3건(1 수정·2 기재) · Suggestion: 4건(기재)

## 구현 결과
| Step | 상태 | 변경 파일 | 메모 |
|------|------|----------|------|
| 1 `.content-card` 정의 | ✅ | components.css | `.entry-card` 자매(경량): content-bg·radius-md·호버 `translateY(-2px)`+shadow-sm. 평상시 평평 |
| 2 Author `.au-card` 전환 | ✅ | author.css, author.js | 스킨 제거(레이아웃만), 빌더 2곳(일반 L96·점선 `.new` L104)에 클래스 추가 |
| 3 Notebook `.doc-card` 채택 | ✅ | translator.css, translator.js | 스킨 제거(→content-bg 다크정합), 빌더 L353 클래스, **리스트모드 들림 억제**, 다크 오버라이드 제거 |
| 4 검증·문서 | ✅ | CLAUDE.md | 컴포넌트 표에 `.content-card` 등재 |

## 검증 결과

### 코드 품질 (code-reviewer) — Critical 0 / Warning 3 / Suggestion 4
- **W1 리스트모드 `:focus-visible` 들림 미억제** (실제 키보드 a11y 버그) → **즉시 수정 완료**: 억제 규칙에 `:focus-visible` 추가(translator.css).
- W2 리스트모드 transition shadowing → 이론적(리스트 hover는 transform 없음). 미적용.
- W3 `.au-card.new:hover` border-color 암묵 상속 → pre-refactor와 동일 동작(회귀 0). 향후 robustness용 명시는 선택. 미적용.
- S1 `.doc-grid.drag-over` 하드코딩 rgba(기존) · S2 빈상태에 "새 문서" 진입점 부재(기존 UX) · S3 `box-shadow:none` 명시(클arity) · S4 transition 주석 보강 → 전부 기존/이론. **후속**.

### 사용성·디자인 (design-reviewer) — Critical 0 (완료 기준 충족)
- 현대화(평평→호버 들림) ✅ · 다크 솔리드 패널(content-bg #22223a, 기존 반투명 개선) **AA 통과**(제목 13.7:1·메타 7:1) ✅ · 위계 유지 ✅ · 카드↔리스트 일관(리스트 평평) ✅ · radius-md 자연 ✅ · entry(중량)/content(경량) 무게 구분 ✅ · 버튼 톤 조화 ✅
- primary 버튼 다크 대비 3.0:1 경계선 → **전역 토큰 사안, Plan-63 결함 아님**. 후속.

### 사용성 테스트 (Playwright)
- Notebook 카드: `doc-card content-card` · 라이트 흰색 · **다크 솔리드 `#22223a`** · radius 10px(md 통일) · 버튼(열기/삭제) 유지 · 카드 3개 ✓
- 리스트 모드: 행 평평(들림 억제 `transform:none;box-shadow:none`, `:hover`+`:focus-visible` 모두) ✓
- Author `.au-card`: authored 문서 0건 → 빌더 마크업 주입검증으로 **pre-refactor와 계산스타일 동일** 확인 — 일반(흰배경·1px solid·radius10·평평·column) + 점선(transparent·1px **dashed**·row) ✓
- 콘솔 에러: **0** · 스크린샷: `workbench/screenshots/p63-notebook-{light,dark,listmode}.png`

### 회귀 스팟체크 ("건드리지 않는 곳")
- 리스트 뷰 구현(`.au-list/.au-row` ↔ `.doc-grid.doc-list-mode`)은 통일 범위 밖 — 미변경 ✓
- `.card-btn`(열기/삭제)·`.doc-card-title`(제목편집)·`.doc-card-status` 무변경(액션 보존) ✓
- `.content-card` 사용처 = components.css(정의)+author/translator(빌더)뿐 → 타 시스템 무영향 ✓

## 사용자 관점 피드백
- **긍정**: Notebook 문서 카드가 구형 평평 → Author와 같은 "경량 떠오르는 카드"로 현대화. 다크에서 솔리드 패널로 가독성·정합 ↑. 학습비용 0(버튼/구조 그대로).
- **우려**: 없음(Author 회귀 0·인터랙션 보존).

## 웹디자인 전문가 관점 피드백
- **시각 위계**: 카드 무게가 2단(entry=중량/평상시 elevation, content=경량/호버 들림)으로 체계화 — 진입 허브 카드와 문서 카드가 의미적으로 구분됨.
- **다크모드**: 반투명 rgba → content-bg 솔리드 전환으로 카드가 실제 패널처럼 보임(Plan-62 Verify와 동일 개선).
- **접근성**: 리스트 행 들림 억제를 `:focus-visible`까지 확장(키보드 정합). primary 버튼 다크 대비는 전역 과제.

## 잔여·후속 제안 (전부 Plan-63 범위 밖)
- [ ] Notebook/Author 빈 상태에 editor용 "새 문서 작성" 진입점(현재 docs 0건 시 누락) — UX
- [ ] `.doc-grid.drag-over` 하드코딩 rgba → `--active-color-subtle` 토큰화
- [ ] 전역 primary 버튼 다크 대비 AA 상향(플랫폼 전역)
- [ ] 리스트 뷰 구현 통일(`.au-list/.au-row` ↔ doc-list-mode) — 별 계획

## 커밋 제안 (사용자 요청 시)
```
스타일 [Platform] 공통 경량 카드 스킨(.content-card) 추출 — Notebook 문서 카드 정합 (Plan-63)

Author .au-card·Notebook .doc-card 가 중복으로 갖던 문서 카드 스킨(배경·테두리·
둥글기·호버 들림)을 components.css .content-card 로 추출. .entry-card(중량)의
경량 자매(평상시 평평+호버 -2px). 두 시스템은 스킨 상속 + 레이아웃/액션 자체 유지.

- components.css: .content-card + :hover/:focus-visible 신규
- author.css/js: .au-card 스킨 제거(시각 무변), 빌더 2곳 클래스 추가
- translator.css/js: .doc-card 스킨 제거(--white→content-bg 다크정합), 빌더 클래스,
  리스트모드 호버/포커스 들림 억제, 다크 오버라이드 제거(토큰 위임)
- CLAUDE.md: 컴포넌트 표에 .content-card 등재
- 검증: 라이트/다크·리스트모드·콘솔0, Author 회귀0(계산스타일 동일), code/design-review Critical 0

계획 완료 처리: 헤더 ✅ + done/ 이동 + README 갱신 + 피드백 보고서.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
```
