# 표준 기반 규칙 카탈로그

> 작성일: 2026-04-04
> 목적: Phase 5 규칙 엔진에서 구현할 규칙 목록 + 자동화 등급 + 우선순위
> 대상 표준: ASD-STE100, MIL-STD-961E, MIL-STD-38784
> **기준 문서**: [`docs/12-VERIFY-SYSTEM.md`](../../docs/12-VERIFY-SYSTEM.md) — 원본 대조 분석 + 선정 사유

---

## 자동화 등급 기준

| 등급 | 의미 | Precision 기대치 |
|:----:|------|:---------------:|
| A | 정규식/사전 룩업으로 완전 자동화 | > 90% |
| B | 휴리스틱으로 부분 자동화 (오탐 가능) | 60~90% |
| C | 사람 판단 필요 (자동화 부적합) | — |

---

## 1. ASD-STE100 작성 규칙

### 구현 대상 (A/B 등급)

| ID | 규칙명 | 설명 | 등급 | 기존 규칙 | 구현 방법 |
|---|---|---|:---:|:---:|---|
| STE-1.1 | Approved words only | 승인 사전에 없는 단어 사용 경고 | A | `forbidden_terms` 업그레이드 | 승인 사전 룩업 (블랙리스트→화이트리스트 전환) |
| STE-1.3 | Technical Names permitted | 기술명은 예외 허용 | A | — | TND(기술명사 사전) 화이트리스트로 오탐 억제 |
| STE-1.5 | No synonyms for TN | 동일 개념에 동의어 사용 금지 | A | `inconsistent_terms` 업그레이드 | 동의어 그룹 맵 확장 |
| STE-2.1 | Max 3 nouns in cluster | 명사 클러스터 3단어 이하 | B | — | 연속 비관사/비전치사 단어 카운트 (low confidence, 기본 OFF) |
| STE-3.1 | Max 20 words (procedural) | 절차문 20단어 이하 | A | `sentence_length` 업그레이드 | 문자 수→단어 수 전환, 절차/설명 구분 |
| STE-3.2 | Max 25 words (descriptive) | 설명문 25단어 이하 | A | `sentence_length` 업그레이드 | 위와 동일, 임계값 25 |
| STE-3.3 | One instruction per sentence | 한 문장 한 지시 | B | — | and/or + 동사원형 2회 이상 패턴 |
| STE-3.6 | Use active voice | 능동태 사용 (수동태 감지) | B | — | `(is|are|was|were|been|being)\s+\w+ed\b` (low confidence, 기본 OFF) |
| STE-3.7 | Imperative in procedures | 절차문 명령형 시작 | B | — | 번호 목록 첫 단어가 동사원형 사전에 있는지 |
| STE-3.9 | Max 1 subordination level | 종속절 1단계만 | B | — | which/that/if/when 2회 이상 검출 |
| STE-5.1 | WARNING before procedure | 경고문은 해당 절차 앞 배치 | A | — | WARNING 위치가 참조 단계보다 앞인지 (38-W1과 통합) |
| STE-6.1 | Short paragraphs (max 6 sent) | 단락 6문장 이하 | A | — | 단락별 `.`/`!`/`?` 카운트 |
| STE-7.4 | No slash as conjunction | `/`를 and/or 대용 금지 | A | — | `\w+/\w+` 패턴, 단위(km/h 등) 예외 |
| STE-9.1 | Standard abbreviations only | 비표준 약어 금지 | A | — | 승인 약어 사전 대조 (38-A3과 통합) |

### 제외 (C 등급)

| ID | 사유 |
|---|---|
| STE-1.2 | 단어의 "허용된 의미"로만 사용 — 의미 판별 NLP 필수 |
| STE-3.4 | 한 문장 한 주제 — 의미 분석 필요 |
| STE-4.3 | 절차 순서 논리성 — 사람 판단 |
| STE-7.1 | 관사 생략 감지 — 문맥 의존, 오탐 과다 |

---

## 2. MIL-STD-961E 구조 규칙

### 구현 대상

| ID | 규칙명 | 설명 | 등급 | 기존 규칙 | 구현 방법 |
|---|---|---|:---:|:---:|---|
| 961-S1 | SCOPE required | Section 1 "SCOPE" 필수 | A | — | `1\.\s+SCOPE` 패턴 검색 |
| 961-S2 | APPLICABLE DOCUMENTS required | Section 2 필수 | A | — | `2\.\s+APPLICABLE DOCUMENTS` |
| 961-S3 | REQUIREMENTS required | Section 3 필수 | A | — | `3\.\s+REQUIREMENTS` |
| 961-S4 | VERIFICATION required | Section 4 필수 | A | — | `4\.\s+VERIFICATION` |
| 961-S5 | PACKAGING required | Section 5 필수 | A | — | `5\.\s+PACKAGING` |
| 961-S6 | NOTES required | Section 6 필수 | A | — | `6\.\s+NOTES` |
| 961-N1 | Decimal numbering | 십진 번호 체계 (1→1.1→1.1.1) | A | `numbering_continuity` 업그레이드 | 기존 검사에 961 규칙 통합 |
| 961-N2 | Max 6 subdivision levels | 번호 최대 6단계 | A | `numbering_continuity` 업그레이드 | `.` 구분자 ≤ 5 검사 |
| 961-R2 | No shall in SCOPE | Section 1에 shall 금지 | A | — | 섹션 범위 판별 + `shall` 검색 |
| 961-R3 | No shall in NOTES | Section 6에 shall 금지 | A | — | 동일 |
| 961-T1 | shall location restriction | shall은 Section 3/4에서만 | B | — | shall 사용 위치 섹션 판별 |
| 961-R1 | Referenced docs in Sec 2 | 본문 참조 문서가 Section 2에 등재 | B | — | 본문 규격번호 추출 → Sec 2 대조 |
| 961-N3 | Req ↔ Verification traceability | 3.x → 4.x 대응 존재 | B | — | 하위번호 추출 → 대응 확인 |

---

## 3. MIL-STD-38784 기술교범 규칙

### 구현 대상

| ID | 규칙명 | 설명 | 등급 | 기존 규칙 | 구현 방법 |
|---|---|---|:---:|:---:|---|
| 38-A1 | Abbreviation first-use expansion | 약어 첫 사용 시 풀네임 필수 | A | — | `\b[A-Z]{2,}\b` 첫 출현에 인접 풀네임 존재 확인 |
| 38-A2 | Abbreviation list required | 약어 목록 섹션 필수 | A | — | "ABBREVIATIONS"/"약어" 섹션 존재 확인 |
| 38-W1 | WARNING placement | WARNING은 위험 절차 직전 | A | — | WARNING → 다음 단락이 절차 단계인지 (STE-5.1과 통합) |
| 38-W2 | CAUTION placement | CAUTION은 손상 절차 직전 | A | — | 위와 동일 로직 |
| 38-W5 | WARNING/CAUTION capitalized | 전체 대문자 표기 필수 | A | — | `Warning`/`caution` 등 비표준 표기 검출 |
| 38-F1 | Figure ref before appearance | 그림은 참조 후 등장 | A | `figure_caption` 업그레이드 | 참조 위치 < 그림 위치 순서 검증 |
| 38-F2 | Figure sequential numbering | 그림 번호 순차 | A | `figure_caption` 업그레이드 | 기존 번호 연속성 검사 |
| 38-T1 | Table ref before appearance | 표는 참조 후 등장 | A | `table_caption` 업그레이드 | 참조 위치 < 표 위치 순서 검증 |
| 38-T2 | Table sequential numbering | 표 번호 순차 | A | `table_caption` 업그레이드 | 기존 번호 연속성 검사 |
| 38-XR | Cross-ref target exists | 본문 "Figure N"/"Table N" 참조 대상 실존 | A | — | 참조 번호 추출 → 실제 그림/표 목록 대조 |
| 38-U1 | SI units required | SI 단위 사용 필수 | B | — | 비SI 패턴(`inches`, `feet`, `lbs`) 검출 |

---

## 4. 기존 규칙 업그레이드 매핑

| 기존 규칙 | 업그레이드 내용 | 관련 표준 |
|----------|--------------|---------|
| `sentence_length` | 문자 수→단어 수, 절차/설명 구분 (20/25단어) | STE-3.1, 3.2, 38-S1 |
| `forbidden_terms` | 블랙리스트→화이트리스트(승인어 사전) 모드 추가 | STE-1.1 |
| `inconsistent_terms` | 동의어 그룹 맵 확장 | STE-1.5 |
| `figure_caption` | 참조 순서 검증 + 번호 형식 확장 | 38-F1, 38-F2 |
| `table_caption` | 참조 순서 검증 + 번호 형식 확장 | 38-T1, 38-T2 |
| `numbering_continuity` | 961 십진체계 + 깊이 6단계 제한 | 961-N1, 961-N2 |

---

## 5. 구현 우선순위

### Priority 1 — A등급 신규, 즉시 효과

| 순위 | ID | 핵심 | 필요 자원 |
|:---:|---|---|---|
| 1 | 961-S1~S6 | 필수 섹션 존재 검증 | 제목 패턴 매칭 |
| 2 | 961-R2, R3 | shall 위치 제한 | 섹션 범위 + shall 검색 |
| 3 | 38-A1 | 약어 첫 사용 풀네임 | 약어 정규식 + 상태 추적 |
| 4 | 38-W1, W2, W5 | WARNING/CAUTION 배치·서식 | 위치 + 대문자 검사 |
| 5 | 38-XR | 교차참조 역방향 검증 | 참조 번호 ↔ 실제 목록 대조 |
| 6 | STE-6.1 | 단락 6문장 제한 | 문장 카운트 |
| 7 | STE-7.4 | 슬래시 접속사 금지 | 정규식 |

### Priority 2 — A등급 업그레이드

| 순위 | 대상 | 변경 |
|:---:|---|---|
| 8 | sentence_length | 단어 수 기반 + 절차/설명 구분 |
| 9 | figure/table_caption | 참조 순서 검증 추가 |
| 10 | numbering_continuity | 961 깊이 제한 추가 |

### Priority 3 — B등급 (신뢰도 보통)

| 순위 | ID | 비고 |
|:---:|---|---|
| 11 | STE-3.3 | 한 문장 한 지시 (medium confidence) |
| 12 | STE-3.7, 4.1 | 절차 명령형 시작 |
| 13 | STE-3.9 | 종속절 1단계 제한 |
| 14 | 961-R1 | 참조 문서 Section 2 등재 확인 |

### Priority 4 — B등급 (저신뢰도, 기본 OFF)

| 순위 | ID | 비고 |
|:---:|---|---|
| 15 | STE-3.6 | 수동태 감지 (precision ~60%) |
| 16 | STE-2.1 | 명사 클러스터 (TND 없으면 오탐 다수) |

---

## 6. 필요 데이터 자원

| 자원 | 설명 | 규모 |
|------|------|------|
| STE 승인 어휘 사전 | STE100 Section 1 기반 승인 단어 목록 | ~900 entries |
| 기술명사 사전 (TND) | 프로젝트별 기술 용어 화이트리스트 | 사용자 관리 |
| 승인 약어 사전 | 표준 약어 목록 (MIL-STD-12 등) | ~200 entries |
| 동의어 그룹 맵 | 같은 개념의 허용/금지 표현 그룹 | ~50 groups |
| 비SI 단위 블랙리스트 | inches, feet, lbs, psi 등 | ~30 entries |
| STE 금지 동사형 목록 | -ing 시작 금지, 비승인 동사형 | ~100 entries |

---

*수집 기준: ASD-STE100 Issue 8, MIL-STD-961E (2019), MIL-STD-38784 Rev. D*
