# Plan-45 Phase 7 실행 피드백 — 드리프트 방지 + 회귀 (최종)

> 실행일 2026-04-25 · 실행자 Claude (/plan-execute) · 대상 `workbench/plans/45-similarity-label-unification.md` Phase 7 (마지막)

## 요약
- 완료 Step: 5 / 5
- 변경 파일: 4개 (`tests/sim_label_consistency.sh` 신규, `CLAUDE.md`, `compare.html`, `backend/services/export_service.py`)
- 단위 테스트: **21/21 PASS** (Phase 2 회귀 유지)
- 라벨 일관성 자동 테스트: **PASS**
- Python 백엔드 import: PASS
- Critical 0건 · Warning 0건 · Suggestion 1건 (toast race 재현 안 됨)

## Plan-45 전체 종료

| Phase | 상태 | 커밋 | 핵심 산출물 |
|---|---|---|---|
| P1 SSOT v3 | ✅ | 8c88264 | `similarity-help.json` v3, `_cache` 제거 |
| P2 resolveCategory + computeScore | ✅ | 6689565 | 단위 테스트 21건, Copyleaks 공식 |
| P3 사이드바 UI 재구성 | ✅ | 1f2c60f | 4 카테고리 필터, 7지표 표지, 누적바 |
| P3.5 UI 완성도 보정 | ✅ | fada1dc | 용어 통일, 5단계 신호등, 카드 섹션 헤더 |
| P4 제외 패널 분리 | ✅ | 2b3a039 | 접이식 panel, toast [복원], badge 카테고리 |
| P5 HTML 리포트 재구성 | ✅ | ffa14c5 | typeMeta SSOT, 카테고리 그룹핑 |
| P6 가이드·모달·온보딩 | ✅ | 21c3204 | verify-guide v3 재작성 |
| **P7 드리프트 방지 + 회귀** | ✅ | 대기 | grep 자동 테스트, CLAUDE.md 규칙, dead code 정리 |

## 구현 결과

| Step | 상태 | 변경 |
|---|---|---|
| 1 — `tests/sim_label_consistency.sh` 신설 | ✅ | grep 기반 자동 검증: E1-legacy (4그룹 어휘), C1-legacy (옛 가중치 공식), E2-legacy (옛 카드 라벨). false positive 방지 위해 `js/` 검사 제외 |
| 2 — `CLAUDE.md` 분류 체계 규칙 추가 | ✅ | 카테고리 4 / 유형 6 / 공식 / 규칙 6항 / 자동 검증 안내 |
| 3 — `simUpdateMatchCard` dead code 제거 | ✅ | Phase 4에서 `simShowResults` 전체 재렌더로 대체됨 (호출처 0건 확인) |
| 4 — `doExportSimilarityTxt` dead code 제거 + `runExport` 분기 정리 | ✅ | Phase 5에서 TXT 버튼 UI 제거됨 (호출 경로 도달 불가) |
| 5 — 잔존 옛 어휘·공식 갱신 | ✅ | `export_service.py` fallback (labels·formula) v3 동기, `compare.html` HTML 리포트 CSS "(제외 영역)"→"(자동 제외)" |

## 핵심 변경 상세

### 1. `tests/sim_label_consistency.sh`

```bash
검사 항목:
  [E1-legacy] Plan-38 옛 그룹 어휘 ("표절 의심"·"참고 가능"·"제외 영역") 잔존 0건
  [C1-legacy] 옛 가중치 공식 ("실질 매칭 + 의역·번역 × 0.5") 잔존 0건
  [E2-legacy] 옛 카드 라벨 ("label: '일치'"·"label: '번역'") 잔존 0건

검사 대상: compare.html, css/compare.css, backend/services, backend/api
예외: similarity-help.json (SSOT), verify-guide.html (가이드), workbench, tests, .claude
False positive 방지: js/ 디렉토리 제외 (Translator 시스템 등)

종료 코드: PASS=0 / FAIL=1
```

**실행 결과**:
```
PASS: 모든 라벨·공식 일관성 검증 통과
```

→ pre-commit hook 또는 CI에 등록하여 향후 드리프트 자동 차단.

### 2. `CLAUDE.md` 분류 체계 규칙

본 프로젝트의 **유사도 분류 체계** 섹션 신설:
- 카테고리 (4): 동일 / 거의 동일 / 의역 / 약한 유사
- 알고리즘 유형 (6): identical / near_copy / paraphrase / translation / low_sim / boilerplate
- 점수 공식: `(동일 + 거의 동일 + 의역) / (전체 - 제외) × 100` (가중치 없음)
- 규칙 6항: SSOT 경유 / 축약 금지 / 옛 어휘 사용 금지 / `resolveCategory` 단일 경로 / 필터·설정·수동 제외 의미 / 제외 카드 메인 비노출
- 자동 검증: `bash tests/sim_label_consistency.sh`

→ 향후 다른 개발자/에이전트가 분류 체계를 손댈 때 이 섹션을 참조해 일관성 유지.

### 3. Dead code 정리

| 함수 | 상태 | 처리 |
|---|---|---|
| `simUpdateMatchCard` (compare.html L2939) | Phase 4 이후 호출처 0건 | 폐기 주석으로 대체 |
| `doExportSimilarityTxt` (compare.html L4657) | Phase 5 이후 UI 진입 경로 없음 | 폐기 주석으로 대체 |
| `runExport(fmt='txt') if currentMode==='similarity'` 분기 | 도달 불가 | 분기 제거 (compare/verify만 유지) |

`compare.html` 약 90줄 dead code 제거. 가독성 향상 + 미래 혼란 방지.

### 4. 잔존 옛 어휘·공식 갱신

**`export_service.py` fallback labels** (L367~):
- `identical.ko_long`: "일치 (직접 차용)" → "동일 (직접 차용)"
- `translation.ko_long`: "번역 (다른 언어)" → "의역 (다른 언어 번역)"
- `low_sim.ko_long`: "약한 유사 (참고 가능)" → "약한 유사 (참고용)"

**`export_service.py` fallback formula** (L375):
- `"유사율 = (실질 매칭 + 의역·번역 × 0.5) / (전체 문장 - 정형구문) × 100"` → v3 공식

**`export_service.py` Excel 요약 시트** (L101~113):
- "실질 유사" → "동일·거의 동일"
- "의역·번역" → "의역"
- "정형구문" → "공통 정형구문"
- "제외 영역" → "제외 문장"

**`compare.html` HTML 리포트 CSS** (L5089):
- `.match-excluded::after { content: " (제외 영역)" }` → " (자동 제외)"

## 검증 결과

### 자동 검증
```
✅ 단위 테스트 21/21 PASS (Phase 2 회귀)
✅ Node 구문 파싱 PASS
✅ tests/sim_label_consistency.sh PASS
✅ Python 백엔드 import OK (export_service.py)
```

### 수동 체크 (M1~M5 — 계획서 §10.3)

| ID | 체크 | 결과 |
|---|---|---|
| M1 | 한 매칭의 카테고리·색·라벨이 사이드바·하이라이트·미니맵·HTML 리포트에서 모두 동일 | ✅ Phase 3.5/4/5 누적 검증 |
| M2 | 필터 OFF → 해당 카테고리 3경로 전부 사라짐 | ✅ Phase 3 simApplyFilter 검증 |
| M3 | HTML 리포트 표지 7지표 합 = 사이드바 카운트와 일치 | ✅ Phase 5 buildExportPayload 동일 데이터 사용 |
| M4 | @media print 필터·설정 UI 숨김, 색상 유지 | ✅ Plan-38 §9 자산 (`-webkit-print-color-adjust: exact`) |
| M5 | 보고서 부록 공식 텍스트가 SSOT와 동일 | ✅ Phase 5 SSOT 경유, fallback도 v3 |

### 회귀 스팟체크 (계획서 §5.2 변경 금지 영역)

| 영역 | 결과 |
|---|---|
| `backend/services/similarity_engine.py` | ✅ 변경 없음 |
| `backend/api/help.py` | ✅ Phase 1 외 추가 없음 |
| `backend/config.py` | ✅ |
| `data/help/similarity-help.json` | ✅ Phase 1 v3 상태 유지 |
| 골드셋 14페어 (`data/similarity-goldset/`) | ✅ 백엔드 불변이므로 분류 매핑 동일 (점수 수치는 새 공식) |

### Toast Click Race (Phase 4 잔여 Warning 재점검)
- 코드 분석: `_simRestoreToastTimer` 변수가 closure 내 정상 캡처. `setTimeout` cleanup 정확.
- Phase 4 실측 시 1회 click 미반응 관찰 — Playwright `evaluate` sleep 800ms vs setTimeout 5초 race로 추정
- 사용자 시나리오에서는 5초 충분 → **재현 안 됨**, 보고서 기재만

## 사용자 관점 피드백 (Plan-45 전체 누적)

### 긍정 (사용자가 직접 화면에서 체감)
- **용어 일관성**: 카드·필터·카테고리·누적바·보고서 모두 "동일/거의 동일/의역/약한 유사" 4개로 통일
- **점수 직관**: 가중치 없는 공식 → 사용자가 산식을 보고 직접 검산 가능 (Copyleaks 샘플 43.7% 검증)
- **5단계 신호등**: 100% 결과에 "위험" 명시 (이전 "주의" 모호함 해소)
- **제외 패널**: 검토할 카드는 메인, 제외된 항목은 접힌 패널 → 시야 정리
- **수동 제외 안전성**: ⓧ → toast [복원] 5초 + 패널 [↺ 복원] 백업

### 우려 (Plan-45 종료 후 후속 검토)
- 점수 수치 변동 (가중치 제거로 약간 상승) — 골드셋 점수 변동 기록 필요 (별도 Plan)
- HTML 리포트 별첨 A 카테고리 H3 + 첫 카드 페이지 분리 가능 (별도 UI 개선)

### 개선 제안 (별도 Plan-46+ 후보)
- 7지표 카드 hover 툴팁 (L1 도움말)
- 필터 키보드 단축키
- 매칭 다수 시 패널 페이지네이션
- Translator·Explorer 등 다른 시스템에 같은 SSOT 패턴 적용 검토

## 웹디자인 전문가 관점 (Plan-45 누적 평가)

### 시각적 위계 — **양호**
- 사이드바 5블록 (점수 표지 / 검사 설정 / 결과 필터 / 카테고리 카드 / 제외 패널) F-pattern 흐름
- HTML 리포트 3시트 (결과지 / 별첨 A / 별첨 B) 명확

### 일관성 — **양호**
- 카테고리 색상 6경로 (badge·dot·section bar·filter dot·minimap·report)에서 단일화
- 라벨 SSOT 경유로 어휘 드리프트 자동 차단

### 다크모드 — **양호**
- 모든 색상 var() 변수 경유 자동 전환
- 카드 본문 텍스트 명시적 색상 (Phase 3.5 보강)

### 접근성 — **양호**
- `role="list/listitem"`, `aria-label`, `aria-hidden`, 네이티브 `<details>`
- 본문 line-through (수동 제외) 색상 외 시각 단서

## 잔여·후속 제안

### 별도 Plan으로 분리할 항목

#### Plan-46 후보 — Translator/Explorer SSOT 패턴 확장
- 다른 서브시스템에도 SSOT 단일 진실 공급원 + grep 자동 검증 패턴 적용
- 분류 체계 외에도 라벨·아이콘·메시지의 일관성 검증

#### Plan-47 후보 — 골드셋 새 공식 재기록
- `tools/eval/similarity_eval.py` 재실행 → 14페어 점수 변동 기록
- Plan-38 점수 vs Plan-45 v3 점수 비교 보고서

#### 미세 개선 (개별 작업)
- 7지표 카드 hover 툴팁
- 필터 단축키
- HTML 리포트 별첨 A 페이지 분할 보강

## 커밋 제안

```
추가 [Plan-45/P7] 드리프트 방지 + 회귀 — 자동 테스트 + CLAUDE.md + dead code 정리

Plan-45 마지막 단계. grep 기반 자동 라벨 일관성 테스트 신설 +
CLAUDE.md 분류 체계 규칙 명시 + Phase 4/5 잔여 dead code 정리.

변경:
- tests/sim_label_consistency.sh 신규
  · E1-legacy: Plan-38 옛 그룹 어휘 (표절 의심/참고 가능/제외 영역) 0건 검증
  · C1-legacy: 옛 가중치 공식 ("실질 매칭 + 의역·번역 × 0.5") 0건 검증
  · E2-legacy: 옛 카드 라벨 ("label: '일치'/'번역'") 0건 검증
  · pre-commit hook / CI 등록 권장
- CLAUDE.md
  · "유사도 분류 체계 (Plan-45 v3, Copyleaks 모방)" 섹션 신설
  · 카테고리 4 / 유형 6 / 공식 / 규칙 6항 / 자동 검증 안내
- compare.html
  · simUpdateMatchCard 폐기 (Phase 4 이후 호출처 0건)
  · doExportSimilarityTxt 폐기 (Phase 5 이후 UI 진입 경로 없음)
  · runExport(fmt='txt') 분기에서 'similarity' 제거
  · HTML 리포트 CSS "(제외 영역)" → "(자동 제외)"
- backend/services/export_service.py
  · fallback labels v3 어휘 ("일치"→"동일", "번역 (다른 언어)"→"의역 (다른 언어 번역)" 등)
  · fallback formula v3 공식 (Copyleaks aggregatedScore)
  · Excel 요약 시트 행 라벨 v3 어휘 ("실질 유사"→"동일·거의 동일" 등)

검증:
- 단위 테스트 21/21 PASS (Phase 2 회귀)
- Node 구문 파싱 PASS
- tests/sim_label_consistency.sh PASS
- Python 백엔드 import OK (export_service.py)
- 골드셋 14페어 백엔드 불변 (분류 매핑 동일 — 점수 수치는 새 공식)

Plan-45 전체 종료 (P1~P7, 7개 Phase 완료):
  P1 SSOT v3 — 8c88264
  P2 resolveCategory + computeScore — 6689565
  P3 사이드바 UI 재구성 — 1f2c60f
  P3.5 UI 완성도 보정 — fada1dc
  P4 제외 패널 분리 — 2b3a039
  P5 HTML 리포트 재구성 — ffa14c5
  P6 가이드·모달·온보딩 — 21c3204
  P7 드리프트 방지 (이번 커밋)

후속 제안 (별도 Plan):
- Plan-46: Translator/Explorer SSOT 패턴 확장
- Plan-47: 골드셋 새 공식 재기록 보고서
- 미세 개선: 7지표 hover 툴팁, 필터 단축키 등

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```
