# Plan-54 — 자동 제외 매칭 본문 시각 신호 검증

> 작성일: 2026-04-30
> 변경 범위: `css/compare.css` (CSS 신규) + `compare.html` (simApplyHighlights / simRecomputeFromSettings / simApplyFilter 보강)
> 검증: 자동 회귀 24건 PASS + Playwright 사용자 흐름 검증

---

## 1. 배경

### 발견 경위
사용자 입장 테스트 (`plan-53-user-feedback.md`) 에서 식별:
> "표 헤더가 자동 제외됐다는 게 본문 패널에서는 안 보임. 자동 제외 패널을 펼쳐야 비로소 인지."

### 결함 메커니즘
- `simApplyHighlights` 가 매칭 type 만 보고 sim-hl-${type} 클래스 부여 — 자동 제외 카테고리 무시
- `simApplyFilter` 가 자동 제외 매칭의 본문 hl 을 inline `display:none` 으로 **숨김 처리** ← 결정적 결함
- 사이드바 카드는 `sim-match-excluded` 로 흐림 처리되지만 본문 패널은 누락

### 업계 표준 (Copyleaks / Turnitin / iThenticate)
모든 주요 도구가 자동 제외 영역을 **본문 안에서 시각적으로 구분 표시** (회색 + 흐림 + 점선). "이 매칭은 점수 미반영" 한눈에 인지.

---

## 2. 변경 항목

### 2-1. CSS 추가 (`css/compare.css`)
```css
/* paragraph 매칭 + 자동 제외 (브라우저 thead row collapse 회피로 셀렉터 좁힘) */
.sim-md-view p.sim-hl.sim-hl-excluded,
.sim-md-view div.sim-hl.sim-hl-excluded {
    opacity: 0.55;
    border-left-style: dashed !important;
}
/* 표 행 매칭 + 자동 제외 — 셀 단위 background/color 변경 (tr 에 opacity/border 적용 시
   border-collapse 모드에서 layout 깨짐 발생) */
.sim-md-view table.sim-md-table tr.sim-hl.sim-hl-excluded > th,
.sim-md-view table.sim-md-table tr.sim-hl.sim-hl-excluded > td {
    background: var(--bg-gray);
    color: var(--text-muted);
}
.sim-md-view p.sim-hl.sim-hl-excluded:hover,
.sim-md-view div.sim-hl.sim-hl-excluded:hover { opacity: 0.7; }

/* 표 셀 폰트 본문과 동일 (12 → 13px) */
.sim-md-view table.sim-md-table { font-size: var(--font-body); }
```

### 2-2. simApplyHighlights 보강 (compare.html:2769~)
초기 마킹 시 `excluded_auto` 카테고리이면 `sim-hl-excluded` 추가:
```js
var settings = simLoadCheckSettings();
var isExcluded = resolveCategory(m, settings) === 'excluded_auto';
...
els[ei].classList.add('sim-hl', 'sim-hl-' + type);
if (isExcluded) els[ei].classList.add('sim-hl-excluded');
```

### 2-3. simRecomputeFromSettings 본문 마킹 토글 (compare.html:1488~)
사이드바 카드 토글 직후 본문 hl 도 동일 갱신 (사용자 토글 시 즉시 반영).

### 2-4. simApplyFilter 자동 제외 본문 표시 (compare.html:3281~)
**결정적 수정** — 기존 `hlShow = isExcluded ? false : show` (자동 제외 본문 숨김) → `hlShow = isExcluded ? true : show` (자동 제외 본문 표시).
- 이전 의도: "메인 카드 없으니 본문 hl 도 숨김"
- 신규 의도: "본문에 표시 + sim-hl-excluded 시각 구분" (업계 표준)

---

## 3. 검증 결과

### 3-1. 자동 회귀 — 백엔드 무수정으로 24/24 PASS
| 검사 | 결과 |
|------|------|
| `sim_block_order_test.py` | ✅ 5/5 |
| `sim_table_structural_test.py` | ✅ 6/6 |
| `sim_score_v3_unit_test.py` | ✅ 5/5 |
| `sim_merge_adjacent_unit_test.py` | ✅ 8/8 |
| `sim_label_consistency.sh` | ✅ PASS |

### 3-2. Playwright 사용자 흐름 검증

#### 시나리오 1: 토글 ON (default) — 자동 제외 시각 구분
- 표 헤더 행 클래스: `sim-sent sim-hl sim-hl-identical sim-hl-excluded`
- 셀 background: `rgb(245, 247, 250)` (회색)
- 셀 color: `rgb(148, 163, 184)` (text-muted, 흐림)
- 본문 단락 (의역 매칭): 분홍 배경 그대로
- 점수: 66.7%

#### 시나리오 2: 토글 OFF 시 시각 + 점수 변동
- 표 헤더 클래스: `sim-sent sim-hl sim-hl-identical` (sim-hl-excluded 제거)
- 점수: 66.7% → **71.4%** (헤더 매칭이 분자에 포함)
- 사이드바 카드와 본문 마킹 양쪽 모두 동기화

#### 시나리오 3: 표 셀 폰트
- 표 셀 텍스트 13px (본문과 동일)
- 가이드 모달 (.sim-help-bands) 영향 0

### 3-3. 발견 + 해결한 부수 이슈

#### A. CSS opacity 가 thead row 를 collapse 시키는 브라우저 버그
- 초기 구현: `.sim-hl.sim-hl-excluded { opacity: 0.55 }` 가 `<tr>` 에도 적용 → thead height: 0
- 해결: paragraph 한정 셀렉터 (`.sim-md-view p.sim-hl.sim-hl-excluded`) 로 좁힘
- 표 행은 셀 단위 background/color 변경

#### B. simApplyFilter 가 자동 제외 본문을 숨겼던 기존 결함
- Plan-52 본체 적용 시점부터 잠재되어 있던 결함 — Plan-53 사용자 테스트에선 시점 차이로 잠시 보였음
- Plan-54 의 의도와 정면 충돌 — 자동 제외 본문 표시로 변경

### 3-4. 시각 캡처
- `plan54-final-with-excluded-marking.png` — 표 헤더 회색 처리 + 본문 단락 일반 매칭 그대로

---

## 4. 영향 분석

### 격리
- **백엔드 무수정** — 단위 테스트 24건 무영향
- **기존 sim-hl-${type} 클래스 무수정** — 기존 색상 토큰 그대로
- **추가 클래스만 적용** — fallback 안전 (CSS 누락해도 layout 안 깨짐)
- **표 셀 폰트** — `.sim-md-table` 한정 셀렉터, 다른 표 무영향

### 점수 영향
- 토글 ON (default): 백엔드 점수와 프론트 재계산 일치 (변동 0)
- 토글 OFF: 헤더 매칭이 분자 포함 — 점수 상승 (의도된 동작)

### 사용자 인지 변화 (긍정)
- 이전: "표 헤더 매칭 1건 — 어디 있지?" (자동 제외 패널 펼쳐야 인지)
- 이후: 본문에서 회색 처리된 표 헤더 = "이게 자동 제외됐구나" 즉시 인지

### 잔여 위험 0
- 모든 변경이 시각 + 본문 표시 로직 한정
- 매칭 알고리즘 / 점수 분모 / API 응답 무영향

---

## 5. UX/UI 전문가 관점

### 시각 위계 회복
- 본문 단락 의역 매칭: 분홍 배경 + 좌측 색 띠 (Plan-52 이전 그대로)
- 본문 단락 자동 제외: 분홍 배경 + 좌측 점선 + opacity 0.55 (신규, paragraph 케이스)
- 표 헤더 자동 제외: 회색 셀 + text-muted 색 (신규, 표 케이스)
- 표 데이터 행 (미매칭): 일반 표 (변동 없음)

### 업계 표준 부합
| 도구 | 우리 적용 |
|------|----------|
| Copyleaks (회색 + 점선) | ✅ paragraph 점선 + table 회색 |
| Turnitin (흐림 + 다른 색) | ✅ opacity 0.55 + text-muted |
| iThenticate (Excluded 라벨) | ✅ filter (visual indicator) |

### 일관성
- 사이드바 카드 (`sim-match-excluded`) 와 본문 마킹 (`sim-hl-excluded`) 동기화
- 토글 변경 시 양쪽 즉시 갱신

---

## 6. 사용자 관점 피드백

### Before
- "표 헤더가 자동 제외됐는지 본문에선 모른다"
- 자동 제외 패널을 펼쳐야 비로소 인지

### After
- 표 헤더가 회색 처리 + text-muted 로 시각 구분
- 사용자가 본문 보면서 "이건 점수 안 들어간다" 즉시 인지
- 토글 OFF 시 회색 → 분홍 (일반 매칭 색) 전환 — 인터랙션 명확

### 통일된 가이드 시리즈
- 5번째 자동 제외 카테고리 (table_structural, Plan-52 hotfix1) 와 동일한 시각 패턴
- caption / toc / cited_quote 등도 자동 활성화 시 동일하게 회색/점선 처리

---

## 7. 한 줄 결론

**PASS.** Plan-54 완료 — 자동 제외 매칭 본문 시각 신호 (paragraph 점선 + table 회색) + 표 셀 폰트 정합. 업계 표준 (Copyleaks/Turnitin) 부합. 단위 테스트 24/24 PASS, 백엔드 무수정. 부수 발견 2건 (CSS opacity thead collapse + simApplyFilter 자동 제외 숨김) 함께 해소. 사용자 인지 명확성 회복.
