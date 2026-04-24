"""
Translator API — PDF 업로드, 페이지별 번역, 문서 관리
"""
import asyncio

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Body, Request, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
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
    start_web_translation, get_web_translation_status,
    get_web_translated_md, get_web_page_boxes, cancel_web_translation,
    get_web_full_md,
    start_web_extraction, start_full_extraction,
    get_web_extraction_status, get_full_extraction_status,
    get_web_extracted_md, get_web_full_extracted_md,
    start_summary_generation, get_summary_status, get_summary, cancel_analysis,
    start_full_extraction,
    get_annotations, create_annotation, update_annotation, delete_annotation,
    ai_selection_query,
    search_documents,
    get_glossary, save_glossary,
    create_document_zip,
    build_mindmap_tree,
)
import config

router = APIRouter(prefix="/translator", tags=["translator"])


# ── Analytics 헬퍼 ──
def _record_translator_event(raw_request, user, event_type, metadata=None,
                             *, subsystem="translator", status=None):
    """Translator/Notebook 계측용. 실패가 비즈니스 로직 영향 주지 않도록 silent."""
    try:
        from services.analytics import record_event, get_client_ip
        record_event(event_type, get_client_ip(raw_request), metadata,
                     username=user["username"] if user else None,
                     subsystem=subsystem, status=status)
    except Exception:
        pass


# ── 검색 ──

@router.get("/search")
async def api_search_documents(
    q: str = "",
    source: str = "",
    user: dict = Depends(get_current_user),
):
    """유저 문서 검색 (본문 + 메모). source: "" (전체) | "source" (원문만) | "translated" (번역만)"""
    if not q.strip():
        return {"memos": [], "pages": [], "query": "", "total": 0}
    return search_documents(user["username"], q, source_filter=source or None)


# ── 용어집 ──

@router.get("/glossary")
async def api_get_glossary(user: dict = Depends(get_current_user)):
    """유저 용어집 조회"""
    return get_glossary(user["username"])


@router.put("/glossary")
async def api_save_glossary(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """유저 용어집 저장 (전체 교체)"""
    body = await request.json()
    return save_glossary(user["username"], body)


# ── 폴더 CRUD ──

@router.get("/folders")
async def api_list_folders(user: dict = Depends(get_current_user)):
    """폴더 목록"""
    return get_folders(user["username"])


@router.post("/folders")
async def api_create_folder(
    body: dict = Body(...),
    user: dict = Depends(get_current_user),
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
    user: dict = Depends(get_current_user),
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
    user: dict = Depends(get_current_user),
):
    """폴더 삭제 (하위 항목은 상위로 이동)"""
    if not delete_folder(user["username"], folder_id):
        raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다")
    return {"success": True}


@router.post("/document/{doc_id}/move")
async def api_move_document(
    doc_id: str,
    body: dict = Body(...),
    user: dict = Depends(get_current_user),
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
        # ai_selection_query는 sync requests.post를 사용하므로 to_thread로 이벤트 루프 블로킹 방지
        return await asyncio.to_thread(ai_selection_query, text, action, model)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI 서비스 오류: {e}")


# ── 업로드 ──

@router.post("/upload")
async def api_upload_pdf(
    raw_request: Request,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """PDF 업로드 → 즉시 응답"""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드할 수 있습니다")

    contents = await file.read()
    size = len(contents)
    if size > config.TRANSLATOR_MAX_PDF_SIZE:
        size_mb = size / 1024 / 1024
        max_mb = config.TRANSLATOR_MAX_PDF_SIZE / 1024 / 1024
        _record_translator_event(
            raw_request, user, "upload",
            {"filename": file.filename, "size": size, "ext": "pdf"},
            status="error",
        )
        raise HTTPException(
            status_code=400,
            detail=f"파일 크기 초과: {size_mb:.1f}MB (최대 {max_mb:.0f}MB)",
        )

    meta = upload_pdf(contents, file.filename, user["username"])
    _record_translator_event(
        raw_request, user, "upload",
        {"filename": file.filename, "size": size, "ext": "pdf"},
        status="ok",
    )
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
async def api_delete_document(doc_id: str, user: dict = Depends(get_current_user)):
    """문서 삭제"""
    if not delete_document(user["username"], doc_id):
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    return {"success": True}


@router.put("/document/{doc_id}")
async def api_rename_document(
    doc_id: str,
    body: dict = Body(...),
    user: dict = Depends(get_current_user),
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
    raw_request: Request,
    body: dict = Body(default={}),
    user: dict = Depends(get_current_user),
):
    """단일 페이지 번역 시작 → 202 Accepted (하위 호환)"""
    model = body.get("model")
    meta_ev = {"doc_id": doc_id, "pages": [page_num], "engine": "pmt"}
    try:
        start_page_translation(user["username"], doc_id, str(page_num), model)
    except FileNotFoundError:
        _record_translator_event(raw_request, user, "translate", meta_ev, status="error")
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    except ValueError as e:
        _record_translator_event(raw_request, user, "translate", meta_ev, status="error")
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        _record_translator_event(raw_request, user, "translate", meta_ev, status="error")
        raise HTTPException(status_code=409, detail=str(e))
    _record_translator_event(raw_request, user, "translate", meta_ev, status="started")
    return JSONResponse(status_code=202, content={"status": "translating", "doc_id": doc_id, "page": page_num})


@router.post("/translate/{doc_id}/pages")
async def api_start_range_translation(
    doc_id: str,
    raw_request: Request,
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
    meta_ev = {"doc_id": doc_id, "pages": list(range(page_start, page_end + 1)), "engine": "pmt"}
    try:
        start_page_translation(user["username"], doc_id, pages_str, model)
    except FileNotFoundError:
        _record_translator_event(raw_request, user, "translate", meta_ev, status="error")
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    except ValueError as e:
        _record_translator_event(raw_request, user, "translate", meta_ev, status="error")
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        _record_translator_event(raw_request, user, "translate", meta_ev, status="error")
        raise HTTPException(status_code=409, detail=str(e))
    _record_translator_event(raw_request, user, "translate", meta_ev, status="started")
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


# ── ZIP 다운로드 ──

@router.get("/document/{doc_id}/download/zip")
async def api_download_zip(
    doc_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """문서의 MD + assets를 ZIP으로 다운로드"""
    import os
    zip_path = create_document_zip(user["username"], doc_id)
    if not zip_path:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")

    meta = get_document(user["username"], doc_id)
    title = (meta or {}).get("title", doc_id)
    filename = f"{title}.zip"

    # 응답 후 임시 파일 삭제
    background_tasks.add_task(os.unlink, str(zip_path))
    return FileResponse(
        path=str(zip_path),
        media_type="application/zip",
        filename=filename,
    )


# ── 웹 뷰 번역 (Markdown) ──

@router.post("/web-translate/{doc_id}/page/{page_num}")
async def api_start_web_translation(
    doc_id: str,
    page_num: int,
    raw_request: Request,
    body: dict = Body(default={}),
    user: dict = Depends(get_current_user),
):
    """웹 뷰 번역 시작 (추출+번역 일괄) → 202 Accepted"""
    model = body.get("model")
    meta_ev = {"doc_id": doc_id, "pages": [page_num], "engine": "web"}
    try:
        start_web_translation(user["username"], doc_id, page_num, model)
    except FileNotFoundError:
        _record_translator_event(raw_request, user, "translate", meta_ev, status="error")
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    except ValueError as e:
        _record_translator_event(raw_request, user, "translate", meta_ev, status="error")
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        _record_translator_event(raw_request, user, "translate", meta_ev, status="error")
        raise HTTPException(status_code=409, detail=str(e))
    _record_translator_event(raw_request, user, "translate", meta_ev, status="started")
    return JSONResponse(
        status_code=202,
        content={"status": "translating", "doc_id": doc_id, "page": page_num, "mode": "web"},
    )


@router.get("/web-translate/{doc_id}/page/{page_num}/status")
async def api_web_translation_status(
    doc_id: str,
    page_num: int,
    user: dict = Depends(get_current_user),
):
    """웹 뷰 번역 상태"""
    status = get_web_translation_status(user["username"], doc_id, page_num)
    if status is None:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    return status


@router.post("/web-translate/{doc_id}/page/{page_num}/cancel")
async def api_cancel_web_translation(
    doc_id: str,
    page_num: int,
    user: dict = Depends(get_current_user),
):
    """웹 뷰 번역 취소"""
    cancel_web_translation(user["username"], doc_id, page_num)
    return {"success": True, "status": "cancelled"}


# ── 추출 전용 (번역 없이 MD 추출) ──

@router.post("/extract/{doc_id}")
async def api_start_extraction(
    doc_id: str,
    body: dict = Body(default={}),
    user: dict = Depends(get_current_user),
):
    """전체 또는 지정 페이지 MD 추출 시작 → 202 Accepted"""
    pages = body.get("pages", "all")
    try:
        if pages == "all":
            started = await start_full_extraction(user["username"], doc_id)
        else:
            started = 0
            for p in pages:
                start_web_extraction(user["username"], doc_id, int(p))
                started += 1
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return JSONResponse(
        status_code=202,
        content={"status": "extracting", "doc_id": doc_id, "started_pages": started},
    )


@router.get("/extract/{doc_id}/status")
async def api_extraction_status(
    doc_id: str,
    user: dict = Depends(get_current_user),
):
    """전체 문서 추출 진행 상태"""
    status = get_full_extraction_status(user["username"], doc_id)
    if status is None:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    return status


@router.get("/extracted-view/{doc_id}/page/{page_num}")
async def api_serve_extracted_view(
    doc_id: str,
    page_num: int,
    user: dict = Depends(get_current_user),
):
    """추출된 원문 Markdown 서빙"""
    md = get_web_extracted_md(user["username"], doc_id, page_num)
    if md is None:
        raise HTTPException(status_code=404, detail="추출된 Markdown이 없습니다")
    boxes = get_web_page_boxes(user["username"], doc_id, page_num)
    return {"markdown": md, "page_boxes": boxes}


@router.get("/extracted-view/{doc_id}/full")
async def api_serve_extracted_view_full(
    doc_id: str,
    user: dict = Depends(get_current_user),
):
    """전체 문서 추출 병합 Markdown 서빙"""
    result = get_web_full_extracted_md(user["username"], doc_id)
    if result is None:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    return result


# ── AI 요약 ──

@router.post("/document/{doc_id}/summary")
async def api_generate_summary(
    doc_id: str,
    raw_request: Request,
    body: dict = Body(default={}),
    user: dict = Depends(get_current_user),
):
    """AI 요약 생성 시작 (또는 기존 요약 반환)"""
    force = body.get("force", False)
    try:
        result = start_summary_generation(user["username"], doc_id, force=force)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if result == "exists":
        summary = get_summary(user["username"], doc_id)
        _record_translator_event(raw_request, user, "summarize",
                                 {"doc_id": doc_id, "mode": "cached"}, status="ok")
        return {"status": "exists", "summary": summary}

    _record_translator_event(raw_request, user, "summarize",
                             {"doc_id": doc_id, "mode": "generate"}, status="started")
    return JSONResponse(
        status_code=202,
        content={"status": "generating", "doc_id": doc_id},
    )


@router.get("/document/{doc_id}/summary")
async def api_get_summary(
    doc_id: str,
    user: dict = Depends(get_current_user),
):
    """AI 요약 조회 (상태 + 데이터)"""
    status = get_summary_status(user["username"], doc_id)
    if status is None:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")

    if status.get("status") == "done":
        summary = get_summary(user["username"], doc_id)
        return {"status": "done", "summary": summary}

    return status


@router.post("/document/{doc_id}/analysis/cancel")
async def api_cancel_analysis(
    doc_id: str,
    user: dict = Depends(get_current_user),
):
    """문서 분석(추출+요약) 취소"""
    cancelled = await cancel_analysis(user["username"], doc_id)
    return {"cancelled": cancelled}


# ── 마인드맵 ──

@router.get("/document/{doc_id}/mindmap")
async def api_mindmap(doc_id: str, user: dict = Depends(get_current_user)):
    """문서의 마인드맵 트리 데이터 반환 (Markmap INode 호환)"""
    try:
        return build_mindmap_tree(user["username"], doc_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")


# ── Q&A 챗봇 ──

class NotebookChatRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None


@router.post("/document/{doc_id}/chat/stream")
async def api_document_chat_stream(
    doc_id: str,
    request: NotebookChatRequest,
    raw_request: Request,
    user: dict = Depends(get_current_user),
):
    """문서 Q&A 스트리밍 (NDJSON). Explorer chat/stream과 동일 포맷."""
    import json as _json
    from services.notebook_chat import ask_document_stream
    from services.conversation import store as conversation_store

    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="질문이 비어있습니다")

    _record_translator_event(
        raw_request, user, "chat",
        {"doc_id": doc_id},
        subsystem="notebook", status="started",
    )

    conversation_id = request.conversation_id

    try:
        token_iter, source_type, model_name, session_id, source_pages = await ask_document_stream(
            user["username"], doc_id, question, conversation_id
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")

    async def event_generator():
        full_answer = []
        try:
            async for token in token_iter:
                full_answer.append(token)
                yield _json.dumps({"type": "token", "content": token}, ensure_ascii=False) + "\n"

            answer_text = "".join(full_answer)

            # 어시스턴트 응답 대화 기록 저장
            session = conversation_store.get_session(session_id)
            if session:
                session.add_message("assistant", answer_text)

            yield _json.dumps({
                "type": "done",
                "source_type": source_type,
                "model": model_name,
                "conversation_id": session_id,
                "source_pages": source_pages,
            }, ensure_ascii=False) + "\n"

        except Exception as e:
            logger.error("Q&A 스트리밍 오류: %s", e, exc_info=True)
            yield _json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


@router.get("/web-view/{doc_id}/full")
async def api_serve_web_view_full(
    doc_id: str,
    user: dict = Depends(get_current_user),
):
    """전체 문서 병합 Markdown 서빙"""
    result = get_web_full_md(user["username"], doc_id)
    if result is None:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    return result


@router.get("/web-view/{doc_id}/page/{page_num}")
async def api_serve_web_view(
    doc_id: str,
    page_num: int,
    user: dict = Depends(get_current_user),
):
    """페이지 번역 Markdown 서빙"""
    md = get_web_translated_md(user["username"], doc_id, page_num)
    if md is None:
        raise HTTPException(status_code=404, detail="웹 뷰 번역이 없습니다")
    boxes = get_web_page_boxes(user["username"], doc_id, page_num)
    return {"markdown": md, "page_boxes": boxes}


@router.get("/web-view/{doc_id}/page/{page_num}/assets/{filename}")
async def api_serve_web_asset(
    doc_id: str,
    page_num: int,
    filename: str,
    user: dict = Depends(get_current_user),
):
    """웹 뷰 이미지 자산 서빙"""
    from pathlib import Path
    assets_dir = Path(config.TRANSLATOR_DATA_DIR) / user["username"] / doc_id / "pages" / str(page_num) / "assets"
    file_path = assets_dir / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다")
    # 경로 탈출 방지
    if not file_path.resolve().is_relative_to(assets_dir.resolve()):
        raise HTTPException(status_code=403, detail="접근 거부")
    media_type = "image/png" if filename.endswith(".png") else "image/jpeg"
    return FileResponse(path=str(file_path), media_type=media_type)


@router.put("/web-view/{doc_id}/page/{page_num}")
async def api_save_web_view(
    doc_id: str,
    page_num: int,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Markdown 편집 저장"""
    data = await request.json()
    markdown = data.get("markdown", "")
    if not markdown:
        raise HTTPException(status_code=400, detail="markdown 내용이 비어있습니다")

    from pathlib import Path
    md_path = Path(config.TRANSLATOR_DATA_DIR) / user["username"] / doc_id / "pages" / str(page_num) / "web_translated.md"
    if not md_path.parent.exists():
        raise HTTPException(status_code=404, detail="문서 페이지를 찾을 수 없습니다")
    md_path.write_text(markdown, encoding="utf-8")

    # full_translated.md 재병합
    from services.translator_service import _load_meta, _doc_dir
    from services.md_translator import merge_full_translated
    meta = _load_meta(user["username"], doc_id)
    if meta:
        doc_dir = _doc_dir(user["username"], doc_id)
        merge_full_translated(doc_dir, meta.get("pages", 0), meta.get("title", ""))

    return {"success": True}


@router.get("/models")
async def api_list_models(user: dict = Depends(get_current_user)):
    """Ollama 사용 가능 모델 목록"""
    try:
        return await get_ollama_models()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama 모델 목록 조회 실패: {e}")
