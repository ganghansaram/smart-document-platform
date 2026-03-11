"""
질문 유형 분류 (Question Router)

질문을 SIMPLE/COMPARE/REASON/CHAT으로 분류하여 적절한 RAG 파이프라인으로 라우팅한다.
"""
import logging
from typing import Optional

import config
from services.llm_provider import get_provider

logger = logging.getLogger(__name__)

ROUTE_PROMPT = """질문을 분류하세요. 하나만 출력:
- SIMPLE: 정의, 절차, 수치 조회 등 단순 질문
- COMPARE: 비교, 대조, 종합이 필요한 질문
- REASON: 근거 판단, 분석, 추론이 필요한 질문
- CHAT: 인사, 잡담, 문서와 무관한 질문

질문: {question}
분류:"""

VALID_TYPES = {"SIMPLE", "COMPARE", "REASON", "CHAT"}


async def route_question(question: str) -> str:
    """
    질문 유형 분류.
    비활성화 시 또는 실패 시 SIMPLE 반환 (기존 파이프라인).
    """
    if not getattr(config, "QUESTION_ROUTING_ENABLED", True):
        return "SIMPLE"

    # 매우 짧은 질문은 라우팅 불필요
    if len(question) < 5:
        return "CHAT"

    provider = get_provider()

    try:
        prompt = ROUTE_PROMPT.format(question=question)
        result = await provider.generate(prompt, timeout=10)
        result = result.strip().upper()

        # 응답에서 유효한 타입 추출
        for t in VALID_TYPES:
            if t in result:
                logger.info("질문 라우팅: '%s' → %s", question[:50], t)
                return t

        logger.debug("라우팅 결과 파싱 불가 → SIMPLE: %s", result[:50])
        return "SIMPLE"

    except Exception as e:
        logger.warning("질문 라우팅 오류 → SIMPLE: %s", e)
        return "SIMPLE"
