# Plan-50 hotfix1 — 다운로드 회귀 + 부수 정합 정리

> 작성일: 2026-04-30
> 변경 범위: `compare.html` (5곳)
> 검증: 자동 회귀 + Playwright 다운로드 시나리오 (HTML/PDF + 수동 제외 baseline)

---

## 1. 배경

Plan-50 Phase 2 (커밋 `6d482d2`) 적용 시 `var tiers` 변수 선언만 삭제하고 사용처 한 곳을 정리하지 못해 **PDF/HTML 다운로드 silent fail**. 면밀히 점검 중 4건의 추가 회귀·잠재 결함 발견.

---

## 2. 변경 항목

| # | 항목 | 위치 | 변경 |
|---|------|------|------|
| **C-1** | `payload.tiers = tiers;` ReferenceError 복구 | `compare.html:5252` | `summary.tiers \|\| {}` 직접 참조 |
| **W-1** | `simShowResults` 미사용 `var tiers` 제거 | `compare.html:2427` | 라인 삭제 (정리 일관성) |
| **W-2** | `simBaselineScore` 모드 전환 reset 추가 | `compare.html:584` | `simBaselineScore = null;` 1줄 추가 |
| **W-3** | `doExportHtml`/`doExportPdf` try 범위 확장 | `compare.html:5139, 5145` | `buildHtmlReport` 호출을 try 블록 내로 이동 + HTML 도 try/catch |
| **W-5** | 보고서 verdict 라벨 v3 score 기반 재계산 | `compare.html:5247~5260` | 백엔드 `summary.verdict` 직접 사용 → `simHelp.verdict_bands` 매핑 |

---

## 3. 영향 분석 (코드 전문가 관점)

### 3-1. C-1 (Critical)
- silent ReferenceError → 사용자 체감 "응답 없음"
- 1줄 정정으로 복구. 호환성 영향 없음 (백엔드 `tiers` 는 Phase 1 으로 v3 점수 기반)

### 3-2. W-5 (새로 발견)
**Phase 2 의 미해결 잔재** — 보고서 verdict_label/색상이 백엔드 `summary.verdict` 를 직접 사용했음. 이 값은 검사 시점의 점수 기준 → 사용자가 수동 제외해도 갱신 안 됨.

**예시**:
- 검사 직후: 점수 100% → 백엔드 verdict="red" / verdict_label="위험"
- 사용자가 일괄 제외 → 화면 점수 0% (v3 재계산)
- 보고서 다운로드 → 점수 "0%" 인데 라벨 "위험" + 색상 red ← **stale**

**수정**: payload.score (v3, 수동 제외 반영) 를 `simHelp.verdict_bands` 에 매핑하여 재산출.

### 3-3. W-2 stale 방지
- 모드 전환 시 `simLastResult` 만 reset 하던 패턴에 `simBaselineScore` 동시 reset 추가
- 시나리오: 검사 A (의역, baseline=100) → 모드 전환 → 검사 B → 첫 렌더 baseline 갱신 시 정상이지만, 수동 제외 상태 유지하면서 모드 토글 시 stale 위험. 안전망.

### 3-4. W-3 try 범위
- 향후 buildExportPayload·buildSimilarityReportHtml 회귀 시 사용자 토스트로 즉시 가시화
- 동일 silent fail 재발 방지

### 3-5. SSOT 정합
- 모든 변경이 `simHelp.verdict_bands` (data/help/similarity-help.json) SSOT 경유
- `tests/sim_label_consistency.sh` PASS 유지

---

## 4. 검증 결과

### 4-1. 자동 회귀
| 검사 | 결과 |
|------|------|
| `tests/sim_label_consistency.sh` | ✅ PASS |
| `tests/sim_score_v3_unit_test.py` (골든셋 5건) | ✅ 5/5 PASS |

### 4-2. Playwright 시나리오

**시나리오 1 — 검사 후 즉시 HTML 다운로드** (C-1 복구 검증)
| 항목 | 결과 |
|------|------|
| 다운로드 트리거 | ✅ 정상 작동 |
| Blob 생성 | type=`text/html;charset=utf-8`, size=10KB |
| 보고서 score | 100% |
| 보고서 verdict | "위험" / score-band-red |
| 콘솔 에러 | 0건 |

**시나리오 2 — 검사 후 즉시 PDF 다운로드**
| 항목 | 결과 |
|------|------|
| `/api/compare/html-to-pdf` 호출 | ✅ 200 OK |
| Blob 생성 | PDF 1.7, 306KB |
| 다운로드 완료 토스트 | ✅ |

**시나리오 3 — 일괄 제외 후 HTML 다운로드** (W-5 검증)
| 항목 | 결과 |
|------|------|
| 화면 점수 (제외 후) | 0% |
| 화면 verdict 라벨 | "매칭 없음" (Blue) |
| 보고서 score | 0% |
| 보고서 verdict 라벨 | **"매칭 없음"** (이전: "위험" 잔존) ✅ 정합 |
| 보고서 score-band 색상 | **blue** ✅ 정합 |
| baseline note | "수동 제외 전 100% · 수동 제외 1건 반영" ✅ |

→ 모든 표기 (점수·라벨·색상·baseline) 가 단일 v3 기준으로 정합.

### 4-3. 회귀 검사 (기존 동작 유지)
- 단건 ⓧ → 사유 모달 → 제외 + 토스트 ✅
- 그룹 일괄 제외 → 모달 → 일괄 적용 + 전체 복원 토스트 ✅
- 다크/라이트 모드 시각 회귀 0
- 이력 저장 색상 (v3 5단계) ✅

---

## 5. 사용자 / UI/UX 관점 피드백

### 5-1. 사용자 페인 해소
**Before** (오늘 발견 시점):
- 검사 결과 → "다운로드" 버튼 클릭 → 아무 응답 없음 → 사용자 답답

**After**:
- HTML/PDF 모두 즉시 다운로드 + 토스트 안내
- 보고서 본문의 점수·라벨·색상 100% 일관 (수동 제외 후도 stale 없음)

### 5-2. 신뢰성 강화
- 향후 유사 silent fail 발생 시 토스트로 즉시 가시화 (W-3)
- 모든 verdict 표기가 SSOT(`verdict_bands`) 경유 → 임계값 변경 시 한 곳만 수정

### 5-3. 사용자가 인지 불가했던 잠재 위험 해소
- W-2 (baseline stale): 평소 흐름에선 발생 빈도 낮지만 모드 전환·복원 조합 시 잘못된 baseline 가능성. 안전망 추가.

---

## 6. 부수 발견 (현 범위 외 — 후속 처리 후보)

| # | 항목 | 영향 | 후속 |
|---|------|------|------|
| O-1 | 그룹 헤더 sentCount = bucket span 합산 vs 사이드바 indicator = unique count (cluster overlap 시 차이) | 일반 케이스 영향 0 | W-4 별도 hotfix 가능 |
| O-2 | 자동 회귀에 다운로드 시나리오 미포함 | 같은 회귀 재발 위험 | S-1: Playwright 다운로드 시나리오 자동화 |

---

## 7. 자기 비판 (재발 방지)

### 이번 회귀의 근본 원인
- **변수 사용처 검색 누락**: Phase 2 작업 시 `var tiers` 만 보고 다른 사용처를 grep 하지 않음
- **다운로드 시나리오 회귀 검증 누락**: Playwright 검증을 검사·제외·복원·이력까지만 하고 다운로드는 빠뜨림

### 재발 방지 표준 (개인 체크리스트)
1. **변수 변경 → 동일 변수명 grep** (5초)
2. **try/catch 핵심 진입점** — 사용자 액션 → 즉시 가시화 안 되면 silent fail 의심
3. **Playwright 골든 패스에 다운로드 포함** — export 는 표절 검출 도구의 핵심 출력

---

## 8. 한 줄 결론

**PASS.** Plan-50 hotfix1 완료 — C-1 (Critical) + W-1·W-2·W-3·W-5 (Warning 4건) 5건 동시 정리. 다운로드 정상 복구, 보고서 표기 v3 일관성 회복. 자동 회귀·Playwright 시나리오 모두 통과.
