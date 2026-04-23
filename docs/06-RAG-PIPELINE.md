# RAG Pipeline

검색 증강 생성(Retrieval-Augmented Generation) 파이프라인 기술 문서

> **이 문서의 역할**: RAG 파이프라인의 **구현 사양**(모듈·파라미터·프롬프트·엔드포인트)을 다룹니다.
> 품질 개선의 **근거·실험 수치·튜닝 히스토리**는 [RAG-TECHNICAL-REPORT](RAG-TECHNICAL-REPORT.md) 를 참조하세요. 두 문서는 짝으로 설계되었으며, 중복 서술 대신 상호 참조로 연결됩니다.

---

## 목차

1. [개요](#1-개요)
2. [문서 처리 파이프라인](#2-문서-처리-파이프라인)
3. [청킹 전략](#3-청킹-전략)
4. [임베딩 모델](#4-임베딩-모델)
5. [검색 전략](#5-검색-전략)
6. [프롬프트 설계](#6-프롬프트-설계)
7. [질문 라우팅 및 고급 RAG](#7-질문-라우팅-및-고급-rag)
8. [LLM 프로바이더 추상화](#8-llm-프로바이더-추상화)
9. [채팅 UI](#9-채팅-ui)
10. [평가 지표](#10-평가-지표)
11. [관련 문서](#11-관련-문서)
12. [참고 자료](#12-참고-자료)

---

## 1. 개요

### RAG란?

```
사용자 질문 → [검색] → 관련 문서 추출 → [생성] → LLM 답변
                ↑                           ↑
           Retrieval                    Generation
```

RAG는 LLM의 환각(hallucination)을 줄이고, 도메인 특화 질문에 정확한 답변을 제공하기 위한 구조입니다.

### 현재 RAG 구성 (요약)

| 영역 | 구성 |
|------|------|
| 문서 처리 | 섹션 단위(h1~h3) + 구조 보존(테이블→GFM MD, 수식→LaTeX) |
| 검색 | 하이브리드(BM25 30% + FAISS 70%, RRF 병합) + Cross-encoder 리랭킹 |
| 생성 | LLM 프로바이더 추상화 (Ollama + OpenAI 호환), `temperature=0` |
| 대화 | 멀티턴 (인메모리 세션, 쿼리 재작성) + 스트리밍(NDJSON) + 피드백 |
| 고급 RAG | 질문 라우팅 · 쿼리 분해 · Agentic RAG 반복 루프 |

> **진화 과정**(Phase 1 키워드 검색 → Phase 2 섹션 청킹 → Phase 3 하이브리드·리랭킹 → Phase 4 고급 RAG)의 **의사결정 근거·실험 수치**는 [RAG-TECHNICAL-REPORT](RAG-TECHNICAL-REPORT.md) 참조.

---

## 2. 문서 처리 파이프라인

### 2.1 섹션 단위 인덱싱 (search-index.json)

```
HTML 문서 → 헤딩 파싱 → 섹션별 분할 → search-index.json
              ↓
         h1, h2, h3 기준 분할
```

**인덱스 구조:**

```json
{
  "title": "1.2 문제 제기",
  "url": "contents/dev-overview/paper.html",
  "section_id": "section-1-2",
  "path": "개발 개요 > 논문 > 1.2 문제 제기",
  "content": "해당 섹션 본문만...",
  "heading_level": 2
}
```

### 2.2 섹션 네비게이션

검색 결과 또는 AI 채팅의 참고 문서 링크 클릭 시 해당 섹션으로 정확히 이동합니다.

**핵심 기술**: `content-visibility: auto`가 적용된 대용량 문서에서는 미렌더링 섹션의 높이가 추정값(500px)으로 대체되므로, 일반적인 `scrollIntoView`가 목표 위치를 놓칩니다. **반복 수렴 스크롤**(`scrollToElementReliably`)로 해결:

```
instant scrollIntoView → 주변 섹션 렌더링 → 위치 재확인 → 수렴 (2~3프레임)
```

**적용 위치**: TOC 클릭, 검색 결과 이동, AI 채팅 참조 링크, 페이지 간 섹션 이동

### 2.3 벡터 인덱싱 (FAISS + bge-m3)

```
search-index.json (섹션 텍스트)
       ↓
  build-vector-index.py
       ↓
  Ollama /api/embed (bge-m3, 1024차원)
       ↓
  batch 임베딩 (32건 단위)
       ↓
  FAISS IndexFlatL2 빌드
       ↓
  data/vector-index/
    ├── vector-index.faiss     (벡터 인덱스)
    └── vector-index_meta.json (메타데이터)
```

**벡터 인덱스 빌드 파이프라인 (`build-vector-index.py`):**
1. `search-index.json`에서 content가 있는 문서 필터링
2. 텍스트 구성: `{title} {title} {content}` (제목 2회 반복 → 가중치 효과)
3. Ollama bge-m3로 배치 임베딩 (32건/배치, 1024차원)
4. FAISS `IndexFlatL2` 생성 및 저장
5. 메타데이터 JSON 저장 (title, content[:500], url, section_id, path)

**증분 추가**: `vector_search.append_documents()`로 업로드 시 전체 재빌드 없이 새 문서만 추가

---

## 3. 청킹 전략

### 현행 설정

| 항목 | 값 | 이유 |
|------|-----|------|
| 청킹 단위 | 섹션 (h1, h2, h3) | 기술문서 구조 보존 |
| 최대 길이 | 3200자 (≈ 800토큰) | LLM 컨텍스트 효율 |
| 최소 길이 | 100자 | 짧은 섹션 병합 기준 |

### 섹션 기반 청킹 로직

```python
def chunk_by_section(html_content):
    """
    HTML에서 섹션 단위로 청크 생성
    """
    chunks = []
    current_section = None

    for heading in find_headings(html_content):  # h1, h2, h3
        # 이전 섹션 저장
        if current_section:
            chunks.append(current_section)

        # 새 섹션 시작
        current_section = {
            'id': generate_section_id(heading),
            'title': heading.text,
            'level': int(heading.tag[1]),
            'content': extract_until_next_heading(heading)
        }

    return chunks
```

### 긴 섹션 처리

섹션이 3200자를 초과하면:
1. 문단(`<p>`) 단위로 분할
2. 섹션 메타데이터 유지

---

## 4. 임베딩 모델

### 모델 선정: BAAI/bge-m3 (Ollama)

| 항목 | 값 |
|------|-----|
| 모델명 | bge-m3 (Ollama 호스팅) |
| 차원 | 1024 |
| API | Ollama `/api/embed` |
| 언어 | 다국어 (한국어 우수) |
| 특징 | Dense + Sparse + ColBERT 지원 |

### 선정 이유

1. **한국어 성능**: 다국어 모델 중 한국어 성능 우수
2. **폐쇄망 호환**: Ollama로 로컬 실행 가능 (외부 API 불필요)
3. **기술문서 적합**: 전문 용어 임베딩 품질 검증됨
4. **통합 인프라**: LLM과 같은 Ollama 서버에서 호스팅 (추가 서비스 불필요)

### 대안 모델

| 모델 | 장점 | 단점 |
|------|------|------|
| multilingual-e5-base | 가벼움 (~1GB) | 한국어 성능 약간 낮음 |
| ko-sroberta | 한국어 특화 | 영어 성능 낮음 |
| bge-m3 | 균형 잡힘, Ollama 지원 | 크기 큼 |

---

## 5. 검색 전략

### 5.1 키워드 검색 (BM25)

`backend/services/keyword_search.py` — kiwipiepy 형태소 분석 + rank-bm25. 제목 가중치는 `title` 필드를 본문 앞에 반복 삽입하여 반영.

### 5.2 하이브리드 검색 (RRF 기반)

```
질문 → [키워드 검색] → 키워드 매칭 결과 (Sparse)
    ↘                                           ↗
      [RRF 점수 병합] → 최종 후보 → [리랭킹] → 최종 결과
    ↗                                           ↘
질문 → [임베딩] → [FAISS 검색] → 의미 유사도 결과 (Dense)
```

**Reciprocal Rank Fusion (RRF) 공식:**

```
rrf_score(d) = Σ  weight_i × 1/(k + rank_i(d))
               i∈{keyword, vector}

최종 점수 = keyword_weight × rrf_keyword + vector_weight × rrf_vector
```

**실제 구현 설정값:**

| 파라미터 | 값 | 설명 |
|----------|-----|------|
| `HYBRID_KEYWORD_WEIGHT` | 0.3 | 키워드 비중 30% |
| 벡터 비중 | 0.7 (= 1 - 0.3) | 의미 검색 비중 70% |
| `HYBRID_RRF_K` | 60 | RRF 상수 (순위 차이 완화) |
| `MIN_VECTOR_SCORE` | 0.48 | 벡터 유사도 임계값 (이하 제거) |

> **RRF 선택 근거·α 선형결합 대비 이점·Cormack (2009) 논문 참조**: [RAG-TECHNICAL-REPORT §6](RAG-TECHNICAL-REPORT.md) 참조.

### 5.3 Cross-encoder 리랭킹

초기 검색(하이브리드)의 상위 후보를 Cross-encoder로 정밀 재정렬합니다.

| 항목 | 값 |
|------|-----|
| 모델 | bge-reranker-v2-m3 (로컬 배포) |
| 저장 위치 | `models/bge-reranker-v2-m3/` |
| 입력 | `[query, doc_text]` 쌍 |
| 최대 토큰 | 512 |
| 후보 수 | `top_k × RERANKER_TOP_K_MULTIPLIER` (기본 5×3=15) |
| 출력 | 상위 `top_k`개 재정렬 |
| 로딩 | Lazy (첫 호출 시 모듈 캐시) |

**Bi-encoder vs Cross-encoder:**
- Bi-encoder (bge-m3): 문서와 쿼리를 독립적으로 인코딩 → 빠르지만 덜 정확
- Cross-encoder (bge-reranker): 문서-쿼리 쌍을 함께 인코딩 → 느리지만 더 정확
- 따라서 Bi-encoder로 넓게 검색 → Cross-encoder로 정밀 필터링하는 2단계 구조

### 5.4 검색 결과 중복 제거

하이브리드 검색에서 키워드/벡터 양쪽에 동일 문서가 나올 수 있으므로 중복 제거를 수행합니다.

- **기준**: `content[:200]` (본문 처음 200자)
- **시점**: 리랭킹 이후 최종 결과에서 적용
- **효과**: 동일 섹션의 중복 노출 방지

---

## 6. 프롬프트 설계

### 6.1 시스템 프롬프트

```
당신은 KF-21 전투기 기술 문서 전문 어시스턴트입니다. 제공된 참고 문서만을 기반으로 답변합니다.

[핵심 규칙]
1. 오직 제공된 문서 내용만 사용
2. 문서에 없는 내용은 절대 추측 금지
3. 정보 없으면 "제공된 문서에서 해당 정보를 찾지 못했습니다" 답변

[답변 방식]
- 핵심 내용 간결 제시
- 불릿/번호 목록 사용
- 기술 용어는 문서 표기대로
- 답변 끝에 참고 문서 제목 명시

[요청 유형별]
- "요약": 3~5문장 핵심
- "핵심 내용": 불릿 5개 이내
- "쉽게 설명": 전문용어 풀어서
- 일반 질문: 직접 답변 후 맥락 보충

[언어] 한국어
```

### 토큰 예산 관리

| 항목 | 최대 문자 수 | 비율 |
|------|-------------|------|
| 시스템 프롬프트 | ~500 | 고정 |
| 컨텍스트 문서 | ~5,000 | 62.5% |
| 대화 기록 | ~2,000 | 25% |
| 질문 | ~500 | 고정 |
| **합계** | **~8,000** | |

**컨텍스트 트리밍:**
1. 대화 기록이 `MAX_HISTORY_LENGTH`(2000자) 초과 → 오래된 턴부터 제거
2. 컨텍스트 문서가 남은 예산 초과 → 문서별 **균등 할당** (최소 500자 보장)
3. 개별 문서 내 잘림은 문서 중간이 아닌 끝부분에서 발생
4. LLM 호출 시 `temperature=0` (결정적 응답)

### 6.2 멀티턴 대화

후속 질문의 컨텍스트를 유지하여 자연스러운 대화를 지원합니다.

**인메모리 세션 저장소 (`conversation.py`):**

| 설정 | 값 | 설명 |
|------|-----|------|
| `MAX_SESSIONS` | 100 | 동시 세션 상한 |
| `MAX_IDLE_MINUTES` | 60 | 유휴 세션 자동 삭제 |
| `MAX_HISTORY_MESSAGES` | 50 | 세션당 최대 메시지 (25턴) |
| `MAX_CONVERSATION_TURNS` | 5 | 프롬프트에 포함할 턴 수 |
| 세션 ID | UUID hex[:16] | 고유 식별자 |

**LRU 퇴거 정책:**
1. 매 세션 생성/조회 시 유휴 시간 초과(60분) 세션 삭제
2. `MAX_SESSIONS`(100) 초과 시 가장 오래된 세션 퇴거

**쿼리 재작성 (`query_rewriter.py`):**

후속 질문에서 대명사·생략 주어를 복원하여 독립적 검색 쿼리로 변환합니다.

```
사용자: "KF-21의 레이더는?"
시스템: (검색 → 답변)
사용자: "그것의 탐지 거리는?"
    ↓ 쿼리 재작성
재작성: "KF-21 레이더 탐지 거리"
    ↓ 하이브리드 검색
    ↓ 리랭킹
    ↓ LLM (대화 기록 포함)
    → 답변
```

**폴백 전략:**
- LLM 쿼리 재작성 실패 시 → 이전 질문 키워드 + 현재 질문 결합
- 재작성 결과가 원본의 3배 이상 길면 → 폴백
- 대화 기록 없으면 → 원본 질문 그대로 사용

**전체 데이터 흐름:**
```
후속 질문 → 세션 조회 → 대화 기록 추출
    ↓
쿼리 재작성 (LLM 기반, 폴백: 키워드 결합)
    ↓
하이브리드 검색 (keyword 30% + vector 70%)
    ↓
Cross-encoder 리랭킹
    ↓
중복 제거
    ↓
LLM 생성 (시스템 프롬프트 + 컨텍스트 + 대화 기록 + 질문)
    ↓
응답 + 대화 기록 저장
```

### 6.3 구조 보존 인덱싱

**문제**: 기존 `strip_html_tags()`는 테이블과 수식의 구조를 완전히 소실시킵니다.

```
# strip_html_tags() 결과 (구조 소실)
"항목 값 항목 값 항목 값"  ← 테이블의 행/열 관계 사라짐
""                          ← MathML 태그 제거 후 빈 문자열
```

**해결**: `html_to_searchable_text()` (tools/html_to_text.py)

```
HTML 원본
    ↓
1. <table> → GFM 마크다운 테이블 (TableConverter)
   | 항목 | 값 |
   | --- | --- |
   | 속도 | Mach 1.8 |

2. <math> → LaTeX (MathConverter)
   $$\frac{L}{D} = \frac{C_L}{C_D}$$

3. 나머지 HTML 태그 제거 + 엔티티 디코딩
    ↓
검색 인덱싱 가능한 텍스트
```

**기술 근거:**
- LLM은 마크다운 테이블을 잘 이해함 (벤치마크 51.9% 정확도, 일반 텍스트 대비 크게 향상)
- LaTeX는 LLM 학습 데이터에 풍부하게 포함되어 있어 수식 이해도가 높음
- 외부 의존성 0 (Python 표준 라이브러리 `html.parser`만 사용)

**병합셀 처리:**
- 단순 테이블 (병합 없음) → GFM 마크다운 테이블
- 병합셀 포함 테이블 → Key-Value 형식 (`항목: 값 | 항목: 값`)
- `colspan`/`rowspan` 확장한 2D 그리드 빌드 → 병합 여부 자동 판별

---

## 7. 질문 라우팅 및 고급 RAG

### 7.1 질문 라우팅 (`question_router.py`)

사용자 질문을 4가지 유형으로 자동 분류하여 최적의 RAG 전략을 적용합니다.

```
사용자 질문
    ↓
[질문 라우터] → LLM 분류 (timeout 10초, 실패 시 SIMPLE 폴백)
    ↓
┌─ SIMPLE ──→ 단일 검색 (기본 RAG)
├─ COMPARE ─→ 쿼리 분해 + 병렬 검색 + 결과 병합
├─ REASON ──→ Agentic RAG (반복 검색-판단 루프)
└─ CHAT ────→ 검색 없이 직접 응답 (인사, 잡담)
```

| 유형 | 설명 | 예시 |
|------|------|------|
| SIMPLE | 정의, 절차, 수치 질문 | "AESA 레이더란?" |
| COMPARE | 비교·대조 질문 | "A와 B의 차이점은?" |
| REASON | 근거 기반 분석·추론 | "왜 X 방식을 선택했나?" |
| CHAT | 인사, 잡담, 주제 외 | "안녕하세요" |

- `config.QUESTION_ROUTING_ENABLED`로 활성/비활성 전환 (기본: True)
- 5자 미만 짧은 질문은 LLM 호출 없이 CHAT으로 즉시 분류

### 7.2 쿼리 분해 (`query_decomposer.py`)

COMPARE 유형의 복합 질문을 1~3개 독립 서브쿼리로 분할하여 병렬 검색 후 결과를 병합합니다.

```
"A와 B의 차이점은?"
    ↓ 쿼리 분해
["A의 특성", "B의 특성"]
    ↓ 각각 검색
결과 병합 → 리랭킹 → LLM 답변
```

- `config.QUERY_DECOMPOSE_ENABLED`로 활성/비활성 전환 (기본: True)
- 서브쿼리 길이: 3~200자, 최대 3개
- 분해 결과가 1개면 원본 질문 그대로 사용 (불필요한 변환 방지)
- LLM 응답 파싱: JSON 배열 → 마크다운 코드블록 → 줄 단위 폴백

### 7.3 Agentic RAG (`rag_agent.py`)

REASON 유형의 질문에 대해 반복적으로 검색-판단-재검색하여 충분한 정보를 수집합니다.

```
질문 → [계획 수립] → 충분한가?
                        ├─ Yes → 종료
                        └─ No → [새 쿼리로 검색] → [중복 제거] → 다시 판단
                        (최대 3회 반복)
```

| 파라미터 | 값 | 설명 |
|----------|-----|------|
| `MAX_ITERATIONS` | 3 | 최대 반복 횟수 |
| 계획 프롬프트 타임아웃 | 15초 | LLM 판단 시간 |
| 충분성 판단 | JSON `{"sufficient": true/false, "query": "..."}` | LLM 출력 |
| 신뢰도 판단 | 문서 수 기반 (0=low, 1=medium, 2+=high) | 결정적 판단 |

- 첫 반복에서 결과가 없으면 원본 질문으로 직접 검색 (폴백)
- 중복 제거: `content[:200]` 기준
- 리랭킹: 원본 질문 기준으로 최종 결과 정렬

### 7.4 스트리밍 응답

`POST /api/chat/stream` 엔드포인트로 NDJSON 형식의 토큰 스트리밍을 지원합니다.

```
{"type": "token", "content": "답변"}
{"type": "token", "content": " 텍스트"}
...
{"type": "done", "sources": [...], "confidence": "high", "reasoning_steps": 2, "route": "REASON"}
```

- rAF(requestAnimationFrame) 기반 렌더링 버퍼링으로 DOM 업데이트 최적화
- 에러 시 `{"type": "error", "message": "..."}` 반환

---

## 8. LLM 프로바이더 추상화

### 8.1 프로바이더 아키텍처 (`llm_provider.py`)

LLM 백엔드를 교체할 수 있는 추상화 계층입니다.

```
┌─ LLMProvider (추상 베이스) ──────────────────┐
│  generate(prompt, system?, timeout?)          │
│  generate_stream(prompt, system?, timeout?)   │
│  health_check()                               │
│  model_name                                   │
├───────────────────────────────────────────────┤
│  ┌─ OllamaProvider ─┐  ┌─ OpenAICompatProvider ─┐
│  │  /api/generate    │  │  /v1/chat/completions  │
│  │  Ollama 전용 API  │  │  vLLM, NIM, TGI 호환  │
│  └───────────────────┘  └────────────────────────┘
└───────────────────────────────────────────────┘
```

| 설정 | 값 | 설명 |
|------|-----|------|
| `LLM_PROVIDER` | `"ollama"` (기본) / `"openai_compat"` | 프로바이더 선택 |
| `LLM_ENDPOINT` | URL | OpenAI 호환 엔드포인트 |
| `LLM_MODEL_ID` | 모델 ID | OpenAI 호환 모델명 |
| `LLM_API_KEY` | 토큰 | Bearer 인증 (선택) |

- **싱글턴 패턴**: 설정 변경 감지 시 자동 인스턴스 재생성
- **타임아웃**: 동기 120초, 스트리밍 300초
- **temperature**: 0 (결정적 응답)
- OpenAI 호환 설정 불완전 시 Ollama로 자동 폴백

### 8.2 LLM 클라이언트 (`llm_client.py`)

프로바이더 위에 프롬프트 구성·토큰 예산 관리를 담당하는 래퍼입니다.

- `generate_response()`: 동기식 응답 (기존 API 호환)
- `generate_response_stream()`: 스트리밍 응답 (토큰 이터레이터 반환)
- 시스템 프롬프트: `config.CHAT_SYSTEM_PROMPT` → 기본 프롬프트 폴백
- 컨텍스트 트리밍: 문서별 균등 할당 (최소 500자 보장)

---

## 9. 채팅 UI

### 9.1 어시스턴트 메시지 스타일

ChatGPT/Claude 스타일로 어시스턴트 답변에는 버블(배경)이 없습니다. 사용자 메시지만 버블로 표시됩니다.

### 9.2 답변 액션 바

답변 하단에 피드백(좋아요/싫어요) + 복사 버튼이 표시됩니다.
- 복사 클릭 시 클립보드 아이콘 → 체크마크로 2초간 전환

### 9.3 스크롤-투-바텀 버튼

채팅 영역에서 위로 스크롤하면 하단 중앙에 `↓` 버튼이 나타납니다.
- `backdrop-filter: blur()` 글래스모피즘 배경
- 스크롤 위치가 바닥에서 80px 이상 떨어지면 표시
- 클릭 시 즉시 최하단으로 스크롤

### 9.4 스트리밍 렌더링 최적화

- rAF 버퍼링: `requestAnimationFrame`으로 DOM 업데이트를 프레임 단위로 배칭
- 델타 어펜드: 전체 텍스트 교체 대신 새로 추가된 부분만 `TextNode`로 추가
- 자동 스크롤: 사용자가 위로 스크롤하지 않은 경우만 자동 스크롤 유지 (임계값 40px)

---

## 10. 평가 지표

### 검색 품질 — 실측 결과

20건 테스트셋 기준 평가 결과:

| 검색 방식 | Recall@5 | MRR |
|-----------|----------|-----|
| 키워드 단독 | 85% | 0.750 |
| 벡터 단독 | 90% | 0.833 |
| **하이브리드 (RRF)** | **100%** | **0.967** |

**하이브리드 검색의 우위:**
- 키워드 검색은 동의어·유사 표현에 약함 (예: "전투기" vs "항공기")
- 벡터 검색은 정확한 명칭·숫자 매칭에 약함 (예: "Mach 1.81")
- 하이브리드는 두 검색의 장점을 결합하여 모든 테스트 케이스에서 정답 포함

### 응답 품질 (정성 평가)

- 정확성: 문서 내용과 일치하는가
- 완전성: 질문에 충분히 답변했는가
- 인용: 출처가 명확한가

---

## 11. 관련 문서

- [05-ARCHITECTURE.md](05-ARCHITECTURE.md): 시스템 구조, 배포 절차
- [RAG-TECHNICAL-REPORT.md](RAG-TECHNICAL-REPORT.md): RAG 답변 품질 개선 기술 보고서
- [04-USER-GUIDE.md](04-USER-GUIDE.md): 검색 인덱스 업데이트 방법

---

## 12. 참고 자료

- 프로젝트 내 연구 논문: `contents/dev-overview/MyPaper_20251109_V2.8_Claude.html`
  - BM25+FAISS 하이브리드 검색 실험 결과
  - α=0.2 최적값 도출 근거
- Cormack, G. V., Clarke, C. L., & Buettcher, S. (2009). Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods. SIGIR.
- BAAI/bge-m3: Multi-Functionality, Multi-Linguality, Multi-Granularity Text Embeddings
- BAAI/bge-reranker-v2-m3: Cross-encoder Reranker
