# 디자인 시스템 구축 — CSS 토큰 + 공통 컴포넌트

> 작성일: 2026-03-13
> 브랜치: `feature/design-system`
> 상태: **B-1 완료, B-2 적용 완료(커밋 대기) — B-3~B-6 남음**

---

## 목적

플랫폼 전체에서 반복되는 UI 컴포넌트를 공통 CSS로 추출하여,
**어떤 페이지에서든 클래스만 붙이면 동일한 컴포넌트가 나오는 구조**를 만든다.

### 핵심 원칙
- **시각적 변화 제로** (Step A) / **의도된 미세 개선만** (Step B)
- **단계별 검증 필수**: 각 단계마다 반영 전/후 사용자 확인
- **기존 제약 유지**: Vanilla JS, 빌드 없음, 모놀리식 HTML, 폐쇄망

---

## 현황 요약

### CSS 로드 현황 (Step A 적용 후)

| 페이지 | 공통 CSS | 공통 수 |
|--------|---------|--------|
| index.html | tokens, scrollbar, toast, **components** | 4/6 |
| translator.html | tokens, scrollbar, **components** | 3/6 |
| compare.html | tokens, scrollbar, **components**, compare | 4/6 |
| admin.html | tokens, toast, **components** | 3/6 |
| launcher.html | tokens | 1/6 |
| login.html | tokens | 1/6 |

### Step A 적용 완료 항목

| 페이지 | 요소 | 적용 방식 |
|--------|------|----------|
| compare | 스피너 ×2 | `spinner cp-upload-spinner` 병행 |
| translator | 스피너 ×1 | `spinner page-spinner` 병행 |
| admin | 스피너 ×2 | `spinner admin-spinner` 병행 |
| index | 에디터 저장 버튼 | `btn btn-primary editor-save-btn` 병행 |

> 기존 페이지 CSS 미변경 → cascade 순서(components.css → page CSS)로 시각적 변화 제로

---

## UX 감사 결과

### 핵심 발견

1. **admin `--as-*` 변수 = 글로벌 토큰 별칭**: `--as-primary` = `var(--active-color)`, `--as-text` = `var(--text-dark)` 등. 값이 동일하므로 통합 안전.

2. **3가지 버튼 크기 체계**: 플랫폼 전체에서 의도적으로 3단계 밀도를 사용 중.
   - 툴바/사이드바: 26px 아이콘, 3~5px padding (밀도 우선)
   - 모달/다이얼로그: 28~32px, 8~20px padding (접근성 우선)
   - 브랜드/FAB: 44~56px (터치 타겟)

3. **실제 비일관성** (수정 필요):
   - editor 취소 버튼: padding `8px 16px` → 표준 `8px 20px` (4px 부족)
   - translator model-select: padding `4px 8px` → 표준 `8px 10px` (같은 툴바 내 불일치)

4. **디자인 시스템 누락 컴포넌트**: `.form-input-sm`, `.btn-icon-lg`, `.spinner-lg`, `.toggle`

### 컴포넌트별 판정 결과

> (a) 공통 클래스 그대로 적용 | (b) 공통 클래스 + 페이지 override | (c) 커스텀 유지 (의도적 차이)

#### Admin

| 컴포넌트 | 판정 | 사유 |
|----------|------|------|
| `.admin-input` → `.form-input` | ✅ B-1 | 중복 CSS 제거, border-color override만 유지 |
| `.admin-select` → `.form-select` | ✅ B-1 | 중복 CSS 제거, border-color override만 유지 |
| `.admin-btn` + `.admin-btn-save` → `.btn .btn-primary` | ✅ B-1 | 중복 CSS 제거, hover override 유지 |
| `.admin-btn-reset` → `.btn .btn-secondary` | ✅ B-1 | 병행 적용, 중복 CSS 제거 |
| `.admin-btn-sm` → `.btn-sm` | **(b)** | padding 2px 차이 (10px→12px). 테이블 밀도 위해 `4px 10px` override |
| `.admin-textarea` | **(c)** | padding 8px 10px vs 12px, font 13px vs 14px — 설정 패널 밀도에 맞는 의도적 차이 |
| `.admin-spinner` | ✅ A+B-1 | Step A 병행, B-1에서 독자 CSS 제거 |
| `.admin-toggle` | **(c)** | 디자인 시스템에 미정의. 향후 `.toggle` 컴포넌트로 승격 검토 |
| `.admin-role-badge` → `.badge` | ✅ B-1 | 병행 적용, 중복 CSS 제거 |
| `.admin-restart-badge` | **(c)** | padding·font 미세 차이 + 전용 경고 색상. 유지 |

#### Compare

| 컴포넌트 | 판정 | 사유 |
|----------|------|------|
| `.scroll-sync-btn` (툴바 버튼 7종) | **(c)** | padding 3px 10px — 툴바 밀도 의도적. `.btn-sm`(4px 12px)보다 컴팩트 |
| `.cp-nav-btn` (네비게이션 4종) | **(c)** | 26×26px — 그룹 밀도 의도적. `.btn-icon`(28px)과 다른 컨텍스트 |
| `.cp-file-remove` (닫기 2종) | **(c)** | 16×16px 마이크로 버튼 — hover-reveal 패턴, 표준화 불필요 |
| `.placeholder-upload-btn` (업로드 2종) | ✅ B-2 | `btn btn-primary` 병행, 중복 CSS 제거 (svg 크기만 유지) |
| `.cp-paste-textarea` | ✅ B-2 | `form-textarea` 병행, flex:1 + resize:none override만 유지 |
| `.cp-upload-spinner` | ✅ A | Step A에서 병행 적용 |
| `.mode-toggle-btn` | **(c)** | 세그먼트 컨트롤 패턴 — 버튼이 아닌 별도 UI 패턴 |
| `.cp-sidebar-collapse` | **(c)** | 24×24px — `.btn-icon`(28px)보다 작은 사이드바 전용 |
| 배지 3종 (.cp-stat, .cp-change-badge, .vd-issue-badge) | **(c)** | 의도적 크기 계층 (요약=큰 pill, 목록=작은 태그) |
| 모달 입력 (preset, severity, term, param) | ✅ B-2 | `form-select-sm`/`form-input-sm` 병행, 4px 8px 12px로 통일 |

#### Explorer (index.html)

| 컴포넌트 | 판정 | 사유 |
|----------|------|------|
| `.editor-save-btn` | ✅ 완료 | Step A에서 병행 적용 |
| `.editor-cancel-btn` | **(a)** | padding `8px 16px` → `8px 20px`. `.btn .btn-secondary` 적용 (비일관성 수정) |
| `.editor-fullscreen-btn`, `.editor-close-btn` | **(b)** | 32×32px — `.btn-icon` 기반 + 크기 override. 향후 `.btn-icon-lg` 추가 |
| `.panel-action-btn` | **(c)** | 26×26px, border 없음 — 패널 헤더 전용 아이콘 |
| `.loading-spinner` (editor) | **(b)** | 36×36px — `.spinner` 기반 + 크기 override. 향후 `.spinner-lg` 추가 |
| AI 챗 전체 (FAB, send, quick, input) | **(c)** | 브랜드 디자인 — pill/원형/그라디언트. 표준화 대상 아님 |
| `#search-input` | **(c)** | 모달 검색 전용 oversized input — 표준 폼과 다른 용도 |

#### Translator

| 컴포넌트 | 판정 | 사유 |
|----------|------|------|
| `.page-spinner` | ✅ 완료 | Step A에서 병행 적용 |
| `.tp-btn`, `.zoom-btn` | **(c)** | 26×26px — 사이드바/툴바 밀도 의도적 |
| `.pn-btn` | **(c)** | 28×28px, radius 4px — 툴바 톤 일관성 (전체 4px radius) |
| `.translate-page-btn` 외 3종 | **(c)** | padding 5px 14px — 툴바 밀도 의도적 |
| `.card-btn` | **(c)** | padding 5px 12px — 카드 그리드 밀도 |
| `#model-select` | **(a)** | padding `4px 8px` → `8px 10px` — 같은 툴바 내 폼 불일치 수정 |
| `.font-scale-btn` | **(c)** | 3px 7px 초소형 — 글꼴 크기 조절 전용 |
| Title edit input | **(c)** | 2px 4px 인라인 편집 — 최소 패딩 의도적 |
| 다이얼로그 버튼 (range, folder picker) | **(b)** | padding 6px 18px → `.btn` 기반 + override 검토 |

#### Login / Launcher

| 컴포넌트 | 판정 | 사유 |
|----------|------|------|
| `.login-btn` | **(c)** | 13px 0 full-width — 로그인 전용 대형 버튼 |
| Login inputs | **(b)** | padding 12px 14px — `.form-input` 기반 + 크기 override. 향후 `.form-input-lg` |
| `.system-card-badge` | **(a)** | `.badge` + `.badge-info` 적용 가능 (미세 차이 1~2px) |

---

## Step B: 점진 적용 계획

### 작업 원칙
- 한 번에 한 화면, 한 카테고리씩 적용
- 적용 전 변경 내용 고지 → 사용자 확인 후 다음 진행
- **(a)** 항목: 시각 변화 없음 또는 비일관성 수정 (1~2px)
- **(b)** 항목: 의도된 미세 개선, 사전 고지 필수

### B-1: Admin ✅ (d0bc534)

> Playwright 전후 비교 검증 완료 — 시각적 변화 없음

- [x] `.admin-input` → `form-input admin-input` 병행, 중복 CSS ~15줄 제거
- [x] `.admin-select` → `form-select admin-select` 병행
- [x] `.admin-btn-save` → `btn btn-primary`, `.admin-btn-reset` → `btn btn-secondary` 병행
- [x] `.admin-spinner` + `@keyframes admin-spin` 독자 CSS 17줄 제거
- [x] `.admin-role-badge` → `badge` 병행

### B-2: Compare ✅ (커밋 대기)

> Playwright 전후 비교 검증 완료 — 메인/붙여넣기 변화 없음, 모달 입력 크기 통일 (의도적 미세 변화)

- [x] `.placeholder-upload-btn` → `btn btn-primary` 병행, 중복 CSS ~18줄 제거 + 다크모드 4줄 제거
- [x] `.cp-paste-textarea` → `form-textarea` 병행, 중복 CSS ~15줄 제거 (flex:1, resize:none override 유지)
- [x] 모달 입력 4종 → `form-select-sm`/`form-input-sm` 병행, 중복 CSS ~30줄 제거
- [x] `components.css`에 `.form-input-sm`/`.form-select-sm` 신규 추가

### B-3: Explorer/Index (위험도: 중)

| 작업 | 유형 | 예상 시각 변화 |
|------|------|--------------|
| `.editor-cancel-btn` → `btn btn-secondary editor-cancel-btn`, 중복 CSS 제거 | (a) | 좌우 padding 16px→20px (4px 넓어짐) |
| `.editor-fullscreen-btn`/`.editor-close-btn` → `btn-icon` 기반 + 32px override | (b) | border 1px 추가 가능 — 검토 필요 |
| `.loading-spinner` → `spinner` 기반 + 36px override | (b) | 없음 (크기 override 유지) |

**확인 포인트**: 에디터 모달 (열기 → 저장/취소/전체화면/닫기 버튼), 에디터 로딩 스피너

### B-4: Translator (위험도: 낮)

| 작업 | 유형 | 예상 시각 변화 |
|------|------|--------------|
| `#model-select` padding 통일 → `.form-select` 적용 | (a) | padding 4px 8px → 8px 10px (셀렉트 높이 약간 증가) |

**확인 포인트**: 번역 툴바의 모델 선택 드롭다운

### B-5: Login (위험도: 낮)

| 작업 | 유형 | 예상 시각 변화 |
|------|------|--------------|
| Login inputs → `form-input` 기반 + 크기 override (12px 14px 유지) | (b) | 없음 (override로 기존 크기 유지) |

**확인 포인트**: 로그인 화면 입력 필드

### B-6: Launcher (위험도: 최소)

| 작업 | 유형 | 예상 시각 변화 |
|------|------|--------------|
| `.system-card-badge` → `badge badge-info` 적용 | (a) | padding 3px→2px, font 10px→11px, radius 3px→4px (미세) |

**확인 포인트**: 런처 카드의 "개발중" 배지

---

## 디자인 시스템 확장 (Step B 과정에서 필요 시 추가)

| 컴포넌트 | 스펙 | 용도 | 추가 시점 |
|----------|------|------|----------|
| `.form-input-sm`/`.form-select-sm` | padding 4px 8px, font 12px, radius 4px | 모달/밀집 폼 | ✅ B-2에서 추가 |
| `.btn-icon-lg` | 32×32px | 에디터 모달 헤더 | B-3 (Explorer) |
| `.spinner-lg` | 36×36px | 에디터 로딩 오버레이 | B-3 (Explorer) |
| `.form-input-lg` | padding 12px 14px, font 14px | 로그인 폼 | B-5 (Login) |

> `.toggle` 컴포넌트(admin-toggle 기반)는 B 완료 후 별도 검토.

---

## 의도적 커스텀 유지 목록

아래는 UX 감사 결과 **표준화하지 않기로 판정**한 항목. 각 페이지의 맥락에 맞는 의도적 차이.

| 페이지 | 컴포넌트 | 사유 |
|--------|----------|------|
| Compare | `.scroll-sync-btn`, `.cp-nav-btn` | 툴바/네비 밀도 (3~5px padding, 26px 아이콘) |
| Compare | `.mode-toggle-btn` | 세그먼트 컨트롤 패턴 (버튼 아님) |
| Compare | `.cp-file-remove` | 16px 마이크로 close — hover-reveal |
| Compare | `.cp-sidebar-collapse` | 24px 사이드바 전용 |
| Compare | 배지 3종 | 의도적 크기 계층 (요약 vs 목록) |
| Admin | `.admin-btn-reset` | hover 시 빨간색 → "초기화" 의미론 |
| Admin | `.admin-textarea` | 설정 패널 밀도 (13px/1.5 vs 14px/1.6) |
| Admin | `.admin-toggle` | 토글 스위치 — 디자인 시스템 미정의 |
| Admin | `.admin-restart-badge` | 전용 경고 색상 |
| Translator | `.tp-btn`, `.zoom-btn`, `.font-scale-btn` | 툴바 초소형 버튼 (26px, 3px padding) |
| Translator | `.pn-btn` | 28px, radius 4px — 툴바 톤 일관성 |
| Translator | `.translate-page-btn` 외 액션 버튼 | 5px 14px — 툴바 밀도 |
| Translator | `.card-btn` | 카드 그리드 밀도 |
| Translator | Title edit input | 인라인 편집 최소 패딩 |
| Explorer | `.panel-action-btn` | 26px, border 없음 — 패널 헤더 전용 |
| Explorer | AI 챗 전체 | 브랜드 디자인 (pill/원형/그라디언트) |
| Explorer | `#search-input` | 모달 검색 oversized input |
| Login | `.login-btn` | full-width 대형 버튼 |

---

## 실행 완료 Step

### Step 1~4: 토큰 확장 + CSS 추출 ✅
### Step 5: 모달 기반 정의 ✅ (기존 모달 교체는 보류)
### Step 6-A: 공통 컴포넌트 클래스 정의 ✅
### Step 6-B (A): 안전 항목 병행 적용 ✅

- [x] compare 스피너 ×2 → `spinner` 병행
- [x] translator 스피너 ×1 → `spinner` 병행 + components.css `<link>`
- [x] admin 스피너 ×2 → `spinner` 병행 + components.css `<link>`
- [x] editor 저장 버튼 → `btn btn-primary` 병행

### Step 7: 인라인 CSS 추출 ✅ (compare 완료, launcher/login 유지)
### Step 8: 규칙 문서화 ✅ (부분 — 테마 기준서 미갱신)
### Step 9: 기반 검증 ✅

### B-1: Admin 통합 ✅ (d0bc534)

- [x] 버튼 6종 → `.btn .btn-primary`/`.btn-secondary` 병행, `.admin-btn` 10속성→1속성
- [x] 입력 4종 → `.form-input` 병행, 공유 CSS 제거 (border-color override만 유지)
- [x] 셀렉트 3종 → `.form-select` 병행
- [x] 배지 1종 → `.badge` 병행
- [x] 스피너 독자 CSS + `@keyframes` 17줄 제거
- Playwright 전후 비교: 시각적 변화 0건

### B-2: Compare 통합 ✅ (커밋 대기)

- [x] 업로드 버튼 3개소 → `.btn .btn-primary` 병행, CSS ~18줄 제거
- [x] 붙여넣기 textarea → `.form-textarea` 병행, CSS ~15줄 제거
- [x] 모달 입력 4종 → `.form-input-sm`/`.form-select-sm` 병행, CSS ~30줄 제거
- [x] `components.css`에 `.form-input-sm`/`.form-select-sm` 신규 컴포넌트 추가
- Playwright 전후 비교: 메인/붙여넣기 변화 0건, 모달 입력 크기 통일 (의도적)

---

## 변경 수치 요약 (현재까지)

| 지표 | 값 |
|------|---|
| 신규 파일 | 6개 CSS + 계획서 1개 |
| 수정 파일 | 18개 (HTML 5 + CSS 4 + JS 4 + CLAUDE.md) |
| 제거된 중복 코드 | ~1,740줄 |
| 추가된 공통 코드 | ~1,956줄 |
| 시각적 변화 | 0건 (의도적 모달 입력 통일 제외) |
| 커밋 | 3건 (c186620, a110311, d0bc534) + B-2 대기 |

---

## 참고

- 베이스라인 스크린샷: `workbench/screenshots/design-system/baseline-*.png`
- 테마 기준서: `memory/theme-guide.md`
- CLAUDE.md 스타일 규칙: `CLAUDE.md` > "스타일 규칙 (디자인 시스템)" 섹션
