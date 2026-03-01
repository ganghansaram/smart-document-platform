"""
LLM 기반 후속 질문 → 독립 검색 쿼리 재작성
"""
import logging
from typing import List

import requests

import config

logger = logging.getLogger(__name__)

REWRITE_SYSTEM_PROMPT = """당신은 검색 쿼리 재작성 전문가입니다.
사용자의 후속 질문을 대화 맥락을 반영하여 **독립적인 검색 쿼리**로 변환합니다.

규칙:
1. 대명사("그것", "이", "그 엔진" 등)를 구체적 명사로 교체
2. 생략된 주어/목적어를 대화 맥락에서 복원
3. 검색에 불필요한 조사/어미는 간결하게 정리
4. 이미 독립적인 질문이면 그대로 반환
5. 재작성된 쿼리만 출력 (설명 없이 한 줄)"""


def _fallback_query(question: str, history: List[dict]) -> str:
    """이전 사용자 질문의 핵심 키워드 + 현재 질문을 결합."""
    # 가장 최근 사용자 질문 추출
    prev_user_q = ""
    for msg in reversed(history):
        if msg["role"] == "user":
            prev_user_q = msg["content"]
            break

    if not prev_user_q:
        return question

    # 이전 질문에서 조사/어미 제거한 키워드 추출 (2자 이상)
    prev_keywords = [w for w in prev_user_q.split() if len(w) >= 2]
    # 현재 질문과 중복되는 단어 제거
    current_words = set(question.split())
    unique_keywords = [w for w in prev_keywords if w not in current_words]

    if not unique_keywords:
        return question

    combined = " ".join(unique_keywords) + " " + question
    logger.info("폴백 쿼리 결합: '%s'", combined)
    return combined


def rewrite_query(question: str, history: List[dict]) -> str:
    """
    대화 기록을 참고하여 후속 질문을 독립 검색 쿼리로 재작성.
    기록이 없거나 재작성 비활성화 시 원본 반환.
    LLM 재작성 실패 시 이전 질문 키워드 + 현재 질문 결합으로 폴백.
    """
    if not config.QUERY_REWRITE_ENABLED:
        return question

    if not history:
        return question

    fallback = _fallback_query(question, history)

    # 최근 대화 요약 구성
    history_lines = []
    for msg in history:
        role_label = "사용자" if msg["role"] == "user" else "어시스턴트"
        # 어시스턴트 답변은 첫 100자만
        content = msg["content"]
        if msg["role"] == "assistant" and len(content) > 100:
            content = content[:100] + "..."
        history_lines.append(f"{role_label}: {content}")

    history_text = "\n".join(history_lines)

    prompt = (
        f"{REWRITE_SYSTEM_PROMPT}\n\n"
        f"=== 대화 기록 ===\n{history_text}\n\n"
        f"=== 현재 질문 ===\n{question}\n\n"
        f"=== 재작성된 검색 쿼리 ==="
    )

    try:
        response = requests.post(
            f"{config.OLLAMA_URL}/api/generate",
            json={
                "model": config.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0},
            },
            timeout=15,
        )
        response.raise_for_status()
        rewritten = response.json().get("response", "").strip()

        # 빈 결과 또는 비정상 응답 → 폴백
        if not rewritten or len(rewritten) > len(question) * 3:
            return fallback

        logger.info("쿼리 재작성: '%s' → '%s'", question, rewritten)
        return rewritten

    except Exception as e:
        logger.warning("쿼리 재작성 실패 (폴백 사용): %s", e)
        return fallback
