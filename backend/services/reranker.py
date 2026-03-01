"""
Cross-encoder 리랭커 서비스
bge-reranker-v2-m3를 사용하여 검색 결과를 재정렬
"""
import logging
from typing import List

import config

logger = logging.getLogger(__name__)

# 모듈 레벨 캐시 (모델 로딩은 한 번만)
_model = None


def _load_model():
    """CrossEncoder 모델 lazy-load"""
    global _model
    if _model is not None:
        return _model

    from sentence_transformers import CrossEncoder

    logger.info("리랭커 모델 로딩: %s", config.RERANKER_MODEL)
    _model = CrossEncoder(config.RERANKER_MODEL, max_length=512)
    logger.info("리랭커 모델 로딩 완료")
    return _model


def rerank(query: str, results: List[dict], top_k: int = 5) -> List[dict]:
    """
    검색 결과를 cross-encoder로 재정렬.
    results: [{title, content, path, section_id, score}, ...]
    returns: 재정렬된 상위 top_k개 결과
    """
    if not results:
        return results

    model = _load_model()

    # (query, document_text) 쌍 구성
    pairs = []
    for r in results:
        doc_text = f"{r['title']}\n{r.get('content', '')}"
        pairs.append([query, doc_text])

    # cross-encoder 스코어링
    scores = model.predict(pairs)

    # 점수 부여 후 재정렬
    for i, r in enumerate(results):
        r["rerank_score"] = float(scores[i])

    results.sort(key=lambda x: -x["rerank_score"])

    # 상위 top_k 반환, score를 rerank_score로 교체
    reranked = []
    for r in results[:top_k]:
        out = r.copy()
        out["score"] = round(out.pop("rerank_score"), 6)
        reranked.append(out)

    return reranked
