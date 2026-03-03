"""
Translator API — PDF 업로드, PMT 번역, 문서 관리
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Body
from fastapi.responses import FileResponse, JSONResponse
from typing import Optional

from dependencies import get_current_user, require_editor
from services.translator_service import (
    upload_pdf, get_documents, get_document, delete_document,
    get_pdf_path, start_translation, get_translation_status,
    retranslate, cancel_translation, get_ollama_models,
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


@router.post("/translate/{doc_id}")
async def api_start_translation(
    doc_id: str,
    body: dict = Body(default={}),
    user: dict = Depends(get_current_user),
):
    """번역 시작 → 202 Accepted"""
    model = body.get("model")
    try:
        start_translation(user["username"], doc_id, model)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    return JSONResponse(status_code=202, content={"status": "translating", "doc_id": doc_id})


@router.get("/translate/{doc_id}/status")
async def api_translation_status(doc_id: str, user: dict = Depends(get_current_user)):
    """번역 진행 상태"""
    status = get_translation_status(user["username"], doc_id)
    if not status:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    return status


@router.post("/translate/{doc_id}/cancel")
async def api_cancel_translation(doc_id: str, user: dict = Depends(get_current_user)):
    """번역 취소"""
    if not cancel_translation(user["username"], doc_id):
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    return {"success": True, "status": "pending"}


@router.post("/retranslate/{doc_id}")
async def api_retranslate(
    doc_id: str,
    body: dict = Body(default={}),
    user: dict = Depends(get_current_user),
):
    """재번역 → 202 Accepted"""
    model = body.get("model")
    try:
        retranslate(user["username"], doc_id, model)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    return JSONResponse(status_code=202, content={"status": "translating", "doc_id": doc_id})


@router.get("/pdf/{doc_id}")
async def api_serve_original_pdf(doc_id: str, user: dict = Depends(get_current_user)):
    """원본 PDF 서빙"""
    path = get_pdf_path(user["username"], doc_id, "original")
    if not path:
        raise HTTPException(status_code=404, detail="PDF 파일을 찾을 수 없습니다")
    return FileResponse(path=str(path), media_type="application/pdf")


@router.get("/translated-pdf/{doc_id}")
async def api_serve_translated_pdf(doc_id: str, user: dict = Depends(get_current_user)):
    """번역 PDF 서빙"""
    path = get_pdf_path(user["username"], doc_id, "translated")
    if not path:
        raise HTTPException(status_code=404, detail="번역 PDF가 없습니다")
    return FileResponse(path=str(path), media_type="application/pdf")


@router.get("/dual-pdf/{doc_id}")
async def api_serve_dual_pdf(doc_id: str, user: dict = Depends(get_current_user)):
    """이중언어 PDF 서빙"""
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
