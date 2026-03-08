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
# 키: "{doc_id}:{pages_str}" (예: "doc:3" 또는 "doc:3-7")
_active_tasks: dict[str, asyncio.Task] = {}
_active_procs: dict[str, asyncio.subprocess.Process] = {}

# ── GPU 동시 번역 제한 (L40-48GB 기준) ──
_translation_semaphore: asyncio.Semaphore | None = None

def _get_semaphore() -> asyncio.Semaphore:
    """이벤트 루프 내에서 Semaphore 지연 생성"""
    global _translation_semaphore
    if _translation_semaphore is None:
        max_concurrent = getattr(config, "TRANSLATOR_MAX_CONCURRENT", 4)
        _translation_semaphore = asyncio.Semaphore(max_concurrent)
    return _translation_semaphore

# ── 진행 상태 메모리 캐시 (meta.json I/O 최소화) ──
# 키: "{doc_id}:{pages_str}" → progress_stage 문자열
_page_progress: dict[str, str] = {}

MAX_RANGE_PAGES = 5


def _ensure_data_dir():
    """data/translator 디렉토리 보장"""
    Path(config.TRANSLATOR_DATA_DIR).mkdir(parents=True, exist_ok=True)


def _user_dir(username: str) -> Path:
    return Path(config.TRANSLATOR_DATA_DIR) / username


def _doc_dir(username: str, doc_id: str) -> Path:
    return _user_dir(username) / doc_id


def _user_index_path(username: str) -> Path:
    return _user_dir(username) / "_index.json"


def _user_folders_path(username: str) -> Path:
    return _user_dir(username) / "_folders.json"


def _generate_id() -> str:
    now = datetime.now()
    rand = hashlib.md5(os.urandom(8)).hexdigest()[:6]
    return f"{now.strftime('%Y%m%d_%H%M%S')}_{rand}"


def _task_key(doc_id: str, pages_str: str) -> str:
    return f"{doc_id}:{pages_str}"


def _parse_pages(pages_str: str, total: int) -> list[int]:
    """페이지 문자열 파싱: "3" → [3], "3-7" → [3,4,5,6,7]"""
    pages_str = pages_str.strip()
    if "-" in pages_str:
        parts = pages_str.split("-", 1)
        start, end = int(parts[0]), int(parts[1])
        if end < start:
            raise ValueError(f"끝 페이지({end})가 시작 페이지({start})보다 작습니다")
        if end - start + 1 > MAX_RANGE_PAGES:
            raise ValueError(f"최대 {MAX_RANGE_PAGES}페이지까지 범위 번역 가능합니다")
        page_list = list(range(start, end + 1))
    else:
        page_list = [int(pages_str)]

    for p in page_list:
        if p < 1 or p > total:
            raise ValueError(f"유효하지 않은 페이지 번호: {p} (1~{total})")
    return page_list


def _is_page_in_task_key(key: str, page_num: int) -> bool:
    """Task 키(예: "doc:3-7")에 특정 페이지가 포함되는지 확인"""
    parts = key.split(":", 1)
    if len(parts) != 2:
        return False
    pages_str = parts[1]
    try:
        if "-" in pages_str:
            s, e = pages_str.split("-", 1)
            return int(s) <= page_num <= int(e)
        else:
            return int(pages_str) == page_num
    except ValueError:
        return False


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
# 폴더 CRUD
# ══════════════════════════════════════

def _load_user_folders(username: str) -> list[dict]:
    path = _user_folders_path(username)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _save_user_folders(username: str, folders: list[dict]):
    udir = _user_dir(username)
    udir.mkdir(parents=True, exist_ok=True)
    with open(_user_folders_path(username), "w", encoding="utf-8") as f:
        json.dump(folders, f, ensure_ascii=False, indent=2)


def get_folders(username: str) -> list[dict]:
    return _load_user_folders(username)


def create_folder(username: str, name: str, parent_id: Optional[str] = None) -> dict:
    folders = _load_user_folders(username)

    # parent_id 유효성 검증
    if parent_id:
        if not any(f["id"] == parent_id for f in folders):
            raise ValueError(f"상위 폴더를 찾을 수 없습니다: {parent_id}")

    # 같은 레벨에서 order 산출
    siblings = [f for f in folders if f.get("parent_id") == parent_id]
    order = max((f.get("order", 0) for f in siblings), default=-1) + 1

    folder = {
        "id": "f_" + _generate_id(),
        "name": name,
        "parent_id": parent_id,
        "order": order,
    }
    folders.append(folder)
    _save_user_folders(username, folders)
    return folder


def rename_folder(username: str, folder_id: str, new_name: str) -> dict:
    folders = _load_user_folders(username)
    for f in folders:
        if f["id"] == folder_id:
            f["name"] = new_name
            _save_user_folders(username, folders)
            return f
    raise FileNotFoundError(f"폴더를 찾을 수 없습니다: {folder_id}")


def delete_folder(username: str, folder_id: str) -> bool:
    """폴더 삭제 — 하위 폴더/문서는 삭제된 폴더의 상위로 이동"""
    folders = _load_user_folders(username)
    target = None
    for f in folders:
        if f["id"] == folder_id:
            target = f
            break
    if not target:
        return False

    parent_id = target.get("parent_id")

    # 하위 폴더들의 parent_id를 삭제 폴더의 parent로 변경
    for f in folders:
        if f.get("parent_id") == folder_id:
            f["parent_id"] = parent_id

    # 대상 폴더 제거
    folders = [f for f in folders if f["id"] != folder_id]
    _save_user_folders(username, folders)

    # 이 폴더에 속한 문서들을 상위 폴더로 이동
    index = _load_user_index(username)
    changed = False
    for entry in index:
        if entry.get("folder") == folder_id:
            entry["folder"] = parent_id
            changed = True
    if changed:
        _save_user_index(username, index)

    return True


def move_document_to_folder(username: str, doc_id: str, folder_id: Optional[str]) -> bool:
    """문서를 폴더로 이동 (folder_id=None → 루트)"""
    if folder_id:
        folders = _load_user_folders(username)
        if not any(f["id"] == folder_id for f in folders):
            raise ValueError(f"폴더를 찾을 수 없습니다: {folder_id}")

    index = _load_user_index(username)
    found = False
    for entry in index:
        if entry["id"] == doc_id:
            entry["folder"] = folder_id
            found = True
            break
    if not found:
        return False

    _save_user_index(username, index)
    return True


# ══════════════════════════════════════
# 마킹 (annotations) CRUD
# ══════════════════════════════════════

def _annotations_path(username: str, doc_id: str) -> Path:
    return _doc_dir(username, doc_id) / "annotations.json"


def _load_annotations(username: str, doc_id: str) -> dict:
    path = _annotations_path(username, doc_id)
    if not path.exists():
        return {"highlights": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"highlights": []}


def _save_annotations(username: str, doc_id: str, data: dict):
    with open(_annotations_path(username, doc_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_annotations(username: str, doc_id: str) -> dict:
    """문서의 전체 마킹 목록 반환"""
    meta = _load_meta(username, doc_id)
    if not meta:
        raise FileNotFoundError(f"문서를 찾을 수 없습니다: {doc_id}")
    return _load_annotations(username, doc_id)


def create_annotation(username: str, doc_id: str, annotation: dict) -> dict:
    """마킹 생성 → ID 자동 부여 후 반환"""
    meta = _load_meta(username, doc_id)
    if not meta:
        raise FileNotFoundError(f"문서를 찾을 수 없습니다: {doc_id}")

    ann_id = "h_" + _generate_id()
    highlight = {
        "id": ann_id,
        "page": annotation["page"],
        "rects": annotation["rects"],
        "color": annotation.get("color", "yellow"),
        "text": annotation.get("text", ""),
        "memo": annotation.get("memo", ""),
        "created_at": datetime.now().isoformat(),
    }

    data = _load_annotations(username, doc_id)
    data["highlights"].append(highlight)
    _save_annotations(username, doc_id, data)
    return highlight


def update_annotation(username: str, doc_id: str, ann_id: str, updates: dict) -> dict:
    """마킹 수정 (memo, color 등)"""
    data = _load_annotations(username, doc_id)
    for h in data["highlights"]:
        if h["id"] == ann_id:
            for key in ("memo", "color"):
                if key in updates:
                    h[key] = updates[key]
            _save_annotations(username, doc_id, data)
            return h
    raise FileNotFoundError(f"마킹을 찾을 수 없습니다: {ann_id}")


def delete_annotation(username: str, doc_id: str, ann_id: str) -> bool:
    """마킹 삭제"""
    data = _load_annotations(username, doc_id)
    before = len(data["highlights"])
    data["highlights"] = [h for h in data["highlights"] if h["id"] != ann_id]
    if len(data["highlights"]) == before:
        raise FileNotFoundError(f"마킹을 찾을 수 없습니다: {ann_id}")
    _save_annotations(username, doc_id, data)
    return True


# ══════════════════════════════════════
# AI 선택 번역/요약
# ══════════════════════════════════════

def ai_selection_query(text: str, action: str, model: Optional[str] = None) -> str:
    """선택 텍스트에 대해 Ollama로 번역/요약 수행"""
    import requests

    if action == "translate":
        system_prompt = config.TRANSLATOR_AI_TRANSLATE_PROMPT
    elif action == "summarize":
        system_prompt = config.TRANSLATOR_AI_SUMMARIZE_PROMPT
    else:
        raise ValueError(f"지원하지 않는 액션: {action}")

    use_model = model or config.TRANSLATOR_TRANSLATION_MODEL or config.OLLAMA_MODEL

    resp = requests.post(
        f"{config.OLLAMA_URL}/api/generate",
        json={
            "model": use_model,
            "system": system_prompt,
            "prompt": text,
            "stream": False,
            "options": {"temperature": 0.3},
        },
        timeout=config.TRANSLATOR_AI_SELECTION_TIMEOUT,
    )
    resp.raise_for_status()
    return {"result": resp.json().get("response", "").strip(), "model": use_model}


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
            if meta.get("title") and meta["title"] != meta.get("filename"):
                entry["title"] = meta["title"]
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
        _page_progress.pop(key, None)

    if doc_path.exists():
        shutil.rmtree(doc_path, ignore_errors=True)
        # Windows 파일 잠금 등으로 삭제 실패 시 재시도
        if doc_path.exists():
            import time, gc
            gc.collect()
            time.sleep(0.5)
            shutil.rmtree(doc_path, ignore_errors=True)
        if doc_path.exists():
            print(f"[Translator] WARNING: 디렉토리 삭제 실패 (잠금?) — {doc_path}")

    # 인덱스에서 제거
    index = _load_user_index(username)
    new_index = [e for e in index if e["id"] != doc_id]
    if len(new_index) == len(index):
        return False
    _save_user_index(username, new_index)
    return True


def rename_document(username: str, doc_id: str, new_title: str) -> bool:
    """문서 제목(title) 변경 — meta.json + _index.json 동시 갱신"""
    meta = _load_meta(username, doc_id)
    if not meta:
        return False
    meta["title"] = new_title
    _save_meta(username, doc_id, meta)
    # 인덱스에도 title 반영
    index = _load_user_index(username)
    for entry in index:
        if entry["id"] == doc_id:
            entry["title"] = new_title
            break
    _save_user_index(username, index)
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

def start_page_translation(username: str, doc_id: str, pages: str, model: Optional[str] = None):
    """페이지 번역 시작 (단일 또는 범위) → asyncio.Task 생성, 즉시 반환
    pages: "3" (단일) 또는 "3-7" (범위, 최대 5페이지)
    """
    meta = _load_meta(username, doc_id)
    if not meta:
        raise FileNotFoundError(f"문서 없음: {doc_id}")

    total = meta.get("pages", 0)
    page_list = _parse_pages(pages, total)

    # 동시성 제어: 이 문서에서 이미 번역 중인 페이지가 있으면 거부
    for key, task in _active_tasks.items():
        if key.startswith(doc_id + ":") and not task.done():
            raise RuntimeError("이 문서에서 이미 번역이 진행 중입니다")

    effective_model = model or config.TRANSLATOR_TRANSLATION_MODEL or config.OLLAMA_MODEL

    # 범위 내 모든 페이지 상태를 translating으로 기록
    page_status = meta.get("page_status", {})
    for pnum in page_list:
        page_status[str(pnum)] = {
            "status": "translating",
            "model": effective_model,
            "progress_stage": "번역 준비 중...",
            "started_at": datetime.now().isoformat(),
        }
    meta["page_status"] = page_status
    meta["status"] = "uploaded"  # 문서 전체 상태는 uploaded 유지
    _save_meta(username, doc_id, meta)

    key = _task_key(doc_id, pages)
    _page_progress[key] = "번역 대기 중..."
    task = asyncio.create_task(_run_pmt_pages_guarded(username, doc_id, pages, page_list, effective_model))
    _active_tasks[key] = task


async def _run_pmt_pages_guarded(username: str, doc_id: str, pages_str: str, page_list: list[int], model: str):
    """Semaphore로 동시 번역 수 제한 후 실제 번역 실행"""
    key = _task_key(doc_id, pages_str)
    sem = _get_semaphore()
    _page_progress[key] = "번역 대기 중... (GPU 순서 대기)"
    async with sem:
        _page_progress[key] = "번역 준비 중..."
        await _run_pmt_pages(username, doc_id, pages_str, page_list, model)


async def _run_pmt_pages(username: str, doc_id: str, pages_str: str, page_list: list[int], model: str):
    """PMT CLI 비동기 실행 — 단일 또는 범위 페이지"""
    import time
    import fitz

    key = _task_key(doc_id, pages_str)
    is_range = len(page_list) > 1
    label = f"p{pages_str}" if is_range else f"p{page_list[0]}"

    src_path = _doc_dir(username, doc_id) / "original.pdf"
    if not src_path.exists():
        for pnum in page_list:
            _mark_page_error(username, doc_id, pnum, "원본 PDF 파일 없음")
        return

    tmp_dir = _doc_dir(username, doc_id) / f"_pmt_tmp_{label}"
    tmp_dir.mkdir(exist_ok=True)

    # pdf2zh의 --pages: "3" 또는 "3-7" (네이티브 범위 지원)
    cmd = [
        "pdf2zh",
        "--ollama",
        "--ollama-model", model,
        "--ollama-host", config.OLLAMA_URL,
        "--lang-in", "English",
        "--lang-out", "Korean",
        "--primary-font-family", "sans-serif",
        "--pages", pages_str,
        "--only-include-translated-page",
        "--no-dual",
        "--output", str(tmp_dir),
    ]

    # 동적 옵션 (settings에서 읽음)
    if getattr(config, "TRANSLATOR_CUSTOM_PROMPT", ""):
        cmd += ["--custom-system-prompt", config.TRANSLATOR_CUSTOM_PROMPT]
    if getattr(config, "TRANSLATOR_DISABLE_RICH_TEXT", False):
        cmd.append("--disable-rich-text-translate")
    if getattr(config, "TRANSLATOR_TRANSLATE_TABLE", False):
        cmd.append("--translate-table-text")
    if getattr(config, "TRANSLATOR_MIN_TEXT_LENGTH", 0) > 0:
        cmd += ["--min-text-length", str(config.TRANSLATOR_MIN_TEXT_LENGTH)]
    if getattr(config, "TRANSLATOR_QPS", 0) > 0:
        cmd += ["--qps", str(config.TRANSLATOR_QPS)]
    if getattr(config, "TRANSLATOR_OCR_WORKAROUND", False):
        cmd.append("--ocr-workaround")
    if getattr(config, "TRANSLATOR_ENHANCE_COMPAT", False):
        cmd.append("--enhance-compatibility")

    cmd.append(str(src_path))  # 입력 파일은 항상 마지막

    for pnum in page_list:
        _update_page_progress(username, doc_id, pnum, "번역 중...")

    # 로그 파일
    log_path = _doc_dir(username, doc_id) / "pmt.log"

    def _log(msg):
        with open(log_path, "a", encoding="utf-8") as lf:
            lf.write(f"[{datetime.now().strftime('%H:%M:%S')}] [{label}] {msg}\n")

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _active_procs[key] = proc

        # 범위 번역은 페이지 수에 비례한 타임아웃
        base_timeout = getattr(config, "TRANSLATOR_PAGE_TIMEOUT", 300)
        timeout = base_timeout * len(page_list)
        deadline = time.monotonic() + timeout

        pmt_start = time.monotonic()
        _log(f"시작 | model: {model} | pages: {pages_str}")

        # stderr 파싱
        while True:
            if time.monotonic() > deadline:
                proc.kill()
                shutil.rmtree(tmp_dir, ignore_errors=True)
                elapsed = time.monotonic() - pmt_start
                _log(f"TIMEOUT | total {elapsed:.1f}s")
                for pnum in page_list:
                    _mark_page_error(username, doc_id, pnum, f"번역 시간 초과 ({timeout // 60}분)")
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
                _page_progress[key] = stage

        await proc.wait()

        if proc.returncode != 0:
            elapsed = time.monotonic() - pmt_start
            _log(f"FAILED (exit {proc.returncode}) | total {elapsed:.1f}s")
            stdout_data = await proc.stdout.read()
            shutil.rmtree(tmp_dir, ignore_errors=True)
            log_text = stdout_data.decode("utf-8", errors="replace")[-500:] if stdout_data else ""
            for pnum in page_list:
                _mark_page_error(username, doc_id, pnum, f"pdf2zh 실패 (exit {proc.returncode}): {log_text}")
            return

        # 결과 PDF 찾기
        mono_files = list(tmp_dir.glob("*.mono.pdf"))
        if not mono_files:
            mono_files = [f for f in tmp_dir.glob("*.pdf") if "dual" not in f.name]

        if not mono_files:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            for pnum in page_list:
                _mark_page_error(username, doc_id, pnum, "pdf2zh 완료되었으나 결과 PDF가 없습니다")
            return

        mono_file = mono_files[0]
        elapsed = time.monotonic() - pmt_start

        # PyMuPDF로 페이지별 분리 저장
        result_doc = fitz.open(str(mono_file))
        result_pages = len(result_doc)

        if result_pages != len(page_list):
            _log(f"WARNING: 결과 PDF {result_pages}페이지, 요청 {len(page_list)}페이지")

        for i, pnum in enumerate(page_list):
            if i >= result_pages:
                _mark_page_error(username, doc_id, pnum, f"결과 PDF에 해당 페이지 없음 (인덱스 {i})")
                continue

            page_dir = _doc_dir(username, doc_id) / "pages" / str(pnum)
            page_dir.mkdir(parents=True, exist_ok=True)

            single = fitz.open()
            single.insert_pdf(result_doc, from_page=i, to_page=i)
            single.save(str(page_dir / "translated.pdf"))
            single.close()

        result_doc.close()
        shutil.rmtree(tmp_dir, ignore_errors=True)

        # 성공 — 메타 업데이트
        _log(f"DONE | total {elapsed:.1f}s")

        meta = _load_meta(username, doc_id)
        if meta:
            ps = meta.get("page_status", {})
            for pnum in page_list:
                entry = {
                    "status": "done",
                    "model": model,
                    "translated_at": datetime.now().isoformat(),
                    "elapsed_sec": round(elapsed, 1),
                }
                if is_range:
                    entry["batch"] = pages_str
                ps[str(pnum)] = entry
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
            for pnum in page_list:
                ps.pop(str(pnum), None)
            meta["page_status"] = ps
            _save_meta(username, doc_id, meta)
        return
    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        for pnum in page_list:
            _mark_page_error(username, doc_id, pnum, str(e))
    finally:
        _active_tasks.pop(key, None)
        _active_procs.pop(key, None)
        _page_progress.pop(key, None)


def get_page_translation_status(username: str, doc_id: str, page_num: int) -> Optional[dict]:
    """페이지별 번역 상태 (활성 Task는 메모리 캐시 우선, 그 외 meta.json)"""
    # 활성 Task에서 이 페이지가 포함된 키 찾기
    for tk, task in _active_tasks.items():
        if tk.startswith(doc_id + ":") and not task.done():
            if _is_page_in_task_key(tk, page_num):
                return {
                    "status": "translating",
                    "progress_stage": _page_progress.get(tk, "번역 준비 중..."),
                }

    # 완료/에러/미번역은 meta.json에서 확인
    meta = _load_meta(username, doc_id)
    if not meta:
        return None

    ps = meta.get("page_status", {}).get(str(page_num))
    if not ps:
        return {"status": "pending"}

    return ps


def cancel_page_translation(username: str, doc_id: str, page_num: int) -> bool:
    """페이지 번역 취소 — 해당 페이지를 포함하는 범위 Task도 취소"""
    # 이 페이지를 포함하는 활성 Task 키 찾기
    matched_key = None
    for tk, task in _active_tasks.items():
        if tk.startswith(doc_id + ":") and not task.done():
            if _is_page_in_task_key(tk, page_num):
                matched_key = tk
                break

    if matched_key:
        proc = _active_procs.pop(matched_key, None)
        if proc:
            try:
                proc.kill()
            except Exception:
                pass

        task = _active_tasks.pop(matched_key, None)
        if task and not task.done():
            task.cancel()
        _page_progress.pop(matched_key, None)

        # 범위 내 모든 페이지 상태 초기화
        pages_str = matched_key.split(":", 1)[1]
        meta = _load_meta(username, doc_id)
        if meta:
            total = meta.get("pages", 0)
            try:
                affected = _parse_pages(pages_str, total)
            except ValueError:
                affected = [page_num]
            ps = meta.get("page_status", {})
            for pnum in affected:
                ps.pop(str(pnum), None)
            meta["page_status"] = ps
            _save_meta(username, doc_id, meta)
        return True

    # 활성 Task 없는 경우 — meta에서만 제거
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

    # 런타임 상태 보정 (메모리 캐시에서 최신 progress_stage 반영)
    for key, task in _active_tasks.items():
        if key.startswith(doc_id + ":") and not task.done():
            pages_str = key.split(":", 1)[1]
            progress = _page_progress.get(key, "번역 준비 중...")
            total_p = meta.get("pages", 0)
            try:
                affected = _parse_pages(pages_str, total_p)
            except ValueError:
                continue
            for pnum in affected:
                page_status[str(pnum)] = {
                    "status": "translating",
                    "progress_stage": progress,
                }

    return {
        "id": doc_id,
        "filename": meta.get("filename"),
        "pages": meta.get("pages", 0),
        "page_status": page_status,
        "has_legacy_translation": (_doc_dir(username, doc_id) / "translated.pdf").exists(),
    }


# ══════════════════════════════════════
# 텍스트 번역 (폴백 엔진)
# ══════════════════════════════════════

# 텍스트 번역 전용 작업 추적 (pdf2zh와 독립)
_text_active_tasks: dict[str, asyncio.Task] = {}
_text_page_progress: dict[str, str] = {}


def start_text_translation(username: str, doc_id: str, page_num: int,
                           model: Optional[str] = None, font_scale: Optional[float] = None):
    """텍스트 번역 시작 → asyncio.Task 생성, 즉시 반환"""
    meta = _load_meta(username, doc_id)
    if not meta:
        raise FileNotFoundError(f"문서 없음: {doc_id}")

    total = meta.get("pages", 0)
    if page_num < 1 or page_num > total:
        raise ValueError(f"유효하지 않은 페이지 번호: {page_num} (1~{total})")

    # 동시성 제어: 이 문서에서 텍스트 번역 진행 중이면 거부
    key = f"tt:{doc_id}:{page_num}"
    if key in _text_active_tasks and not _text_active_tasks[key].done():
        raise RuntimeError("이 페이지에서 텍스트 번역이 진행 중입니다")

    effective_model = model or config.TRANSLATOR_TRANSLATION_MODEL or config.OLLAMA_MODEL

    # meta.json에 텍스트 번역 상태 기록
    page_status = meta.get("page_status", {})
    ps = page_status.get(str(page_num), {})
    ps["text_translate"] = {
        "status": "translating",
        "model": effective_model,
        "font_scale": font_scale,
        "started_at": datetime.now().isoformat(),
    }
    page_status[str(page_num)] = ps
    meta["page_status"] = page_status
    _save_meta(username, doc_id, meta)

    _text_page_progress[key] = "번역 준비 중..."
    task = asyncio.create_task(
        _run_text_translation(username, doc_id, page_num, effective_model, font_scale, key)
    )
    _text_active_tasks[key] = task


async def _run_text_translation(username: str, doc_id: str, page_num: int,
                                 model: str, font_scale: Optional[float], key: str):
    """텍스트 번역 비동기 래퍼 (동기 함수를 스레드 풀에서 실행)"""
    from services.text_translator import translate_page

    src_path = _doc_dir(username, doc_id) / "original.pdf"
    output_dir = _doc_dir(username, doc_id) / "pages" / str(page_num)

    def progress_cb(stage: str):
        _text_page_progress[key] = stage

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: translate_page(
                original_pdf_path=src_path,
                output_dir=output_dir,
                page_num=page_num,
                model=model,
                font_scale=font_scale,
                progress_callback=progress_cb,
            ),
        )

        # 성공 — meta.json 업데이트
        meta = _load_meta(username, doc_id)
        if meta:
            ps = meta.get("page_status", {}).get(str(page_num), {})
            ps["text_translate"] = {
                "status": "done",
                "model": model,
                "font_scale": result.get("font_scale", 0.75),
                "translated_at": datetime.now().isoformat(),
                "elapsed_sec": result.get("elapsed_sec", 0),
            }
            meta["page_status"][str(page_num)] = ps
            _save_meta(username, doc_id, meta)

    except Exception as e:
        meta = _load_meta(username, doc_id)
        if meta:
            ps = meta.get("page_status", {}).get(str(page_num), {})
            ps["text_translate"] = {
                "status": "error",
                "error": str(e),
            }
            meta["page_status"][str(page_num)] = ps
            _save_meta(username, doc_id, meta)
    finally:
        _text_active_tasks.pop(key, None)
        _text_page_progress.pop(key, None)


def get_text_translation_status(username: str, doc_id: str, page_num: int) -> Optional[dict]:
    """텍스트 번역 상태"""
    key = f"tt:{doc_id}:{page_num}"
    if key in _text_active_tasks and not _text_active_tasks[key].done():
        return {
            "status": "translating",
            "progress_stage": _text_page_progress.get(key, "번역 준비 중..."),
        }

    meta = _load_meta(username, doc_id)
    if not meta:
        return None

    ps = meta.get("page_status", {}).get(str(page_num), {})
    tt = ps.get("text_translate")
    if not tt:
        return {"status": "pending"}
    return tt


def get_text_translated_pdf_path(username: str, doc_id: str, page_num: int) -> Optional[Path]:
    """텍스트 번역 PDF 경로"""
    path = _doc_dir(username, doc_id) / "pages" / str(page_num) / "text_translated.pdf"
    return path if path.exists() else None


def cancel_text_translation(username: str, doc_id: str, page_num: int) -> bool:
    """텍스트 번역 취소"""
    key = f"tt:{doc_id}:{page_num}"
    task = _text_active_tasks.pop(key, None)
    if task and not task.done():
        task.cancel()
    _text_page_progress.pop(key, None)

    meta = _load_meta(username, doc_id)
    if meta:
        ps = meta.get("page_status", {}).get(str(page_num), {})
        ps.pop("text_translate", None)
        meta["page_status"][str(page_num)] = ps
        _save_meta(username, doc_id, meta)
    return True


# ── 헬퍼 ──

def _update_page_progress(username: str, doc_id: str, page_num: int, stage: str):
    """메모리 캐시에만 진행 상태 저장 — 이 페이지를 포함하는 Task 키에 기록"""
    # 이 페이지를 포함하는 활성 Task 키 찾기
    for tk in _active_tasks:
        if tk.startswith(doc_id + ":") and _is_page_in_task_key(tk, page_num):
            _page_progress[tk] = stage
            return
    # 폴백: 단일 페이지 키
    _page_progress[f"{doc_id}:{page_num}"] = stage


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
    _page_progress.pop(key, None)


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
