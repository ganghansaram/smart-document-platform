"""
AI 지표 수집·판정 (Plan-44 Phase 5)

역할:
- 1시간 롤링 버퍼에 LLM 호출 이벤트 기록 (purpose, duration_ms, status)
- 4 지표 계산: p95 지연, Ollama 503/hour, 피크 동접, 활성 스트림
- L2/L3 트리거 상태(normal/warning/fired) 판정 (계획서 §우선순위 레이어)
- 1시간 주기 스냅샷을 Plan-41 `analytics_events` 테이블에 저장 (신규 테이블 없음)

호출 지점:
- llm_retry.call_with_retry_* — 호출 완료 시 record_llm_call
- llm_provider.generate_stream — 스트림 시작/종료 시 mark_stream_start/end
- main.py lifespan — 스냅샷 루프 시작
- api/metrics.py — 대시보드용 /api/metrics/ai-status
- main.py /api/health — ollama_503_last_hour 필드

임계값(L2):
  p95_latency_ms > 8000 / ollama_503_per_hour > 5 / peak_concurrent_users_1h > 7
임계값(L3):
  p95_latency_ms > 20000 / ollama_503_per_hour > 10 / peak_concurrent_users_1h > 15
"""
import logging
import threading
import time
from collections import deque
from typing import Optional

logger = logging.getLogger(__name__)

_WINDOW_SEC = 3600  # 1시간

# (timestamp, purpose, duration_ms, status) — status: "ok"/"503"/"error"/"timeout"/"cancelled"
_events: deque = deque()
_lock = threading.Lock()

_active_streams: int = 0
_active_streams_lock = threading.Lock()

# 락 획득 순서 규칙 (deadlock 방지): _lock → _active_streams_lock
# get_indicators() 가 _lock 하에서 이벤트 스냅샷 후 lock 해제,
# 이후 _active_streams_lock 을 별도 획득하므로 순서 이슈 없음.
# 향후 두 락을 동시에 들어야 하는 코드 추가 시 반드시 이 순서 유지.


# ── 기록 API ────────────────────────────────────────────────────

def record_llm_call(purpose: str, duration_ms: float, status: str) -> None:
    """LLM 호출 완료 이벤트 기록. 실패는 무시 (본 경로에 영향 없어야)."""
    try:
        now = time.time()
        with _lock:
            _events.append((now, purpose, float(duration_ms), status))
            _evict_old_locked(now)
    except Exception as e:
        logger.debug("record_llm_call 실패 (무시): %s", e)


def mark_stream_start() -> None:
    global _active_streams
    with _active_streams_lock:
        _active_streams += 1


def mark_stream_end() -> None:
    global _active_streams
    with _active_streams_lock:
        _active_streams = max(0, _active_streams - 1)


def _evict_old_locked(now: float) -> None:
    cutoff = now - _WINDOW_SEC
    while _events and _events[0][0] < cutoff:
        _events.popleft()


# ── 조회 API ────────────────────────────────────────────────────

def get_indicators() -> dict:
    """현재 4 지표 스냅샷."""
    now = time.time()
    with _lock:
        _evict_old_locked(now)
        latencies_ok = sorted(e[2] for e in _events if e[3] == "ok")
        count_503 = sum(1 for e in _events if e[3] == "503")

    p95 = latencies_ok[int(len(latencies_ok) * 0.95)] if latencies_ok else 0.0
    # 95th percentile: 표본 적을 때 마지막 원소로 fallback
    if latencies_ok and p95 == 0.0:
        p95 = latencies_ok[-1]

    with _active_streams_lock:
        active = _active_streams

    return {
        "p95_latency_ms": round(p95, 1),
        "ollama_503_per_hour": count_503,
        "peak_concurrent_users_1h": _peak_users_1h(),
        "active_streams": active,
    }


def get_ollama_503_last_hour() -> int:
    """/api/health 전용 간편 조회."""
    now = time.time()
    with _lock:
        _evict_old_locked(now)
        return sum(1 for e in _events if e[3] == "503")


def _peak_users_1h() -> int:
    """최근 1시간 피크 동접. Plan-41 analytics 의 현재 활성 사용자 수로 근사."""
    try:
        from services.analytics import get_active_user_count
        return get_active_user_count()
    except Exception:
        return 0


# ── 트리거 판정 ─────────────────────────────────────────────────

L2_THRESHOLDS = {
    "p95_latency_ms": 8000,
    "ollama_503_per_hour": 5,
    "peak_concurrent_users_1h": 7,
}
L3_THRESHOLDS = {
    "p95_latency_ms": 20000,
    "ollama_503_per_hour": 10,
    "peak_concurrent_users_1h": 15,
}
WARNING_RATIO = 0.7


def _evaluate(indicators: dict, thresholds: dict) -> tuple[str, list[str]]:
    """임계값 대비 상태 판정. 반환: (normal|warning|fired, 해당 지표 목록)."""
    fired: list[str] = []
    warning: list[str] = []
    for key, limit in thresholds.items():
        value = indicators.get(key, 0)
        if value >= limit:
            fired.append(key)
        elif value >= limit * WARNING_RATIO:
            warning.append(key)
    if fired:
        return "fired", fired
    if warning:
        return "warning", warning
    return "normal", []


def get_ai_status() -> dict:
    """대시보드용 — 지표 + 트리거 상태 + 타임스탬프."""
    indicators = get_indicators()
    l2_status, l2_fired = _evaluate(indicators, L2_THRESHOLDS)
    l3_status, l3_fired = _evaluate(indicators, L3_THRESHOLDS)
    return {
        "indicators": indicators,
        "thresholds": {"l2": L2_THRESHOLDS, "l3": L3_THRESHOLDS},
        "triggers": {
            "l2_status": l2_status,
            "l2_fired_indicators": l2_fired,
            "l3_status": l3_status,
            "l3_fired_indicators": l3_fired,
        },
        "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


# ── 스냅샷 (Plan-41 analytics_events 재사용) ─────────────────────

def save_hourly_snapshot() -> None:
    """현재 지표를 analytics_events 테이블에 ai_indicator_snapshot 이벤트로 저장.
    신규 테이블 없이 Plan-41 인프라 재사용.
    """
    try:
        from services.analytics import record_event
        status_data = get_ai_status()
        metadata = {
            **status_data["indicators"],
            "l2_status": status_data["triggers"]["l2_status"],
            "l3_status": status_data["triggers"]["l3_status"],
        }
        record_event(
            "ai_indicator_snapshot",
            "system",
            metadata,
            subsystem="platform",
            status=status_data["triggers"]["l2_status"],
        )
        logger.debug("AI indicator snapshot 기록: %s", metadata)
    except Exception as e:
        logger.warning("AI indicator snapshot 저장 실패 (무시): %s", e)


async def snapshot_loop(interval_sec: int = 3600) -> None:
    """main.py lifespan 에서 asyncio.create_task 로 기동되는 주기적 스냅샷 루프."""
    import asyncio
    while True:
        try:
            await asyncio.sleep(interval_sec)
            save_hourly_snapshot()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning("snapshot_loop 반복 실패: %s", e)
