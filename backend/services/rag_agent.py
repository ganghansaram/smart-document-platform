"""
Agentic RAG — 반복적 검색-판단-재검색 루프

복합 질문에 대해 최대 MAX_ITERATIONS 회 반복하여
필요한 정보를 수집한 후 최종 응답을 생성한다.
"""
import json
import logging
from typing import List, Optional

import config
from services.llm_provider import get_provider

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 3

PLAN_PROMPT = """당신은 기술 문서 검색 에이전트입니다.
사용자 질문에 답하기 위해 어떤 정보를 검색해야 하는지 판단합니다.

이미 수집된 문서:
{collected_summary}

사용자 질문: {question}

다음 JSON만 출력하세요:
{{"sufficient": true/false, "query": "검색할 쿼리", "reason": "판단 이유"}}

규칙:
- 수집된 문서로 질문에 충분히 답할 수 있으면 sufficient=true
- 부족하면 sufficient=false, 필요한 정보를 찾기 위한 검색 쿼리를 query에 작성
- 이전 검색과 다른 관점의 쿼리를 생성 (중복 검색 방지)"""

CONFIDENCE_PROMPT = """수집된 문서를 기반으로 질문에 대한 답변 신뢰도를 판단하세요.

질문: {question}
수집된 문서 수: {doc_count}
검색 반복 횟수: {iterations}

다음 중 하나만 출력하세요:
- high: 문서에서 직접적인 답변을 찾을 수 있음
- medium: 관련 정보는 있지만 일부 부족
- low: 관련 문서를 충분히 찾지 못함

신뢰도:"""


def _summarize_collected(context: List[dict]) -> str:
    """수집된 문서를 간략히 요약 (플래닝 프롬프트용)"""
    if not context:
        return "(아직 수집된 문서 없음)"

    parts = []
    for i, doc in enumerate(context[:5], 1):
        title = doc.get("title", "?")
        snippet = doc.get("content", "")[:100]
        parts.append(f"{i}. [{title}] {snippet}...")
    return "\n".join(parts)


def _parse_plan(text: str) -> dict:
    """LLM 계획 응답을 JSON으로 파싱"""
    text = text.strip()

    # JSON 직접 파싱
    if text.startswith("{"):
        end = text.rfind("}")
        if end != -1:
            try:
                return json.loads(text[:end + 1])
            except json.JSONDecodeError:
                pass

    # 마크다운 코드 블록 내 JSON
    if "```" in text:
        import re
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

    # "sufficient": true/false 패턴 탐색
    if "sufficient" in text.lower():
        sufficient = "true" in text.lower().split("sufficient")[1][:20]
        return {"sufficient": sufficient, "query": "", "reason": "파싱 폴백"}

    return {"sufficient": True, "query": "", "reason": "파싱 실패 → 충분으로 간주"}


async def _judge_confidence(question: str, context: List[dict], iterations: int) -> str:
    """응답 신뢰도 판단 (high/medium/low)"""
    # 문서가 없으면 무조건 low
    if not context:
        return "low"

    # 단일 패스 + 문서 충분 → high (LLM 호출 절약)
    if iterations <= 1 and len(context) >= 3:
        return "high"

    provider = get_provider()
    try:
        prompt = CONFIDENCE_PROMPT.format(
            question=question,
            doc_count=len(context),
            iterations=iterations,
        )
        result = await provider.generate(prompt, timeout=10)
        result = result.strip().lower()

        for level in ("high", "medium", "low"):
            if level in result:
                return level

        return "medium"
    except Exception:
        # 판단 실패 시 보수적으로
        return "medium" if context else "low"


async def agentic_rag(question: str, search_fn, top_k: int = 5) -> dict:
    """
    Agentic RAG 루프.

    Args:
        question: 사용자 질문
        search_fn: 검색 함수 (query, top_k, skip_rerank) → List[dict]
        top_k: 최종 결과 수

    Returns:
        {
            "context": List[dict],  # 수집된 검색 결과
            "confidence": str,      # "high" | "medium" | "low"
            "iterations": int,      # 실행된 반복 수
            "search_queries": List[str],  # 사용된 검색 쿼리
        }
    """
    max_iter = getattr(config, "MAX_AGENT_ITERATIONS", MAX_ITERATIONS)
    provider = get_provider()
    collected_context = []
    search_queries = []
    iterations = 0

    for i in range(max_iter):
        iterations = i + 1

        # 1. 계획: 어떤 정보를 더 찾아야 하는지 판단
        summary = _summarize_collected(collected_context)
        plan_prompt = PLAN_PROMPT.format(
            collected_summary=summary,
            question=question,
        )
        try:
            plan_text = await provider.generate(plan_prompt, timeout=15)
            plan = _parse_plan(plan_text)
        except Exception as e:
            logger.warning("Agent 계획 수립 오류 (iter %d): %s", i + 1, e)
            break

        # 충분하다고 판단하면 종료
        if plan.get("sufficient"):
            logger.info("Agent: 충분성 판단 → 종료 (iter %d)", i + 1)
            break

        # 2. 검색 실행
        query = plan.get("query", "").strip()
        if not query:
            break

        search_queries.append(query)
        logger.info("Agent 검색 (iter %d): '%s'", i + 1, query)

        try:
            new_results = search_fn(query, top_k, skip_rerank=True)
            collected_context.extend(new_results)
        except Exception as e:
            logger.warning("Agent 검색 오류 (iter %d): %s", i + 1, e)
            break

        # 3. 중복 제거
        collected_context = _deduplicate(collected_context)

    # 첫 반복에서 검색 결과가 없으면 원본 질문으로 직접 검색
    if not collected_context:
        search_queries.append(question)
        try:
            collected_context = search_fn(question, top_k, skip_rerank=False)
        except Exception:
            pass

    # 리랭킹 (원본 질문 기준)
    if config.RERANKER_ENABLED and collected_context and len(collected_context) > top_k:
        try:
            from services.reranker import rerank
            collected_context = rerank(question, collected_context, top_k)
        except Exception as e:
            logger.warning("Agent 리랭커 폴백: %s", e)
            collected_context = collected_context[:top_k]
    else:
        collected_context = collected_context[:top_k]

    # 신뢰도 판단
    confidence = await _judge_confidence(question, collected_context, iterations)

    return {
        "context": collected_context,
        "confidence": confidence,
        "iterations": iterations,
        "search_queries": search_queries,
    }


def _deduplicate(results: List[dict]) -> List[dict]:
    """검색 결과 중복 제거"""
    seen = set()
    deduped = []
    for r in results:
        key = r.get("content", "")[:200]
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    return deduped
