# Plan-50 Phase 4~7 — 구현 후 검증 피드백

> 작성일: 2026-04-30
> 변경 범위: `compare.html` (computeScore + 그룹 헤더 카운트 + 카드 ⓧ 분기 + 배너 + 모달)
> 검증: 자동 회귀 (sim_label_consistency + 골든셋) + Playwright 브라우저 시나리오

---

## 1. 변경 요약

### Phase 4 — 분모 계산 정합 (sentence index set)
| 위치 | 변경 |
|------|------|
| `compare.html:computeScore` | 카드 span 단순 합산 → **sentence index set + 카테고리 우선순위** (excluded > identical > near_copy > paraphrased > low_similarity) |
| 부수 | 100% 초과 시 console.warn (Phase 7 통합), `target_idx` 미존재 NaN 방어 (Phase 7 통합) |

### Phase 5 — 사이드바·그룹 헤더 단위 표기 통일
| 위치 | 변경 |
|------|------|
| 그룹 헤더 첫 렌더 | `bucket.length` (카드 수) → **`sentCount`** (sentence span 합산) |
| 헤더 count title | `"N건 매칭 / M문장"` 병기 |
| `sectionCounts` 갱신 (L3262~) | `+1` (카드 수) → **`+span`** (sentence span 합산) — 필터 토글·재렌더 시 stale 방지 |

### Phase 6 — 약한 유사 ⓧ 버튼 제거
| 위치 | 변경 |
|------|------|
| `renderCard` 카드 ⓧ 분기 (L2633) | `matchCat !== 'excluded_auto'` → `matchCat !== 'excluded_auto' && matchCat !== 'low_similarity'` |
| 그룹 헤더 일괄 버튼 분기 (L2664) | `low_similarity` 그룹은 일괄 버튼 미렌더 |

### Phase 7 — 마감 (방어 + 단위 병기)
| 위치 | 변경 |
|------|------|
| `computeScore` | `target_idx`/`target_idx_end` 타입 검증 (NaN 방어) + 100% 초과 시 console.warn |
| 일괄 모달 preview | `"의역 N건 일괄 처리"` → `"의역 N건 (M문장) 일괄 처리"` |
| `simUpdateExclusionBanner` | `"수동 제외 N건 반영"` → `"수동 제외 N건 (M문장) 반영"` (M > N 일 때만 병기) |

---

## 2. 영향도 분석 (코드 전문가 관점)

### 2-1. Phase 4 분모 정합 — 백엔드와 동일 패턴
**Before**:
```js
counts[cat] += span;  // 카드별 단순 합산. cluster overlap 시 중복 카운트
excluded += span;
```

**After**:
```js
sentCat[s] = cat;  // sentence index → 우선순위 최상위 카테고리
// 같은 sentence 가 paraphrase + identical 양쪽 카드에 매칭되어도
// rank 우선순위로 1번만 카운트 (identical 우세)
```

→ 백엔드 `similarity_engine.py` 의 `active_excluded_idx = set()` 패턴과 일치. cluster overlap 케이스에서 점수 부정확 해소.

### 2-2. Phase 5 단위 통일 — 두 갈래 모두 처리
- **첫 렌더**: 그룹 헤더 만들 때 sentCount (`bucket.reduce(span)`)
- **재렌더 stale 방지**: `sectionCounts` 도 sentence span 합산

→ 단일 단위 (sentence count) 로 통일. 사이드바 indicator·점수 분모와 일관.

### 2-3. Phase 6 약한 유사 ⓧ 제거 — 안티패턴 해소
- 약한 유사는 `scored = identical + near_copy + paraphrased` 분자에 포함 X
- 그러나 수동 제외 시 `excluded += span` → 분모 감소 → 점수 상승 (역설)
- **해결**: ⓧ 버튼 자체를 노출하지 않음 → 사용자가 분모 영향 액션 트리거 불가

### 2-4. Phase 7 방어 + 단위 병기
- NaN 방어로 silent failure (NaN 점수) 방지
- 100% 초과 console.warn → 데이터 무결성 디버깅 가시화
- 단위 병기 ("N건 (M문장)") 로 사용자 인지 명확화

### 2-5. 회귀 위험 평가
| 시나리오 | 위험 | 완화 |
|---------|------|------|
| Phase 4 — cluster overlap 케이스 점수 변동 | 🟡 중 | 우선순위 명확 정의, 백엔드와 동일 패턴 → 점수 신뢰성 강화 |
| Phase 5 — 카운트 표시 변경 | 🟢 낮 | 사용자 인지 단위 통일, 학습 비용 0 |
| Phase 6 — 약한 유사 ⓧ 제거 | 🟢 낮 | 점수 미반영 카테고리, 사용자가 ⓧ 클릭할 동기 없음 |
| Phase 7 — 방어/단위 병기 | 🟢 0 | 추가 표기, 기존 흐름 영향 없음 |

---

## 3. UI/UX 영향 분석

### 3-1. 단위 일관성 회복 (가장 큰 개선)
**Before**:
- 사이드바: "의역 10" (sentence count)
- 그룹 헤더: "의역 1" (card count)
- 같은 카테고리에 다른 숫자 — 사용자 혼란

**After**:
- 사이드바: "의역 5"
- 그룹 헤더: "의역 5"
- 모든 카운트가 sentence count 단일 단위 — 직관적

→ Turnitin·Copyleaks 의 표준 ("matched sentences" 단일 단위) 부합.

### 3-2. 모달·배너 단위 병기
- 일괄 제외 모달 "의역 1건 (5문장) 일괄 처리" — 클릭 단위(카드)와 점수 영향(문장) 동시 인지
- 배너 "수동 제외 1건 (5문장) 반영" — 동일 패턴

### 3-3. 약한 유사 ⓧ 제거 — 직관 회복
- 점수 미반영 카테고리에 점수 영향 액션 노출 = 사용자 혼란
- ⓧ 자체 미노출 → "약한 유사는 참고용" 시각 신호 강화

### 3-4. 점수 정합성 강화 (Phase 4)
- 화면 점수와 백엔드 점수 산식 일치
- cluster overlap 시 분모 부정확 제거 → 일반 사용자엔 영향 미미, 복잡 매칭 케이스 신뢰성 ↑

---

## 4. 검증 결과

### 4-1. 자동 회귀
| 검사 | 결과 |
|------|------|
| `tests/sim_label_consistency.sh` (E1·E2·C1·C2·T1) | ✅ PASS |
| `tests/sim_score_v3_unit_test.py` (골든셋 5건) | ✅ 5/5 PASS |

### 4-2. 브라우저 시나리오 (실측 데이터)
| 검증 항목 | Before | After |
|----------|--------|-------|
| 그룹 헤더 count (단일 카드 cluster span 5) | "1" (card count) | **"5"** (sentence count) ✓ |
| 헤더 title | "1" 만 표시 | **"1건 매칭 / 5문장"** ✓ |
| 일괄 버튼 title | "이 그룹 1건 일괄 제외" | **"이 그룹 1건(5문장) 일괄 제외"** ✓ |
| 일괄 모달 preview | "의역 1건 일괄 처리" | **"의역 1건 (5문장) 일괄 처리"** ✓ |
| 배너 (제외 후) | "수동 제외 1건 반영" | **"수동 제외 1건 (5문장) 반영"** ✓ |
| 사이드바 indicator (의역) | 5 | 5 (변동 없음, 이미 sentence count) |
| 점수 (제외 후) | 0% (분모 max(0,1)=1) | 0% (변동 없음) |
| 5단계 verdict (0%) | "매칭 없음" Blue | "매칭 없음" Blue ✓ |

### 4-3. 시각 캡처
- `phase4-7-final.png` — 모든 카운트가 sentence count 단위, 배너 "수동 제외 1건 (5문장) 반영"

---

## 5. 사용자 관점 피드백

### 5-1. 표준 부합
**Turnitin / Copyleaks 비교**:
- ✅ 단위: "matched sentences" 단일 단위 (이전: 카드 vs 문장 혼재)
- ✅ 점수 미반영 카테고리에 제외 액션 미노출 (이전: 약한 유사 ⓧ 노출 — 안티패턴)
- ✅ 분모 = unique sentence coverage (이전: 카드 span 단순 합산 — 부정확)

→ 표절 검출 도구 표준 산식·UX 패턴에 정렬.

### 5-2. 사용자 페인 해소 시나리오
**Phase 5+6 결합 효과**:
- "사이드바 의역 10" + "그룹 헤더 의역 1" 인지 부조화 해소 (단위 일관)
- 약한 유사 ⓧ 클릭 후 점수 상승 역설 사라짐 (버튼 미노출)

### 5-3. 잠재 우려 (낮음)
- Phase 4 분모 변경으로 cluster overlap 문서에서 점수 약간 변동 가능. 다만 일반 문서 영향 미미. 변동 방향은 "분모 정확도 향상" 이므로 수용 가능.

---

## 6. 웹디자인 전문가 관점 피드백

### 6-1. 정보 위계
- 점수 카드 = primary (큰 글씨, 단일 점수)
- 7지표 카드 = 카테고리별 sentence count 일관
- 그룹 헤더 = 같은 sentence count 단위
- 모달·배너 = "N건 (M문장)" 병기 — 클릭 단위와 점수 단위 분리

→ 모든 시각 위계가 단일 단위 (sentence) 로 정합.

### 6-2. 인터랙션 명확성
- 약한 유사 카드 — ⓧ 미노출, 호버 시 카드 자체 클릭 가능 (본문 점프)
- 그룹 헤더 [⊘ 일괄 제외] — 4개 카테고리 (동일·거의 동일·의역) 만 노출. 약한 유사 헤더는 카운트만 표시
- 모달 preview·OK 라벨 — 적용 결과 명확 ("1건 제외" Primary)

### 6-3. 접근성
- title 어트리뷰트로 카드 수·문장 수 둘 다 hover 노출 — 화면 클릭과 점수 영향 분리 인지
- 단위 라벨 ("문장") 한국어 명시 — 색상 의존 없이 의미 전달

### 6-4. 개선 제안 (수용은 후속 판단)
1. 약한 유사 카드에 hover 시 "참고용 — 점수 미반영" 툴팁 추가 검토 (현재는 ⓧ 미노출만으로도 충분)
2. cluster overlap 매칭 시각 표시 — 본문 하이라이트가 겹치는 경우 시각 단서 추가 검토 (현재는 sentence index set 으로 1번 카운트하지만 시각은 그대로 — UX 일관성 측면 검토 가치)

---

## 7. 발견된 부수 관찰 (현 범위 외)

| # | 항목 | 비고 |
|---|------|------|
| O-1 | `simRecomputeFromSettings` 의 `sectionCounts` 와 첫 렌더 `sentCount` 모두 sentence span 합산으로 통일됨 | Phase 5 완성도 검증 시점에 발견되어 함께 처리 |
| O-2 | 약한 유사 카드의 본문 하이라이트는 그대로 유지 (시각 가시성) | 사용자가 "약한 유사 = 참고" 인식 시 본문 위치 점프는 여전히 유용 |
| O-3 | 백엔드 `_compute_summary` 의 sentence index set 패턴과 프론트 `computeScore` 가 이제 동일 동선 | 일관성 검증 가치 — 향후 추가 골든셋 (cluster overlap 케이스) 가능 |

---

## 8. 한 줄 결론

**PASS.** Plan-50 Phase 4~7 완료. 자동 회귀·골든셋·Playwright 시나리오 모두 통과.

- **Phase 4**: 분모 계산이 백엔드와 일관 (unique sentence coverage)
- **Phase 5**: 사이드바·헤더·배너·모달 모든 카운트가 sentence count 단일 단위
- **Phase 6**: 약한 유사 ⓧ 제거로 점수 상승 역설 안티패턴 해소
- **Phase 7**: NaN 방어 + 100% 초과 디버그 로그 + 단위 병기

업계 표준 (Turnitin·Copyleaks) 산식·UX 패턴에 정렬. Plan-50 전체 (Phase 0~7) 완료 — 유사도 점수 정합 부채 해소 완성.
