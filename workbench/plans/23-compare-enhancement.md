# Plan-23: Verify(Compare) 시스템 고도화

> **작성일**: 2026-04-01
> **최종 갱신**: 2026-04-04 (Phase 4 Step 1 완료)
> **상태**: Phase 4 Step 1 완료, Phase 5 대기
> **관련**: `compare.html`, `backend/api/compare.py`, `backend/services/compare_service.py`
> **선행 문서**: `docs/11-COMPARE-SYSTEM.md`, `docs/research-semantic-comparison.md`

---

## 진행 현황

| Phase | 설명 | 태스크 | 완료 | 상태 |
|:-----:|------|:------:|:----:|:----:|
| 0 | 모드 선택 허브 + 이탈 방지 | 7 | 7 | ✅ 완료 |
| 1 | 유사도 검사 (핵심) | 13 | 13 | ✅ 완료 |
| 2 | 내보내기 확장 | 7 | 7 | ✅ 완료 |
| 3 | 규칙 검증 고도화 + 인텔리전스 패널 | 8 | 8 | ✅ 완료 |
| 3V | 실효성 검증 (3모드 신뢰도) | 6 | 6 | ✅ 완료 |
| 4 | 서버 이력 (Step 1) | 3 | 3 | ✅ 완료 (Step 2~3은 Phase 5 이후) |
| 5 | 표준 기반 규칙 엔진 (STE + MIL-STD) | 10 | 0 | 3V 완료 후 착수 |

---

## 목표

Compare를 **Verify**로 리브랜딩하고, "두 문서 diff 도구"에서 **문서 품질 게이트**로 확장한다.
유사도 검사(표절 점검), 내보내기 확장, 규칙 고도화를 순차 구현한다.

> 다중 문서 비교 + 문서 생성은 **Author 시스템(Plan-24)**의 책임. Verify는 "검증(판단)"에 집중한다.

---

## 완료된 Phase 요약

### Phase 0: 모드 선택 허브 (7/7 ✅)

| 구현 내용 |
|----------|
| 3모드 카드 허브 (유사도/비교/검증) — 진입점 재설계 |
| 모드별 전용 뷰 전환 + 탭 네비게이션 유지 |
| 이탈 방지 (beforeunload + Home 버튼 확인 모달) |
| 드래그 드롭 → 자동 모드 판별 + 파일 로드 |
| 최근 작업 이력 (localStorage, 최대 10건) |
| **버그픽스**: 초기 로드 시 이력 미표시 — `HISTORY_KEY` var 호이스팅 순서 수정 |

### Phase 1: 유사도 검사 (13/13 ✅)

| 구현 내용 |
|----------|
| 2층 파이프라인: Winnowing L1 (텍스트 매칭) + Semantic L3 (bge-m3 임베딩) |
| 6종 유형 분류: identical, near_copy, paraphrase, translation, low_sim, boilerplate |
| 3-tier 유사율 집계: 실질/의역/공통 — 정형구문 자동 필터링 |
| 백엔드 태깅 HTML + 프론트 하이라이트 (data-sent-idx 기반) |
| 사이드바: 판정 라벨(양호/보통/주의) + 유형별 필터 + 미니맵 + 네비게이션 |
| 관리자 설정 7개 (임계값, Winnow 파라미터, 판정 경계) |
| 파일럿 테스트: L3 임계값 0.70→0.75 튜닝 |

### Phase 2: 내보내기 확장 (7/7 ✅)

| 구현 내용 |
|----------|
| 포맷 선택 모달 (Excel/HTML/TXT) — 사이드바 헤더에 내보내기 버튼 배치 |
| Excel (.xlsx): 백엔드 `export_service.py` (openpyxl), 요약+상세 2시트, 색상 스타일링 |
| HTML 리포트: 프론트엔드 인라인 CSS, @media print 인쇄 최적화 |
| TXT: 3모드 공통 텍스트 리포트 (기존 비교 패턴 확장) |
| API: `POST /api/compare/export` — JSON 페이로드 → .xlsx 스트림 |
| 비교 모드: 미처리 경고 메시지 포맷 모달에 통합 |
| 허브 정리: coming-soon 블록 제거 |

---

## Phase 3: 규칙 검증 고도화 + 문서 인텔리전스 패널

### 3.0 배경

현재 검증 모드는 좌측 패널(문서 본문 + 이슈 하이라이트)만 사용하고 **우측 패널(panel-b)이 `display:none`**으로 숨겨져 있다. 화면 절반이 비어 있고, 검증 결과가 사이드바 이슈 목록에만 표시되어 문서 전체 품질을 한눈에 파악하기 어렵다.

**현재 상태**:
- 6종 규칙: 번호연속, 표캡션, 그림캡션, 금지어, 용어일치, 문장길이
- 점수: penalty(error×10 + warning×3 + suggestion×1) → score = max(0, 100 − penalty/단락수 × 10)
- issue 객체: rule_id, category(structure/terminology/readability), severity, paragraph_index, char_start/end
- 사이드바: SVG 도넛링 스코어 카드 + 카테고리별 이슈 그룹

**해결**: 우측 패널을 **문서 인텔리전스 대시보드**로 활용한다.

```
┌──────────────────┬──────────────────┬────────────────┐
│  문서 본문        │  인텔리전스 패널  │  사이드바       │
│  (이슈 하이라이트) │  ┌─────────────┐ │  이슈 목록     │
│                   │  │평가표│구조│용어│ │  (네비게이션)  │
│                   │  ├─────────────┤ │               │
│                   │  │ 탭별 내용    │ │               │
│                   │  └─────────────┘ │               │
└──────────────────┴──────────────────┴────────────────┘
```

### 3.1 핵심 설계 결정

| 결정 | 이유 |
|------|------|
| **API 통합** — 기존 `validate` 응답에 structure/requirements/terms 추가 | 프론트 fetch 1회, 백엔드 내부 병렬, 기존 호환 유지 |
| **스코어 카드 패널 이동** — 사이드바 → 인텔리전스 패널 탭 1 | 사이드바는 이슈 목록 전용으로 단순화, 정보 중복 제거 |
| **영어 패턴 우선** | 주 시나리오(영문 스펙) 집중, 한국어는 후속 확장 |
| **탭 전환은 프론트 전용** | 탭마다 API 호출하지 않음, 한 번 받은 데이터를 탭별 분배 |

### 3.2 인텔리전스 패널 — 탭 1: 평가표 (Scorecard)

기존 사이드바 스코어 카드를 이동 + 확장:

| 항목 | 내용 |
|------|------|
| 전체 등급 | A/B/C/D 등급 + 점수 (도넛 링 확장) |
| 항목별 체크 | 규칙별 ✅/⚠️/❌ + 건수 |
| 심각도 분포 | 오류/경고/제안 비율 바 차트 |
| 카테고리별 점수 | 구조 / 용어 / 가독성 각각 점수 |

> 기존 validate 데이터(score, summary, issues)만으로 즉시 구현 가능.

### 3.3 인텔리전스 패널 — 탭 2: 문서 구조 (Structure)

| 항목 | 내용 | 데이터 소스 |
|------|------|-----------|
| 장/절/항 트리 | 헤딩 기반 문서 구조 트리 (클릭 시 좌측 패널 이동) | 백엔드 신규 |
| 섹션별 분량 | 각 섹션의 단락/문장 수, 상대 비율 바 | 백엔드 신규 |
| 요구사항 분류 | shall/should/may/information/test_condition 통계 | 백엔드 신규 |
| 표/그림 번호 | 자동 감지된 표/그림 목록 + 번호 체계 검증 | 기존 규칙 확장 |

**요구사항 문장 분류 기준** (영어 우선):

| 분류 | 키워드 패턴 | 의미 |
|------|-----------|------|
| shall | shall, must, is required to | 필수 요구사항 |
| should | should, is recommended | 권고 |
| may | may, is permitted | 허용 |
| information | is, are, was (서술문) | 정보 서술 |
| test_condition | under the condition, test at | 시험 조건 |

### 3.4 인텔리전스 패널 — 탭 3: 용어/참조 (Terminology)

| 항목 | 내용 |
|------|------|
| 규격 번호 목록 | 자동 추출 (MIL-STD-xxx, AS xxxx 등) + 출현 횟수 |
| 약어 목록 | 문서 내 약어 + 최초 정의 위치 (있으면) |
| 단위 표기 | 사용된 단위 목록 + SI 단위 준수 여부 |

> 용어 일관성 검사는 기존 규칙(inconsistent_terms)에서 이미 처리. 여기서는 추출·표시에 집중.

### 3.5 백엔드 확장

기존 `POST /api/compare/validate` 응답을 확장한다:

```json
{
  "score": 71,
  "summary": { "error": 1, "warning": 3, "suggestion": 1 },
  "issues": [ ... ],
  "structure": {
    "headings": [ { "level": 1, "text": "Introduction", "paragraph_index": 0, "sentence_count": 5 } ],
    "sections": [ { "heading": "...", "paragraph_count": 10, "sentence_count": 45 } ],
    "figures": [ { "number": 1, "caption": "...", "paragraph_index": 15 } ],
    "tables": [ { "number": 1, "caption": "...", "paragraph_index": 20 } ]
  },
  "requirements": {
    "shall": 12, "should": 3, "may": 5, "information": 20, "test_condition": 2,
    "details": [ { "type": "shall", "text": "...", "paragraph_index": 5 } ]
  },
  "terms": {
    "specifications": [ { "id": "MIL-STD-461G", "count": 8, "first_index": 2 } ],
    "abbreviations": [ { "abbr": "EMC", "definition": "Electromagnetic Compatibility", "first_index": 1 } ],
    "units": [ { "unit": "kHz", "count": 5, "si_compliant": true } ]
  }
}
```

> 기존 클라이언트는 `score`, `summary`, `issues`만 사용하므로 하위 호환 유지.

### 3.6 구현 순서

| # | 태스크 | 설명 | 난이도 | 의존 | 상태 |
|---|--------|------|--------|------|------|
| 3a | 인텔리전스 패널 UI 프레임 | panel-b 활성화, 3탭 구조, 빈 탭 placeholder | 중 | — | ✅ |
| 3b | 평가표 탭 | 스코어 카드 패널 이동 + 등급 + 카테고리별 점수 + 규칙 체크리스트 | 중 | 3a | ✅ |
| 3c | 백엔드: 구조 분석 | validate 응답에 structure 추가 (헤딩 트리, 섹션 분량, 표/그림) | 중 | — | ✅ |
| 3d | 백엔드: 요구사항 분류 | validate 응답에 requirements 추가 (shall/should/may 통계) | 중 | — | ✅ |
| 3e | 구조 탭 (프론트) | 헤딩 트리 + 분량 바 + 요구사항 통계 + 표/그림 목록 | 중 | 3a, 3c, 3d | ✅ |
| 3f | 백엔드: 용어/규격 추출 | validate 응답에 terms 추가 (규격번호, 약어, 단위) | 중 | — | ✅ |
| 3g | 용어 탭 (프론트) | 규격 목록 + 약어 + 단위 표기 | 중 | 3a, 3f | ✅ |
| 3h | 내보내기 반영 + 테스트 | 인텔리전스 데이터를 Excel/HTML/TXT에 반영, 통합 테스트 | 하 | 3b~3g | ✅ |

> **3i (KAI 지침 규칙)**: 보류 — 사내 지침 확정 후 프레임워크로 추가.

### 3.7 구현 흐름

```
3a~3g: 완료
 ↓
3h: 내보내기 반영 + 통합 테스트
 ↓
Phase 3V: 실효성 검증 (Phase 4 착수 전 필수)
```

---

## Phase 3V: 실효성 검증 (Phase 3h 완료 후)

### 3V.1 배경

Phase 3까지 구현된 3모드(비교/유사도/검증)의 분석 결과가 **실제로 신뢰할 수 있는지** 검증한다.
시각적으로 그럴듯하지만 실질적 근거가 약한 항목을 식별하여 개선하거나 제거한다.

> Phase 4(세션 영속화)에서 결과를 저장하기 전에 반드시 수행해야 한다.
> 신뢰할 수 없는 결과를 영속화하면 문제가 확대된다.
> Phase 5(표준 기반 규칙)의 우선순위 결정에도 3V 진단 결과가 입력이 된다.

### 3V.2 모드별 현재 신뢰도 평가

| 모드 | 핵심 알고리즘 | 신뢰도 | 근거 |
|------|-------------|:------:|------|
| **비교** | jsdiff (단어 수준 diff) | **높음** | 업계 표준, 수백만 다운로드, 오탐 없음 |
| **유사도** | Winnowing L1 + bge-m3 L3 | **중상** | MOSS(Stanford) 표절 검출 표준 + 검증된 다국어 임베딩 |
| **검증 — 규칙 6종** | 정규식 패턴 매칭 | **중하** | 작동하지만 깊이 얕음, 다양한 문서 형식 미대응 |
| **검증 — 점수/등급** | penalty/단락수 × 스케일링 | **낮음** | 통계적 근거 없는 임의 공식 |
| **검증 — 요구사항 분류** | shall/should/may 키워드 | **높음** | INCOSE 가이드와 일치하는 업계 방법론 |
| **검증 — 구조 분석** | "N. Title" 정규식 | **중** | 번호 형식 한정, Word 스타일 기반 미감지 |
| **검증 — 용어 추출** | 규격번호/약어/단위 정규식 | **중상** | 규격번호는 정확, 약어 오탐 가능성 있음 |

### 3V.3 검증 태스크

| # | 태스크 | 설명 | 방법 | 산출물 | 상태 |
|---|--------|------|------|--------|------|
| 3V-a | 업계 스코어링 조사 | SonarQube, 카피킬러, HyperSTE 등의 점수 산출 방식 조사 | 웹 리서치 + 문서 분석 | 스코어링 비교표 + 개선안 | ✅ |
| 3V-b | 점수 공식 개선 + 코드 반영 | 3V-a 결과 기반으로 penalty 공식, 카테고리 스케일링 개선 | 코드 수정 | 개선된 `validate_paragraphs()` | ✅ |
| 3V-c | 테스트 문서셋 구성 | 공개 MIL-STD 2~3건 텍스트화, 기대 결과 수동 라벨링 | ASSIST에서 DL + 수작업 | `tests/verify/` 테스트 데이터 | ✅ |
| 3V-d | 규칙·구조·용어 정확도 측정 | 테스트셋 대비 precision/recall 측정, 오탐·미탐 분류 | 테스트 스크립트 실행 | 모드별 정확도 보고 | ✅ |
| 3V-e | 유사도 경계 케이스 검증 | 빈 문서, 긴 문서, 특수문자, L3 임계값 0.75 재검증 | 엣지 케이스 테스트 | 임계값 조정 여부 결정 | ✅ |
| 3V-f | 종합 진단 보고서 | 겉보기 vs 실질 갭 정리, 개선/제거 판단, Phase 5 우선순위 입력 | 분석 문서화 | `workbench/plans/3v-report.md` | ✅ |

### 3V.4 산출물

- 종합 진단 보고서: `workbench/plans/3v-report.md`
- 개선된 점수 공식 (코드 반영 완료 — Acrolinx density 방식)
- 테스트 문서셋: `tests/verify/test_scoring.py` (3종, Phase 5 회귀 테스트 재사용)
- Phase 5 우선순위 권고: STE 작성 규칙 > MIL-STD 구조 규칙 > 약어 패턴 확장

### 3V.5 핵심 결론

> 점수 공식과 기존 규칙의 **정확도는 확보**되었으나(87.5%, 오탐 0%), 규칙 6종 자체가 **포맷 검사 수준**에 머물러 있어 검증 모드의 실질적 가치는 Phase 5(STE/MIL-STD 규칙)에 의존한다.
> Phase 4 세션 영속화보다 **Phase 5 규칙 깊이 확보를 선행**해야 한다.

---

## Phase 4: 세션 관리 + 이력

### 4.0 3V 진단 결과에 따른 진행 방침

Phase 3V 검증 결과, 현재 검증 결과는 **저장할 가치가 있는 수준**으로 확인됨 (점수 공식 업계 근거 확보, 규칙 정확도 87.5%, 오탐률 0%).

단, 규칙 6종 자체가 **문서 포맷 검사 수준**이므로(번호·캡션·문장길이), Phase 5(STE/MIL-STD)에서 실질적 작성 품질 규칙이 추가되어야 검증 모드의 진정한 가치가 생긴다.

**진행 방침**:
- Phase 4는 **Step 1(이력 표시)만 경량 구현** → 사용자 워크플로우 기반 마련
- Step 2~3(결과 재열람, 참조 라이브러리)은 **Phase 5 이후로 보류** — 얕은 규칙 결과를 저장·재열람하는 것보다, 규칙 깊이를 먼저 확보하는 게 우선
- Phase 5 완료 후 Step 2~3 진행 시 저장 가치가 높은 결과를 영속화

### 4.1 배경

현재 Verify는 완전 무상태(휘발성). 검증 결과는 브라우저 세션이 끝나면 사라진다.

**채택 모델**: 카피킬러 기반 — 검사 완료 시 자동 저장, 이력에서 재열람 가능. 3단계로 점진 구현.

### 4.2 Step 1: 서버 이력 (이번 Phase 범위)

- 저장: `data/verify/{username}/_history.json` (요약 정보만, 최대 10건 FIFO)
- 허브 UI: 기존 localStorage 이력을 서버 API로 전환
- 각 모드 결과 완료 시 자동 저장
- API: `GET/POST /api/verify/history`

### 4.3 구현 순서

| # | 태스크 | 난이도 | 상태 |
|---|--------|:------:|------|
| 4a | 백엔드: 이력 저장/조회 API | 하 | ✅ |
| 4b | 프론트: localStorage → API fetch 전환 | 중 | ✅ |
| 4c | 각 모드 결과 후 이력 자동 저장 연동 | 하 | ✅ |

### 4.4 Step 2~3: Phase 5 이후 진행 (보류)

> **보류 사유**: 3V 진단 결과, 현재 규칙 6종은 포맷 검사 수준. 얕은 결과를 영속화·재열람하기보다 Phase 5에서 규칙 깊이를 확보한 후 진행하는 게 효과적.

| # | 태스크 | 난이도 | Step | 상태 |
|---|--------|:------:|:----:|------|
| 4d | 백엔드: 세션 저장/로드/삭제 API | 중 | 2 | 보류 |
| 4e | 프론트: 이력 클릭 → 결과 재열람 | 상 | 2 | 보류 |
| 4f | 세션 용량 관리 (자동 삭제, 관리자 설정) | 하 | 2 | 보류 |
| 4g | 백엔드: 참조 문서 라이브러리 API | 중 | 3 | 보류 |
| 4h | 프론트: 라이브러리 UI | 중 | 3 | 보류 |

---

## Phase 5: 표준 기반 규칙 엔진 (ASD-STE + MIL-STD)

### 5.1 배경

Phase 3의 자체 규칙 6종은 작동하지만 **업계 표준 근거가 없다**. Phase 3V 진단에서 "깊이 얕음"으로 평가된 부분의 근본 해결책으로, 국제/방산 기술문서 표준에 기반한 규칙 엔진을 구축한다.

**대상 표준**:

| 표준 | 성격 | 입수 | 규칙 유형 |
|------|------|:----:|----------|
| **ASD-STE100** | 통제 영어 (Simplified Technical English) | 유료 (핵심 규칙은 공개 논문에서 확보 가능) | 문장 수준 작성 품질 |
| **MIL-STD-38784** | 기술교범(TM) 작성 요구사항 | 무료 (ASSIST/DLA) | 문서 구조·포맷 |
| **MIL-STD-961** | 규격서(specification) 작성 양식 | 무료 (ASSIST/DLA) | 섹션 순서·필수 항목 |
| **MIL-HDBK-1222** | TM 작성 가이드 (38784 해설서) | 무료 (ASSIST/DLA) | 구현 참고자료 (직접 규칙화 X) |

> **핵심 전략**: STE = 문장 품질, MIL-STD = 문서 구조 품질. 두 축을 결합하면 현재 자체 규칙의 상위 호환.

### 5.2 아키텍처 — 데이터 주도 규칙 엔진

현재: 규칙이 Python 코드에 하드코딩 (6개 함수).
목표: **규칙 정의를 데이터(JSON)로 분리**, 엔진은 정의를 로드하여 실행.

```
backend/rules/                     ← 규칙 정의 (데이터)
  ├── _schema.json                 ← 규칙 JSON 스키마
  ├── ste-writing.json             ← STE 작성 규칙 (~15개)
  ├── mil-structure.json           ← MIL-STD 구조 규칙 (~10개)
  └── custom.json                  ← 기존 자체 규칙 (마이그레이션)

backend/services/rule_engine.py    ← 스키마 기반 규칙 실행 엔진
  ├── load_rules(category)         ← JSON 로드 + 검증
  ├── match_rule(rule, paragraph)  ← 개별 규칙 매칭
  └── run_all(paragraphs, rules)   ← 전체 실행 + 결과 집계
```

**규칙 정의 스키마 (예시)**:
```json
{
  "id": "ste-sentence-length",
  "source": "ASD-STE100",
  "source_rule": "Rule 1.1",
  "category": "readability",
  "severity": "warning",
  "name_ko": "문장 길이 제한",
  "name_en": "Sentence Length Limit",
  "description": "절차문은 20단어, 설명문은 25단어를 초과하면 안 된다",
  "type": "sentence_metric",
  "params": {
    "max_procedural": 20,
    "max_descriptive": 25
  },
  "enabled": true
}
```

이렇게 하면:
- 규칙 추가/수정에 코드 변경 불필요 (JSON만 편집)
- 프리셋 + 개별 토글로 사용자가 규칙 ON/OFF 가능 (5i에서 구현)
- 사내 지침(KAI 등) 추가도 JSON 파일 하나 추가로 해결

**규칙 설정 UI 설계 — 프리셋 + 개별 오버라이드** (Acrolinx/SonarQube 방식):

```
┌─ 검증 설정 ──────────────────────────────────────┐
│ 프리셋  ▼ MIL-STD-461 검증용                      │
│         ──────────────────                        │
│          MIL-STD-461 검증용  (STE + 961 구조)     │
│          기술 교범 (TM) 작성  (STE + 38784)       │
│          일반 기술문서        (STE만)              │
│          커스텀              (전부 수동 선택)       │
│                                                   │
│ ☑ ASD-STE 작성 규칙                               │
│   ☑ 문장 길이 제한    ☑ 수동태 감지               │
│   ☑ 명사 클러스터     ☑ 이중 부정 금지            │
│   ☑ 한 문장 한 지시   ☑ 불명확 표현               │
│ ☑ MIL-STD 구조 규칙                               │
│   ☑ 필수 섹션 검증    ☑ 섹션 순서 검증            │
│   ☑ 그림/표 번호 형식  ☐ 경고문 배치 ← OFF        │
│ ☑ 기존 규칙 (자체)                                │
│   ☑ 번호 연속성       ☑ 금지 용어                 │
└───────────────────────────────────────────────────┘
```

- 프리셋 선택 → 해당 표준의 규칙 일괄 ON/OFF
- 개별 체크박스 → 프리셋 위에 사용자 오버라이드 (프리셋은 "커스텀"으로 변경됨)
- 기존 검증 모드 ⚙ 설정 버튼에 통합 (현재 6종 규칙 설정 UI 확장)
- 설정은 `compare-rules.json`의 기존 프리셋 구조를 확장하여 저장

### 5.3 구현 단계

#### Step 1: 표준 문서 수집 + 규칙 카탈로그 (리서치, 코드 없음)

MIL-STD는 ASSIST에서 다운로드, STE는 공개 학술 자료에서 핵심 규칙 수집.
각 규칙을 **자동화 가능성** 기준으로 3등급 분류:

| 등급 | 의미 | 예시 |
|:----:|------|------|
| A | 정규식/통계로 완전 자동화 | 문장 길이, 수동태, 번호 형식 |
| B | 휴리스틱으로 부분 자동화 (오탐 가능) | 명사 클러스터, 약어 첫사용 검증 |
| C | 사람 판단 필요 (자동화 부적합) | "기술적으로 정확한가", "그림이 내용과 일치하는가" |

**산출물**: 규칙 카탈로그 (`workbench/plans/rule-catalog.md`) — 전체 규칙 목록 + 등급 + 우선순위

#### Step 2: 규칙 스키마 + 엔진 아키텍처

- 규칙 JSON 스키마 설계 (`backend/rules/_schema.json`)
- 규칙 엔진 코어 구현 (`backend/services/rule_engine.py`)
- **기존 6종 규칙을 새 스키마로 마이그레이션** (하위 호환 유지)
- 기존 `validate_paragraphs()`가 새 엔진을 호출하도록 리팩터

#### Step 3: STE 작성 규칙 구현 (Priority 1 — 영향력 최대)

기존 규칙과 겹치는 것은 업그레이드, 나머지는 신규:

| # | 규칙 | 현재 상태 | 작업 |
|---|------|----------|------|
| 1 | 문장 길이 제한 (절차 20 / 설명 25단어) | `sentence_length` 존재 (단일 임계값) | 업그레이드: 절차/설명 구분 |
| 2 | 수동태 감지 | 없음 | 신규: be + past participle 패턴 |
| 3 | 명사 클러스터 제한 (연속 명사 3개 이하) | 없음 | 신규: POS 없이 휴리스틱 |
| 4 | 한 문장 한 지시 (절차문) | 없음 | 신규: and/or + 동사 패턴 |
| 5 | 이중 부정 금지 | 없음 | 신규: not + un-/in- 패턴 |
| 6 | 불명확 표현 경고 | `forbidden_words` 존재 (임의 목록) | 업그레이드: STE 비승인 목록 기반 |
| 7 | 동명사 시작 금지 (절차문) | 없음 | 신규: -ing로 시작하는 문장 |

#### Step 4: MIL-STD 구조 규칙 구현 (Priority 2)

| # | 규칙 | 출처 | 작업 |
|---|------|------|------|
| 1 | 필수 섹션 존재 검증 | MIL-STD-961 §4 | SCOPE/APPLICABLE DOCS/REQUIREMENTS 등 필수 섹션 누락 검사 |
| 2 | 섹션 순서 검증 | MIL-STD-961 §4 | 표준 섹션 순서 위반 검사 |
| 3 | 그림/표 번호 형식 | MIL-STD-38784 | 섹션-순번 형식(Figure 3-1) 준수 여부 |
| 4 | 약어 첫사용 전개 | MIL-STD-38784 §5.9 | 약어 최초 등장 시 풀어쓰기 여부 |
| 5 | 경고/주의문 배치 | MIL-STD-38784 §5.7 | WARNING/CAUTION이 해당 절차 앞에 위치하는지 |
| 6 | 참조 문서 유효성 | MIL-STD-961 §4.2 | APPLICABLE DOCUMENTS 섹션 내 문서가 본문에서 참조되는지 |

#### Step 5: 스코어링 체계 개편

현재 임의 penalty 공식을 표준 근거 기반으로 교체:

```
현재:  score = max(0, 100 - (penalty / paragraphs) × 10)
       penalty = error×10 + warning×3 + suggestion×1

개선:  규칙별 가중치를 표준 출처 + severity로 결정
       카테고리별 독립 점수 (구조 / 작성 / 용어)
       종합 점수 = 가중 평균 (3V-a 조사 결과 반영)
```

#### Step 6: 검증 + 캘리브레이션

- 3V-c에서 구축한 테스트 문서셋으로 회귀 테스트
- 오탐률(false positive) 목표: < 15%
- 인텔리전스 패널에 규칙 출처 표시 (예: "ASD-STE Rule 1.1")

### 5.4 구현 순서

| # | 태스크 | 설명 | 난이도 | 의존 | 상태 |
|---|--------|------|--------|------|------|
| 5a | 표준 문서 수집 | MIL-STD DL + STE 공개 규칙 수집 | 하 | — | ⬜ |
| 5b | 규칙 카탈로그 작성 | 전체 규칙 목록 + 자동화 등급(A/B/C) + 우선순위 | 중 | 5a | ⬜ |
| 5c | 규칙 JSON 스키마 설계 | 규칙 정의 데이터 구조 확정 | 중 | 5b | ⬜ |
| 5d | 규칙 엔진 코어 | `rule_engine.py` — 스키마 기반 로더 + 매처 + 리포터 | 상 | 5c | ⬜ |
| 5e | 기존 6종 마이그레이션 | 하드코딩 규칙 → JSON 정의로 전환, 하위 호환 | 중 | 5d | ⬜ |
| 5f | STE 작성 규칙 구현 | Priority 1: 7개 규칙 (Step 3) | 상 | 5d | ⬜ |
| 5g | MIL-STD 구조 규칙 구현 | Priority 2: 6개 규칙 (Step 4) | 상 | 5d | ⬜ |
| 5h | 스코어링 개편 | 표준 근거 기반 가중치 + 카테고리별 독립 점수 | 중 | 5f, 5g | ⬜ |
| 5i | 규칙 설정 UI + 패널 연동 | 프리셋+개별 토글 설정 UI, 규칙 출처 표시, 카테고리 확장 | 상 | 5h | ⬜ |
| 5j | 검증 + 캘리브레이션 | 테스트셋 회귀, 오탐률 측정, 임계값 튜닝 | 중 | 5i | ⬜ |

### 5.5 Phase 순서 관계 (3V 진단 결과 반영)

```
Phase 3V (완료) → 진단: "규칙 6종은 포맷 검사 수준, 깊이 부족"
                      ↓
              Phase 4 Step 1 (이력 표시) — 경량, 빠르게 처리
                      ↓
              Phase 5 (표준 규칙) — 핵심 가치, 무게 중심
                      ↓
              Phase 4 Step 2~3 (결과 재열람/라이브러리) — 깊은 규칙 결과를 영속화
```

> **3V 결론**: 현재 규칙은 정확하지만 범위가 좁다 ("맞춤법 검사기 정확도 100%"와 유사).
> Phase 5에서 STE 작성 규칙 + MIL-STD 구조 규칙이 추가되어야 "이 도구가 진짜 도움이 된다"는 사용자 체감이 생긴다.
> 따라서 Phase 4 전체 완성보다 **Phase 5 선행**이 전략적으로 옳다.

---

## 부록

### 리브랜딩 (Compare → Verify)

| 항목 | 상태 |
|------|:----:|
| 런처 카드 제목/설명, 헤더 타이틀, 스위처 라벨, `<title>` | ✅ |
| HTML/CSS/API 파일명 rename (compare → verify) | 보류 |

### 설정 (config.py)

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `VERIFY_SIMILARITY_THRESHOLD_HIGH` | `0.85` | 높은 유사 임계값 |
| `VERIFY_SIMILARITY_THRESHOLD_MEDIUM` | `0.75` | 중간 유사 임계값 |
| `VERIFY_SIMILARITY_WINNOW_K` | `25` | Winnow K 파라미터 |
| `VERIFY_SIMILARITY_WINNOW_WINDOW` | `4` | Winnow 윈도우 크기 |
| `VERIFY_SIMILARITY_VERDICT_LOW` | `30` | 양호/보통 경계 |
| `VERIFY_SIMILARITY_VERDICT_HIGH` | `60` | 보통/주의 경계 |
| `VERIFY_SIMILARITY_EMBEDDING_BATCH` | `64` | 임베딩 배치 크기 |

### 기술문서 표준 참조 (Phase 5)

| 표준 | 정식 명칭 | 입수처 |
|------|----------|--------|
| ASD-STE100 | Simplified Technical English | ASD (유료), 핵심 규칙은 학술 논문에서 공개 확인 가능 |
| MIL-STD-38784 | Standard Practice for Technical Manuals | ASSIST (quicksearch.dla.mil) 무료 |
| MIL-STD-961 | Defense and Program-Unique Specifications Format | ASSIST 무료 |
| MIL-HDBK-1222 | Guide for Technical Manual Preparation | ASSIST 무료 |

> 상용 STE 도구 참고: HyperSTE (Etteplan), Congree Authoring Server, Acrolinx

### Author(Plan-24) 연계

| Verify 기능 | Author 활용 |
|------------|-------------|
| 유사도 검사 | Author 초안을 원문 대비 표절 점검 |
| 규칙 검증 + 인텔리전스 | Author 초안의 작성 지침 준수 검증 |
| 내보내기 | 검증 결과를 Excel/HTML 리포트로 |

---

*작성: 2026-04-01 · 최종 갱신: 2026-04-04*
