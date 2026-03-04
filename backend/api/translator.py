"""
Translator API — PDF 업로드, 페이지별 번역, 문서 관리
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Body
from fastapi.responses import FileResponse, JSONResponse
from typing import Optional

from dependencies import get_current_user, require_editor
from services.translator_service import (
    upload_pdf, get_documents, get_document, delete_document,
    get_pdf_path, get_page_pdf_path,
    start_page_translation, get_page_translation_status,
    cancel_page_translation, get_doc_page_summary,
    get_ollama_models,
)
import config

router = APIRouter(prefix="/translator", tags=["translator"])


@router.post("/upload")
async def api_upload_pdf(
    file: UploadFile = File(...),
    user: dict = Depends(require_editor),
):
    """PDF 업로드 → 즉시 응답"""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드할 수 있습니다")

    contents = await file.read()
    if len(contents) > config.TRANSLATOR_MAX_PDF_SIZE:
        size_mb = len(contents) / 1024 / 1024
        max_mb = config.TRANSLATOR_MAX_PDF_SIZE / 1024 / 1024
        raise HTTPException(
            status_code=400,
            detail=f"파일 크기 초과: {size_mb:.1f}MB (최대 {max_mb:.0f}MB)",
        )

    meta = upload_pdf(contents, file.filename, user["username"])
    return meta


@router.get("/documents")
async def api_list_documents(user: dict = Depends(get_current_user)):
    """유저별 문서 목록"""
    return get_documents(user["username"])


@router.get("/document/{doc_id}")
async def api_get_document(doc_id: str, user: dict = Depends(get_current_user)):
    """문서 메타 (meta.json)"""
    doc = get_document(user["username"], doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    return doc


@router.delete("/document/{doc_id}")
async def api_delete_document(doc_id: str, user: dict = Depends(require_editor)):
    """문서 삭제"""
    if not delete_document(user["username"], doc_id):
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    return {"success": True}


# ── 페이지별 번역 ──

@router.post("/translate/{doc_id}/page/{page_num}")
async def api_start_page_translation(
    doc_id: str,
    page_num: int,
    body: dict = Body(default={}),
    user: dict = Depends(get_current_user),
):
    """단일 페이지 번역 시작 → 202 Accepted (하위 호환)"""
    model = body.get("model")
    try:
        start_page_translation(user["username"], doc_id, str(page_num), model)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return JSONResponse(status_code=202, content={"status": "translating", "doc_id": doc_id, "page": page_num})


@router.post("/translate/{doc_id}/pages")
async def api_start_range_translation(
    doc_id: str,
    body: dict = Body(...),
    user: dict = Depends(get_current_user),
):
    """범위 번역 시작 (최대 5페이지) → 202 Accepted"""
    page_start = body.get("page_start")
    page_end = body.get("page_end")
    model = body.get("model")

    if page_start is None or page_end is None:
        raise HTTPException(status_code=400, detail="page_start, page_end 필수")
    if page_end < page_start:
        raise HTTPException(status_code=400, detail="page_end는 page_start 이상이어야 합니다")
    if page_end - page_start + 1 > 5:
        raise HTTPException(status_code=400, detail="최대 5페이지까지 범위 번역 가능합니다")

    pages_str = str(page_start) if page_start == page_end else f"{page_start}-{page_end}"
    try:
        start_page_translation(user["username"], doc_id, pages_str, model)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return JSONResponse(status_code=202, content={
        "status": "translating", "doc_id": doc_id,
        "page_start": page_start, "page_end": page_end,
    })


@router.get("/translate/{doc_id}/page/{page_num}/status")
async def api_page_translation_status(
    doc_id: str,
    page_num: int,
    user: dict = Depends(get_current_user),
):
    """페이지 번역 상태"""
    status = get_page_translation_status(user["username"], doc_id, page_num)
    if status is None:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    return status


@router.post("/translate/{doc_id}/page/{page_num}/cancel")
async def api_cancel_page_translation(
    doc_id: str,
    page_num: int,
    user: dict = Depends(get_current_user),
):
    """페이지 번역 취소"""
    if not cancel_page_translation(user["username"], doc_id, page_num):
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    return {"success": True, "status": "cancelled"}


@router.get("/translated-pdf/{doc_id}/page/{page_num}")
async def api_serve_page_translated_pdf(
    doc_id: str,
    page_num: int,
    user: dict = Depends(get_current_user),
):
    """페이지별 번역 PDF 서빙"""
    path = get_page_pdf_path(user["username"], doc_id, page_num)
    if not path:
        raise HTTPException(status_code=404, detail="번역 PDF가 없습니다")
    return FileResponse(path=str(path), media_type="application/pdf")


@router.get("/document/{doc_id}/pages")
async def api_doc_page_summary(doc_id: str, user: dict = Depends(get_current_user)):
    """전체 페이지 상태 요약"""
    summary = get_doc_page_summary(user["username"], doc_id)
    if not summary:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    return summary


# ── PDF 서빙 (원본 + 레거시) ──

@router.get("/pdf/{doc_id}")
async def api_serve_original_pdf(doc_id: str, user: dict = Depends(get_current_user)):
    """원본 PDF 서빙"""
    path = get_pdf_path(user["username"], doc_id, "original")
    if not path:
        raise HTTPException(status_code=404, detail="PDF 파일을 찾을 수 없습니다")
    return FileResponse(path=str(path), media_type="application/pdf")


@router.get("/translated-pdf/{doc_id}")
async def api_serve_translated_pdf(doc_id: str, user: dict = Depends(get_current_user)):
    """레거시 통번역 PDF 서빙"""
    path = get_pdf_path(user["username"], doc_id, "translated")
    if not path:
        raise HTTPException(status_code=404, detail="번역 PDF가 없습니다")
    return FileResponse(path=str(path), media_type="application/pdf")


@router.get("/dual-pdf/{doc_id}")
async def api_serve_dual_pdf(doc_id: str, user: dict = Depends(get_current_user)):
    """레거시 이중언어 PDF 서빙"""
    path = get_pdf_path(user["username"], doc_id, "dual")
    if not path:
        raise HTTPException(status_code=404, detail="이중언어 PDF가 없습니다")
    return FileResponse(path=str(path), media_type="application/pdf")


@router.get("/models")
async def api_list_models(user: dict = Depends(get_current_user)):
    """Ollama 사용 가능 모델 목록"""
    try:
        return get_ollama_models()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama 모델 목록 조회 실패: {e}")
