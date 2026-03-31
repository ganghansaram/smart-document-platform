"""
FastAPI 백엔드 진입점
"""
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import search, chat, document, upload, auth, analytics, settings, menu, translator, compare
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
    yield
    # ── shutdown ──
    await _graceful_shutdown()
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


# ── 헬스체크 ──

@app.get("/api/health")
def health_check():
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

    # Ollama 확인
    try:
        import requests
        resp = requests.get(f"{config.OLLAMA_URL}/api/tags", timeout=3)
        checks["ollama"] = "ok" if resp.status_code == 200 else "unreachable"
    except Exception:
        checks["ollama"] = "unreachable"

    # 디스크 확인
    try:
        usage = shutil.disk_usage(config.TRANSLATOR_DATA_DIR)
        free_gb = usage.free / (1024 ** 3)
        checks["disk_free_gb"] = round(free_gb, 1)
        checks["disk"] = "ok" if free_gb > 1.0 else "low"
    except Exception:
        checks["disk"] = "unknown"

    overall = "ok" if all(
        v == "ok" for k, v in checks.items() if k != "disk_free_gb"
    ) else "degraded"
    return {"status": overall, "checks": checks}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.HOST, port=config.PORT)
