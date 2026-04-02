"""
임베딩 클라이언트 — 로컬 SentenceTransformer 우선, Ollama 폴백

EMBEDDING_BACKEND 설정에 따라 추론 경로 선택:
  - "local": sentence-transformers로 인프로세스 추론 (기본, 권장)
  - "ollama": Ollama HTTP API 호출 (레거시 호환)
"""
import logging
import os
from typing import List

import requests

import config

logger = logging.getLogger(__name__)

os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

# ── 싱글턴 모델 캐시 ──
_model = None


def _load_model():
    """SentenceTransformer 모델 lazy-load (reranker.py 패턴 동일)"""
    global _model
    if _model is not None:
        return _model

    from sentence_transformers import SentenceTransformer

    model_path = config.EMBEDDING_LOCAL_MODEL
    device = "cuda" if _cuda_available() else "cpu"
    logger.info("임베딩 모델 로딩: %s (device=%s)", model_path, device)
    _model = SentenceTransformer(model_path, device=device)
    logger.info("임베딩 모델 로딩 완료 (dim=%d)", _model.get_sentence_embedding_dimension())
    return _model


def _cuda_available():
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


# ── 공개 API (시그니처 불변) ──

def get_embeddings(texts: List[str]) -> List[List[float]]:
    """
    텍스트 리스트를 임베딩 벡터 리스트로 변환.
    EMBEDDING_BACKEND 설정에 따라 로컬 또는 Ollama 경로 선택.
    """
    if not texts:
        return []

    backend = getattr(config, "EMBEDDING_BACKEND", "local")
    if backend == "local":
        return _encode_local(texts)
    return _encode_ollama(texts)


def get_embedding(text: str) -> List[float]:
    """단일 텍스트 임베딩"""
    return get_embeddings([text])[0]


# ── 로컬 추론 (sentence-transformers) ──

def _encode_local(texts: List[str]) -> List[List[float]]:
    model = _load_model()
    batch_size = getattr(config, "EMBEDDING_BATCH_SIZE", 64)
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return embeddings.tolist()


# ── Ollama HTTP 추론 (레거시) ──

def _encode_ollama(texts: List[str]) -> List[List[float]]:
    response = requests.post(
        f"{config.OLLAMA_URL}/api/embed",
        json={
            "model": config.EMBEDDING_MODEL,
            "input": texts,
        },
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    return data["embeddings"]
