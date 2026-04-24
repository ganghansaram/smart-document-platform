"""
Help API — 도움말 콘텐츠 SSOT 노출 (Plan-38 §5)

도움말 단일 소스(SSOT) JSON을 정적으로 반환한다.
프론트엔드는 모달·툴팁·보고서 부록·가이드 페이지 4채널에서 동일 콘텐츠를 사용한다.
"""
import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/help", tags=["help"])

# 프로젝트 루트 / data / help
_HELP_DIR = Path(__file__).parent.parent.parent / "data" / "help"


def _load(name: str) -> dict:
    fp = _HELP_DIR / f"{name}.json"
    if not fp.exists():
        raise HTTPException(status_code=404, detail=f"help '{name}' not found")
    try:
        with open(fp, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.exception("help JSON 파싱 실패: %s", name)
        raise HTTPException(status_code=500, detail=f"help '{name}' parse error: {e}")


@router.get("/similarity")
async def get_similarity_help() -> dict:
    """유사도 검사 도움말 SSOT — Plan-38 §5.2."""
    return _load("similarity-help")
