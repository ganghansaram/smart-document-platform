# Plan-48 Hotfix 실행 피드백 — 미니맵 위치 정확도 진짜 정상화

> 실행일 2026-04-25 · 실행자 Claude · 대상 계획서 `workbench/plans/48-similarity-minimap-improvement.md`

## 배경 — 실제 사용자 시나리오에서 미니맵 작동 안 함 발견

Phase 1·2 코드 리뷰·단위 테스트는 모두 통과했으나, 사용자 지적으로 **긴 PDF 2개**(46페이지 / 22페이지, 총 4397 문장 임베딩)로 실측한 결과 미니맵이 거의 무용지물:

### Hotfix 전 상태 (Playwright 실측)
- 마커 263개 중 **243개(92.4%)가 top=14px 한 점에 누적**
- 나머지 20개는 미니맵 영역(979px) 한참 밖(top=14620 등)
- 시각적으론 미니맵 최상단에 짧은 띠 1개만 보이고 본체 전부 비어 있음 (`plan-48-bug-minimap-stacked.png`)

### 두 근본 결함

#### 결함 A — 잘못된 scroll container 참조
- 미니맵 코드: `panel-body-a.scrollHeight` 사용 (= **979**, 잘못)
- 진짜 scroll container: 자식 `.sim-md-view` (자체 `overflow: auto`, scrollHeight = **41653**)
- 분모 42배 작아져 ratio 폭주

#### 결함 B — display:none element 의 offsetTop=0
- 약한 유사 default OFF · 자동 제외 등으로 본문 element `display: none`
- `display:none` element 의 `offsetTop = 0` → ratio = 0 → top=14 누적
- 마커 카드 가시성만 검사하고 실제 element 가시성 미검사

## 변경 사항 (compare.html — `simRenderMinimap` + `simAppendSpanMark`)

| 변경 | 이전 | 이후 |
|------|------|------|
| **scroll container** | `panel-body-a` | `panelA.querySelector('.sim-md-view') \|\| panelA` (sim 모드 = .sim-md-view) |
| **분모 (scrollHeight)** | `panel.scrollHeight` (979, 잘못) | `scroller.scrollHeight` (41653, 정확) |
| **element 검색 컨테이너** | `panel.querySelectorAll(...)` | `scroller.querySelectorAll(...)` |
| **가시성 검사** | 없음 | `els[i].offsetHeight > 0` 인 visible element 만 채택 |
| **fallback** | — | scroller 없으면 panel 자체 사용 (diff 모드 호환) |

코드 위치: `compare.html` L3091~3175

## Hotfix 후 검증 결과 (Playwright 동일 시나리오)

### 마커 위치 분포 — A 패널 (실측)

| 항목 | Before | After |
|------|--------|-------|
| 총 마커 | 263 | 20 (visible 매칭만) |
| distinct top 위치 | 21개 | **19개** (사실상 모두 다른 위치) |
| top=14 누적 | **243개** | **0개** |
| top 범위 | 14 ~ 14620 (대부분 14) | **67 ~ 963px** (미니맵 979px 풀 활용) |

### 5개 샘플 수학 정합성

| idx | offsetTop (실제 본문) | scrollH (분모) | ratio | mark.top (계산값) | 검증 |
|-----|----------------------|----------------|-------|-------------------|------|
| 14 | 2319 | 41653 | 0.0557 | 14 + 0.0557 × 951 = 67.0 | **= 66.95 ✅** |
| 25 | 3740 | 41653 | 0.0898 | 14 + 0.0898 × 951 = 99.4 | **= 99.39 ✅** |
| 57 | 6000 | 41653 | 0.1440 | 14 + 0.1440 × 951 = 151.0 | **= 150.99 ✅** |
| 122 | 15037 | 41653 | 0.3610 | 14 + 0.3610 × 951 = 357.4 | **= 357.32 ✅** |
| 159 | 19482 | 41653 | 0.4676 | 14 + 0.4676 × 951 = 458.7 | **= 458.80 ✅** |

→ **본문 위치와 미니맵 마커가 1:1 정확 매칭**.

### 추가 인터랙션 검증
- ✅ 마커 클릭 → `simNavigateToMatch(14)` 발화 → 본문 좌·우 양쪽 패널 동시 점프 + 사이드바 카드 active
- ✅ active 마커: A·B 양쪽 마커에 `.active` 클래스 동기 (`activeMarks: 2`)
- ✅ 호버 200ms → 툴팁 정상 표시 ("● 의역 · 83.1% / Recent advancements in large language models (LLMs), such as / #15 / 418")
- ✅ ESC 키 → 툴팁 닫힘
- ✅ 다크 모드: 마커·툴팁 모두 가시성 정상 (`plan-48-hotfix-dark.png`)

### 자동 (회귀 0)
- 단위 테스트 21/21 PASS
- `tests/sim_label_consistency.sh` PASS
- `vm.Script` 구문 errors 0

### 다른 모드 영향성
- `panelA.querySelector('.sim-md-view') || panelA` fallback — diff 모드에는 `.sim-md-view` 가 없으므로 panel 자체 사용 → 기존 동작 보존 (회귀 0)
- `.cp-minimap-mark` (diff 마커) 코드 변경 0

## 사용자 관점 피드백

### 긍정 (실측 후)
- **미니맵이 진짜 분포 인지 도구로 작동 시작** — 이전엔 첫 픽셀 줄에만 모인 보라색 띠 1개였는데, 이제 우측 미니맵 위~아래 전체에 매칭이 자연스럽게 분포 표시
- **본문 하이라이트 위치와 정확히 매칭** — 사용자 의심 ("색상 위치가 안 맞는다") 100% 해소. 수학적으로도 5개 샘플 모두 서브픽셀 단위 정확도
- **클릭 점프** 정상 작동 — 매칭 14번 클릭 시 본문 양쪽 패널이 즉시 해당 sentence 로 스크롤
- **호버 툴팁** 정상 작동 — 마커 위에 마우스 올리면 카테고리·점수·스니펫 미리보기

### 우려
- visible 매칭만 표시되므로, 사용자가 "약한 유사" filter ON 토글하면 268개가 추가로 나타남 — 직관적 동작이라 우려 아님

## 웹디자인 전문가 관점 피드백

### 분포 인지 가치 회복
- 미니맵의 본질 = "문서 내 매칭 분포 한눈 인지". hotfix 전엔 정보 0 (다 위쪽에 쌓임), hotfix 후엔 의역 23개가 문서 길이에 따라 자연스럽게 분포 — F-pattern 스캔 가능
- 마커 색·길이로 카테고리·매칭 길이 모두 표현 가능

### 시각 디자인 변경 0
- CSS 변경 없음. 다크모드 회귀 없음. 토큰 사용 그대로
- 단순히 데이터 입력 정정 (잘못된 scroll container → 진짜 scroll container)

### 접근성
- 사이드바 카드가 1차 정보원, 미니맵은 보조 시각 채널 — 정보 등가성 유지
- 마커 작은 hover 영역 (12×3px ~ 12×N px)은 여전히 좁음 → 향후 폭 확장 검토 가능 (Phase 4)

## Plan-48 Phase 1·2 가 못 잡은 이유 (사후 분석)

- Phase 1 multi-sentence 보정 로직 자체는 수학적으로 정상이었음
- 그러나 **입력 데이터** (panel.scrollHeight, el.offsetTop) 가 잘못된 scroll container 참조로 부정확
- code-reviewer 정적 분석에 panel.scrollHeight 가 어떤 값인지 실측 안 됨 (단위 테스트 환경에서는 .sim-md-view 가 없음)
- 단위 테스트 + Playwright 짧은 문서 시나리오에서는 결함이 표면화 안 됨
- 긴 문서 (4397 문장) + filter OFF 268매칭 + 자동 제외 260매칭 조건이 결함을 드러냄

→ **교훈**: 미니맵류 positioning 코드는 반드시 실제 콘텐츠로 longitudinal 검증 필요. 이미 `memory/feedback_*` 후보로 기록 가치 있음.

## 추가 hotfix2 — 색상 본문/미니맵 일치 (사용자 지적)

사용자 후속 지적 — "미니맵 색상이 일치되는 것 같아?"

### 발견 (Playwright 색상 실측)
| 카테고리 | 본문 hl border | 미니맵 마커 (이전) | 일치? |
|---------|----------------|-------------------|------|
| 동일 | rgb(248,113,113) `--sim-identical-border` | rgb(248,113,113) `--color-error` | ✅ 우연 |
| 거의 동일 | rgb(251,191,36) `--sim-near-copy-border` | rgb(251,191,36) `--color-warning` | ✅ 우연 |
| **의역** | **rgb(167,139,250) 보라 `--sim-paraphrase-border`** | **rgb(96,165,250) 파랑 `--color-info`** | **❌** |
| **약한 유사** | **rgb(96,165,250) 파랑 `--sim-low-border`** | **회색 `--text-muted`** | **❌** |

### 원인
Phase 1 작성 시 미니맵을 시맨틱 토큰(`--color-error/warning/info`)으로 매핑했으나 본문 하이라이트는 Plan-45 v3 디자인의 `--sim-*-border` 전용 토큰 사용. 두 매핑 체계 불일치.

### 수정 (12 라인 — `css/compare.css` L184~189 + L228~233)
미니맵 마커·툴팁 dot 모두 `--sim-*-border` 토큰으로 통일:
```
--color-error    → --sim-identical-border
--color-warning  → --sim-near-copy-border
--color-info     → --sim-paraphrase-border  (보라로 정정)
--text-muted     → --sim-low-border          (파랑으로 정정)
--border-color   → --sim-boilerplate-border
```

### 검증
- 단위 21/21 PASS · sim_label_consistency PASS · vm.Script errors 0
- 토큰 직접 read: sim-identical=#ef4444 / near_copy=#f59e0b / paraphrase=#7c3aed / low=#3b82f6 / boilerplate=#9ca3af
- 다크 모드 자동 전환 (tokens.css `body[data-theme="dark"]` 오버라이드 사용)
- 본문 `.sim-hl-*` border-color 와 100% 동일 토큰 → 완전 일치

### 영향 범위
- `.sim-mark-cat-*` 클래스는 미니맵 마커 + 툴팁 dot 만 사용 (grep 검증)
- 본문 하이라이트(.sim-hl-*) · 사이드바 카드 · 필터 칩 · 도움말 모달 모두 무관
- 회귀 위험 0

## 추가 hotfix3 — 본문 outlier 정정 (전 UI 색상 통일)

사용자 후속 지적 — "약한 유사가 회색인데, 체크 ON 해보니까 본문에 파란색으로 표현되네."

### 진단 (전수 매트릭스)
3 카테고리에서 본문(`.sim-hl-*`) 가 사이드바·필터·카드·도움말과 다른 색 사용 (Plan-45 v3 통합 시 본문만 옛 `--sim-*-*` 토큰 잔존):

| 카테고리 | 본문 (이전) | 그 외 모든 UI | 정합성 |
|---------|------------|---------------|--------|
| 의역 | 보라 #7c3aed | 파랑 `--color-info` | ❌ |
| 약한 유사 | 파랑 #3b82f6 | 회색 `--text-muted` | ❌ |
| 자동 제외 | 중간 회색 #9ca3af | 옅은 회색 `--border-color` | ❌ (미세) |

hotfix2 가 미니맵을 본문과 일치시키며 outlier 그룹이 미니맵·툴팁까지 확장됨.

### 수정 — tokens.css 5개 토큰 정렬 + 인쇄 리포트 1라인

**css/tokens.css** (라이트 + 다크):
```css
/* 라이트 */
--sim-paraphrase: rgba(124,58,237,0.15) → rgba(59,130,246,0.15)   /* 보라→파랑 */
--sim-paraphrase-border: #7c3aed → #3b82f6                         /* 보라→파랑 */
--sim-low: rgba(59,130,246,0.1) → rgba(148,163,184,0.10)            /* 파랑→회색 */
--sim-low-border: #3b82f6 → #94a3b8                                /* 파랑→회색 */
--sim-boilerplate-border: #9ca3af → #dde4e8                        /* 중간→옅은 회색 */

/* 다크 동일 패턴 (다크 시맨틱 토큰값으로 정렬) */
--sim-paraphrase: rgba(167,139,250,0.2) → rgba(96,165,250,0.20)
--sim-paraphrase-border: #a78bfa → #60a5fa
--sim-low: rgba(96,165,250,0.12) → rgba(156,163,175,0.12)
--sim-low-border: #60a5fa → #9ca3af
--sim-boilerplate-border: #6b7280 → #3d3f50
```

**compare.html L5149** (인쇄 리포트):
```css
.mb-translation { background: #7c3aed; } → #2563eb  /* paraphrase 와 일치 (의역 통합) */
```

### 영향 범위 (정밀 grep 결과)
| 위치 | 자동 정렬 |
|------|----------|
| 본문 hl (`.sim-hl-paraphrase`, `.sim-hl-low_sim`, `.sim-hl-boilerplate`) | ✅ tokens.css 변경으로 자동 |
| 미니맵 마커 | ✅ 자동 (`.sim-mark-cat-*` 가 `--sim-*-border` 참조) |
| 호버 툴팁 dot | ✅ 자동 (동일 토큰 참조) |
| `.sim-tier-seg-derived` | ✅ 자동 (`--sim-paraphrase-border` 참조) |
| `.sim-tier-seg-boilerplate` | ✅ 자동 |
| 인쇄 리포트 `.mb-translation` | ✅ 직접 정정 |

다른 모드 (diff `.cp-*`, verify `.vd-*`) 무관 — 별 토큰 사용.

### 검증
- 단위 21/21 PASS · sim_label_consistency PASS · vm.Script errors 0
- **Playwright 토큰 직접 read 라이트**: paraphrase=#3b82f6 (= color-info) / low=#94a3b8 (= text-muted) / boilerplate=#dde4e8 (= border-color) ✅
- **Playwright 토큰 직접 read 다크**: paraphrase=#60a5fa / low=#9ca3af / boilerplate=#3d3f50 ✅
- **Playwright 가상 `.sim-hl-*` 노드 cascade 실측 (라이트+다크)** — 본문 background 와 border-left 모두 의도한 색상으로 정렬:
  - 의역: bg rgba(59,130,246,0.15) / border rgb(59,130,246) ✅
  - 약한유사: bg rgba(148,163,184,0.10) / border rgb(148,163,184) ✅
  - 자동제외: border rgb(221,228,232) (옅은회색) ✅

### 최종 매트릭스 (모든 9 위치 일관)

| 카테고리 | 라이트 색상 | 모든 위치 일치 |
|---------|------------|---------------|
| 동일 | #ef4444 빨강 | ✅ |
| 거의 동일 | #f59e0b 주황 | ✅ |
| **의역** | **#3b82f6 파랑** | **✅ (보라→파랑 정정)** |
| **약한 유사** | **#94a3b8 회색** | **✅ (파랑→회색 정정)** |
| **자동 제외** | **#dde4e8 옅은회색** | **✅ (중간→옅은 정정)** |

사용자 멘탈 모델 회복 — 사이드바·필터·미니맵·본문 모두 동일 색.

## 잔여·후속 (이번 범위 외)

- [ ] **Phase 3 — diff·sim 코드 통합** — 잠재 부채 정리 (사용자 만족 시 미진행)
- [ ] **Phase 2 호버 툴팁 추가 — 좌측 패널 마커 시 우측 표시 우선 휴리스틱** (DR-W5, 마이크로 개선)
- [ ] **마커 폭 확장** — 호버 영역 확장 검토
- [ ] memory 후보 — "scroll container 실측 검증 필수" 패턴

## 커밋 제안

```
버그 [Verify/Compare] Plan-48 hotfix — 유사도 미니맵 위치 정확도 정상화

긴 문서(4397 문장) Playwright 실측에서 발견된 두 근본 결함 청산.
사용자 지적 — "잘 표현되지 않는다 / 위치가 안 맞는다" 100% 해소.

근본 원인:
1. 잘못된 scroll container 참조 — panel-body-a.scrollHeight 사용 중인데
   진짜 scroll container 는 자식 .sim-md-view (자체 overflow:auto).
   분모 42배 작아져 ratio 폭주 → 마커 263개 중 243개가 top=14 누적.
2. display:none element 의 offsetTop=0 — 약한 유사 default OFF +
   자동 제외 본문 element 가 hidden 인데 카드만 가시 → 마커 잘못 생성.

수정:
- simRenderMinimap: panelA.querySelector('.sim-md-view') || panelA
  fallback 으로 진짜 scroller 결정 (diff 모드 호환)
- simAppendSpanMark: scroller.scrollHeight 분모 + offsetHeight>0
  visible element 만 채택. 모두 hidden 이면 마커 자체 skip.

검증 (Playwright 4_Life-Cycle vs 5_Generating Diverse Datasets):
- 마커 263→20개 (visible 매칭만 정확 표시)
- distinct top 위치 21개→19개 (사실상 모두 분리)
- top 범위 14~14620 (대부분 14)→67~963px (미니맵 풀 활용)
- 5개 샘플 수학 정합성 검증 — 서브픽셀 단위 정확
- 클릭 점프·active 동기·호버 툴팁·다크 모드 모두 정상
- 단위 21/21 PASS · sim_label_consistency PASS · vm.Script errors 0

스크린샷:
- plan-48-bug-minimap-stacked.png (Before)
- plan-48-hotfix-after.png (After 라이트)
- plan-48-hotfix-click-jumped.png (클릭 점프)
- plan-48-hotfix-tooltip.png (호버 툴팁)
- plan-48-hotfix-dark.png (다크 모드)

diff 모드 미니맵 영향 0 (.sim-md-view fallback 으로 panel 직접 사용).
백엔드·SSOT·라벨 불변. Plan-45 invariants 준수.
```
