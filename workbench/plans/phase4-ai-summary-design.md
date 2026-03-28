# Phase 4 설계서: AI 요약·Q&A + 추출 전용 파이프라인

> 작성일: 2026-03-27
> 최종 수정: 2026-03-27 (업계 조사 기반 크기 적응형 전략 반영)
> 상태: 설계 확정
> 소속: Plan-19 Phase 4
> 브랜치: `plan17-library`

---

## 1. 배경과 문제 정의

### 1.1 시스템 성격 전환

Translator(번역기)에서 **Notebook(지식 노트북)** 으로 전환이 진행 중이다.
번역은 핵심 기능 중 하나일 뿐, 사용자는 원문을 그대로 읽고·메모하고·요약받는 시나리오도 많다.

### 1.2 현재 데이터 흐름의 문제

```
업로드 → original.pdf + meta.json
                ↓
        사용자가 "웹뷰 번역" 요청해야만
                ↓
        extract_page() → translate_blocks() → web_translated.md
        ^^^^^^^^^^^^     ^^^^^^^^^^^^^^^^^^
        MD 추출           번역 (Ollama 호출)
                ↓
        merge_full_translated() → full_translated.md
```

**문제**: MD 추출이 번역 파이프라인에 결합되어 있어, 번역을 실행하지 않으면 구조화된 텍스트를 얻을 수 없다.

**결과**:
- 요약·Q&A를 하려면 반드시 번역을 먼저 해야 함
- 원문만 읽고 싶은 사용자에게 불필요한 번역을 강제
- "노트북" 경험과 괴리

### 1.3 해결 방향

```
업로드 → original.pdf + meta.json
                ↓
        ┌───────────────────┬────────────────────┐
        ▼                   ▼                    ▼
   [A] 추출 전용        [B] 웹뷰 번역        [C] PDF 번역
   extract_page()       extract + translate   pdf2zh (기존)
        ↓                   ↓
   web_extracted.md     web_translated.md
        ↓                   ↓
   full_extracted.md    full_translated.md
        ↓                   ↓
        └───────┬───────────┘
                ▼
          AI 요약 · Q&A
```

번역 없이 **추출만** 수행하는 경로 [A]를 신설한다.
요약·Q&A는 가용한 최고 품질 소스를 자동 선택한다.

---

## 2. 현재 코드 분석

### 2.1 분리 가능한 추출 함수

```python
# md_extractor.py
extract_page(pdf_path: Path, page_num: int, assets_dir: Path | None) -> dict
# 반환: {"markdown": str, "page_boxes": list, "assets": list, "metadata": dict}
```

- 번역과 **무관하게** 독립 호출 가능
- PyMuPDF4LLM → Markdown + 이미지 캡처 + 좌표 데이터
- YOLO 폴백 내장

### 2.2 번역 파이프라인 (참고)

```python
# md_translator.py — 번역 경로에서만 사용
parse_blocks(markdown) → translate_blocks(blocks, model) → assemble_translated_md(blocks, ...)
```

### 2.3 병합 함수

```python
# md_translator.py
merge_full_translated(doc_dir, total_pages, title) → full_translated.md
```

- `pages/{N}/web_translated.md` 를 순회하며 병합
- 추출 전용에서는 `pages/{N}/web_extracted.md` 를 병합하는 변형 필요

### 2.4 LLM 호출 패턴

```python
# llm_provider.py — 반드시 이 추상화 경유
provider = get_provider()
result = await provider.generate(prompt, system=system_prompt, temperature=0.3)
```

### 2.5 Q&A 세션 패턴

```python
# conversation.py — 싱글턴 스토어
store = ConversationStore.store
session = store.create_session()  # UUID hex[:16]
session.add_message("user", question)
# MAX_HISTORY_MESSAGES=50, LRU 100세션, 60분 유휴
```

---

## 3. 추출 전용 파이프라인 설계

### 3.1 목적

번역 없이 PDF → 구조화된 Markdown을 생산한다.
이 Markdown은 웹뷰 원문 읽기, 요약, Q&A의 데이터 소스가 된다.

### 3.2 파일 구조

```
data/translator/{username}/{doc_id}/
├── original.pdf
├── meta.json
├── pages/
│   └── {N}/
│       ├── web_extracted.md        ← [신규] 원문 MD
│       ├── web_translated.md       ← [기존] 번역 MD
│       ├── web_page_boxes.json     ← 공유 (추출 시점에 생성)
│       └── assets/                 ← 공유 (추출 시점에 생성)
├── full_extracted.md               ← [신규] 원문 전체 병합
├── full_translated.md              ← [기존] 번역 전체 병합
└── ai_summary.json                 ← [신규] 요약 결과
```

### 3.3 추출 전용 함수

```python
# translator_service.py 신규

async def start_web_extraction(username: str, doc_id: str, page_num: int):
    """번역 없이 MD 추출만 수행. 웹뷰 원문·요약·Q&A의 전제 조건."""
    # 1. meta.json 상태 업데이트
    #    page_status[N].web_extract = {"status": "extracting", "started_at": ...}
    # 2. asyncio.create_task(_run_web_extraction(...))
    # 3. 태스크 키: f"we:{doc_id}:{page_num}"

def _sync_extraction(pdf_path, page_num, page_dir, assets_dir, title, total_pages):
    """동기 추출 파이프라인 (executor에서 실행)"""
    # Step 1: extract_page() — 기존 함수 그대로 사용
    # Step 2: assemble_extracted_md() — frontmatter 부착 (번역 없음)
    # Step 3: web_extracted.md 저장
    # Step 4: web_page_boxes.json 저장 (번역에서도 재사용)
    # Step 5: merge_full_extracted() — 전체 병합
```

### 3.4 assemble_extracted_md (신규)

```python
def assemble_extracted_md(markdown: str, page_num: int, total_pages: int, title: str, assets_dir) -> str:
    """추출된 원문 MD에 frontmatter 부착. translate 없이 원본 그대로."""
    # frontmatter:
    #   title, page, total_pages, extracted_at
    #   summary: ""  ← AI 요약이 나중에 채움
    #   keywords: [] ← AI 키워드가 나중에 채움
    # 본문: markdown 원본 (이미지 경로만 상대경로 변환)
```

### 3.5 merge_full_extracted (신규)

기존 `merge_full_translated()` 와 동일 로직이지만, `web_extracted.md` 를 순회한다.
코드 중복을 피하기 위해 기존 함수를 일반화하는 방안 검토:

```python
def merge_full_document(doc_dir, total_pages, title, source="translated"):
    """source: "translated" | "extracted" — 파일명 접미사 결정"""
    filename = f"web_{source}.md"
    output = f"full_{source}.md"
    # 나머지 로직 동일
```

### 3.6 meta.json 상태 확장

```json
{
  "page_status": {
    "1": {
      "web_extract": {
        "status": "done",
        "extracted_at": "2026-03-27T10:00:00",
        "elapsed_sec": 2.1
      },
      "web_translate": {
        "status": "done",
        "model": "gemma3:4b",
        "translated_at": "...",
        "elapsed_sec": 45.3
      }
    }
  },
  "ai_summary": {
    "status": "done|generating|error|none",
    "model": "gemma3:4b",
    "created_at": "...",
    "source": "translated|extracted"
  }
}
```

### 3.7 번역 파이프라인과의 관계

**핵심 원칙**: 번역은 추출을 포함한다.

```
번역 요청 시:
  1. web_extracted.md 가 없으면 → 추출 먼저 실행 후 저장
  2. web_extracted.md 가 있으면 → 추출 스킵, 번역만 실행
  3. 번역 완료 후 web_translated.md 저장 (기존 흐름 유지)
```

이렇게 하면:
- 추출 결과를 번역이 **재사용** — 중복 추출 방지
- 추출 → 번역 순서가 보장
- `assets/` 와 `web_page_boxes.json` 은 추출 시점에 한 번만 생성

### 3.8 API 엔드포인트

```
POST /api/translator/document/{doc_id}/extract
  Body: { "pages": "all" | [1, 2, 3] }
  Response: { "status": "started", "total_pages": N }

GET /api/translator/document/{doc_id}/extract/status
  Response: { "total": N, "done": M, "pages": {"1": {"status": "done"}, ...} }

GET /api/translator/document/{doc_id}/extracted-md?page={N}
  Response: raw markdown text

GET /api/translator/document/{doc_id}/full-extracted-md
  Response: { "markdown": "...", "total_pages": N, "extracted_pages": [1,2,...] }
```

### 3.9 트리거 시점

| 시나리오 | 추출 트리거 | 비고 |
|----------|-----------|------|
| 사용자가 "AI 요약" 요청 | **자동** — 추출 안 된 페이지 먼저 추출 후 요약 | 사용자에게 투명 |
| 사용자가 "Q&A" 질문 | **자동** — full_extracted.md 없으면 전체 추출 후 응답 | 첫 질문만 대기 |
| 사용자가 "웹뷰 번역" 요청 | 기존 흐름 유지 (내부적으로 추출 재사용) | 변경 최소화 |
| 사용자가 "웹뷰 원문" 열기 | **자동** — 해당 페이지 추출 | 향후 Phase에서 검토 |

> **Phase 4 범위**: 요약·Q&A 트리거만 구현. "웹뷰 원문" UI는 향후 과제.

---

## 4. AI 요약 설계

### 4.1 업계 조사 기반 전략 선택

업계 유사 시스템 조사 결과, 단일 문서 AI 처리는 **문서 크기에 따라 전략을 나누는 것**이 표준이다.

| 시스템 | 단일 문서 Q&A 방식 | 요약 방식 |
|--------|-------------------|----------|
| **Google NotebookLM** | 사전 청킹+임베딩 (다중 소스 대상) | Gemini 롱 컨텍스트 단일 패스 |
| **Notion AI** | 단일 페이지 → 직접 주입 (벡터 검색 안 함) | 단일 패스 |
| **ChatPDF** | 청킹+임베딩 (GPT-3.5 시절 설계) | Map-reduce |
| **Obsidian Copilot** | 단일 노트 → 전문 직접 전달 | 단일 패스 |
| **LlamaIndex 권장** | 컨텍스트 내 → SummaryIndex, 초과 → VectorIndex | tree_summarize |

**핵심 발견**: 단일 문서가 컨텍스트 윈도우에 들어가면 벡터 검색을 **건너뛰고 직접 주입**하는 것이 업계 표준.

### 4.2 크기 적응형 전략 (Size-Adaptive)

Ollama 로컬 모델(gemma3:4b) 컨텍스트 윈도우: **~8K 토큰 (~6000자 한국어)**.

```
문서 크기 측정: full_extracted.md의 문자 수 (항상 원문 기준 — 전체 커버 보장)

               ┌─────────────────────────────────────┐
               │        문서 크기 < 6000자?            │
               └──────┬──────────────┬────────────────┘
                    Yes               No
                     ▼                 ▼
            ┌─── 단일 패스 ───┐  ┌─── 계층적 요약 ───┐
            │ 전문 → LLM 1회  │  │ 섹션 분할          │
            │ 요약 + 키워드   │  │ → 섹션별 LLM 호출  │
            │ 동시 생성       │  │ → 통합 LLM 호출    │
            │                 │  │ → 키워드 LLM 호출  │
            │ LLM 호출: 1회   │  │ LLM 호출: N+2회    │
            │ 품질: 최고      │  │ 품질: 높음         │
            │ (cross-section  │  │ (구조 보존,        │
            │  추론 가능)     │  │  초반 편향 없음)   │
            └─────────────────┘  └────────────────────┘
```

**우리 문서 분포 예상:**
- 10페이지 논문 → ~5,000~8,000자 → 단일 패스 가능 (~60%)
- 20페이지 논문 → ~12,000~16,000자 → 계층적 요약 필요 (~30%)
- 30페이지+ 논문 → ~20,000자+ → 확실히 계층적 (~10%)

### 4.3 요약 파이프라인

```
Step 1: 소스 확보
        full_extracted.md 존재 → 원문 사용 (항상 전체 문서 커버, LLM 영어 이해도 높음)
        없음                  → 자동 추출 실행 → full_extracted.md 생성
        ※ 번역문(full_translated.md)은 요약에 사용하지 않음 (부분 번역 문제 방지)

Step 2: 크기 판정
        문서 전문 문자 수 측정
        ≤ SUMMARY_DIRECT_THRESHOLD (6000자) → Step 3A (단일 패스)
        > SUMMARY_DIRECT_THRESHOLD           → Step 3B (계층적)

Step 3A: 단일 패스 요약 (짧은 문서)
         전문 → LLM 1회 호출 → 요약 + 키워드 동시 생성
         → Step 6

Step 3B: 섹션 분할 (긴 문서)
         Markdown 헤딩(##, ###) 기준으로 섹션 분리
         헤딩이 없는 문서 → 페이지 단위 폴백

Step 4: 섹션별 요약 (병렬 가능)
        각 섹션 → LLM 1회 호출 → 1~3문장 요약
        컨텍스트 내 확실히 수용 (섹션 ≪ 6000자)

Step 5: 최종 통합 요약 + 키워드
        섹션 요약들을 합쳐서 LLM 1회 호출 → 3~5문장 통합 요약
        전체 텍스트 앞 6000자 → LLM 1회 호출 → 키워드 5~10개

Step 6: 저장
        ai_summary.json 파일로 저장 (meta.json 상태 업데이트)
        strategy: "direct" | "hierarchical" 기록
```

### 4.4 섹션 분할 알고리즘 (계층적 요약 시에만 사용)

```python
def split_sections(markdown: str) -> list[dict]:
    """Markdown 헤딩 기준 섹션 분할."""
    sections = []
    current = {"heading": "(서두)", "level": 0, "content": ""}

    for line in markdown.split("\n"):
        match = re.match(r'^(#{1,4})\s+(.+)', line)
        if match:
            if current["content"].strip():
                sections.append(current)
            current = {
                "heading": match.group(2),
                "level": len(match.group(1)),
                "content": ""
            }
        else:
            current["content"] += line + "\n"

    if current["content"].strip():
        sections.append(current)

    # 폴백: 섹션 0~1개면 페이지 단위 분할
    if len(sections) <= 1:
        return split_by_page_comments(markdown)

    return sections
```

### 4.5 컨텍스트 제한 처리

| 전략 | 단계 | 입력 크기 | 초과 대응 |
|------|------|----------|----------|
| 단일 패스 | 전문 요약 | ≤ 6000자 (보장) | 해당 없음 |
| 계층적 | 섹션별 요약 | 섹션 1개 (~500~3000자) | 거의 초과 안 함. 초과 시 앞 6000자만 |
| 계층적 | 최종 통합 | 섹션 요약 합계 (~500~2000자) | 초과 안 함 |
| 공통 | 키워드 추출 | 전체 텍스트 → 앞 6000자 | 문서 대표성 충분 |

### 4.6 프롬프트 설계

#### 단일 패스 요약+키워드 프롬프트 (짧은 문서)

```
System: 당신은 학술 문서 분석 전문가입니다. 아래 문서를 분석하여 두 가지를 생성하세요.

        [요약] 문서 전체의 핵심을 3~5문장으로 요약하세요.
        - 문서의 목적, 방법, 주요 결과, 결론을 포함
        - 구체적 수치·방법명·결론을 포함
        - 추상적 표현("다양한 방법을 사용") 대신 구체적 내용 서술

        [키워드] 핵심 키워드 5~10개를 추출하세요.
        - 전문 용어, 고유명사, 핵심 개념 위주
        - 한국어 키워드 우선, 영어 원어가 중요하면 병기

        반드시 아래 JSON 형식으로 출력:
        {"summary": "요약 텍스트", "keywords": ["키워드1", "키워드2", ...]}

        한국어로 답변하세요.

User: {full_document_text}
```

#### 섹션 요약 프롬프트 (긴 문서 — 계층적)

```
System: 당신은 학술 문서 분석 전문가입니다. 주어진 섹션의 핵심 내용을 1~3문장으로 요약하세요.
        - 구체적 수치·방법명·결론을 포함
        - 추상적 표현("다양한 방법을 사용") 대신 구체적 내용 서술
        - 한국어로 답변

User: ## 섹션 제목: {heading}

{section_content}
```

#### 최종 통합 프롬프트 (긴 문서 — 계층적)

```
System: 당신은 학술 문서 분석 전문가입니다. 아래 섹션별 요약을 바탕으로
        문서 전체의 핵심을 3~5문장으로 통합 요약하세요.
        - 문서의 목적, 방법, 주요 결과, 결론을 포함
        - 각 섹션 간 논리적 흐름을 보존
        - 한국어로 답변

User: {section_summaries}
```

#### 키워드 추출 프롬프트 (긴 문서 — 별도 호출)

```
System: 아래 문서에서 핵심 키워드 5~10개를 추출하세요.
        - 전문 용어, 고유명사, 핵심 개념 위주
        - JSON 배열로 출력: ["키워드1", "키워드2", ...]
        - 한국어 키워드 우선, 영어 원어가 중요하면 병기

User: {document_text_truncated}
```

### 4.7 저장 구조: ai_summary.json

```json
{
  "version": 1,
  "strategy": "direct",
  "source": "translated",
  "model": "gemma3:4b",
  "created_at": "2026-03-27T14:30:00",
  "elapsed_sec": 8.2,
  "overall_summary": "본 논문은 ... 를 제안하며, ... 실험 결과 ... 를 달성하였다.",
  "keywords": ["딥러닝", "객체 감지", "YOLO", "실시간 추론"],
  "sections": []
}
```

```json
{
  "version": 1,
  "strategy": "hierarchical",
  "source": "translated",
  "model": "gemma3:4b",
  "created_at": "2026-03-27T14:30:00",
  "elapsed_sec": 23.5,
  "overall_summary": "본 논문은 ... 를 제안하며, ... 실험 결과 ... 를 달성하였다.",
  "keywords": ["딥러닝", "객체 감지", "YOLO", "실시간 추론"],
  "sections": [
    {
      "heading": "Introduction",
      "level": 2,
      "summary": "기존 객체 감지 모델의 속도-정확도 트레이드오프 문제를 제기하며..."
    },
    {
      "heading": "Related Work",
      "level": 2,
      "summary": "R-CNN 계열과 SSD/YOLO 계열의 발전 과정을 정리하며..."
    }
  ]
}
```

**별도 파일로 분리하는 이유:**
- meta.json 비대화 방지 (요약 텍스트가 수KB)
- 요약 재생성 시 파일 덮어쓰기로 간단 처리
- meta.json에는 상태 참조만 저장

**strategy 필드:**
- `"direct"` — 단일 패스 (짧은 문서). `sections`는 빈 배열.
- `"hierarchical"` — 계층적 요약 (긴 문서). `sections`에 섹션별 요약 포함.
- 프론트엔드는 `sections` 배열이 비어있으면 아코디언 UI를 숨기면 됨.

### 4.8 API 엔드포인트

```
POST /api/translator/document/{doc_id}/summary
  Body: { "force": false }   ← true면 기존 요약 무시하고 재생성
  Response: { "status": "started" } | { "status": "exists", "summary": {...} }

GET /api/translator/document/{doc_id}/summary
  Response: ai_summary.json 내용 그대로
  404: 요약 미생성
```

### 4.9 자동 요약 옵션

`config.TRANSLATOR_WEB_AUTO_SUMMARY = True` 시:
- 웹뷰 번역 **전체 완료** 후 (마지막 페이지 번역 완료 시점)
- `merge_full_translated()` 직후 자동으로 요약 태스크 시작
- 사용자 개입 없이 백그라운드 실행

---

## 5. Q&A (문서 챗봇) 설계

### 5.1 범위와 아키텍처 원칙

**Phase 4 범위**: 현재 열린 문서 1개에 대한 Q&A.
전체 개인 문서 검색은 향후 과제 (벡터 인덱스 격리 구조 필요).

**아키텍처 원칙: Explorer 챗봇 인프라 재사용**

업계 조사 결과, Notion AI가 단일 페이지 Q&A에서 RAG 없이 직접 주입하듯이,
단일 문서 Q&A는 **컨텍스트 공급 방식만** 다르고 나머지는 동일하다.

```
[Explorer 챗봇]                    [Notebook Q&A]
─────────────────────              ──────────────────────
질문 수신                           질문 수신
  ↓                                  ↓
_routed_search() ← RAG 파이프라인   get_qa_context() ← 문서 파일 읽기
  ↓                                  ↓
context_dicts 구성                  context_dicts 구성
  ↓                                  ↓
generate_response_stream() ← 공유   generate_response_stream() ← 공유
  ↓                                  ↓
NDJSON 스트리밍    ← 공유           NDJSON 스트리밍    ← 공유
  ↓                                  ↓
ConversationStore  ← 공유           ConversationStore  ← 공유
```

**공유하는 것**: `llm_provider.py`, `llm_client.py`, `conversation.py`, NDJSON 포맷, 스트리밍 파서 패턴
**분리하는 것**: 엔드포인트 URL, 시스템 프롬프트, 컨텍스트 공급 로직

### 5.2 컨텍스트 소스 폴백 체인

```
1순위: full_translated.md   (번역문, 한국어, 이해도 최고)
2순위: full_extracted.md    (원문 MD, 구조 보존)
3순위: PDF 텍스트 직접 추출  (fitz.open → get_text("text"), 구조 없음)
```

선택 로직:

```python
def get_qa_context(username: str, doc_id: str) -> tuple[str, str]:
    """Q&A 컨텍스트 소스 결정. Returns (text, source_type)."""
    doc_dir = _get_doc_dir(username, doc_id)

    translated = doc_dir / "full_translated.md"
    if translated.exists():
        return translated.read_text("utf-8"), "translated"

    extracted = doc_dir / "full_extracted.md"
    if extracted.exists():
        return extracted.read_text("utf-8"), "extracted"

    # 최후 폴백: PDF 직접 텍스트 추출 (비구조)
    return _extract_all_pdf_text(doc_dir / "original.pdf"), "raw_pdf"
```

### 5.3 크기 적응형 컨텍스트 관리

요약과 동일한 원칙 — 문서 크기에 따라 전략을 나눈다.

```
문서 전문 ≤ QA_DIRECT_THRESHOLD (6000자)
  → 직접 주입: 전문을 그대로 LLM 컨텍스트에 넣음 (Notion AI 방식)
  → 답변 품질 최고 (cross-section 추론 가능)
  → 벡터 검색·섹션 선별 불필요

문서 전문 > QA_DIRECT_THRESHOLD
  → 섹션 선별: 질문 관련 섹션만 골라서 6000자 이내로 구성
  → 키워드 매칭 (단일 문서 내에서는 충분, 업계 조사 확인)
```

```python
def build_qa_context(question: str, full_text: str, max_chars: int = 6000) -> str:
    """크기 적응형 컨텍스트 구성."""
    # 짧은 문서: 직접 주입 (업계 표준 — Notion AI, Obsidian Copilot 방식)
    if len(full_text) <= max_chars:
        return full_text

    # 긴 문서: 질문-관련 섹션 선별
    return _select_relevant_sections(question, full_text, max_chars)


def _select_relevant_sections(question: str, full_text: str, max_chars: int) -> str:
    """키워드 매칭 기반 관련 섹션 선별."""
    sections = split_sections(full_text)

    # 키워드 매칭 (단일 문서 내에서는 벡터 검색과 품질 차이 미미)
    question_tokens = set(question.lower().split())
    scored = []
    for sec in sections:
        content_lower = sec["content"].lower()
        overlap = sum(1 for t in question_tokens if t in content_lower)
        scored.append((overlap, sec))

    # 점수순 정렬, 상위 섹션들을 max_chars까지 수집
    scored.sort(key=lambda x: -x[0])
    result = ""
    for score, sec in scored:
        chunk = f"## {sec['heading']}\n{sec['content']}\n\n"
        if len(result) + len(chunk) > max_chars:
            break
        result += chunk

    # 폴백: 관련 섹션 없으면 앞 max_chars
    return result if result else full_text[:max_chars]
```

**향후 고도화 경로** (필요 시):
키워드 매칭 → 임베딩 유사도(bge-m3) → 문서별 FAISS 인덱스.
`_select_relevant_sections()` 함수만 교체하면 되므로 나머지 코드에 영향 없음.

### 5.4 세션 관리

기존 `ConversationStore` 싱글턴을 그대로 재사용한다.

```python
# 문서별 Q&A 세션 ID 규칙
session_id = f"nb:{doc_id}:{session_hex}"
# "nb:" 접두어로 Explorer 채팅과 구분
```

### 5.5 시스템 프롬프트

```
당신은 학술 문서 분석 어시스턴트입니다.
아래 제공된 문서 내용을 바탕으로 사용자의 질문에 답변하세요.

규칙:
- 문서에 없는 내용은 "문서에서 해당 내용을 찾을 수 없습니다"라고 답변
- 구체적 수치·페이지·섹션을 인용하여 근거 제시
- 한국어로 답변
- 간결하고 명확하게 (3~5문장 권장)
```

### 5.6 API 엔드포인트

```
POST /api/translator/document/{doc_id}/chat
  Body: {
    "question": "이 논문의 실험 결과는?",
    "conversation_id": null | "nb:abc123:f1e2d3"
  }
  Response: {
    "answer": "...",
    "source_type": "translated",
    "model": "gemma3:4b",
    "conversation_id": "nb:abc123:f1e2d3"
  }

POST /api/translator/document/{doc_id}/chat/stream
  Body: (동일)
  Response: NDJSON 스트리밍 (Explorer chat.py 패턴)
    {"type": "token", "content": "..."}
    {"type": "done", "source_type": "translated", "model": "...", "conversation_id": "..."}
```

---

## 6. 프론트엔드 UI 설계

### 6.1 아이콘 레일 변경

| 변경 전 | 변경 후 | 비고 |
|---------|---------|------|
| 5번: AI 요약·Q&A (disabled) | 5번: AI 요약·Q&A **(활성)** | `data-panel="ai-summary"` |
| 6번: 문서 요약 (disabled) | **삭제** | 5번에 통합 (탭으로 분리) |
| 7번: 마인드맵 (disabled) | 6번: 마인드맵 (disabled) | 번호 당겨짐 |

아이콘 레일이 **7 → 6개**로 축소.
요약과 Q&A는 하나의 패널 내 탭으로 구성.

### 6.2 패널 레이아웃

```
┌─ AI 분석 ─────────────────────────────┐
│  [요약]  [Q&A]              ← 탭 전환  │
├───────────────────────────────────────┤
│                                       │
│  ┌─ 전체 요약 ──────────────────────┐ │
│  │ 본 논문은 ... 를 제안하며,       │ │
│  │ ... 실험 결과 ... 를 달성        │ │
│  └──────────────────────────────────┘ │
│                                       │
│  🏷️  딥러닝  객체 감지  YOLO  ...    │
│                                       │
│  ┌─ 섹션별 요약 ────────────────────┐ │
│  │ ▸ Introduction                   │ │
│  │   기존 객체 감지의 속도-정확도... │ │
│  │ ▸ Methods                        │ │
│  │   (접힌 상태)                    │ │
│  │ ▸ Experiments                    │ │
│  │   (접힌 상태)                    │ │
│  └──────────────────────────────────┘ │
│                                       │
│  [🔄 요약 재생성]                      │
└───────────────────────────────────────┘
```

```
┌─ AI 분석 ─────────────────────────────┐
│  [요약]  [Q&A]              ← 탭 전환  │
├───────────────────────────────────────┤
│                                       │
│  ┌────────────────────────────────┐   │
│  │ 🤖 안녕하세요! 이 문서에 대해  │   │
│  │    질문해 주세요.              │   │
│  └────────────────────────────────┘   │
│                                       │
│  ┌────────────────────────────────┐   │
│  │ 👤 이 논문의 실험 결과는?      │   │
│  └────────────────────────────────┘   │
│                                       │
│  ┌────────────────────────────────┐   │
│  │ 🤖 실험 결과, 제안 모델은      │   │
│  │    mAP 47.2%를 달성하여 ...    │   │
│  └────────────────────────────────┘   │
│                                       │
│  ┌─────────────────────────┬──────┐   │
│  │ 질문을 입력하세요...     │ 전송 │   │
│  └─────────────────────────┴──────┘   │
└───────────────────────────────────────┘
```

### 6.3 상태별 화면

#### 요약 탭

| 상태 | 화면 |
|------|------|
| **요약 없음 + 번역/추출 없음** | "요약을 생성하려면 문서 추출이 필요합니다" + [추출 시작] 버튼 |
| **요약 없음 + 추출/번역 있음** | "AI 요약을 생성하세요" + [요약 생성] 버튼 |
| **요약 생성 중** | 스피너 + 진행 단계 표시 ("섹션 분할 중...", "3/7 섹션 요약 중...") |
| **요약 완료** | 전체 요약 + 키워드 + 섹션별 아코디언 + [재생성] 버튼 |
| **에러** | 에러 메시지 + [재시도] 버튼 |

#### Q&A 탭

| 상태 | 화면 |
|------|------|
| **추출/번역 없음** | "Q&A를 사용하려면 문서 추출이 필요합니다" + [추출 시작] 버튼 |
| **컨텍스트 준비됨** | 웰컴 메시지 + 입력창 활성 |
| **응답 대기 중** | 스트리밍 토큰 표시 (타이핑 효과) |
| **에러** | 인라인 에러 메시지 |

### 6.4 CSS 클래스 명명

기존 패널 패턴(`ts-side-panel`, `ts-panel-header` 등)을 따른다.

```css
/* 탭 */
.ai-tab-bar { }
.ai-tab-btn { }
.ai-tab-btn.active { }

/* 요약 */
.ai-summary-card { }          /* 전체 요약 카드 */
.ai-keywords { }              /* 키워드 배지 컨테이너 */
.ai-keyword-tag { }           /* 개별 키워드 */
.ai-section-list { }          /* 섹션별 요약 아코디언 */
.ai-section-item { }
.ai-section-heading { }       /* 클릭으로 접기/펼치기 */
.ai-section-body { }

/* Q&A */
.ai-chat-messages { }         /* 메시지 목록 스크롤 영역 */
.ai-chat-bubble { }           /* 메시지 버블 */
.ai-chat-bubble.user { }
.ai-chat-bubble.assistant { }
.ai-chat-input-area { }       /* 입력 영역 */
.ai-chat-input { }            /* 텍스트 입력 */
.ai-chat-send { }             /* 전송 버튼 */
```

---

## 7. 구현 순서

의존성을 기반으로 4단계로 분할한다.

### Step 1: 추출 전용 파이프라인 (백엔드) — ✅ 완료

> 요약·Q&A의 **전제 조건**. 이것 없이는 번역 안 한 문서에서 아무것도 할 수 없다.

- ✅ `md_translator.py` — `merge_full_document()` 일반화 (translated/extracted 공용)
- ✅ `md_translator.py` — `assemble_extracted_md()` 원문 MD frontmatter 부착
- ✅ `translator_service.py`:
  - `start_web_extraction()`, `_run_web_extraction()` 비동기 추출 파이프라인
  - `start_full_extraction()` 전체 페이지 일괄 추출
  - `get_web_extraction_status()`, `get_full_extraction_status()` 상태 조회
  - `get_web_extracted_md()`, `get_web_full_extracted_md()` 데이터 조회
- ✅ `translator.py` (API) — 추출 엔드포인트 4개 (extract, extract/status, extracted-view/page, extracted-view/full)
- ✅ 기존 `_run_web_translation()` 수정 — 추출 결과 재사용 (extract_page 스킵)
- ✅ `config.py` — `TRANSLATOR_AI_SUMMARY_MODEL`, `THRESHOLD` 키 추가
- ✅ 검증: 4페이지 문서 전체 추출 (~3초), 중복 추출 방지, 번역 시 재사용 확인

### Step 2: AI 요약 (백엔드 + 프론트) — ✅ 완료

> 추출 파이프라인 위에 구축.

- ✅ `services/ai_summary.py` (신규):
  - `split_sections()` — 헤딩 기반 섹션 분할 + 페이지 주석 폴백
  - `generate_summary()` — **크기 적응형** 요약 오케스트레이터
    - 짧은 문서 (≤6000자): 단일 패스 (LLM 1회, JSON 응답)
    - 긴 문서 (>6000자): 계층적 (섹션별 → 통합 → 키워드)
  - JSON 파싱 + 정규식 폴백 파서
- ✅ `translator_service.py` — `start_summary_generation()`, 비동기 태스크, ai_summary.json 저장
- ✅ `translator_service.py` — 소스 파일 없을 시 **자동 추출 → 요약** 연속 실행 (설계서 3.9)
- ✅ `translator.py` (API) — POST/GET document/{id}/summary
- ✅ 프론트엔드:
  - 아이콘 레일 5번 활성화, 6번(문서요약) 삭제 → 7→6개
  - 패널 헤더 (요약/Q&A 탭), panelHdrMap 확장, _showToolContent 분기
  - 상태별 화면 (empty → loading → result → error)
  - 요약 카드 + 키워드 배지 + 섹션별 아코디언 + 재생성 버튼
  - 3초 폴링, 캐시, 문서 전환 시 리셋 (nb-doc-switch 이벤트)
- ✅ CSS: ai-tab-bar, ai-summary-card, ai-keywords, ai-section-list + 다크모드
- ✅ 검증: 실제 요약 생성 성공 (계층적, ~10초), Light + Dark 확인, 기존 패널 회귀 없음

### Step 3: Q&A 챗봇 (백엔드 + 프론트) — ✅ 완료

> Explorer 챗봇 인프라(llm_provider, conversation, NDJSON) 재사용. 컨텍스트 공급부만 신규.

- ✅ `services/notebook_chat.py` (신규):
  - `get_qa_context()` — 소스 폴백 체인 (translated → extracted → raw PDF)
  - `build_qa_context()` — **크기 적응형** 컨텍스트 구성 (직접 주입 / 키워드 매칭 섹션 선별)
  - `ask_document_stream()` — 스트리밍 응답, `ConversationStore` 싱글턴 재사용
  - 시스템 프롬프트: 문서 분석 어시스턴트 (한국어, 마크다운, 근거 인용)
- ✅ `translator.py` (API) — `POST /document/{doc_id}/chat/stream`
  - `NotebookChatRequest` Pydantic 모델 (`question`, `conversation_id`)
  - Explorer `chat.py`와 동일 NDJSON 포맷 (token/done/error)
  - `StreamingResponse` + `event_generator()` 패턴
- ✅ 프론트엔드 — Q&A 탭 UI
  - 채팅 버블 (user 우측 파란색 / assistant 좌측 회색)
  - NDJSON 스트리밍 파서 + rAF 버퍼링 + 자동스크롤 (Explorer 패턴 재활용)
  - 타이핑 인디케이터 (dot bounce 애니메이션)
  - 스트리밍 커서 (깜빡이는 블루 커서)
  - `marked.js` 마크다운 렌더링 (스트리밍 완료 시)
  - 멀티턴 대화 (`conversation_id` 유지)
  - 문서 전환 시 대화 리셋 (`nb-doc-switch` 이벤트)
- ✅ CSS: qa-messages, qa-bubble, qa-input-area, qa-typing, qa-streaming + 다크모드 (토큰 변수만)
- ✅ 검증: 질문 → 한국어 스트리밍 응답, 멀티턴, 마크다운 렌더링, 요약↔Q&A 탭 전환, 기존 패널 회귀 없음

### Step 4: 통합·검증 — ⬜ 미착수

- ⬜ 자동 요약 옵션 연결 (`TRANSLATOR_WEB_AUTO_SUMMARY`)
- ⬜ 문서 전환 시 패널 상태 초기화
- ⬜ Light + Dark 모드 전수 검증
- ⬜ 에러 케이스 테스트 (Ollama 미실행, 빈 문서, 1페이지 문서)

---

## 8. 리스크 및 대응

| 리스크 | 심각도 | 대응 |
|--------|:------:|------|
| 전체 추출 시간 (100페이지 문서) | 중 | 페이지별 비동기 + 프로그레스. 추출은 번역보다 10배 빠름 (~2초/페이지) |
| 소형 모델 교차 언어 지시 무시 | 중 | `/api/chat` messages 배열로 전환 완료. 그래도 안 되면 모델 크기 업 필요 |
| 긴 문서 Q&A 컨텍스트 초과 | 중 | 크기 적응형: 직접 주입(짧음) / 섹션 선별(긴 문서). 향후 임베딩 검색 교체 가능 |
| 추출 전용 경로 추가로 코드 복잡도 증가 | 하 | 기존 함수 재사용, 상태 키만 분리 |
| 헤딩 없는 문서 (스캔 PDF 등) | 하 | 페이지 단위 폴백 |
| 번역/추출 동시 요청 충돌 | 하 | 추출 완료 → 번역 진행 순서 보장, 태스크 키 분리 |
| 단일 패스 JSON 파싱 실패 | 하 | LLM이 JSON을 깨뜨릴 수 있음. 정규식 폴백 파서로 추출 |

---

## 9. 설계 결정 사항

| # | 항목 | 결정 | 근거 |
|:-:|------|------|------|
| 1 | 요약/Q&A 전략 | **크기 적응형** | 업계 표준. 짧은 문서→직접 주입(Notion 방식), 긴 문서→계층적/섹션선별 |
| 2 | Q&A 컨텍스트 검색 | **키워드 매칭** (Phase 4) | 단일 문서 내에서는 벡터 검색과 품질 차이 미미. `_select_relevant_sections()` 교체만으로 향후 벡터 전환 가능 |
| 3 | Q&A 인프라 | **Explorer 챗봇 공유** | `llm_provider`, `conversation.py`, `generate_response_stream()`, NDJSON 포맷 재사용. 컨텍스트 공급부만 분리 |
| 4 | Q&A 스트리밍 | **NDJSON 스트리밍** | Explorer 패턴 그대로. 체감 응답성 향상 |
| 5 | 요약 모델 | **별도 설정** | `TRANSLATOR_AI_SUMMARY_MODEL` 신설. 요약에는 더 큰 모델이 유리할 수 있음 |
| 6 | 추출 시 assets | **재사용** | 추출→번역 시 assets 재생성 스킵. 추출 시점에 한 번만 생성 |
| 7 | 레일 6번(문서 요약) | **삭제** | 5번 탭으로 통합, 레일 7→6개 축소 |
| 8 | 추출 전용 웹뷰 UI | **별도 Phase** | Phase 4는 요약·Q&A에 집중, 웹뷰 원문 읽기는 향후 |
| 9 | 크기 임계값 | **12,000자** (config 수동 설정) | `TRANSLATOR_AI_SUMMARY_THRESHOLD` / `QA_THRESHOLD`. 0이면 기본 12,000자. 모델에 맞게 관리자가 조정 |
| 10 | LLM API 형식 | **chat API (messages 배열)** | `/api/generate` → `/api/chat` 전환. OpenAI/Anthropic/vLLM 등 범용 호환 |
| 11 | 요약 소스 | **항상 원문 (extracted)** | 번역문 사용 시 부분 번역 문제. 원문은 전체 커버 + LLM 영어 이해도 높음 |

---

## 10. 향후 개선 여지 (실사용 피드백 후)

구현 완료 후 실사용에서 필요성이 확인되면 진행할 항목들.

| 항목 | 분류 | 비고 |
|------|------|------|
| 계층적 요약 섹션별 LLM 병렬 호출 | 코드 | GPU 부하 고려 필요, 현재 순차도 동작함 |
| JSON 폴백 파서 보강 | 코드 | 단일 패스 응답의 엣지 케이스 대응 |
| 요약 생성 중 예상 소요 시간 표시 | UX | "3/7 섹션" 외에 남은 시간 추정 |
| 단일 패스 결과 UI 보강 | UX | 섹션 아코디언 없이 전체 요약만 보여서 다소 단조로움 |

---

## 10. 참고: 기존 코드 재사용 맵

| 신규 기능 | 재사용 대상 | 파일 | 비고 |
|----------|-----------|------|------|
| 추출 파이프라인 | `extract_page()` | md_extractor.py | 그대로 사용 |
| 원문 MD 병합 | `merge_full_translated()` 일반화 | md_translator.py | 파라미터 추가 |
| LLM 호출 | `get_provider().generate()` | llm_provider.py | 추상화 경유 |
| Q&A 세션 | `ConversationStore` | conversation.py | 싱글턴 재사용 |
| 스트리밍 응답 | `chat/stream` NDJSON 패턴 | chat.py | 포맷 동일 |
| 상태 관리 | `meta.json` 패턴 | translator_service.py | 키 추가 |
| 비동기 태스크 | `asyncio.create_task` + executor | translator_service.py | 동일 패턴 |
