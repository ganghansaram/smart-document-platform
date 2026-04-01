"""
Compare API — 문서 업로드, 텍스트 추출, 검증, AI 의미 분류, 유사도 검사
"""
import logging
import os

from fastapi import APIRouter, File, Form, UploadFile, Depends, HTTPException, Request
from typing import Optional

import config

logger = logging.getLogger(__name__)
from dependencies import get_current_user, require_admin
from services.compare_service import (
    extract_text,
    validate_paragraphs,
    load_rules,
    save_rules,
    classify_changes,
)
from services.document_extractor import extract_document
from services.similarity_engine import run_similarity

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
    user: dict = Depends(require_admin),
):
    """규칙 설정 저장 (관리자 전용)"""
    body = await request.json()
    save_rules(body)
    return {"ok": True}


@router.post("/ai-classify")
async def api_compare_ai_classify(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """diff 변경 구간 AI 의미 분류"""
    if not getattr(config, "COMPARE_AI_ENABLED", True):
        raise HTTPException(status_code=400, detail="AI 분석이 비활성화되어 있습니다")

    body = await request.json()
    changes = body.get("changes", [])

    if not changes:
        raise HTTPException(status_code=400, detail="changes가 비어 있습니다")

    if len(changes) > 200:
        raise HTTPException(status_code=400, detail="변경 구간이 너무 많습니다 (최대 200건)")

    try:
        classifications = await classify_changes(changes)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"AI 분류 실패: {e}",
        )

    return {"classifications": classifications}


# ══════════════════════════════════════════
# 유사도 모드 — 문서 추출 (듀얼 포맷)
# ══════════════════════════════════════════

@router.post("/extract-document")
async def api_extract_document(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    user: dict = Depends(get_current_user),
):
    """문서 추출 → 듀얼 포맷 (MD + plain text) 반환

    입력: 파일 업로드 또는 텍스트 붙여넣기 (둘 중 하나)
    스캔 PDF는 OCR 자동 폴백.
    """
    if file is None and text is None:
        raise HTTPException(status_code=400, detail="파일 또는 텍스트를 입력하세요")

    if file is not None and text is not None:
        raise HTTPException(status_code=400, detail="파일과 텍스트 중 하나만 입력하세요")

    if text is not None:
        result = extract_document(text=text)
        return {
            "filename": "(텍스트 붙여넣기)",
            "markdown": result["markdown"],
            "plain_text": result["plain_text"],
            "page_count": result["page_count"],
            "is_scanned": result["is_scanned"],
        }

    # 파일 업로드
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
        result = extract_document(file_bytes=contents, ext=ext)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"문서 추출 실패: {e}")

    return {
        "filename": filename,
        "markdown": result["markdown"],
        "plain_text": result["plain_text"],
        "page_count": result["page_count"],
        "is_scanned": result["is_scanned"],
    }


# ══════════════════════════════════════════
# 유사도 모드 — 유사도 검사 실행
# ══════════════════════════════════════════

@router.post("/similarity")
async def api_similarity(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """두 문서의 유사도를 비교한다.

    입력 (JSON):
        target_text: 검사 대상 plain text
        reference_text: 참조 원문 plain text
        threshold_high: 높은 유사 임계값 (선택, 기본 0.85)
        threshold_medium: 중간 유사 임계값 (선택, 기본 0.70)
    """
    body = await request.json()
    target_text = body.get("target_text", "")
    reference_text = body.get("reference_text", "")

    if not target_text.strip():
        raise HTTPException(status_code=400, detail="검사 대상 텍스트가 비어 있습니다")
    if not reference_text.strip():
        raise HTTPException(status_code=400, detail="참조 원문 텍스트가 비어 있습니다")

    threshold_high = body.get("threshold_high")
    threshold_medium = body.get("threshold_medium")

    try:
        result = run_similarity(
            target_text=target_text,
            reference_text=reference_text,
            threshold_high=threshold_high,
            threshold_medium=threshold_medium,
        )
    except Exception as e:
        logger.exception("유사도 검사 실패")
        raise HTTPException(status_code=502, detail=f"유사도 검사 실패: {e}")

    return result
