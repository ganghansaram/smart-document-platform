"""
Ollama 임베딩 클라이언트
"""
import requests
from typing import List

import config


def get_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Ollama /api/embed API를 사용하여 텍스트 임베딩 생성.
    texts: 임베딩할 텍스트 리스트
    returns: 임베딩 벡터 리스트 (각 벡터 = float 리스트)
    """
    if not texts:
        return []

    response = requests.post(
        f"{config.OLLAMA_URL}/api/embed",
        json={
            "model": config.EMBEDDING_MODEL,
            "input": texts
        },
        timeout=120
    )
    response.raise_for_status()
    data = response.json()
    return data["embeddings"]


def get_embedding(text: str) -> List[float]:
    """단일 텍스트 임베딩"""
    return get_embeddings([text])[0]
