"""
FastAPI 백엔드 진입점
"""
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import search, chat, document, upload, auth, analytics, settings, menu, translator, compare, help as help_api, export_docx
from services.auth import init_db
from services.analytics import init_db as init_analytics_db
from services.settings_service import apply_settings_on_startup
import config

logger = logging.getLogger(__name__)


# ── Lifespan (startup + shutdown) ──

@asynccontextmanager
async def lifespan(app):
    # ── startup ──
    _setup_logging()
    logger.info("서버 시작 (port=%s)", config.PORT)
    init_db()
    init_analytics_db()
    apply_settings_on_startup()  # settings.json → config 적용
    _reset_stuck_tasks()
    _cleanup_stale_preprocessed()
    # Plan-44 Phase 5: AI 지표 시간별 스냅샷 루프
    import asyncio as _asyncio
    from services.ai_metrics import snapshot_loop
    _snapshot_task = _asyncio.create_task(snapshot_loop(3600))
    app.state._snapshot_task = _snapshot_task
    yield
    # ── shutdown ──
    _snapshot_task.cancel()
    try:
        await _snapshot_task
    except (_asyncio.CancelledError, Exception):
        pass
    await _graceful_shutdown()
    # Plan-44 Phase 2b: LLM Gateway 정리 (Semaphore / 큐)
    try:
        from services.llm_gateway import shutdown as _gw_shutdown
        await _gw_shutdown()
    except Exception as e:
        logger.warning("LLM Gateway shutdown 실패 (무시): %s", e)
    # Plan-44 Phase 2a-1: 공유 httpx 클라이언트 정리
    try:
        from services.llm_provider import aclose_shared_client
        await aclose_shared_client()
    except Exception as e:
        logger.warning("LLM 공유 client aclose 실패 (무시): %s", e)
    logger.info("서버 종료 완료")


def _setup_logging():
    """로깅 체계 초기화 (Phase 3에서 logging_config.py로 대체 가능)"""
    try:
        from logging_config import setup_logging
        setup_logging()
    except ImportError:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def _reset_stuck_tasks():
    """서버 시작 시 이전 실행에서 고착된 translating/generating 상태를 pending으로 리셋"""
    from pathlib import Path
    import json
    data_dir = Path(config.TRANSLATOR_DATA_DIR)
    if not data_dir.exists():
        return
    reset_count = 0
    for meta_path in data_dir.glob("*/*/meta.json"):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            changed = False
            # page_status 고착 리셋
            for page_key, ps in (meta.get("page_status") or {}).items():
                if isinstance(ps, dict) and ps.get("status") == "translating":
                    ps["status"] = "pending"
                    changed = True
            # web_pages_status 고착 리셋
            for page_key, ws in (meta.get("web_pages_status") or {}).items():
                if isinstance(ws, dict) and ws.get("status") == "translating":
                    ws["status"] = "pending"
                    changed = True
            # summary_status 고착 리셋
            ss = meta.get("summary_status")
            if isinstance(ss, dict) and ss.get("status") == "generating":
                ss["status"] = "pending"
                changed = True
            if changed:
                tmp = meta_path.with_suffix(".tmp")
                tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
                tmp.replace(meta_path)
                reset_count += 1
        except Exception:
            pass
    if reset_count:
        logger.info("고착 태스크 %d건 리셋 (translating/generating → pending)", reset_count)


def _cleanup_stale_preprocessed():
    """서버 크래시로 남은 preprocessed_*.docx_1 임시파일 청소 (24h 이상)"""
    try:
        import sys
        from pathlib import Path
        converter_dir = Path(__file__).parent.parent / "tools" / "converter"
        if str(converter_dir) not in sys.path:
            sys.path.insert(0, str(converter_dir))
        from preprocess import cleanup_stale_temp_files
        removed = cleanup_stale_temp_files()
        if removed:
            logger.info("stale preprocessed 임시파일 %d건 정리", removed)
    except Exception as e:
        logger.warning("preprocessed temp cleanup 실패 (무시): %s", e)


async def _graceful_shutdown():
    """서버 종료 시 진행 중 태스크/서브프로세스 정리"""
    import asyncio
    try:
        from services.translator_service import (
            _active_tasks, _active_procs, _page_progress,
        )
        # 웹뷰/요약 태스크 dict도 가져오기 (존재하는 경우)
        try:
            from services.translator_service import _web_active_tasks, _summary_active_tasks
            extra_dicts = [_web_active_tasks, _summary_active_tasks]
        except ImportError:
            extra_dicts = []

        all_task_dicts = [_active_tasks] + extra_dicts
        total = sum(len(d) for d in all_task_dicts)
        if total:
            logger.info("진행 중 태스크 %d건 취소 중...", total)

        # 1. asyncio Task 취소
        for tasks_dict in all_task_dicts:
            for key, task in list(tasks_dict.items()):
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
            tasks_dict.clear()

        # 2. 서브프로세스 종료
        for key, proc in list(_active_procs.items()):
            try:
                proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        _active_procs.clear()

        # 3. 진행 캐시 정리
        _page_progress.clear()
    except Exception as e:
        logger.warning("Shutdown 정리 중 오류: %s", e)


# ── App 생성 ──

app = FastAPI(title="Smart Document Platform API", lifespan=lifespan)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(search.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(document.router, prefix="/api")
app.include_router(upload.router, prefix="/api")      # 문서 업로드/변환 API
app.include_router(auth.router, prefix="/api")         # 인증 API
app.include_router(analytics.router, prefix="/api")    # Analytics API
app.include_router(settings.router, prefix="/api")     # 관리자 설정 API
app.include_router(menu.router, prefix="/api")         # 메뉴 관리 API
app.include_router(translator.router, prefix="/api")    # Translator API
app.include_router(compare.router, prefix="/api")       # Compare API
app.include_router(help_api.router, prefix="/api")      # Help SSOT API (Plan-38)
app.include_router(export_docx.router, prefix="/api")   # 통일 양식 DOCX 내보내기 API (Plan-60)


# ── 전역 예외 핸들러 (5xx 계측) ──

from fastapi import Request as _Request, HTTPException as _HTTPException
from fastapi.responses import JSONResponse as _JSONResponse
from starlette.exceptions import HTTPException as _StarletteHTTPException

# 폭주 방지: 동일 path 에서 분당 최대 N건만 기록
_error_rate_limit: dict = {}
_ERROR_RATE_MAX_PER_MIN = 10


def _should_record_error(path: str) -> bool:
    import time as _t
    bucket = int(_t.time() // 60)
    key = (path, bucket)
    _error_rate_limit[key] = _error_rate_limit.get(key, 0) + 1
    # 오래된 버킷 제거 (현재 버킷만 유지)
    for k in list(_error_rate_limit.keys()):
        if k[1] < bucket:
            del _error_rate_limit[k]
    return _error_rate_limit[key] <= _ERROR_RATE_MAX_PER_MIN


def _path_to_subsystem(path: str) -> str:
    """엔드포인트 path → subsystem 매핑. 에러 이벤트 분석용."""
    if path.startswith("/api/translator"):
        return "translator"
    if path.startswith("/api/compare"):
        return "verify"
    if path.startswith("/api/search") or path.startswith("/api/chat") or path.startswith("/api/upload"):
        return "explorer"
    return "platform"


# Plan-44 Phase 3: Ollama 503(큐 포화) → HTTP 429 + Retry-After 변환
from services.llm_retry import LLMQueueFullError as _LLMQueueFullError


@app.exception_handler(_LLMQueueFullError)
async def _llm_queue_full_handler(request: _Request, exc: _LLMQueueFullError):
    """Ollama 큐 포화 시 클라이언트에 429 + Retry-After 로 응답.
    프론트엔드 RequestGuard 가 이 헤더를 읽고 자동 재시도(카운트다운 토스트)."""
    retry_after = max(1, int(round(exc.retry_after)))
    return _JSONResponse(
        status_code=429,
        headers={"Retry-After": str(retry_after)},
        content={"detail": str(exc), "retry_after": retry_after},
    )


@app.exception_handler(Exception)
async def _global_exception_handler(request: _Request, exc: Exception):
    """처리되지 않은 예외를 500 으로 응답하면서 analytics 에 기록 (rate-limit 적용).
    FastAPI/Starlette HTTPException 은 기본 처리기에 위임 (404/401/409 등 가로채지 않음)."""
    if isinstance(exc, (_HTTPException, _StarletteHTTPException)):
        raise exc
    if isinstance(exc, _LLMQueueFullError):
        # 전용 핸들러로 위임 (방어적 — FastAPI 디스패치가 먼저 처리해야 정상)
        return await _llm_queue_full_handler(request, exc)
    path = request.url.path
    logger.exception("Unhandled exception at %s: %s", path, exc)
    if _should_record_error(path):
        try:
            from services.analytics import record_event, get_client_ip
            from dependencies import get_optional_user
            u = get_optional_user(request)
            record_event("error", get_client_ip(request),
                         # 민감정보 유출 방지: 예외 타입만 기록, str(exc) 제외
                         {"endpoint": path, "status": 500,
                          "exception": type(exc).__name__},
                         username=u["username"] if u else None,
                         subsystem=_path_to_subsystem(path), status="error")
        except Exception:
            pass
    return _JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


# ── 헬스체크 ──

@app.get("/api/health")
async def health_check():
    import shutil
    import sqlite3
    checks = {}

    # DB 확인
    try:
        conn = sqlite3.connect(config.AUTH_DB_PATH)
        conn.execute("SELECT 1")
        conn.close()
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"

    # Ollama 확인 — Plan-44 Phase 2a-1: 공유 httpx 클라이언트 재사용
    try:
        import time as _t
        from services.llm_provider import _get_shared_client
        t0 = _t.perf_counter()
        shared = _get_shared_client()
        resp = await shared.get(f"{config.OLLAMA_URL}/api/tags", timeout=3.0)
        checks["ollama"] = "ok" if resp.status_code == 200 else "unreachable"
        checks["ollama_latency_ms"] = round((_t.perf_counter() - t0) * 1000, 1)
    except Exception:
        checks["ollama"] = "unreachable"
        checks["ollama_latency_ms"] = None
    try:
        from services.ai_metrics import get_ollama_503_last_hour
        checks["ollama_503_last_hour"] = get_ollama_503_last_hour()
    except Exception:
        checks["ollama_503_last_hour"] = 0

    # 디스크 확인
    try:
        usage = shutil.disk_usage(config.TRANSLATOR_DATA_DIR)
        free_gb = usage.free / (1024 ** 3)
        checks["disk_free_gb"] = round(free_gb, 1)
        checks["disk"] = "ok" if free_gb > 1.0 else "low"
    except Exception:
        checks["disk"] = "unknown"

    # FAISS 벡터 인덱스 최신성 (search-index.json mtime 과 비교)
    # search-index 는 업로드 시 즉시 갱신되고, vector-index 는 후속으로 rebuild 됨.
    # search-index 가 더 새로우면 vector-index 재생성 필요.
    # 2초 버퍼: FAT 파일시스템 mtime granularity 및 rebuild 직후 타임스탬프 차이 흡수
    from pathlib import Path
    search_idx = Path(config.SEARCH_INDEX_PATH)
    vector_faiss = Path(str(config.VECTOR_INDEX_PATH) + ".faiss")
    try:
        vec_exists = vector_faiss.exists()
        src_exists = search_idx.exists()
        if not vec_exists and not src_exists:
            checks["faiss"] = "ok"  # 빈 시스템 (초기 설치)
        elif not vec_exists:
            checks["faiss"] = "missing"  # 콘텐츠는 있는데 벡터 없음
        elif not src_exists:
            checks["faiss"] = "ok"  # 콘텐츠 삭제된 상태
        elif search_idx.stat().st_mtime > vector_faiss.stat().st_mtime + 2:
            checks["faiss"] = "stale"
        else:
            checks["faiss"] = "ok"
    except Exception:
        checks["faiss"] = "unknown"

    # overall 판정에서 수치 필드(disk_free_gb, ollama_latency_ms, ollama_503_last_hour) 제외
    _non_status_keys = ("disk_free_gb", "ollama_latency_ms", "ollama_503_last_hour")
    overall = "ok" if all(
        v == "ok" for k, v in checks.items()
        if k not in _non_status_keys
    ) else "degraded"
    return {"status": overall, "checks": checks}


# ── Plan-44 Phase 5: AI 동시성 상태 지표 (관리자 대시보드 연동) ──

from fastapi import Depends as _Depends
from dependencies import require_admin as _require_admin


@app.get("/api/metrics/ai-status")
async def ai_status(_user: dict = _Depends(_require_admin)):
    """대시보드 AI 동시성 상태 패널용 — 4 지표 + L2/L3 트리거 판정.
    관리자 전용 (운영 지표 비공개)."""
    from services.ai_metrics import get_ai_status
    return get_ai_status()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.HOST, port=config.PORT)
