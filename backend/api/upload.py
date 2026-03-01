"""
문서 업로드 및 변환 API
- Word/PDF 파일 업로드 → HTML 변환 → contents/ 배치
- 변환 후 검색 인덱스 자동 재생성
- menu.json 자동 갱신 (URL 없는 노드에 업로드 시)
"""
import os
import sys
import json
import shutil
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from dependencies import require_editor

router = APIRouter(tags=["upload"])

# 프로젝트 루트 디렉토리 (backend/api/ → backend/ → project root)
PROJECT_ROOT = Path(__file__).parent.parent.parent

# 변환기 경로
CONVERTER_DIR = PROJECT_ROOT / "tools" / "converter"

# 허용 확장자
ALLOWED_EXTENSIONS = {'.docx', '.pdf'}

# 최대 파일 크기 (500MB)
MAX_FILE_SIZE = 500 * 1024 * 1024

# 임시 업로드 디렉토리
from config import UPLOAD_TEMP_DIR as _CUSTOM_TEMP_DIR
UPLOAD_TEMP_DIR = Path(_CUSTOM_TEMP_DIR) if _CUSTOM_TEMP_DIR else PROJECT_ROOT / "backend" / "temp"


def _progress_event(step: str, status: str, message: str, **extra) -> str:
    """NDJSON 진행 이벤트 생성"""
    event = {"step": step, "status": status, "message": message, **extra}
    return json.dumps(event, ensure_ascii=False) + "\n"


STREAM_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Content-Type-Options": "nosniff",
}


class UploadResponse(BaseModel):
    success: bool
    message: str
    output_path: Optional[str] = None
    stats: Optional[dict] = None


class ReindexResponse(BaseModel):
    success: bool
    message: str
    indexed_count: Optional[int] = None


class IndexStatusResponse(BaseModel):
    up_to_date: bool
    index_modified: Optional[str] = None
    latest_content_modified: Optional[str] = None


def validate_target_path(target_path: str) -> Path:
    """대상 경로 검증 (보안: contents/ 외부 접근 방지)"""
    if not target_path.startswith("contents/"):
        raise HTTPException(status_code=400, detail="Invalid path: must be under contents/")

    full_path = (PROJECT_ROOT / target_path).resolve()
    contents_root = (PROJECT_ROOT / "contents").resolve()

    if not str(full_path).startswith(str(contents_root)):
        raise HTTPException(status_code=400, detail="Invalid path: path traversal detected")

    return full_path


def run_converter(input_path: Path, output_path: Path, file_ext: str) -> dict:
    """변환기를 호출하여 파일 변환"""
    # 변환기 모듈 경로를 sys.path에 추가
    converter_dir_str = str(CONVERTER_DIR)
    if converter_dir_str not in sys.path:
        sys.path.insert(0, converter_dir_str)

    preprocessed_path = None
    try:
        if file_ext == '.docx':
            # 전처리: COM으로 장절번호 평문화 + 필드 갱신
            from config import WORD_COM_PREPROCESS
            if WORD_COM_PREPROCESS:
                from word_preprocessor import preprocess_docx
                preprocessed_path = preprocess_docx(str(input_path))

            from converter import DocxConverter
            conv = DocxConverter(config_path=str(CONVERTER_DIR / "config.json"))
            convert_input = preprocessed_path if preprocessed_path else str(input_path)
        elif file_ext == '.pdf':
            from pdf_converter import PdfConverter
            conv = PdfConverter(config_path=str(CONVERTER_DIR / "config.json"))
            convert_input = str(input_path)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")

        result = conv.convert(convert_input, str(output_path))

        if result.success:
            resp = {
                "success": True,
                "output_path": str(result.output_path),
                "stats": result.stats
            }
            if result.warnings:
                resp["warnings"] = result.warnings
            return resp
        else:
            return {
                "success": False,
                "error": result.error_message
            }
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"변환기 모듈 로드 실패: {str(e)}. python-docx 또는 PyMuPDF 패키지 설치를 확인하세요."
        )
    finally:
        # 전처리 임시 파일 정리
        if preprocessed_path and preprocessed_path != str(input_path):
            try:
                Path(preprocessed_path).unlink(missing_ok=True)
            except OSError:
                pass



def _run_search_reindex() -> dict:
    """검색 인덱스 재생성 (build-search-index.py --inject-ids)"""
    index_script = PROJECT_ROOT / "tools" / "build-search-index.py"

    if not index_script.exists():
        return {"success": False, "error": "build-search-index.py not found"}

    try:
        result = subprocess.run(
            [sys.executable, str(index_script), "--inject-ids"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=600
        )

        if result.returncode == 0:
            indexed_count = None
            for line in result.stdout.splitlines():
                if "항목" in line or "entries" in line.lower() or "indexed" in line.lower():
                    import re
                    nums = re.findall(r'\d+', line)
                    if nums:
                        indexed_count = int(nums[0])
                        break

            return {"success": True, "indexed_count": indexed_count, "output": result.stdout}
        else:
            return {"success": False, "error": result.stderr or result.stdout}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "검색 인덱싱 시간 초과 (600초)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _run_vector_incremental(target_url: str) -> str:
    """변환된 문서의 섹션을 벡터 인덱스에 증분 추가.
    search-index.json에서 해당 URL의 섹션만 추출하여 임베딩.
    returns: 상태 메시지 문자열 (빈 문자열이면 스킵)
    """
    try:
        # search-index.json에서 새 문서의 섹션 추출
        index_path = PROJECT_ROOT / "data" / "search-index.json"
        if not index_path.exists():
            return ""

        with open(index_path, "r", encoding="utf-8") as f:
            all_docs = json.load(f)

        new_sections = [d for d in all_docs if d.get("url") == target_url and d.get("content", "").strip()]
        if not new_sections:
            return ""

        from services.vector_search import append_documents
        result = append_documents(new_sections)

        if result["success"]:
            return f", 벡터 증분 추가: {result['added']}건"
        else:
            return f", 벡터 증분 실패: {result.get('error', '')}"
    except Exception as e:
        return f", 벡터 증분 실패: {e}"


def _run_vector_reindex() -> dict:
    """벡터 인덱스 재생성 (build-vector-index.py) + 메모리 캐시 갱신"""
    vector_script = PROJECT_ROOT / "tools" / "build-vector-index.py"

    if not vector_script.exists():
        return {"success": False, "error": "build-vector-index.py not found"}

    try:
        result = subprocess.run(
            [sys.executable, str(vector_script)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=600  # 임베딩 생성은 시간이 더 걸림
        )

        if result.returncode == 0:
            # 서버 메모리의 FAISS 캐시 갱신
            try:
                from services.vector_search import reload_index
                reload_index()
            except Exception:
                pass  # 임포트 실패 시 다음 검색에서 자동 로드됨
            return {"success": True, "output": result.stdout}
        else:
            return {"success": False, "error": result.stderr or result.stdout}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "벡터 인덱싱 시간 초과 (600초)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def update_menu_json(menu_path: list, url: str) -> bool:
    """menu.json에서 label 경로로 노드를 찾아 url 설정

    Args:
        menu_path: 루트→대상 노드까지의 레이블 배열 (예: ["개발 개요...", "개발 히스토리", "체계개발 단계"])
        url: 설정할 URL (예: "contents/dev-overview/history/phase.html")
    """
    menu_file = PROJECT_ROOT / "data" / "menu.json"

    if not menu_file.exists():
        return False

    with open(menu_file, 'r', encoding='utf-8') as f:
        menu_data = json.load(f)

    # label 경로를 따라 노드 탐색
    current_items = menu_data
    target_node = None

    for i, label in enumerate(menu_path):
        for item in current_items:
            if item.get('label') == label:
                if i == len(menu_path) - 1:
                    target_node = item
                else:
                    current_items = item.get('children', [])
                break
        else:
            # label을 찾지 못함
            return False

    if target_node is None:
        return False

    target_node['url'] = url

    with open(menu_file, 'w', encoding='utf-8') as f:
        json.dump(menu_data, f, ensure_ascii=False, indent=2)

    return True


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    target_path: str = Form(...),
    menu_path: Optional[str] = Form(None),
    auto_search_index: str = Form("true"),
    auto_vector_index: str = Form("true"),
    user: dict = Depends(require_editor),
):
    """
    문서 업로드 및 변환 API (NDJSON 스트리밍)

    - file: Word(.docx) 또는 PDF(.pdf) 파일
    - target_path: 변환 결과 저장 경로 (예: contents/dev-overview/document.html)
    - menu_path: 메뉴 노드 레이블 경로 (JSON 배열 문자열, URL 없는 노드 업로드 시)
    """
    # 유효성 검증은 스트리밍 전에 수행 (에러 시 HTTPException)
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식: {file_ext}. 허용: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    output_path = validate_target_path(target_path)

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"파일 크기 초과: {len(contents) / 1024 / 1024:.1f}MB (최대 {MAX_FILE_SIZE / 1024 / 1024:.0f}MB)"
        )

    # 기존 파일 백업
    if output_path.exists():
        backup_dir = PROJECT_ROOT / "backups"
        backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{output_path.stem}_{timestamp}_before_upload.bak"
        shutil.copy2(str(output_path), str(backup_dir / backup_name))

    # 임시 파일로 저장
    UPLOAD_TEMP_DIR.mkdir(exist_ok=True)
    temp_file = UPLOAD_TEMP_DIR / f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_ext}"
    with open(temp_file, "wb") as f:
        f.write(contents)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    async def _upload_stream():
        try:
            # 1. 문서 변환
            yield _progress_event("conversion", "started", "문서 변환 중...")
            try:
                conv_result = await asyncio.to_thread(run_converter, temp_file, output_path, file_ext)
            except HTTPException as e:
                yield _progress_event("conversion", "error", str(e.detail))
                yield _progress_event("done", "error", str(e.detail), success=False)
                return
            if not conv_result["success"]:
                err = conv_result.get("error", "Unknown error")
                yield _progress_event("conversion", "error", f"변환 실패: {err}")
                yield _progress_event("done", "error", f"변환 실패: {err}", success=False)
                return
            yield _progress_event("conversion", "completed", "문서 변환 완료")

            # 2. menu.json 갱신 (빠르므로 별도 이벤트 없음)
            menu_updated = False
            if menu_path:
                try:
                    path_list = json.loads(menu_path)
                    if isinstance(path_list, list) and len(path_list) > 0:
                        menu_updated = update_menu_json(path_list, target_path)
                except (json.JSONDecodeError, TypeError):
                    pass

            # 3. 검색 인덱스 재생성
            if auto_search_index.lower() == "true":
                yield _progress_event("search_index", "started", "검색 인덱스 생성 중...")
                search_result = await asyncio.to_thread(_run_search_reindex)
                if search_result["success"]:
                    count = search_result.get("indexed_count")
                    msg = f"검색 인덱스 갱신 완료{f' ({count}건)' if count else ''}"
                    yield _progress_event("search_index", "completed", msg)
                else:
                    err = search_result.get("error", "")
                    yield _progress_event("search_index", "error", f"검색 인덱스 실패: {err}")
            else:
                yield _progress_event("search_index", "skipped", "검색 인덱스 — 수동 모드 (건너뜀)")

            # 4. 벡터 인덱스 증분 추가
            if auto_vector_index.lower() == "true":
                yield _progress_event("vector_index", "started", "벡터 인덱스 갱신 중...")
                vec_msg = await asyncio.to_thread(_run_vector_incremental, target_path)
                if vec_msg and "실패" in vec_msg:
                    yield _progress_event("vector_index", "error", vec_msg.lstrip(", "))
                else:
                    msg = vec_msg.lstrip(", ") if vec_msg else "벡터 인덱스 갱신 완료"
                    yield _progress_event("vector_index", "completed", msg)
            else:
                yield _progress_event("vector_index", "skipped", "벡터 인덱스 — 수동 모드 (건너뜀)")

            # 5. 완료
            yield _progress_event(
                "done", "completed", "완료",
                success=True,
                output_path=target_path,
                menu_updated=menu_updated,
                stats=conv_result.get("stats"),
            )
        finally:
            if temp_file.exists():
                temp_file.unlink()

    return StreamingResponse(
        _upload_stream(),
        media_type="text/plain; charset=utf-8",
        headers=STREAM_HEADERS,
    )


@router.post("/reindex")
async def reindex(user: dict = Depends(require_editor)):
    """검색 인덱스 + 벡터 인덱스 전체 재생성 (NDJSON 스트리밍)"""

    async def _reindex_stream():
        indexed_count = None

        # 1. 검색 인덱스
        yield _progress_event("search_index", "started", "검색 인덱스 재생성 중...")
        search_result = await asyncio.to_thread(_run_search_reindex)
        if search_result["success"]:
            indexed_count = search_result.get("indexed_count")
            msg = f"검색 인덱스 완료{f' ({indexed_count}건)' if indexed_count else ''}"
            yield _progress_event("search_index", "completed", msg)
        else:
            err = search_result.get("error", "")
            yield _progress_event("search_index", "error", f"검색 인덱스 실패: {err}")
            yield _progress_event("done", "error", f"검색 인덱스 실패: {err}", success=False)
            return

        # 2. 벡터 인덱스 전체 재빌드
        yield _progress_event("vector_index", "started", "벡터 인덱스 재생성 중...")
        vector_result = await asyncio.to_thread(_run_vector_reindex)
        if vector_result["success"]:
            yield _progress_event("vector_index", "completed", "벡터 인덱스 재생성 완료")
        else:
            err = vector_result.get("error", "")
            yield _progress_event("vector_index", "error", f"벡터 인덱스 실패: {err}")

        # 3. 완료
        yield _progress_event(
            "done", "completed", "인덱스 재생성 완료",
            success=True,
            indexed_count=indexed_count,
        )

    return StreamingResponse(
        _reindex_stream(),
        media_type="text/plain; charset=utf-8",
        headers=STREAM_HEADERS,
    )


@router.get("/index-status", response_model=IndexStatusResponse)
async def index_status():
    """검색 인덱스 상태 확인 (최신/오래됨)"""
    index_path = PROJECT_ROOT / "data" / "search-index.json"
    contents_dir = PROJECT_ROOT / "contents"

    if not index_path.exists():
        return IndexStatusResponse(
            up_to_date=False,
            index_modified=None,
            latest_content_modified=None
        )

    index_mtime = index_path.stat().st_mtime

    # contents/ 하위 HTML 파일 중 가장 최근 수정 시간
    latest_content_mtime = 0
    for html_file in contents_dir.rglob("*.html"):
        mtime = html_file.stat().st_mtime
        if mtime > latest_content_mtime:
            latest_content_mtime = mtime

    return IndexStatusResponse(
        up_to_date=index_mtime >= latest_content_mtime,
        index_modified=datetime.fromtimestamp(index_mtime).isoformat(),
        latest_content_modified=datetime.fromtimestamp(latest_content_mtime).isoformat() if latest_content_mtime > 0 else None
    )
