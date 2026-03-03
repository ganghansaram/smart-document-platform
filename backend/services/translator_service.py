"""
Translator 서비스 — PMT 중심 문서 단위 번역 + 개인 작업공간
"""
import json
import hashlib
import os
import shutil
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional

import config

# ── 백그라운드 번역 작업 추적 ──
_active_tasks: dict[str, asyncio.Task] = {}  # doc_id → Task


def _ensure_data_dir():
    """data/translator 디렉토리 보장"""
    Path(config.TRANSLATOR_DATA_DIR).mkdir(parents=True, exist_ok=True)


def _user_dir(username: str) -> Path:
    return Path(config.TRANSLATOR_DATA_DIR) / username


def _doc_dir(username: str, doc_id: str) -> Path:
    return _user_dir(username) / doc_id


def _user_index_path(username: str) -> Path:
    return _user_dir(username) / "_index.json"


def _generate_id() -> str:
    now = datetime.now()
    rand = hashlib.md5(os.urandom(8)).hexdigest()[:6]
    return f"{now.strftime('%Y%m%d_%H%M%S')}_{rand}"


def _load_user_index(username: str) -> list[dict]:
    path = _user_index_path(username)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _save_user_index(username: str, index: list[dict]):
    udir = _user_dir(username)
    udir.mkdir(parents=True, exist_ok=True)
    with open(_user_index_path(username), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def _load_meta(username: str, doc_id: str) -> Optional[dict]:
    meta_path = _doc_dir(username, doc_id) / "meta.json"
    if not meta_path.exists():
        return None
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_meta(username: str, doc_id: str, meta: dict):
    doc_path = _doc_dir(username, doc_id)
    doc_path.mkdir(parents=True, exist_ok=True)
    with open(doc_path / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


# ══════════════════════════════════════
# 업로드
# ══════════════════════════════════════

def upload_pdf(pdf_bytes: bytes, filename: str, username: str) -> dict:
    """PDF 업로드 → 즉시 응답 (페이지 수 + meta)"""
    import fitz

    doc_id = _generate_id()
    doc_path = _doc_dir(username, doc_id)
    doc_path.mkdir(parents=True, exist_ok=True)

    # original.pdf 저장
    (doc_path / "original.pdf").write_bytes(pdf_bytes)

    # 페이지 수 추출
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = len(doc)
    doc.close()

    # meta.json 생성
    meta = {
        "id": doc_id,
        "filename": filename,
        "title": filename,
        "pages": pages,
        "uploaded_at": datetime.now().isoformat(),
        "status": "pending",
        "progress_stage": None,
        "model": None,
        "translated_at": None,
        "error": None,
    }
    _save_meta(username, doc_id, meta)

    # _index.json 갱신
    index = _load_user_index(username)
    index.append({
        "id": doc_id,
        "filename": filename,
        "pages": pages,
        "status": "pending",
        "uploaded_at": meta["uploaded_at"],
    })
    _save_user_index(username, index)

    return meta


# ══════════════════════════════════════
# 문서 CRUD
# ══════════════════════════════════════

def get_documents(username: str) -> list[dict]:
    """유저별 문서 목록 (인덱스에서 + 런타임 상태 보정 + meta 부가정보)"""
    index = _load_user_index(username)
    for entry in index:
        meta = _load_meta(username, entry["id"])
        # 런타임 작업 중이면 status 보정
        if entry["id"] in _active_tasks and not _active_tasks[entry["id"]].done():
            entry["status"] = "translating"
        elif meta:
            entry["status"] = meta["status"]
        # meta에서 부가정보 포함
        if meta:
            entry["model"] = meta.get("model")
            entry["translated_at"] = meta.get("translated_at")
            entry["translation_started_at"] = meta.get("translation_started_at")
    return index


def get_document(username: str, doc_id: str) -> Optional[dict]:
    """문서 메타 반환"""
    meta = _load_meta(username, doc_id)
    if not meta:
        return None
    # 런타임 상태 보정
    if doc_id in _active_tasks and not _active_tasks[doc_id].done():
        meta["status"] = "translating"
    return meta


def delete_document(username: str, doc_id: str) -> bool:
    """문서 디렉토리 삭제 + 인덱스 갱신"""
    doc_path = _doc_dir(username, doc_id)

    # 진행 중인 번역 취소
    task = _active_tasks.pop(doc_id, None)
    if task and not task.done():
        task.cancel()

    if doc_path.exists():
        shutil.rmtree(doc_path, ignore_errors=True)

    # 인덱스에서 제거 (디렉토리 삭제 실패해도 인덱스는 정리)
    index = _load_user_index(username)
    new_index = [e for e in index if e["id"] != doc_id]
    if len(new_index) == len(index):
        return False
    _save_user_index(username, new_index)
    return True


def cancel_translation(username: str, doc_id: str) -> bool:
    """번역 취소 → pending으로 복귀"""
    task = _active_tasks.pop(doc_id, None)
    if task and not task.done():
        task.cancel()

    meta = _load_meta(username, doc_id)
    if not meta:
        return False

    meta["status"] = "pending"
    meta["progress_stage"] = None
    meta["error"] = None
    _save_meta(username, doc_id, meta)
    _update_index_status(username, doc_id, "pending")
    return True


# ══════════════════════════════════════
# PDF 서빙
# ══════════════════════════════════════

def get_pdf_path(username: str, doc_id: str, kind: str = "original") -> Optional[Path]:
    """PDF 파일 경로 반환. kind: original | translated | dual"""
    fname = {
        "original": "original.pdf",
        "translated": "translated.pdf",
        "dual": "dual.pdf",
    }.get(kind, "original.pdf")
    path = _doc_dir(username, doc_id) / fname
    return path if path.exists() else None


# ══════════════════════════════════════
# PMT 번역
# ══════════════════════════════════════

def start_translation(username: str, doc_id: str, model: Optional[str] = None):
    """번역 시작 → asyncio.Task 생성, 즉시 반환"""
    meta = _load_meta(username, doc_id)
    if not meta:
        raise FileNotFoundError(f"문서 없음: {doc_id}")

    effective_model = model or config.TRANSLATOR_TRANSLATION_MODEL or config.OLLAMA_MODEL

    # 메타 업데이트
    meta["status"] = "translating"
    meta["model"] = effective_model
    meta["progress_stage"] = "번역 준비 중..."
    meta["translation_started_at"] = datetime.now().isoformat()
    meta["error"] = None
    _save_meta(username, doc_id, meta)

    # 인덱스도 갱신
    _update_index_status(username, doc_id, "translating")

    # 기존 작업이 있으면 취소
    old_task = _active_tasks.pop(doc_id, None)
    if old_task and not old_task.done():
        old_task.cancel()

    task = asyncio.create_task(_run_pmt(username, doc_id, effective_model))
    _active_tasks[doc_id] = task


async def _run_pmt(username: str, doc_id: str, model: str):
    """PMT CLI 비동기 실행"""
    import time

    src_path = _doc_dir(username, doc_id) / "original.pdf"
    if not src_path.exists():
        _mark_error(username, doc_id, "원본 PDF 파일 없음")
        return

    tmp_dir = _doc_dir(username, doc_id) / "_pmt_tmp"
    tmp_dir.mkdir(exist_ok=True)

    cmd = [
        "pdf2zh",
        "--ollama",
        "--ollama-model", model,
        "--ollama-host", config.OLLAMA_URL,
        "--lang-in", "English",
        "--lang-out", "Korean",
        "--primary-font-family", "sans-serif",
        "--output", str(tmp_dir),
        str(src_path),
    ]

    _update_progress(username, doc_id, "번역 중...")

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        timeout = getattr(config, "TRANSLATOR_PMT_TIMEOUT", 1200)
        deadline = time.monotonic() + timeout

        # stderr에서 진행 정보 파싱
        while True:
            if time.monotonic() > deadline:
                proc.kill()
                shutil.rmtree(tmp_dir, ignore_errors=True)
                _mark_error(username, doc_id, f"번역 시간 초과 ({timeout // 60}분)")
                return

            try:
                line = await asyncio.wait_for(proc.stderr.readline(), timeout=30)
            except asyncio.TimeoutError:
                continue

            if not line:
                break

            text = line.decode("utf-8", errors="replace").strip()
            if not text:
                continue

            # 진행 단계 추출
            stage = None
            if "translat" in text.lower():
                stage = "번역 중..."
            elif "download" in text.lower():
                stage = "리소스 다운로드 중..."
            elif "pars" in text.lower() or "extract" in text.lower():
                stage = "PDF 분석 중..."
            elif "render" in text.lower() or "writ" in text.lower():
                stage = "PDF 생성 중..."

            if stage:
                _update_progress(username, doc_id, stage)

        await proc.wait()

        if proc.returncode != 0:
            stdout_data = await proc.stdout.read()
            shutil.rmtree(tmp_dir, ignore_errors=True)
            log_text = stdout_data.decode("utf-8", errors="replace")[-500:] if stdout_data else ""
            _mark_error(username, doc_id, f"pdf2zh 실패 (exit {proc.returncode}): {log_text}")
            return

        # 결과 PDF 이동
        doc_path = _doc_dir(username, doc_id)
        mono_files = list(tmp_dir.glob("*.mono.pdf"))
        dual_files = list(tmp_dir.glob("*.dual.pdf"))

        if not mono_files:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            _mark_error(username, doc_id, "pdf2zh 완료되었으나 결과 PDF가 없습니다")
            return

        shutil.move(str(mono_files[0]), str(doc_path / "translated.pdf"))
        if dual_files:
            shutil.move(str(dual_files[0]), str(doc_path / "dual.pdf"))

        shutil.rmtree(tmp_dir, ignore_errors=True)

        # 성공 마킹
        meta = _load_meta(username, doc_id)
        if meta:
            meta["status"] = "done"
            meta["progress_stage"] = None
            meta["translated_at"] = datetime.now().isoformat()
            meta["error"] = None
            _save_meta(username, doc_id, meta)
            _update_index_status(username, doc_id, "done")

    except asyncio.CancelledError:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return
    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        _mark_error(username, doc_id, str(e))
    finally:
        _active_tasks.pop(doc_id, None)


def get_translation_status(username: str, doc_id: str) -> Optional[dict]:
    """번역 상태 반환"""
    meta = _load_meta(username, doc_id)
    if not meta:
        return None

    # 런타임 상태 보정
    if doc_id in _active_tasks and not _active_tasks[doc_id].done():
        meta["status"] = "translating"

    return {
        "status": meta["status"],
        "progress_stage": meta.get("progress_stage"),
        "model": meta.get("model"),
        "translated_at": meta.get("translated_at"),
        "error": meta.get("error"),
    }


def retranslate(username: str, doc_id: str, model: Optional[str] = None):
    """기존 번역 삭제 + 재번역"""
    doc_path = _doc_dir(username, doc_id)
    for fname in ("translated.pdf", "dual.pdf"):
        f = doc_path / fname
        if f.exists():
            f.unlink()

    start_translation(username, doc_id, model)


# ── 헬퍼 ──

def _update_progress(username: str, doc_id: str, stage: str):
    """meta.json progress_stage 업데이트"""
    meta = _load_meta(username, doc_id)
    if meta:
        meta["progress_stage"] = stage
        _save_meta(username, doc_id, meta)


def _mark_error(username: str, doc_id: str, error_msg: str):
    """에러 상태로 마킹"""
    meta = _load_meta(username, doc_id)
    if meta:
        meta["status"] = "error"
        meta["error"] = error_msg
        meta["progress_stage"] = None
        _save_meta(username, doc_id, meta)
    _update_index_status(username, doc_id, "error")
    _active_tasks.pop(doc_id, None)


def _update_index_status(username: str, doc_id: str, status: str):
    """인덱스의 특정 문서 상태 갱신"""
    index = _load_user_index(username)
    for entry in index:
        if entry["id"] == doc_id:
            entry["status"] = status
            break
    _save_user_index(username, index)


# ══════════════════════════════════════
# Ollama 모델 목록
# ══════════════════════════════════════

def get_ollama_models() -> dict:
    """Ollama 사용 가능 모델 목록"""
    import requests
    resp = requests.get(f"{config.OLLAMA_URL}/api/tags", timeout=5)
    resp.raise_for_status()
    return resp.json()
