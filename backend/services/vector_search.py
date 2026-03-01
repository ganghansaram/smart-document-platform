"""
FAISS 벡터 검색 서비스
"""
import json
import logging
from pathlib import Path
from typing import List, Optional

import numpy as np

import config

logger = logging.getLogger(__name__)

# 모듈 레벨 캐시
_faiss_index = None
_index_metadata = None


def _load_index():
    """FAISS 인덱스 + 메타데이터 로드 (캐시)"""
    global _faiss_index, _index_metadata

    if _faiss_index is not None and _index_metadata is not None:
        return _faiss_index, _index_metadata

    import faiss

    base_path = Path(__file__).parent.parent / config.VECTOR_INDEX_PATH
    faiss_path = str(base_path) + ".faiss"
    meta_path = str(base_path) + "_meta.json"

    if not Path(faiss_path).exists() or not Path(meta_path).exists():
        logger.warning("벡터 인덱스 파일 없음: %s", faiss_path)
        return None, None

    _faiss_index = faiss.read_index(faiss_path)

    with open(meta_path, "r", encoding="utf-8") as f:
        _index_metadata = json.load(f)

    logger.info("벡터 인덱스 로드: %d 문서", _faiss_index.ntotal)
    return _faiss_index, _index_metadata


def reload_index():
    """인덱스 강제 리로드"""
    global _faiss_index, _index_metadata
    _faiss_index = None
    _index_metadata = None
    return _load_index()


def vector_search(query_embedding: List[float], top_k: int = 5) -> List[dict]:
    """
    벡터 유사도 검색.
    returns: [{title, content, path, section_id, score}, ...]
    """
    index, metadata = _load_index()
    if index is None:
        return []

    query_vec = np.array([query_embedding], dtype=np.float32)

    # L2 거리 → 유사도 점수로 변환
    distances, indices = index.search(query_vec, min(top_k, index.ntotal))

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0 or idx >= len(metadata):
            continue
        doc = metadata[idx]
        # L2 거리를 0~1 유사도로 변환: score = 1 / (1 + distance)
        score = 1.0 / (1.0 + float(dist))
        # 최소 유사도 이하 제거 (무관한 쿼리 필터링)
        if score < config.MIN_VECTOR_SCORE:
            continue
        results.append({
            "title": doc["title"],
            "content": doc.get("content", "")[:1600],
            "path": doc.get("url", ""),
            "section_id": doc.get("section_id"),
            "score": score,
        })

    return results


def _index_paths():
    """인덱스 파일 경로 반환"""
    base_path = Path(__file__).parent.parent / config.VECTOR_INDEX_PATH
    return str(base_path) + ".faiss", str(base_path) + "_meta.json"


def append_documents(docs: list) -> dict:
    """
    새 문서를 기존 FAISS 인덱스에 증분 추가.
    docs: [{title, content, url, section_id, path}, ...]
    returns: {"success": bool, "added": int}
    """
    import faiss
    from services.embedding_client import get_embeddings

    if not docs:
        return {"success": True, "added": 0}

    faiss_path, meta_path = _index_paths()

    # 기존 인덱스 로드 (없으면 새로 생성)
    if Path(faiss_path).exists() and Path(meta_path).exists():
        index = faiss.read_index(faiss_path)
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    else:
        index = faiss.IndexFlatL2(config.EMBEDDING_DIMENSION)
        metadata = []

    # 임베딩 생성 (title 가중 반복)
    texts = [f"{d.get('title','')}\n{d.get('title','')}\n{d.get('content','')}" for d in docs]
    embeddings = np.array(get_embeddings(texts), dtype=np.float32)

    # FAISS에 추가
    index.add(embeddings)

    # 메타데이터 추가
    for doc in docs:
        metadata.append({
            "title": doc.get("title", ""),
            "content": doc.get("content", ""),
            "url": doc.get("url", ""),
            "section_id": doc.get("section_id"),
            "path": doc.get("path", ""),
        })

    # 저장
    Path(faiss_path).parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, faiss_path)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    # 메모리 캐시 갱신
    global _faiss_index, _index_metadata
    _faiss_index = index
    _index_metadata = metadata

    logger.info("벡터 인덱스 증분 추가: %d문서 (총 %d)", len(docs), index.ntotal)
    return {"success": True, "added": len(docs)}


def hybrid_search(
    query: str,
    query_embedding: List[float],
    top_k: int = 5,
    keyword_results: Optional[List[dict]] = None,
) -> List[dict]:
    """
    하이브리드 검색: RRF (Reciprocal Rank Fusion) 기반 키워드 + 벡터 결과 병합.
    """
    from services.keyword_search import search_documents

    # 키워드 검색 결과 (이미 계산된 경우 재사용)
    if keyword_results is None:
        keyword_results = search_documents(query, top_k=top_k * 2)

    # 벡터 검색 결과
    vec_results = vector_search(query_embedding, top_k=top_k * 2)

    # RRF 병합
    k = config.HYBRID_RRF_K
    doc_scores = {}  # key = (path, section_id)
    doc_data = {}

    for rank, doc in enumerate(keyword_results):
        key = (doc["path"], doc.get("section_id"))
        rrf = 1.0 / (k + rank + 1)
        doc_scores[key] = doc_scores.get(key, 0) + config.HYBRID_KEYWORD_WEIGHT * rrf
        doc_data[key] = doc

    vec_weight = 1.0 - config.HYBRID_KEYWORD_WEIGHT
    for rank, doc in enumerate(vec_results):
        key = (doc["path"], doc.get("section_id"))
        rrf = 1.0 / (k + rank + 1)
        doc_scores[key] = doc_scores.get(key, 0) + vec_weight * rrf
        if key not in doc_data:
            doc_data[key] = doc

    # 점수순 정렬
    sorted_keys = sorted(doc_scores, key=lambda k: -doc_scores[k])

    results = []
    for key in sorted_keys[:top_k]:
        doc = doc_data[key].copy()
        doc["score"] = round(doc_scores[key], 6)
        results.append(doc)

    return results
