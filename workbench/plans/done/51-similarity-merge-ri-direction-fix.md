# Plan-51 — 유사도 매칭 병합 ri 단방향 검사 결함 수정

> 작성일: 2026-04-30
> 완료일: 2026-04-30
> 변경 범위: `backend/services/similarity_engine.py` (1줄), `compare.html` (1줄), 신규 단위 테스트 1건
> 위험도: **낮음** — 변경 영향은 "역행 병합 케이스" 에 국한, 정상 작동 케이스 무영향
> 검증: 단위 테스트 fail-then-pass + API E2E + 자동 회귀

---

## 진행 현황 요약

| Phase | 내용 | 상태 |
|-------|------|------|
| Phase 1 | `_merge_adjacent` 단위 테스트 신규 작성 (7 케이스) + 수정 전 실행으로 결함 객관 증거 확보 | ✅ 완료 |
| Phase 2 | 백엔드 1줄 수정 (similarity_engine.py:794) + 단위 테스트 7/7 PASS | ✅ 완료 |
| Phase 3 | 프론트 방어선 1줄 추가 (compare.html:2773) | ✅ 완료 |
| Phase 4 | API E2E 검증 + 시각 캡처 + 자동 회귀 모두 PASS | ✅ 완료 |
| Phase 5 | 피드백 보고서 작성 + 계획서 done- 처리 | ✅ 완료 |

---

## 0. Context

### 사용자 페인
유사도 검사 결과 패널에서 카드 클릭 시 좌(A) 패널은 매칭 위치로 스크롤되지만 **우(B) 패널은 일부 카드에서 스크롤되지 않음**. ref_text 를 우 패널 Ctrl+F 로 검색하면 텍스트는 존재하지만 **마킹 클래스 미부착**. 발생 카테고리는 **"의역" 집중**.

### 결함 메커니즘

`backend/services/similarity_engine.py:_merge_adjacent` 의 ri 인접 검사가 단방향:
```python
# 결함 (line 794)
and m["ref_idx"] - prev.get("ref_idx_end", prev["ref_idx"]) <= 2
```

`all_matches` 는 ti 정렬, ri 무관. ti 인접 + 같은 type 인 두 매칭의 ri 가 역방향일 때 (예: prev.ri_end=50, m.ri=10) 음수도 통과 → 잘못 병합 → `ri_end < ri_start` 인 망가진 범위 → 프론트 마킹 루프 0회 실행.

#### 의역 집중 발현 이유
- L1 fingerprint (identical, near_copy) — 텍스트 동일성, ti↔ri 위치 상관 강함
- **L3 semantic (paraphrase, translation) — 의미 기반, 위치 무관 페어링** → ri 역행 흔함

---

## 1. Phase 1 — 단위 테스트 신규 작성

### 신규 파일
`tests/sim_merge_adjacent_unit_test.py` — 7 케이스

| Case | 입력 | 기대 | 의도 |
|------|------|------|------|
| A | [ti=5,ri=10], [ti=6,ri=11] | 병합 1건 | Forward 정상 (회귀 방지) |
| B | [ti=5,ri=10], [ti=7,ri=12] | 병합 1건 | Forward 경계 gap=2 (회귀 방지) |
| C | [ti=5,ri=10], [ti=8,ri=13] | 미병합 2건 | ti gap=3 미병합 (회귀 방지) |
| **D** ★ | **[ti=5,ri=50], [ti=6,ri=10]** | **미병합 2건** | **ri 큰 역행** |
| **E** ★ | **[ti=5,ri=10], [ti=6,ri=9]** | **미병합 2건** | **ri 작은 역행** |
| F | [ti=5,ri=10,paraphrase], [ti=6,ri=11,translation] | 미병합 2건 | Type 차이 (회귀 방지) |
| G | [ti=5,ri=10], [ti=6,ri=11], [ti=7,ri=12] | 병합 1건 [ti:5-7, ri:10-12] | Forward 3건 연쇄 (회귀 방지) |

### 수정 전 실행 결과 (결함 객관 증거)
- Case D: `merged[0].ri=50, ri_end=10` ← **`ri_end < ri_start` 패턴 직접 관찰**
- Case E: `merged[0].ri=10, ri_end=9`
- A, B, C, F, G PASS (forward 동작 정상)

---

## 2. Phase 2 — 백엔드 1줄 수정

### 변경
`backend/services/similarity_engine.py:794`
```python
# Before (단방향)
and m["ref_idx"] - prev.get("ref_idx_end", prev["ref_idx"]) <= 2)

# After (양방향 forward 강제)
and 0 <= m["ref_idx"] - prev.get("ref_idx_end", prev["ref_idx"]) <= 2)
```

### 영향 표

| 케이스 (prev.ri_end = 50) | 수정 전 | 수정 후 |
|--------------------------|---------|---------|
| m.ri = 51 (gap=1) | 병합 | 병합 (동일) |
| m.ri = 52 (gap=2) | 병합 | 병합 (동일) |
| m.ri = 53 (gap=3) | 미병합 | 미병합 (동일) |
| m.ri = 49 (gap=-1) | **병합 (broken)** | 미병합 (개선) |
| m.ri = 30 (gap=-20) | **병합 (broken)** | 미병합 (개선) |

### 검증
- `python tests/sim_merge_adjacent_unit_test.py` → **7/7 PASS**
- `python tests/sim_score_v3_unit_test.py` → **5/5 PASS** (점수 영향 0)
- `bash tests/sim_label_consistency.sh` → **PASS**

---

## 3. Phase 3 — 프론트 방어선 (1줄)

### 변경
`compare.html:2773`
```js
// Before
var endR = m.ref_idx_end !== undefined ? m.ref_idx_end : startR;

// After (역행 방어)
var endR = (m.ref_idx_end !== undefined && m.ref_idx_end >= startR) ? m.ref_idx_end : startR;
```

### 효과
- 백엔드 정상 동작 시: 기존과 100% 동일
- 백엔드 회귀 시: startR 1점은 최소 마킹 → silent 페인 방지

---

## 4. Phase 4 — API E2E + 자동 회귀

### API 시나리오 — 4 문단 순서 완전 역전
- target ti=0~3, reference ri=0~3 완전 역순
- 기대: 매칭 4건 분리 + 양 패널 정확 마킹

### 결과
- matches_count: 4 (정확 분리)
- inverted_count: 0 (역행 매칭 0)
- similarity_score: 100 (정상 채점)
- per_match 모두 aHits=1, bHits=1 (양 패널 누락 0)
- missing_A_count: 0, missing_B_count: 0

### 자동 회귀
- 신규 단위 테스트 7/7 PASS
- 기존 점수 회귀 5/5 PASS
- SSOT 라벨 회귀 PASS

---

## 5. Phase 5 — 산출물

| 파일 | 내용 |
|------|------|
| `backend/services/similarity_engine.py` | line 794 ri 조건 양방향화 (1줄) |
| `compare.html` | line 2773 endR 가드 (1줄) |
| `tests/sim_merge_adjacent_unit_test.py` | 신규 단위 테스트 7 케이스 |
| `workbench/reports/plan-51-feedback.md` | 검증 보고서 |
| `workbench/plans/done-51-...md` | 본 계획서 (완료) |

---

## 6. 위험 분석 — 사용자 우려 직접 응답

### 우려: "정상 작동 기능이 안 좋은 방향으로 수정될 가능성"

| 항목 | 변동 |
|------|------|
| Forward 병합 (정상 케이스) | **0** — 동일 조건 통과 |
| 점수 (similarity_score) | **0** — Plan-50 sentence index set 기반 |
| 좌(A) 패널 마킹·네비 | **0** — ti 기반 영향 없음 |
| 카드 개수 (의역) | 약간 증가 — 잘못 병합 → 분리, 정보 손실 0 |
| 카드 ref_text 미리보기 | **개선** — jumbled 제거 |
| 우(B) 패널 마킹 | **개선** — 누락 지점 마킹 부여 |
| B 패널 네비게이션 | **개선** — 사용자 페인 직접 해소 |
| 수동 제외 UX | 미세 손실 — 분리된 카드 각각 제외 (1→2~3 클릭) |
| 그룹 일괄 제외 | **0** — 카테고리 단위 |
| 보고서 (HTML/PDF/Excel) | 카드 행 수만 증가 |
| 다른 카테고리 (동일/거의/약한) | 거의 **0** — L1 기반은 ri 역행 자체가 드뭄 |

### 안전망
1. **수정 전 골든 캡처** — 정상 forward 케이스 변동 0 객관 증거 (Phase 1 단위 테스트)
2. **프론트 방어선** — 백엔드 회귀해도 silent 페인 방지
3. **롤백 용이** — 1줄 수정, git revert 1회로 즉시 복원

---

## 7. 한 줄 결론

**PASS.** Plan-51 완료 — `_merge_adjacent` ri 인접 검사 단방향 결함 수정 (1줄) + 프론트 방어선 (1줄) + 회귀 단위 테스트 7건. 의역 카테고리 B 패널 마킹·네비 미동기 페인 직접 해소. 점수·라벨·기존 카테고리 회귀 0. 단위 테스트 fail-then-pass 로 결함 객관 증거 확보 + 수정 효과 검증.
