# Plan-51 — 유사도 매칭 병합 ri 단방향 검사 결함 수정 검증

> 작성일: 2026-04-30
> 변경 범위: `backend/services/similarity_engine.py` (1줄), `compare.html` (1줄), `tests/sim_merge_adjacent_unit_test.py` (신규)
> 검증: 단위 테스트 fail-then-pass + API E2E + 자동 회귀 (점수 + SSOT 라벨)

---

## 1. 배경

### 사용자 페인
유사도 검사 결과 패널에서 카드 클릭 시 좌(A) 패널은 매칭 위치로 스크롤되지만 **우(B) 패널은 일부 카드에서 스크롤되지 않음**. 사용자가 카드의 ref_text 를 우 패널 Ctrl+F 로 검색해 본 결과 **텍스트는 패널에 존재하지만 마킹 클래스가 부착되지 않은 상태**. 발생 카테고리는 **"의역" 집중**.

### 결함 메커니즘
`_merge_adjacent` 의 ri 인접 검사가 단방향 (`m.ri - prev.ri_end <= 2`) 으로, 음수도 통과. ti 정렬 후 인접한 두 매칭의 ri 가 역방향이면 잘못 병합 → `ri_end < ri_start` 인 망가진 범위 → 프론트 마킹 루프 0회 실행.

### 의역 집중 발현 이유
- L1 fingerprint 매칭 (identical, near_copy) — 텍스트 동일성 기반, ti↔ri 위치 상관 강함
- **L3 semantic 매칭 (paraphrase, translation) — 의미 기반, 위치 무관 페어링** → ti 정렬 후 ri 역행 흔함
- 사용자 관찰과 메커니즘이 정확히 일치

---

## 2. 변경 항목

### 2-1. 백엔드 (`backend/services/similarity_engine.py:794`)
```python
# Before (단방향)
and m["ref_idx"] - prev.get("ref_idx_end", prev["ref_idx"]) <= 2)

# After (양방향 forward 강제)
and 0 <= m["ref_idx"] - prev.get("ref_idx_end", prev["ref_idx"]) <= 2)
```

### 2-2. 프론트 방어선 (`compare.html:2773`)
```js
// Before
var endR = m.ref_idx_end !== undefined ? m.ref_idx_end : startR;

// After (백엔드 회귀 시 silent 페인 방지)
var endR = (m.ref_idx_end !== undefined && m.ref_idx_end >= startR) ? m.ref_idx_end : startR;
```

### 2-3. 신규 단위 테스트 (`tests/sim_merge_adjacent_unit_test.py`)
7 케이스 (A~G) 검증:
| Case | 시나리오 | 의도 |
|------|---------|------|
| A | Forward 정상 병합 [ti:5-6, ri:10-11] | 회귀 방지 |
| B | Forward 경계 gap=2 | 회귀 방지 |
| C | Forward ti gap=3 미병합 | 회귀 방지 |
| **D** | **ri 큰 역행 (-40) 미병합** | **★ 핵심 결함 검증** |
| **E** | **ri 작은 역행 (-1) 미병합** | **★ 결함 보강 검증** |
| F | Type 다른 매칭 (paraphrase + translation) 미병합 | 회귀 방지 |
| G | Forward 3건 연쇄 병합 | 회귀 방지 |

---

## 3. 검증 결과

### 3-1. 단위 테스트 — fail-then-pass

#### 수정 전
```
PASS  A. Forward 정상 병합 [ti:5-6, ri:10-11]
PASS  B. Forward 경계 gap=2 병합 [ti:5-7, ri:10-12]
PASS  C. Forward ti gap=3 미병합 → 2건 유지
FAIL  D. ★ ri 큰 역행 (-40) 미병합 — 핵심
      Case D 실패: ri 역행 (-40) 잘못 병합됨 (merged=1건). merged[0].ri=50, ri_end=10
FAIL  E. ★ ri 작은 역행 (-1) 미병합
      Case E 실패: ri 1 역행 잘못 병합됨 (merged=1건). merged[0].ri=10, ri_end=9
PASS  F. Type 다른 매칭 미병합 (paraphrase + translation)
PASS  G. Forward 3건 연쇄 병합 [ti:5-7, ri:10-12]
============================================================
FAIL: 2/7 건 실패 — 결함 객관 증거 ★
============================================================
```
→ **`merged[0].ri=50, ri_end=10`** — 정확히 예측한 `ri_end < ri_start` 패턴 직접 관찰

#### 수정 후
```
PASS  A. Forward 정상 병합 [ti:5-6, ri:10-11]
PASS  B. Forward 경계 gap=2 병합 [ti:5-7, ri:10-12]
PASS  C. Forward ti gap=3 미병합 → 2건 유지
PASS  D. ★ ri 큰 역행 (-40) 미병합 — 핵심
PASS  E. ★ ri 작은 역행 (-1) 미병합
PASS  F. Type 다른 매칭 미병합 (paraphrase + translation)
PASS  G. Forward 3건 연쇄 병합 [ti:5-7, ri:10-12]
============================================================
PASS: 7 케이스 모두 통과 — ri 양방향 forward 보장
============================================================
```

### 3-2. 기존 회귀 테스트 — 영향 0

| 검사 | 결과 |
|------|------|
| `tests/sim_score_v3_unit_test.py` | ✅ 5/5 PASS — 점수 공식 영향 0 |
| `tests/sim_label_consistency.sh` | ✅ PASS — SSOT 라벨 회귀 0 |

### 3-3. API E2E 검증 (Playwright + 백엔드 직접 호출)

#### 시나리오: 4 문단 순서 완전 역전
- target: `[winnowing, embeddings, detector, reporter]` (ti=0~3)
- reference: `[reporter, detector, embeddings, winnowing]` (ri=0~3)
- 기대: 매칭 4건 모두 분리 + ri 역행 0건 + 양 패널 정확 마킹

#### 실제 결과
```json
{
  "matches_count": 4,
  "inverted_count": 0,
  "similarity_score": 100,
  "matches": [
    {"type":"identical","ti":0,"ri":3},
    {"type":"identical","ti":1,"ri":2},
    {"type":"identical","ti":2,"ri":1},
    {"type":"identical","ti":3,"ri":0}
  ],
  "A_sim_idx_total": 4,
  "B_sim_idx_total": 4,
  "missing_A_count": 0,
  "missing_B_count": 0,
  "per_match": [
    {"i":0,"aHits":1,"bHits":1},
    {"i":1,"aHits":1,"bHits":1},
    {"i":2,"aHits":1,"bHits":1},
    {"i":3,"aHits":1,"bHits":1}
  ]
}
```

→ 모든 매칭 양 패널 정확 마킹. 수정 전이라면 broken merge 1건 [ti:0-3, ri:3-0] 이 되어 B 마킹 0건이었을 시나리오.

### 3-4. 시각 캡처
- `plan51-after-fix-both-panels-marked.png` — 수정 후 정상 동작 화면

---

## 4. 영향 분석 (코드 전문가 관점)

### 4-1. 격리
수정 영향이 명시적으로 다음 케이스에만 국한:
- **차이 발생 케이스**: `m.ref_idx < prev.ref_idx_end` (ri 역행)
- **무영향 케이스**: forward 병합, 큰 gap, type 다름, 정상 분리 등 모든 경우

### 4-2. 토큰·SSOT·점수 보존
- `tokens.css`, `similarity-help.json` 무수정
- Plan-50 sentence index set 분모는 type 무관 → similarity_score **0 변동**
- verdict_band, exclusion_breakdown 등 파생 필드 무영향

### 4-3. 프론트 방어선 격리
- 수정된 endR 가드는 `m.ref_idx_end >= startR` 인 정상 케이스에선 기존 동작과 100% 동일
- 백엔드 회귀로 ri_end < startR 인 매칭이 들어와도 startR 1점 마킹으로 silent 페인 방지

---

## 5. 영향 분석 (UX/UI 전문가 관점)

### 5-1. 사용자 페인 직접 해소
- 카드 클릭 → 양 패널 동기 스크롤 정상화
- 의역 카드의 ref_text 미리보기 jumbled 제거 (ri 역행 병합 폐기)
- 우 패널 마킹 누락 0

### 5-2. 카드 개수 변화
- ri 역행 페어가 분리되어 의역 카드 개수 약간 증가 가능 (5~20% 추정)
- **정보 손실 0** — 분리 전 카드는 시각화 깨진 상태였음
- 분리 후 카드는 각각 정상 마킹·네비게이션

### 5-3. 점수 변동 0
- Plan-50 sentence index set 분모 기반 → 카드 개수와 무관
- 동일 입력 수정 전후 similarity_score 100 → 100 (변동 없음)

---

## 6. 사용자 관점 피드백

### Before (사용자 보고)
- "의역 카드 클릭하니 좌(A)는 가는데 우(B)는 그대로"
- "Ctrl+F 로 ref 문장 찾아도 마킹 안 됨"

### After
- 모든 카드 양 패널 동기 스크롤
- ref 문장 마킹 누락 0
- 의역 카드 미리보기 텍스트 정합 회복

### 통일된 경험
- L1 (identical/near_copy) 과 L3 (paraphrase/translation) 카드 모두 동일한 양방향 동기화
- 백엔드 회귀해도 프론트 가드로 최소 동작 보장 — silent fail 페인 방지

---

## 7. 부수 발견 (현 범위 외)

| # | 항목 | 비고 |
|---|------|------|
| O-1 | startT/endT 도 동일 가드 적용 가능 | ti 는 sort 보장으로 거의 항상 forward, 일관성 차원에서 후속 검토 |
| O-2 | 매칭 type 동일성 검사 외에 cross-language flag 차이도 추가 검토 가능 | translation vs paraphrase 분기 강화 후속 |
| O-3 | _merge_adjacent 가 (ti, ri) 의 2D 조밀도 기반 클러스터링으로 발전할 여지 | 현 그리디 인접 병합으로 충분, 발전은 페인 발생 시 |

---

## 8. 한 줄 결론

**PASS.** Plan-51 완료 — `_merge_adjacent` ri 인접 검사 단방향 결함 수정 (1줄) + 프론트 방어선 (1줄) + 회귀 단위 테스트 7건. 의역 카테고리 B 패널 마킹·네비 미동기 페인 직접 해소. 점수·라벨·기존 카테고리 회귀 0. 단위 테스트 fail-then-pass 로 결함 객관 증거 확보 + 수정 효과 검증.
