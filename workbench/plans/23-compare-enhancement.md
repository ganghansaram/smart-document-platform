# Plan-23: Verify(Compare) 시스템 고도화

> **작성일**: 2026-04-01
> **최종 갱신**: 2026-04-04 (Phase 3g 완료)
> **상태**: Phase 3 진행 중 (3a~3g 완료, 3h 잔여)
> **관련**: `compare.html`, `backend/api/compare.py`, `backend/services/compare_service.py`
> **선행 문서**: `docs/11-COMPARE-SYSTEM.md`, `docs/research-semantic-comparison.md`

---

## 진행 현황

| Phase | 설명 | 태스크 | 완료 | 상태 |
|:-----:|------|:------:|:----:|:----:|
| 0 | 모드 선택 허브 + 이탈 방지 | 7 | 7 | ✅ 완료 |
| 1 | 유사도 검사 (핵심) | 13 | 13 | ✅ 완료 |
| 2 | 내보내기 확장 | 7 | 7 | ✅ 완료 |
| 3 | 규칙 검증 고도화 + 인텔리전스 패널 | 8 | 7 | 🔵 진행 중 |
| 3V | 실효성 검증 (3모드 신뢰도) | — | 0 | Phase 3h 후 착수 |
| 4 | 세션 관리 + 이력 | 8 | 0 | 대기 |

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
| 3h | 내보내기 반영 + 테스트 | 인텔리전스 데이터를 Excel/HTML/TXT에 반영, 통합 테스트 | 하 | 3b~3g | ⬜ |

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

## Phase 3V: 실효성 검증 (Phase 3h 완료 후, Phase 4 착수 전)

### 3V.1 배경

Phase 3까지 구현된 3모드(비교/유사도/검증)의 분석 결과가 **실제로 신뢰할 수 있는지** 검증한다.
시각적으로 그럴듯하지만 실질적 근거가 약한 항목을 식별하여 개선하거나 제거한다.

> Phase 4(세션 영속화)에서 결과를 저장하기 전에 반드시 수행해야 한다.
> 신뢰할 수 없는 결과를 영속화하면 문제가 확대된다.

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

### 3V.3 검증 범위

| # | 항목 | 방법 |
|---|------|------|
| 1 | 점수 공식 타당성 | SonarQube, 카피킬러 등 업계 점수 산출 방식 조사 → 공식 개선 또는 근거 확보 |
| 2 | 규칙 감지 정확도 | 실제 방산 문서(MIL-STD 등)로 precision/recall 측정 |
| 3 | 유사도 문장 분할 | 복잡한 문서 구조에서 분할 정확도 검증 |
| 4 | "겉보기 vs 실질" 갭 식별 | 시각적으로 인상적이지만 실질 가치 낮은 항목 → 개선 또는 제거 판단 |
| 5 | 카테고리 점수 스케일링 | 현재 catPenalty × 5 임의 공식 → 의미 있는 스케일링 근거 확보 |

### 3V.4 산출물

- 모드별 신뢰도 보고서 (현재 수준 + 개선 방안)
- 점수 공식 개선안 (근거 포함)
- 개선/제거 대상 항목 목록

---

## Phase 4: 세션 관리 + 이력

### 4.1 배경

현재 Verify는 완전 무상태(휘발성). 검증 결과는 브라우저 세션이 끝나면 사라진다.

**채택 모델**: 카피킬러 기반 — 검사 완료 시 자동 저장, 이력에서 재열람 가능. 3단계로 점진 구현.

### 4.2 구현 로드맵

#### Step 1: 이력 텍스트 표시 (허브 개선)

- 저장: `data/verify/{username}/_history.json` (요약 정보만, 최대 10건 FIFO)
- 허브 UI: 최근 작업 섹션 (모드/파일명/점수/시간)
- 클릭 시 해당 모드 전환 (파일 자동 로드 없음 — Step 2에서 확장)
- API: `GET/POST /api/verify/history`

#### Step 2: 결과 재열람 (세션 영속화)

- 저장: `data/verify/{username}/{session_id}/` (meta + 원문 텍스트 + 결과 JSON)
- 이력 클릭 → 결과 재열람 (읽기 전용)
- 사용자당 최대 20세션 (자동 삭제)
- API: `POST/GET/DELETE /api/verify/session/{id}`

#### Step 3: 참조 문서 라이브러리

- 자주 쓰는 참조 원문(MIL-STD 등) 서버 저장
- 업로드 대신 "라이브러리에서 선택" 옵션
- API: `GET/POST/DELETE /api/verify/library/{id}`

### 4.3 구현 순서

| # | 태스크 | 예상 | Step | 상태 |
|---|--------|------|:----:|------|
| 4a | 백엔드: 이력 저장/조회 API | 하 | 1 | ⬜ |
| 4b | 프론트: 허브 이력 섹션 UI | 중 | 1 | ⬜ |
| 4c | 각 모드 결과 후 이력 자동 저장 연동 | 하 | 1 | ⬜ |
| 4d | 백엔드: 세션 저장/로드/삭제 API | 중 | 2 | ⬜ |
| 4e | 프론트: 이력 클릭 → 결과 재열람 | 상 | 2 | ⬜ |
| 4f | 세션 용량 관리 (자동 삭제, 관리자 설정) | 하 | 2 | ⬜ |
| 4g | 백엔드: 참조 문서 라이브러리 API | 중 | 3 | ⬜ |
| 4h | 프론트: 라이브러리 UI | 중 | 3 | ⬜ |

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

### Author(Plan-24) 연계

| Verify 기능 | Author 활용 |
|------------|-------------|
| 유사도 검사 | Author 초안을 원문 대비 표절 점검 |
| 규칙 검증 + 인텔리전스 | Author 초안의 작성 지침 준수 검증 |
| 내보내기 | 검증 결과를 Excel/HTML 리포트로 |

---

*작성: 2026-04-01 · 최종 갱신: 2026-04-03*
