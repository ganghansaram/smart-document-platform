"""
답변 검증 서비스 — LLM 자기 검증 (경량 할루시네이션 체크)

LLM 응답이 제공된 문서에 근거하는지 검증하고,
근거 불충분 시 면책 문구를 반환한다.

기본 비활성화. config.ANSWER_VERIFICATION_ENABLED = True로 활성화.
"""
import logging
from typing import List, Optional

import config
from services.llm_provider import get_provider

logger = logging.getLogger(__name__)

VERIFY_PROMPT = """답변이 참고 문서에 **실제로 포함된 정보만** 사용했는지 검증하세요.

=== 참고 문서 ===
{context}

=== 답변 ===
{answer}

검증 방법:
1. 답변의 각 구체적 사실(수치, 명칭, 비교)을 참고 문서에서 찾으세요
2. 문서에 없는 수치나 사실이 하나라도 있으면 PARTIAL 또는 UNSUPPORTED입니다
3. "정보를 찾지 못했습니다"류의 답변은 SUPPORTED입니다

판정 (SUPPORTED/PARTIAL/UNSUPPORTED 중 하나만):"""

DISCLAIMERS = {
    "PARTIAL": "\n\n---\n*이 답변의 일부는 제공된 문서에서 직접 확인되지 않았습니다.*",
    "UNSUPPORTED": "\n\n---\n*이 답변에 대한 충분한 근거를 문서에서 찾지 못했습니다. 정확성을 직접 확인해주세요.*",
}


async def verify_answer(
    answer: str,
    context: List[dict],
) -> Optional[str]:
    """
    답변 검증 수행.

    Returns:
        면책 문구 문자열 (PARTIAL/UNSUPPORTED 시) 또는 None (SUPPORTED/비활성화 시)
    """
    if not getattr(config, "ANSWER_VERIFICATION_ENABLED", False):
        return None

    # 컨텍스트가 없으면 검증 불필요 (CHAT 라우트 등)
    if not context:
        return None

    # 답변이 너무 짧으면 스킵
    if len(answer.strip()) < 20:
        return None

    # 토큰 절약: 컨텍스트 상위 3건 × 500자, 답변 500자
    context_summary = _summarize_context(context, max_docs=3, max_chars=500)
    answer_summary = answer[:500]

    provider = get_provider()

    try:
        prompt = VERIFY_PROMPT.format(
            context=context_summary,
            answer=answer_summary,
        )
        result = await provider.generate(prompt, timeout=15)
        result = result.strip().upper()

        # 유효한 판정 추출 (UNSUPPORTED를 먼저 체크 — SUPPORTED가 부분 문자열이므로)
        for verdict in ("UNSUPPORTED", "PARTIAL", "SUPPORTED"):
            if verdict in result:
                logger.info("답변 검증: %s (답변 %d자, 문서 %d건)", verdict, len(answer), len(context))
                return DISCLAIMERS.get(verdict)

        # 파싱 실패 → SUPPORTED로 간주 (답변 차단 안 함)
        logger.debug("답변 검증 파싱 불가 → SUPPORTED 간주: %s", result[:50])
        return None

    except Exception as e:
        logger.warning("답변 검증 오류 → 스킵: %s", e)
        return None


def _summarize_context(context: List[dict], max_docs: int = 3, max_chars: int = 500) -> str:
    """검증용 컨텍스트 요약 (토큰 절약)"""
    parts = []
    for doc in context[:max_docs]:
        title = doc.get("title", "")
        content = doc.get("content", "")[:max_chars]
        parts.append(f"[{title}] {content}")
    return "\n\n".join(parts)
