# Verify(Compare) 시스템 — 설계 문서

DOCX/PDF 문서 비교 → 듀얼 diff + AI 의미 분류 + 유사도 검사 + 규칙 검증 + 검토 리포트

---

## 목차

1. [개요](#1-개요)
2. [화면 구성](#2-화면-구성)
3. [비교 파이프라인](#3-비교-파이프라인)
4. [AI 의미 분류](#4-ai-의미-분류)
5. [검증 모드](#5-검증-모드)
6. [수락/거절 + 검토 리포트](#6-수락거절--검토-리포트)
7. [백엔드 API](#7-백엔드-api)
8. [설정](#8-설정)
9. [데이터 구조](#9-데이터-구조)

---

## 1. 개요

### 시스템 정체성

Verify(Compare)는 **비교·유사도·규칙검증·검토 판정 도구**다. 3-모드 허브(비교 / 유사도 검사 / 규칙 검증)를 통해 문서 품질을 다각도로 평가한다.

- **비교 모드**: 두 문서 버전 간 차이를 시각화하고, AI가 변경의 의미를 자동 분류하며, 검토자가 수락/거절을 판정
- **유사도 검사**: Winnowing(구문) + bge-m3(시맨틱) 2계층 파이프라인으로 유사도를 정밀 측정
- **규칙 검증**: 21종 규칙 엔진으로 문서 작성 규칙 준수 여부를 자동 검증, Acrolinx 밀도 방식 스코어링

세션 이력 저장을 지원하며, 검토 리포트를 XLSX/HTML/TXT로 내보낼 수 있다.

### 핵심 특징

| 항목 | 설명 |
|------|------|
| 3-모드 허브 | 비교(diff) / 유사도 검사 / 규칙 검증 모드 전환 |
| 비교 모드 | 듀얼 패널 diff (추가/삭제/수정), 단어 수준 하이라이트, 동기 스크롤 |
| AI 의미 분류 | Ollama 구조화 출력 6태그 → 3그룹 시각화 (주의·참고·편집) |
| 유사도 검사 | Winnowing L1(구문 지문) + bge-m3 L3(시맨틱 임베딩), 6종 지표 |
| 규칙 엔진 | 21종 규칙 (번호 연속성, 캡션, 금지어, 용어 통일, 문장 길이, 구조 등) |
| 스코어링 | Acrolinx 밀도 방식 (이슈 수/단어 수), 인텔리전스 패널 (스코어카드·구조·용어) |
| 검토 리포트 | XLSX, HTML, TXT 다형식 내보내기 |
| 미니맵 | 스크롤바 오버레이에 변경점/이슈 위치 마커 (PyCharm 스타일) |
| 입력 방식 | DOCX/PDF 파일 업로드 또는 텍스트 직접 붙여넣기 (DRM 환경 대응) |
| diff 라이브러리 | jsdiff (클라이언트사이드, `js/lib/jsdiff/diff.min.js`) |
| 텍스트 추출 | DOCX: python-docx, PDF: PyMuPDF (서버사이드) |
| 세션 이력 | 비교/검증 결과 자동 저장, 이력 조회·재열람 |
| 권한 | 비교/AI 분류/유사도: viewer 이상 / 규칙 저장: admin |

---

## 2. 화면 구성

### 2.1 전체 레이아웃

```
┌─ 플랫폼 헤더 ─────────────────────────────────────────────┐
├─ 툴바 ───────────────────────────────────────────────────┤
│  [비교|검증] [◀▶탐색] [스왑] [동기] [필터] [AI분석] [리포트] │
├───────────────┬──────┬────────────────┬─────────────────┤
│  패널 A (원본)  │핸들  │  패널 B (수정본)  │   사이드바       │
│               │     │                │  변경점 목록     │
│  단락 diff     │ ↔  │  단락 diff      │  수락/거절 버튼  │
│  하이라이트     │     │  하이라이트      │  AI 태그 배지   │
│               │     │                │                 │
│  미니맵 오버레이 │     │  미니맵 오버레이  │                 │
└───────────────┴──────┴────────────────┴─────────────────┘
```

### 2.2 3-모드 허브

툴바 좌측의 모드 탭으로 전환:

- **비교 모드**: 두 문서의 텍스트 diff 표시, AI 분류, 수락/거절
- **유사도 검사**: 두 문서 간 구문/시맨틱 유사도 다계층 분석
- **규칙 검증**: 단일 문서의 규칙 위반 검사, 이슈 하이라이트, 스코어링

모드 전환 시 사이드바, 필터, 탐색 버튼이 해당 모드에 맞게 토글된다.

### 2.3 주요 UI 요소

**문서 입력**:
- 파일 업로드: 패널 플레이스홀더에서 DOCX/PDF 드래그 앤 드롭 또는 클릭
- 텍스트 붙여넣기: 플레이스홀더의 "텍스트 붙여넣기" 링크 → textarea 입력

**동기 스크롤**:
- 좌우 패널의 `scrollTop` 비율을 동기화
- 툴바 토글 버튼으로 ON/OFF

**변경점 탐색**:
- ▲▼ 버튼 또는 키보드 ↑↓로 변경점/이슈 순회
- 현재 위치 표시기 ("3/12")

**미니맵**:
- 각 패널 스크롤바 위에 반투명 오버레이
- 변경점(비교 모드) 또는 이슈(검증 모드) 위치를 컬러 마커로 표시
- 마커 클릭으로 해당 위치 스크롤 이동

**사이드바**:
- 우측 접을 수 있는 패널 (기본 열림)
- 비교 모드: 변경점 목록 + 수락/거절 버튼 + AI 태그 배지
- 검증 모드: 이슈 목록 (오류/경고/제안) + 점수 표시
- 변경 요약: 추가/삭제/수정 건수 배지

**단락 번호**: 툴바 버튼으로 좌우 패널에 단락 번호 표시 토글

**원본↔수정본 스왑**: 스왑 버튼으로 패널 A/B 문서 교체

---

## 3. 비교 파이프라인

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

텍스트 붙여넣기 모드에서는 서버 호출 없이 클라이언트에서 직접 줄 분리 → paragraphs 배열 생성.

### 3.2 diff 계산 (클라이언트사이드)

두 문서의 paragraphs가 준비되면 jsdiff로 diff 계산:

1. **단락 매칭**: `Diff.diffArrays(parasA, parasB)` — 단락 단위 추가/삭제/유지 판별
2. **단어 수준 diff**: 수정(modified)된 단락 쌍에 대해 `Diff.diffWords(textA, textB)` — 단어 단위 변경점 추출
3. **갭 라인 정렬**: 추가/삭제 시 반대편 패널에 빈 줄(gap line) 삽입 → 좌우 시각적 정렬
4. **결과**: `diffState.changes[]` — 각 항목에 `{ type, indexA, indexB, textA, textB, wordDiff }` 포함

### 3.3 렌더링

- 추가(added): 우측 패널에 초록 배경 (`--diff-added-bg`)
- 삭제(deleted): 좌측 패널에 빨강 배경 (`--diff-deleted-bg`)
- 수정(modified): 양쪽 패널에 노랑 배경 + 단어 수준 `<span>` 하이라이트
- 필터: 추가/삭제/수정 개별 표시/숨김, 공백 무시 옵션
- diff 색상은 `tokens.css`의 `--diff-*` 변수 사용 (다크모드 자동 전환)

### 3.4 동기 스크롤

```javascript
function syncScroll(source, target) {
    var ratio = source.scrollTop / (source.scrollHeight - source.clientHeight);
    target.scrollTop = ratio * (target.scrollHeight - target.clientHeight);
}
```

갭 라인이 양쪽 패널의 높이를 맞추므로, 비율 기반 동기화가 자연스럽게 동작한다.

---

## 4. AI 의미 분류

### 4.1 3그룹 체계

6개 태그를 3개 시각적 그룹으로 매핑:

| 그룹 | 태그 | 색상 | 의미 |
|------|------|------|------|
| **주의** (Attention) | `STRICTER`, `MORE_LENIENT` | 빨강 (`--color-error`) | 요구사항 강화/완화 — 검토 필수 |
| **참고** (Info) | `EXPANDED`, `CLARIFICATION` | 파랑 (`--active-color`) | 내용 추가/명확화 — 인지 필요 |
| **편집** (Editorial) | `EDITORIAL`, `RESTRUCTURED` | 회색 (`--text-light`) | 편집/구조 변경 — 의미 변화 없음 |

### 4.2 분류 흐름

```
사용자: 툴바 [AI 분석] 버튼 클릭
    ↓
프론트엔드: diffState.changes에서 변경 구간 추출
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

### 4.3 Ollama 호출 상세

- **구조화 출력**: `format` 파라미터에 JSON Schema 전달 → LLM이 스키마 준수 JSON 출력
- **Few-shot 프롬프트**: 5개 예시 포함 (STRICTER, CLARIFICATION, EXPANDED, STRICTER, MORE_LENIENT)
- **판단 기준**: "의무 vs 허용" 관점 — 시스템 의무 강화=STRICTER, 사용자 제약 완화=MORE_LENIENT
- **temperature=0**: 분류 일관성 최대화

### 4.4 태그 드롭다운 수동 재분류

사이드바에서 AI 태그 배지를 클릭하면 드롭다운으로 6태그 중 수동 선택 가능. 수동 변경된 항목은 리포트에 "(수동)" 표기.

### 4.5 AI 필터

필터 드롭다운에 AI 분류 섹션 추가:
- 태그별 체크박스 (STRICTER, MORE_LENIENT, EXPANDED, CLARIFICATION, EDITORIAL, RESTRUCTURED)
- "주의 필요만 보기" 프리셋 버튼 (STRICTER + MORE_LENIENT만 표시)

---

## 5. 검증 모드

### 5.1 규칙 엔진 아키텍처

```
프론트엔드: 검증 탭 선택 → 문서 업로드
    ↓
POST /api/compare/validate { paragraphs[], preset? }
    ↓
백엔드 (compare_service.py):
    1. compare-rules.json에서 프리셋 규칙 로드
    2. 활성화된 규칙별 runner 실행
    3. 이슈 목록 생성 + 점수 계산
    ↓
응답: { score, summary: { error, warning, suggestion }, issues[] }
    ↓
프론트엔드: 이슈 하이라이트 + 사이드바 목록 표시
```

### 5.2 자체 규칙 6종

| 규칙 ID | 카테고리 | 설명 |
|---------|---------|------|
| `numbering_continuity` | structure | 번호 체계 연속성 (1.1 → 1.3 누락 감지) |
| `table_caption` | structure | 표 캡션 번호 연속성 + 본문 참조 여부 |
| `figure_caption` | structure | 그림 캡션 번호 연속성 + 본문 참조 여부 |
| `forbidden_terms` | terminology | 금지 용어 감지 (대체어 제안) |
| `inconsistent_terms` | terminology | 동일 그룹 내 복수 용어 사용 감지 (최빈 용어 통일 권장) |
| `sentence_length` | readability | 문장 길이 초과 (기본 80자) |

> 위 6종은 `backend/rules/custom.json`에 정의된 자체 규칙이다. 이 외에 ASD-STE100 기반 8종(`ste-writing.json`)과 MIL-STD 기반 7종(`mil-structure.json`)이 추가로 탑재되어 **총 21종 규칙**을 제공한다. 표준 규칙의 상세 분석은 [12-VERIFY-SYSTEM.md](12-VERIFY-SYSTEM.md) 참조.

### 5.3 규칙 관리

- **프리셋**: `compare-rules.json`에 프리셋별 규칙 설정 저장
- **관리 API**: `GET /api/compare/rules` (조회), `PUT /api/compare/rules` (저장, admin)
- **프론트엔드**: 검증 모드 설정 버튼 → 규칙 활성/비활성, 심각도 변경, 파라미터 편집
- 각 규칙의 `enabled`, `severity` (error/warning/suggestion), `params` 개별 설정 가능

### 5.4 점수 계산

```
score = 100 − (error × 10 + warning × 3 + suggestion × 1)
```

최소 0점. 점수와 심각도별 건수가 사이드바 상단에 표시.

### 5.5 이슈 하이라이트

각 이슈는 `paragraph_index`, `char_start`, `char_end`를 포함하여 해당 위치에 마커 하이라이트를 렌더링. 사이드바 항목 클릭 시 해당 위치로 스크롤 이동.

---

## 6. 수락/거절 + 검토 리포트

### 6.1 판정 워크플로우

비교 모드에서 각 변경점에 대해:

- **수락** (✓): 변경이 적절함 → 사이드바 항목 초록 강조
- **거절** (✗): 변경이 부적절함 → 사이드바 항목 빨강 강조
- **미처리**: 아직 판정하지 않음

**키보드**: Enter(수락), Delete(거절)로 현재 선택 항목 판정.

### 6.2 벌크 처리

사이드바 헤더의 벌크 버튼:
- **전체 수락** (✓): 모든 변경점을 수락
- **전체 거절** (✗): 모든 변경점을 거절

AI 분류 완료 시 그룹별 벌크 처리도 가능 (예: "편집 그룹 전체 수락").

### 6.3 리포트 형식

검토 리포트 버튼 → 텍스트 파일 (.txt) 다운로드:

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

--- 미처리 항목 ---
[15] 수정 | 미처리 | EDITORIAL | "시스템은" → "본 시스템은"
```

미처리 항목이 있으면 내보내기 전 확인 다이얼로그 표시.

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

### AI 의미 분류

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/ai-classify` | POST | viewer | diff 변경 구간 AI 의미 분류 |

- 입력: `{ changes: [{ index, type, text_a, text_b }] }` (최대 200건)
- 응답: `{ classifications: [{ index, tag, confidence, explanation }] }`
- 배치 처리: `COMPARE_AI_BATCH_SIZE` (기본 20) 단위로 분할 호출
- 실패 시: 1회 재시도 → 최종 실패 시 `tag: "UNKNOWN"` 반환

### 유사도 검사

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/similarity` | POST | viewer | 두 문서 간 유사도 다계층 분석 |

- 입력: `{ paragraphs_a[], paragraphs_b[] }`
- 2계층 파이프라인:
  - **L1 (Winnowing)**: 텍스트 지문(fingerprint) 기반 구문 수준 유사도
  - **L3 (시맨틱 임베딩)**: bge-m3 기반 의미 수준 유사도
- 6종 유사도 지표 반환: 전체, 구문, 의미, 코사인, 자카드, 보일러플레이트 제외
- 보일러플레이트 제외: `data/boilerplate-phrases.json`에 정의된 상용구 자동 제외

### 문서 추출

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/extract-document` | POST | viewer | 문서 텍스트 추출 (규칙 정의 목록 포함) |

### 규칙 정의

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/rule-definitions` | GET | viewer | 사용 가능한 규칙 정의 목록 (이름, 설명, 파라미터) |

### 내보내기

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/export` | POST | viewer | 검토 리포트 내보내기 |

- 입력: `{ format, changes, decisions, classifications, ... }`
- 지원 형식: `xlsx` (Excel), `html` (시각적 리포트), `txt` (텍스트)
- XLSX: 시트별 구분 (변경점, 판정, AI 분류, 규칙 이슈)

### 세션 이력

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/history` | GET | viewer | 비교/검증 세션 이력 조회 |
| `/history` | POST | viewer | 세션 결과 저장 |

---

## 8. 설정

`backend/config.py` 내 Compare 관련 설정:

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `COMPARE_AI_ENABLED` | `True` | AI 의미 분류 활성화 |
| `COMPARE_AI_MODEL` | `""` (OLLAMA_MODEL 폴백) | 분류용 Ollama 모델 |
| `COMPARE_AI_TEMPERATURE` | `0` | 분류 일관성 최대화 |
| `COMPARE_AI_BATCH_SIZE` | `20` | 1회 LLM 호출당 최대 변경 구간 수 |
| `COMPARE_AI_TIMEOUT` | `60` (초) | LLM 호출 타임아웃 |
| `COMPARE_AI_SYSTEM_PROMPT` | `""` (기본 내장 프롬프트) | 커스텀 시스템 프롬프트 |

**유사도 검사 설정:**

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `VERIFY_SIMILARITY_THRESHOLD_HIGH` | `0.8` | 높은 유사도 판정 임계값 |
| `VERIFY_SIMILARITY_THRESHOLD_MEDIUM` | `0.5` | 중간 유사도 판정 임계값 |

관리자 설정 페이지(`admin.html`)에서 런타임 변경 가능 (재시작 불필요).

---

## 9. 데이터 구조

### 9.1 compare-rules.json

규칙 프리셋 설정 파일. `data/compare-rules.json`에 저장.

```json
{
  "active_preset": "technical",
  "presets": {
    "technical": {
      "name": "기술문서",
      "rules": {
        "numbering_continuity": {
          "enabled": true,
          "severity": "error",
          "params": {}
        },
        "table_caption": {
          "enabled": true,
          "severity": "warning",
          "params": {}
        },
        "forbidden_terms": {
          "enabled": true,
          "severity": "warning",
          "params": {
            "terms": [
              { "term": "어쩌면", "replacement": "경우에 따라" }
            ]
          }
        },
        "inconsistent_terms": {
          "enabled": true,
          "severity": "suggestion",
          "params": {
            "groups": [
              ["비행제어장치", "비행 제어 장치", "FCS"]
            ]
          }
        },
        "sentence_length": {
          "enabled": true,
          "severity": "suggestion",
          "params": { "max_chars": 80 }
        }
      }
    }
  }
}
```

### 9.2 프론트엔드 상태 (휘발성)

모든 상태는 브라우저 메모리에만 존재하며, 새로고침 시 초기화된다.

```javascript
// 문서 상태
var docState = {
    a: { file: null, text: null, paragraphs: [], filename: '' },
    b: { file: null, text: null, paragraphs: [], filename: '' }
};

// diff 상태
var diffState = {
    changes: [],           // diff 결과 배열
    currentIndex: -1,      // 현재 선택된 변경점
    decisions: [],         // null | 'accepted' | 'rejected'
    aiClassifications: null, // AI 분류 결과
    filter: { added: true, deleted: true, modified: true },
    aiFilter: { STRICTER: true, MORE_LENIENT: true, ... },
    ignoreWhitespace: false
};
```

### 9.3 파일 구조

```
프론트엔드
├── compare.html                   ← Compare SPA (모놀리식 HTML, inline JS)
├── css/tokens.css                 ← 디자인 토큰 (diff 색상 변수 포함)
├── css/compare.css                ← Compare 전용 스타일
├── css/components.css             ← 공통 컴포넌트 (버튼, 배지 등)
├── css/modal.css                  ← 모달 스타일
├── css/platform-header.css        ← 공통 헤더 스타일
├── js/lib/jsdiff/diff.min.js      ← jsdiff 라이브러리
├── js/platform-header.js          ← 공통 헤더 컴포넌트
└── js/config.js                   ← AUTH_CONFIG (backendUrl)

백엔드
├── backend/api/compare.py              ← Verify API 라우터
├── backend/services/compare_service.py ← 텍스트 추출, AI 의미 분류
├── backend/services/similarity_engine.py ← 유사도 검사 (Winnowing + 시맨틱 임베딩)
├── backend/services/rule_engine.py     ← 규칙 검증 엔진 (21종)
├── backend/services/export_service.py  ← 검토 리포트 내보내기 (XLSX/HTML/TXT)
└── backend/config.py                   ← COMPARE_AI_*, VERIFY_* 설정

데이터
├── data/compare-rules.json             ← 규칙 프리셋 설정
├── data/boilerplate-phrases.json       ← 유사도 검사 보일러플레이트 제외 구문
├── data/compare/                       ← 비교 세션 데이터
└── data/verify/                        ← 검증 결과
```
