# Plan-45 Phase 6 실행 피드백 — 가이드·모달·온보딩 갱신

> 실행일 2026-04-25 · 실행자 Claude (/plan-execute) · 대상 `workbench/plans/45-similarity-label-unification.md` Phase 6 단독

## 요약
- 완료 Step: 5 / 5
- 변경 파일: 2개 (`contents/guide/verify-guide.html`, `compare.html`)
- 단위 테스트: **21/21 PASS** (Phase 2 회귀 유지)
- 어휘 정합성: Plan-38 옛 어휘 (4그룹/표절 의심/참고 가능/제외 영역) 잔존 0건
- Critical 0건 · Warning 0건 · Suggestion 1건 (TXT dead code 정리는 Phase 7)

## 구현 결과

| Step | 상태 | 변경 |
|---|---|---|
| 1 — verify-guide.html 분류 체계 재작성 | ✅ | 4그룹 + 6세부 → **4 카테고리** (Copyleaks 모방). v3 공식 + 신호등 5단계 |
| 2 — verify-guide.html 검사 설정·보고서·근거·FAQ 갱신 | ✅ | Excel·TXT 폐기 반영 (PDF·HTML), 자동 제외/수동 제외 FAQ 신설, "번역" → "의역 통합" 일관성 |
| 3 — Modal B (compare.html L1283~) fallback formula 갱신 | ✅ | "실질 매칭 + 의역·번역 × 0.5" → "(동일 + 거의 동일 + 의역) / (전체 - 제외)" |
| 4 — Modal A SVG 라벨 v3 동기 | ✅ | "일치" → **"동일"**, "번역" → **"의역 (번역)"** 색상 통합 (#7c3aed → #2563eb 의역 색) |
| 5 — 온보딩 2/3단계 텍스트 갱신 | ✅ | "4그룹" → "누적바", "HTML/Excel/TXT" → "PDF·HTML 보고서" |

## 핵심 변경 상세

### 1. verify-guide.html 분류 체계

**Before** (Plan-38 4그룹 + 6세부):
| 그룹 | 색상 | 포함 라벨 |
|---|---|---|
| 표절 의심 | 빨강 | 일치, 거의 동일, 의역, 번역 |
| 참고 가능 | 노랑 | 약한 유사 |
| 제외 영역 | 회색 | 공통 정형구문, 목차, ... |
| 일반 | 검정 | 매칭이 없는 일반 본문 |

**After** (Plan-45 v3 4 카테고리):
| 카테고리 | 색상 | 설명 | 점수 영향 |
|---|---|---|---|
| 동일 | 🔴 빨강 | 단어까지 거의 그대로 일치 | 점수에 포함 |
| 거의 동일 | 🟧 연빨강 | 단어 일부만 바꾼 구간 | 점수에 포함 |
| 의역 | 🟪 보라 | 표현은 다르나 같은 의미 (다른 언어 번역 포함) | 점수에 포함 |
| 약한 유사 | ⚪ 회색 | 부분 의미 겹침 — 검토자 판단 영역 | 점수 제외 (참고용) |

→ "번역" 카테고리 폐기 → 의역에 통합. "점수 영향" 컬럼 신설 (사용자 직관).

### 2. verify-guide.html 점수 산출법

**Before**:
```
유사율 = (실질 매칭 + 의역·번역 × 0.5) / (전체 문장 - 제외 영역) × 100
```

**After** (Copyleaks 공식, 가중치 없음):
```
유사율 = (동일 + 거의 동일 + 의역) / (전체 문장 - 제외 문장) × 100
```

→ 검증 표기 추가: "(76+50+89)/(597-105) = 43.7%" (Copyleaks 샘플 일치)

### 3. Modal B fallback formula 갱신

`compare.html:1283~1289`:
- SSOT 정상 시 `simHelp.score_formula` 자동 사용
- SSOT 로드 실패 시 fallback도 v3 공식
- 변수 의미: 동일/거의 동일/의역/제외 4개 (이전: 실질 매칭/의역·번역/정형구문 3개 가중치 형태)

### 4. Modal A SVG 라벨

`compare.html:1605~1620`:
- "일치" → **"동일"** (카테고리와 일치)
- "번역" → **"의역 (번역)"** + 색상 보라 (의역 카테고리 색)
- 카테고리 4종 × 알고리즘 6 유형 매핑 시각화 유지

### 5. 온보딩 2/3단계

- 2단계: "4그룹 옆 ⓘ" → "누적바 옆 ⓘ" (Phase 3.5 누적바 도입 반영)
- 3단계: "HTML/Excel/TXT" → "PDF·HTML 보고서" (Phase 5 폐기 반영)

## 검증 결과

### Grep 잔존 검증
```
=== verify-guide.html (Phase 6 후) ===
  "표절 의심" 잔존: 0건
  "참고 가능" 잔존: 0건
  "제외 영역" 잔존: 0건
  "4그룹" 잔존: 0건
  "의역·번역 × 0.5" 잔존: 0건
  "4 카테고리" 등장: 3건 ✓
  "Copyleaks" 등장: 5건 ✓
  "동일 + 거의 동일 + 의역" 등장: 1건 ✓

=== compare.html Modal/Onboarding ===
  옛 가중치 공식 잔존: 0건 (Modal B + 보고서 fallback 모두 v3로)
  "4그룹" 잔존: 0건
```

### Playwright 실측 (Modal B 직접 확인)

```
Modal B 텍스트 발췌:
  "유사율 = (동일 + 거의 동일 + 의역) / (전체 문장 - 제외 문장) × 100"
  변수: 동일 / 거의 동일 / 의역 / 제외 (4개)
  5단계 신호등: BLUE 0% / GREEN 1~24% 양호 / YELLOW 25~49% 검토 필요 / 
                 ORANGE 50~74% 상당량 매칭 / RED 75~100% 위험
  면책: 유사도 ≠ 표절 — 검토자의 판단이 최종
```

### Modal A 실측

```
2축 다이어그램 SVG 라벨: 동일 / 거의 동일 / 의역 / 의역 (번역) / 약한 유사
6라벨 정의표: SSOT labels.ko_long 자동 동기 (Phase 3.5 적용 유지)
```

### 단위 테스트 + 구문
- Phase 2 회귀: **21/21 PASS**
- Node 구문 파싱: PASS

### 회귀 스팟체크 (변경 금지 영역)
| 영역 | 결과 |
|---|---|
| 백엔드 `similarity_engine.py` | ✅ 변경 없음 |
| `data/help/similarity-help.json` | ✅ 변경 없음 |
| 사이드바 UI (Phase 3~4 결과) | ✅ 영향 없음 |
| HTML 리포트 (Phase 5 결과) | ✅ SSOT 경유로 자동 v3 동기 |
| 다른 모드 (compare/verify) export | ✅ 영향 없음 |

## 사용자 관점 피드백 (실측)

### 긍정
- **점수 ⓘ 클릭** → v3 공식 + 5단계 신호등 + 면책이 즉시 노출. Phase 5 보고서·사이드바와 일관
- **누적바 ⓘ 클릭** → 2축 다이어그램에 4 카테고리 시각화 (동일/거의 동일/의역/의역(번역)/약한 유사). 사이드바와 직관적 매칭
- **가이드 페이지** Plan-38 어휘 0건, v3 어휘 100% 정착
- **온보딩 1~3단계** 4 카테고리 안내 일관 (Phase 3.5 + Phase 6 조합)

### 우려
- Modal A SVG가 정적 이미지라 SSOT 변경 시 자동 갱신 안 됨 (수동 변경 필요) — 현재는 v3 동기 완료, 향후 7번째 카테고리 추가 시 SVG 직접 수정 필요
- "의역 (번역)" 라벨이 알고리즘 구분(translation type)과 카테고리 통합(paraphrased)을 동시에 표현 — 학술 사용자에게 명확하지만 일반 사용자에 약간 혼란 가능

### 개선 제안
- Modal A 별첨 표에 "translation 유형도 의역 카테고리에 속함" 명시적 주석 (Phase 7 또는 후속)

## 웹디자인 전문가 관점 (자가 평가)

### 시각적 위계
- **양호**: Modal B 산식 → 변수 의미 → 5단계 신호등 → 면책 흐름 자연스러움
- 가이드 페이지 4 카테고리 표 + 점수 영향 컬럼 (사이드바 7지표와 같은 시각 언어)

### 인터랙션
- 모달 ⓘ 클릭 → 즉시 표시 (지연 없음)
- 가이드 페이지 헤딩 앵커 (#분류-체계 등) 그대로 유지

### 다크모드
- Modal: var() 변수 경유 자동 전환
- 가이드 페이지: contents/guide CSS 자동 전환

### 접근성
- Modal `role`·`aria-label` 유지
- 가이드 표 thead/tbody 시맨틱

## 잔여·후속 제안

### Phase 7 (드리프트 방지 + 회귀)
- [ ] TXT export dead code 정리 (`doExportSimilarityTxt`, L4711) — Phase 5에서 UI 버튼 제거됐으나 함수 잔존
- [ ] `simUpdateMatchCard` dead code 정리 (Phase 4 이후 simShowResults 전체 재렌더로 대체됨)
- [ ] `tests/sim_label_consistency.sh` 작성 — grep 자동 검증 (E1~E3 + Plan-38 옛 어휘 잔존 검사)
- [ ] CLAUDE.md 분류 체계 규칙 추가
- [ ] 골드셋 14페어 재실행 (점수 수치 변동 기록)

### 후속 개선 (별도 Plan)
- [ ] Modal A "translation→의역 통합" 명시 주석 추가
- [ ] ⓘ/? 아이콘 정책 — 현재 ⓘ=모달, ?=툴팁 명확. 추가 통일 불필요 판단

## 커밋 제안

```
추가 [Plan-45/P6] 가이드·모달·온보딩 v3 어휘·공식 동기

Plan-45 Phase 6: verify-guide.html, Modal B fallback, Modal A SVG,
온보딩 텍스트를 Plan-45 v3 (4 카테고리 + Copyleaks 공식 + PDF/HTML) 기준으로 갱신.

변경:
- contents/guide/verify-guide.html
  · 분류 체계 표: 4그룹 + 6세부 → 4 카테고리 (Copyleaks 모방)
    "점수 영향" 컬럼 신설
  · 점수 산출법: 가중치 0.5 폐기 → Copyleaks aggregatedScore 공식
    "(76+50+89)/(597-105) = 43.7%" 검증 표기 추가
  · 도구·알고리즘 근거: Copyleaks detection levels 출처 명시
  · 보고서 출력 활용법: HTML/Excel/TXT 3종 → PDF/HTML 2종
    별첨 A 매칭 상세 + 별첨 B 검사 기준 양식 설명
  · FAQ: "자동 제외 카드는 무엇?", "수동 제외와 복원 방법" 신설
    "번역" 단독 카테고리 → "의역 통합" 어휘 일관성
- compare.html Modal B fallback (L1283~1289)
  · formula: "(실질 + 의역·번역 × 0.5)" → "(동일 + 거의 동일 + 의역)"
  · variables: 4개 항목 (동일/거의 동일/의역/제외) v3 어휘
- compare.html Modal A SVG 라벨 (L1605~1620)
  · "일치" → "동일" (카테고리 일치)
  · "번역" → "의역 (번역)" + 색상 보라 (의역 카테고리 통합 시각화)
- compare.html 온보딩 2/3단계 (L1701~1708)
  · "4그룹 옆 ⓘ" → "누적바 옆 ⓘ"
  · "HTML/Excel/TXT 보고서" → "PDF·HTML 보고서 (PDF 권장)"

검증:
- 단위 테스트 21/21 PASS (Phase 2 회귀)
- Node 구문 파싱 PASS
- verify-guide.html 옛 어휘 (4그룹/표절 의심/참고 가능/제외 영역) 0건
- compare.html 옛 가중치 공식 ("실질 매칭 + 의역·번역 × 0.5") 0건
- Playwright 실측 — Modal B v3 공식 + 5단계 신호등 정상 표시
- 백엔드·SSOT JSON 변경 없음

잔여 (Phase 7):
- TXT export dead code 정리 (doExportSimilarityTxt)
- simUpdateMatchCard dead code 정리
- tests/sim_label_consistency.sh 자동 grep 테스트
- CLAUDE.md 분류 체계 규칙 추가
- 골드셋 14페어 재실행

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```
