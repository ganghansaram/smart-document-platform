# Plan 21: 디자인 시스템 리파인먼트

> 작성일: 2026-03-30
> 상태: 설계 완료 / 착수 대기
> 선행: Plan-20 Phase 2 마인드맵 완료

---

## 1. 배경

### 1.1 현황 평가

tokens.css 기반 디자인 시스템이 구축되어 있으나, 실제 적용률이 불균일하다.
신규 코드(AI 패널, 마인드맵 등)는 토큰 참조가 잘 되어 있지만,
초기 코드(카드, 뷰어, 팝오버 등)에 하드코딩이 다수 잔존하여
테마 변경 시 일관성이 깨지고, 유지보수 비용이 증가한다.

### 1.2 목표

1. **토큰 커버리지 100%** — 모든 색상·그림자·radius·spacing이 변수 참조
2. **모던 비주얼 업그레이드** — 2025년 트렌드 반영 (깊이감, 부드러운 곡선, 미세 그림자)
3. **기능 영향 0건** — 레이아웃·인터랙션 변경 없이 시각적 품질만 개선

---

## 2. 현황 분석 — 문제 영역

### 2.1 토큰 정의 공백

tokens.css에 정의되지 않았으나 반복 사용되는 값:

| 필요 토큰 | 현재 하드코딩 값 | 사용처 |
|----------|---------------|-------|
| `--color-highlight` | `#ffe066` / 다크 `#665500` | 검색 하이라이트 (4곳) |
| `--popover-bg` | `#1e1e2e`, `#2a2a3e` | 팝오버/컨텍스트메뉴 다크 (8곳) |
| `--line-height-body` | 1.5 / 1.6 / 1.7 혼용 | 전체 |
| `--line-height-relaxed` | 1.7 | AI 요약, 드로어 등 |

### 2.2 하드코딩 색상 현황

| 파일 | 하드코딩 건수 | 주요 영역 |
|------|:-----------:|----------|
| `translator.css` | ~40건 | 다크모드 팝오버, range-dialog, 트리패널 |
| `components.css` | ~15건 | 버튼 `#fff`, 스피너 rgba |
| `modal.css` | ~5건 | box-shadow, 배경 |
| `platform-header.css` | ~5건 | box-shadow, 드롭다운 |

### 2.3 컴포넌트 토큰 미참조

| 컴포넌트 | 문제 | 영향 |
|----------|------|------|
| `.btn` 시리즈 | `border-radius: 6px` 하드코딩 | `--radius-sm` 변경해도 버튼에 미반영 |
| `.form-input` | `border-radius: 6px` 하드코딩 | 동일 |
| `.modal-box` | `box-shadow` 하드코딩, `border-radius: 12px` 하드코딩 | `--shadow-lg`, `--radius-lg` 미참조 |
| `.platform-header` | `box-shadow` 하드코딩 | `--shadow-sm` 미참조 |
| font-size 전체 | `13px`, `14px` 등 직접 사용 | `--font-body` 변경해도 미반영 |

### 2.4 시각 품질 개선 여지

| 항목 | 현재 | 개선 방향 |
|------|------|----------|
| 배경 레이어 | 2단계 (white + bg-gray) | 3~4단계 (subtle depth) |
| 그림자 | 약하거나 미사용 | 카드·모달에 미세 그림자 적용 |
| 곡선 (radius) | 4px/8px — 약간 각진 느낌 | 6px/10px/14px — 부드러운 곡선 |
| 호버 피드백 | 배경색만 변경 | 배경 + 그림자 + 미세 translate 조합 |
| 타이포 위계 | 600/400 두 단계 | 700/600/500/400 네 단계 |
| 행간 | 미정의, 곳마다 다름 | 토큰으로 통일 (1.5/1.65/1.8) |

---

## 3. 단계별 실행 계획

### Phase 1: 토큰 확장 + 공백 해소 (~0.5일)

> tokens.css에 누락 변수 추가. 기존 하드코딩 참조는 아직 수정하지 않음.

- ✅ `--color-highlight` / `--color-highlight-text` 추가 (라이트: #ffe066/#2c3e50, 다크: #665500/#ffe066)
- ✅ `--popover-bg` / `--popover-bg-hover` 추가 (라이트: #ffffff/#f5f7fa, 다크: #1e1e2e/#2a2a3e)
- ✅ `--line-height-body: 1.5`, `--line-height-relaxed: 1.65` 추가
- ✅ `--font-weight-bold: 700`, `--font-weight-semibold: 600`, `--font-weight-medium: 500` 추가
- ⬜ 기존 `--radius-sm`/`--radius-md`/`--radius-lg` 값 검토 → Phase 5로 이관 (값 변경 시 기존 참조에 즉시 영향)

### Phase 2: components.css 토큰 준수 (~0.5일)

> 핵심 공통 컴포넌트의 하드코딩을 토큰 참조로 교체.

- ✅ `.btn` — `font-size` → `var(--font-body)`, `font-weight` → `var(--font-weight-medium)`, `transition` → `var(--transition-fast)`
- ✅ `.btn-icon-sm` — `border-radius: 4px` → `var(--radius-sm)`
- ✅ `.btn-lg` — `font-size` → `var(--font-title)`
- ✅ `.form-input`, `.form-select` — `font-size` → `var(--font-body)`, `transition` → `var(--transition-fast)`
- ✅ `.form-group label` — `font-size` → `var(--font-body)`, `font-weight` → `var(--font-weight-medium)`
- ✅ `.form-input-sm`, `.form-select-sm` — `border-radius` → `var(--radius-sm)`
- ✅ `.badge` — `font-size` → `var(--font-caption)`, `font-weight` → `var(--font-weight-semibold)`, `border-radius` → `var(--radius-sm)`
- ✅ `.tooltip-popup` — `line-height` → `var(--line-height-body)`
- ✅ `.form-range-value` — `font-weight` → `var(--font-weight-semibold)`
- ✅ `.mode-toggle-btn` — `font-size`, `font-weight`, `transition` 토큰화
- ⏭️ `.btn` 시리즈 `border-radius: 6px` — Phase 5로 이관 (--radius-sm=4px ≠ 6px, 시각 변화 방지)
- ⏭️ `.spinner` rgba — 값이 다름 (rgba(0,102,204,0.15) ≠ --active-color-subtle), 의도적 차이 유지

> **⚠️ Phase 2 주의사항**
> - `font-weight` 교체 범위: components.css 내부만 교체. 다른 CSS 파일은 Phase 3~4에서 처리
> - `line-height` 교체 시 주의: 현재 1.4~1.8까지 **의도적으로 다른 값**이 혼용됨
>   - `1.4` = 밀도 높은 UI (배지, 메뉴 항목) → 교체하지 않음
>   - `1.5` = 일반 본문 → `var(--line-height-body)`
>   - `1.6~1.7` = 긴 텍스트 → `var(--line-height-relaxed)` 또는 유지
>   - `1.8` = 읽기 전용 콘텐츠 → 유지 (토큰 범위 밖)
>   - **일괄 교체 금지** — 항목별로 의도를 확인 후 개별 판단

### Phase 3: modal.css + platform-header.css 토큰 준수 (~0.5일)

- ⬜ `.modal-box` — `box-shadow` → `var(--shadow-lg)`, `border-radius` → `var(--radius-lg)`
- ⬜ `.platform-header` — `box-shadow` → `var(--shadow-sm)`
- ⬜ `.ph-system-dropdown` — 검토 및 토큰 교체

### Phase 4: translator.css 하드코딩 정리 (~1일)

> 가장 큰 영역. 다크모드 하드코딩 색상을 토큰 참조로 교체.

- ⬜ range-dialog — `#2d2d2d`, `#444`, `#333` → `--content-bg`, `--border-color`, `--bg-secondary`
- ⬜ 팝오버/컨텍스트메뉴 — `#1e1e2e`, `#2a2a3e`, `#353550` → `--popover-bg` 시리즈
- ⬜ 트리패널 다크 배경 — `--panel-bg` 통일
- ⬜ 검색 하이라이트 — `#ffe066` → `var(--color-highlight)`
- ⬜ title-edit 관련 — GitHub 팔레트 → 토큰 참조

> **⚠️ Phase 4 주의사항**
> - `--popover-bg`와 `--white`는 라이트/다크 모두 동일 값. 팝오버·컨텍스트메뉴·드롭다운 등
>   **떠 있는 레이어 전용**으로 `--popover-bg`를 사용하고, 일반 배경은 `--white`/`--bg-primary` 유지
>   → Phase 5에서 팝오버 배경만 별도 조정할 수 있는 여지 확보
> - `--color-highlight` 교체는 안전 — 5개 파일 17곳 모두 동일 패턴 (`#ffe066`/`#665500`)
- ⬜ Markmap `#e2e8f0` → `var(--text-primary)`
- ⬜ 독자 버튼 (`.card-btn`, `.translate-page-btn` 등) → `.btn` 시리즈 위임 또는 토큰 참조

### Phase 5: 비주얼 업그레이드 — 토큰 값 조정 (~0.5일)

> Phase 1~4가 완료되어 모든 코드가 토큰을 참조하는 상태에서,
> tokens.css 값만 변경하여 전체 시각 품질을 일괄 업그레이드.

- ⬜ **배경 팔레트 세분화**
  - 라이트: `--white` 유지, `--bg-gray: #f8f9fb` (약간 따뜻하게), `--canvas-bg: #f0f2f5` 조정
  - 다크: `--bg-primary: #1a1a2e`, `--content-bg: #24243c` (깊이 차이 강화)
- ⬜ **경계선 연하게** — `--border-color: #e8ecf0` (라이트), 주장 줄임
- ⬜ **곡선 부드럽게** — `--radius-sm: 6px`, `--radius-md: 10px`, `--radius-lg: 14px`
- ⬜ **그림자 강화** — `--shadow-sm/md/lg` 값 미세 조정 (현재보다 약간 더 visible)
- ⬜ **호버 피드백 강화** — `--hover-bg` 톤 조정, `--transition-fast: 0.15s`로 변경 검토
- ⬜ **line-height 토큰 적용** — body 1.5, relaxed 1.65 통일

### Phase 6: 크로스 검증 (~0.5일)

- ⬜ 전 페이지 라이트/다크 스크린샷 비교 (launcher, index, translator, compare)
- ⬜ 컴포넌트별 시각 일관성 확인 (버튼, 입력, 모달, 카드, 배지)
- ⬜ 다크모드 가독성 확인 (대비율 4.5:1 이상)
- ⬜ 콘솔 에러 0건 확인
- ⬜ 기능 회귀 없음 확인

---

## 4. 예상 공수

| Phase | 내용 | 예상 |
|:-----:|------|:----:|
| 1 | 토큰 확장 | ~0.5일 |
| 2 | components.css 토큰 준수 | ~0.5일 |
| 3 | modal + header 토큰 준수 | ~0.5일 |
| 4 | translator.css 하드코딩 정리 | ~1일 |
| 5 | 비주얼 업그레이드 (토큰 값 조정) | ~0.5일 |
| 6 | 크로스 검증 | ~0.5일 |
| **합계** | | **~3.5일** |

---

## 5. 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| 토큰 교체 시 시각 변화 | 일부 요소가 예상과 다르게 보일 수 있음 | Phase별 스크린샷 비교, 단계적 진행 |
| components.css 수정 → 전 페이지 영향 | Explorer, Compare 등에도 영향 | 각 페이지별 검증 필수 |
| 다크모드 팝오버 색상 통일 시 미세 차이 | 기존에 의도적 차이였을 수 있음 | 변경 전 현재 값 스크린샷 보존 |

---

## 6. 원칙

1. **토큰 퍼스트** — 모든 시각 속성은 tokens.css 변수를 통해야 한다
2. **기능 불변** — 레이아웃, 인터랙션, 컴포넌트 구조는 변경하지 않는다
3. **단계적 진행** — Phase 1~4(토큰 준수)를 먼저 완료한 후 Phase 5(값 조정)
4. **비교 검증** — 모든 Phase 완료 시 before/after 스크린샷 비교

---

## 7. 참고

### 벤치마크 디자인 시스템

- **Shadcn/ui** — 중립 팔레트, 미세 그림자, 부드러운 곡선
- **Linear** — 다크모드 깊이감, 3~4단계 배경 레이어
- **Notion** — 깔끔한 타이포 위계, 최소한의 장식
- **Radix Themes** — 체계적 토큰 구조, 접근성 기준 준수

### 현재 토큰 구조도

```
tokens.css
├── 색상 (primary, secondary, gray, semantic, accent)
├── 레이아웃 (panel-radius, panel-gap, canvas-bg, panel-bg)
├── 그림자 (shadow-sm ~ shadow-xl, panel-shadow, focus-ring)
├── 둥글기 (radius-sm ~ radius-xl, radius-pill)
├── 간격 (space-xs ~ space-2xl)
├── 폰트 (font-title, font-body, font-caption)
├── 트랜지션 (transition-fast ~ transition-slow)
└── diff 색상 (diff-added, diff-deleted 등)
```
