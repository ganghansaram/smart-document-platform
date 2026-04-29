# Plan-50 Phase 0~3 — 구현 후 검증 피드백

> 작성일: 2026-04-30
> 변경 범위: `backend/services/similarity_engine.py`, `compare.html`, `tests/sim_label_consistency.sh`, `tests/sim_score_v3_unit_test.py` (신규)
> 검증: 자동 회귀 (sim_label_consistency + 골든셋 5건) + Playwright 브라우저 시나리오

---

## 1. 변경 요약

### Phase 0 — 회귀 방어망 강화
| 파일 | 변경 |
|------|------|
| `tests/sim_label_consistency.sh` | C2-legacy (백엔드 `× 0.5`), T1-legacy (옛 3단계 임계 30/60·40/70) 패턴 신규 추가 |
| `tests/sim_score_v3_unit_test.py` (신규) | `_compute_summary` 직접 호출 골든셋 5건 (의역만/혼합/약한유사/동일/verdict_band 정합) |

### Phase 1 — 백엔드 점수 공식 v3 통일
| 파일·위치 | 변경 |
|----------|------|
| `similarity_engine.py:897` | `(substantive + derived * 0.5)` → `(substantive + derived)` (Plan-45 v3 공식) |
| 자동 파급 | `tiers.adjusted` · `similarity_score` · `verdict_band` · `verdict_label` · `sources[].match_pct` 모두 v3 점수 기반으로 자동 갱신 |

### Phase 2 — 화면 배너 단일 점수 + 보고서 baseline 정합
| 파일·위치 | 변경 |
|----------|------|
| `compare.html:382` | `simBaselineScore` 변수 신규 (수동 제외 전 v3 baseline 보관) |
| `compare.html:simShowResults` | 첫 렌더 시점 `simBaselineScore = initialResult.score` (수동 제외 카드 미존재일 때만) |
| `compare.html:simUpdateExclusionBanner` | 배너 단일 점수 — `"수동 제외 N건 반영"` 만 표시 (옛 "원점수 X% → 조정 Y%" 제거) |
| `compare.html:buildExportPayload` | `payload.score_baseline` 신규 + `score_original` 의미 v3 baseline 으로 재정의 |
| `compare.html:buildSimilarityReportHtml` (L5346) | 보고서 라벨 "원점수" → "수동 제외 전" |

### Phase 3 — 옛 3단계 임계값 잔존 정리
| 파일·위치 | 변경 |
|----------|------|
| `compare.html` 이력 저장 (L2664~) | 색상 임계 (40/70) → v3 verdict_band (`bandColorMap[summary.verdict]`) 기반 |
| `compare.html` (L624~625) | `verdictBoundLow=30/High=60` → `25/74` (v3 5단계 첫·마지막 임계와 정합) |
| `compare.html` (L2444~) | simHelp 미로드 fallback 라벨 "양호/보통/주의" → "양호/검토 필요/위험" (v3 어휘) |
| `compare.html:payload.verdict_legacy` | "주의/보통/양호" → "위험/검토 필요/양호" (v3 라벨, 안전망 fallback) |

---

## 2. 영향도 분석 (코드 전문가 관점)

### 2-1. Phase 1 자동 파급 검증
백엔드 `adjusted_pct` 한 줄 변경으로 다음이 모두 v3 점수 기반이 됨:
- `summary.similarity_score` (이력 점수값)
- `summary.tiers.adjusted` (보고서 score_original 폴백)
- `summary.verdict` / `verdict_label` (보고서 점수 BOX 색상·라벨)
- `summary.sources[].match_pct` (보고서 출처 카드)

→ **현업 피드백 2 (보고서 점수 BOX 색상 불일치) 자동 해소**. 코드 변경량 최소.

### 2-2. baseline 보존 로직
`simBaselineScore` 는 첫 렌더 시점에만 갱신 (`hasUserExcluded` 체크). 수동 제외 후 `simShowResults` 가 재렌더해도 baseline 은 고정. 모드 전환 시 `simLastResult = null` 과 함께 자연 reset.

### 2-3. payload 호환 유지
- `payload.score_original` 은 키 이름 보존, 의미만 v3 baseline 으로 재정의 — 기존 보고서 파서 (백엔드 export_service.py) 무수정
- `payload.score_baseline` 은 신규 명시적 키 — 향후 보고서 코드에서 baseline 의미 명확히 지칭 가능

### 2-4. SSOT 라벨 정합
- `tests/sim_label_consistency.sh` PASS — 옛 어휘·옛 공식·옛 임계값 잔존 0건
- 골든셋 5/5 PASS — `_compute_summary` 가 v3 공식 일치

### 2-5. 회귀 위험 평가
| 시나리오 | 위험도 | 완화 |
|---------|-------|------|
| 점수 표기 변동 (의역 다발 문서) | 🟡 중 | 사용자 사전 공지 (v2.8 릴리즈 노트) |
| 기존 이력 점수와 신규 검사 점수 불일치 | 🟡 중 | 비목표 §4 정책 — 신규부터 v3, 기존 이력 그대로 |
| 보고서 호환 (`score_original`) | 🟢 낮음 | 의미 재정의로 키 이름 보존 |
| Phase 3 fallback 라벨 변경 | 🟢 낮음 | simHelp 미로드 케이스 (실제 거의 미발생) |

---

## 3. UI/UX 영향 분석

### 3-1. 현업 피드백 1 직접 해소
**Before**: "수동 제외 1건 반영 / 원점수 50% → 조정 0%" — 사용자: "원점수 50%? 점수 카드는 100% 였는데?"
**After**: "수동 제외 1건 반영" 단일 라인 — 점수 카드는 항상 v3 점수만 표시

→ "원점수" 단어가 화면에서 사라짐. 인지 부담 0.

### 3-2. 현업 피드백 2 직접 해소
**Before**: 보고서 점수 BOX "39.4% / 양호 / 녹색" (점수는 v3, 라벨/색상은 옛 공식)
**After**: 보고서 점수 BOX "39.4% / 검토 필요 / 노랑" (점수·라벨·색상 모두 v3 5단계)

→ 점수와 시각 표시 일치.

### 3-3. 이력 페이지 색상 정합
**Before**: 임계 40/70 — 50% 노랑, 80% 빨강
**After**: v3 5단계 — 25/49/74 — 50% 주황, 80% 빨강

→ 5단계 verdict 정확 매핑.

### 3-4. 보고서 감사 추적
- 화면은 단순 (단일 점수)
- 보고서는 "수동 제외 전 X% / 조정 Y%" 두 점수 + 사유별 집계 — 검토자가 의사결정 근거 확인 가능

---

## 4. 검증 결과

### 4-1. 자동 회귀
| 검사 | 결과 |
|------|------|
| `tests/sim_label_consistency.sh` (E1·E2·C1·C2·E2-legacy·T1-legacy) | ✅ PASS |
| `tests/sim_score_v3_unit_test.py` (골든셋 5건) | ✅ 5/5 PASS |
| 골든셋 케이스 A (의역 10/10 → 100%) | ✅ |
| 골든셋 케이스 B (혼합 → 60%) | ✅ |
| 골든셋 케이스 C (약한유사 분자 미반영 → 40%) | ✅ |
| 골든셋 케이스 D (동일만 → 50%, v2/v3 동일) | ✅ |
| 골든셋 케이스 E (verdict 100→red, 40→yellow) | ✅ |

### 4-2. Playwright 브라우저 시나리오
| 항목 | Before | After | 결과 |
|------|--------|-------|------|
| 점수 카드 | 100% (v3) | 100% (v3) | 무변동 |
| Verdict 라벨 | "주의" (옛 3단계) | **"위험"** (v3 5단계) | ✅ v3 정합 |
| 배너 | "원점수 50% → 조정 0%" | **"수동 제외 1건 반영"** | ✅ 단일 점수 |
| 이력 색상 | 임계 40/70 | **v3 verdict_band 색상** | ✅ 신규 검사 정합 |
| 단건 ⓧ 회귀 | 정상 | 정상 | ✅ |
| 일괄 제외 회귀 | 정상 | 정상 | ✅ |

### 4-3. 시각 캡처
- `phase123-result.png` — 검사 결과 (100% / "위험" / 의역 10건 + 일괄 버튼)
- `history-loaded.png` — 이력 페이지 (신규 100% 빨강 / 옛 50% 노랑 / 옛 0.8% 초록)

---

## 5. 사용자 관점 피드백 (현업 부서 가상 시나리오)

### 시나리오 — "의역 비중 큰 문서를 검사하고 일부 항목을 제외"
**Before** (Plan-50 적용 전):
1. 검사 → 100% (v3)
2. 일부 제외 → 50% / 배너 "원점수 25% → 조정 50%"
3. 사용자: **"원점수가 뭐고 왜 더 낮지? 50% 가 더 높은데"** 🚨

**After** (Phase 0~3 적용 후):
1. 검사 → 100% / "위험"
2. 일부 제외 → 50% / 배너 "수동 제외 N건 반영" (단일)
3. 보고서: 점수 BOX "50% / 위험 / 빨강" + 작은 글씨 "수동 제외 전 100% · 수동 제외 N건 반영"
4. 사용자: **"원점수 단어 안 보이고 점수와 색상이 일치하니 직관적"** ✅

### 잠재 우려
- 의역 비중 큰 기존 문서를 다시 검사하면 점수 약 2배 상승 (옛 가중치 0.5 → 1.0). 사용자가 "왜 점수가 갑자기 올랐지?" 인지 가능.
- **권장 완화**: v2.8 릴리즈 노트에 "점수 산식 v3 통일로 의역 다발 문서 점수 상승 가능. 절대 임계는 동일." 명시.

---

## 6. 웹디자인 전문가 관점 피드백

### 6-1. 시각 일관성 ✅
- 점수 카드·verdict 라벨·5단계 신호등 색상이 단일 공식 기반으로 정합
- 보고서 점수 BOX 색상이 5단계 SSOT 와 일치 — 인쇄·PDF 출력 시도 동일
- 이력 페이지 색상도 v3 verdict 와 정합 (신규 검사부터)

### 6-2. 정보 위계
- 화면 점수 카드 = primary (가장 큰 글씨, 단일 점수)
- 배너 = secondary (작은 글씨, 사실 안내)
- 보고서 score-card = primary (점수 + 라벨), 작은 글씨로 baseline + 사유 (감사 추적)

→ 의도된 **단순 화면 / 풍부한 보고서** 분리 패턴 구현됨.

### 6-3. 접근성
- v3 색상 토큰 (var(--color-error) 등) 사용 — 라이트/다크 모두 자동 적응
- 라벨 어휘 ("위험", "검토 필요") 가 색상 의존 없이 의미 전달

### 6-4. 개선 제안 (수용은 후속 판단)
1. **이력 페이지 공식 버전 메타** (Plan-50 §10 후속 검토 — C-1)
   - 기존 이력 (옛 공식 점수) 과 신규 (v3) 가 시각 구분 없이 섞임
   - 향후 옵션: 이력 항목에 작은 배지 "v2 공식" 표시, 또는 새 v3 적용 이전 이력 흐림 처리
   - 우선순위: 낮음 (사용자 명시 요구 시 적용)
2. **배너 액세서리 라인 텍스트 확장 검토**
   - 현재: "수동 제외 1건 반영"
   - 검토 대상: "수동 제외 1건 반영 (점수 0%)" 처럼 결과 명시
   - 다만 점수 카드가 바로 위에 있어 중복 — 현재 형태 유지가 깔끔

---

## 7. 발견된 부수 관찰 (현 범위 외)

| # | 항목 | 우선 | 비고 |
|---|------|------|------|
| O-1 | 기존 이력 (`_history.json`) 점수 = 옛 공식 영구 잔존 | 중 | Plan-50 §4 비목표 — 소급 재계산 안 함. C-1 메타 표기 후속 검토 |
| O-2 | 사용자 가이드 페이지 (`verify-guide.html`) 점수 예시 | 낮 | "원점수" 표현 사용 안 함 — 무수정 OK. v2.8 릴리즈 노트에 점수 변동 안내 권장 |
| O-3 | Excel 보고서 (`export_service.py:105`) | 낮 | `verdict_label` (백엔드 v3) 우선 사용 — Phase 1 자동 파급으로 정합 |
| O-4 | Plan-50 Phase 4~7 (분모 정합·단위 표기·약한유사 ⓧ·마감) | 후속 | 후속 릴리즈에 묶음 적용 |

---

## 8. 한 줄 결론

**PASS.** Plan-50 Phase 0~3 완료. 자동 회귀·골든셋·브라우저 시나리오 모두 통과. 현업 피드백 2건 (원점수 인지 부담 + 보고서 색상 불일치) 정확히 해소. 1라인 백엔드 변경 + 프론트 표기 정정 + 이력 색상 정합으로 SSOT 통일 완성.
