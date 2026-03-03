"""
Translator 서비스 — 페이지별 온디맨드 번역 + 개인 작업공간
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
# 키: "{doc_id}:{page_num}"
_active_tasks: dict[str, asyncio.Task] = {}
_active_procs: dict[str, asyncio.subprocess.Process] = {}


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


def _task_key(doc_id: str, page_num: int) -> str:
    return f"{doc_id}:{page_num}"


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
        "status": "uploaded",
        "page_status": {},
        "has_legacy_translation": False,
    }
    _save_meta(username, doc_id, meta)

    # _index.json 갱신
    index = _load_user_index(username)
    index.append({
        "id": doc_id,
        "filename": filename,
        "pages": pages,
        "status": "uploaded",
        "uploaded_at": meta["uploaded_at"],
    })
    _save_user_index(username, index)

    return meta


# ══════════════════════════════════════
# 문서 CRUD
# ══════════════════════════════════════

def get_documents(username: str) -> list[dict]:
    """유저별 문서 목록 (인덱스 + 메타 보강)"""
    index = _load_user_index(username)
    for entry in index:
        meta = _load_meta(username, entry["id"])
        if meta:
            entry["status"] = meta.get("status", "uploaded")
            entry["has_legacy_translation"] = meta.get("has_legacy_translation", False)
            # 페이지별 번역 통계
            page_status = meta.get("page_status", {})
            done_count = sum(1 for ps in page_status.values() if ps.get("status") == "done")
            total = meta.get("pages", 0)
            entry["translated_pages"] = done_count
            entry["total_pages"] = total
            # 레거시 통번역 존재 여부
            translated_path = _doc_dir(username, entry["id"]) / "translated.pdf"
            if translated_path.exists():
                entry["has_legacy_translation"] = True
    return index


def get_document(username: str, doc_id: str) -> Optional[dict]:
    """문서 메타 반환"""
    meta = _load_meta(username, doc_id)
    if not meta:
        return None
    # 레거시 통번역 존재 여부 갱신
    translated_path = _doc_dir(username, doc_id) / "translated.pdf"
    meta["has_legacy_translation"] = translated_path.exists()
    return meta


def delete_document(username: str, doc_id: str) -> bool:
    """문서 디렉토리 삭제 + 인덱스 갱신"""
    doc_path = _doc_dir(username, doc_id)

    # 진행 중인 페이지별 번역 취소
    keys_to_cancel = [k for k in _active_tasks if k.startswith(doc_id + ":")]
    for key in keys_to_cancel:
        proc = _active_procs.pop(key, None)
        if proc:
            try:
                proc.kill()
            except Exception:
                pass
        task = _active_tasks.pop(key, None)
        if task and not task.done():
            task.cancel()

    if doc_path.exists():
        shutil.rmtree(doc_path, ignore_errors=True)

    # 인덱스에서 제거
    index = _load_user_index(username)
    new_index = [e for e in index if e["id"] != doc_id]
    if len(new_index) == len(index):
        return False
    _save_user_index(username, new_index)
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


def get_page_pdf_path(username: str, doc_id: str, page_num: int) -> Optional[Path]:
    """페이지별 번역 PDF 경로"""
    path = _doc_dir(username, doc_id) / "pages" / str(page_num) / "translated.pdf"
    return path if path.exists() else None


# ══════════════════════════════════════
# 페이지별 번역
# ══════════════════════════════════════

def start_page_translation(username: str, doc_id: str, page_num: int, model: Optional[str] = None):
    """단일 페이지 번역 시작 → asyncio.Task 생성, 즉시 반환"""
    meta = _load_meta(username, doc_id)
    if not meta:
        raise FileNotFoundError(f"문서 없음: {doc_id}")

    if page_num < 1 or page_num > meta.get("pages", 0):
        raise ValueError(f"유효하지 않은 페이지 번호: {page_num}")

    # 동시성 제어: 이 문서에서 이미 번역 중인 페이지가 있으면 거부
    for key, task in _active_tasks.items():
        if key.startswith(doc_id + ":") and not task.done():
            raise RuntimeError("이 문서에서 이미 번역이 진행 중입니다")

    effective_model = model or config.TRANSLATOR_TRANSLATION_MODEL or config.OLLAMA_MODEL

    # 페이지 상태 업데이트
    page_status = meta.get("page_status", {})
    page_status[str(page_num)] = {
        "status": "translating",
        "model": effective_model,
        "progress_stage": "번역 준비 중...",
        "started_at": datetime.now().isoformat(),
    }
    meta["page_status"] = page_status
    meta["status"] = "uploaded"  # 문서 전체 상태는 uploaded 유지
    _save_meta(username, doc_id, meta)

    key = _task_key(doc_id, page_num)
    task = asyncio.create_task(_run_pmt_page(username, doc_id, page_num, effective_model))
    _active_tasks[key] = task


async def _run_pmt_page(username: str, doc_id: str, page_num: int, model: str):
    """PMT CLI 비동기 실행 — 단일 페이지"""
    import time

    key = _task_key(doc_id, page_num)

    src_path = _doc_dir(username, doc_id) / "original.pdf"
    if not src_path.exists():
        _mark_page_error(username, doc_id, page_num, "원본 PDF 파일 없음")
        return

    tmp_dir = _doc_dir(username, doc_id) / f"_pmt_tmp_p{page_num}"
    tmp_dir.mkdir(exist_ok=True)

    cmd = [
        "pdf2zh",
        "--ollama",
        "--ollama-model", model,
        "--ollama-host", config.OLLAMA_URL,
        "--lang-in", "English",
        "--lang-out", "Korean",
        "--primary-font-family", "sans-serif",
        "--pages", str(page_num),
        "--only-include-translated-page",
        "--no-dual",
        "--output", str(tmp_dir),
        str(src_path),
    ]

    _update_page_progress(username, doc_id, page_num, "번역 중...")

    # 로그 파일
    log_path = _doc_dir(username, doc_id) / "pmt.log"

    def _log(msg):
        with open(log_path, "a", encoding="utf-8") as lf:
            lf.write(f"[{datetime.now().strftime('%H:%M:%S')}] [p{page_num}] {msg}\n")

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _active_procs[key] = proc

        timeout = getattr(config, "TRANSLATOR_PAGE_TIMEOUT", 300)
        deadline = time.monotonic() + timeout

        pmt_start = time.monotonic()
        _log(f"시작 | model: {model}")

        # stderr 파싱
        while True:
            if time.monotonic() > deadline:
                proc.kill()
                shutil.rmtree(tmp_dir, ignore_errors=True)
                elapsed = time.monotonic() - pmt_start
                _log(f"TIMEOUT | total {elapsed:.1f}s")
                _mark_page_error(username, doc_id, page_num, f"번역 시간 초과 ({timeout // 60}분)")
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

            _log(f"stderr: {text}")

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
                _update_page_progress(username, doc_id, page_num, stage)

        await proc.wait()

        if proc.returncode != 0:
            elapsed = time.monotonic() - pmt_start
            _log(f"FAILED (exit {proc.returncode}) | total {elapsed:.1f}s")
            stdout_data = await proc.stdout.read()
            shutil.rmtree(tmp_dir, ignore_errors=True)
            log_text = stdout_data.decode("utf-8", errors="replace")[-500:] if stdout_data else ""
            _mark_page_error(username, doc_id, page_num, f"pdf2zh 실패 (exit {proc.returncode}): {log_text}")
            return

        # 결과 PDF 이동 → pages/{page_num}/translated.pdf
        page_dir = _doc_dir(username, doc_id) / "pages" / str(page_num)
        page_dir.mkdir(parents=True, exist_ok=True)

        mono_files = list(tmp_dir.glob("*.mono.pdf"))
        if not mono_files:
            # --only-include-translated-page 사용 시 .mono 없이 직접 출력될 수 있음
            mono_files = [f for f in tmp_dir.glob("*.pdf") if "dual" not in f.name]

        if not mono_files:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            _mark_page_error(username, doc_id, page_num, "pdf2zh 완료되었으나 결과 PDF가 없습니다")
            return

        shutil.move(str(mono_files[0]), str(page_dir / "translated.pdf"))
        shutil.rmtree(tmp_dir, ignore_errors=True)

        # 성공
        elapsed = time.monotonic() - pmt_start
        _log(f"DONE | total {elapsed:.1f}s")

        meta = _load_meta(username, doc_id)
        if meta:
            ps = meta.get("page_status", {})
            ps[str(page_num)] = {
                "status": "done",
                "model": model,
                "translated_at": datetime.now().isoformat(),
                "elapsed_sec": round(elapsed, 1),
            }
            meta["page_status"] = ps
            _save_meta(username, doc_id, meta)

    except asyncio.CancelledError:
        try:
            proc.kill()
        except Exception:
            pass
        shutil.rmtree(tmp_dir, ignore_errors=True)
        # 취소 시 상태를 pending으로 되돌림
        meta = _load_meta(username, doc_id)
        if meta:
            ps = meta.get("page_status", {})
            ps.pop(str(page_num), None)
            meta["page_status"] = ps
            _save_meta(username, doc_id, meta)
        return
    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        _mark_page_error(username, doc_id, page_num, str(e))
    finally:
        _active_tasks.pop(key, None)
        _active_procs.pop(key, None)


def get_page_translation_status(username: str, doc_id: str, page_num: int) -> Optional[dict]:
    """페이지별 번역 상태"""
    meta = _load_meta(username, doc_id)
    if not meta:
        return None

    ps = meta.get("page_status", {}).get(str(page_num))

    # 런타임 상태 보정
    key = _task_key(doc_id, page_num)
    if key in _active_tasks and not _active_tasks[key].done():
        if ps:
            ps["status"] = "translating"
        else:
            ps = {"status": "translating", "progress_stage": "번역 준비 중..."}

    if not ps:
        return {"status": "pending"}

    return ps


def cancel_page_translation(username: str, doc_id: str, page_num: int) -> bool:
    """페이지 번역 취소"""
    key = _task_key(doc_id, page_num)

    proc = _active_procs.pop(key, None)
    if proc:
        try:
            proc.kill()
        except Exception:
            pass

    task = _active_tasks.pop(key, None)
    if task and not task.done():
        task.cancel()

    meta = _load_meta(username, doc_id)
    if not meta:
        return False

    ps = meta.get("page_status", {})
    ps.pop(str(page_num), None)
    meta["page_status"] = ps
    _save_meta(username, doc_id, meta)
    return True


def get_doc_page_summary(username: str, doc_id: str) -> Optional[dict]:
    """뷰어용 전체 페이지 상태 요약"""
    meta = _load_meta(username, doc_id)
    if not meta:
        return None

    page_status = meta.get("page_status", {})

    # 런타임 상태 보정
    for key, task in _active_tasks.items():
        if key.startswith(doc_id + ":") and not task.done():
            pnum = key.split(":")[1]
            if pnum in page_status:
                page_status[pnum]["status"] = "translating"

    return {
        "id": doc_id,
        "filename": meta.get("filename"),
        "pages": meta.get("pages", 0),
        "page_status": page_status,
        "has_legacy_translation": (_doc_dir(username, doc_id) / "translated.pdf").exists(),
    }


# ── 헬퍼 ──

def _update_page_progress(username: str, doc_id: str, page_num: int, stage: str):
    meta = _load_meta(username, doc_id)
    if meta:
        ps = meta.get("page_status", {})
        entry = ps.get(str(page_num), {})
        entry["progress_stage"] = stage
        entry["status"] = "translating"
        ps[str(page_num)] = entry
        meta["page_status"] = ps
        _save_meta(username, doc_id, meta)


def _mark_page_error(username: str, doc_id: str, page_num: int, error_msg: str):
    meta = _load_meta(username, doc_id)
    if meta:
        ps = meta.get("page_status", {})
        entry = ps.get(str(page_num), {})
        entry["status"] = "error"
        entry["error"] = error_msg
        entry["progress_stage"] = None
        ps[str(page_num)] = entry
        meta["page_status"] = ps
        _save_meta(username, doc_id, meta)

    key = _task_key(doc_id, page_num)
    _active_tasks.pop(key, None)


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
