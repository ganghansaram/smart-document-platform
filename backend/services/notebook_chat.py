"""
Notebook Q&A 서비스 — 단일 문서 기반 질의응답

크기 적응형 컨텍스트 구성:
- 짧은 문서 (≤ threshold): 전문 직접 주입 (Notion AI 방식)
- 긴 문서 (> threshold): 키워드 매칭 관련 섹션 선별
"""
import logging
import re
from pathlib import Path
from typing import Optional, AsyncIterator

import config
from services.llm_provider import get_provider
from services.ai_summary import split_sections

logger = logging.getLogger(__name__)

_DEFAULT_QA_THRESHOLD = 12000  # 기본 12,000자

_QA_SYSTEM_PROMPT = (
    "당신은 학술 문서 분석 어시스턴트입니다.\n"
    "아래 제공된 문서 내용을 바탕으로 사용자의 질문에 답변하세요.\n\n"
    "규칙:\n"
    "- 문서에 없는 내용은 \"문서에서 해당 내용을 찾을 수 없습니다\"라고 답변\n"
    "- 구체적 수치·페이지·섹션을 인용하여 근거 제시\n"
    "- 한국어로 답변\n"
    "- 간결하고 명확하게 (3~5문장 권장)\n"
    "- 마크다운 서식 사용 가능 (**굵게**, 목록 등)"
)


def get_qa_context(username: str, doc_id: str) -> tuple[str, str]:
    """Q&A 컨텍스트 소스 결정.

    Returns: (text, source_type)
    폴백 체인: translated → extracted → raw PDF
    """
    from services.translator_service import _doc_dir

    doc_dir = _doc_dir(username, doc_id)

    # 1순위: 번역문 (한국어 질문 시 한국어 컨텍스트가 유리)
    translated = doc_dir / "full_translated.md"
    if translated.exists():
        return translated.read_text(encoding="utf-8"), "translated"

    # 2순위: 추출 원문
    extracted = doc_dir / "full_extracted.md"
    if extracted.exists():
        return extracted.read_text(encoding="utf-8"), "extracted"

    # 3순위: PDF 직접 텍스트 추출 (비구조)
    pdf_path = doc_dir / "original.pdf"
    if pdf_path.exists():
        try:
            import fitz
            doc = fitz.open(str(pdf_path))
            texts = [doc[i].get_text() for i in range(len(doc))]
            doc.close()
            return "\n\n".join(texts), "raw_pdf"
        except Exception as e:
            logger.warning("PDF 텍스트 추출 실패: %s", e)

    return "", "none"


def build_qa_context(question: str, full_text: str) -> tuple[str, list[int]]:
    """크기 적응형 컨텍스트 구성.

    짧은 문서 → 직접 주입 (업계 표준, Notion AI 방식)
    긴 문서 → 질문 관련 섹션 선별 (키워드 매칭)

    Returns: (context_text, source_pages)
    """
    from services.md_translator import _strip_frontmatter

    text = _strip_frontmatter(full_text).strip()
    threshold = getattr(config, "TRANSLATOR_AI_QA_THRESHOLD", 0) or _DEFAULT_QA_THRESHOLD

    if len(text) <= threshold:
        pages = _extract_page_numbers(text)
        return text, pages

    context = _select_relevant_sections(question, text, threshold)
    pages = _extract_page_numbers(context)
    return context, pages


def _extract_page_numbers(text: str) -> list[int]:
    """텍스트 내 <!-- Page N --> 주석에서 페이지 번호 추출."""
    return sorted(set(int(m) for m in re.findall(r'<!--\s*Page\s+(\d+)', text)))


def _select_relevant_sections(question: str, full_text: str, max_chars: int) -> str:
    """키워드 매칭 기반 관련 섹션 선별."""
    sections = split_sections(full_text)

    # 질문에서 토큰 추출 (한국어+영어 모두 지원)
    question_tokens = set(re.findall(r'\w{2,}', question.lower()))
    scored = []
    for sec in sections:
        content_lower = sec["content"].lower()
        overlap = sum(1 for t in question_tokens if t in content_lower)
        scored.append((overlap, sec))

    # 점수순 정렬, 상위 섹션들을 max_chars까지 수집
    scored.sort(key=lambda x: -x[0])
    result = ""
    for score, sec in scored:
        heading = sec.get("heading", "")
        chunk = f"## {heading}\n{sec['content']}\n\n" if heading else sec["content"] + "\n\n"
        if len(result) + len(chunk) > max_chars:
            break
        result += chunk

    # 폴백: 관련 섹션 없으면 앞 max_chars
    return result if result.strip() else full_text[:max_chars]


def _build_qa_prompt(question: str, context: str, history: list) -> str:
    """Q&A 프롬프트 구성."""
    parts = [f"=== 문서 내용 ===\n{context}"]

    if history:
        history_lines = []
        for msg in history[-10:]:  # 최근 10개 메시지 (5턴)
            role_label = "사용자" if msg["role"] == "user" else "어시스턴트"
            history_lines.append(f"{role_label}: {msg['content']}")
        history_text = "\n".join(history_lines)
        # 히스토리 길이 제한
        if len(history_text) > 2000:
            history_text = history_text[-2000:]
        parts.append(f"\n\n=== 대화 기록 ===\n{history_text}")

    parts.append(f"\n\n=== 질문 ===\n{question}")
    return "".join(parts)


async def ask_document_stream(
    username: str,
    doc_id: str,
    question: str,
    conversation_id: Optional[str] = None,
) -> tuple[AsyncIterator[str], str, str, str, list[int]]:
    """문서 Q&A 스트리밍 응답.

    Returns: (token_iterator, source_type, model_name, conversation_id, source_pages)
    """
    from services.conversation import store as conversation_store

    # 1. 세션 관리
    session = None
    if conversation_id:
        session = conversation_store.get_session(conversation_id)
    if not session:
        session = conversation_store.create_session()

    # 2. 대화 기록
    history = session.get_history(getattr(config, "MAX_CONVERSATION_TURNS", 5))

    # 3. 컨텍스트 확보
    full_text, source_type = get_qa_context(username, doc_id)
    if not full_text:
        async def error_stream():
            yield "문서 텍스트를 찾을 수 없습니다. 먼저 문서 추출 또는 번역을 실행해주세요."
        return error_stream(), "none", "", session.id, []

    context, source_pages = build_qa_context(question, full_text)

    # 4. 프롬프트 구성
    prompt = _build_qa_prompt(question, context, history)

    # 5. LLM 스트리밍 호출
    provider = get_provider()
    model_name = provider.model_name

    token_iter = provider.generate_stream(prompt, system=_QA_SYSTEM_PROMPT, temperature=0.3, timeout=180)

    # 6. 대화 기록 저장 (사용자 메시지 먼저, 어시스턴트는 스트리밍 완료 후 호출자가 저장)
    session.add_message("user", question)

    return token_iter, source_type, model_name, session.id, source_pages
