"""
Compare API — 문서 업로드, 텍스트 추출, 검증
"""
import os

from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, Request

from dependencies import get_current_user
from services.compare_service import (
    extract_text,
    validate_paragraphs,
    load_rules,
    save_rules,
)

router = APIRouter(prefix="/compare", tags=["compare"])

ALLOWED_EXTENSIONS = {".docx", ".pdf"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@router.post("/upload")
async def api_compare_upload(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """문서 업로드 → 텍스트 추출 (파일 저장 없음)"""
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 형식입니다. 허용: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    contents = await file.read()

    if len(contents) > MAX_FILE_SIZE:
        size_mb = len(contents) / 1024 / 1024
        raise HTTPException(
            status_code=400,
            detail=f"파일 크기 초과: {size_mb:.1f}MB (최대 50MB)",
        )

    try:
        result = extract_text(contents, ext)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"텍스트 추출 실패: {e}")

    return {
        "filename": filename,
        "format": ext.lstrip("."),
        "paragraphs": result["paragraphs"],
        "page_count": result["page_count"],
    }


@router.post("/validate")
async def api_compare_validate(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """단락 배열 → 규칙 기반 검증 → 이슈 목록"""
    body = await request.json()
    paragraphs = body.get("paragraphs", [])
    preset = body.get("preset")

    if not paragraphs:
        raise HTTPException(status_code=400, detail="paragraphs가 비어 있습니다")

    result = validate_paragraphs(paragraphs, preset)
    return result


@router.get("/rules")
async def api_compare_rules_get(
    user: dict = Depends(get_current_user),
):
    """현재 규칙 설정 반환"""
    return load_rules()


@router.put("/rules")
async def api_compare_rules_put(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """규칙 설정 저장"""
    body = await request.json()
    save_rules(body)
    return {"ok": True}
