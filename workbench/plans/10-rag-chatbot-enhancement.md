# 지식기반 챗봇 고도화 계획서

> **문서 번호**: Plan-10
> **작성일**: 2026-03-10
> **상태**: ✅ 구현 완료 (Phase 1~3), Phase 4~5는 환경/별도 계획으로 이관
> **대상 시스템**: Explorer RAG 챗봇

---

## 진행 현황

| 단계 | 내용 | 상태 | 비고 |
|:----:|------|:----:|------|
| **준비** | 베이스라인 측정 (4b, 15문항) | ✅ 완료 | 정확도 3.8/5, 적중률 97% → `test-results/rag-baseline-v2-4b.md` |
| **Phase 1** | 모델 업그레이드 + 스트리밍 + 프로바이더 추상화 | ✅ 완료 | 1-A 모델설정, 1-B 스트리밍, 1-C 프로바이더 |
| **Phase 2** | 쿼리 분해 + 메타데이터 인덱싱 + 컨텍스트 확장 | ✅ 완료 | 2-A 쿼리분해, 2-B 메타데이터필터, 2-C 설정확장 |
| **Phase 3** | Agentic RAG 루프 + 질문 라우터 + 신뢰도 | ✅ 완료 | 3-A Agent루프, 3-B 라우터, 3-C 신뢰도표시 |
| **Phase 4** | 사내 MLOps 엔드포인트 연동 | ⏸ 보류 | 4-A 프로바이더 구현 완료(Phase 1), 4-B/4-C는 사내 서버 확보 후 진행 |
| **Phase 5** | 세션 영속화, 프롬프트 설정, 피드백, 표 QA | ➡ 이관 | 5-B+5-C → 별도 계획서(Plan-11)로 분리, 5-A/5-D는 필요 시 |

---

## 1. 현황 분석

### 1.1 현재 아키텍처

```
사용자 질문
    ↓
[세션 관리] ← 인메모리 LRU (100세션, 60분 TTL)
    ↓
[쿼리 재작성] ← Ollama (후속질문 → 독립 쿼리)
    ↓
[하이브리드 검색] ← 키워드(30%) + 벡터(70%) RRF 병합
    ↓
[리랭킹] ← bge-reranker-v2-m3 (Cross-Encoder)
    ↓
[LLM 응답 생성] ← Ollama gemma3:4b, stream=false
    ↓
[응답 + 출처] → 프론트엔드 렌더링
```

### 1.2 현재 구성 요소

| 구성 요소 | 현재 상태 | 비고 |
|-----------|-----------|------|
| **LLM** | gemma3:4b (Ollama) | 3B 활성 파라미터, 추론 능력 제한적 |
| **임베딩** | bge-m3 (1024차원) | 260 섹션 인덱싱, FAISS IndexFlatL2 |
| **검색** | 하이브리드 (키워드 + 벡터 + RRF) | MIN_VECTOR_SCORE=0.48 |
| **리랭킹** | bge-reranker-v2-m3 | Cross-Encoder, GPU 가속 |
| **대화 관리** | 인메모리 세션, 5턴 제한 | 서버 재시작 시 소실 |
| **쿼리 재작성** | Ollama 기반, 키워드 폴백 | 단순 대명사 치환 수준 |
| **응답 방식** | 동기 (stream=false) | 60초 타임아웃, 전체 대기 |
| **프롬프트** | 고정 시스템 프롬프트 (KF-21 특화) | 코드 수정 필요 |
| **컨텍스트** | 최대 8000자 (문서 + 히스토리) | 문서별 500자 최소 보장 |

### 1.3 인프라 환경

| 항목 | 사양 |
|------|------|
| **GPU** | NVIDIA L40-48Q (vGPU, Ada Lovelace) |
| **VRAM** | 48GB GDDR6 ECC |
| **메모리 대역폭** | 864 GB/s |
| **배포 모델** | gemma3:27b (현재 회사 서버에 배포) |
| **추가 GPU** | VM이므로 필요 시 L40 1장 추가 가능 |
| **네트워크** | 폐쇄망 (인터넷 차단) |
| **LLM 서빙** | Ollama (현재), 사내 MLOps 엔드포인트 연동 예정 |

### 1.4 gemma3:27b 활용 시 예상 성능

| 양자화 | 모델 VRAM | KV캐시 포함 | 추정 속도 | 비고 |
|--------|----------|------------|----------|------|
| Q8_0 | ~28GB | ~32-36GB | 15-20 tok/s | **권장** — L40 48GB에 여유 |
| Q4_K_M | ~14GB | ~18-24GB | 20-30 tok/s | 품질 약간 감소, 속도 우선 시 |
| BF16 | ~54GB | >54GB | N/A | VRAM 초과, 불가 |

- gemma3:27b는 128K 토큰 컨텍스트 윈도우 지원
- Gemini 1.5 Pro 급 벤치마크 (MMLU, GSM8K)
- 복잡한 지시 이해, 다문서 종합, 구조화 출력에서 4b 대비 현저한 차이

---

## 2. 티어별 역량 분석

### 2.1 역량 매트릭스

| 티어 | 질문 유형 | 예시 질문 | 구현 가능? | 필요 기술 | 현재 미달 원인 |
|:---:|:----------|:----------|:---:|:----------|:--------------|
| **1** | **단순 검색/조회** | | | | |
| 1-1 | 정의·용어 질문 | "감항인증이란?" | ✅ 구현됨 | 키워드 검색 + 용어집 | — |
| 1-2 | 특정 조항 찾기 | "MIL-STD-810 Section 5.2 내용은?" | ✅ 구현됨 | 섹션 단위 벡터 인덱싱 | — |
| 1-3 | 수치/스펙 조회 | "허용 진동 주파수 범위는?" | ✅ 구현됨 | 정확한 청크 매칭 | — |
| 1-4 | 절차 안내 | "복합재 수리 절차를 알려줘" | ✅ 구현됨 | 순차적 청크 검색 | — |
| **2** | **비교·종합** | | | | |
| 2-1 | 문서 간 비교 | "MIL-STD-810과 사내 기준의 차이점은?" | ⚠️ → ✅ | 쿼리 분해 + 멀티 검색 | 단일 쿼리로는 양쪽 동시 히트 불안정 |
| 2-2 | 요약·종합 | "구조 시험 전체 절차를 요약해줘" | ⚠️ → ✅ | 긴 컨텍스트 + 27b 모델 | 4b 모델 요약 품질 부족, 8000자 제한 |
| 2-3 | 조건부 필터링 | "2024년 이후 변경된 규격만 알려줘" | ❌ → ✅ | 메타데이터 인덱싱 + 필터 | 날짜/버전/문서유형 메타 없음 |
| 2-4 | 멀티홉 질문 | "A규격에서 참조하는 B규격의 내용은?" | ⚠️ → ✅ | 쿼리 분해 (decomposition) | 재작성은 있으나 분해 없음 |
| **3** | **추론·분석** | | | | |
| 3-1 | 근거 기반 판단 | "이 설계가 MIL-STD-XXX를 만족하는가?" | ❌ → ⚠️ | 27b + CoT 프롬프팅 | 4b로는 추론 깊이 부족 → 27b로 개선 |
| 3-2 | 갭 분석 | "시험 절차에서 빠진 항목은?" | ❌ → ⚠️ | Agent 패턴 (반복 검색) | 단일 패스 RAG만 지원 |
| 3-3 | What-if 시나리오 | "진동 기준을 10% 높이면 영향은?" | ❌ → ❌ | 도메인 파인튜닝 | 범용 모델의 한계, 전문 학습 필요 |
| 3-4 | 크로스 문서 추적 | "요구사항 → 설계 → 시험 추적" | ❌ → ⚠️ | 관계 그래프 + Agent | 문서 간 참조 관계 미구축 |
| **4** | **멀티모달·고급** | | | | |
| 4-1 | 도면/그림 해석 | "이 도면에서 Part 3은 어디인가?" | ❌ | Vision LLM | gemma3:27b에 Vision 있으나 정밀도 미검증 |
| 4-2 | 표 데이터 분석 | "시험 결과 표의 최대값은?" | ⚠️ → ✅ | Table QA + 수치 연산 | GFM 테이블 변환은 있으나 연산 없음 |
| 4-3 | 문서 초안 생성 | "시험 보고서 초안을 작성해줘" | ❌ → ⚠️ | 긴 생성 + 템플릿 | 구조화 생성은 27b로 가능, 서식은 별도 |

### 2.2 구현 가능성 요약

| 구분 | 항목 | 현재 | 고도화 후 |
|:---:|:---:|:---:|:---:|
| Tier 1 (검색/조회) | 4 | **4/4 (100%)** | 4/4 (유지) |
| Tier 2 (비교/종합) | 4 | **1/4 (25%)** | **4/4 (100%)** |
| Tier 3 (추론/분석) | 4 | **0/4 (0%)** | **2/4 (50%)** |
| Tier 4 (멀티모달) | 3 | **0/3 (0%)** | **1/3 (33%)** |

> **목표**: Tier 2 완전 달성 + Tier 3 부분 진입
> **현실적 한계**: Tier 3-3(What-if)은 도메인 파인튜닝 없이 불가, Tier 4-1(도면)은 Vision 모델 정밀도 한계

---

## 3. 온프레미스 RAG 솔루션 비교

계획 수립에 앞서, 기존 솔루션과 자체 구축의 타당성을 검토한다.

| 솔루션 | 장점 | 단점 | 우리 환경 적합성 |
|--------|------|------|:---:|
| **GPT4All LocalDocs** | 설치 간편, 완전 로컬 | 벡터 전용(하이브리드 없음), 리랭킹 없음, API 없음, 웹 통합 불가 | ❌ |
| **AnythingLLM** | 멀티유저, Agent 지원, Docker | 추상화 레이어 추가, 우리 검색 파이프라인 대체 불가 | ❌ |
| **PrivateGPT** | 단순, 완전 로컬 | 단일 사용자, 커넥터 부족, 웹 통합 불가 | ❌ |
| **Open WebUI** | 성숙한 UI, 문서 관리 | Ollama 종속, 검색 파이프라인 유연성 부족 | ❌ |
| **Danswer/Onyx** | 40+ 커넥터, 기업용 | 과도한 인프라, 폐쇄망 배포 복잡 | ❌ |
| **자체 파이프라인 (현재)** | 완전한 제어, 플랫폼 통합, 커스텀 검색 | 개발 공수 필요 | ✅ |

**결론**: 기존 솔루션은 모두 **독립형 애플리케이션**으로, 우리 플랫폼(Explorer)에 통합 불가.
현재 자체 파이프라인(FastAPI + FAISS + bge-m3 + bge-reranker)이 이미 대부분의 솔루션보다 우수한 검색 품질을 보유하고 있으므로, **기존 구조를 확장하는 방향이 최적**.

---

## 4. LLM 프로바이더 추상화 설계

### 4.1 배경

현재 시스템은 Ollama API에 직접 의존한다. 향후 사내 AI 조직의 MLOps 플랫폼(예: Kubeflow Serving, NVIDIA NIM, vLLM, TGI 등)에서 배포된 모델의 엔드포인트를 연결할 수 있어야 한다.

### 4.2 엔드포인트 유형

MLOps 플랫폼에서 모델을 배포하면 일반적으로 다음 형태의 엔드포인트를 제공한다:

| 프로토콜 | URL 예시 | 특징 |
|----------|---------|------|
| **OpenAI-compatible** | `https://model-server/v1/chat/completions` | 업계 표준, vLLM/TGI/NIM 모두 지원 |
| **Ollama** | `http://host:11434/api/generate` | 현재 사용 중 |
| **커스텀 REST** | `https://internal-api/predict` | 사내 독자 규격 가능 |

> 대부분의 MLOps 도구(vLLM, NVIDIA NIM, TGI, Triton)는 **OpenAI-compatible API**를 지원한다.

### 4.3 추상화 구조

```
┌──────────────────────────────────────────────┐
│           LLM Provider Interface              │
│  generate(prompt, options) → stream/response  │
│  embed(text) → vector                         │
│  health_check() → bool                        │
└────────┬──────────┬──────────┬────────────────┘
         │          │          │
    ┌────▼───┐ ┌───▼────┐ ┌──▼──────────────┐
    │ Ollama │ │OpenAI- │ │ Custom REST     │
    │Provider│ │compat  │ │ Provider        │
    │        │ │Provider│ │ (사내 MLOps)    │
    └────────┘ └────────┘ └─────────────────┘
```

### 4.4 구현 설계

```python
# backend/services/llm_provider.py

class LLMProvider:
    """LLM 프로바이더 인터페이스"""
    async def generate(self, prompt, system=None, stream=False, **opts): ...
    async def generate_stream(self, prompt, system=None, **opts): ...
    async def embed(self, text) -> list[float]: ...
    async def health_check(self) -> bool: ...

class OllamaProvider(LLMProvider):
    """현재 Ollama 백엔드 (하위 호환)"""
    def __init__(self, url, model, embed_model): ...

class OpenAICompatProvider(LLMProvider):
    """OpenAI-compatible API (vLLM, NIM, TGI, 사내 MLOps)"""
    def __init__(self, base_url, api_key, model): ...
    # POST {base_url}/v1/chat/completions
    # POST {base_url}/v1/embeddings

class CustomRESTProvider(LLMProvider):
    """사내 독자 규격 엔드포인트"""
    def __init__(self, endpoint, headers, request_template): ...
```

### 4.5 설정 확장

```python
# config.py 추가 항목
LLM_PROVIDER = "ollama"           # "ollama" | "openai_compat" | "custom"
LLM_ENDPOINT = ""                 # OpenAI-compat / Custom 엔드포인트 URL
LLM_API_KEY = ""                  # API 키 (필요 시)
LLM_MODEL_ID = ""                 # 엔드포인트의 모델 ID
EMBEDDING_PROVIDER = "ollama"     # 임베딩도 별도 프로바이더 가능
EMBEDDING_ENDPOINT = ""           # 임베딩 전용 엔드포인트 (다를 수 있음)
```

관리자 설정 UI에서 프로바이더 전환 가능하도록 설계한다.

---

## 5. 고도화 단계별 계획

### Phase 1: 기반 강화 (LLM 업그레이드 + 스트리밍)

**목표**: 체감 품질 즉시 향상, 사용자 경험 개선
**예상 공수**: 3-4일
**위험도**: 낮음 (기존 구조 유지, API 추가)

#### 1-A. LLM 모델 업그레이드 (gemma3:27b)

**변경 사항**:
- `config.py`: `OLLAMA_MODEL = "gemma3:27b"`
- 기존 코드 수정 없음 — 설정값만 변경

**기대 효과**:
- 답변 품질 즉시 향상 (요약, 비교, 구조화 출력)
- 복잡한 지시 이해도 향상 (멀티스텝 프롬프트)
- 한국어 생성 품질 향상

**VRAM 산정**:
```
gemma3:27b Q8_0:     ~28GB
bge-m3 임베딩:        ~2GB
bge-reranker-v2-m3:  ~1GB
KV 캐시 (8K ctx):    ~4GB
────────────────────────
합계:                ~35GB / 48GB (여유: 13GB)
```

#### 1-B. 스트리밍 응답 구현

현재 `stream=false`로 전체 응답 대기(5~30초). 토큰 단위 스트리밍으로 체감 응답 시간을 1초 이내로 단축.

**백엔드 변경**:
```python
# backend/api/chat.py — 새 엔드포인트 추가

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    # 기존 검색 + 컨텍스트 구성 동일
    context = await _search_internal(query, ...)
    prompt = build_prompt(question, context, history)

    async def generate():
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", f"{OLLAMA_URL}/api/generate",
                json={"model": MODEL, "prompt": prompt, "stream": True}
            ) as resp:
                async for chunk in resp.aiter_lines():
                    yield chunk + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")
```

**프론트엔드 변경** (`js/ai-chat.js`):
```javascript
// ReadableStream으로 NDJSON 파싱
var response = await fetch(API + '/api/chat/stream', { method: 'POST', body: ... });
var reader = response.body.getReader();
var decoder = new TextDecoder();
while (true) {
    var result = await reader.read();
    if (result.done) break;
    var lines = decoder.decode(result.value).split('\n').filter(Boolean);
    for (var i = 0; i < lines.length; i++) {
        var json = JSON.parse(lines[i]);
        appendToken(json.response);  // 토큰 단위 실시간 렌더링
    }
}
```

**하위 호환**: 기존 `/api/chat` 엔드포인트 유지 (비스트리밍 모드 지원)

#### 1-C. LLM 프로바이더 추상화 (Phase 1에서 구조만 구축)

- `backend/services/llm_provider.py` 생성
- `OllamaProvider` 구현 (현재 `llm_client.py` 코드 이전)
- `OpenAICompatProvider` 스텁 구현
- `config.py`에 `LLM_PROVIDER` 설정 추가
- 기존 `llm_client.py`는 프로바이더를 호출하는 래퍼로 전환

이 단계에서는 Ollama만 사용하되, 추후 사내 MLOps 엔드포인트 연동 시 설정 변경만으로 전환 가능한 구조를 확보한다.

---

### Phase 2: 검색 고도화 (Tier 2 완전 달성)

**목표**: 비교·종합·멀티홉 질문 지원
**예상 공수**: 5-7일
**위험도**: 중간 (검색 파이프라인 확장)

#### 2-A. 쿼리 분해 (Query Decomposition)

복합 질문을 서브쿼리로 분해하여 각각 독립 검색 후 결과를 병합한다.

**동작 흐름**:
```
"MIL-STD-810과 사내 기준의 진동 시험 차이점은?"
    ↓ LLM 쿼리 분해
서브쿼리 1: "MIL-STD-810 진동 시험 기준"
서브쿼리 2: "사내 표준 진동 시험 기준"
    ↓ 각각 하이브리드 검색
결과 1: [MIL-STD-810 관련 청크 3개]
결과 2: [사내 기준 관련 청크 3개]
    ↓ 병합 + 리랭킹
통합 컨텍스트 → LLM 비교 응답 생성
```

**구현 위치**: `backend/services/query_decomposer.py` (신규)

```python
DECOMPOSE_PROMPT = """질문을 분석하여 독립적인 검색 쿼리로 분해하세요.

규칙:
1. 단순 질문은 분해하지 않고 그대로 반환
2. 비교/대조 질문은 각 대상별 쿼리로 분해
3. 멀티홉 질문은 단계별 쿼리로 분해
4. 최대 3개 서브쿼리로 제한
5. JSON 배열로만 출력: ["쿼리1", "쿼리2"]

질문: {question}
서브쿼리:"""

async def decompose_query(question: str) -> list[str]:
    result = await llm_provider.generate(DECOMPOSE_PROMPT.format(question=question))
    queries = parse_json_array(result)
    return queries if len(queries) > 1 else [question]
```

**검색 흐름 변경**:
```python
# 기존: 단일 쿼리 → 단일 검색
results = hybrid_search(query, top_k=5)

# 변경: 쿼리 분해 → 멀티 검색 → 병합
sub_queries = await decompose_query(query)
all_results = []
for sq in sub_queries:
    results = hybrid_search(sq, top_k=3)
    all_results.extend(results)
# 중복 제거 + 리랭킹 (원본 질문 기준)
final = rerank(question, deduplicate(all_results), top_k=5)
```

#### 2-B. 메타데이터 인덱싱

검색 인덱스에 구조화 메타데이터를 추가하여 필터링 검색을 지원한다.

**인덱스 확장**:
```json
{
    "title": "Section Title",
    "content": "...",
    "url": "page.html",
    "section_id": "sec-001",
    "path": "pages/page.html",
    "metadata": {
        "doc_type": "standard",
        "doc_category": "구조 설계",
        "parent_doc": "MIL-STD-810",
        "depth": 2
    }
}
```

**메타데이터 추출**: `build-search-index.py` 확장
- `menu.json` 계층 구조에서 `doc_category` 자동 매핑
- HTML `<meta>` 태그 또는 첫 번째 헤딩에서 문서 유형 추출
- 경로 기반 depth 계산

**필터 검색 API**:
```python
# POST /api/search 확장
{
    "query": "진동 시험",
    "filters": {
        "doc_category": "시험 · 평가",
        "doc_type": "standard"
    }
}
```

#### 2-C. 컨텍스트 윈도우 확장

gemma3:27b의 128K 토큰 윈도우를 활용하여 더 많은 컨텍스트를 제공한다.

**변경**:
```python
# config.py
MAX_CONTEXT_LENGTH = 16000   # 8000 → 16000자 (27b 모델 여유 활용)
MAX_HISTORY_LENGTH = 4000    # 2000 → 4000자
MAX_SEARCH_RESULTS = 7       # 5 → 7 (더 많은 문서 참조)
```

**주의**: VRAM의 KV 캐시 사용량이 증가하므로 단계적으로 늘려가며 모니터링.

---

### Phase 3: 지능형 RAG (Tier 3 진입)

**목표**: Agent 패턴 도입, 반복적 추론 가능
**예상 공수**: 7-10일
**위험도**: 중간~높음 (새로운 아키텍처 패턴)

#### 3-A. Agentic RAG 루프

단일 패스 RAG를 **반복적 검색-판단-재검색** 루프로 확장한다.

```
사용자 질문
    ↓
[판단] 질문 유형 분류 (단순검색 / 비교 / 추론 / 부적합)
    ↓
[단순검색] → 기존 파이프라인 (Phase 1-2)
    ↓
[비교/추론] → Agent 루프 진입
    ↓
┌─ Agent Loop (최대 3회) ─────────────────────┐
│  1. 쿼리 계획 수립 (어떤 정보가 필요한가?)    │
│  2. 검색 실행 (하이브리드 / 메타데이터 필터)   │
│  3. 충분성 판단 (정보가 충분한가?)             │
│     ├─ 충분 → 최종 응답 생성                  │
│     └─ 부족 → 보완 쿼리 생성 → 1로 돌아감     │
└─────────────────────────────────────────────┘
```

**핵심 구현**: `backend/services/rag_agent.py` (신규)

```python
MAX_AGENT_ITERATIONS = 3

async def agentic_rag(question: str, session) -> dict:
    """Agent 루프 RAG"""
    collected_context = []

    for i in range(MAX_AGENT_ITERATIONS):
        # 1. 계획: 어떤 정보를 더 찾아야 하는지 판단
        plan = await plan_next_search(question, collected_context)

        if plan["sufficient"]:
            break

        # 2. 검색: 계획에 따라 실행
        new_results = await execute_search(plan["query"], plan.get("filters"))
        collected_context.extend(new_results)

        # 3. 중복 제거
        collected_context = deduplicate(collected_context)

    # 최종 응답 생성
    return await generate_response(question, collected_context, session.history)
```

#### 3-B. 질문 유형 분류 (Router)

모든 질문에 Agent 루프를 적용하면 느리므로, 질문 유형에 따라 경로를 분기한다.

```python
ROUTE_PROMPT = """질문을 분류하세요. 하나만 출력:
- SIMPLE: 정의, 절차, 수치 조회 등 단순 질문
- COMPARE: 비교, 대조, 종합이 필요한 질문
- REASON: 근거 판단, 분석, 추론이 필요한 질문
- CHAT: 인사, 잡담, 문서와 무관한 질문

질문: {question}
분류:"""

async def route_question(question: str) -> str:
    result = await llm_provider.generate(ROUTE_PROMPT.format(question=question))
    return result.strip().upper()  # "SIMPLE", "COMPARE", "REASON", "CHAT"
```

**라우팅 전략**:

| 분류 | 처리 경로 | 응답 시간 |
|------|----------|----------|
| SIMPLE | 기존 단일 패스 RAG | 3-5초 |
| COMPARE | 쿼리 분해 + 멀티 검색 (Phase 2) | 5-10초 |
| REASON | Agent 루프 (최대 3회) | 10-20초 |
| CHAT | 검색 없이 LLM 직접 응답 | 2-3초 |

#### 3-C. 응답 신뢰도 표시

Agent 루프 결과에 신뢰도 메타데이터를 포함하여 사용자에게 투명성을 제공한다.

```json
{
    "answer": "...",
    "sources": [...],
    "confidence": "high",
    "reasoning_steps": 2,
    "search_queries_used": ["쿼리1", "쿼리2", "보완쿼리"]
}
```

프론트엔드에서 `confidence` 값에 따라 시각적 표시:
- **high**: 일반 표시
- **medium**: "⚠ 일부 정보가 부족할 수 있습니다" 안내
- **low**: "⚠ 관련 문서를 충분히 찾지 못했습니다" 안내

---

### Phase 4: 사내 LLM 엔드포인트 연동

**목표**: MLOps 플랫폼 배포 모델 연동
**예상 공수**: 2-3일 (인터페이스는 Phase 1에서 준비 완료)
**위험도**: 낮음 (프로바이더 추가만)

#### 4-A. OpenAI-compatible 프로바이더 구현

사내 MLOps 플랫폼(vLLM, NVIDIA NIM, Triton 등)은 대부분 OpenAI-compatible API를 제공한다:

```
POST {endpoint}/v1/chat/completions
Authorization: Bearer {api_key}

{
    "model": "deployed-model-id",
    "messages": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."}
    ],
    "stream": true,
    "temperature": 0
}
```

**구현**:
```python
class OpenAICompatProvider(LLMProvider):
    def __init__(self, base_url, api_key="", model="default"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def generate_stream(self, prompt, system=None, **opts):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient() as client:
            async with client.stream("POST",
                f"{self.base_url}/v1/chat/completions",
                json={"model": self.model, "messages": messages,
                      "stream": True, **opts},
                headers=headers
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        chunk = json.loads(line[6:])
                        yield chunk["choices"][0]["delta"].get("content", "")
```

#### 4-B. 관리자 설정 UI 확장

관리자 설정 → AI 설정 탭에 프로바이더 선택 및 엔드포인트 설정 추가:

```
┌─ AI 모델 설정 ──────────────────────────────┐
│                                              │
│  프로바이더:  ○ Ollama  ○ OpenAI-compat      │
│              ○ 사내 MLOps                    │
│                                              │
│  ── Ollama ──────────────────────────        │
│  서버 URL:   [http://localhost:11434    ]     │
│  모델:       [gemma3:27b               ]     │
│                                              │
│  ── OpenAI-compat / 사내 MLOps ──────        │
│  엔드포인트: [https://mlops.internal/v1]     │
│  API 키:     [****                     ]     │
│  모델 ID:    [company-llm-v2           ]     │
│                                              │
│  ── 임베딩 ──────────────────────────        │
│  프로바이더:  ○ 동일  ○ 별도 설정            │
│  엔드포인트: [                         ]     │
│                                              │
│  [연결 테스트]              [저장]            │
└──────────────────────────────────────────────┘
```

#### 4-C. 연결 테스트 API

```python
@router.post("/api/settings/test-llm")
async def test_llm_connection(config: LLMConfig):
    """프로바이더 연결 + 간단한 생성 테스트"""
    provider = create_provider(config)
    healthy = await provider.health_check()
    if healthy:
        # 간단한 테스트 생성
        result = await provider.generate("안녕하세요라고 답하세요.", temperature=0)
        return {"status": "ok", "response": result[:100]}
    return {"status": "error", "message": "연결 실패"}
```

---

### Phase 5: 고급 기능 (선택적 확장)

**목표**: Tier 3 깊이 확보, 사용성 개선
**예상 공수**: 각 기능별 2-3일
**위험도**: 개별 기능별 독립적, 선택 적용

#### 5-A. 대화 세션 영속화

현재 인메모리 세션을 SQLite로 영속화하여 서버 재시작 후에도 대화 이력 유지.

```python
# analytics.db에 테이블 추가 (또는 별도 chat.db)
CREATE TABLE chat_sessions (
    id TEXT PRIMARY KEY,
    username TEXT,
    created_at TIMESTAMP,
    last_active TIMESTAMP
);

CREATE TABLE chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT REFERENCES chat_sessions(id),
    role TEXT,        -- 'user' | 'assistant'
    content TEXT,
    sources TEXT,     -- JSON
    created_at TIMESTAMP
);
```

**효과**: 사용자별 대화 기록 열람, 자주 묻는 질문 분석, 품질 모니터링 가능.

#### 5-B. 시스템 프롬프트 관리자 설정화

현재 하드코딩된 KF-21 전용 프롬프트를 관리자 UI에서 수정 가능하도록 변경.

```python
# settings.json 확장
{
    "chat_system_prompt": "당신은 {domain} 기술 문서 전문 어시스턴트입니다...",
    "chat_domain": "항공 기술"
}
```

#### 5-C. 답변 품질 피드백 루프

사용자 피드백(👍/👎)을 수집하여 검색/프롬프트 개선에 활용.

```
┌────────────────────────────────┐
│ 답변 내용...                    │
│                                │
│ 출처: [문서1] [문서2]           │
│ 👍 도움이 됐어요  👎 아쉬워요   │
└────────────────────────────────┘
```

**데이터 활용**:
- 👎 비율 높은 질문 유형 → 프롬프트/검색 개선 우선순위
- 👍 답변의 검색 결과 패턴 → 검색 가중치 최적화

#### 5-D. 표 데이터 정밀 QA

GFM 테이블을 구조화 파싱하여 수치 질문에 대응.

```python
# 테이블 감지 + 구조화
def extract_tables(context: str) -> list[dict]:
    """GFM 마크다운 테이블 → 딕셔너리 리스트"""
    # | col1 | col2 | → [{"col1": "val1", "col2": "val2"}, ...]
    ...

# 수치 연산 프롬프트
TABLE_QA_PROMPT = """다음 표 데이터에서 질문에 답하세요.
정확한 수치를 사용하고, 계산이 필요하면 과정을 보여주세요.
표: {table_json}
질문: {question}"""
```

---

## 6. 구현 로드맵

```
Phase 1 (기반 강화)                             Phase 2 (검색 고도화)
┌──────────────────────┐                        ┌──────────────────────┐
│ 1-A. 모델 업그레이드  │ ← 설정 변경만          │ 2-A. 쿼리 분해       │
│ 1-B. 스트리밍 응답    │ ← 체감 즉시 개선       │ 2-B. 메타데이터 인덱싱│
│ 1-C. 프로바이더 추상화│ ← 향후 확장 기반       │ 2-C. 컨텍스트 확장    │
└──────────┬───────────┘                        └──────────┬───────────┘
           ↓                                               ↓
Phase 3 (지능형 RAG)                             Phase 4 (사내 LLM 연동)
┌──────────────────────┐                        ┌──────────────────────┐
│ 3-A. Agent 루프      │                        │ 4-A. OpenAI-compat   │
│ 3-B. 질문 라우터     │                        │ 4-B. 관리자 설정 UI  │
│ 3-C. 신뢰도 표시     │                        │ 4-C. 연결 테스트     │
└──────────┬───────────┘                        └──────────┬───────────┘
           ↓                                               ↓
Phase 5 (고급 기능) ─── 선택적 적용 ───────────────────────
┌──────────────────────────────────────────────────────────┐
│ 5-A. 세션 영속화  │ 5-B. 프롬프트 설정  │ 5-C. 피드백   │
│ 5-D. 표 QA       │                     │               │
└──────────────────────────────────────────────────────────┘
```

### 우선순위 및 의존 관계

| Phase | 선행 조건 | 산출물 | Tier 달성 |
|:-----:|:---------:|:------:|:---------:|
| **1** | 없음 | 27b 모델 적용, 스트리밍 UI, 프로바이더 인터페이스 | Tier 1 유지 + 품질↑ |
| **2** | Phase 1 완료 | 쿼리 분해, 메타 필터, 확장 컨텍스트 | **Tier 2 완전 달성** |
| **3** | Phase 2 완료 | Agent 루프, 질문 라우터, 신뢰도 | **Tier 3 부분 진입** |
| **4** | Phase 1-C 완료 | 사내 LLM 연동, 관리자 UI | 인프라 확장 |
| **5** | Phase 1 이후 언제든 | 각 기능별 독립 적용 | 품질·사용성 개선 |

---

## 7. 고도화 전후 비교

### 기대 효과 종합

| 항목 | 현재 (Before) | 고도화 후 (After) |
|------|:---:|:---:|
| **LLM** | gemma3:4b | gemma3:27b (+ 사내 LLM 전환 가능) |
| **응답 방식** | 전체 대기 (5~30초) | 스트리밍 (첫 토큰 ~1초) |
| **검색 전략** | 단일 쿼리 하이브리드 | 쿼리 분해 + 멀티 검색 + Agent 루프 |
| **컨텍스트** | 8000자 / 5개 문서 | 16000자 / 7개 문서 |
| **대화 턴** | 5턴 (인메모리) | 5턴 + SQLite 영속화 |
| **질문 라우팅** | 없음 (모두 동일 처리) | 유형별 최적 경로 분기 |
| **메타데이터 필터** | 없음 | 문서 유형, 카테고리 필터 |
| **신뢰도** | 없음 | high/medium/low 표시 |
| **LLM 연동** | Ollama 전용 | Ollama + OpenAI-compat + 사내 MLOps |
| **Tier 수준** | Tier 1 완전 + Tier 2 일부 | **Tier 2 완전 + Tier 3 부분** |

### 현실적 한계 (정직한 평가)

| 항목 | 한계 원인 | 대안 |
|------|----------|------|
| **Tier 3-3 (What-if)** | 도메인 파인튜닝 없는 범용 모델의 한계 | 사내 AI팀의 도메인 학습 모델 배포 시 해소 가능 |
| **Tier 4-1 (도면 해석)** | 기술 도면의 정밀한 이해는 현 Vision LLM 한계 | 전용 도면 인식 모델 필요 |
| **동시 접속** | 27b 모델 단일 GPU 처리량 한계 (~15-20 tok/s) | GPU 추가 또는 vLLM 배치 서빙 |
| **실시간 인덱싱** | 전체 인덱스 리빌드 구조 | 증분 인덱싱 개발 (별도 과제) |

---

## 8. 성능 비교 프레임워크

### 8.1 목적

각 Phase 적용 전후의 품질 변화를 **정량적으로 측정**하여, 개선 효과를 객관적으로 입증한다.
베이스라인(4b)은 Phase 1 착수 전에 반드시 먼저 측정해둔다.

### 8.2 표준 테스트 질문 세트

동일 질문으로 Before/After를 비교한다. 질문은 Tier별로 구성.

#### Tier 1 — 단순 검색/조회 (5문항)

> 대상 문서에서 특정 사실/수치/정의를 정확히 추출하는 능력 측정

| # | 질문 | 대상 문서 | 기대 답변 핵심 | 검증 포인트 |
|:-:|------|----------|--------------|------------|
| T1-1 | "KF-21의 주요 특징을 알려줘" | introduction.html | 스텔스, AESA 레이더, 전자전, 네트워크 중심전 | 4가지 핵심 특징 정확 추출 |
| T1-2 | "BM25와 FAISS의 차이점은?" | RAG 논문 | 희소 검색 vs 밀집 검색 설명 | 기술 용어 정확성 |
| T1-3 | "DRACO 시스템의 주요 기능은?" | SWA_Sample_KOR | DRL 충돌회피, 군집 통신 | 유즈케이스 기반 기능 나열 |
| T1-4 | "FY 2020 국방 연구소 총 예산은?" | FY1 보고서 | $558.6M | 정확한 수치 인용 |
| T1-5 | "부품 생성 요청 절차를 설명해줘" | SWA_PMS (UC-02) | 설계자→부품공학팀 요청 흐름 | 절차 순서 정확성 |

#### Tier 2 — 비교/종합 (5문항)

> 두 개 이상의 문서/섹션에서 정보를 수집하여 비교·종합하는 능력 측정

| # | 질문 | 대상 문서 | 기대 답변 핵심 | 검증 포인트 |
|:-:|------|----------|--------------|------------|
| T2-1 | "육군과 공군의 FY 2020 연구 활동 차이점은?" | FY1 보고서 | 육군 $163.8M/281건 vs 공군 $98.6M/57건, 중점 분야 차이 | 양쪽 수치 모두 포함 |
| T2-2 | "PLM 시스템의 품질 속성을 요약해줘" | SWA_PMS (QA-01~05) | 성능(<2초), 가용성(<10초 복구), 보안 등 5개 | 5개 QA 시나리오 종합 |
| T2-3 | "하이브리드 검색 실험에서 최적 설정값은?" | RAG 논문 (실험결과) | α=0.2, Top-k=8, Recall=1.0, nDCG=0.99 | 수치 정확성 + 근거 제시 |
| T2-4 | "DRACO의 유즈케이스를 우선순위별로 정리해줘" | SWA_Sample_KOR | UC-05~07 High, UC-02/04 Medium | 7개 UC 종합 + 우선순위 |
| T2-5 | "KF-21 개발 일정을 단계별로 정리해줘" | introduction.html | 2015 계약~2021 시험, Block 1→2→3 | 연도별 마일스톤 종합 |

#### Tier 3 — 추론/분석 (5문항)

> 문서 정보를 기반으로 분석, 판단, 교차 검증하는 능력 측정

| # | 질문 | 대상 문서 | 기대 답변 핵심 | 검증 포인트 |
|:-:|------|----------|--------------|------------|
| T3-1 | "하이브리드 검색이 단일 검색보다 나은 이유를 실험 결과로 설명해줘" | RAG 논문 | nDCG 64.5% 향상, Recall 26.6% 향상 등 수치 근거 | 데이터 기반 논증 |
| T3-2 | "DRACO의 품질 속성 중 가장 달성하기 어려운 것은?" | SWA_Sample_KOR | QA-01(0.05초) 또는 QA-02(0.01% 오류율) + 근거 | 분석적 판단 + 이유 |
| T3-3 | "PLM 시스템의 설계 결정(DD-01~03)이 품질 속성을 어떻게 만족시키는지 설명해줘" | SWA_PMS | DD-01→QA-01/02, DD-02→QA-03/05, DD-03→QA-04/02 매핑 | 설계-품질 연결 추론 |
| T3-4 | "FY 2014~2020 국방 연구소 예산 추세를 분석해줘" | FY1 보고서 | $249M→$558.6M (6년간 2배 증가), 카테고리별 변화 | 추세 분석 + 수치 해석 |
| T3-5 | "KF-21의 AESA 레이더와 전자전 능력이 네트워크 중심전에 어떻게 기여하는지 설명해줘" | introduction.html | AESA→다중표적 추적, EW→생존성, NCW→통합 전투력 | 크로스 개념 연결 추론 |

### 8.3 측정 지표

| 지표 | 측정 방법 | 단위 |
|------|----------|------|
| **응답 시간** | 질문 전송 → 전체 응답 완료 | 초 (s) |
| **첫 토큰 지연** | 질문 전송 → 첫 글자 표시 (스트리밍 시) | 초 (s) |
| **검색 적중률** | 정답 출처가 반환된 sources에 포함되는지 | O/X |
| **답변 정확도** | 핵심 정보가 정확히 포함되었는지 (수동 평가) | 1~5점 |
| **답변 완성도** | 질문 의도를 충분히 충족하는지 (수동 평가) | 1~5점 |
| **환각 여부** | 문서에 없는 내용을 생성했는지 | O/X |

**점수 기준**:
- 5점: 완벽 — 정확하고 충분한 답변
- 4점: 우수 — 핵심 정보 포함, 사소한 누락
- 3점: 보통 — 방향은 맞지만 불완전
- 2점: 부족 — 핵심 누락 또는 부정확
- 1점: 실패 — 무관한 답변 또는 "정보를 찾지 못했습니다"

### 8.4 Before/After 비교 테이블 (기록 양식)

#### Phase 1 비교: gemma3:4b → 파이프라인 개선

| # | 질문 | 모델 | 응답시간 | 검색적중 | 정확도 | 완성도 | 환각 | 비고 |
|:-:|------|:---:|:---:|:---:|:---:|:---:|:---:|------|
| T1-1 | KF-21의 주요 특징을 알려줘 | 4b | 6.6초 | O | 5/5 | 5/5 | X | 5가지 핵심 특징 완벽 추출 |
| | | After | _초 | O/X | _/5 | _/5 | O/X | |
| T1-2 | BM25와 FAISS의 차이점은? | 4b | 6.3초 | O | 4/5 | 4/5 | X | 희소/밀집 구분 정확 |
| | | After | _초 | O/X | _/5 | _/5 | O/X | |
| T1-3 | DRACO 시스템의 주요 기능은? | 4b | 6.1초 | O | 4/5 | 3/5 | X | UC 세부사항 부족 |
| | | After | _초 | O/X | _/5 | _/5 | O/X | |
| T1-4 | FY 2020 국방 연구소 총 예산은? | 4b | 5.6초 | O | 5/5 | 5/5 | X | $558.6M 정확 |
| | | After | _초 | O/X | _/5 | _/5 | O/X | |
| T1-5 | 부품 생성 요청 절차를 설명해줘 | 4b | 7.8초 | O | 4/5 | 5/5 | X | UC-02 기반 6단계 절차 |
| | | After | _초 | O/X | _/5 | _/5 | O/X | |
| T2-1 | 육군과 공군의 FY 2020 연구 활동 차이점은? | 4b | 7.5초 | O | 4/5 | 4/5 | X | 양쪽 수치 포함 |
| | | After | _초 | O/X | _/5 | _/5 | O/X | |
| T2-2 | PLM 시스템의 품질 속성을 요약해줘 | 4b | 7.1초 | O | 4/5 | 4/5 | X | QA-01~05 나열, 수치 미포함 |
| | | After | _초 | O/X | _/5 | _/5 | O/X | |
| T2-3 | 하이브리드 검색 실험에서 최적 설정값은? | 4b | 6.8초 | O | 3/5 | 3/5 | X | Top-k, Threshold 수치 오류 |
| | | After | _초 | O/X | _/5 | _/5 | O/X | |
| T2-4 | DRACO의 유즈케이스를 우선순위별로 정리해줘 | 4b | 7.1초 | O | 3/5 | 3/5 | X | 5/7개만 나열, 우선순위 오류 |
| | | After | _초 | O/X | _/5 | _/5 | O/X | |
| T2-5 | KF-21 개발 일정을 단계별로 정리해줘 | 4b | 5.8초 | O | 4/5 | 3/5 | X | Block 1-3 미포함 |
| | | After | _초 | O/X | _/5 | _/5 | O/X | |
| T3-1 | 하이브리드 검색이 단일 검색보다 나은 이유를 실험 결과로 설명해줘 | 4b | 11.6초 | O | 4/5 | 5/5 | X | 5가지 근거 체계적 |
| | | After | _초 | O/X | _/5 | _/5 | O/X | |
| T3-2 | DRACO의 품질 속성 중 가장 달성하기 어려운 것은? | 4b | 7.0초 | O | 3/5 | 3/5 | △ | 수치 목표 미고려 |
| | | After | _초 | O/X | _/5 | _/5 | O/X | |
| T3-3 | PLM 시스템의 설계 결정이 품질 속성을 어떻게 만족시키는지 설명해줘 | 4b | 10.8초 | △ | 3/5 | 4/5 | △ | DRACO DD-03 혼입 |
| | | After | _초 | O/X | _/5 | _/5 | O/X | |
| T3-4 | FY 2014~2020 국방 연구소 예산 추세를 분석해줘 | 4b | 7.1초 | O | 4/5 | 3/5 | X | 추세 정확, 카테고리 분석 부족 |
| | | After | _초 | O/X | _/5 | _/5 | O/X | |
| T3-5 | KF-21의 AESA 레이더와 전자전 능력이 네트워크 중심전에 어떻게 기여하는지 설명해줘 | 4b | 7.8초 | O | 3/5 | 3/5 | △ | 추론 깊이 부족 |
| | | After | _초 | O/X | _/5 | _/5 | O/X | |

#### 단계별 누적 비교 (요약)

| Phase | 모델/변경사항 | Tier 1 평균 | Tier 2 평균 | Tier 3 평균 | 평균 응답시간 |
|:-----:|:---:|:---:|:---:|:---:|:---:|
| **Before** | gemma3:4b | **4.4**/5 | **3.5**/5 | **3.5**/5 | **7.4초** |
| Phase 1 | 4b + 파이프라인 개선 | _/5 | _/5 | _/5 | _초 |
| Phase 2 | + 쿼리분해 + 메타필터 | _/5 | _/5 | _/5 | _초 |
| Phase 3 | + Agent 루프 | _/5 | _/5 | _/5 | _초 |

### 8.5 베이스라인 측정 절차

**Phase 1 착수 전**, 현재 환경(gemma3:4b)에서 반드시 수행:

1. 백엔드 서버 시작 (평소 환경 그대로)
2. 15개 테스트 질문을 순서대로 입력
3. 각 질문마다: 응답 시간 기록, sources 확인, 답변 스크린샷 또는 텍스트 저장
4. 비교 테이블에 Before 열 기록
5. 결과 파일 저장: `workbench/test-results/rag-baseline-v2-4b.md`

> **완료** (2026-03-10): 베이스라인 v2 측정 완료. 결과 요약 — 전체 정확도 3.8/5, 검색 적중률 97%, 환각률 10%, 평균 응답시간 7.4초. 상세 결과는 `workbench/test-results/rag-baseline-v2-4b.md` 참조.
>
> **참고**: v1 질문 세트는 인덱스 콘텐츠와 불일치하여 적중률 0%였음. 인덱스 내 실제 문서에 맞게 질문을 교체한 v2로 재측정. v1 원본은 `rag-baseline-4b.json`, `rag-baseline-4b.md`에 보존.

---

## 9. 검증 계획

### Phase 1 검증
- [x] **베이스라인 측정 완료** (2026-03-10, v2 질문 세트, 결과: 3.8/5 정확도, 97% 적중률)
- [ ] gemma3:27b 모델 로드 확인 (VRAM 사용량 모니터링: `nvidia-smi`)
- [ ] 동일 15문항으로 27b 측정 → Before/After 비교 테이블 작성
- [ ] 스트리밍 응답 첫 토큰 지연 측정 (목표: < 2초)
- [ ] 프로바이더 추상화 단위 테스트

### Phase 2 검증
- [ ] Tier 2 질문(T2-1~T2-5) 재측정 → Phase 1 대비 개선 확인
- [ ] 비교 질문: 양쪽 문서 모두 검색되는지
- [ ] 멀티홉 질문: 2단계 검색 동작 확인
- [ ] 메타데이터 필터: 카테고리별 검색 정확도
- [ ] 컨텍스트 확장 후 VRAM 안정성 (장시간 운용 테스트)

### Phase 3 검증
- [ ] Tier 3 질문(T3-1~T3-5) 재측정 → Phase 2 대비 개선 확인
- [ ] 질문 라우터 정확도: 15개 테스트 질문 분류 정확도 80% 이상
- [ ] Agent 루프: 단순 질문에서 1회 종료, 복합 질문에서 2-3회 반복 확인
- [ ] 응답 시간: SIMPLE < 5초, COMPARE < 10초, REASON < 20초
- [ ] 신뢰도 표시 적절성 (수동 평가)

### Phase 4 검증
- [ ] 사내 MLOps 엔드포인트 연결 테스트 (연결 테스트 API)
- [ ] Ollama ↔ OpenAI-compat 전환 후 동일 질문 응답 비교
- [ ] 관리자 설정 저장/복원 확인

---

## 부록: 참고 기술 정보

### A. gemma3:27b VRAM 프로파일 (L40-48Q 기준)

```
[모델 웨이트]          28GB (Q8_0)
[bge-m3 임베딩]         2GB
[bge-reranker]          1GB
[KV 캐시 8K ctx]       ~4GB
[KV 캐시 16K ctx]      ~8GB
[OS/드라이버]           2GB
─────────────────────────
8K 기준 합계:         ~37GB (여유 11GB)
16K 기준 합계:        ~41GB (여유  7GB)
```

### B. Ollama 스트리밍 프로토콜

요청:
```json
POST /api/generate
{"model": "gemma3:27b", "prompt": "...", "stream": true}
```

응답 (NDJSON, 줄 단위):
```json
{"model":"gemma3:27b","response":"안","done":false}
{"model":"gemma3:27b","response":"녕","done":false}
{"model":"gemma3:27b","response":"하","done":false}
...
{"model":"gemma3:27b","response":"","done":true,"total_duration":1234567890}
```

### C. OpenAI-compatible API 스트리밍 프로토콜 (SSE)

요청:
```json
POST /v1/chat/completions
{"model": "model-id", "messages": [...], "stream": true}
```

응답 (SSE, `text/event-stream`):
```
data: {"choices":[{"delta":{"content":"안"}}]}
data: {"choices":[{"delta":{"content":"녕"}}]}
...
data: [DONE]
```

### D. 파일 변경 예상 목록

| Phase | 신규 파일 | 수정 파일 |
|:-----:|-----------|-----------|
| 1 | `backend/services/llm_provider.py` | `config.py`, `llm_client.py`, `api/chat.py`, `js/ai-chat.js` |
| 2 | `backend/services/query_decomposer.py` | `api/chat.py`, `vector_search.py`, `build-search-index.py` |
| 3 | `backend/services/rag_agent.py` | `api/chat.py`, `js/ai-chat.js` |
| 4 | — | `llm_provider.py`, `js/admin-settings.js`, `api/settings.py` |
| 5 | — | `conversation.py`, `llm_client.py`, `js/ai-chat.js` |
