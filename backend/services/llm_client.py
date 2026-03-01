"""
Ollama LLM 클라이언트
"""
import requests
from typing import List, Optional

import config

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

def generate_response(question: str, context: List[dict], history: Optional[List[dict]] = None) -> dict:
    """
    Ollama API를 사용하여 응답 생성
    history: [{"role": "user"|"assistant", "content": str}, ...] 대화 기록 (선택)
    """
    # 컨텍스트 구성 (직접 호출 모드와 동일한 형식)
    context_parts = []
    sources = []

    for i, doc in enumerate(context):
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
        # 최대 길이 제한 (오래된 턴부터 잘림)
        if len(history_text) > config.MAX_HISTORY_LENGTH:
            history_text = history_text[-config.MAX_HISTORY_LENGTH:]
            # 잘린 줄 제거 (중간에 끊긴 첫 줄 삭제)
            first_nl = history_text.find("\n")
            if first_nl != -1:
                history_text = history_text[first_nl + 1:]

    # 컨텍스트 길이 제한 — 문서별 균등 할당 (중간 잘림 방지)
    max_ctx = config.MAX_CONTEXT_LENGTH - len(history_text)
    if len(context_text) > max_ctx and context:
        per_doc = max(500, max_ctx // len(context))
        trimmed_parts = []
        for i, doc in enumerate(context):
            part = f"[{doc['title']}]\n{doc['content']}"
            if len(part) > per_doc:
                part = part[:per_doc] + "..."
            trimmed_parts.append(part)
        context_text = "\n\n".join(trimmed_parts)
        # 최종 안전장치
        if len(context_text) > max_ctx:
            context_text = context_text[:max_ctx] + "..."

    # 프롬프트 구성
    prompt_parts = [SYSTEM_PROMPT, f"\n\n=== 참고 문서 ===\n{context_text}"]
    if history_text:
        prompt_parts.append(f"\n\n=== 대화 기록 ===\n{history_text}")
    prompt_parts.append(f"\n\n=== 질문 ===\n{question}")
    prompt = "".join(prompt_parts)

    try:
        response = requests.post(
            f"{config.OLLAMA_URL}/api/generate",
            json={
                "model": config.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0}
            },
            timeout=60
        )
        response.raise_for_status()
        data = response.json()

        return {
            'answer': data.get('response', ''),
            'sources': sources,
            'model': config.OLLAMA_MODEL
        }

    except requests.exceptions.RequestException as e:
        return {
            'answer': f'Ollama 서버 연결 오류: {str(e)}',
            'sources': [],
            'model': config.OLLAMA_MODEL
        }
