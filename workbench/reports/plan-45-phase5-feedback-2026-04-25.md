# Plan-45 Phase 5 실행 피드백 — HTML 리포트 재구성

> 실행일 2026-04-25 · 실행자 Claude (/plan-execute) · 대상 `workbench/plans/45-similarity-label-unification.md` Phase 5 단독

## 요약
- 완료 Step: 6 / 6
- 변경 파일: 1개 (`compare.html`) — CSS·백엔드 무관
- 단위 테스트: **21/21 PASS** (Phase 2 회귀 유지)
- Phase 3.5 TODO 청산 완료 (typeMeta SSOT 경유)
- Critical 0건 · Warning 0건 · Suggestion 2건 (Phase 6/7 후속)

## 구현 결과

| Step | 상태 | 핵심 변경 |
|------|------|----------|
| 1 | ✅ | 유사도 모드 export 모달에서 Excel·TXT 버튼 제거 (PDF + HTML 2개만 노출). 다른 모드는 4종 유지 |
| 2 | ✅ | `typeMeta` 하드코딩 폐기 → SSOT `simHelp.categories.*.ko` 경유 (`catReportMeta`) |
| 3 | ✅ | "③ 매칭 분류 분포" 재구성: 4 카테고리 + 자동/수동 제외 행, SSOT 라벨, 카테고리 색상 일관 |
| 4 | ✅ | 점수 카드 `tiers.substantive/derived` 메타라인 폐기 (Plan-45 v3 폐기 항목) |
| 5 | ✅ | 별첨 A 매칭 상세 — 카테고리별 H3 그룹 (사이드바와 일관), 좌측 카테고리 색바 |
| 6 | ✅ | 자가검증 — 단위 테스트·구문 파싱·grep 검증·Playwright 모달 검증 |

## 핵심 변경 상세

### 1. Export 모달 단순화 (Plan-45 §4.3 적용)

```
유사도 모드:
  [PDF (인쇄·배포용) 권장]   ← btn-primary
  [HTML (웹뷰 — 인쇄 외 용도)]  ← btn-secondary

다른 모드 (compare/verify):
  [PDF] [Excel] [HTML] [TXT]  ← 기존 유지
```

- `isSimilarity ? '' : '<button data-fmt="xlsx">'` 분기로 모드별 격리
- 백엔드 `export_service.py` 자체는 **유지** (다른 모드용)

### 2. typeMeta SSOT 경유 (Phase 3.5 TODO 청산)

**Before** (Plan-38 레거시 하드코딩):
```js
var typeMeta = [
    { key: 'identical',   group: '표절 의심',  label: '일치' },
    { key: 'translation', group: '표절 의심',  label: '번역' },
    ...
];
```

**After** (Plan-45 v3 SSOT):
```js
var TYPE_TO_CAT_REPORT = {
    identical: 'identical',
    translation: 'paraphrased',  // ← 의역 통합
    ...
};
var catReportMeta = [
    { key: 'identical',  ko: help.categories.identical.ko, color: '#dc2626' },
    { key: 'paraphrased', ko: help.categories.paraphrased.ko, color: '#2563eb' },
    ...
];
```

→ E1 불변 회복 (SSOT 경유 강제), 라벨 자동 v3 동기.

### 3. ③ 매칭 분류 분포 재구성

**Before**: 6세부 행 × 그룹 컬럼 ("표절 의심/참고 가능/제외 영역")
**After**: 4 카테고리 행 + 제외 분리 (자동/수동), "점수 영향" 컬럼 추가

| 카테고리 | 건수 | 비율 | 점수 영향 |
|---|---|---|---|
| 동일 | N | N% [bar] | 포함 |
| 거의 동일 | N | N% [bar] | 포함 |
| 의역 | N | N% [bar] | 포함 |
| 약한 유사 | N | N% [bar] | 제외 |
| 자동 제외 | N | N% [bar] | 제외 |
| 수동 제외 | N | N% [bar] | 제외 |

- 사이드바 7지표·누적바와 일관된 카운트
- "점수 영향" 컬럼으로 사용자 직관 (low_similarity는 표시되지만 점수 제외)

### 4. 점수 카드 tiers 메타라인 폐기

**Before**:
```
50.0%  검토 필요
       전체 411문장
       실질 X% · 의역·번역 Y% · 정형구문 Z%   ← 폐기 (Plan-45 v3)
       원점수 45% · 수동 제외 1건 반영
```

**After**:
```
50.0%  검토 필요
       전체 411문장
       원점수 45% · 수동 제외 1건 반영        ← 유지 (투명성)
```

→ 카테고리 분포는 ③ 표에서 4 카테고리로 일관 표시.

### 5. 별첨 A 카테고리 그룹핑

**Before**: 모든 매칭이 하나의 리스트 (#1, #2, #3 ...)
**After**: 카테고리별 H3 섹션 + 좌측 색바
```
▌ 동일 (3건)
  [매칭 카드 #1] [매칭 카드 #2] [매칭 카드 #3]
▌ 거의 동일 (5건)
  [매칭 카드 #4] ...
▌ 의역 (8건)
  ...
▌ 약한 유사 (2건)
  ...
▌ 자동 제외 (4건)
  ...
▌ 수동 제외 (1건)
  [매칭 카드 + 제외 사유]
```

→ 사이드바 카드 그룹핑과 일관, 보고서 검토자가 카테고리별 문제 이슈 파악 용이.

## 검증 결과

### 단위 테스트
- Phase 2 회귀: **21/21 PASS**
- Node 구문 파싱: PASS

### Grep 검증

| 검증 | 결과 |
|---|---|
| `TODO(Plan-45/P5)` 잔존 | **0건** (청산 완료) |
| 옛 typeMeta `label: '일치/번역'` | **0건** |
| SSOT `help.categories.identical` 경유 | **있음** ✓ |
| `tiers.substantive/derived` 점수 카드 메타라인 | **0건** (폐기 완료) |

**잔존 (의도된 fallback)**:
- L1284 Modal B fallback formula → Phase 6에서 정리 예정
- L4711 TXT export fallback line → 호출 경로 없음 (UI 버튼 제거됨), Phase 7 dead code 정리
- L5043 HTML 리포트 fallback formula → SSOT 로드 실패 시만 사용

### Playwright 실측

**시나리오**: testbot 로그인 → 유사도 검사 실행 → 내보내기 버튼

**모달 검증 결과**:
```json
{
  "modalOpen": true,
  "buttons": [
    { "fmt": "pdf",  "text": "PDF (인쇄·배포용) 권장", "primary": true },
    { "fmt": "html", "text": "HTML (웹뷰 — 인쇄 외 용도)", "primary": false }
  ]
}
```

✅ 유사도 모드에서 Excel·TXT 버튼 미노출, PDF·HTML 2종만 표시. PDF 권장 표시.

### 회귀 스팟체크 (변경 금지 영역)

| 영역 | 결과 |
|---|---|
| 백엔드 `similarity_engine.py` | ✅ 변경 없음 |
| `data/help/similarity-help.json` | ✅ 변경 없음 |
| 백엔드 `export_service.py` | ✅ 유지 (다른 모드용) |
| 다른 모드 (compare/verify) export 모달 | ✅ Excel/TXT 버튼 그대로 |
| 사이드바 UI | ✅ 영향 없음 |
| simRecomputeFromSettings · resolveCategory | ✅ 변경 없음 |
| 백엔드 `/api/compare/html-to-pdf` (WeasyPrint) | ✅ 유지 |

## 사용자 관점 피드백

### 긍정
- **내보내기 옵션 단순화** — 유사도 모드는 PDF/HTML 2개만 노출. 사용자가 어떤 포맷을 골라야 할지 명확
- **PDF 우선 표시** — "인쇄·배포용 권장" 라벨, btn-primary 스타일로 의도 강조
- **보고서 카테고리 분포** — 사이드바와 같은 4 카테고리 + 제외 행. 일관성 ↑
- **별첨 A 그룹핑** — 동일/거의 동일/의역/약한 유사 + 제외 섹션 분리. 검토자가 카테고리별 문제 카드를 모아서 보기 쉬움

### 우려
- 별첨 A 카테고리 헤더가 페이지 분할 시 카드와 분리될 가능성 (CSS `break-inside: avoid` 매칭 카드만 적용, H3 헤더는 미적용)
- WeasyPrint 변환 결과는 실제 PDF 다운로드해서 확인 필요 — Playwright로 직접 검증 못 함

### 개선 제안
- 별첨 A 카테고리 헤더 + 첫 카드 1쌍은 함께 페이지 유지 (`break-after: avoid`) — 다음 단계에서 검토

## 웹디자인 전문가 관점 (자가 평가)

### 시각적 위계
- **양호**: 결과지 → 별첨 A → 별첨 B 3시트 명확. 결과지 안에서 ① 메타 → ② 점수 → ③ 카테고리 분포 → ④ 출처 → ⑤ 검사 기준 → 면책 흐름 자연스러움
- 별첨 A 카테고리 H3 + 좌측 색바 → 사이드바 sticky 헤더와 같은 시각 언어

### 인터랙션 (모달)
- 유사도 모드: PDF (강조) / HTML (보조) 2 옵션 — 결정 명확
- 다른 모드: 4 옵션 유지 — 회귀 없음

### 다크모드
- HTML 리포트 자체는 인쇄용 라이트 톤 (의도). 사이드바·모달은 var() 변수 자동 전환

### 접근성
- 모달 내 버튼 명확 라벨, SVG 장식 요소
- HTML 리포트 색상 인쇄 보존 (`-webkit-print-color-adjust: exact`)

## 잔여·후속 제안

### Phase 6 (가이드·모달·온보딩) 시
- [ ] Modal B fallback formula (L1284) — SSOT 경유 시 자동 갱신, fallback 텍스트도 v3 공식으로 교체
- [ ] ⓘ 아이콘 4종 정책 통일 (Phase 3.5 후속 체크리스트)

### Phase 7 (드리프트 방지) 시
- [ ] TXT export 함수 (`doExportSimilarityTxt`, L4711) — 호출 경로 제거됐으나 코드 잔존, dead code 정리
- [ ] HTML 리포트 fallback formula (L5043) — SSOT 정합성 검증 (이미 v3 동일)
- [ ] 별첨 A 카테고리 H3 + 첫 카드 페이지 분리 방지

## 커밋 제안

```
추가 [Plan-45/P5] HTML 리포트 재구성 — typeMeta SSOT 경유 + 카테고리 그룹핑

Plan-45 Phase 5: 보고서를 4 카테고리 (Copyleaks 기준) 일관 양식으로
재구성. Phase 3.5 TODO 청산 (typeMeta SSOT 경유) + Excel/TXT UI 폐기.

변경:
- compare.html export 모달 (L4445~4493)
  · 유사도 모드: Excel·TXT 버튼 제거, PDF/HTML 2종만 노출
  · 다른 모드 (compare/verify): 4종 유지 (회귀 방지)
- compare.html buildSimilarityReportHtml (L5019~)
  · ③ 매칭 분류 분포: 6세부 그룹 표 -> 4 카테고리 + 자동/수동 제외 행
    SSOT help.categories.*.ko 경유, 카테고리 색상 일관
    "점수 영향" 컬럼 신설
  · 점수 카드 tiers 메타라인 ("실질 X% · 의역·번역 Y%") 폐기
  · TYPE_TO_CAT_REPORT 매핑 신설 — 6 유형 -> 4 카테고리 통합
  · catReportMeta SSOT 경유로 라벨·색상 자동 동기
  · Phase 3.5 TODO 주석 청산 완료
- compare.html 별첨 A (L5239~)
  · 매칭을 카테고리별 H3 그룹으로 분류 (좌측 색바 + 라벨 + 카운트)
  · 사이드바 카드 그룹핑과 시각 일관
  · 자동 제외 / 수동 제외 별도 섹션

검증:
- 단위 테스트 21/21 PASS (Phase 2 회귀)
- Node 구문 파싱 PASS
- TODO(Plan-45/P5) 잔존 0건 (청산 완료)
- 옛 typeMeta 'label: 일치/번역' 0건
- Playwright 실측: 모달 PDF/HTML 2종만, Excel/TXT 미노출
- 백엔드 export_service.py·SSOT JSON 변경 없음

잔여 (Phase 6~7):
- Phase 6: Modal B fallback formula 갱신 (SSOT 정상 시 자동, fallback 정리)
- Phase 7: TXT export 함수 dead code 정리, 별첨 A 페이지 분할 보강
```
