"""
LLM 클라이언트 — 프로바이더 추상화 래퍼

기존 generate_response() 시그니처 유지 (하위 호환).
스트리밍은 generate_response_stream()으로 제공.
"""
import asyncio
import json
import logging
from typing import AsyncIterator, List, Optional

import config
from services.llm_provider import get_provider

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """당신은 KF-21 전투기 기술 문서 전문 어시스턴트입니다. 제공된 참고 문서만을 기반으로 답변합니다.

[핵심 규칙]
1. 오직 제공된 문서 내용만 사용하여 답변합니다
2. 문서에 없는 내용은 절대 추측하지 않습니다
3. 정보가 없으면 "제공된 문서에서 해당 정보를 찾지 못했습니다"라고 답변합니다

[답변 형식]
- 마크다운으로 답변합니다: **굵게**와 목록(- 또는 1.)만 사용합니다
- 헤딩(#, ##, ### 등) 사용 금지
- 목록은 5개 이내로 제한합니다
- 핵심 내용을 먼저 간결하게 제시하고, 필요한 경우만 목록으로 구조화합니다
- 기술 용어는 문서에 표기된 그대로 사용합니다

[요청 유형별 대응]
- "요약해줘": 3~5문장으로 핵심만 간결하게 정리
- "핵심 내용": 중요 포인트를 불릿으로 5개 이내 나열
- "쉽게 설명해줘": 전문용어를 풀어서 비전문가도 이해할 수 있게 설명
- 일반 질문: 질문에 직접 답변 후 관련 맥락 보충
- 표 형태 요청: 마크다운 테이블(| col | col |) 형식 사용

[언어]
한국어로 답변합니다."""


def _build_prompt(question: str, context: List[dict], history: Optional[List[dict]] = None) -> tuple[str, list]:
    """프롬프트와 소스 목록 구성 (기존 로직 보존)"""
    context_parts = []
    sources = []

    for doc in context:
        context_parts.append(f"[{doc['title']}]\n{doc['content']}")
        sources.append({
            'title': doc['title'],
            'path': doc.get('path'),
            'section_id': doc.get('section_id')
        })

    context_text = "\n\n".join(context_parts)

    # 대화 기록 구성
    history_text = ""
    if history:
        history_lines = []
        for msg in history:
            role_label = "사용자" if msg["role"] == "user" else "어시스턴트"
            history_lines.append(f"{role_label}: {msg['content']}")
        history_text = "\n".join(history_lines)
        if len(history_text) > config.MAX_HISTORY_LENGTH:
            history_text = history_text[-config.MAX_HISTORY_LENGTH:]
            first_nl = history_text.find("\n")
            if first_nl != -1:
                history_text = history_text[first_nl + 1:]

    # 컨텍스트 길이 제한 — 문서별 균등 할당
    max_ctx = config.MAX_CONTEXT_LENGTH - len(history_text)
    if len(context_text) > max_ctx and context:
        per_doc = max(500, max_ctx // len(context))
        trimmed_parts = []
        for doc in context:
            part = f"[{doc['title']}]\n{doc['content']}"
            if len(part) > per_doc:
                part = part[:per_doc] + "..."
            trimmed_parts.append(part)
        context_text = "\n\n".join(trimmed_parts)
        if len(context_text) > max_ctx:
            context_text = context_text[:max_ctx] + "..."

    # 프롬프트 구성 (system은 별도 전달, prompt에는 문서+기록+질문만)
    prompt_parts = [f"=== 참고 문서 ===\n{context_text}"]
    if history_text:
        prompt_parts.append(f"\n\n=== 대화 기록 ===\n{history_text}")
    prompt_parts.append(f"\n\n=== 질문 ===\n{question}")
    prompt = "".join(prompt_parts)

    return prompt, sources


def generate_response(question: str, context: List[dict], history: Optional[List[dict]] = None) -> dict:
    """
    동기식 응답 생성 (기존 API 호환).
    내부적으로 async 프로바이더를 호출한다.
    """
    prompt, sources = _build_prompt(question, context, history)
    provider = get_provider()

    try:
        # FastAPI 이벤트 루프 내에서 호출될 수 있으므로 새 루프 생성
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # 이미 이벤트 루프가 돌고 있으면 (sync 엔드포인트에서 호출),
            # 별도 스레드에서 실행
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                answer = pool.submit(
                    asyncio.run,
                    provider.generate(prompt, system=SYSTEM_PROMPT)
                ).result(timeout=120)
        else:
            answer = asyncio.run(provider.generate(prompt, system=SYSTEM_PROMPT))

        return {
            'answer': answer,
            'sources': sources,
            'model': provider.model_name
        }

    except Exception as e:
        logger.error("LLM 응답 생성 오류: %s", e, exc_info=True)
        return {
            'answer': f'LLM 서버 연결 오류: {str(e)}',
            'sources': [],
            'model': provider.model_name
        }


async def generate_response_stream(
    question: str, context: List[dict], history: Optional[List[dict]] = None
) -> tuple[AsyncIterator[str], list, str]:
    """
    스트리밍 응답 생성.
    Returns: (token_iterator, sources, model_name)
    """
    prompt, sources = _build_prompt(question, context, history)
    provider = get_provider()

    async def token_stream():
        async for token in provider.generate_stream(prompt, system=SYSTEM_PROMPT):
            yield token

    return token_stream(), sources, provider.model_name
