"""
쿼리 분해 (Query Decomposition)

복합 질문을 독립적인 서브쿼리로 분해하여 각각 검색 후 결과를 병합한다.
단순 질문은 분해하지 않고 그대로 반환한다.
"""
import json
import logging
from typing import List

import config
from services.llm_provider import get_provider

logger = logging.getLogger(__name__)

DECOMPOSE_PROMPT = """질문을 분석하여 독립적인 검색 쿼리로 분해하세요.

규칙:
1. 단순 질문(정의, 절차, 수치 조회)은 분해하지 않고 그대로 반환
2. 비교/대조 질문은 각 대상별 쿼리로 분해
3. 멀티홉 질문(A를 참조하는 B)은 단계별 쿼리로 분해
4. 최대 3개 서브쿼리로 제한
5. 반드시 JSON 배열로만 출력: ["쿼리1", "쿼리2"]
6. **서브쿼리는 반드시 한국어로 작성** (영어 약어는 예외)

예시:
- "RAG 파이프라인의 구조는?" → ["RAG 파이프라인의 구조"]
- "BM25와 벡터 검색의 차이점은?" → ["BM25 검색 방식", "벡터 검색 방식"]
- "FY1 국방부 보고서에서 언급된 시험 결과의 세부 내용은?" → ["FY1 국방부 보고서 시험 결과", "시험 결과 세부 내용"]

질문: {question}
서브쿼리:"""


def _parse_json_array(text: str) -> List[str]:
    """LLM 응답에서 JSON 배열 추출"""
    text = text.strip()

    # JSON 배열 직접 파싱 시도
    if text.startswith("["):
        # 닫는 괄호까지만 추출
        end = text.rfind("]")
        if end != -1:
            try:
                result = json.loads(text[:end + 1])
                if isinstance(result, list) and all(isinstance(q, str) for q in result):
                    return [q.strip() for q in result if q.strip()]
            except json.JSONDecodeError:
                pass

    # 마크다운 코드 블록 내 JSON 추출
    if "```" in text:
        import re
        match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group(1))
                if isinstance(result, list) and all(isinstance(q, str) for q in result):
                    return [q.strip() for q in result if q.strip()]
            except json.JSONDecodeError:
                pass

    # 줄 단위 파싱 폴백 (번호 매기기/불릿 형식만)
    import re
    lines = text.strip().split("\n")
    queries = []
    for line in lines:
        line = line.strip()
        # "1. 쿼리", "1) 쿼리", "- 쿼리", "* 쿼리" 형식만 매칭
        match = re.match(r'^(?:[\d]+[.)]\s+|[-*]\s+)(.+)', line)
        if match:
            cleaned = match.group(1).strip('"\'')
            if cleaned and len(cleaned) > 2:
                queries.append(cleaned)

    return queries[:3] if queries else []


async def decompose_query(question: str) -> List[str]:
    """
    질문을 서브쿼리로 분해.
    단순 질문이면 원본 그대로 반환 (1개짜리 리스트).
    실패 시에도 원본 질문 반환 (안전한 폴백).
    """
    if not getattr(config, "QUERY_DECOMPOSE_ENABLED", True):
        return [question]

    # 너무 짧은 질문은 분해 불필요
    if len(question) < 10:
        return [question]

    provider = get_provider()

    try:
        prompt = DECOMPOSE_PROMPT.format(question=question)
        result = await provider.generate(prompt, timeout=15)

        queries = _parse_json_array(result)

        if not queries:
            logger.debug("쿼리 분해 실패 (파싱 불가) → 원본 사용: %s", result[:100])
            return [question]

        # 단일 결과면 원본 사용 (불필요한 변환 방지)
        if len(queries) == 1:
            return [question]

        # 각 서브쿼리 길이 검증 (너무 길거나 짧으면 폴백)
        valid = [q for q in queries if 3 <= len(q) <= 200]
        if len(valid) < 2:
            return [question]

        logger.info("쿼리 분해: '%s' → %s", question, valid)
        return valid[:3]

    except Exception as e:
        logger.warning("쿼리 분해 오류 → 원본 사용: %s", e)
        return [question]
