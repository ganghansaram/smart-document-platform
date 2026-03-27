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
    model_name_override = getattr(config, "TRANSLATOR_AI_SUMMARY_MODEL", "")
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
