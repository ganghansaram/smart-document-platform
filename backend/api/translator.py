"""
Translator API — PDF 업로드, 페이지별 번역, 문서 관리
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Body
from fastapi.responses import FileResponse, JSONResponse
from typing import Optional

from dependencies import get_current_user, require_editor
from services.translator_service import (
    upload_pdf, get_documents, get_document, delete_document, rename_document,
    get_pdf_path, get_page_pdf_path,
    start_page_translation, get_page_translation_status,
    cancel_page_translation, get_doc_page_summary,
    get_ollama_models,
    get_folders, create_folder, rename_folder, delete_folder,
    move_document_to_folder,
    start_text_translation, get_text_translation_status,
    get_text_translated_pdf_path, cancel_text_translation,
    get_annotations, create_annotation, update_annotation, delete_annotation,
    ai_selection_query,
)
import config

router = APIRouter(prefix="/translator", tags=["translator"])


# ── 폴더 CRUD ──

@router.get("/folders")
async def api_list_folders(user: dict = Depends(get_current_user)):
    """폴더 목록"""
    return get_folders(user["username"])


@router.post("/folders")
async def api_create_folder(
    body: dict = Body(...),
    user: dict = Depends(require_editor),
):
    """폴더 생성"""
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="폴더 이름이 필요합니다")
    parent_id = body.get("parent_id")
    try:
        return create_folder(user["username"], name, parent_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/folders/{folder_id}")
async def api_rename_folder(
    folder_id: str,
    body: dict = Body(...),
    user: dict = Depends(require_editor),
):
    """폴더 이름 변경"""
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="폴더 이름이 필요합니다")
    try:
        return rename_folder(user["username"], folder_id, name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다")


@router.delete("/folders/{folder_id}")
async def api_delete_folder(
    folder_id: str,
    user: dict = Depends(require_editor),
):
    """폴더 삭제 (하위 항목은 상위로 이동)"""
    if not delete_folder(user["username"], folder_id):
        raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다")
    return {"success": True}


@router.post("/document/{doc_id}/move")
async def api_move_document(
    doc_id: str,
    body: dict = Body(...),
    user: dict = Depends(require_editor),
):
    """문서를 폴더로 이동 (folder_id=null → 루트)"""
    folder_id = body.get("folder_id")
    try:
        if not move_document_to_folder(user["username"], doc_id, folder_id):
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"success": True}


# ── 마킹 (annotations) CRUD ──

@router.get("/document/{doc_id}/annotations")
async def api_get_annotations(doc_id: str, user: dict = Depends(get_current_user)):
    """문서의 전체 마킹 목록"""
    try:
        return get_annotations(user["username"], doc_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")


@router.post("/document/{doc_id}/annotations")
async def api_create_annotation(
    doc_id: str,
    body: dict = Body(...),
    user: dict = Depends(get_current_user),
):
    """마킹 생성"""
    if "page" not in body or "rects" not in body:
        raise HTTPException(status_code=400, detail="page, rects 필수")
    try:
        return create_annotation(user["username"], doc_id, body)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")


@router.put("/document/{doc_id}/annotations/{ann_id}")
async def api_update_annotation(
    doc_id: str,
    ann_id: str,
    body: dict = Body(...),
    user: dict = Depends(get_current_user),
):
    """마킹 수정 (memo, color)"""
    try:
        return update_annotation(user["username"], doc_id, ann_id, body)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/document/{doc_id}/annotations/{ann_id}")
async def api_delete_annotation(
    doc_id: str,
    ann_id: str,
    user: dict = Depends(get_current_user),
):
    """마킹 삭제"""
    try:
        delete_annotation(user["username"], doc_id, ann_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"success": True}


# ── AI 선택 번역/요약 ──

@router.post("/ai/selection")
async def api_ai_selection(
    body: dict = Body(...),
    user: dict = Depends(get_current_user),
):
    """선택 텍스트 번역/요약"""
    text = (body.get("text") or "").strip()
    action = body.get("action", "")
    model = body.get("model")

    if not text:
        raise HTTPException(status_code=400, detail="텍스트가 비어있습니다")
    if len(text) > 3000:
        text = text[:3000]
    if action not in ("translate", "summarize"):
        raise HTTPException(status_code=400, detail="action은 translate 또는 summarize")

    try:
        return ai_selection_query(text, action, model)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI 서비스 오류: {e}")


# ── 업로드 ──

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


@router.put("/document/{doc_id}")
async def api_rename_document(
    doc_id: str,
    body: dict = Body(...),
    user: dict = Depends(require_editor),
):
    """문서 제목 변경"""
    title = body.get("title", "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="제목이 필요합니다")
    if not rename_document(user["username"], doc_id, title):
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


# ── 텍스트 번역 (폴백 엔진) ──

@router.post("/text-translate/{doc_id}/page/{page_num}")
async def api_start_text_translation(
    doc_id: str,
    page_num: int,
    body: dict = Body(default={}),
    user: dict = Depends(get_current_user),
):
    """텍스트 번역 시작 → 202 Accepted"""
    model = body.get("model")
    font_scale = body.get("font_scale")
    try:
        start_text_translation(user["username"], doc_id, page_num, model, font_scale)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return JSONResponse(
        status_code=202,
        content={"status": "translating", "doc_id": doc_id, "page": page_num, "mode": "text"},
    )


@router.get("/text-translate/{doc_id}/page/{page_num}/status")
async def api_text_translation_status(
    doc_id: str,
    page_num: int,
    user: dict = Depends(get_current_user),
):
    """텍스트 번역 상태"""
    status = get_text_translation_status(user["username"], doc_id, page_num)
    if status is None:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    return status


@router.get("/text-translated-pdf/{doc_id}/page/{page_num}")
async def api_serve_text_translated_pdf(
    doc_id: str,
    page_num: int,
    user: dict = Depends(get_current_user),
):
    """텍스트 번역 PDF 서빙"""
    path = get_text_translated_pdf_path(user["username"], doc_id, page_num)
    if not path:
        raise HTTPException(status_code=404, detail="텍스트 번역 PDF가 없습니다")
    return FileResponse(path=str(path), media_type="application/pdf")


@router.post("/text-translate/{doc_id}/page/{page_num}/cancel")
async def api_cancel_text_translation(
    doc_id: str,
    page_num: int,
    user: dict = Depends(get_current_user),
):
    """텍스트 번역 취소"""
    cancel_text_translation(user["username"], doc_id, page_num)
    return {"success": True, "status": "cancelled"}


@router.get("/models")
async def api_list_models(user: dict = Depends(get_current_user)):
    """Ollama 사용 가능 모델 목록"""
    try:
        return get_ollama_models()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama 모델 목록 조회 실패: {e}")
