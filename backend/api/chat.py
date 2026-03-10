"""
채팅 API (멀티턴 대화 지원 + 스트리밍)
"""
import asyncio
import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional

import config
from services.llm_client import generate_response, generate_response_stream
from services.conversation import store as conversation_store
from services.query_rewriter import rewrite_query

router = APIRouter()
logger = logging.getLogger(__name__)


class ContextDoc(BaseModel):
    title: str
    content: str
    path: Optional[str] = None
    section_id: Optional[str] = None


class ChatRequest(BaseModel):
    question: str
    context: List[ContextDoc] = []
    conversation_id: Optional[str] = None


class Source(BaseModel):
    title: str
    path: Optional[str] = None
    section_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]
    model: str
    conversation_id: str


def _search_internal(query: str, top_k: int = 5, skip_rerank: bool = False, filters: Optional[dict] = None) -> List[dict]:
    """내부 검색 호출 (search API와 동일 로직)"""
    from services.keyword_search import search_documents

    search_type = config.DEFAULT_SEARCH_TYPE
    fetch_k = top_k * config.RERANKER_TOP_K_MULTIPLIER if config.RERANKER_ENABLED else top_k

    if search_type == "keyword":
        results = search_documents(query, fetch_k)
    else:
        try:
            from services.embedding_client import get_embedding
            from services.vector_search import vector_search, hybrid_search

            query_embedding = get_embedding(query)

            if search_type == "vector":
                results = vector_search(query_embedding, fetch_k)
            else:
                results = hybrid_search(query, query_embedding, fetch_k)
        except Exception as e:
            logger.warning("벡터 검색 폴백 → 키워드: %s", e)
            results = search_documents(query, fetch_k)

    # 리랭킹 (skip_rerank=True이면 생략 — 멀티쿼리 병합 후 일괄 리랭킹 용도)
    if not skip_rerank and config.RERANKER_ENABLED and results:
        try:
            from services.reranker import rerank
            results = rerank(query, results, top_k)
        except Exception as e:
            logger.warning("리랭커 폴백: %s", e)
            results = results[:top_k]
    else:
        results = results[:top_k]

    # 중복 제거 (동일 content → 첫 번째만 유지)
    seen = set()
    deduped = []
    for r in results:
        key = r.get("content", "")[:200]
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    results = deduped

    # 메타데이터 필터 적용 (있는 경우)
    if filters:
        results = _apply_filters(results, filters)

    return results


def _apply_filters(results: List[dict], filters: dict) -> List[dict]:
    """
    메타데이터 기반 검색 결과 필터링.
    metadata 필드가 없는 결과는 path 기반 폴백으로 필터링.
    filters: {"doc_category": "시험 · 평가", "parent_doc": "..."}
    """
    if not filters:
        return results

    filtered = []
    for r in results:
        meta = r.get("metadata", {})
        path = r.get("path", "")
        match = True

        for key, value in filters.items():
            if not value:
                continue
            if meta:
                # 메타데이터 필드로 매칭
                if meta.get(key, "") != value:
                    match = False
                    break
            else:
                # 메타데이터 없으면 path 기반 폴백
                if key == "doc_category" and not path.startswith(value):
                    match = False
                    break

        if match:
            filtered.append(r)

    return filtered if filtered else results  # 필터 결과가 0이면 원본 반환 (안전)


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


async def _search_with_decomposition(question: str, search_query: str, top_k: int = 5) -> List[dict]:
    """
    쿼리 분해 + 멀티 검색 + 병합.
    분해가 비활성화이거나 단일 쿼리면 기존 검색과 동일하게 동작.
    """
    from services.query_decomposer import decompose_query

    sub_queries = await decompose_query(search_query)

    if len(sub_queries) <= 1:
        # 단일 쿼리 → 기존 검색 (리랭킹 포함)
        return _search_internal(search_query, top_k)

    # 멀티 쿼리 → 각각 검색 (리랭킹 생략) → 병합 → 원본 질문 기준 리랭킹
    logger.info("멀티 검색: %d 서브쿼리 실행", len(sub_queries))
    per_query_k = max(3, top_k // len(sub_queries) + 1)
    all_results = []
    for sq in sub_queries:
        results = _search_internal(sq, per_query_k, skip_rerank=True)
        all_results.extend(results)

    # 중복 제거
    all_results = _deduplicate(all_results)

    # 원본 질문 기준으로 리랭킹
    if config.RERANKER_ENABLED and all_results:
        try:
            from services.reranker import rerank
            all_results = rerank(question, all_results, top_k)
        except Exception as e:
            logger.warning("멀티쿼리 리랭커 폴백: %s", e)
            all_results = all_results[:top_k]
    else:
        all_results = all_results[:top_k]

    return all_results


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, raw_request: Request):
    # Analytics: record chat event
    try:
        from services.analytics import record_event, get_client_ip
        record_event("chat", get_client_ip(raw_request), None)
    except Exception:
        pass

    try:
        # 1) 세션 관리
        session = None
        if request.conversation_id:
            session = conversation_store.get_session(request.conversation_id)
        if not session:
            session = conversation_store.create_session()

        # 2) 대화 기록 조회
        history = session.get_history(config.MAX_CONVERSATION_TURNS)

        # 3) 컨텍스트 결정: 프론트엔드가 context를 보냈으면 그대로 사용, 아니면 백엔드 검색
        if request.context and len(request.context) > 0:
            # 기존 호환 모드 (프론트엔드가 검색 결과를 직접 전달)
            context_dicts = [
                {"title": d.title, "content": d.content, "path": d.path, "section_id": d.section_id}
                for d in request.context
            ]
        else:
            # 멀티턴 모드: 쿼리 재작성 → 쿼리 분해 → 검색
            search_query = rewrite_query(request.question, history)
            context_dicts = await _search_with_decomposition(
                request.question, search_query, config.MAX_SEARCH_RESULTS
            )

        # 4) LLM 응답 생성 (대화 기록 포함, sync → thread로 실행)
        result = await asyncio.to_thread(
            generate_response, request.question, context_dicts, history
        )

        # 5) 대화 기록에 현재 턴 저장
        session.add_message("user", request.question)
        session.add_message("assistant", result["answer"])

        return ChatResponse(
            answer=result["answer"],
            sources=result["sources"],
            model=result["model"],
            conversation_id=session.id,
        )

    except Exception as e:
        logger.error("채팅 처리 오류: %s", e, exc_info=True)
        return ChatResponse(
            answer="죄송합니다. 일시적인 오류가 발생했습니다. 다시 시도해주세요.",
            sources=[],
            model=config.OLLAMA_MODEL,
            conversation_id=request.conversation_id or "",
        )


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, raw_request: Request):
    """
    스트리밍 채팅 엔드포인트.
    NDJSON 형식으로 토큰을 실시간 전송한다.

    응답 형식 (한 줄씩):
      {"type":"token","content":"안녕"}
      {"type":"token","content":"하세요"}
      {"type":"done","sources":[...],"model":"...","conversation_id":"..."}
    오류 시:
      {"type":"error","message":"..."}
    """
    # Analytics
    try:
        from services.analytics import record_event, get_client_ip
        record_event("chat", get_client_ip(raw_request), None)
    except Exception:
        pass

    try:
        # 1) 세션 관리
        session = None
        if request.conversation_id:
            session = conversation_store.get_session(request.conversation_id)
        if not session:
            session = conversation_store.create_session()

        # 2) 대화 기록 조회
        history = session.get_history(config.MAX_CONVERSATION_TURNS)

        # 3) 컨텍스트 결정
        if request.context and len(request.context) > 0:
            context_dicts = [
                {"title": d.title, "content": d.content, "path": d.path, "section_id": d.section_id}
                for d in request.context
            ]
        else:
            search_query = rewrite_query(request.question, history)
            context_dicts = await _search_with_decomposition(
                request.question, search_query, config.MAX_SEARCH_RESULTS
            )

        # 4) 스트리밍 응답 생성
        token_iter, sources, model_name = await generate_response_stream(
            request.question, context_dicts, history=history
        )

        async def event_generator():
            full_answer = []
            try:
                async for token in token_iter:
                    full_answer.append(token)
                    yield json.dumps({"type": "token", "content": token}, ensure_ascii=False) + "\n"

                # 스트리밍 완료 → 대화 기록 저장
                answer_text = "".join(full_answer)
                session.add_message("user", request.question)
                session.add_message("assistant", answer_text)

                # 완료 메시지 (소스, 모델, 세션 ID 포함)
                done_payload = {
                    "type": "done",
                    "sources": [
                        {"title": s["title"], "path": s.get("path"), "section_id": s.get("section_id")}
                        for s in sources
                    ],
                    "model": model_name,
                    "conversation_id": session.id,
                }
                yield json.dumps(done_payload, ensure_ascii=False) + "\n"

            except Exception as e:
                logger.error("스트리밍 생성 오류: %s", e, exc_info=True)
                yield json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False) + "\n"

        return StreamingResponse(event_generator(), media_type="application/x-ndjson")

    except Exception as e:
        logger.error("스트리밍 채팅 처리 오류: %s", e, exc_info=True)
        error_payload = json.dumps({"type": "error", "message": "일시적인 오류가 발생했습니다."}, ensure_ascii=False) + "\n"

        async def error_stream():
            yield error_payload

        return StreamingResponse(error_stream(), media_type="application/x-ndjson")
