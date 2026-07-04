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


class EmbeddingBackendError(RuntimeError):
    """임베딩 백엔드 호출 실패 — 원인(연결/타임아웃/모델/HTTP)을 구분해 담는다.

    조용한 실패(raw traceback·모호한 에러) 방지용. 서브프로세스(build-vector-index.py)
    에서 발생 시 stderr 마지막 줄에 `EmbeddingBackendError: <메시지>` 형태로 남아
    재인덱싱 스트림이 사람이 읽을 원인으로 되살릴 수 있다 (Plan-68 C2).
    """

    def __init__(self, reason: str, message: str):
        self.reason = reason  # connection | timeout | model | http
        super().__init__(message)

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
    url = f"{config.OLLAMA_URL}/api/embed"
    try:
        response = requests.post(
            url,
            json={
                "model": config.EMBEDDING_MODEL,
                "input": texts,
            },
            timeout=120,
        )
        response.raise_for_status()
    except requests.exceptions.ReadTimeout as e:
        raise EmbeddingBackendError(
            "timeout",
            f"Ollama 임베딩 응답 타임아웃(120초): {config.OLLAMA_URL}. "
            f"모델 로드 지연 또는 서버 과부하 가능.",
        ) from e
    except requests.exceptions.ConnectionError as e:
        # ConnectTimeout 포함 — 서버 미기동/주소 오류/네트워크 차단
        raise EmbeddingBackendError(
            "connection",
            f"Ollama 연결 실패: {config.OLLAMA_URL}. 서버 미기동 또는 주소·네트워크 오류.",
        ) from e
    except requests.exceptions.Timeout as e:
        raise EmbeddingBackendError(
            "timeout",
            f"Ollama 연결 타임아웃: {config.OLLAMA_URL}. 서버 응답 없음.",
        ) from e
    except requests.exceptions.HTTPError as e:
        sc = e.response.status_code if e.response is not None else None
        if sc == 404:
            raise EmbeddingBackendError(
                "model",
                f"Ollama 모델 미로드: '{config.EMBEDDING_MODEL}'. "
                f"대상 서버에 `ollama pull {config.EMBEDDING_MODEL}` 필요.",
            ) from e
        raise EmbeddingBackendError("http", f"Ollama HTTP 오류({sc}): {url}.") from e

    data = response.json()
    return data["embeddings"]


# ── 관측 (Plan-68 C1) — 순수 조회, 부작용 없음 ──

def get_backend_info() -> dict:
    """현재 해석된 용도별 백엔드·모델·URL. 관리자 대시보드 노출용."""
    return {
        "index": _resolve_backend("index"),
        "runtime": _resolve_backend("runtime"),
        "model": config.EMBEDDING_MODEL,
        "ollama_url": config.OLLAMA_URL,
    }


def get_ollama_ps() -> dict:
    """Ollama `/api/ps` 조회 — 임베딩 모델 로드 여부·GPU(VRAM) 사용 여부.

    ⚠️ index=ollama 일 때 GPU 사용은 이 경로로만 확인 가능
    (`_cuda_available()` 는 컨테이너 내 로컬 torch 만 반영 → 오지정 금지, Plan-68 C1).
    관측용이라 실패는 예외 대신 reachable=False 로 반환.
    """
    try:
        resp = requests.get(f"{config.OLLAMA_URL}/api/ps", timeout=3)
        resp.raise_for_status()
        models = resp.json().get("models", []) or []
    except Exception:
        return {"reachable": False, "embed_loaded": False, "on_gpu": None}

    model = config.EMBEDDING_MODEL
    entry = next(
        (m for m in models if model in (m.get("name", "") or "") or model in (m.get("model", "") or "")),
        None,
    )
    if not entry:
        return {"reachable": True, "embed_loaded": False, "on_gpu": None}

    size = entry.get("size", 0) or 0
    vram = entry.get("size_vram", 0) or 0
    return {
        "reachable": True,
        "embed_loaded": True,
        "on_gpu": vram > 0,
        "vram_ratio": round(vram / size, 2) if size else None,
    }
