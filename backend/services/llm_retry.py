"""
LLM 호출 재시도·에러 변환 헬퍼 (Plan-44 Phase 3)

역할:
- Ollama 503(큐 포화) → 지수 백오프 재시도 → 지속되면 LLMQueueFullError 로 변환
- 일시적 ConnectError / ReadTimeout → 재시도
- 기타 HTTP 에러는 그대로 전파

FastAPI 전역 예외 핸들러가 LLMQueueFullError 를 HTTP 429 + Retry-After 로 변환.
프론트엔드 RequestGuard(Phase 4) 가 429 를 받아 자동 재시도 + 토스트 카운트다운.
"""
import asyncio
import logging
import random
import time
from typing import Awaitable, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BASE_DELAY = 0.5   # 초, attempt 0 기본 지연 기반
DEFAULT_MAX_DELAY = 8.0
DEFAULT_RETRY_AFTER = 5.0  # Retry-After 헤더 부재 시 fallback


class LLMQueueFullError(Exception):
    """Ollama / LLM 백엔드 큐 포화 (HTTP 503).

    main.py 전역 예외 핸들러가 HTTP 429 + Retry-After 헤더로 변환한다.
    """

    def __init__(self, retry_after: float = DEFAULT_RETRY_AFTER,
                 message: str = "AI 서버가 현재 처리 중인 요청이 많습니다."):
        super().__init__(message)
        self.retry_after = retry_after


def _backoff_delay(attempt: int, base: float = DEFAULT_BASE_DELAY,
                   cap: float = DEFAULT_MAX_DELAY) -> float:
    return min(base * (2 ** attempt) + random.uniform(0, base), cap)


def _parse_retry_after(headers, default: float = DEFAULT_RETRY_AFTER) -> float:
    if not headers:
        return default
    ra = headers.get("Retry-After") if hasattr(headers, "get") else None
    if ra is None:
        return default
    try:
        return float(ra)
    except (TypeError, ValueError):
        return default


# ── 비동기 (httpx) ─────────────────────────────────────────────

async def call_with_retry_async(
    func: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    purpose: str = "llm",
) -> T:
    """비동기 httpx 호출 재시도 래퍼."""
    import httpx
    for attempt in range(max_attempts):
        try:
            return await func()
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 503:
                if attempt < max_attempts - 1:
                    delay = _backoff_delay(attempt)
                    logger.info("LLM(%s) 503 queue-full, %.1fs retry (%d/%d)",
                                purpose, delay, attempt + 1, max_attempts)
                    await asyncio.sleep(delay)
                    continue
                raise LLMQueueFullError(
                    retry_after=_parse_retry_after(e.response.headers)
                ) from e
            raise
        except (httpx.ConnectError, httpx.ReadTimeout) as e:
            if attempt < max_attempts - 1:
                delay = _backoff_delay(attempt)
                logger.info("LLM(%s) %s, %.1fs retry (%d/%d)",
                            purpose, type(e).__name__, delay,
                            attempt + 1, max_attempts)
                await asyncio.sleep(delay)
                continue
            raise
    raise RuntimeError(f"LLM retry exhausted (unreachable) for {purpose}")


# ── 동기 (requests) ────────────────────────────────────────────

def call_with_retry_sync(
    func: Callable[[], T],
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    purpose: str = "llm",
) -> T:
    """동기 requests 호출 재시도 래퍼."""
    import requests
    for attempt in range(max_attempts):
        try:
            return func()
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            if status == 503:
                if attempt < max_attempts - 1:
                    delay = _backoff_delay(attempt)
                    logger.info("LLM(%s) 503 queue-full, %.1fs retry (%d/%d)",
                                purpose, delay, attempt + 1, max_attempts)
                    time.sleep(delay)
                    continue
                raise LLMQueueFullError(
                    retry_after=_parse_retry_after(
                        e.response.headers if e.response is not None else None)
                ) from e
            raise
        except (requests.ConnectionError, requests.Timeout) as e:
            if attempt < max_attempts - 1:
                delay = _backoff_delay(attempt)
                logger.info("LLM(%s) %s, %.1fs retry (%d/%d)",
                            purpose, type(e).__name__, delay,
                            attempt + 1, max_attempts)
                time.sleep(delay)
                continue
            raise
    raise RuntimeError(f"LLM retry exhausted (unreachable) for {purpose}")
