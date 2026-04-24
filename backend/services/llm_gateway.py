"""
LLM Gateway — 단일 진입점 (Plan-44 Phase 2b)

역할:
- 모든 LLM 호출이 이 모듈의 `llm_generate` / `llm_stream` 을 거치게 하여 Semaphore 로
  동시 호출 수를 제한
- **단발(chat/summary/classify/rewrite/translation-LLM)** 과 **스트림(qa_stream)** 을 분리된
  Semaphore 로 관리 — 긴 스트림이 짧은 단발 호출을 굶게 하는 문제 해소
- 대기열 한도 초과 시 `LLMQueueFullError` → 기존 main.py 핸들러가 HTTP 429 + Retry-After 변환
- `LLM_GATEWAY_ENABLED=False` 이면 Semaphore 우회, provider 직통 → Phase 2a 와 동일 동작
  (shadow 단계 / 롤백 플래그)

내부 구성:
- Provider 조회: `llm_provider.get_provider(model_override)` 재사용
- httpx: Phase 2a 의 `_get_shared_client()` 재사용 (연결 풀)
- 계측: `call_with_retry_async` 가 provider 내부에서 `record_llm_call` 수행 중 → Gateway 는
  Semaphore 만 관리 (중복 계측 방지)
"""
import asyncio
import logging
from typing import AsyncIterator, Optional

import config

logger = logging.getLogger(__name__)


# ── Semaphore 관리 ──────────────────────────────────────────────

_sem: Optional[asyncio.Semaphore] = None         # 단발 호출 공유
_stream_sem: Optional[asyncio.Semaphore] = None  # 스트림 전용
_queue_count: int = 0                            # 대기열 추정치
_config_cache: tuple = (None, None, None)        # (max_concurrent, max_queue, stream_slots)


def _ensure_sems() -> tuple:
    """설정 기반 Semaphore lazy init. 설정값이 바뀌면 재생성 (Settings 런타임 변경)."""
    global _sem, _stream_sem, _config_cache
    cur = (
        int(getattr(config, "LLM_GATEWAY_MAX_CONCURRENT", 8)),
        int(getattr(config, "LLM_GATEWAY_MAX_QUEUE", 32)),
        int(getattr(config, "LLM_GATEWAY_STREAM_SLOTS", 3)),
    )
    if _sem is None or _config_cache != cur:
        _sem = asyncio.Semaphore(cur[0])
        _stream_sem = asyncio.Semaphore(cur[2])
        _config_cache = cur
    return cur


def _enabled() -> bool:
    return bool(getattr(config, "LLM_GATEWAY_ENABLED", False))


def _is_stream_purpose(purpose: str) -> bool:
    return purpose == "qa_stream"


async def _acquire(purpose: str) -> asyncio.Semaphore:
    """Semaphore 획득. 대기열 초과 시 LLMQueueFullError."""
    from services.llm_retry import LLMQueueFullError
    global _queue_count

    _mc, max_queue, _ss = _ensure_sems()
    sem = _stream_sem if _is_stream_purpose(purpose) else _sem

    if _queue_count >= max_queue:
        raise LLMQueueFullError(retry_after=5.0)

    _queue_count += 1
    try:
        await sem.acquire()
    finally:
        _queue_count -= 1
    return sem


def _release(sem: asyncio.Semaphore) -> None:
    sem.release()


def get_status() -> dict:
    """관측용 — /api/metrics/ai-status 확장 시 참조."""
    mc, mq, ss = _ensure_sems()
    return {
        "enabled": _enabled(),
        "max_concurrent": mc,
        "max_queue": mq,
        "stream_slots": ss,
        "queue_count_est": _queue_count,
        "available_single": _sem._value if _sem is not None else None,
        "available_stream": _stream_sem._value if _stream_sem is not None else None,
    }


# ── 공개 API ────────────────────────────────────────────────────

async def llm_generate(
    prompt: str,
    *,
    system: Optional[str] = None,
    purpose: str = "chat",
    model_override: Optional[str] = None,
    **opts,
) -> str:
    """단발 LLM 호출 (Gateway 경유).

    purpose: chat | summary | classify | rewrite | translation (모두 단발 Sem 공유).
    Flag OFF 또는 Ollama 직접 테스트 시 Semaphore 우회.
    """
    from services.llm_provider import get_provider
    provider = get_provider(model_override=model_override)

    if not _enabled():
        return await provider.generate(prompt, system=system, **opts)

    sem = await _acquire(purpose)
    try:
        return await provider.generate(prompt, system=system, **opts)
    finally:
        _release(sem)


async def llm_stream(
    prompt: str,
    *,
    system: Optional[str] = None,
    purpose: str = "qa_stream",
    model_override: Optional[str] = None,
    **opts,
) -> AsyncIterator[str]:
    """스트리밍 LLM 호출 (Gateway 경유, 스트림 전용 슬롯)."""
    from services.llm_provider import get_provider
    provider = get_provider(model_override=model_override)

    if not _enabled():
        async for tok in provider.generate_stream(prompt, system=system, **opts):
            yield tok
        return

    sem = await _acquire(purpose)
    try:
        async for tok in provider.generate_stream(prompt, system=system, **opts):
            yield tok
    finally:
        _release(sem)


async def shutdown() -> None:
    """main.py lifespan shutdown 훅 — 현재는 no-op.

    httpx 공유 client 는 llm_provider.aclose_shared_client() 가 담당.
    asyncio Semaphore 는 프로세스 종료 시 자동 정리.
    """
    return None
