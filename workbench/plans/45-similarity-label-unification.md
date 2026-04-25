# Plan-45: 유사도 분류 체계 정립 (Copyleaks 모방)

> **목적**: 개발 중 시스템에 **명확한 분류 기준·계산 공식·일관된 표현**을 정립한다.
> Copyleaks의 실측 표준을 기반으로 한 단일 축 설계로, 이후 추가 기능 개발 시 드리프트를 구조적으로 차단한다.
> **조사 근거**: Copyleaks API 스키마·샘플 리포트·scan settings 실측 (2026-04-24~25)
> **작성일**: 2026-04-25
> **운영 전 시스템**: 하위호환·기존 데이터 마이그레이션 고려 없음. 지금 정하는 것이 곧 기준.

---

## 0. 확정 사항 한눈에

### 0.1 분류 체계 — 4 카테고리 (단일 강도 축)

| 카테고리 | 색상 | 내부 유형 매핑 | 기본 필터 | 점수 포함 |
|---|---|---|---|---|
| **동일** (Identical) | 🔴 빨강 | `identical` | ON | ✅ |
| **거의 동일** (Minor Changes) | 🟧 연빨강 | `near_copy` | ON | ✅ |
| **의역** (Paraphrased) | 🟪 보라 | `paraphrase` + `translation` | ON | ✅ |
| **약한 유사** (Low Similarity) | ⚪ 회색 | `low_sim` | OFF | ❌ |

- Copyleaks 3 카테고리 + 우리 도메인 특화 1 카테고리("약한 유사" — 한↔영 번역 감지)
- 라벨은 **풀네임만**. "유사"·"참고"·"공통" 등 축약 금지.

### 0.2 계산 공식 — Copyleaks aggregatedScore 모방

```
유사율 = (동일 + 거의 동일 + 의역) / (전체 문장 - 제외 문장) × 100

  동일       = identical 문장 수
  거의 동일  = near_copy 문장 수
  의역       = paraphrase + translation 문장 수
  제외       = 자동 제외 + 수동 제외 (중복 없음)
  약한 유사  = 점수 제외 (참고 카테고리, 표시만)
```

**가중치 없음** — 3 카테고리 동등 합산. Copyleaks 실측 검증: (76 + 50 + 89) / (597 - 105) = **43.7%** ✅

### 0.3 제외 처리 — 별도 패널 (업계 표준)

| 제외 출처 | 의미 |
|---|---|
| 자동 제외 | `boilerplate` + 활성 exclusion_reason (정형구문·목차·캡션·참고문헌·규격번호·짧은매칭·인용) |
| 수동 제외 | 사용자가 ⓧ로 false positive 판정한 매칭 |

- 메인 리스트에서 **제거**, 접이식 "제외된 N건 보기" 패널에서 확인
- 수동 제외는 패널 내에서 [↺ 복원] 버튼 제공

### 0.4 UI 5블록 구성

```
┌──────────────────────────────────────┐
│ ① 점수 카드 (표지) — 43.7% + 🟡 + 7지표 카드 │
├──────────────────────────────────────┤
│ ② ⚙ 검사 설정 (접이식) — 제외 옵션 5개      │
├──────────────────────────────────────┤
│ ③ 👁 카테고리 필터 (4 체크박스)              │
│    ☑ 🔴 동일  ☑ 🟧 거의 동일               │
│    ☑ 🟪 의역  ☐ ⚪ 약한 유사               │
├──────────────────────────────────────┤
│ ④ 매칭 카드 (카테고리별 섹션)               │
├──────────────────────────────────────┤
│ ⑤ [제외된 N건 보기 ▾] (접힘)                │
│    └─ 자동 제외 / 수동 제외 [↺ 복원]        │
└──────────────────────────────────────┘
```

---

## 1. 일관성 불변 (Invariants)

이 프레임워크의 유일한 성공 조건: 아래가 **모든 경로에서 항상 성립**한다.

### 1.1 표현 불변 (E)

| # | 불변 | 검증 |
|---|---|---|
| E1 | 카테고리 라벨은 `similarity-help.json#categories.*.ko`만 사용 | grep — 라벨 리터럴 SSOT 외 0건 |
| E2 | 유형 라벨은 `similarity-help.json#labels.*.ko`만 사용 | grep — 6 유형 라벨 SSOT 외 0건 |
| E3 | 축약어 금지 — "유사"·"참고"·"공통" 단독 출현 0건 (합성어 "공통 정형구문" 내부에서만 허용) | grep |
| E4 | 동일 개체를 한 화면에서 두 이름으로 부르지 않는다 | 수동 |
| E5 | 카테고리 축과 유형 축은 한 레이아웃 블록에 섞이지 않는다 | DOM |

### 1.2 계산 불변 (C)

| # | 불변 | 검증 |
|---|---|---|
| C1 | 유사율 공식은 SSOT 단일 (`score_formula.equation`) | grep |
| C2 | 가중치 없음 — 3 카테고리 문장 수 단순 합산 | 단위 테스트 |
| C3 | 약한 유사는 점수에 포함되지 않는다 | 단위 테스트 |
| C4 | 자동 제외 + 수동 제외 중복 없음 (자동 먼저 판정) | 단위 테스트 |
| C5 | 필터 토글은 유사율에 영향 없음 | E2E |
| C6 | 검사 설정 토글은 유사율 즉시 재계산 | E2E |
| C7 | 수동 제외는 유사율 즉시 재계산 | E2E |

### 1.3 가시성 불변 (V)

| # | 불변 | 검증 |
|---|---|---|
| V1 | 카드·본문 하이라이트·미니맵 마커 가시성 규칙 동일 | 필터 토글 시 3경로 동기 |
| V2 | 가시성 2치값 — 보이거나 완전 숨김. 반투명 중간 상태 금지 | CSS opacity < 1 없음 |
| V3 | 필터 OFF 시 해당 카테고리 카드·하이라이트·마커 전부 제거 | E2E |
| V4 | 제외(자동+수동)는 메인 리스트 비노출 — 접이식 패널에서만 접근 | E2E |
| V5 | 4 필터 모두 OFF → 빈 상태 안내 | E2E |

### 1.4 상태 전이 불변 (S)

```
매칭 생성
  ├─ boilerplate? → 자동 제외 (고정)
  ├─ exclusion_reason 있음 + 설정 활성? → 자동 제외 (토글 가능)
  └─ 그 외 → 카테고리 배정 (동일/거의 동일/의역/약한 유사)
                │
                │ 사용자 ⓧ 클릭
                ▼
              수동 제외 (패널로 이동)
                │
                │ ↺ 복원 클릭
                ▼
              원래 카테고리로 복귀
```

| # | 불변 |
|---|---|
| S1 | 판정 우선순위: user_excluded > 자동 제외 > 카테고리 |
| S2 | 복원은 user_excluded만 제거, 자동 제외·유형은 원복 |
| S3 | 설정 변경으로 자동 제외가 켜져도 user_excluded 플래그 보존 |

---

## 2. 단일 판정 함수 `resolveCategory`

```js
// 모든 UI 렌더 경로가 이 함수만 거쳐 카테고리를 결정한다.
// 이 함수 외 경로로 카테고리를 얻는 코드는 존재해선 안 된다.
function resolveCategory(match, activeSettings) {
  if (match.user_excluded) return 'excluded_manual';
  if (match.type === 'boilerplate') return 'excluded_auto';
  if (isActiveExclusion(match.exclusion_reason, activeSettings)) return 'excluded_auto';

  const categoryMap = {
    identical:   'identical',
    near_copy:   'near_copy',
    paraphrase:  'paraphrased',
    translation: 'paraphrased',   // 번역 → 의역에 통합
    low_sim:     'low_similarity'
  };
  return categoryMap[match.type] || 'low_similarity';
}
```

### 점수 계산 함수

```js
function computeScore(matches, totalSentences, activeSettings) {
  let identical = 0, nearCopy = 0, paraphrased = 0, excluded = 0;

  for (const m of matches) {
    const cat = resolveCategory(m, activeSettings);
    const span = (m.target_idx_end ?? m.target_idx) - m.target_idx + 1;

    if (cat === 'excluded_auto' || cat === 'excluded_manual') excluded += span;
    else if (cat === 'identical')   identical += span;
    else if (cat === 'near_copy')   nearCopy += span;
    else if (cat === 'paraphrased') paraphrased += span;
    // low_similarity는 점수 제외 (C3)
  }

  const denominator = Math.max(totalSentences - excluded, 1);
  return Math.round((identical + nearCopy + paraphrased) / denominator * 1000) / 10;
}
```

**프론트가 항상 재계산한다**. 백엔드 `similarity_score` 반환값은 초기 placeholder로만 사용.

---

## 3. SSOT 스키마 (`similarity-help.json`)

```json
{
  "categories": {
    "identical": {
      "ko": "동일",
      "ko_long": "동일 (직접 차용)",
      "en": "Identical",
      "short": "단어까지 거의 그대로 일치",
      "color_var": "--color-error",
      "default_visible": true,
      "in_score": true,
      "members": ["identical"]
    },
    "near_copy": {
      "ko": "거의 동일",
      "en": "Minor Changes",
      "short": "단어 일부만 바꾼 구간",
      "color_var": "--color-warning",
      "default_visible": true,
      "in_score": true,
      "members": ["near_copy"]
    },
    "paraphrased": {
      "ko": "의역",
      "ko_long": "의역 (재서술·번역 포함)",
      "en": "Paraphrased",
      "short": "단어는 다른데 같은 의미 (번역 포함)",
      "color_var": "--color-info",
      "default_visible": true,
      "in_score": true,
      "members": ["paraphrase", "translation"]
    },
    "low_similarity": {
      "ko": "약한 유사",
      "en": "Low Similarity (Reference)",
      "short": "부분 의미 겹침, 차용 단정 어려움",
      "color_var": "--text-muted",
      "default_visible": false,
      "in_score": false,
      "members": ["low_sim"]
    }
  },
  "exclusions": {
    "auto": {
      "ko": "자동 제외",
      "reasons": ["boilerplate", "toc_heading", "caption", "references_section",
                  "spec_number_only", "short_match", "cited_quote"]
    },
    "manual": {
      "ko": "수동 제외"
    }
  },
  "labels": {
    "identical":   { "ko": "일치",         "category_key": "identical" },
    "near_copy":   { "ko": "거의 동일",    "category_key": "near_copy" },
    "paraphrase":  { "ko": "의역",         "category_key": "paraphrased" },
    "translation": { "ko": "번역",         "category_key": "paraphrased" },
    "low_sim":     { "ko": "약한 유사",    "category_key": "low_similarity" },
    "boilerplate": { "ko": "공통 정형구문", "category_key": "__excluded__" }
  },
  "score_formula": {
    "equation": "유사율 = (동일 + 거의 동일 + 의역) / (전체 문장 - 제외 문장) × 100",
    "variables": {
      "동일": "identical 매칭 문장 수",
      "거의 동일": "near_copy 매칭 문장 수",
      "의역": "paraphrase + translation 매칭 문장 수",
      "제외": "자동 제외 + 수동 제외 (중복 없음)"
    },
    "rationale": "Copyleaks aggregatedScore 공식. 가중치 없이 단순 합산."
  },
  "verdict_bands": [
    { "range_min": 0,  "range_max": 0,  "color": "blue",   "label": "매칭 없음" },
    { "range_min": 1,  "range_max": 24, "color": "green",  "label": "양호" },
    { "range_min": 25, "range_max": 49, "color": "yellow", "label": "검토 필요" },
    { "range_min": 50, "range_max": 74, "color": "orange", "label": "상당량 매칭" },
    { "range_min": 75, "range_max": 100,"color": "red",    "label": "위험" }
  ],
  "check_settings": {
    "exclude_boilerplate":  { "ko": "정형구문 제외",           "default": true },
    "exclude_short_match":  { "ko": "짧은 매칭 제외 (8단어 미만)", "default": true },
    "exclude_toc":          { "ko": "목차/장절 헤딩 제외",      "default": true },
    "exclude_caption":      { "ko": "표/그림 캡션 제외",         "default": true },
    "exclude_cited_quote":  { "ko": "인용·출처 표시 제외",       "default": false }
  },
  "disclaimer": "유사도 ≠ 표절 — 검토자의 판단이 최종"
}
```

---

## 4. 보고서 양식 (Copyleaks PDF 모방)

### 4.1 HTML A4 보고서 구조

```
┌────────────────────────────────────────┐
│  [로고]  K-SPEC 유사도 검사 보고서      │
│         문서: K-SPEC-001.docx          │
│         검토자: 홍길동 (품질보증부)     │
│         검토일시: 2026-04-27 14:30     │
│                                         │
│         ╔════════════╗                  │
│         ║   43.7%   ║   🟡 검토 필요    │
│         ╚════════════╝                  │
│                                         │
│   ┌────────┬─────────┬────────┐        │
│   │  동일  │거의 동일│  의역  │        │
│   │   64   │   47    │   36   │        │
│   └────────┴─────────┴────────┘        │
│   ┌────────┬─────────┬────────┐        │
│   │약한유사│  제외   │전체문장│        │
│   │   23   │   31    │  411   │        │
│   └────────┴─────────┴────────┘        │
├────────────────────────────────────────┤  ← 페이지 나눔
│ ▓▓ 동일 섹션 (64건)                     │
│   #1 MIL-STD-461G §5.2 [95%]          │
│   [본문 A 빨간 하이라이트]             │
│   [본문 B 참조 문장]                    │
│   ...                                   │
├────────────────────────────────────────┤
│ ░░ 거의 동일 섹션 (47건)  ...           │
├────────────────────────────────────────┤
│ ▒▒ 의역 섹션 (36건)  ...                │
├────────────────────────────────────────┤
│ ○○ 약한 유사 섹션 (23건, 참고용)        │
├────────────────────────────────────────┤
│ 제외 목록 (자동 28건 + 수동 3건)        │
├────────────────────────────────────────┤
│ 검사 기준 부록                          │
│ ─ 활성 카테고리: 동일·거의 동일·의역   │
│ ─ 제외 설정: 정형구문·목차·캡션·참고문헌│
│ ─ 공식: (동일+거의 동일+의역)/          │
│         (전체-제외) × 100               │
│ ─ 알고리즘: Winnowing + bge-m3          │
│ ─ 참고: Copyleaks aggregatedScore 모방  │
│ ─ 면책: 유사도 ≠ 표절. 검토자 판단 필수│
└────────────────────────────────────────┘
```

### 4.2 구현 수단 (Vanilla JS 제약 준수)

- 정적 HTML + `@media print` CSS
- 페이지 브레이크: `page-break-before: always`
- 색상 인쇄 유지: `print-color-adjust: exact`
- 트리거: `window.print()` + "PDF로 저장" 안내

### 4.3 출력 포맷 — HTML + PDF만

- **HTML**: 메인 출력 포맷. `window.print()` → "PDF로 저장"으로 PDF 획득
- **Excel·TXT 제거**: 회람·보관 모두 HTML/PDF로 충분. 단일 포맷 유지로 라벨 드리프트 표면적 최소화

---

## 5. 변경 대상 파일

| 파일 | 변경 |
|---|---|
| `data/help/similarity-help.json` | 신규 작성 (§3 구조) |
| `compare.html` UI 렌더 | `resolveCategory` 도입 · 4 카테고리 필터 · 카드 섹션화 · 제외 패널 · `computeScore` 재작성 |
| `compare.html` HTML 리포트 | 표지+섹션+부록 재구성 (`doExportHtml`) |
| `css/compare.css` | 4 카테고리 색상 · 반투명 제거 · 제외 패널 · @media print (인쇄·PDF 저장 최적화) |
| `contents/guide/verify-guide.html` | 유사도 챕터 4 카테고리 기준 재작성 |

**변경 금지 (백엔드 알고리즘 보존)**:
- `backend/services/similarity_engine.py` — 6 유형 분류·exclusion_breakdown 구조
- `backend/config.py` — 임계값

**제거 대상 (범위 축소)**:
- `backend/services/export_service.py` — Excel 내보내기 (본 Plan 범위 외, 추후 정리)
- `compare.html` TXT 내보내기 경로 — 폐기

---

## 6. Phase 분해

### Phase 1 — SSOT 작성 + 백엔드 연결 (0.3일) ✅ **완료 (2026-04-25)**
- `similarity-help.json` v1→v3 전면 교체 (§3): categories/exclusions 섹션 신설, 공식 Copyleaks 교체, v1 호환 섹션 계승
- `backend/api/help.py` `_cache` 모듈 변수 제거 → JSON 수정 시 서버 재시작 불필요
- `/api/help/similarity` 엔드포인트 변경 없음 (기존 `_load` 재사용)
- 검증: JSON 문법 PASS · Copyleaks 공식 샘플 (76+50+89)/(597-105)=43.7% 일치 · 프론트 기존 접근 경로 전부 유효
- 보고서: `workbench/reports/plan-45-feedback-2026-04-25.md`

### Phase 2 — `resolveCategory` + `computeScore` 도입 (0.7일) ✅ **완료 (2026-04-25)**
- `SIM_TYPE_TO_CATEGORY` + `resolveCategory()` 단일 판정 함수 신설 (compare.html:2374~)
- `computeScore()` 순수 계산 함수 신설 (Copyleaks aggregatedScore 공식, 가중치 없음)
- `simRecomputeFromSettings()` 재작성 (compare.html:1411~) — computeScore 재사용
- `tiers.substantive/derived` hint 폐기 → "유사율 N%" 단순 표기
- `simShowResults`에서 `simRecomputeFromSettings` 무조건 호출로 변경 (백엔드 구공식 값 화면 노출 차단)
- 단위 테스트 U1~U10: **21/21 PASS** (`tests/sim_phase2_test.js`)
- Copyleaks 샘플 검증: (76+50+89)/(597-105) = 43.7% ✓
- 보고서: `workbench/reports/plan-45-phase2-feedback-2026-04-25.md`
- **잔여 (Phase 3~5 예정)**: 4그룹 바 DOM, HTML/TXT 리포트 tiers 참조, `m.level` 폴백 코드

### Phase 3 — 사이드바 UI 재구성 (1일) ⚠️ **부분 완료 (2026-04-25) — Phase 3.5로 완성도 보정**
- 4 카테고리 필터 체크박스 (`sim-filter-bar`) — SSOT `simHelp.categories` 경유, 👁 아이콘으로 검사 설정(⚙)과 시각 분리
- 점수 카드 7지표 표지 (`sim-indicators`) — 동일/거의 동일/의역/약한 유사/제외/전체 Copyleaks 양식
- 4 카테고리 누적바 (`sim-category-bar`) — 빨강/연빨강/보라/회색
- 빈 상태 2종 (매칭 0 / 필터 모두 OFF)
- 카드에 `data-sim-cat` 속성 + `m.level` 폴백 제거
- `simApplyFilter` data-sim-filter-cat 기반 재작성 (3경로 동기, V1 불변)
- `simRenderMinimap` resolveCategory 기반 색상 맵 (S1 불변, Critical 1건 수정)
- 초기 점수 `computeScore()` 인라인 계산 (flash 방지)
- 검증: 21/21 테스트 PASS · E3 축약어 전면 제거 · code-reviewer Critical 0건 · review-ui 하드코딩 0건
- 보고서: `workbench/reports/plan-45-phase3-feedback-2026-04-25.md`
- **누락·이관 사항 (Phase 3.5 에서 처리)**:
  - 용어 불일치 — 카드 라벨 "일치"(카테고리 "동일"과 불일치), "번역"(카테고리 "의역"에 통합됐으나 카드에 노출됨) → E4 불변 위반
  - Playwright 실측 검증 누락 (스킬 Phase 4.4 미수행)
  - design-reviewer 에이전트 리뷰 부재 (레이아웃 위계·정보 밀도 전문가 검토 없음)
  - 매칭 카드 카테고리별 섹션 헤더 미구현 (계획서 원안 항목)
  - 수동 제외 toast [복원] 링크 (Phase 4 제외 패널과 병행 처리)

### Phase 3.5 — UI 완성도 보정 (0.7일) ✅ **완료 (2026-04-25)**

**완료 결과**:
- E4 불변 회복: SSOT `labels.identical.ko` "일치"→"동일", `labels.translation.ko` "번역"→"의역" (UI 4 라벨 완전 통일)
- 5단계 신호등 SSOT verdict_bands 경유 (이전 "주의" → "위험" 정확 표시)
- 카드 카테고리별 sticky 섹션 헤더 (좌측 색바 + 라벨 + 동적 카운트)
- 누적바 6→8px, 다크모드 대비비 명시 (WCAG AA)
- 온보딩 1단계 텍스트 4 카테고리 안내로 갱신
- 단위 테스트 21/21 PASS · 구문 파싱 PASS · E4 grep PASS
- Playwright 실측 (라이트/다크 5종 스크린샷): "위험" + "의역 1" 섹션 헤더 + 콘솔 에러 0
- design-reviewer Critical 3건 → 0건 (전건 수정)
- code-reviewer Critical 0건, Warning 2건 즉시 수정 (섹션 카운트 stale + 온보딩 잔존)
- 보고서: `workbench/reports/plan-45-phase3.5-feedback-2026-04-25.md`

**착수 근거 (이력)**: Phase 3이 기능 구현은 완료했으나 (a) 용어 불일치, (b) 실측 검증 누락, (c) 디자인 전문가 리뷰 부재로 완성도가 불충분. Plan-45 불변 원칙 중 E4(용어 일관성) 위반 상태.

#### Step 1 — 용어 통일 (SSOT 수정)
- `data/help/similarity-help.json` `labels.identical.ko` "일치" → **"동일"**
- `labels.translation.ko` "번역" → **"의역"** (paraphrased 카테고리와 완전 통합)
- **선택**: 카드 hover 툴팁에 "번역 (다른 언어)" 부가 정보 — 데이터 보존 vs UI 단순화 트레이드오프, 구현 중 결정
- 이 계획서 §2.2 문구 수정: "카드 번역 라벨 유지" → "카드도 4 라벨로 완전 통일"
- 검증: grep 으로 `"일치"` · `"번역"` 라벨 리터럴 잔존 0건 (tests/sim_label_consistency.sh 사전 작성)

#### Step 2 — Playwright 실측 스크린샷
- 로컬 dev 서버 구동 확인 (`http://localhost:8080/compare.html`)
- 유사도 검사 시나리오 실행 (샘플 문서 2개 업로드 → 검사)
- 라이트/다크 테마 각 스크린샷 저장
- `workbench/screenshots/plan-45-phase3.5-{YYYYMMDD-HHMM}/` 경로 고정
- 콘솔 에러·네트워크 4xx/5xx 수집

#### Step 3 — design-reviewer 에이전트 호출
- 입력: Phase 3 변경 diff + Step 2 스크린샷
- 요청 범위:
  - 시각 위계 (점수 카드 → 7지표 → 필터 → 카드 리스트 흐름)
  - 정보 밀도 (280px 폭 내 컨트롤 6~7 블록 과다 여부)
  - 공간 배분 (접이식 `<details>` vs 인라인 필터의 visual weight)
  - 터치 타겟 크기 (체크박스·ⓘ 버튼 최소 24×24 / 44×44)
  - 다크모드 대비비 (WCAG AA)
  - 카드 카테고리별 섹션 헤더 구조 제안
- 출력: Critical / Warning / Suggestion 분류

#### Step 4 — 리뷰 반영 + 카드 카테고리 섹션 헤더 구현
- design-reviewer Critical 0건까지 조치
- `simShowResults` 카드 렌더 루프에서 카테고리별 섹션 헤더 삽입
  - 구조: `<div class="sim-cat-section-header" data-cat="...">동일 (N건)</div>`
  - 필터로 카테고리 숨김 시 섹션 헤더도 함께 숨김 (simApplyFilter 확장)
- 레이아웃 정리 (지적사항 기반, 예상): 7지표 카드 콤팩트 모드, 검사 설정 hover 시 미리보기, 불필요한 여백 조정

#### Step 5 — 재검증
- 단위 테스트 21/21 유지
- 구문 파싱 PASS
- E3/E4 불변 grep 확인
- Playwright 재실측 — Before/After 스크린샷 비교
- design-reviewer 재호출 (Critical/Warning 해소 확인)

**완료 기준**:
- E4 불변 회복 (한 화면 동일 개체 단일 이름)
- design-reviewer Critical 0건
- 카드 섹션 헤더 DOM 확인
- 스크린샷 before/after 비교 저장

**보고서**: `workbench/reports/plan-45-phase3.5-feedback-{YYYY-MM-DD}.md`

### Phase 4 — 제외 패널 분리 (0.7일) ✅ **완료 (2026-04-25)**
- 메인 리스트에서 자동·수동 제외 카드 분리 → `<details class="sim-exclusion-panel">` 접이식 패널로 이전
- 패널 내부 자동·수동 섹션 헤더 + 콤팩트 카드 (`sim-match-item-compact`)
- 수동 제외 카드 [↺ 복원] 버튼 (패널 내) + 토스트 [복원] (5초, 중첩 시 최근 1건)
- `simApplyUserExclusion` 전체 재렌더로 전환 (메인↔패널 DOM 이동 보장)
- `simActiveIdx` 무효화 방지 (next visible로 자동 이동)
- `sim-user-excluded` 반투명·줄무늬 CSS **폐기** (V2 불변 회복)
- 본문 하이라이트 `line-through` 보강 (수동 제외 시각 단서)
- **(Phase 3.5 후속) UI/UX 일관성**: 카드 badge 색상 카테고리 기반 통일 (`sim-cat-badge-*`), 메인/콤팩트 카드 차별화, label visual weight 정리
- 검증: 21/21 테스트 PASS · 구문 PASS · Playwright 실측 메인↔패널 이동·복원·점수 재계산 정상
- 보고서: `workbench/reports/plan-45-phase4-feedback-2026-04-25.md`
- **잔여 (Phase 7)**: toast click race 재현 점검, simApplyFilter 카운트 갱신 분리, simUpdateMatchCard dead code 정리

### Phase 5 — HTML 리포트 재구성 (0.8일) ✅ **완료 (2026-04-25)**
- 유사도 모드 export 모달: Excel·TXT 버튼 **제거** → PDF·HTML 2종만 노출 (PDF 권장)
- 다른 모드 (compare/verify) export: **4종 유지** (회귀 방지)
- `buildSimilarityReportHtml` ③ 매칭 분류 분포 — 6세부+그룹 표 → **4 카테고리 + 제외 행** SSOT 경유, "점수 영향" 컬럼 신설
- 점수 카드 `tiers.substantive/derived` 메타라인 **폐기** (Plan-45 v3)
- 별첨 A 매칭 상세 — 카테고리별 H3 그룹핑 (사이드바와 일관, 좌측 색바)
- Phase 3.5 TODO 청산 완료 (typeMeta SSOT 경유)
- PDF 변환은 백엔드 WeasyPrint(`/api/compare/html-to-pdf`) 유지 — `window.print()` 대신 더 정밀한 결과
- @page A4 + page-break + print-color-adjust 이미 구현 (Plan-38 §9 자산 계승)
- 검증: 21/21 테스트 PASS · 구문 PASS · grep 청산 확인 · Playwright 모달 PDF/HTML 2종 확인
- 보고서: `workbench/reports/plan-45-phase5-feedback-2026-04-25.md`
- **잔여 (Phase 6/7)**: Modal B fallback formula 갱신, TXT export dead code 정리, 별첨 A 페이지 분할 보강

### Phase 6 — 가이드·모달·온보딩 갱신 (0.4일)
- `verify-guide.html` 유사도 챕터 재작성 (4 카테고리 라벨 기준)
- 모달 A (2축 다이어그램) 캡션 업데이트 — "동일/거의 동일/의역/약한 유사" 동기
- **모달 B (점수 산식) — v3 공식으로 갱신** ← 필수
- 모달 C (검사 설정) 텍스트 검토
- 온보딩 3-step 텍스트 교체 (1단계는 Phase 3.5에서 이미 갱신, 나머지 점검)
- **(추가 — Phase 3.5 후속) 도움말 아이콘 통일**:
  - ⓘ/? 아이콘 4종 정책 통일: 점수 ⓘ(Modal B) / 누적바 ⓘ(Modal A) / 검사 설정 ⓘ(Modal C) / 판정 ?(툴팁)
  - 결정: 모달 트리거는 ⓘ, hover 툴팁은 ? — 또는 단일 ⓘ로 통합 후 hover/click 동작 규약화
  - 검사 설정 ⓘ 와 결과 필터 ⓘ 부재의 일관성 검토 (필터에도 ⓘ 추가 또는 검사 설정 ⓘ 제거)

### Phase 7 — 드리프트 방지 + 회귀 (0.4일)
- `tests/sim_label_consistency.sh` 작성 (§8.1)
- `CLAUDE.md`에 분류 체계 규칙 추가
- 골드셋 14 페어 재실행 (분류 매핑 PASS, 점수는 새 공식 기준 기록)
- 수동 체크 M1~M5
- `design-reviewer` → `code-reviewer` 순차 실행

**총 4.3일** (단일 PR) — Excel·TXT 경로 제거로 공수 축소

---

## 7. 테스트 매트릭스

### 7.1 단위 테스트 (수동 콘솔)

| ID | 케이스 | 기대 |
|---|---|---|
| U1 | resolveCategory: type=identical | 'identical' |
| U2 | resolveCategory: type=near_copy | 'near_copy' |
| U3 | resolveCategory: type=paraphrase | 'paraphrased' |
| U4 | resolveCategory: type=translation | 'paraphrased' (통합) |
| U5 | resolveCategory: type=low_sim | 'low_similarity' |
| U6 | resolveCategory: type=boilerplate | 'excluded_auto' |
| U7 | exclusion_reason='toc_heading' + exclude_toc=true | 'excluded_auto' |
| U8 | exclusion_reason='toc_heading' + exclude_toc=false | 원래 카테고리 |
| U9 | user_excluded=true (type=identical) | 'excluded_manual' (우선) |
| U10 | computeScore: 가중치 없이 3 카테고리 합산 | Copyleaks 공식 |

### 7.2 E2E 시나리오

| ID | 시나리오 | 기대 |
|---|---|---|
| 1 | 검사 실행 (기본 필터) | 동일·거의 동일·의역 표시, 약한 유사 숨김, 점수는 모든 반영 |
| 2 | 약한 유사 필터 ON | 카드 노출, 점수 변동 없음 |
| 3 | 동일 필터 OFF | 동일 카드 숨김, 점수 그대로 |
| 4 | 카드 ⓧ | 즉시 제거 + toast [복원] + 점수 재계산 |
| 5 | toast [복원] | 복귀 + 점수 원복 |
| 6 | "제외된 N건" 펼침 | 자동·수동 섹션 분리 |
| 7 | 제외 패널에서 [↺ 복원] | 복귀 |
| 8 | 설정 "정형구문 제외" OFF | 해당 매칭 카테고리 복귀 + 점수 상승 |
| 9 | 4 필터 모두 OFF | 빈 상태 안내 |
| 10 | 골드셋 14 페어 | 분류 매핑 일치 (점수는 새 공식 기준) |

### 7.3 일관성 점검 (수동)

| ID | 체크 |
|---|---|
| M1 | 한 매칭의 카테고리·색·라벨이 사이드바 카드·본문 하이라이트·미니맵·HTML 리포트·Excel에서 모두 동일 |
| M2 | 필터 OFF → 해당 카테고리 3경로 전부 사라짐 |
| M3 | HTML 리포트 표지 7지표 합 = 사이드바 카운트와 일치 |
| M4 | @media print에서 필터·설정 UI 숨김, 색상 유지, PDF로 저장 시 레이아웃 깨짐 없음 |
| M5 | 보고서 부록의 공식 텍스트가 SSOT와 동일 |

---

## 8. 드리프트 방지

### 8.1 자동 검증 (`tests/sim_label_consistency.sh`)

```bash
#!/bin/bash
set -e

# E1: 카테고리 라벨 SSOT 외 하드코딩 금지
for label in "동일" "거의 동일" "의역" "약한 유사"; do
  cnt=$(grep -rn "$label" --include="*.html" --include="*.py" \
      compare.html js/ backend/ contents/ \
      | grep -v "similarity-help.json\|verify-guide.html" \
      | grep -v "categories\.\|simHelp\.categories" \
      | wc -l)
  [ "$cnt" -gt 0 ] && { echo "FAIL E1: '$label' hardcoded"; exit 1; }
done

# E3: 축약어 금지 (합성어 내부는 허용)
for abbr in '"유사"' '"참고"' '"공통"'; do
  cnt=$(grep -rn "$abbr" --include="*.html" --include="*.py" compare.html js/ backend/ | wc -l)
  [ "$cnt" -gt 0 ] && { echo "FAIL E3: 축약어 $abbr"; exit 1; }
done

echo "OK"
```

pre-commit hook 또는 CI에 연결. 드리프트가 코드에 들어가기 전 차단.

### 8.2 문서 규칙 (`CLAUDE.md` 추가)

```markdown
## 유사도 분류 체계 (Plan-45)

- **카테고리 (4)**: 동일 / 거의 동일 / 의역 / 약한 유사 (Copyleaks 모방)
- **유형 (내부 6종, 카드 라벨은 카테고리와 동일 4개로 축소)**: `identical` / `near_copy` / `paraphrase` / `translation` / `low_sim` / `boilerplate` (알고리즘 키). 사용자 UI 라벨은 **동일 / 거의 동일 / 의역 / 약한 유사 / 공통 정형구문** 5개 (translation 은 "의역"으로 통합 표시 — Phase 3.5 Step 1)
- **공식**: (동일 + 거의 동일 + 의역) / (전체 문장 - 제외) × 100 (가중치 없음)
- **규칙**:
  1. 라벨은 `data/help/similarity-help.json` 경유만 허용 (하드코딩 금지)
  2. 축약 금지 — "유사"·"참고"·"공통" 단독 사용 불가, 풀네임만
  3. 카테고리 판정은 `resolveCategory(match, activeSettings)` 단독 사용
  4. 필터 = 가시성, 설정 = 점수 재계산, 수동 제외 = 가시성 제거 + 점수 재계산
  5. 제외는 메인 리스트 비노출, 접이식 패널에서만
```

### 8.3 구조적 차단

- `SIM_TYPE_MAP`에서 `group` 필드 삭제 → 카테고리를 외부 경로로 얻을 수 없음
- 사이드바 CSS grid: 검사 설정 블록과 카테고리 필터 블록을 다른 cell에 배치 (마크업 섞기 어려움)
- `resolveCategory`가 유일 판정 함수 — 주석에 "이 함수 외 경로 금지" 명시

---

## 9. 유지·폐기 정리

### 유지 (Plan-38 자산)

- 백엔드 6 유형 분류 로직·exclusion_breakdown 구조
- 5단계 신호등 (Blue/Green/Yellow/Orange/Red)
- 검사 설정 5옵션 (정형구문/짧은매칭/목차/캡션/인용)
- 자동 제외 3종 (references_section/spec_number_only/boilerplate_pattern — 항상 제외)
- 골드셋 14 페어 채점 로직
- 2축 다이어그램 (어휘 × 의미)
- 모달 A·B·C 구조

### 폐기

- "표절 의심 / 참고 가능 / 제외 영역 / 일반" 4그룹 — **4 카테고리로 대체**
- `paraphrase·translation × 0.5` 가중치 — **제거**
- 필터 칩 6 유형 중 5 하드코딩 — **4 카테고리 필터**
- `SIM_TYPE_MAP.group` 필드 — **삭제**, `resolveCategory`로 대체
- `sim-user-excluded` 반투명·줄무늬 CSS — **제거**, 제외 패널로 이동
- DETECTION_LAYER 카드 노출 — **기본 숨김**, hover 툴팁만 ✅ **완료 (2026-04-25, Phase 3.5 후속)** — `sim-match-method` span 카드 렌더 제거, `sim-match-level` title 속성에 "탐지: ..." 추가
- `tiers.substantive/derived` hint 문구 — **폐기**, 단순 "유사율 N%"
- 카드 라벨의 "일치"·"번역" — **폐기** (Phase 3.5): 카테고리 라벨과 완전 통일 ("동일"·"의역"으로 표시)

---

## 10. 최종 확정 요약

이 계획서는 다음을 **확정**한다:

1. **분류**: 4 카테고리 (동일 / 거의 동일 / 의역 / 약한 유사) — Copyleaks 모방
2. **공식**: `(동일 + 거의 동일 + 의역) / (전체 문장 - 제외) × 100`, 가중치 없음
3. **단위**: 문장
4. **라벨**: SSOT(`similarity-help.json`) 경유 강제, 축약 금지
5. **제외**: 메인 리스트 제외 + 접이식 패널에서 확인
6. **가시성**: 2치값 (표시/숨김), 반투명 금지
7. **UI**: 사이드바 5블록, 카테고리별 섹션 카드
8. **보고서**: HTML 단일 포맷 + `window.print()`로 PDF 저장. 표지(7지표) + 카테고리별 섹션 + 부록
9. **드리프트 방지**: grep 자동 테스트 + CLAUDE.md 규칙 + 단일 판정 함수
10. **공수**: 단일 PR **5.0일** (Phase 1~3 완료 + Phase 3.5 신설 0.7일 + Phase 4~7 2.3일)

---

## 11. 진행 상태 (2026-04-25 기준)

| Phase | 공수 | 상태 | 커밋 |
|---|---|---|---|
| 1 SSOT v3 | 0.3일 | ✅ 완료 | `8c88264` |
| 2 resolveCategory + computeScore | 0.7일 | ✅ 완료 | `6689565` |
| 3 사이드바 UI 재구성 | 1.0일 | ⚠️ 부분 완료 | (미커밋) |
| **3.5 UI 완성도 보정 (신설)** | **0.7일** | **⏳ 다음 단계** | — |
| 4 제외 패널 분리 | 0.7일 | 대기 | — |
| 5 HTML 리포트 재구성 | 0.8일 | 대기 | — |
| 6 가이드·모달·온보딩 | 0.4일 | 대기 | — |
| 7 드리프트 방지 + 회귀 | 0.4일 | 대기 | — |

Phase 3.5 착수로 용어 통일·레이아웃 실측 검증·design-reviewer 리뷰 3가지를 묶어서 해소.
