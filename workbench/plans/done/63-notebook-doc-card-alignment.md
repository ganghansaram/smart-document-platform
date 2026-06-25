# Plan-63 — Notebook 문서 카드를 Author 카드 언어로 정합 (공통 경량 카드 스킨 추출)

> **상태: ✅ 완료 (2026-06-25, /plan-execute) — `.content-card`(entry-card 경량 자매) 추출, Notebook 문서 카드 현대화·다크 솔리드 정합, Author 회귀 0. 피드백 `reports/plan-63-feedback-2026-06-25.md`**
> 작성: 2026-06-25 · 트리거: 진입 홈 정합 작업(Plan-61/62, 히어로·헤더·`.entry-card`) 후, Notebook 배너 **아래** 문서 카드가 Author 카드보다 구형(평평·다크 비정합)으로 관찰됨.
> 근거: Plan-62(`.entry-card` 추출)의 *문서 카드판*. "복붙 아닌 추출"로 드리프트 방지.

## 🧭 현황 한눈에

> **핵심 = Notebook `.doc-card` 를 Author `.au-card` 의 "경량 문서 카드" 언어로 통일.** 단, `.entry-card`(진입/허브용 *중량* 카드, 평상시 elevation)와는 **다른 무게**다. 문서 그리드는 카드가 많아 평상시 그림자를 다 주면 시끄럽다 → `.au-card` 처럼 **평상시 평평 + 호버 때만 들림**이 맞다. 그래서 entry-card 가 아니라 **경량 문서 카드 스킨을 새로 추출**한다.

| 결정 | 값 |
|------|------|
| 방식 | 공통 경량 카드 스킨 **추출**(components.css) — 복붙 금지 |
| 기준 스펙 | 현재 Author `.au-card` (content-bg·radius-md·호버 `translateY(-2px)`+`shadow-sm`) |
| Notebook 채택 범위 | **스킨만** (배경·테두리·둥글기·호버 들림·트랜지션·다크정합) |
| Notebook 유지 | **버튼 액션**(열기/삭제·`.card-btn`) · **제목 인라인 편집** · **상태 배지**(`.doc-card-status`) — 번역 문서 특성상 필수 |
| Author | `.au-card` 를 공통 스킨 확장으로 리팩터(**시각 무변**, 중복 제거) |
| 범위 밖 | 리스트 뷰 구현 통일(`.au-list/.au-row` ↔ `.doc-grid.doc-list-mode`) · 업로드존 · 레이아웃 대수술 |

## 🔬 왜 (코드 근거)

| 요소 | Author `.au-card` (author.css:249) | Notebook `.doc-card` (translator.css:166) |
|---|---|---|
| 배경 | `var(--content-bg)` (다크 자동전환) | **`var(--white)`** (다크 정합 약함) |
| 둥글기 | `--radius-md` | `--radius-lg` |
| 트랜지션 | border-color/transform/box-shadow | border-color/background |
| **호버** | **`translateY(-2px)` + `box-shadow:shadow-sm`** (들림) | **border-color 만** (평평) |
| 선택 방식 | 카드 전체 클릭(액션 1개) | 버튼(열기/삭제) + 제목편집 + 상태 |

- **Notebook 카드는 호버해도 안 떠오름 / Author는 들림** → Author가 더 현대적으로 보이는 실제 원인. Plan-62 의 Verify 허브 사례와 동형.
- Notebook `.doc-card` 의 `--white` 하드 배경은 다크모드에서 `--content-bg`(#22223a) 대비 부정합 소지 → 정합 겸 정정.

---

## 1. 범위 (IN / OUT)

| ✅ 이번 | ⏭️ 후속/별건 |
|---|---|
| `components.css` 공통 **경량 카드 스킨**(가칭 `.content-card`) 정의 | 리스트 뷰 구현 통일(별 구조) |
| Notebook `.doc-card` → 스킨 채택(테마 현대화) | 업로드존(`.upload-zone`) 리프레시 |
| Author `.au-card` → 스킨 기반 리팩터(시각 무변) | 빈 상태(`.au-empty`↔`.doc-empty`) 통일 |
| Notebook `.doc-card` 배경 `--white`→스킨 `--content-bg`(다크 정합) | Explorer(별 패턴, Plan 합의로 유지) |

## 2. 설계 — 공통 경량 카드 스킨

**`.content-card` (components.css, 공통 스킨 — 이름은 §3 결정)**
- `background: var(--content-bg)` · `border: 1px solid var(--border-color)` · `border-radius: var(--radius-md)`
- `transition: border-color/transform/box-shadow var(--transition-normal)`
- 평상시 **그림자 없음**(문서 그리드 다량 카드 → 평평 유지)
- `:hover, :focus-visible` → `border-color: var(--active-color)` · `transform: translateY(-2px)` · `box-shadow: var(--shadow-sm)` · `outline:none`
- 다크: 토큰 자동(별도 색 없음)
- ⚠️ `.entry-card`(중량, 평상시 panel-shadow, radius-lg, `-3px`)와 **구분**. 둘은 자매(중량/경량) 스킨.

**시스템별 확장(각 CSS 유지)**
- Author `.au-card`: `.content-card` + `.au-card-top`/`-name`/`-meta`·`.au-card.new` 점선 타일
- Notebook `.doc-card`: `.content-card` + padding(20px) · `.doc-card-title`(제목+편집) · `.doc-card-meta` · `.doc-card-status` · `.doc-card-actions`(`.card-btn`)
  - 현재 `background:var(--white)`·`border-radius:var(--radius-lg)`·`:hover{border-color만}` 제거(→ 스킨 상속). padding/구조/버튼은 잔존.

## 3. 결정 사항
1. **추출 > 복붙** — Plan-62 와 동일 원칙. 단일 출처(components.css).
2. **entry-card 재사용 금지** — 문서 카드는 *경량*(평상시 평평). entry-card 의 평상시 elevation 을 문서 그리드에 주면 과함 → 별도 자매 스킨.
3. **공통 클래스 이름** — 가칭 `.content-card`. 대안: `.doc-tile`·`.list-card`. (entry-card 와 대구되는 중립명 권장) — **승인 시 확정.**
4. **합성 = HTML/JS 클래스 추가 (필수)** — Notebook 카드는 JS 생성(`js/translator.js:353` `card.className='doc-card'`) → `'doc-card content-card'` 로 변경. Author 카드 빌더에도 동일 추가.
5. **중복 규칙 제거 = 필수** — ⚠️ page CSS(translator/author)가 components.css 보다 **나중 로드** + 동일 specificity → 잔존 `.doc-card` 배경/둥글기/호버가 스킨을 이김. 미제거 시 스킨 무효(Plan-62 와 동일 함정).
6. **Notebook 선택 방식 유지** — 카드 전체 클릭(Author)로 바꾸지 않음. 열기/삭제/제목편집 다중 액션은 번역 문서 필수 → **테마만 채택, 인터랙션 보존.**
7. **Author 시각 무변** — `.au-card` 픽셀 동일(회귀 0). Notebook 은 의도된 변경(들림·다크정합·radius).

## 4. 파일별 변경
- `css/components.css` (신규 블록): `.content-card` + 호버/포커스. 컴포넌트 표(문서)에 1행 추가.
- `css/author.css` (`.au-card` L249~): 배경·테두리·둥글기·트랜지션·`:hover`(L261) **중복 제거**(→ 스킨 상속). 잔존 = padding·`.au-card-top/-name/-meta`·`.au-card.new`.
- `css/translator.css` (`.doc-card` L166~): 배경 `--white`·`border`·`border-radius:lg`·`transition`·`:hover`(L176) **제거**(→ 스킨 상속). 잔존 = padding 20px·제목/메타/상태/액션. (`.doc-card.drag-over`·`.doc-grid` 그리드는 무관, 유지)
- `js/translator.js` (L353): `card.className = 'doc-card'` → `'doc-card content-card'`. (Author 카드 빌더에도 동일 클래스 추가)
- (선택) `CLAUDE.md` 공통 컴포넌트 표에 `.content-card`(경량) 등재 — `.entry-card`(중량) 옆.

## 5. 리스크 · 주의
| 항목 | 완화 |
|------|------|
| Translator 는 다용도·복잡 시스템 | **문서 카드 스킨만** 손댐(번역 엔진·뷰어 무관). 회귀 점검 |
| Notebook 카드 JS 생성 | 클래스는 빌더(L353) 한 곳 → 단일 변경 |
| **page CSS가 components.css보다 나중 로드** | 중복 규칙 제거 **필수** + 빌더에 클래스 추가 (§3-4·5) |
| 다크모드 `--white`→`--content-bg` 전환으로 카드색 변동 | 의도된 정합(다크에서 솔리드 패널). 라이트는 둘 다 흰색이라 무변 |
| radius-lg→md 로 카드 모서리 살짝 작아짐 | Author 와 통일이 목적. before/after 확인 |
| Author 픽셀 변동 | 리팩터 후 `.au-card` before/after 비교(회귀 0) |
| 리스트 뷰 불통일 잔존 | 본 계획 범위 밖(명시). 카드 뷰 우선 |

## 6. 검증 (Playwright + 측정)
- Notebook 문서 카드: 라이트/다크 · 호버 들림(`translateY(-2px)`+shadow-sm) · 다크 솔리드 배경(`--content-bg`) · 버튼/제목편집/상태 **정상 동작 유지** · 콘솔 0
- Author `.au-card`: **시각 무변**(before/after 동일) 회귀 확인
- 나란히 비교: Author·Notebook 문서 카드가 같은 "경량 카드" 언어로 통일
- entry-card(중량) vs content-card(경량) 두 무게가 시각적으로 구분되는지
- 하드코딩 색 grep 0 · components.css 컴포넌트 표 갱신

## 7. 단계
1. `components.css` `.content-card` 정의(현 `.au-card` 스펙 기준)
2. Author `.au-card` 스킨 기반 전환(픽셀 무변 확인)
3. Notebook `.doc-card` 채택(스킨) + 빌더 클래스 추가 + 중복 제거 + 회귀(버튼/편집/상태)
4. 검증·문서 갱신

---

## 부록 — 근거 파일
- `css/author.css` L249~301 (`.au-card`: content-bg·radius-md·호버 translateY(-2px)+shadow-sm)
- `css/translator.css` L166~273 (`.doc-card`·`.card-btn`: white·radius-lg·호버 border만 + 버튼 액션)
- `js/translator.js` L353(카드 빌더)·318/322(리스트토글)·414/423(버튼)
- `css/components.css` (`.entry-card` 중량 스킨 — 자매 경량 스킨 정의처)
- `css/tokens.css` (`--content-bg`·`--shadow-sm`·`--radius-md`·`--active-color`)
- Plan-62 (`.entry-card` 추출 — 본 계획의 진입 카드판 선례)
