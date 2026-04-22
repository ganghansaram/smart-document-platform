# Verify 시스템 — 설계 및 규칙 기준 문서

DOCX/PDF 문서 **비교 + 유사도 검사 + 규칙 검증 + 검토 리포트** 통합 도구.
3개 표준(ASD-STE100, MIL-STD-961E, MIL-STD-38784B) 기반 규칙 엔진(21종) + Acrolinx 밀도 방식 스코어링 탑재.

---

## 목차

1. [개요](#1-개요)
2. [화면 구성](#2-화면-구성)
3. [비교 모드](#3-비교-모드)
4. [유사도 검사 모드](#4-유사도-검사-모드)
5. [규칙 검증 모드](#5-규칙-검증-모드)
6. [검토 리포트 + 세션 이력](#6-검토-리포트--세션-이력)
7. [백엔드 API](#7-백엔드-api)
8. [설정](#8-설정)
9. [데이터·파일 구조](#9-데이터파일-구조)

---

## 1. 개요

### 시스템 정체성

Verify(구 Compare)는 **비교·유사도·규칙검증·검토 판정 도구**다. 3-모드 허브를 통해 문서 품질을 다각도로 평가한다.

| 모드 | 목적 | 핵심 알고리즘 | 출처 |
|------|------|---------------|------|
| **비교** | 두 문서 버전 간 차이 시각화 + 판정 | jsdiff(단어 수준) + AI 의미 분류(Ollama) | 업계 표준 |
| **유사도 검사** | 표절·참조 유사도 정밀 측정 | Winnowing L1 + bge-m3 L3 (크로스링구얼) | MOSS(Stanford) + BAAI |
| **규칙 검증** | 작성 규칙 준수 여부 자동 검증 | 21종 정규식·휴리스틱 규칙 엔진 | ASD-STE100 / MIL-STD / 자체 |

### 핵심 특징

| 항목 | 설명 |
|------|------|
| 3-모드 허브 | 비교 / 유사도 검사 / 규칙 검증 모드 전환 |
| 듀얼 패널 diff | 추가/삭제/수정 하이라이트, 단어 수준, 동기 스크롤 |
| AI 의미 분류 | Ollama 구조화 출력 6태그 → 3그룹 시각화 (주의·참고·편집) |
| 유사도 2계층 | Winnowing(구문 지문) + bge-m3(시맨틱 임베딩), 6종 지표, 보일러플레이트 제외 |
| 규칙 엔진 | 21종 = ASD-STE100 8 + MIL-STD 7 + 자체 6 |
| 스코어링 | Acrolinx 밀도 방식 (이슈 가중치 / 단어 수) + 인텔리전스 패널 |
| 검토 리포트 | XLSX(시트별), HTML(시각적), TXT 다형식 내보내기 |
| 미니맵 | 스크롤바 오버레이에 변경점/이슈 위치 마커 (PyCharm 스타일) |
| 입력 방식 | DOCX/PDF 파일 업로드 또는 텍스트 직접 붙여넣기 (DRM 환경 대응) |
| 텍스트 추출 | DOCX: python-docx, PDF: PyMuPDF |
| diff 라이브러리 | jsdiff (클라이언트사이드, `js/lib/jsdiff/diff.min.js`) |
| 세션 이력 | 비교/검증 결과 자동 저장, 이력 조회·재열람 |
| 권한 | 비교/AI 분류/유사도: viewer 이상 / 규칙 저장: admin |

---

## 2. 화면 구성

### 2.1 전체 레이아웃

```
┌─ 플랫폼 헤더 ─────────────────────────────────────────────┐
├─ 툴바 ───────────────────────────────────────────────────┤
│  [비교|유사도|검증] [◀▶탐색] [스왑] [동기] [필터] [AI분석] [리포트] │
├───────────────┬──────┬────────────────┬─────────────────┤
│  패널 A (원본)  │핸들  │  패널 B (수정본)  │   사이드바       │
│               │     │                │  변경점/이슈 목록  │
│  단락 diff     │ ↔  │  단락 diff      │  수락/거절 버튼   │
│  하이라이트     │     │  하이라이트      │  AI 태그 배지    │
│  미니맵 오버레이 │     │  미니맵 오버레이  │  스코어카드      │
└───────────────┴──────┴────────────────┴─────────────────┘
```

### 2.2 3-모드 허브

툴바 좌측 모드 탭으로 전환:
- **비교 모드**: 두 문서 텍스트 diff + AI 분류 + 수락/거절
- **유사도 검사**: 두 문서 간 구문·시맨틱 유사도 다계층 분석
- **규칙 검증**: 단일 문서의 규칙 위반 검사 + 이슈 하이라이트 + 스코어링

모드 전환 시 사이드바·필터·탐색 버튼이 해당 모드에 맞게 토글된다.

### 2.3 주요 UI 요소

- **문서 입력**: 파일 드래그앤드롭(DOCX/PDF) 또는 "텍스트 붙여넣기" 링크 → textarea
- **동기 스크롤**: 좌우 패널 `scrollTop` 비율 동기화 (툴바 ON/OFF)
- **변경점 탐색**: ▲▼ 버튼 또는 ↑↓ 키로 순회, 위치 표시기(`3/12`)
- **미니맵**: 패널 스크롤바 오버레이에 변경점/이슈 컬러 마커, 클릭 시 스크롤 이동
- **사이드바**: 우측 접이식 패널 — 모드별 콘텐츠(변경점 / 유사도 결과 / 이슈 목록), 수락·거절 버튼, AI 태그 배지, 스코어 표시
- **단락 번호**: 툴바 토글로 좌우 패널에 단락 번호 표시
- **원본↔수정본 스왑**: 스왑 버튼으로 패널 A/B 문서 교체

---

## 3. 비교 모드

### 3.1 문서 입력 → 텍스트 추출

```
사용자: DOCX/PDF 업로드 (또는 텍스트 붙여넣기)
    ↓
프론트엔드: POST /api/compare/upload (FormData)
    ↓
백엔드 (compare_service.py):
    DOCX → python-docx → paragraphs[] (빈 단락 제외)
    PDF  → PyMuPDF get_text("blocks") → paragraphs[]
    ↓
응답: { filename, format, paragraphs[], page_count }
    ↓
프론트엔드: docState[side] 에 저장
```

텍스트 붙여넣기 모드에서는 서버 호출 없이 클라이언트에서 줄 분리 → paragraphs 배열 생성.

### 3.2 diff 계산 (클라이언트사이드)

1. **단락 매칭**: `Diff.diffArrays(parasA, parasB)` — 단락 단위 추가/삭제/유지 판별
2. **단어 수준 diff**: 수정된 단락 쌍에 `Diff.diffWords(textA, textB)`
3. **갭 라인 정렬**: 추가/삭제 시 반대편에 빈 줄 삽입 → 좌우 시각적 정렬
4. **결과**: `diffState.changes[]` — `{ type, indexA, indexB, textA, textB, wordDiff }`

### 3.3 렌더링

- 추가(added): 우측 패널 초록 배경 (`--diff-added-bg`)
- 삭제(deleted): 좌측 패널 빨강 배경 (`--diff-deleted-bg`)
- 수정(modified): 양쪽 노랑 배경 + 단어 수준 `<span>` 하이라이트
- 필터: 추가/삭제/수정 개별 토글, 공백 무시 옵션
- diff 색상은 `tokens.css` 의 `--diff-*` 변수 사용 (다크모드 자동 전환)

### 3.4 AI 의미 분류

#### 3.4.1 3그룹 체계

6개 태그를 3개 시각 그룹으로 매핑:

| 그룹 | 태그 | 색상 | 의미 |
|------|------|------|------|
| **주의** (Attention) | `STRICTER`, `MORE_LENIENT` | 빨강 (`--color-error`) | 요구사항 강화/완화 — 검토 필수 |
| **참고** (Info) | `EXPANDED`, `CLARIFICATION` | 파랑 (`--active-color`) | 내용 추가/명확화 — 인지 필요 |
| **편집** (Editorial) | `EDITORIAL`, `RESTRUCTURED` | 회색 (`--text-light`) | 편집/구조 변경 — 의미 변화 없음 |

#### 3.4.2 분류 흐름

```
사용자: 툴바 [AI 분석] 버튼 클릭
    ↓
프론트엔드: diffState.changes 에서 변경 구간 추출
    → POST /api/compare/ai-classify { changes[] }
    ↓
백엔드 (compare_service.py):
    1. 배치 분할 (COMPARE_AI_BATCH_SIZE, 기본 20)
    2. 각 배치 → Ollama /api/generate (구조화 출력, JSON Schema)
    3. 분류 결과 검증 + 정규화
    4. 실패 배치 1회 재시도, 최종 실패 시 UNKNOWN 표시
    ↓
응답: { classifications: [{ index, tag, confidence, explanation }] }
    ↓
프론트엔드: 사이드바에 태그 배지 + 설명 표시, 필터 활성화
```

#### 3.4.3 Ollama 호출 특성

- **구조화 출력**: `format` 파라미터에 JSON Schema 전달 → LLM 이 스키마 준수 JSON 출력
- **Few-shot 프롬프트**: 5개 예시 (STRICTER, CLARIFICATION, EXPANDED, STRICTER, MORE_LENIENT)
- **판단 기준**: "의무 vs 허용" 관점 — 시스템 의무 강화=STRICTER, 사용자 제약 완화=MORE_LENIENT
- **temperature=0**: 분류 일관성 최대화

#### 3.4.4 수동 재분류 + 필터

- 사이드바 태그 배지 클릭 → 6태그 드롭다운 (수동 변경 시 리포트에 "(수동)" 표기)
- 필터 드롭다운에 태그별 체크박스 + "주의 필요만 보기" 프리셋 (STRICTER + MORE_LENIENT)

### 3.5 수락/거절 판정

- **수락** (✓): 사이드바 항목 초록 강조 (키 Enter)
- **거절** (✗): 사이드바 항목 빨강 강조 (키 Delete)
- **미처리**: 판정 전 상태
- **벌크**: 사이드바 헤더 "전체 수락/거절" 버튼. AI 분류 완료 시 그룹별 벌크 처리 가능 (예: "편집 그룹 전체 수락")

---

## 4. 유사도 검사 모드

### 4.1 2계층 파이프라인

```
사용자: 두 문서 업로드 (또는 paragraphs 배열 직접 입력)
    ↓
프론트엔드: POST /api/compare/similarity { paragraphs_a[], paragraphs_b[] }
    ↓
백엔드 (similarity_engine.py):
    L1. Winnowing — k-gram 해시 지문 기반 구문 수준 유사도
        · MOSS(Stanford) 알고리즘, 파라미터: k=5, w=4
        · 지문 집합 자카드 유사도
    L3. bge-m3 — 시맨틱 임베딩 기반 의미 수준 유사도
        · 단락별 bge-m3 (1024차원) 임베딩 → 코사인 유사도
        · 크로스링구얼(한↔영) 지원
    ↓
보일러플레이트 제외:
    · data/boilerplate-phrases.json 에 정의된 상용구 단락 자동 제외
    ↓
응답: 6종 지표 { total, syntactic, semantic, cosine, jaccard, excl_boilerplate }
```

### 4.2 크로스링구얼 차별점

bge-m3 는 다국어 임베딩이라 한국어 문서 A vs 영문 문서 B 간 **의미 기반** 유사도 측정이 가능하다. 규격서 국문화 시 원문 대비 누락·의역을 자동 감지.

### 4.3 임계치

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `VERIFY_SIMILARITY_THRESHOLD_HIGH` | `0.8` | 높은 유사도 판정 임계값 |
| `VERIFY_SIMILARITY_THRESHOLD_MEDIUM` | `0.5` | 중간 유사도 판정 임계값 |

관리자 설정 > Verify > 유사도 검사 탭에서 런타임 변경 가능.

---

## 5. 규칙 검증 모드

### 5.1 아키텍처

```
프론트엔드: 검증 탭 선택 → 문서 업로드
    ↓
POST /api/compare/validate { paragraphs[], preset? }
    ↓
백엔드 (rule_engine.py):
    1. backend/rules/*.json 에서 활성 규칙 로드
    2. 각 규칙 runner 실행 → 이슈 목록 생성
    3. 이슈 가중치 합산 → Acrolinx 밀도 스코어 계산
    ↓
응답: { score, summary: { error, warning, suggestion }, issues[] }
    ↓
프론트엔드: 이슈 하이라이트 + 사이드바 목록 + 스코어카드
```

각 이슈는 `paragraph_index`, `char_start`, `char_end` 를 포함하여 해당 위치에 마커 하이라이트. 사이드바 항목 클릭 시 해당 위치로 스크롤.

### 5.2 21종 규칙 구현 현황

| 출처 | 정의 파일 | 규칙 수 | 대표 예시 |
|------|-----------|:-------:|-----------|
| **자체** (custom) | `backend/rules/custom.json` | 6 | 번호 연속성, 표 캡션, 그림 캡션, 금지 용어, 용어 통일, 문장 길이 |
| **ASD-STE100** (작성) | `backend/rules/ste-writing.json` | 8 | 승인 사전, 기술명 일관성, 명사 클러스터, 수동태, 절차문 단어 수, 설명문 단어 수, 단락 문장 수, WARNING/CAUTION 표기 |
| **MIL-STD** (구조) | `backend/rules/mil-structure.json` | 7 | 6섹션 구조, 번호 체계, 약어 첫 사용 병기, shall/will/should/may, 표·그림 번호+캡션, 교차참조 실존, WARNING 위치·서식 |

#### 자체 규칙 6종 상세

| 규칙 ID | 카테고리 | 설명 |
|---------|----------|------|
| `numbering_continuity` | structure | 번호 체계 연속성 (1.1 → 1.3 누락 감지) |
| `table_caption` | structure | 표 캡션 번호 연속성 + 본문 참조 여부 |
| `figure_caption` | structure | 그림 캡션 번호 연속성 + 본문 참조 여부 |
| `forbidden_terms` | terminology | 금지 용어 감지 (대체어 제안) |
| `inconsistent_terms` | terminology | 동일 그룹 내 복수 용어 사용 감지 (최빈 용어 통일 권장) |
| `sentence_length` | readability | 문장 길이 초과 (기본 80자) |

### 5.3 참조 표준 기술 분석

#### 5.3.1 참조 표준

| 표준 | 정식 명칭 | 버전 | 입수 |
|------|-----------|------|------|
| **ASD-STE100** | Simplified Technical English | Issue 7 (2017-01-25) | 공개 PDF (382p) |
| **MIL-STD-961E** | Defense and Program-Unique Specifications Format and Content | Rev E w/Change 1 (2008) | army.mil (111p) |
| **MIL-STD-38784B** | Standard Practice for Technical Manuals — General Style and Format | Rev B (2020-11-16) | 공개 PDF (138p) |

> 원본 파일: `workbench/standards/` 디렉토리

#### 5.3.2 ASD-STE100 — 49개 규칙 분석

| 섹션 | 조항 수 | 적용 | 대표 적용 규칙 |
|------|:-------:|:----:|----------------|
| Section 1 Words (1.1~1.14) | 14 | 2 | 1.1 승인 사전, 1.11 동일 항목 단일 기술명 |
| Section 2 Noun Clusters | 3 | 1 | 2.1 명사 클러스터 3단어 이하 (low confidence, 기본 OFF) |
| Section 3 Verbs | 7 | 1 | 3.6 능동태(수동태 감지, low confidence, 기본 OFF) |
| Section 4 Sentences | 4 | 0 | — (주관적 판단) |
| Section 5 Procedural Writing | 5 | 1 | 5.1 절차문 20단어 이하 |
| Section 6 Descriptive Writing | 6 | 2 | 6.3 설명문 25단어 이하, 6.6 단락 6문장 이하 |
| Section 7 Safety Instructions | 3 | 1 | 7.1 WARNING/CAUTION 대문자 표기 |
| Section 8 Punctuation | 7 | 4 | 8.4~8.7 단어 수 카운트 로직 |
| **합계** | **49** | **12** | 적용률 24% |

**미적용 사유**: NLP/형태소 분석 필요 18건, 주관적 판단 10건, 우선순위 낮음/범위 초과 9건.

#### 5.3.3 MIL-STD-961E — 13건 분석, 9건 적용 (69%)

| 조항 | 내용 | 구현 |
|------|------|------|
| 5.5~5.12 | 6섹션 구조(SCOPE/APPLICABLE DOCUMENTS/REQUIREMENTS/VERIFICATION/PACKAGING/NOTES) | 제목 패턴 매칭 |
| 4.9 | 각 단락·하위 단락 번호 부여 | 번호 연속성 |
| 4.6.3 | 약어 첫 사용 시 풀네임 병기 | 약어 패턴 + 정의 매칭 |
| 4.6.6 | shall/will/should/may 사용 규칙 | 섹션별 키워드 위치 검사 |
| 4.13~4.14 | 표·그림 번호 순차 + 제목 필수 | 번호 연속성 + 캡션 존재 검사 |
| 4.18 | 교차참조 관계 명확화 | 참조 대상 실존 검증 |

**미적용**: 4.6 언어 모호성(→ STE 로 커버), 4.6.2 ASME Y14.38 약어 표준(외부 DB 필요), 4.7 분수→소수 변환 등 우선순위 낮음.

#### 5.3.4 MIL-STD-38784B — 10건 분석, 6건 적용 (60%)

| 조항 | 내용 | 구현 |
|------|------|------|
| 4.8 | 약어 첫 사용 시 풀네임 병기 | 961E 4.6.3과 통합 |
| 4.8.8 | shall/will/should/may 사용 | 961E 4.6.6과 동일 로직 |
| App.A 배치 | WARNING/CAUTION 은 해당 절차 직전 | 위치 패턴 검사 |
| App.A 서식 | WARNING 전체 대문자, 4파트 구조 | 대문자 표기(STE 7.1과 통합) |
| 4.7.9 | 표 번호 순차 + 제목 필수 | 961E 4.13과 통합 |
| 일반 | 간결한 문장, 능동태 | STE 5.1, 6.3, 3.6 으로 커버 |

#### 5.3.5 적용 요약

| 출처 | 전체 분석 | 적용 | 적용률 |
|------|:---------:|:----:|:------:|
| ASD-STE100 | 49 | 12 | 24% |
| MIL-STD-961E | 13 | 9 | 69% |
| MIL-STD-38784B | 10 | 6 | 60% |
| 자체 | 6 | 6 | 100% |
| **합계** | **78** | **33** | **42%** |

**분석 적용(33건) → 구현 규칙(21종)**: 분석 "적용" 판정 33건 중 중복·통합 제거 후 최종 21종의 JSON 규칙으로 구현.

#### 5.3.6 업계 도구 비교

| 도구 | 접근 | STE 커버리지 | MIL-STD | 비고 |
|------|------|:------------:|:-------:|------|
| **HyperSTE** | STE100 공인, NLP 탑재 | ~40/65 (62%) | 없음 | 유료, 최고 커버리지 |
| **Acrolinx** | 범용 스타일 가이드 | 낮음 | 없음 | 엔터프라이즈 |
| **Vale** | YAML 규칙 엔진 | 플러그인 의존 | 없음 | 오픈소스 |
| **우리 시스템** | JSON 규칙 엔진, NLP 없음 | 12/49 (24%) | 15건 적용 | 폐쇄망 운용, **MIL-STD 지원 차별화** |

> 상용 도구는 STE 특화이나 MIL-STD 구조 검증은 미지원. 우리 시스템은 STE + MIL-STD 를 통합 제공.

#### 5.3.7 향후 확장 (NLP 도입 시)

현재 "NLP 필요" 미적용 18건은 경량 NLP(spaCy, 모델 ~15MB) 도입 시 적용 가능. 현 환경에서 LLM(수 GB)을 이미 운용 중이므로 기술적 제약 없음.

| 도입 시 추가 가능 규칙 | 예상 효과 |
|----------------------|-----------|
| 수동태 정확 감지 (STE 3.6) | precision 60% → 90%+ |
| 품사 기반 명사 클러스터 (STE 2.1) | 오탐 대폭 감소 |
| 동사 형태 검증 (STE 3.1~3.5) | 5건 추가 적용 |
| 적용률 변화 | 24% → 약 40~50% |

### 5.4 Acrolinx 밀도 방식 스코어링

Phase 3V 에서 업계 조사 후 채택:

```python
severity_weight   = { error: 5, warning: 2, suggestion: 1 }
confidence_weight = { high: 1.0, medium: 0.7, low: 0.4 }

issue_weight = severity_weight × confidence_weight
density      = sum(issue_weights) / (effective_words / 100)
score        = 100 × max(0, 1 - density / DENSITY_THRESHOLD)
```

| 등급 | 점수 범위 |
|:----:|:---------:|
| A | 90~100 |
| B | 70~89 |
| C | 50~69 |
| D | 0~49 |

> 단순 감점식(`100 − error×10 − warning×3 − suggestion×1`)이 아니라 **문서 분량에 비례한 밀도 방식** 을 사용한다. 1,000단어에 오류 10건과 10,000단어에 오류 10건이 같은 점수가 되는 문제를 해소.

### 5.5 운영자 규칙 조정 가이드

#### 5.5.1 규칙 ON/OFF

검증 모드 사이드바 ⚙ 버튼 → 설정 모달:
- **소스 그룹 토글**: ASD-STE100 / MIL-STD-38784 / MIL-STD-961E / 기본 규칙을 그룹 단위
- **개별 규칙 토글**: 각 규칙 ON/OFF
- **심각도 변경**: 오류/경고/제안 선택

#### 5.5.2 약어 오탐 해소

약어 감지(38-A1)에서 사내 용어가 오탐되는 경우, `backend/services/rule_engine.py` 의 `common_abbrs` 집합에 추가:

```python
common_abbrs = {"WARNING", "CAUTION", ...,
    # 사내 용어 추가
    "KUH", "LAH", "KFX", "AESA",
}
```

#### 5.5.3 점수가 너무 낮거나 높을 때

`backend/services/compare_service.py`:

| 상수 | 기본값 | 설명 | 조정 방향 |
|------|:------:|------|-----------|
| `DENSITY_THRESHOLD` | 5.0 | 100단어당 이 값이면 0점 | 올리면 점수 관대, 내리면 엄격 |
| `MIN_WORDS` | 200 | 짧은 문서 최소 단어 수 | 올리면 짧은 문서 점수 상승 |
| `SEVERITY_WEIGHT` | error:5, warning:2, suggestion:1 | 심각도별 가중치 | 비율 조정으로 감점 강도 변경 |

#### 5.5.4 금지 용어 · 용어 그룹 관리

검증 모달 ⚙ → "기본 규칙" 그룹에서:
- **금지 용어**: 직접 입력 또는 CSV 가져오기 (`term,replacement` 형식)
- **용어 일관성 그룹**: 쉼표 구분 입력 또는 CSV 가져오기

#### 5.5.5 새 규칙 추가 (개발자용)

`backend/rules/` 에 JSON 파일 추가:

```json
{
  "id": "custom-new-rule",
  "source": "custom",
  "category": "structure",
  "severity": "warning",
  "confidence": "high",
  "type": "pattern",
  "name_ko": "새 규칙 이름",
  "enabled": true,
  "params": {
    "patterns": ["검출할 정규식"],
    "scope": "sentence"
  }
}
```

서버 재시작 시 자동 로드. 코드 수정 불필요.

---

## 6. 검토 리포트 + 세션 이력

### 6.1 리포트 형식

**XLSX** (Excel — 시트별 구분):
- 변경점, 판정 상태, AI 분류, 규칙 이슈를 각각 독립 시트로 출력
- 필터·정렬이 편리해 감사·보고용에 적합

**HTML** (시각적 리포트):
- 다크/라이트 테마 자동 적용
- 변경점 diff 하이라이트를 유지
- PDF 변환 시에도 색상 보존

**TXT** (텍스트):
```
=== 검토 리포트 ===
원본: document_v1.docx
수정본: document_v2.docx
생성일: 2026-03-15 14:30
총 24건 | 수락 18건 · 거절 3건 · 미처리 3건

--- 변경 목록 ---
[1] 수정 | 수락 | STRICTER | "응답 시간 3초" → "응답 시간 1초"
    AI: 응답 시간 기준이 강화되었습니다. (확신도: 0.95)
[2] 추가 | 거절 | EXPANDED | "4.1 감사 로그: ..."
    AI: 감사 로그 요구사항이 새로 추가되었습니다. (확신도: 0.90)
...
```

미처리 항목이 있으면 내보내기 전 확인 다이얼로그 표시.

### 6.2 세션 이력

- 모든 비교·검증 결과는 `data/compare/`, `data/verify/` 에 자동 저장
- 이력 목록에서 날짜·파일명 기준 재열람 가능
- 저장 항목: 원본·수정본 파일명, diff/이슈/판정, AI 분류 결과, 스코어

---

## 7. 백엔드 API

모든 엔드포인트 prefix: `/api/compare`

### 문서 업로드

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/upload` | POST | viewer | DOCX/PDF 텍스트 추출 (파일 저장 없음, 휘발성) |

- 입력: `multipart/form-data` (file)
- 허용 확장자: `.docx`, `.pdf`
- 최대 크기: 50MB
- 응답: `{ filename, format, paragraphs[], page_count }`

### 규칙 검증

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/validate` | POST | viewer | 단락 배열 → 규칙 검증 → 이슈 목록 |

- 입력: `{ paragraphs[], preset? }`
- 응답: `{ score, summary: { error, warning, suggestion }, issues[] }`
- 각 이슈: `{ id, rule_id, category, severity, message, paragraph_index, char_start, char_end, context, suggestion }`

### 규칙 관리

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/rules` | GET | viewer | 규칙 설정 반환 |
| `/rules` | PUT | admin | 규칙 설정 저장 |
| `/rule-definitions` | GET | viewer | 규칙 정의 목록 (이름, 설명, 파라미터) |

### AI 의미 분류

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/ai-classify` | POST | viewer | diff 변경 구간 AI 의미 분류 |

- 입력: `{ changes: [{ index, type, text_a, text_b }] }` (최대 200건)
- 응답: `{ classifications: [{ index, tag, confidence, explanation }] }`
- 배치 처리: `COMPARE_AI_BATCH_SIZE` (기본 20) 단위 분할
- 실패 시: 1회 재시도 → 최종 실패 시 `tag: "UNKNOWN"`

### 유사도 검사

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/similarity` | POST | viewer | 두 문서 간 유사도 다계층 분석 |

- 입력: `{ paragraphs_a[], paragraphs_b[] }`
- 응답: 6종 지표 `{ total, syntactic, semantic, cosine, jaccard, excl_boilerplate }`
- 보일러플레이트 제외: `data/boilerplate-phrases.json`

### 문서 추출

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/extract-document` | POST | viewer | 문서 텍스트 추출 (규칙 정의 목록 포함) |

### 내보내기

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/export` | POST | viewer | 검토 리포트 내보내기 |

- 입력: `{ format, changes, decisions, classifications, ... }`
- 지원 형식: `xlsx`, `html`, `txt`

### 세션 이력

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/history` | GET | viewer | 비교/검증 세션 이력 조회 |
| `/history` | POST | viewer | 세션 결과 저장 |

---

## 8. 설정

`backend/config.py` 내 Verify 관련 설정 (관리자 설정 > Verify 탭에서 런타임 변경):

**AI 의미 분류**

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `COMPARE_AI_ENABLED` | `True` | AI 의미 분류 활성화 |
| `COMPARE_AI_MODEL` | `""` (OLLAMA_MODEL 폴백) | 분류용 Ollama 모델 |
| `COMPARE_AI_TEMPERATURE` | `0` | 분류 일관성 최대화 |
| `COMPARE_AI_BATCH_SIZE` | `20` | 1회 LLM 호출당 최대 변경 구간 수 |
| `COMPARE_AI_TIMEOUT` | `60` (초) | LLM 호출 타임아웃 |
| `COMPARE_AI_SYSTEM_PROMPT` | `""` (기본 내장) | 커스텀 시스템 프롬프트 |

**유사도 검사**

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `VERIFY_SIMILARITY_THRESHOLD_HIGH` | `0.8` | 높은 유사도 판정 임계값 |
| `VERIFY_SIMILARITY_THRESHOLD_MEDIUM` | `0.5` | 중간 유사도 판정 임계값 |

**규칙 엔진**

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `DENSITY_THRESHOLD` | `5.0` | 밀도 기반 스코어 임계 |
| `MIN_WORDS` | `200` | 짧은 문서 최소 단어 수 |
| `SEVERITY_WEIGHT` | `{error:5, warning:2, suggestion:1}` | 심각도별 가중치 |

---

## 9. 데이터·파일 구조

### 9.1 compare-rules.json (프리셋)

```json
{
  "active_preset": "technical",
  "presets": {
    "technical": {
      "name": "기술문서",
      "rules": {
        "numbering_continuity": { "enabled": true, "severity": "error", "params": {} },
        "table_caption":        { "enabled": true, "severity": "warning", "params": {} },
        "forbidden_terms": {
          "enabled": true, "severity": "warning",
          "params": { "terms": [{ "term": "어쩌면", "replacement": "경우에 따라" }] }
        },
        "inconsistent_terms": {
          "enabled": true, "severity": "suggestion",
          "params": { "groups": [["비행제어장치", "비행 제어 장치", "FCS"]] }
        },
        "sentence_length": {
          "enabled": true, "severity": "suggestion",
          "params": { "max_chars": 80 }
        }
      }
    }
  }
}
```

### 9.2 프론트엔드 상태 (휘발성)

모든 상태는 브라우저 메모리에만 존재, 새로고침 시 초기화:

```javascript
var docState = {
    a: { file: null, text: null, paragraphs: [], filename: '' },
    b: { file: null, text: null, paragraphs: [], filename: '' }
};

var diffState = {
    changes: [],
    currentIndex: -1,
    decisions: [],            // null | 'accepted' | 'rejected'
    aiClassifications: null,
    filter: { added: true, deleted: true, modified: true },
    aiFilter: { STRICTER: true, MORE_LENIENT: true, ... },
    ignoreWhitespace: false
};
```

### 9.3 파일 구조

```
프론트엔드
├── compare.html                   ← Verify SPA (모놀리식 HTML, inline JS)
├── css/tokens.css                 ← 디자인 토큰 (diff 색상 변수 포함)
├── css/compare.css                ← Verify 전용 스타일
├── css/components.css             ← 공통 컴포넌트
├── css/modal.css                  ← 모달 스타일
├── css/platform-header.css        ← 공통 헤더
├── js/lib/jsdiff/diff.min.js      ← jsdiff 라이브러리
├── js/platform-header.js          ← 공통 헤더 컴포넌트
└── js/config.js                   ← AUTH_CONFIG (backendUrl)

백엔드
├── backend/api/compare.py                ← Verify API 라우터
├── backend/services/compare_service.py   ← 텍스트 추출, AI 의미 분류
├── backend/services/similarity_engine.py ← 유사도 (Winnowing + bge-m3)
├── backend/services/rule_engine.py       ← 규칙 검증 엔진 (21종)
├── backend/services/export_service.py    ← 검토 리포트 (XLSX/HTML/TXT)
├── backend/rules/custom.json             ← 자체 규칙 6종
├── backend/rules/ste-writing.json        ← ASD-STE100 규칙 8종
├── backend/rules/mil-structure.json      ← MIL-STD 규칙 7종
└── backend/config.py                     ← COMPARE_AI_* · VERIFY_* 설정

데이터
├── data/compare-rules.json               ← 규칙 프리셋 설정
├── data/boilerplate-phrases.json         ← 유사도 검사 보일러플레이트 제외
├── data/compare/                         ← 비교 세션 데이터
└── data/verify/                          ← 검증 결과

참조 자료
└── workbench/standards/                  ← 원본 표준 PDF (ASD-STE100, MIL-STD)
```

---

*최종 갱신: 2026-04-22 (구 11-COMPARE-SYSTEM + 12-VERIFY-SYSTEM 통합, 원본 표준: ASD-STE100 Issue 7, MIL-STD-961E, MIL-STD-38784B)*
