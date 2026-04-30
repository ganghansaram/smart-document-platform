# Plan-50 — 유사도 점수 공식 통일 + 부수 정합성 정정

> 작성일: 2026-04-29
> 상태: 🟡 계획 단계 (구현 전 사용자 승인 필요)
> 영향 범위: `backend/services/similarity_engine.py`, `compare.html`, `css/compare.css`, `tests/sim_label_consistency.sh`
> 선행: Plan-45 (v3 SSOT 통일) — 백엔드 잔존분 발견으로 본 계획 도출

---

## 진행 현황 요약

| Phase | 제목 | 상태 | 커밋 | 비고 |
|-------|------|------|------|------|
| 계획서 | 작성 + 결정 시트 + 현업 피드백 반영 | ✅ 완료 (2026-04-30) | `9b15dbe` | 본 문서 |
| **Phase 0** | 회귀 방어망 강화 (테스트 스크립트·골든셋) | ✅ 완료 (2026-04-30) | `8931b01` | sim_label_consistency C2/T1 패턴 + 골든셋 5건 신규 |
| **🔴 Phase 1** | 백엔드 점수 공식 v3 통일 (`× 0.5` 제거) — 자동 파급 (verdict·tiers·이력 등) | ✅ 완료 (2026-04-30) | `d0d62cd` | similarity_engine.py 1라인 수정, 골든셋 5/5 PASS |
| **🔴 Phase 2** | 배너·보고서 baseline 정합 + 단일 점수 표시 | ✅ 완료 (2026-04-30) | `6d482d2` | 화면 "원점수" 제거, 보고서 score_baseline 신규 |
| **Phase 3** | 옛 3단계 임계값 잔존 정리 (이력 색상·verdict_legacy) | ✅ 완료 (2026-04-30) | `6d482d2` | 이력 색상 v3 verdict 기반, 25/74 임계 정합 (P2 와 같은 commit) |
| **Phase 4** | 분모 계산 정합 (sentence index set) | ✅ 완료 (2026-04-30) | (예정) | computeScore 우선순위 (excluded > identical > near_copy > paraphrased > low_sim) 적용 |
| **Phase 5** | 사이드바·그룹 헤더 단위 표기 통일 | ✅ 완료 (2026-04-30) | (예정) | 그룹 헤더·sectionCounts 모두 sentence span 합산으로 통일 |
| **Phase 6** | 약한 유사 ⓧ 버튼 제거 (점수 상승 역설 해소) | ✅ 완료 (2026-04-30) | (예정) | 카드 + 그룹 헤더 일괄 버튼 모두 약한 유사 카테고리에서 미노출 |
| **Phase 7** | 마감 (NaN 방어 + 단위 표기 + 디버그 로그) | ✅ 완료 (2026-04-30) | `3f36acf` | target_idx NaN 방어, 100% 초과 console.warn, 배너·모달 "N건 (M문장)" 병기 |
| **hotfix1** | 다운로드 회귀 + verdict stale + baseline reset (C-1·W-1·W-2·W-3·W-5) | ✅ 완료 (2026-04-30) | (예정) | Phase 2 var tiers 정리 누락 → 다운로드 ReferenceError 복구 + 보고서 verdict 라벨 v3 score 기반 재계산 |

**상태 범례**: ⏸ 대기 / 🟡 진행 중 / ✅ 완료 / ⏹ 보류
**Plan-50 전체 완료** (2026-04-30) — 유사도 점수 공식·단위·UX 정합 부채 해소 완성. 업계 표준 (Turnitin·Copyleaks) 산식·UX 패턴에 정렬.

---

## 1. 배경

Plan-45 에서 유사도 라벨·공식을 v3 (Copyleaks, 가중치 없음) 으로 통일했으나, 점수 계산식 점검 중 **백엔드에 Plan-38 옛 가중치 공식이 잔존** 함을 확인. 동시에 단위 표기·분모 계산·예외 케이스 몇 가지 정합 부채가 발견됨.

### 1-1. 핵심 증거 (코드 위치)

**백엔드 (잔존 옛 공식)** — `backend/services/similarity_engine.py:897`
```python
adjusted_pct = round((substantive + derived * 0.5) / effective_total * 100, 1)
```
의역(derived) 에 `× 0.5` 가중치 — Plan-38 옛 공식.

**프론트 (v3 SSOT)** — `compare.html:2355`
```js
var scored = counts.identical + counts.near_copy + counts.paraphrased;
// 가중치 없음 (Plan-45 v3)
```

### 1-2. 사용자에게 노출되는 결과 (실측)

| 표시 위치 | 사용 점수 | 공식 |
|----------|----------|------|
| 점수 카드 (sim-score) | 프론트 재계산 | v3 (가중치 없음) |
| 7지표 카드·필터 칩·누적바 | 프론트 재계산 | v3 |
| 5단계 신호등 (sim-verdict) | 프론트 재계산 | v3 |
| **배너 "원점수 X% → 조정 Y%"** | `tiers.adjusted` | **옛 공식** |
| **보고서 `payload.score_original`** | `tiers.adjusted` | **옛 공식** |
| 보고서 `payload.score` | DOM 점수 | v3 |
| 보고서 `verdict` / `verdict_label` | 백엔드 응답 | **옛 공식 기반** |

→ 사용자가 화면에서 보는 점수와 보고서·배너 일부 점수가 다른 공식으로 산출되어 **정합성 깨짐**.

### 1-3. 실측 시나리오

테스트 (의역 10건, 전체 10문장):
- 점수 카드: **100%** (v3)
- 배너 원점수: **50%** (옛 공식: `0 + 10×0.5 / 10 × 100`)
- 사용자 인지: "원점수 50% 인데 왜 점수 카드는 100% ?" → 신뢰 손상

### 1-4. 현업 부서 사용 테스트 피드백 (2026-04-30 수신)

**피드백 1 — "원점수" 라벨 의미 불명**
> 불필요 검출항목을 제거하여 유사도 점수를 낮추는데, 수동제외를 통한 원점수라는게 등장함. 원점수가 뭔지? 낯선 단어인데, 누구든 이걸 보면 뭔지 설명해달라고 할 듯. 큰 의미 없으면, 제거하고 단일 점수로 (수정→점수반영 단순 로직) 관리하는게 낫지 않을까? 심지어, 최초 41.6%가 나왔는데, 몇개 항목을 제거 했더니, 39.4% (원점수20.3% → 조정 39.4%) 로 표기됨. 그래서 원점수가 뭔지 더 궁금해짐.

→ **I-2 (배너 옛 공식) + I-12 (라벨 모호)** 가 정확히 일치. "원점수 20.3% < 조정 39.4%" 의 역행은 옛 공식 baseline (가중치 0.5) 이 v3 점수(가중치 1.0)보다 낮게 산출되어 발생.

**피드백 2 — 보고서 점수 BOX 색상·라벨 불일치**
> 출력한 Report에 변경된 점수BOX 영역에 '양호'로 녹색으로 보여지는데, 점수/등급 기준에 5단계 신호등 기준에 라벨및 색상이 맞질 않음

→ **I-4 (백엔드 verdict_band 옛 공식 기반)** 가 정확히 일치. 보고서 score-band CSS 클래스가 `payload.verdict` (백엔드 옛 공식) 결정 → 점수 자체는 v3 라 라벨/색상 모순.

→ 두 피드백 모두 본 계획서가 정확히 해결하는 영역. **§5 Phase 1+2 가 동시 해소**.

---

## 2. 발견된 이슈 일람

| # | 항목 | 심각도 | 위치 |
|---|------|--------|------|
| I-1 | 백엔드 `adjusted_pct` 옛 가중치 공식 | 🔴 Critical | `similarity_engine.py:897` |
| I-2 | 배너 "원점수" 가 옛 공식 점수 직접 표시 | 🔴 Critical | `compare.html:3034` (`simUpdateExclusionBanner`) |
| I-3 | 보고서 `payload.score_original` 옛 공식 | 🔴 Critical | `compare.html:5127` |
| I-4 | 백엔드 `verdict_band` 옛 공식 점수 기반 | 🟡 Warning | `similarity_engine.py:923` |
| I-5 | 분모 계산 — 프론트 span 합산 vs 백엔드 sentence index set | 🟡 Warning | `compare.html:2342~2358` vs `similarity_engine.py:858~865` |
| I-6 | 사이드바 indicator (sentence count) vs 그룹 헤더 (card count) 단위 불일치 | 🟡 Warning | `compare.html:2607` vs L2436~2438 |
| I-7 | 약한 유사 수동 제외 시 점수 상승 역설 (분자 미반영, 분모만 감소) | 🟡 Warning | `computeScore` 정의상 부작용 |
| I-8 | `target_idx`/`target_idx_end` 미존재 시 NaN 가능 | 🟡 Warning | `compare.html:2349` |
| I-9 | `sim_label_consistency.sh` 가 백엔드 `× 0.5` 패턴 미검출 (false negative) | 🟡 Warning | `tests/sim_label_consistency.sh:90~99` |
| I-10 | 배너 "수동 제외 N건" — N 이 카드 수, 점수 분모는 문장 수 | 🛈 Suggestion | `compare.html:3047` |
| I-11 | 100% 캡 silent (데이터 무결성 위반 단서 없음) | 🛈 Suggestion | `compare.html:2357`, backend L899 |
| I-12 | "원점수" 라벨 의미 모호 (수동 제외 전? 자동 제외 전? 어느 baseline?) | 🛈 Suggestion | UX |
| **I-13** | **이력 페이지 점수값 = 백엔드 옛 공식** (`summary.similarity_score` 직접 저장) | 🟡 Warning | `compare.html:2666` |
| **I-14** | **이력 점수 색상 임계 = 옛 3단계 (40/70%)** (Plan-45 v3 5단계와 불일치) | 🟡 Warning | `compare.html:2664~2665` |
| **I-15** | `verdictBoundLow/High` (30/60) 옛 3단계 임계값 변수 잔존, `payload.verdict_legacy` 등에서 사용 | 🟡 Warning | `compare.html:621~622, 5147` |
| **I-16** | 화면 배너 "원점수" 표현 — 사용자 인지 부담 (현업 피드백 1과 직결) | 🔴 Critical | UX |

---

## 3. 목표

1. **점수 공식 단일화** — v3 (Copyleaks, 가중치 없음) 가 백엔드·프론트·보고서·이력에서 동일 사용
2. **분모 계산 정합** — sentence index set 기반으로 양측 통일 (cluster overlap 시 분모 부정확 제거)
3. **단위 표기 정합** — UI 모든 카운트는 sentence count (또는 명시적으로 단위 라벨링)
4. **회귀 방어망 강화** — `sim_label_consistency.sh` 가 백엔드 잔존 옛 공식도 검출
5. **기존 사용자 영향 최소화** — Phase 별 안전 적용, 보고서 점수 표기 변동 가능성을 사용자에게 사전 고지

---

## 4. 비목표 (이번 계획 범위 외)

- 점수 산식 자체 재설계 (v3 공식 유지)
- 5단계 신호등 임계값 변경 (Plan-45 임계값 유지)
- 새 매칭 알고리즘 도입
- Compare·Verify 모드 (유사도 모드 한정)
- 보고서·이력 소급 재계산 (저장된 보고서는 그대로 — 신규 검사부터 v3 적용)

---

## 5. Phase 구성

### Phase 0 — 회귀 방어망 강화 (선행, 위험 0)
**목적**: 다음 Phase 들의 회귀를 자동 감지할 수 있게 인프라 준비.

**작업**
- `tests/sim_label_consistency.sh` 에 백엔드 옛 공식 패턴 추가:
  - `derived * 0.5`
  - `+ derived * 0.5`
  - `(substantive + derived`
  - 복합 패턴 — Python·JS 양쪽 정규식
- 골든셋 시나리오 1건 추가 — 의역 N개 단순 케이스, 기대 점수 v3 명시 (`tests/sim_score_v3.json` 신규)
- 골든셋 검증 스크립트 (`tests/sim_score_v3_test.sh`) — 백엔드 응답 vs 기대값 비교

**검증**: Phase 0 적용 후 현재 코드 베이스에서 `sim_label_consistency.sh` 가 **FAIL** (옛 공식 검출) 해야 정상 — 그래야 다음 Phase 의 수정이 PASS 로 전환 보장.

**롤백**: 검사 스크립트만 변경 → 그대로 revert.

---

### Phase 1 — 백엔드 점수 공식 v3 통일 (Critical Fix)
**목적**: I-1, I-4 해소. 백엔드 출력을 v3 공식으로 통일.

**작업**
- `similarity_engine.py:897` 변경
  ```python
  # Before (Plan-38 잔존)
  adjusted_pct = round((substantive + derived * 0.5) / effective_total * 100, 1)
  # After (Plan-45 v3)
  adjusted_pct = round((substantive + derived) / effective_total * 100, 1)
  ```
- `tiers` 호환 필드 (`substantive_pct`, `derived_pct`) 는 유지 (보고서 호환)
- `_compute_verdict_band(adjusted_pct)` 자동으로 v3 점수 기반이 됨 (I-4 해소)

**프론트 영향**
- `compare.html:2400` 의 "백엔드 tiers 구공식 값 미사용" 주석은 그대로 유지하되, 의도가 충족됨 — 백엔드도 이제 v3
- 프론트 v3 재계산은 그대로 유지 (수동 제외 즉시 반영 위해)

**검증**
- Phase 0 골든셋 PASS
- `sim_label_consistency.sh` PASS
- 회사 운영 환경 영향: 새 검사부터 점수 표기가 변동 (예: 의역 다수 문서에서 점수 상승). **사용자 사전 고지 필요**.

**롤백**: 1라인 revert. 위험 낮음.

---

### Phase 2 — 화면 배너 단일 점수 + 보고서 baseline 정합 (UX Critical)
**목적**: I-2, I-3, I-12, I-16 해소. 현업 피드백 1 ("원점수가 뭔지?") 직결.

**설계 방침** (현업 피드백 반영, §9 결정 시트 (B) 채택)
- **화면 배너**: 단일 점수만 표시. baseline 노출 제거.
  - 형태 예: `유사율 39.4%` + 작은 글씨 `수동 제외 N건 반영` (액세서리 라인)
  - "원점수" 라벨 자체를 화면에서 제거 → 사용자 인지 부담 0
- **보고서 (HTML/PDF/Excel)**: 감사 추적용 baseline 유지
  - `payload.score` (조정 v3 점수) 와 `payload.score_baseline` (수동 제외 전 v3 점수) 두 점수 모두 표기
  - 라벨도 "수동 제외 전 X%" 로 명확화 (사용자 가이드에 풀이 추가)

**작업**
- `compare.html:simUpdateExclusionBanner` — 옛 `tiers.adjusted` 의존 제거, 배너 텍스트를 단일 점수 + 액세서리 라인 형태로 변경
- `simShowResults` — 초기 `computeScore` 결과를 `simBaselineScore` 변수로 저장 (수동 제외 전 v3 점수)
- `buildExportPayload` — `payload.score_baseline` 신규 필드 (= simBaselineScore), `payload.score_original` 은 동일 의미로 v3 baseline 으로 변경 (호환 유지)
- 보고서 `buildSimilarityReportHtml` (compare.html:5331) — 라벨 "원점수" → "수동 제외 전" 으로 변경
- 사용자 가이드 (`contents/guide/verify-guide.html`) — Phase 1+2 적용 후 "원점수" 표현 풀이 (필요 시 — 현재 가이드에는 미사용 확인됨)

**검증**
- 화면 배너: "원점수" 단어 0건. 단일 점수 + "수동 제외 N건 반영" 노출
- 보고서: "수동 제외 전 X%" + "조정 Y%" 둘 다 표기 (감사 추적)
- 시나리오: 41.6% (초기) → 5건 제외 → 39.4% (조정) → 보고서 baseline 41.6%, 조정 39.4% — 직관적 단조 감소

**롤백**: 1라인 변수 제거 + 배너 텍스트 원복. 위험 낮음.

---

### Phase 3 — 옛 3단계 임계값 잔존 정리 (이력 색상·verdict_legacy)
**목적**: I-13, I-14, I-15 해소. Phase 1 영향 후속.

**작업**
- `compare.html:2664~2665` 이력 저장 시 `simScoreColor` 임계 (40/70) 를 5단계 verdict_band 결과로 대체
  - 형태: `addHistory({ score, scoreColor: bandColorMap[summary.verdict] })`
  - 백엔드 verdict 가 v3 기반이 되었으므로 자동 정합 (Phase 1 영향)
- `compare.html:2666` 이력 저장 점수값 — `summary.similarity_score` 가 Phase 1 적용 후 v3 점수가 됨 (자동 해소)
- `payload.verdict_legacy` 폐기 또는 v3 기반 재정의 (compare.html:5147)
- `verdictBoundLow/High` 변수 (compare.html:621~622) — 사용처 정리 후 폐기 (v3 5단계 verdict_bands 단일화)

**검증**
- 이력 페이지 점수 색상이 v3 5단계 (Blue/Green/Yellow/Orange/Red) 와 일치
- `grep -nE "verdictBoundLow|verdictBoundHigh|verdict_legacy" compare.html` 결과 0건 (또는 호환 의도된 1건만)

**위험 평가**: 낮음. 표시 로직만 변경, 데이터 모델 무변동.

**롤백**: 이력 저장 라인 + verdict_legacy 라인 revert.

---

### Phase 4 — 분모 계산 정합 (sentence index set 통일)
**목적**: I-5 해소. cluster overlap 시 분모 부정확 제거.

**작업**
- `compare.html:computeScore` — span 단순 합산을 sentence index set 으로 전환
  ```js
  var includedIdx = {};      // matched & non-excluded sentence indices
  var excludedIdx = {};
  for each match:
      for sIdx in [target_idx ... target_idx_end]:
          if cat in (excluded_auto, excluded_manual): excludedIdx[sIdx] = true
          else if cat in (identical, near_copy, paraphrased): includedIdx[sIdx] = true
  scored = Object.keys(includedIdx).length
  excluded = Object.keys(excludedIdx).length
  ```
- 같은 sentence 가 여러 카드에 매칭되어도 분모 1번만 차감
- 백엔드 로직과 동일 동선

**검증**
- 단위 테스트 (Phase 0 골든셋 확장): cluster overlap 시나리오 (sent 0~5 가 카드 A 의역, sent 3~7 이 카드 B 동일) → 분모 = 8 (sent 0~7), 분자 = 8
- 기존 단순 케이스 점수 무변동

**위험 평가**: **중**. 분모 계산 변경은 점수 변동 직접 야기. 사용자 사전 고지 + 시각 검증 필수.

**롤백**: 변수 교체. 다소 큰 패치라 git revert 권장.

---

### Phase 5 — 단위 표기 통일
**목적**: I-6 해소. 사이드바·그룹 헤더 카운트 단위 일치.

**옵션**
- (A) **모두 sentence count** (sentence span 합계) — 점수 분모와 같은 단위, 직관적. 단점: 카드 1개가 cluster 면 "10건" 으로 표시되어 카드 수와 다름.
- (B) **모두 card count** — 카드 1개당 1로 카운트. 단점: 점수 분모(sentence)와 단위 다름.
- (C) **둘 다 표시** — 예: "의역 10문장 (1건)" — 가장 명확하지만 헤더 공간 부담

**권장**: (A) sentence count — 점수 분모와 일관, 사용자가 "10문장 일치" 이해하기 쉬움. 그룹 헤더의 `bucket.length` 를 `bucket.reduce(span)` 으로 변경.

**작업**
- `compare.html:2607` 그룹 헤더 count 를 sentence span 합계로 변경
- 일괄 제외 모달 "N건 일괄 처리" → "N문장 일괄 처리" 또는 "N건 매칭 (X문장) 일괄 처리"

**검증**: 사이드바 indicator 와 그룹 헤더 count 가 동일

**롤백**: 라인 단위 revert.

---

### Phase 6 — 약한 유사 수동 제외 정책 (역설 해소)
**목적**: I-7 해소. 약한 유사 수동 제외 시 점수 상승 방지.

**옵션**
- (A) 약한 유사는 수동 제외 불가 (UI ⓧ 버튼 숨김) — 가장 깔끔
- (B) 약한 유사 수동 제외 시 분모에서도 빼지 않음 — `computeScore` 분기 추가
- (C) 현 상태 유지 + 사용자 가이드에 명시

**권장**: (A) — 약한 유사는 점수 미반영이므로 수동 제외 자체가 의미 없음. UI 단에서 ⓧ 버튼 숨기면 사용자가 의문 가질 일 없음.

**작업**
- `compare.html:2581` 카드 ⓧ 버튼 렌더 분기에 `matchCat !== 'low_similarity'` 추가
- 약한 유사 그룹 헤더 [⊘ 일괄 제외] 버튼도 숨김 (`mainCatOrder.forEach` 에서 분기)

**검증**: 약한 유사 카드에 ⓧ 미노출, 그룹 헤더 일괄 버튼 미노출

**롤백**: 분기 제거.

---

### Phase 7 — 마감 (방어 + 표기)
**목적**: I-8, I-10, I-11 해소.

**작업**
- I-8: `computeScore` 에서 `target_idx`/`target_idx_end` 가 number 아니면 카운트 스킵 + console.warn (개발 환경)
- I-10: 배너 라벨 "수동 제외 N건 반영" → "수동 제외 N건(X문장) 반영" — 단위 모호 해소
- I-11: 100% 캡 발생 시 console.warn (개발 환경) — 데이터 디버깅 단서

**검증**: 기존 정상 케이스 무변동, 비정상 데이터 주입 시 경고 로그

**롤백**: 라인 단위 revert.

---

## 6. 통합 검증 절차 (Phase 1~7 적용 후)

| 검증 항목 | 통과 기준 |
|----------|----------|
| `bash tests/sim_label_consistency.sh` | PASS (백엔드 옛 공식 0건, 옛 3단계 임계값 잔존 0건) |
| `bash tests/sim_score_v3_test.sh` (Phase 0 골든셋) | 기대 점수 일치 |
| 시나리오 A — 의역 10건 단순 | 점수 카드·보고서 모두 100% (v3) |
| 시나리오 B — 현업 피드백 재현 (의역+동일 혼합, 일부 수동 제외) | 41.6% → 39.4% (단조 감소), 화면에 "원점수" 단어 0건 |
| 시나리오 C — 보고서 verdict 정합 | 점수·라벨·색상 모두 동일 5단계 기준 |
| 시나리오 D — cluster overlap (sent 0~5 paraphrase + sent 3~7 identical) | 분자=8, 분모=8, 점수=100% |
| 시나리오 E — 약한 유사만 N건 | 카드 ⓧ 미노출, 그룹 헤더 일괄 버튼 미노출 |
| 시나리오 F — 이력 페이지 색상 | v3 5단계 기준으로 표시 (40/70 옛 임계 사용 안 함) |
| Playwright — 단건/일괄 제외 회귀 | 모든 동작 정상 |
| Playwright — 다크/라이트 모드 | 시각 회귀 0 |

---

## 7. 위험 평가 및 완화

| 위험 | 영향 | 완화 |
|------|------|------|
| 점수 표기 변동 (의역 비중 큰 문서에서 상승) | 운영 사용자 혼란 | 변경 사전 공지 (전사 메일 + 가이드 페이지 보완), v2.7 → v2.8 별도 버전 분기 |
| 보고서 점수 변경 | 기존 보고서와 신규 보고서 비교 시 불일치 | 보고서 메타에 "공식 버전: v3" 표기 추가 |
| 분모 계산 변경 | cluster overlap 케이스 점수 변동 | Phase 3 별도 분리, 사전 시각 검증 필수 |
| 약한 유사 ⓧ 제거 (Phase 5) | 기존 사용자가 ⓧ 클릭 습관 있을 시 위화감 | 가이드 페이지 안내 문구 추가 |

---

## 8. 적용 순서·시점

```
[ 다음 릴리즈 v2.8 핵심 안건 — Critical 묶음 ]
Phase 0 (회귀 방어망)         — 즉시 적용 (위험 0)
  ↓
Phase 1 (백엔드 v3 통일)      — Phase 0 PASS 후. 자동 파급: verdict·tiers·이력 점수값
Phase 2 (배너 단일 점수)      — Phase 1 한 묶음 (현업 피드백 1 직접 해소)
Phase 3 (옛 3단계 임계 정리)  — Phase 1+2 직후 (이력 색상·verdict_legacy 정합)

[ 후속 릴리즈 — 정합 부채 마감 묶음 ]
  ↓
Phase 4 (분모 계산 정합)      — 위험 중, 별도 단계
  ↓
Phase 5 (단위 표기 통일)      — Phase 4 직후
Phase 6 (약한 유사 ⓧ 제거)   — 독립적
Phase 7 (마감 — 방어·로그)    — 마지막
```

**🔴 Critical 묶음**: Phase 0~3 — 현업 부서 피드백 직결, **다음 릴리즈 (v2.8) 핵심 안건**
**🟡 완전 묶음**: Phase 0~7 전체 적용 — 모든 정합 부채 해소

---

## 9. 결정 시트

| 결정 항목 | 옵션 | 권장 (현업 피드백 반영) |
|----------|------|------|
| 백엔드 공식 통일 시점 | 즉시 / 다음 릴리즈 / 운영 부하 테스트 후 | **다음 릴리즈 (v2.8)** |
| 보고서 호환 처리 | `score_original` 유지 / 제거 / 의미 재정의 | **의미 재정의** (수동 제외 전 v3 baseline) |
| **baseline 표시 방식 (UX)** | (A) 화면+보고서 모두 두 점수 / **(B)** 화면 단일 점수, 보고서만 두 점수 / (C) 모두 단일 | **(B)** — 현업 피드백 1 ("원점수가 뭔지?") 직결 |
| 단위 표기 옵션 | A 문장 / B 카드 / C 둘 다 | **A 문장** (점수 분모와 일관) |
| 약한 유사 ⓧ | A 숨김 / B 분모 보호 / C 현상 유지 | **A 숨김** |
| 옛 3단계 임계값 잔존 (`verdictBoundLow/High`, `verdict_legacy`) | A 폐기 / B 호환 유지 | **A 폐기** (5단계 SSOT 단일화) |
| 사용자 공지 채널 | 메일 / 가이드 페이지 / 배너 / 모두 | **메일 + 가이드 페이지** + 첫 검사 시 1회 인포 토스트 |

---

## 10. 후속 검토 (현재 범위 외)

- 보고서 메타에 공식 버전 표기 (`formula_version: "v3"` 필드 추가) → 미래 공식 변경 시 호환 추적
- `payload.score_original` 의 정확한 의미를 보고서 표지에 한 줄 설명 (사용자 오해 방지)
- 점수 계산 단위 테스트 인프라 정착 — 골든셋 케이스 N개 누적, CI 등록
- Compare·Verify 모드도 유사한 점수 계산 부정합 점검 (이번 계획은 유사도 모드 한정)

---

> 진행 현황 표는 문서 상단의 [진행 현황 요약](#진행-현황-요약) 참조.
