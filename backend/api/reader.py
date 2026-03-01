"""
Reader API — PDF 업로드, 번역, 문서 관리
"""
import json
import asyncio
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Body
from fastapi.responses import StreamingResponse, FileResponse
from typing import Optional

from dependencies import get_current_user, require_editor
from services.reader_service import (
    parse_pdf, translate_document, get_documents, get_document, delete_document,
    get_pdf_path,
)
import config

router = APIRouter(prefix="/reader", tags=["reader"])

STREAM_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Content-Type-Options": "nosniff",
}


def _ndjson_line(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False) + "\n"


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    user: dict = Depends(require_editor),
):
    """PDF 업로드 → 파싱 (NDJSON 스트리밍)"""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드할 수 있습니다")

    contents = await file.read()
    if len(contents) > config.READER_MAX_PDF_SIZE:
        size_mb = len(contents) / 1024 / 1024
        max_mb = config.READER_MAX_PDF_SIZE / 1024 / 1024
        raise HTTPException(
            status_code=400,
            detail=f"파일 크기 초과: {size_mb:.1f}MB (최대 {max_mb:.0f}MB)",
        )

    async def _stream():
        gen = parse_pdf(contents, file.filename)
        for event in gen:
            yield _ndjson_line(event)

    return StreamingResponse(
        _stream(),
        media_type="text/plain; charset=utf-8",
        headers=STREAM_HEADERS,
    )


@router.post("/translate")
async def translate(
    body: dict = Body(...),
    user: dict = Depends(get_current_user),
):
    """문단 번역 (NDJSON 스트리밍)

    body: { "document_id": str, "paragraph_ids": [int] | null }
    """
    doc_id = body.get("document_id")
    if not doc_id:
        raise HTTPException(status_code=400, detail="document_id 필수")

    paragraph_ids = body.get("paragraph_ids")  # None → 미번역 전체

    async def _stream():
        gen = translate_document(doc_id, paragraph_ids)
        for event in gen:
            yield _ndjson_line(event)
            # 번역은 CPU-bound이므로 이벤트 루프에 양보
            await asyncio.sleep(0)

    return StreamingResponse(
        _stream(),
        media_type="text/plain; charset=utf-8",
        headers=STREAM_HEADERS,
    )


@router.get("/documents")
async def list_documents(user: dict = Depends(get_current_user)):
    """업로드된 문서 목록"""
    return get_documents()


@router.get("/document/{doc_id}")
async def read_document(doc_id: str, user: dict = Depends(get_current_user)):
    """문서 상세 (원문 + 번역)"""
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    return doc


@router.get("/pdf/{doc_id}")
async def serve_pdf(doc_id: str, user: dict = Depends(get_current_user)):
    """PDF 원본 바이너리 서빙"""
    path = get_pdf_path(doc_id)
    if not path:
        raise HTTPException(status_code=404, detail="PDF 파일을 찾을 수 없습니다")
    return FileResponse(path=str(path), media_type="application/pdf")


@router.delete("/document/{doc_id}")
async def remove_document(doc_id: str, user: dict = Depends(require_editor)):
    """문서 삭제"""
    if not delete_document(doc_id):
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    return {"success": True}
