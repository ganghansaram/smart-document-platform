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
_active_single: int = 0                          # 단발 활성 요청 수 (Semaphore 내부 속성 의존 회피)
_active_stream: int = 0                          # 스트림 활성 요청 수
_config_cache: tuple = (None, None, None)        # (max_concurrent, max_queue, stream_slots)


def _ensure_sems() -> tuple:
    """설정 기반 Semaphore lazy init.

    재생성 정책: 최초 1회만 생성. 설정값 변경은 서버 재시작 시에만 반영 (lifespan 에서
    새 프로세스로 시작). 런타임 재생성을 피하는 이유는 이미 대기 중인 `await sem.acquire()`
    코루틴이 구 sem 에 갇혀 교착되는 위험 때문 (code-reviewer Critical 반영).
    `LLM_GATEWAY_ENABLED` 플래그는 Semaphore 재생성 없이 진입 분기로 처리되므로 즉시 반영됨.
    """
    global _sem, _stream_sem, _config_cache
    cur = (
        int(getattr(config, "LLM_GATEWAY_MAX_CONCURRENT", 8)),
        int(getattr(config, "LLM_GATEWAY_MAX_QUEUE", 32)),
        int(getattr(config, "LLM_GATEWAY_STREAM_SLOTS", 3)),
    )
    if _sem is None:
        _sem = asyncio.Semaphore(cur[0])
        _stream_sem = asyncio.Semaphore(cur[2])
        _config_cache = cur
    elif _config_cache != cur:
        logger.info(
            "LLM Gateway 설정 변경 감지 (max_concurrent=%s→%s, max_queue=%s→%s, stream_slots=%s→%s). "
            "Semaphore 재생성은 대기 요청 교착 위험으로 다음 서버 재시작 시 반영됩니다.",
            _config_cache[0], cur[0], _config_cache[1], cur[1], _config_cache[2], cur[2],
        )
    # 현재 활성 Semaphore 가 반영한 값 반환 (최신 config 아님 — 재시작 전까지 불일치 가능)
    return _config_cache


def _enabled() -> bool:
    return bool(getattr(config, "LLM_GATEWAY_ENABLED", False))


def _is_stream_purpose(purpose: str) -> bool:
    return purpose == "qa_stream"


async def _acquire(purpose: str) -> asyncio.Semaphore:
    """Semaphore 획득. 대기열 초과 시 LLMQueueFullError."""
    from services.llm_retry import LLMQueueFullError
    global _queue_count, _active_single, _active_stream

    _mc, max_queue, _ss = _ensure_sems()
    is_stream = _is_stream_purpose(purpose)
    sem = _stream_sem if is_stream else _sem

    if _queue_count >= max_queue:
        raise LLMQueueFullError(retry_after=5.0)

    _queue_count += 1
    try:
        await sem.acquire()
    finally:
        _queue_count -= 1
    if is_stream:
        _active_stream += 1
    else:
        _active_single += 1
    return sem


def _release(sem: asyncio.Semaphore) -> None:
    global _active_single, _active_stream
    sem.release()
    if sem is _stream_sem:
        _active_stream = max(0, _active_stream - 1)
    else:
        _active_single = max(0, _active_single - 1)


def get_status() -> dict:
    """관측용 — /api/metrics/ai-status 확장 시 참조. 내부 속성 의존 없이 자체 카운터 사용.

    max_* 는 현재 활성 Semaphore 반영값. config 값이 변경됐지만 아직 재시작 안 된 경우
    `pending_restart=True` 로 알림.
    """
    active_mc, active_mq, active_ss = _ensure_sems()
    cfg_mc = int(getattr(config, "LLM_GATEWAY_MAX_CONCURRENT", 8))
    cfg_mq = int(getattr(config, "LLM_GATEWAY_MAX_QUEUE", 32))
    cfg_ss = int(getattr(config, "LLM_GATEWAY_STREAM_SLOTS", 3))
    pending = (cfg_mc, cfg_mq, cfg_ss) != (active_mc, active_mq, active_ss)
    return {
        "enabled": _enabled(),
        "max_concurrent": active_mc,
        "max_queue": active_mq,
        "stream_slots": active_ss,
        "queue_count_est": _queue_count,
        "active_single": _active_single,
        "active_stream": _active_stream,
        "pending_restart": pending,
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


async def acquire_slot(purpose: str = "chat") -> Optional[asyncio.Semaphore]:
    """외부 호출자용 — provider.generate 우회가 필요한 경우(Ollama structured output 등).

    반환값: Flag OFF 시 None, ON 시 Semaphore. 반드시 release_slot(sem) 호출.
    """
    if not _enabled():
        return None
    return await _acquire(purpose)


def release_slot(sem: Optional[asyncio.Semaphore]) -> None:
    if sem is not None:
        _release(sem)


async def shutdown() -> None:
    """main.py lifespan shutdown 훅 — 현재는 no-op.

    httpx 공유 client 는 llm_provider.aclose_shared_client() 가 담당.
    asyncio Semaphore 는 프로세스 종료 시 자동 정리.
    """
    return None
