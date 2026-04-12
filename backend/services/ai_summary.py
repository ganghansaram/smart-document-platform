"""
AI 요약 서비스 — 크기 적응형 (단일 패스 / 계층적)

업계 표준 패턴:
- 짧은 문서 (≤ threshold): 전문 직접 주입 → LLM 1회 (Notion AI 방식)
- 긴 문서 (> threshold): 섹션별 요약 → 통합 요약 → 키워드 (Map-Reduce 방식)
"""
import json
import logging
import re
import time
from typing import Optional

import config
from services.llm_provider import get_provider

logger = logging.getLogger(__name__)

# ── 프롬프트 ──

_DIRECT_PROMPT_SYSTEM = (
    "당신은 학술 문서 분석 전문가입니다. 아래 문서를 분석하여 두 가지를 생성하세요.\n\n"
    "[요약] 문서 전체의 핵심을 3~5문장으로 요약하세요.\n"
    "- 문서의 목적, 방법, 주요 결과, 결론을 포함\n"
    "- 구체적 수치·방법명·결론을 포함\n"
    "- 추상적 표현 대신 구체적 내용 서술\n\n"
    "[키워드] 핵심 키워드 5~10개를 추출하세요.\n"
    "- 전문 용어, 고유명사, 핵심 개념 위주\n"
    "- 한국어 키워드 우선, 영어 원어가 중요하면 병기\n\n"
    '반드시 아래 JSON 형식으로만 출력하세요:\n'
    '{"summary": "요약 텍스트", "keywords": ["키워드1", "키워드2"]}\n\n'
    "한국어로 답변하세요."
)

_SECTION_PROMPT_SYSTEM = (
    "당신은 학술 문서 분석 전문가입니다. 주어진 섹션의 핵심 내용을 1~3문장으로 요약하세요.\n"
    "- 구체적 수치·방법명·결론을 포함\n"
    "- 추상적 표현 대신 구체적 내용 서술\n"
    "- 한국어로 답변"
)

_MERGE_PROMPT_SYSTEM = (
    "당신은 학술 문서 분석 전문가입니다. 아래 섹션별 요약을 바탕으로 "
    "문서 전체의 핵심을 3~5문장으로 통합 요약하세요.\n"
    "- 문서의 목적, 방법, 주요 결과, 결론을 포함\n"
    "- 각 섹션 간 논리적 흐름을 보존\n"
    "- 한국어로 답변"
)

_KEYWORD_PROMPT_SYSTEM = (
    "아래 문서에서 핵심 키워드 5~10개를 추출하세요.\n"
    "- 전문 용어, 고유명사, 핵심 개념 위주\n"
    '- JSON 배열로만 출력: ["키워드1", "키워드2", ...]\n'
    "- 한국어 키워드 우선, 영어 원어가 중요하면 병기"
)

_MINDMAP_PROMPT_SYSTEM = (
    "당신은 문서 구조 분석 전문가입니다. 아래 문서를 분석하여 마인드맵 트리를 JSON으로 생성하세요.\n\n"
    "규칙:\n"
    "1. 루트: 문서 핵심 주제 (10자 이내, 매우 짧게)\n"
    "2. 1단계: 핵심 주제 3~5개 (각 8자 이내)\n"
    "3. 2단계: 각 주제의 포인트 2~3개 (각 15자 이내)\n"
    "4. 절대로 섹션 제목(I. II. A. B.)을 나열하지 말 것\n"
    "5. 명사구 또는 짧은 구문으로 작성 (문장 금지)\n"
    "6. 구체적 용어, 방법명, 수치를 포함\n\n"
    "JSON 형식:\n"
    '{"content": "주제", "children": [\n'
    '  {"content": "카테고리", "children": [\n'
    '    {"content": "포인트1"},\n'
    '    {"content": "포인트2"}\n'
    "  ]}\n"
    "]}\n\n"
    "반드시 위 JSON만 출력. 한국어로 답변."
)


# ── 섹션 분할 ──

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
                "heading": match.group(2).strip(),
                "level": len(match.group(1)),
                "content": "",
            }
        else:
            current["content"] += line + "\n"

    if current["content"].strip():
        sections.append(current)

    # 폴백: 섹션 0~1개면 페이지 주석 기준 분할
    if len(sections) <= 1:
        return _split_by_page_comments(markdown)

    return sections


def _split_by_page_comments(markdown: str) -> list[dict]:
    """<!-- Page N ... --> 주석 기준으로 분할 (헤딩이 없는 문서 폴백)."""
    parts = re.split(r'<!--\s*Page\s+(\d+).*?-->', markdown)
    sections = []
    # parts: [preamble, page_num, content, page_num, content, ...]
    for i in range(1, len(parts), 2):
        page_num = parts[i]
        content = parts[i + 1] if i + 1 < len(parts) else ""
        if content.strip():
            sections.append({
                "heading": f"Page {page_num}",
                "level": 2,
                "content": content.strip(),
            })
    # 폴백의 폴백: 주석도 없으면 전체를 하나의 섹션으로
    if not sections and markdown.strip():
        sections.append({"heading": "(전체)", "level": 0, "content": markdown})
    return sections


# ── JSON 파싱 (LLM 출력) ──

def _parse_direct_response(text: str) -> dict:
    """LLM의 JSON 응답 파싱. 실패 시 정규식 폴백."""
    # 1차: JSON 직접 파싱
    try:
        # ```json ... ``` 감싸기 대응
        cleaned = re.sub(r'^```json\s*', '', text.strip())
        cleaned = re.sub(r'\s*```$', '', cleaned)
        data = json.loads(cleaned)
        if "summary" in data:
            return {
                "summary": data["summary"],
                "keywords": data.get("keywords", []),
            }
    except (json.JSONDecodeError, KeyError):
        pass

    # 2차: JSON 블록 추출 시도
    json_match = re.search(r'\{[^{}]*"summary"[^{}]*\}', text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            return {
                "summary": data["summary"],
                "keywords": data.get("keywords", []),
            }
        except (json.JSONDecodeError, KeyError):
            pass

    # 3차: 정규식 폴백
    summary = text.strip()
    keywords = []
    kw_match = re.search(r'\[([^\]]+)\]', text)
    if kw_match:
        keywords = [k.strip().strip('"\'') for k in kw_match.group(1).split(",")]
        # 키워드 부분 제거하여 요약만 추출
        summary = text[:kw_match.start()].strip()

    return {"summary": summary, "keywords": keywords}


def _parse_keywords_response(text: str) -> list[str]:
    """키워드 JSON 배열 파싱. 실패 시 정규식 폴백."""
    try:
        cleaned = re.sub(r'^```json\s*', '', text.strip())
        cleaned = re.sub(r'\s*```$', '', cleaned)
        arr = json.loads(cleaned)
        if isinstance(arr, list):
            return [str(k) for k in arr]
    except (json.JSONDecodeError, TypeError):
        pass

    # 폴백: 배열 추출
    arr_match = re.search(r'\[([^\]]+)\]', text)
    if arr_match:
        return [k.strip().strip('"\'') for k in arr_match.group(1).split(",")]

    return []


def _parse_mindmap_response(text: str) -> dict | None:
    """마인드맵 JSON 트리 파싱. 실패 시 None."""
    try:
        cleaned = re.sub(r'^```json\s*', '', text.strip())
        cleaned = re.sub(r'\s*```$', '', cleaned)
        data = json.loads(cleaned)
        if isinstance(data, dict) and "content" in data:
            return _normalize_mindmap_node(data, depth=0)
    except (json.JSONDecodeError, KeyError):
        pass

    # 폴백: JSON 객체 추출 시도
    json_match = re.search(r'\{.*"content".*\}', text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            if isinstance(data, dict) and "content" in data:
                return _normalize_mindmap_node(data, depth=0)
        except (json.JSONDecodeError, KeyError):
            pass

    return None


def _normalize_mindmap_node(node: dict, depth: int = 0, max_depth: int = 2) -> dict:
    """INode 트리에 depth 필드 부여 + children 정규화. max_depth로 깊이 제한."""
    result = {
        "content": str(node.get("content", ""))[:25],
        "children": [],
        "depth": depth,
    }
    if depth < max_depth:
        for child in node.get("children", []):
            if isinstance(child, dict) and "content" in child:
                result["children"].append(
                    _normalize_mindmap_node(child, depth + 1, max_depth)
                )
    return result


async def generate_mindmap_tree(
    text: str,
    provider=None,
    progress_callback=None,
) -> dict | None:
    """LLM으로 마인드맵 트리 생성. 실패 시 None (폴백은 호출자가 처리)."""
    if provider is None:
        provider = get_provider()
        model_override = getattr(config, "TRANSLATOR_MODEL", "")
        if model_override:
            from services.llm_provider import OllamaProvider
            provider = OllamaProvider(config.OLLAMA_URL, model_override)

    if progress_callback:
        progress_callback("마인드맵 구조 생성 중...")

    # 입력 텍스트: 요약용과 동일 (최대 6000자로 클리핑 — 구조 파악에 충분)
    input_text = text[:6000] if len(text) > 6000 else text

    try:
        resp = await provider.generate(
            input_text, system=_MINDMAP_PROMPT_SYSTEM, temperature=0.2, timeout=90
        )
        tree = _parse_mindmap_response(resp)
        if tree and tree.get("children"):
            logger.info("LLM 마인드맵 생성 성공: 루트='%s', children=%d",
                        tree["content"], len(tree["children"]))
            return tree
        logger.warning("LLM 마인드맵 파싱 실패 또는 빈 트리")
    except Exception as e:
        logger.warning("LLM 마인드맵 생성 실패: %s", e)

    return None


# ── 모델 컨텍스트 자동 감지 ──

_DEFAULT_SUMMARY_THRESHOLD = 12000  # 기본 12,000자 — 8K 토큰급 모델 기준


# ── 요약 생성 (메인 진입점) ──

async def generate_summary(
    full_text: str,
    source: str = "extracted",
    progress_callback=None,
) -> dict:
    """크기 적응형 요약 생성.

    Args:
        full_text: 전체 문서 텍스트 (full_extracted.md)
        source: "extracted" — 소스 유형 기록용
        progress_callback: 진행 상태 콜백 (단계 문자열)

    Returns:
        ai_summary.json에 저장할 딕셔너리
    """
    from services.md_translator import _strip_frontmatter

    text = _strip_frontmatter(full_text).strip()

    provider = get_provider()
    # 요약 전용 모델이 설정되어 있으면 별도 Ollama 인스턴스 생성
    model_name_override = getattr(config, "TRANSLATOR_MODEL", "")
    if model_name_override:
        from services.llm_provider import OllamaProvider
        provider = OllamaProvider(config.OLLAMA_URL, model_name_override)
    model_name = provider.model_name

    # threshold: config에 설정값이 있으면 사용, 없으면 기본값
    threshold = getattr(config, "TRANSLATOR_AI_SUMMARY_THRESHOLD", 0) or _DEFAULT_SUMMARY_THRESHOLD

    start_time = time.monotonic()

    if len(text) <= threshold:
        # ── 단일 패스 (컨텍스트에 들어가는 문서) ──
        result = await _generate_direct(text, provider, progress_callback)
        result["strategy"] = "direct"
        result["sections"] = []
    else:
        # ── 계층적 요약 (컨텍스트 초과 문서) ──
        result = await _generate_hierarchical(text, provider, progress_callback)
        result["strategy"] = "hierarchical"

    # ── 마인드맵 트리 생성 (요약 완료 후, 동일 provider 재사용) ──
    mindmap_tree = await generate_mindmap_tree(text, provider=provider,
                                                progress_callback=progress_callback)

    elapsed = time.monotonic() - start_time

    return {
        "version": 1,
        "strategy": result["strategy"],
        "source": source,
        "model": model_name,
        "created_at": None,  # 호출자가 설정
        "elapsed_sec": round(elapsed, 1),
        "overall_summary": result["summary"],
        "keywords": result["keywords"],
        "sections": result.get("sections", []),
        "mindmap_tree": mindmap_tree,
    }


async def _generate_direct(text: str, provider, progress_callback=None) -> dict:
    """단일 패스: 전문 → LLM 1회 → 요약 + 키워드 동시."""
    if progress_callback:
        progress_callback("단일 패스 요약 생성 중...")

    response = await provider.generate(
        text, system=_DIRECT_PROMPT_SYSTEM, temperature=0.3, timeout=120
    )
    parsed = _parse_direct_response(response)
    return {
        "summary": parsed["summary"],
        "keywords": parsed["keywords"],
    }


async def _generate_hierarchical(text: str, provider, progress_callback=None) -> dict:
    """계층적 요약: 섹션 분할 → 섹션별 요약 → 통합 → 키워드."""
    if progress_callback:
        progress_callback("섹션 분할 중...")

    sections = split_sections(text)
    max_section_chars = 6000

    # 1. 섹션별 요약
    section_results = []
    for i, sec in enumerate(sections):
        if progress_callback:
            progress_callback(f"섹션 요약 중... ({i + 1}/{len(sections)})")

        content = sec["content"][:max_section_chars]
        prompt = f"## 섹션 제목: {sec['heading']}\n\n{content}"

        try:
            resp = await provider.generate(
                prompt, system=_SECTION_PROMPT_SYSTEM, temperature=0.3, timeout=90
            )
            section_results.append({
                "heading": sec["heading"],
                "level": sec["level"],
                "summary": resp.strip(),
            })
        except Exception as e:
            logger.warning("섹션 요약 실패 (%s): %s", sec["heading"], e)
            section_results.append({
                "heading": sec["heading"],
                "level": sec["level"],
                "summary": "(요약 생성 실패)",
            })

    # 2. 통합 요약
    if progress_callback:
        progress_callback("통합 요약 생성 중...")

    summaries_text = "\n\n".join(
        f"## {s['heading']}\n{s['summary']}" for s in section_results
    )
    overall = await provider.generate(
        summaries_text, system=_MERGE_PROMPT_SYSTEM, temperature=0.3, timeout=90
    )

    # 3. 키워드 추출
    if progress_callback:
        progress_callback("키워드 추출 중...")

    kw_text = text[:6000]
    kw_resp = await provider.generate(
        kw_text, system=_KEYWORD_PROMPT_SYSTEM, temperature=0.1, timeout=60
    )
    keywords = _parse_keywords_response(kw_resp)

    return {
        "summary": overall.strip(),
        "keywords": keywords,
        "sections": section_results,
    }
