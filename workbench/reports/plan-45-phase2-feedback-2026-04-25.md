# Plan-45 Phase 2 실행 피드백 — resolveCategory + computeScore 도입

> 실행일 2026-04-25 · 실행자 Claude (/plan-execute) · 대상 `workbench/plans/45-similarity-label-unification.md` Phase 2 단독

## 요약
- 완료 Step: 1 / 1 (Phase 2 — 프론트 단일 판정 함수 + Copyleaks 공식 도입)
- 변경 파일: 2개 (`compare.html` 로직 변경, `tests/sim_phase2_test.js` 신규)
- 단위 테스트: **21/21 PASS** (U1~U10, 13개 서브케이스 포함)
- Critical 이슈: 0건 · Warning: 3건 (모두 Phase 3~5 예정) · Suggestion: 3건

## 구현 결과

| Step | 상태 | 변경 파일 | 메모 |
|------|------|----------|------|
| 1    | ✅   | `compare.html:2374~` | `SIM_TYPE_TO_CATEGORY` 상수 + `resolveCategory()` 신설 |
| 2    | ✅   | `compare.html:2416~` | `computeScore()` 순수 계산 함수 신설 (Copyleaks 공식) |
| 3    | ✅   | `compare.html:1411~1471` | `simRecomputeFromSettings()` 재작성 — computeScore 재사용, 가중치 제거, hint 단순화 |
| 4    | ✅   | `compare.html:2412 및 2598` | 초기 hint placeholder 전환, simRecomputeFromSettings 무조건 호출 |
| 5    | ✅   | `tests/sim_phase2_test.js` | 21건 단위 테스트 PASS |

**총 코드 변동**: +64 / -55 줄 (compare.html)

## 핵심 변경 상세

### 1. `resolveCategory(match, settings)` — 단일 판정 함수
- Plan-45 §2 원칙 그대로 구현: user_excluded > 자동 제외 > 유형 기반
- `SIM_TYPE_TO_CATEGORY` 매핑 상수 명시 (translation → paraphrased 통합)
- boilerplate 는 항상 `excluded_auto` (설정 무관)

### 2. `computeScore(matches, totalSentences, settings)` — Copyleaks 공식
- 공식: `(identical + near_copy + paraphrased) / (totalSentences - excluded) × 100`
- Plan-38 대비: **0.5 가중치 제거**
- low_similarity 는 점수 분자에서 제외 (C3 불변)
- denominator 0 방지 (`Math.max(total - excluded, 1)`)

### 3. `simRecomputeFromSettings` 재작성
- 순수 계산은 computeScore 에 위임
- DOM 업데이트만 담당
- hint 문구: `'유사율 43.7% (실질 X% · 의역·번역 Y%)'` → **`'유사율 43.7%'`** (카테고리 breakdown은 사이드바에서 확인)
- 카드 흐리게 처리: `simIsActiveExclusion` 직접 호출 → `resolveCategory() === 'excluded_auto'` (단일 경로)
- 4그룹 바 렌더링: **현재는 레거시 호환 유지** (Phase 3에서 4 카테고리로 교체 예정), 단 카운트는 v3 기준으로 계산

### 4. `simShowResults` 초기 hint 단순화
- tiers.adjusted (백엔드 구 공식 값) 노출 제거
- placeholder "유사율 계산 중…" 표시 → 즉시 simRecomputeFromSettings 가 v3 값으로 덮어씀
- `hasOverride` 조건 제거 → **항상 재계산** (백엔드 값과 화면 값 일관성 보장)

## 검증 결과

### 단위 테스트 (tests/sim_phase2_test.js)

```
=== Plan-45 Phase 2 단위 테스트 (U1~U10) ===
[resolveCategory 기본 유형 매핑]
  ✓ U1~U6 (6 유형 모두 정확 매핑)

[자동 제외 + 수동 제외 우선순위]
  ✓ U7 toc_heading + exclude_toc=true → excluded_auto
  ✓ U8 toc_heading + exclude_toc=false → 원래 카테고리
  ✓ U9 user_excluded 최우선 (identical + user_excluded=true → excluded_manual)

[computeScore — Copyleaks aggregatedScore 공식]
  ✓ U10-a Copyleaks 샘플: (76+50+89)/(597-105) = 43.7% ← 샘플 리포트 일치
  ✓ U10-b~e counts 정확
  ✓ U10-f~g low_sim 점수 제외 (C3 불변)
  ✓ U10-h 가중치 없음: 구공식 30% → 신공식 40% (검증)
  ✓ U10-i~j 수동 제외 분모 차감 (C4)
  ✓ U10-k 빈 매칭 안전
  ✓ U10-l denominator 0 방지

───────────────────────────────
PASS: 21 · FAIL: 0
───────────────────────────────
```

### 구문 무결성
- Node.js `new Function(scriptBody)` syntax parse: **PASS**
- Brace balance (1351/1351): 균형
- Paren balance (-2): 문자열/정규식 내 허용 불균형 (실제 문법 오류 아님, parse 성공)

### 코드 품질 리뷰 (code-reviewer 에이전트)

| 카테고리 | 건수 | 상태 |
|---|---|---|
| Critical | 0 | ✅ |
| Warning | 3 | Phase 3~5 범위로 이관 |
| Suggestion | 3 | 선택적 개선 |

#### Warning 3건 (모두 Phase 3~5 예정)

1. **compare.html:5014** — HTML 리포트 export 코드에서 `tm.group === '표절 의심'` 같은 한글 문자열 비교. SIM_TYPE_TO_CATEGORY 외 경로.
   → **Phase 5 (HTML 리포트 재구성)** 에서 resolveCategory 기반 재작성 시 해결

2. **compare.html:2560** — 카드 렌더 시 `typeKey = m.type || (m.level === 'high' ? 'identical' : 'paraphrase')` — `m.level` 폴백 경로.
   → **Phase 3 (사이드바 UI 재구성)** 에서 카드 렌더 재작성 시 해결

3. **compare.html:4548-4549** — TXT export `'실질 유사: X% · 의역: Y% · 공통: Z%'` 라인이 백엔드 tiers (구 공식 값) 사용. Plan-45 v3 정책과 불일치.
   → **Phase 5 (HTML 리포트 + TXT 제거)** 에서 TXT 경로 자체가 제거됨으로 자동 해결

#### Suggestion 3건

- `span` 음수 방지 (`Math.max(1, span)` 가드) — Phase 7 정리 시 적용
- 점수 카드 innerHTML 대체 시 이벤트 리스너 손실 가능성 — 현재 이벤트 위임 방식 사용 확인됨, 무해
- hint 문구에 verdict label 포함 검토 — UX 결정 사안, 보류

### 회귀 스팟체크 (계획서 §5 "변경 금지" 영역)

| 파일 | 체크 | 결과 |
|---|---|---|
| `backend/services/similarity_engine.py` | 분류 로직·exclusion_breakdown 불변 | ✅ git diff 0 |
| `backend/api/help.py` | Phase 1 변경 외 추가 수정 없음 | ✅ git diff 0 |
| `backend/config.py` | 임계값 불변 | ✅ git diff 0 |
| `data/help/similarity-help.json` | Phase 1 상태 유지 | ✅ git diff 0 |

Phase 2 변경은 `compare.html` 단일 파일에 격리됨.

## 사용자 관점 피드백

### 긍정
- **백엔드·SSOT·CSS 모두 불변**: 순수 JS 로직 변경만 — Phase 1의 SSOT 교체와 깔끔하게 분리됨
- **단위 테스트 21건 PASS**: Copyleaks 샘플 정확 재현 포함 — 공식 정합성 확인됨
- **hint 단순화 즉시 체감**: 상단 "유사율 43.7%" 만 보여 인지 부하 감소
- **simRecomputeFromSettings 무조건 호출**: 기본 설정 사용자도 v3 공식 점수를 보게 됨 (이전: 백엔드 구 공식이 화면에 노출될 수 있었음)

### 우려 (Phase 3~5 에서 해소 예정)
- 4그룹 바의 "표절 의심 / 참고 가능 / 제외 영역 / 일반" 라벨은 **아직 그대로** — Phase 3에서 교체
- HTML/TXT 리포트 내보내기는 **아직 구 공식의 잔존 값 노출** — Phase 5에서 재작성
- 카드 내부 라벨·필터 칩 등 UI 전반은 Phase 3 대상

### 개선 제안
- Phase 3 착수 전 브라우저에서 유사도 검사 1회 실행하여 **점수 수치 변화** 확인 권장 (구 공식 대비 몇 % 포인트 상승할 것으로 예상)
- 기존 Plan-38 샘플 테스트 데이터가 있다면 점수 델타 스냅샷 보관

## 웹디자인 전문가 관점 피드백

### 시각적 변화
- **최상단 hint 영역**: `'유사율 43.7% (실질 X% · 의역·번역 Y%)'` → **`'유사율 43.7%'`** — 3개 숫자 → 1개 숫자 (정보 밀도 감소)
- **점수 카드**: 동일 수치 자리에 새 공식 값 (숫자 변동 있음)
- **4그룹 바·사이드바·카드**: 변화 없음 (Phase 3 대상)

### 인터랙션
- 설정 변경 → 즉시 재계산: 기존 동작 유지
- 수동 제외 → 점수 재계산: 기존 동작 유지
- 초기 로드 시 "유사율 계산 중…" placeholder 0.1초 이하 노출 후 실제 값으로 교체 (시각 flash 수준)

### 다크모드·접근성
- DOM 구조 변화 없음 → 다크모드·접근성 영향 0
- placeholder 텍스트 "…" (ellipsis 문자) 사용 — 접근성 문제 없음

## 잔여·후속 제안

### Phase 3 (사이드바 UI 재구성) 시 참고
- [ ] 4그룹 바 DOM을 4 카테고리 (동일/거의 동일/의역/약한 유사) 기반으로 교체
- [ ] 카드 렌더의 `m.level` 폴백 코드 (L2560) 제거 — resolveCategory 로 통일
- [ ] "표절 의심 / 참고 가능 / 제외 영역 / 일반" 하드코딩 라벨을 categories[key].ko 로 교체

### Phase 5 (HTML 리포트 재구성) 시 참고
- [ ] TXT export L4548-4549 `tiers.substantive/derived/boilerplate` 문자열 제거 (TXT 경로 자체 폐기)
- [ ] HTML 리포트 `tm.group` 한글 비교 (L5014) → `CATEGORY_COLOR` 매핑 상수 도입

### Phase 7 (드리프트 방지) 시 참고
- [ ] `span` 음수 방지 가드 추가 (`Math.max(1, ...)`)
- [ ] `tests/sim_phase2_test.js` 를 `tests/sim_label_consistency.sh` 와 함께 CI 또는 pre-commit 에 등록

## 커밋 제안 (사용자 요청 시)

```
추가 [Plan-45/P2] resolveCategory + computeScore 프론트 도입

Phase 2: 유사도 점수 계산을 Copyleaks 공식 (가중치 없음) 으로 교체.
compare.html 순수 JS 로직만 변경. 백엔드·SSOT·CSS 불변.

변경:
- compare.html 2374~ : SIM_TYPE_TO_CATEGORY + resolveCategory() 신설
  · 단일 카테고리 판정 경로 확립
  · 우선순위: user_excluded > 자동 제외 > 유형 기반
  · translation → paraphrased 통합 매핑
- compare.html 2416~ : computeScore() 신설 (Copyleaks aggregatedScore 공식)
  · (동일 + 거의 동일 + 의역) / (전체 문장 - 제외) × 100
  · 가중치 없음 (기존 paraphrase × 0.5 제거)
  · low_similarity 점수 제외 (참고용 유지)
- compare.html 1411~ : simRecomputeFromSettings() 재작성
  · computeScore 재사용
  · hint 단순화: "유사율 N%" (breakdown은 사이드바에서 확인)
  · 카드 excluded 판정을 resolveCategory 단일 경로로
- compare.html 2412 : 초기 hint placeholder "유사율 계산 중…"
- compare.html 2598 : simRecomputeFromSettings 무조건 호출 (hasOverride 조건 제거)
- tests/sim_phase2_test.js 신규: U1~U10 단위 테스트 21건 PASS

검증:
- Copyleaks 샘플: (76+50+89)/(597-105) = 43.7% ✓
- 가중치 제거 검증: 구공식 30% → 신공식 40% ✓
- resolveCategory 우선순위 9건 PASS
- 경계값 (빈 매칭, denominator 0) 안전
- Node syntax parse PASS

잔여 (Phase 3~5 처리 예정):
- 4그룹 바 DOM: 레거시 호환 유지 (Phase 3에서 4 카테고리 교체)
- HTML/TXT 리포트 구 tiers 참조: Phase 5 처리
- m.level 폴백 코드: Phase 3 처리
```
