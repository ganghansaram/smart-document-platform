# Plan-59 피드백 보고서 — verdict 라벨 재갱신 + verdict_legacy 임계 정합

> 작성일: 2026-05-20
> 대상: `compare.html` verdict 재계산 흐름
> 결과: ✅ F-58-2 사용자 페인 해결 · F-58-1 백엔드 임계 정합 · 첫 렌더/재계산 단일 로직 통일

---

## 1. 작업 요약

### 변경 파일

| 파일 | 변경 |
|---|---|
| `compare.html` | `resolveVerdict()` 헬퍼 추가 (line 2429~) + `simShowResults` 첫 렌더 호출로 교체 + `simRecomputeFromSettings` 내 DOM 갱신 추가 + `verdict_legacy` 5→3 매핑 |
| `tests/sim_resolve_verdict_test.js` (신규) | 25 케이스 단위 테스트 (resolveVerdict + verdict_legacy) |
| `workbench/plans/59-verify-verdict-recompute-and-legacy-cleanup.md` (신규) | 계획서 |
| `workbench/reports/plan-59-feedback.md` (신규) | 본 보고서 |

### 핵심 변경 코드

**`resolveVerdict()` 헬퍼 (단일 진실 공급원)**:
```js
function resolveVerdict(score) {
    var bands = (simHelp && Array.isArray(simHelp.verdict_bands)) ? simHelp.verdict_bands : null;
    var match = bands ? matchVerdictBand(score, bands) : null;
    if (match) {
        var classMap = { blue: 'sim-verdict-blue', green: 'sim-verdict-good', yellow: 'sim-verdict-yellow', orange: 'sim-verdict-orange', red: 'sim-verdict-warning' };
        return { label: match.label, cls: classMap[match.color] || 'sim-verdict-moderate', tip: ... };
    }
    // fallback (25/74 정합)
    if (score >= verdictBoundHigh) return { label: '위험', ... };
    ...
}
```

**`simRecomputeFromSettings` DOM 갱신 (F-58-2)**:
```js
var verdictEl = document.querySelector('.sim-verdict');
if (verdictEl) {
    var v = resolveVerdict(score);
    // classList 교체 + tooltip-icon 보존하면서 라벨 갱신
    ...
}
```

**`verdict_legacy` 5→3 매핑 (F-58-1)**:
```js
var legacyMap = { blue: '양호', green: '양호', yellow: '검토 필요', orange: '검토 필요', red: '위험' };
payload.verdict_legacy = matchBand ? legacyMap[matchBand.color] : (fallback);
```

---

## 2. 검증 결과

### 2.1 단위 테스트
```
=== Plan-59 단위 테스트 — resolveVerdict + verdict_legacy ===
[resolveVerdict — SSOT 경로]                  6/6 OK
[resolveVerdict — fallback 경로]              3/3 OK
[라벨 + 색 + 툴팁 통합 검증]                   6/6 OK
[verdict_legacy 5→3 매핑]                     7/7 OK
[verdict_legacy fallback 경로]                 3/3 OK
=== 결과: 25 pass, 0 fail ===
```

### 2.2 회귀 검증 (Plan-58)
```
=== Plan-58 단위 테스트 — matchVerdictBand ===
=== 결과: 37 pass, 0 fail ===
```
이전 작업 회귀 없음.

### 2.3 일관성 가드
```
[T2-band-deadzone] verdict_bands 양방향 비교 안티패턴 검사...
=================================
PASS: 모든 라벨·공식 일관성 검증 통과
```

### 2.4 브라우저 정적 검증 (Playwright)
- `resolveVerdict` 정의: ✅
- `matchVerdictBand` 정의: ✅
- `simShowResults` 가 `resolveVerdict(scoreVal)` 사용: ✅
- `simRecomputeFromSettings` 가 `resolveVerdict(score)` 사용: ✅
- `verdict_legacy` 가 `matchBand.color` 매핑 사용: ✅
- 옛 인라인 verdict 결정 블록 제거: ✅
- 옛 verdict_legacy 직접 분기 제거: ✅
- 콘솔 에러: 0건

---

## 3. 전문가 관점 평가

### 3.1 코드 품질

| 항목 | 평가 |
|---|---|
| 단일 책임 | ✅ verdict 결정 로직 1곳 (`resolveVerdict`) — 첫 렌더·재계산·보고서 paymentload 모두 호출 |
| 일관성 | ✅ 백엔드 `_compute_verdict_band` 와 라벨 그룹화 정합 (5→3 매핑이 시맨틱 합리) |
| 회귀 면적 | 좁음 — DOM 갱신은 가드(`if (verdictEl)`) 후 안전한 클래스 교체·텍스트 교체만 수행 |
| 데이터 무결성 | tooltip-icon 노드 보존 → 클릭/포커스 핸들러 잃지 않음 |

### 3.2 의도된 거동 변화

| 시나리오 | 옛 거동 | 신 거동 |
|---|---|---|
| 첫 검사 결과 표시 | (정상) | (변동 없음) — `simRecomputeFromSettings` 가 직후 호출되지만 같은 점수·같은 라벨 |
| 검사 설정 체크박스 토글로 점수 변동 | 점수만 갱신, 라벨 stale | **점수+라벨 동시 갱신** |
| 매칭 카드 수동 제외로 점수 0.9%까지 하락 | 라벨 "검토 필요" 그대로 (stale) | **"양호"로 정상 갱신** (F-58-2 해결) |
| 점수 74.5%의 `verdict_legacy` | "위험" (옛 `verdictBoundHigh=74` off-by-one) | **"검토 필요"** (백엔드 75 임계 정합) |

### 3.3 회귀 위험

| 위험 | 평가 |
|---|---|
| `.sim-verdict` DOM 미존재 시 | 가드로 silent skip — 안전 |
| `simHelp` 미로드 시 | fallback 분기 정상 동작 (테스트 R7~R9 / L8~L10 검증) |
| `simRecomputeFromSettings` 첫 호출 (line 2750) | 같은 점수→같은 결과 → 시각 변동 0 |
| classList 충돌 | 6개 sim-verdict-* 클래스 모두 제거 후 1개 추가 — race 없음 |
| tooltip 손실 | tooltip-icon 노드 직접 보존 + appendChild — 핸들러 유지 |
| `verdict_legacy` 사용처 | `compare.html:5490`, `export_service.py:105` 모두 `verdict_label` 우선이라 legacy 거의 안 쓰임. 그래도 의미가 정합으로 개선됨 |

### 3.4 잔존 이슈

| ID | 항목 | 본 PR 비포함 사유 |
|---|---|---|
| F-58-3 | `settings_service.py:226-227` 디폴트 (30/60) vs `compare.html:628-629` (25/74) | GUI 라벨(`admin-settings.js:316,319`) + 백엔드 default + 문서 정합이 묶여 있어 표면이 큼 — **별도 Plan-60 권고** |
| `verdictBoundLow/High` 변수 자체 | 본 변수는 `resolveVerdict` fallback 분기 + `verdict_legacy` fallback 에서만 사용 — Plan-50 결정사항 "A 폐기" 미완료 항목 — 별도 정합 작업 |

### 3.5 자동 검증 강화 권고

기존 Plan-58 T2 가드(`sim_label_consistency.sh`)는 verdict 매칭 안티패턴을 차단하지만, **`simRecomputeFromSettings` 가 verdict 라벨도 갱신해야 한다는 약속**은 가드 대상이 아님. 다음 안티패턴 grep 가드 추가 후보:
- `.sim-verdict` 가 `simShowResults` 외부에서 `innerHTML/textContent` 로만 갱신되는 패턴 (positive guard 필요)

다만 false positive 가능성이 커서 본 PR 에서는 미적용. 미래 회귀 시 단위 테스트로 잡는 게 현실적.

---

## 4. 사용자 관점 평가

### 4.1 F-58-2 시나리오 재현 결과

**옛 거동 (Plan-58 적용 직후)**:
```
1. 검사 시작 → 30% "검토 필요(노랑)" 표시
2. 매칭 카드 수동 제외 → 점수 카드: 0.9% (갱신됨)
3. verdict 박스: "검토 필요(노랑)" 그대로 ❌
   사용자 혼란: "점수는 양호 수준인데 왜 검토 필요?"
```

**신 거동 (Plan-59 적용)**:
```
1. 검사 시작 → 30% "검토 필요(노랑)" 표시
2. 매칭 카드 수동 제외 → 점수 카드: 0.9% (갱신됨)
3. verdict 박스: "양호(녹색)" 정상 갱신 ✅
   사용자 인식: 점수와 라벨이 일관 → 신뢰 회복
```

### 4.2 F-58-1 시나리오 (보고서 호환 필드)

- 점수 74.5% 검사 결과의 옛 보고서 호환 라벨: 옛 "위험" → 신 "검토 필요"
- 같은 검사의 백엔드 verdict_label("상당량 매칭") 과도 시맨틱 일관
- 실사용 빈도 거의 0이라 사용자 가시 영향 미미

### 4.3 사용자에게 보일 변화

| 항목 | 변화 |
|---|---|
| 신규 검사 결과 | 변화 없음 (옛 거동에서 첫 렌더는 정상이었음) |
| 검사 설정 토글 후 | **라벨도 점수에 맞춰 즉시 갱신** — 가장 큰 체감 개선 |
| 매칭 카드 수동 제외 후 | **라벨도 점수에 맞춰 즉시 갱신** — F-58-2 해결 |
| 이미 발급된 보고서 | 영향 없음 |
| 같은 검사 재실행 | 점수 동일, 라벨도 동일 (단 74.x% 케이스의 verdict_legacy 만 미세 개선) |

### 4.4 사용자 안내 필요성

- 옛 stale 라벨을 보던 사용자는 새 정상 라벨로 자연스럽게 전환 — 별도 안내 불요
- 점수가 안 바뀌면 라벨도 안 바뀌므로 "갑자기 평가가 바뀌었다" 류 혼란 없음

---

## 5. 결론

### Plan-58 후속 페인 해결 여부
**완전 해결 (F-58-2)** — 수동 제외/설정 토글 후 verdict 라벨이 점수와 함께 정상 갱신됨.
**완전 해결 (F-58-1)** — verdict_legacy 5→3 매핑이 백엔드 임계와 정합.

### 회귀 위험
극히 낮음 — 백엔드 변경 0, DOM 구조 변경 0(요소 갱신만), Plan-58 단위 테스트 37건 회귀 없음 확인.

### 다음 작업 권고

| 우선순위 | 항목 |
|---|---|
| 중간 | **Plan-60** — F-58-3 (settings_service 디폴트 + admin-settings GUI 라벨 5단계 정합화) |
| 낮음 | `verdictBoundLow/High` 변수 자체 폐기 (Plan-50 결정사항 마무리) — `resolveVerdict` 의 fallback 도 SSOT 인라인 fallback bands 로 통일 |
| 낮음 | `tests/sim_label_consistency.sh` 를 pre-commit/CI 에 등록 |

본 PR 은 단독으로 안전하게 적용 가능하며, 사용자가 체감하는 F-58-2 시나리오를 완전히 해결합니다.
