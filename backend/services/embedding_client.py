"""
임베딩 클라이언트 — 용도별 백엔드 분리 (Plan-40)

설계:
  - purpose="runtime" (기본): 실시간 경로 — 검색 쿼리·Compare 유사도
  - purpose="index": 인덱싱 경로 — Explorer 벡터 인덱스 재생성·업로드 증분

백엔드 선택 해석 순서:
  1. 용도별 환경변수: EMBEDDING_BACKEND_INDEX / EMBEDDING_BACKEND_RUNTIME
  2. 레거시 전역: EMBEDDING_BACKEND (deprecated)
  3. 코드 기본값: index=ollama, runtime=local

백엔드:
  - "local": sentence-transformers 인프로세스 추론 (컨테이너 내부, CPU 폴백 가능)
  - "ollama": Ollama HTTP API (GPU 서버 위임, 청크 분할 지원)
"""
import logging
import os
from typing import List, Literal

import requests

import config

logger = logging.getLogger(__name__)

os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

_DEFAULT_BACKEND_BY_PURPOSE = {
    "index": "ollama",
    "runtime": "local",
}

# ── 싱글턴 모델 캐시 ──
_model = None


def _load_model():
    """SentenceTransformer 모델 lazy-load"""
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


def _resolve_backend(purpose: str) -> str:
    """용도별 백엔드 선택 — 해석 순서는 모듈 docstring 참조"""
    per_purpose_attr = f"EMBEDDING_BACKEND_{purpose.upper()}"
    per_purpose = getattr(config, per_purpose_attr, "") or ""
    if per_purpose:
        return per_purpose

    legacy = getattr(config, "EMBEDDING_BACKEND", "") or ""
    if legacy:
        return legacy

    return _DEFAULT_BACKEND_BY_PURPOSE.get(purpose, "local")


# ── 공개 API ──

def get_embeddings(
    texts: List[str],
    *,
    purpose: Literal["index", "runtime"] = "runtime",
) -> List[List[float]]:
    """
    텍스트 리스트를 임베딩 벡터 리스트로 변환.

    Args:
        texts: 임베딩 대상 문자열 목록
        purpose: "runtime"(실시간, 기본) / "index"(인덱싱 배치)
    """
    if not texts:
        return []

    backend = _resolve_backend(purpose)
    if backend == "local":
        return _encode_local(texts)
    return _encode_ollama(texts)


def get_embedding(text: str, *, purpose: Literal["index", "runtime"] = "runtime") -> List[float]:
    """단일 텍스트 임베딩"""
    return get_embeddings([text], purpose=purpose)[0]


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


# ── Ollama HTTP 추론 ──

def _encode_ollama(texts: List[str]) -> List[List[float]]:
    """
    Ollama `/api/embed` 호출. 서버 메모리·배치 한도를 고려해 청크 분할 지원.
    EMBEDDING_OLLAMA_BATCH=0 이면 단일 호출, 그 외 값으로 분할.
    """
    chunk = int(getattr(config, "EMBEDDING_OLLAMA_BATCH", 64) or 0)
    if chunk <= 0 or len(texts) <= chunk:
        return _ollama_embed_call(texts)

    all_embeddings: List[List[float]] = []
    for i in range(0, len(texts), chunk):
        part = texts[i:i + chunk]
        all_embeddings.extend(_ollama_embed_call(part))
    return all_embeddings


def _ollama_embed_call(texts: List[str]) -> List[List[float]]:
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
