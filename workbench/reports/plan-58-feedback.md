# Plan-58 피드백 보고서 — Verify 5단계 신호등 매칭 사각지대 수정

> 작성일: 2026-05-20
> 대상: `compare.html` verdict 매칭 로직
> 결과: ✅ 사각지대 4 구간 모두 정상화 · 백엔드 정합 100%

---

## 1. 작업 요약

### 변경 파일
| 파일 | 변경 | 추가/삭제 |
|---|---|---|
| `compare.html` | `matchVerdictBand()` 헬퍼 추가 (line 2417~) + 두 사용처 교체 (line 2486 / 5285) | +14 / -10 |
| `tests/sim_verdict_band_test.js` | 신규 — 37 케이스 단위 테스트 | +121 |
| `tests/sim_label_consistency.sh` | T2-band-deadzone 안티패턴 가드 + exclude 1건 | +28 |
| `workbench/plans/58-verify-verdict-band-deadzone-fix.md` | 신규 계획서 | +109 |
| `workbench/reports/plan-58-feedback.md` | 본 보고서 | (자체) |

### 적용된 헬퍼 (`compare.html:2421~`)
```js
function matchVerdictBand(score, bands) {
    if (!Array.isArray(bands) || !bands.length) return null;
    if (score <= bands[0].range_min) return bands[0];
    for (var i = 1; i < bands.length; i++) {
        var next = bands[i + 1];
        if (!next || score < next.range_min) return bands[i];
    }
    return bands[bands.length - 1];
}
```
백엔드 `similarity_engine._compute_verdict_band()` 의 `<` 캐스케이드 패턴을 SSOT JSON 의 `range_min` 으로 동적 일반화한 형태.

---

## 2. 검증 결과

### 2.1 단위 테스트 (`tests/sim_verdict_band_test.js`)
```
=== Plan-58 단위 테스트 — matchVerdictBand ===
[사각지대 점수]                          6/6 OK
[정수 경계값 — 회귀 영역]                6/6 OK
[정상 점수 시나리오]                     3/3 OK
[극단값·방어 로직]                       3/3 OK
[백엔드 _compute_verdict_band 정합 검증]  19/19 OK
=== 결과: 37 pass, 0 fail ===
```

### 2.2 그룹별 결과 표

| 그룹 | 입력 | 수정 전 | 수정 후 | 백엔드 | 평가 |
|---|---|---|---|---|---|
| 사각지대 (사용자 보고) | 0.4 | red | green | green | ✅ |
| 사각지대 (사용자 보고) | **0.9** | **red** | **green** | green | ✅ |
| 사각지대 | 24.5 | red | green | green | ✅ |
| 사각지대 | 24.9 | red | green | green | ✅ |
| 사각지대 | 49.9 | red | yellow | yellow | ✅ |
| 사각지대 | 74.9 | red | orange | orange | ✅ |
| 경계값 | 0 | blue | blue | blue | ✅ |
| 경계값 | 1, 25, 50, 75 | (정확) | (동일) | (동일) | ✅ 회귀 없음 |
| 정상 | 1.7, 12.5, 99.9 | (정확) | (동일) | (동일) | ✅ 회귀 없음 |

### 2.3 일관성 가드 (`tests/sim_label_consistency.sh`)
```
[T2-band-deadzone] verdict_bands 양방향 비교 안티패턴 검사...
=================================
PASS: 모든 라벨·공식 일관성 검증 통과
```
신규 T2 가드가 미래의 안티패턴 재유입을 차단 (`bands.find(...range_min...range_max)` 및 `>= b.range_min ... <= b.range_max` 두 패턴).

### 2.4 브라우저 E2E (Playwright, Docker 컨테이너)
- 로그인 (testbot) → `compare.html` 로드 정상
- 페이지 스크립트 정적 검사 결과:
  - `function matchVerdictBand(` 존재: **true**
  - `matchVerdictBand(scoreVal, bands)` 사용: **true**
  - `matchVerdictBand(payload.score, simV3Bands)` 사용: **true**
  - 옛 안티패턴 `bands.find(... range_min ... range_max)`: **false** (제거 확인)
  - 옛 안티패턴 `payload.score >= _b.range_min`: **false** (제거 확인)
- `/api/help/similarity` 응답의 실제 `verdict_bands` (5개) 로 14 입력 재검증 — 100% 통과
- 콘솔 에러: 본 변경 관련 0건

---

## 3. 전문가 관점 평가

### 3.1 코드 품질
- ✅ 중복 제거: 같은 안티패턴이 2곳에 있던 것을 **단일 헬퍼로 추출** → 향후 표시·매칭 정책 변경 시 단일 지점만 수정
- ✅ 안전망 제거: 매칭 실패 시 `bands[last]` (= red) 로 떨어지던 위험 폴백 삭제. 모든 입력에서 결정론적 결과
- ✅ 표준 패턴 채택: NumPy `digitize` · Pandas `cut` · D3 `scaleThreshold` 와 동일한 "하한 inclusive · 상한 exclusive" 캐스케이드
- ✅ 백엔드/프론트 동치성: 백엔드 `_compute_verdict_band()` 와 19/19 일치 — 같은 응답 안에서 verdict 충돌 가능성 차단

### 3.2 회귀 위험
- 점수 공간 약 **96%** (정수 경계 외 모든 영역) 에서 결과 무변동 — 변경 면적이 좁고 의도된 버그 수정에 한정
- 백엔드 0 영향 → 배포 순서 무관 · 마이그레이션 0
- 이미 발급된 보고서·`_history.json` 영향 0 (다음 검사부터 정상화)

### 3.3 미해결 / 후속 PR 권고

| ID | 항목 | 영향 | 우선순위 |
|---|---|---|---|
| F-58-1 | `payload.verdict_legacy` (line 5300) 가 `verdictBoundHigh=74` 사용 — 백엔드 75 와 1 off | 보고서 호환 필드 (실사용 빈도 거의 0) | 낮음 |
| F-58-2 | `simRecomputeFromSettings` 가 수동 제외·설정 변경 후 `.sim-verdict` 텍스트 비갱신 | 사용자가 점수 바꿔도 라벨 stale | **중간** |
| F-58-3 | `settings_service.py:226-227` 디폴트 (30/60) vs `compare.html:628-629` 디폴트 (25/74) 불일치 | simHelp 로드 실패 시에만 노출, 실사용 거의 무영향 | 낮음 |

→ 3건 모두 본 PR 범위와 분리. F-58-2 만 사용자 영향이 있을 수 있어 후속 Plan-59 로 검토 권장.

### 3.4 자동 검증 강화
- `sim_label_consistency.sh` 에 T2 가드 추가로 **재발 방지 기계화 완료**
- pre-commit hook 또는 CI step 등록 권장 (CLAUDE.md 가이드와 정합)

---

## 4. 사용자 관점 평가

### 4.1 사용자 보고 케이스 시뮬레이션
| 사용자 보고 | 결과 |
|---|---|
| "0.9% 인데 위험으로 표시" | **양호 (녹색) 로 정상화 확인** — `matchVerdictBand(0.9, BANDS).label === '양호'` |
| "다른 문서는 1~3% 면 양호" | 변화 없음 — 정수 경계 외 영역은 그대로 |

### 4.2 사용자에게 보일 변화
- 사용자가 인식하기에 **"잘못된 위험" 이 사라짐** — 신뢰도 회복
- 정상 작동하던 점수(1, 25, 50, 75 등) 의 라벨은 그대로 유지
- 라벨 방향은 항상 "위험 → 더 약한 등급" — 양호가 위험으로 바뀌는 역방향 변화는 없음 (불안 유발 0)

### 4.3 안내 필요성
- 이미 발급된 보고서는 영향 없음 — 별도 재발급 통지 불요
- 같은 문서를 재검사하면 일부 케이스에서 라벨이 달라질 수 있으나 **점수 자체는 그대로** — "백엔드는 원래 정확했고 화면 표시만 보정됐다" 라는 한 줄 안내로 충분
- 사용자 시나리오: 새 검사 → 자동으로 정상 라벨 노출 (재학습·재설정 0)

### 4.4 잠재 사용자 페인 (F-58-2 관점)
사용자가 매칭 카드를 수동 제외하여 점수를 0.9% 로 낮춘 직후 verdict 라벨이 위험 그대로 남는 결함이 본 수정 후에도 잔존. 이 경우:
- 점수 카드: "0.9%" (정상 갱신)
- verdict 라벨: 여전히 초기 렌더 값 (예: "위험")

→ 본 사용자 보고 (검사 직후 0.9% = 위험) 는 본 PR 로 완전 해결. 다만 수동 제외 후 라벨 비갱신 시나리오는 F-58-2 후속 작업 필요.

---

## 5. 결론

### 사용자 보고 해결 여부
**완전 해결**. 0.9% / 24.5% / 49.9% / 74.9% 등 사각지대 4구간 모두 백엔드 정합 라벨로 정상화 확인 (단위 37건 + E2E 정적 + SSOT 실데이터 14건).

### 회귀 위험
극히 낮음. 백엔드 변경 0 · 데이터 마이그레이션 0 · 변경 면적 4 구간 · 단일 commit revert 로 즉시 원복 가능.

### 다음 작업 제안
1. (선택) F-58-2 — `simRecomputeFromSettings` 의 verdict 라벨 재갱신 추가 (체감 효과 중간)
2. (선택) F-58-3 — settings_service 디폴트 25/74 정합화 (정합성 위생)
3. (필수) `sim_label_consistency.sh` 를 pre-commit/CI 에 등록 (T2 가드 자동화)
