# Plan-58 — Verify 5단계 신호등 매칭 사각지대 수정 (verdict band dead-zone hotfix) — v1

> 작성일: 2026-05-20
> 대상 시스템: Verify (`compare.html`)
> 변경 범위: 프론트엔드 verdict 밴드 매칭 로직 2곳 + 공통 헬퍼 + JS 단위 테스트 + grep 가드
> 상태: 계획 단계 (사용자 승인 후 진행)

---

## 진행 현황 요약

| Phase | 내용 | 예상 공수 | 상태 |
|-------|------|---------|------|
| Phase 0 | 가설 검증 + 영향성 분석 (완료) | — | ✅ |
| Phase 1 | 공통 헬퍼 `matchVerdictBand()` 추출 + 두 사용처 교체 | 0.25일 | ⬜ 대기 |
| Phase 2 | JS 단위 테스트 (18 케이스) — `tests/sim_verdict_band_test.js` | 0.25일 | ⬜ 대기 |
| Phase 3 | `tests/sim_label_consistency.sh` 안티패턴 가드 추가 | 0.1일 | ⬜ 대기 |
| Phase 4 | 브라우저 E2E 검증 — 사각지대 점수 4구간 시각 확인 | 0.25일 | ⬜ 대기 |
| Phase 5 | 피드백 보고서 + 잔존 이슈 정리 | 0.15일 | ⬜ 대기 |
| **합계** | — | **1.0일** | **0/5** |

---

## 배경

### 사용자 보고
유사도 결과 **0.9%** 인데 verdict 라벨이 **"위험"** 으로 표시됨. 다른 문서들은 1~3% 수준에서 "양호"로 정상 표시.

### 원인 (단위 테스트로 검증 완료)
`compare.html:2486` 의 verdict 밴드 매칭 로직이 정수 경계 사이의 소수점 점수를 모두 마지막 밴드(red/위험)로 폴백시킴.

```js
// 깨진 패턴
var match = bands.find(b => scoreVal >= b.range_min && scoreVal <= b.range_max)
            || bands[bands.length - 1];   // ← 매칭 실패 시 red 폴백
```

SSOT `data/help/similarity-help.json` 의 `verdict_bands` 는 정수 범위 (`[0,0], [1,24], [25,49], [50,74], [75,100]`) 인데 점수는 소수점 1자리. 결과적으로 다음 4개 사각지대 발생:
- `0 < score < 1` (사용자 케이스)
- `24 < score < 25`
- `49 < score < 50`
- `74 < score < 75`

**검증** (Node.js 로 로직 그대로 재현 — 18 입력):

| score | 현재 | 백엔드 `_compute_verdict_band` | 일치 |
|---|---|---|---|
| 0.9 | red | green | ✗ |
| 24.5 | red | green | ✗ |
| 49.9 | red | yellow | ✗ |
| 74.9 | red | orange | ✗ |
| 1, 25, 50, 75, … | (정확) | (정확) | ✓ |

백엔드는 표준 패턴(`<` 캐스케이드)으로 정확. **프론트엔드만 깨짐 → 백/프 verdict 충돌**.

---

## 변경 범위

### 수정 대상 (2곳)

| 위치 | 역할 |
|---|---|
| `compare.html:2486` | 메인 UI verdict 라벨 (`.sim-verdict`) — 사용자가 보는 텍스트·색 |
| `compare.html:5285` | 보고서 payload — Excel/PDF 출력의 `verdict` / `verdict_label` |

두 곳 모두 동일한 안티패턴 사용 중 → **공통 헬퍼로 추출**하여 재발 방지.

### 새 헬퍼 (compare.html `<script>` 상단, `verdictBands5` 디폴트 선언 근처)

```js
// SSOT verdict_bands 매칭 — 표준 패턴 (하한 inclusive, 상한 = 다음 밴드 range_min, exclusive)
// 백엔드 _compute_verdict_band() 와 정합. 정수 경계의 소수점 점수 사각지대 없음.
function matchVerdictBand(score, bands) {
    if (!Array.isArray(bands) || !bands.length) return null;
    if (score <= bands[0].range_min) return bands[0];          // blue (≤0)
    for (var i = 1; i < bands.length; i++) {
        var next = bands[i + 1];
        if (!next || score < next.range_min) return bands[i];  // 다음 밴드 시작 전까지
    }
    return bands[bands.length - 1];
}
```

### 변경 부분 (요약)

**A. `compare.html:2484-2490`** — `bands.find(...) || bands[last]` 제거, `matchVerdictBand(scoreVal, bands)` 호출.
**B. `compare.html:5281-5289`** — for-loop 와 폴백 제거, `matchVerdictBand(payload.score, simV3Bands)` 호출.

---

## 영향성 분석 (사전 조사 결과)

### 영향 없음 (legend·표시 전용)
- `compare.html:1285, 5366` — fallback 밴드 배열 (도움말 모달용, 매칭 안 함)
- `compare.html:1313, 5576, 5688` — `range_min~range_max` 표시 문자열
- `backend/services/export_service.py:381, 424` — Excel "검사 기준" 시트 legend
- `backend/services/similarity_engine.py:_compute_verdict_band()` — 이미 표준 패턴
- `summary.verdict` 색 기반 점수 카드 색 (`compare.html:2755`) — 백엔드 값 사용, 정확

### 관리자 설정 영향
- `js/admin-settings.js` 의 `sim_verdict_low` / `sim_verdict_high` — **3단계 호환용 임계** (디폴트 30/60). `compare.html:2493-2495` fallback 분기에서만 사용. 본 수정은 SSOT verdict_bands 경로만 손대므로 **무관**.
- `VERIFY_SIMILARITY_VERDICT_BANDS = [0, 25, 50, 75]` — 관리자 GUI 미노출. 본 수정과 무관.

### 사용자 영향 (라벨 변화)

| 점수 | 수정 전 | 수정 후 | 방향 |
|---|---|---|---|
| 0.1 ~ 0.9 | 위험 | 양호 | ✓ 정상화 |
| 24.1 ~ 24.9 | 위험 | 양호 | ✓ 정상화 |
| 49.1 ~ 49.9 | 위험 | 검토 필요 | ✓ 정상화 |
| 74.1 ~ 74.9 | 위험 | 상당량 매칭 | ✓ 정상화 |
| 정수 (1, 25, 50, 75, …) | 정상 | 동일 | — |

**위험 → 약한 등급 방향뿐**. 반대 방향(양호 → 위험)은 발생하지 않음.

### 데이터/이력
- `data/verify/{user}/_history.json` — 점수 자체는 변동 없음. `verdict` 라벨만 다음 검사부터 정상화. 마이그레이션 불요.
- 이미 발급된 Excel/PDF 보고서 — 영향 없음 (재발급 시에만 적용).

### 백엔드 영향
- 백엔드 코드/응답 포맷 변경 0. 배포 순서 무관.

### 잠재 동반 이슈 (본 PR 비대상)
1. `payload.verdict_legacy` (line 5297) — `verdictBoundHigh=74` 사용, 백엔드 75와 1 off. 별개 정합화 필요.
2. `simRecomputeFromSettings` — 수동 제외/설정 변경 후 `.sim-verdict` 텍스트 비갱신. 별개 결함.
3. `settings_service.py:226-227` 디폴트 (30/60) vs `compare.html:628-629` 디폴트 (25/74) 불일치. simHelp 로드 실패 시에만 노출.

→ 본 PR 은 사용자 보고된 케이스 완전 해결에 집중. 1~3 은 후속 PR (별 plan) 로 처리.

---

## 검증 계획

### Phase 2 — JS 단위 테스트 (`tests/sim_verdict_band_test.js`)
- Plan-45 `sim_phase2_test.js` 형식 차용 (process.stdout.write, assert)
- 18 입력 케이스 — 사각지대 4구간 + 경계값 + 정상값
- 백엔드 `_compute_verdict_band()` 로직과 일치하는지 비교

### Phase 3 — `tests/sim_label_consistency.sh` 안티패턴 가드
```bash
# T2-band-deadzone — verdict_bands 양방향 비교 패턴 금지 (Plan-58)
# 정수 경계의 소수점 점수가 마지막 밴드로 폴백되는 결함 재발 방지.
```
패턴: `bands\.find.*range_min.*range_max` 와 `>= .*range_min.*<= .*range_max` grep 금지.

### Phase 4 — 브라우저 E2E (Playwright)
1. 개발 PC Docker 컨테이너 정상 동작 확인 (이미 완료)
2. compare.html 로드 → DevTools 콘솔에서 `scoreVal` 강제 주입 시뮬레이션
   - `matchVerdictBand(0.9, simHelp.verdict_bands)` → green 반환
   - `matchVerdictBand(24.5, ...)` → green
   - `matchVerdictBand(49.9, ...)` → yellow
   - `matchVerdictBand(74.9, ...)` → orange
3. 실제 검사 결과가 있다면 `data/verify/testbot/_history.json` 에 사각지대 점수가 있는지 확인. 있으면 재렌더로 라벨 변화 확인.
4. 회귀 — 정상 점수 (1.0, 12.5, 25.0, 75.0 등) 에서 라벨 변동 없음 확인.

### Phase 5 — 피드백 보고서 (`workbench/reports/plan-58-feedback.md`)
- 전문가 관점: 코드 품질, 회귀 위험, 잔존 이슈 우선순위
- 사용자 관점: 사용자 보고된 0.9% 케이스 시뮬레이션 결과, 다른 사각지대 케이스
- 동반 발견된 별개 결함 3건 backlog 등록 권고

---

## 롤백 계획

단일 commit 으로 작업. 회귀 발견 시 `git revert <commit>` 1회로 즉시 원복. 백엔드 변경 0 + 데이터 마이그레이션 0 → 롤백 안전.

---

## 작업 원칙 준수
- 의견 먼저, 구현은 승인 후 — **본 계획서가 그 의견**. 사용자 승인 후 Phase 1 진입.
- 기존 코드 패턴 재사용 — `sim_phase2_test.js` 형식, `sim_label_consistency.sh` 가드 형식
- 과도한 엔지니어링 금지 — fallback 분기 (line 2493-2495) 는 이미 사각지대 없음 → 손대지 않음
- 커밋은 요청 시에만 — 사용자 명시 요청 후에만 commit
