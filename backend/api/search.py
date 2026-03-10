"""
검색 API
"""
import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import List, Optional

import config
from services.keyword_search import search_documents

router = APIRouter()
logger = logging.getLogger(__name__)


class SearchFilters(BaseModel):
    doc_category: Optional[str] = None   # 최상위 메뉴 카테고리 (예: "시험 · 평가")
    parent_doc: Optional[str] = None     # 상위 문서명


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    search_type: Optional[str] = None  # "keyword" | "vector" | "hybrid"
    filters: Optional[SearchFilters] = None


class SearchResult(BaseModel):
    title: str
    content: str
    path: str
    section_id: Optional[str] = None
    score: float


class SearchResponse(BaseModel):
    results: List[SearchResult]
    search_type: str = "keyword"
    total: int


def _maybe_rerank(query: str, results: List[dict], top_k: int) -> List[dict]:
    """리랭커가 활성화되어 있으면 재정렬, 아니면 그대로 반환"""
    if not config.RERANKER_ENABLED or not results:
        return results[:top_k]
    try:
        from services.reranker import rerank
        return rerank(query, results, top_k)
    except Exception as e:
        logger.warning("리랭커 폴백 → 원본 순서: %s", e)
        return results[:top_k]


def _apply_search_filters(results: List[dict], filters: Optional[SearchFilters]) -> List[dict]:
    """메타데이터 기반 검색 결과 필터링"""
    if not filters:
        return results

    filter_dict = {}
    if filters.doc_category:
        filter_dict["doc_category"] = filters.doc_category
    if filters.parent_doc:
        filter_dict["parent_doc"] = filters.parent_doc

    if not filter_dict:
        return results

    filtered = []
    for r in results:
        meta = r.get("metadata", {})
        path = r.get("path", "")
        match = True

        for key, value in filter_dict.items():
            if meta:
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

    return filtered if filtered else results  # 필터 결과가 0이면 원본 반환


@router.post("/search", response_model=SearchResponse)
def search(request: SearchRequest, raw_request: Request):
    # Analytics: record search event
    try:
        from services.analytics import record_event, get_client_ip
        record_event("search", get_client_ip(raw_request), {"query": request.query})
    except Exception:
        pass

    search_type = request.search_type or config.DEFAULT_SEARCH_TYPE
    top_k = request.top_k
    # 리랭킹 시 더 많은 후보를 가져옴 (필터가 있으면 더 많이 가져옴)
    filter_multiplier = 2 if request.filters else 1
    fetch_k = top_k * config.RERANKER_TOP_K_MULTIPLIER * filter_multiplier if config.RERANKER_ENABLED else top_k * filter_multiplier

    # 키워드 전용
    if search_type == "keyword":
        results = search_documents(request.query, fetch_k)
        results = _apply_search_filters(results, request.filters)
        results = _maybe_rerank(request.query, results, top_k)
        return SearchResponse(results=results, search_type="keyword", total=len(results))

    # 벡터 또는 하이브리드 → 임베딩 필요
    try:
        from services.embedding_client import get_embedding
        from services.vector_search import vector_search, hybrid_search

        query_embedding = get_embedding(request.query)

        if search_type == "vector":
            results = vector_search(query_embedding, fetch_k)
            results = _apply_search_filters(results, request.filters)
            results = _maybe_rerank(request.query, results, top_k)
            return SearchResponse(results=results, search_type="vector", total=len(results))

        # hybrid (기본)
        results = hybrid_search(request.query, query_embedding, fetch_k)
        results = _apply_search_filters(results, request.filters)
        results = _maybe_rerank(request.query, results, top_k)
        return SearchResponse(results=results, search_type="hybrid", total=len(results))

    except Exception as e:
        # 벡터 검색 실패 시 키워드로 폴백
        logger.warning("벡터 검색 폴백 → 키워드: %s", e)
        results = search_documents(request.query, fetch_k)
        results = _apply_search_filters(results, request.filters)
        results = _maybe_rerank(request.query, results, top_k)
        return SearchResponse(results=results, search_type="keyword", total=len(results))
