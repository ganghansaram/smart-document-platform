"""
키워드 기반 검색 서비스

BM25 + 한국어 형태소 분석 기반 확률적 검색.
rank-bm25 미설치 시 나이브 substring 매칭으로 폴백.
"""
import json
import logging
from pathlib import Path
from typing import List, Optional

import config

logger = logging.getLogger(__name__)

# BM25 인덱스 캐시
_bm25_index = None
_bm25_metadata = None
_bm25_available = None


def _check_bm25():
    """rank-bm25 사용 가능 여부 확인"""
    global _bm25_available
    if _bm25_available is not None:
        return _bm25_available
    try:
        from rank_bm25 import BM25Okapi  # noqa: F401
        _bm25_available = True
        logger.info("rank-bm25 사용 가능")
    except ImportError:
        _bm25_available = False
        logger.info("rank-bm25 미설치 - 나이브 키워드 검색 폴백")
    return _bm25_available


def load_search_index():
    """검색 인덱스 로드"""
    index_path = Path(__file__).parent.parent / config.SEARCH_INDEX_PATH
    if not index_path.exists():
        return []

    with open(index_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _build_bm25_index(index: list):
    """BM25 인덱스 구축 (제목 3x 가중)"""
    global _bm25_index, _bm25_metadata

    from rank_bm25 import BM25Okapi
    from services.korean_tokenizer import tokenize

    corpus = []
    metadata = []

    for doc in index:
        title = doc.get('title', '')
        content = doc.get('content', '')

        # 제목 토큰 3회 반복으로 가중치 부여
        title_tokens = tokenize(title)
        content_tokens = tokenize(content)
        tokens = title_tokens * 3 + content_tokens

        if tokens:
            corpus.append(tokens)
            metadata.append(doc)

    if corpus:
        _bm25_index = BM25Okapi(corpus)
        _bm25_metadata = metadata
        logger.info("BM25 인덱스 구축 완료: %d 문서", len(metadata))
    else:
        _bm25_index = None
        _bm25_metadata = []


def reload_bm25_index():
    """BM25 인덱스 강제 재구축 (검색 인덱스 재생성 시 호출)"""
    global _bm25_index, _bm25_metadata
    _bm25_index = None
    _bm25_metadata = None

    if _check_bm25():
        index = load_search_index()
        if index:
            _build_bm25_index(index)


def search_documents(query: str, top_k: int = 5) -> List[dict]:
    """
    키워드 기반 문서 검색.

    BM25 사용 가능 시: BM25Okapi 확률적 검색
    미설치 시: 나이브 substring 매칭 (기존 방식)
    """
    if _check_bm25():
        return _search_bm25(query, top_k)
    else:
        return _search_naive(query, top_k)


def _search_bm25(query: str, top_k: int) -> List[dict]:
    """BM25 기반 검색"""
    global _bm25_index, _bm25_metadata

    # lazy 인덱스 구축
    if _bm25_index is None:
        index = load_search_index()
        if not index:
            return []
        _build_bm25_index(index)

    if _bm25_index is None or not _bm25_metadata:
        return []

    from services.korean_tokenizer import tokenize

    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    scores = _bm25_index.get_scores(query_tokens)

    # 점수 > 0인 문서만 추출
    scored_docs = []
    for i, score in enumerate(scores):
        if score > 0 and i < len(_bm25_metadata):
            doc = _bm25_metadata[i]
            scored_docs.append({
                'title': doc.get('title', ''),
                'content': doc.get('content', '')[:1600],
                'path': doc.get('url', ''),
                'section_id': doc.get('section_id'),
                'score': float(score)
            })

    scored_docs.sort(key=lambda x: -x['score'])
    return scored_docs[:top_k]


def _search_naive(query: str, top_k: int) -> List[dict]:
    """나이브 키워드 검색 (폴백)"""
    index = load_search_index()
    if not index:
        return []

    terms = [t.lower() for t in query.split() if len(t) >= 2]
    if not terms:
        return []

    results = []
    for doc in index:
        title_lower = doc.get('title', '').lower()
        content_lower = doc.get('content', '').lower()
        score = 0

        for term in terms:
            if term in title_lower:
                score += 10
            if term in content_lower:
                score += 1

        if score > 0:
            results.append({
                'title': doc.get('title', ''),
                'content': doc.get('content', '')[:1600],
                'path': doc.get('url', ''),
                'section_id': doc.get('section_id'),
                'score': score
            })

    results.sort(key=lambda x: -x['score'])
    return results[:top_k]
