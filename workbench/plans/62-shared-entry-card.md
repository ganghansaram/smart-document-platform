# Plan-62 — 공통 진입 카드(`.entry-card`) 추출 + Verify 허브 카드 현대화

> **상태: ⬜ 착수 대기 (계획 승인 단계)**
> 작성: 2026-06-23 · 트리거: Author 홈 진입 타일이 Verify 허브 카드보다 세련돼 보임 → "구형 시스템을 현재 디자인 기준으로 정합"
> 근거: Plan-61(Author 셸·홈) 완료 후 비교 관찰. 관련 커밋 `f46590a`.

## 🧭 현황 한눈에

> **핵심 = "복붙 아닌 추출".** Author `.au-tile` 스타일을 Verify에 베끼면 또 드리프트(히어로에서 겪은 문제) → **공통 `.entry-card` 베이스를 `components.css`에 한 번 정의**하고 Author·Verify 둘 다 확장하게 한다. 이후 자동으로 같이 간다.

| 결정 | 값 |
|------|------|
| 방식 | 공통 `.entry-card` 추출(components.css) — 복붙 금지 |
| Verify 채택 범위 | **스킨만** (평상시 흰 배경+그림자+테두리+호버 들림) |
| Verify 유지 | **모드별 3색 아이콘**(주황/파랑/초록=기능적 색코딩) · **가운데 3카드 클러스터 레이아웃** |
| Author | `.au-tile`을 `.entry-card` 확장으로 리팩터(시각 동일, 중복 제거) |
| 범위 밖 | Notebook(선택카드 없음)·레이아웃 대수술·신규 기능 |

## 🔬 왜 (코드 근거)
| 요소 | Verify `.verify-hub-card` (현재) | Author `.au-tile` |
|---|---|---|
| 평상시 배경 | `--bg-gray`(납작 회색) | `--content-bg`(흰색) |
| 평상시 그림자 | 없음(호버 때만) | **`--panel-shadow`(항상)** |
| 테두리 | 2px transparent | 1px `--border-color` |
- **Verify는 호버해야 카드처럼 떠오름 / Author는 평상시부터 떠 있음** → Author가 더 세련돼 보이는 실제 원인. Verify에 "평상시 elevation"만 줘도 확 현대화됨.

---

## 1. 범위 (IN / OUT)

| ✅ 이번 | ⏭️ 후속/별건 |
|---|---|
| `components.css`에 공통 `.entry-card`(+`--hover`/`--accent-bar` 등 변형) 정의 | Notebook 카드(별 패턴) |
| Verify `.verify-hub-card` → `.entry-card` 채택(스킨) | Verify 외 다른 컴포넌트 리프레시 |
| Author `.au-tile` → `.entry-card` 기반 리팩터(시각 무변) | 레이아웃(가운데↔왼쪽) 변경 |

## 2. 설계 — 공통 `.entry-card`

**`.entry-card` (components.css, 공통 스킨)**
- `background: var(--content-bg)` · `border: 1px solid var(--border-color)` · `border-radius: var(--radius-lg)`
- `box-shadow: var(--panel-shadow)` (평상시 elevation)
- `transition: border-color/transform/box-shadow var(--transition-normal)`
- `:hover, :focus-visible` → `border-color: var(--active-color)` · `transform: translateY(-3px)` · `box-shadow: var(--shadow-md)` · `outline:none`
- 다크모드: 토큰 자동(별도 색 지정 없음)

**시스템별 확장(각 CSS 유지)**
- Author `.au-tile`: `.entry-card` + 좌측정렬 · 단일 악센트 아이콘 · 칩 · 2-col 그리드
- Verify `.verify-hub-card`: `.entry-card` + 가운데정렬 · **모드별 3색 아이콘 유지** · 220px · 3-card 클러스터
  - 현재 `background:var(--bg-gray)` 제거(→ entry-card의 content-bg 상속), 2px transparent 테두리 제거, 호버 `background:var(--white)` 중복 제거(평상시 이미 흰색)

## 3. 결정 사항
1. **추출 > 복붙** — 히어로 드리프트 재발 방지. 단일 출처(components.css).
2. **Verify는 스킨만** — 모드 3색 아이콘은 *기능적 색코딩*이라 유지. 가운데 클러스터 레이아웃도 유지(저위험, "모드 선택 허브"엔 적합).
3. **Author 시각 무변** — `.au-tile`을 베이스로 리팩터하되 픽셀 동일(회귀 0 목표).
4. **합성 = HTML 클래스 추가 (필수, OR 아님)** — 마크업에 `class="entry-card verify-hub-card"` 직접 추가. 순수 CSS엔 `@extends`가 없어, 클래스를 안 붙이면 `.entry-card` 규칙이 **전혀 적용되지 않음**.
5. **중복 규칙 제거 = 필수 (선택 아님)** — ⚠️ page CSS(compare/author)가 `components.css`보다 **나중 로드** + 동일 specificity(0,1,0) → 잔존 `.verify-hub-card` 배경/테두리 규칙이 `.entry-card`를 **항상 이김**. 미제거 시 entry-card 평상시 흰배경·그림자가 **무효**가 됨(검증: compare.html:11→16, author.html:13→15).
6. **Verify hover 들림 4→3px = 의도된 변경** — 통일 위해 수용. (**Author만 시각 무변, Verify는 의도적 스킨 변경** — "Verify 무변"으로 오해 금지)

## 4. 파일별 변경
- `css/components.css` (신규 블록): `.entry-card` + 호버/포커스. 컴포넌트 테이블(문서)에 1행 추가.
- `compare.html`: 허브 카드 **3개(L145·157·169)** 에 `class="entry-card verify-hub-card"` 추가.
- `css/compare.css` (L666~756): `.verify-hub-card` **중복 제거(필수)** — `background:var(--bg-gray)`·`border:2px transparent`·`:hover{background/box-shadow/transform}` 삭제(→ entry-card 상속). 잔존 = 가운데정렬·220px·모드 3색 아이콘. **추가 수정: `.verify-hub-card-tag`(L749~) 배경 `var(--white)` → `var(--bg-gray)`/`var(--panel-bg)`** — 카드가 흰색이 되면 *흰 태그가 흰 카드 위에서 사라지는* 대비 문제(+ 다크 정합) 발생하므로 함께 정정.
- `author.html`: 모드 타일 **2개(L57·70)** 에 `entry-card` 클래스 추가.
- `css/author.css` (L205~): `.au-tile` 중복 제거(entry-card 상속), 좌측정렬·아이콘·칩만 잔존. (`.au-card.new` 대시 타일은 본 계획 범위 밖 — 영향 없음)
- (선택) `CLAUDE.md` 공통 컴포넌트 표에 `.entry-card` 등재.

## 5. 리스크 · 주의
| 항목 | 완화 |
|------|------|
| Verify는 안정·복잡 시스템(462KB compare.html) | **허브 카드 CSS만** 손댐(엔진·로직 무관). 회귀 점검 |
| 호버 상태 중복(Verify 기존 bg→white) | 평상시 흰색이므로 제거·정리 |
| 모드 3색 아이콘 상실 우려 | **유지 확정**(entry-card는 아이콘 색 미지정) |
| Author 픽셀 변동 | 리팩터 후 before/after 픽셀 비교(회귀 0) |
| `components.css` 로드 | 4개 페이지 모두 로드 확인됨 ✅ |
| **page CSS가 components.css보다 나중 로드** | 중복 규칙 제거 **필수**(미제거=entry-card 무효) + HTML에 `entry-card` 클래스 추가 (§3-4·5) |
| **흰 카드 위 흰 태그**(`.verify-hub-card-tag`) 대비 소실 | 태그 배경 `--bg-gray`/`--panel-bg`로 정정(다크 정합 겸) |
| Verify 엔진 누출 | 없음 — JS는 `data-hub-mode`만 읽음(compare.html:1192), 클래스 미참조. 허브 카드 3개가 유일 인스턴스 |

## 6. 검증 (Playwright + 측정)
- Verify 허브: 라이트/다크 · 평상시 elevation(흰배경+그림자) · 호버 들림 · **모드 3색 아이콘 유지** · 3카드 가운데 정렬 유지 · 콘솔 0
- Author 홈: `.au-tile` **시각 무변**(before/after 동일) 회귀 확인
- 나란히 비교: Verify·Author 카드가 같은 "떠 있는 카드" 언어로 통일
- 하드코딩 색 grep 0 · components.css 컴포넌트 표 갱신

## 7. 단계
1. `components.css` `.entry-card` 정의
2. Verify 허브 카드 채택(스킨) + 회귀
3. Author `.au-tile` 베이스 전환(픽셀 무변 확인)
4. 검증·문서 갱신

---

## 부록 — 근거 파일
- `css/compare.css` L666~735 (`.verify-hub-card` 현재 스펙: bg-gray·2px투명·호버 white)
- `css/author.css` (`.au-tile`: content-bg·panel-shadow·1px·호버 들림)
- `css/components.css` (공통 컴포넌트 정의처)
- `css/tokens.css` (`--content-bg`·`--panel-shadow`·`--shadow-md`·`--active-color`)
- Plan-61 (Author 셸·홈, `.au-tile` 출처)
