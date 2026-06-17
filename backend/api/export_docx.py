"""
통일 양식 DOCX 내보내기 API (Plan-60 Phase 3a)

⚠️ 기존 `POST /api/export` (compare.py) 는 Verify/Compare 의 **Excel(.xlsx)** 내보내기로
별개다. 본 라우트는 저작 마크다운 → 통일 양식 **DOCX** 전용: `POST /api/export-docx`.
"""
import asyncio
import logging
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from pydantic import BaseModel

from dependencies import require_editor

router = APIRouter(tags=["export-docx"])
logger = logging.getLogger(__name__)

DOCX_MEDIA = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class ExportDocxRequest(BaseModel):
    md: str
    filename: Optional[str] = None
    with_cover: bool = True


def _safe_filename(name: Optional[str]) -> str:
    """다운로드 파일명 정제 (헤더 인젝션 방지 + .docx 보장)."""
    name = (name or "").replace("\r", "").replace("\n", "").replace('"', "").strip()
    if not name:
        name = "document"
    if not name.lower().endswith(".docx"):
        name += ".docx"
    return name


@router.post("/export-docx")
async def api_export_docx(body: ExportDocxRequest, user: dict = Depends(require_editor)):
    """저작 마크다운을 통일 양식 DOCX로 내보낸다 (MD→HTML→DOCX 2단계 + 표지 주입)."""
    if not body.md or not body.md.strip():
        raise HTTPException(status_code=400, detail="내보낼 마크다운 내용이 비어 있습니다.")

    from services.docx_export_service import export_markdown_to_docx, ExportError
    try:
        data = await asyncio.to_thread(
            export_markdown_to_docx, body.md, with_cover=body.with_cover
        )
    except ExportError as e:
        logger.warning("DOCX 내보내기 실패: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("DOCX 내보내기 오류")
        raise HTTPException(status_code=500, detail=f"내보내기 실패: {e}")

    filename = _safe_filename(body.filename)
    # 구버전 클라이언트용 ASCII 폴백: 한글 등 비-ASCII 만 있으면 stem 이 사라지므로 기본명 사용
    ascii_stem = filename[:-5].encode("ascii", "ignore").decode().strip()
    ascii_fallback = f"{ascii_stem}.docx" if ascii_stem else "document.docx"
    disposition = (
        f'attachment; filename="{ascii_fallback}"; '
        f"filename*=UTF-8''{quote(filename)}"
    )
    return Response(content=data, media_type=DOCX_MEDIA,
                    headers={"Content-Disposition": disposition})
