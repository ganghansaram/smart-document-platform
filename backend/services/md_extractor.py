"""
PDF → Markdown 추출 모듈 (PyMuPDF4LLM 기반)

Plan 17 Phase 1: PDF 페이지를 Markdown + 이미지로 추출한다.
원문 Markdown은 번역 파이프라인(Phase 2)의 입력으로 사용되며,
번역 완료 후 translated.md만 최종 저장된다.

사용법:
    result = extract_page(pdf_path, page_num=3, assets_dir=Path("pages/3/assets"))
    # result["markdown"]  — 추출된 Markdown 텍스트
    # result["page_boxes"] — 블록별 bbox 좌표 (클릭 네비게이션용)
    # result["assets"]    — 추출된 이미지 파일 목록
"""

import logging
from pathlib import Path
from typing import Optional

import config

logger = logging.getLogger(__name__)


def extract_page(
    pdf_path: Path,
    page_num: int,
    assets_dir: Optional[Path] = None,
) -> dict:
    """단일 PDF 페이지를 Markdown으로 추출한다.

    Args:
        pdf_path: 원본 PDF 경로
        page_num: 1-based 페이지 번호
        assets_dir: 이미지 저장 디렉토리 (None이면 이미지 추출 안 함)

    Returns:
        {
            "markdown": str,           # 추출된 Markdown 텍스트
            "page_boxes": list[dict],  # 블록별 좌표 [{index, class, bbox, pos}, ...]
            "assets": list[str],       # 저장된 이미지 파일명 목록
            "metadata": dict,          # 페이지 메타데이터
        }
    """
    import pymupdf4llm

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")

    # 설정 읽기
    table_mode = getattr(config, "TRANSLATOR_WEB_TABLE_MODE", "extract")
    table_strategy = getattr(config, "TRANSLATOR_WEB_TABLE_STRATEGY", "lines_strict")
    image_dpi = getattr(config, "TRANSLATOR_WEB_IMAGE_DPI", 150)
    debug = getattr(config, "TRANSLATOR_WEB_DEBUG", False)

    # 페이지 번호 변환 (1-based → 0-based for pymupdf4llm)
    page_index = page_num - 1

    # 총 페이지 수 확인
    import fitz
    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)
    doc.close()

    if page_index < 0 or page_index >= total_pages:
        raise ValueError(f"유효하지 않은 페이지 번호: {page_num} (1~{total_pages})")

    # 이미지 추출 설정
    write_images = assets_dir is not None
    if write_images:
        assets_dir = Path(assets_dir)
        assets_dir.mkdir(parents=True, exist_ok=True)

    # PyMuPDF4LLM 추출
    kwargs = {
        "pages": [page_index],
        "page_chunks": True,
        "table_strategy": table_strategy if table_mode == "extract" else "text",
    }

    if write_images:
        kwargs["write_images"] = True
        kwargs["image_path"] = str(assets_dir)
        kwargs["image_format"] = "png"
        kwargs["dpi"] = image_dpi

    logger.info(f"PDF→Markdown 추출 시작: p{page_num}, table_mode={table_mode}")

    chunks = pymupdf4llm.to_markdown(str(pdf_path), **kwargs)

    if not chunks:
        raise ValueError(f"페이지 {page_num} 추출 결과가 비어있습니다")

    chunk = chunks[0]
    markdown_text = chunk.get("text", "")
    page_boxes = chunk.get("page_boxes", [])
    metadata = chunk.get("metadata", {})

    # 표 모드별 후처리
    if table_mode == "image":
        # "image" 모드: Markdown 테이블 구문을 제거하고 원본 이미지만 유지
        # (pymupdf4llm이 표 영역도 이미지로 추출하므로, 텍스트 테이블만 제거)
        markdown_text = _remove_markdown_tables(markdown_text)
        logger.info("table_mode=image: Markdown 테이블 구문 제거, 이미지만 유지")
    elif table_mode == "off":
        markdown_text = _remove_markdown_tables(markdown_text)

    # 추출된 이미지 파일 목록 수집
    assets = []
    if write_images and assets_dir.exists():
        assets = sorted([f.name for f in assets_dir.iterdir() if f.is_file()])

    # 디버그 모드: 추출 원문을 파일로 저장
    if debug and assets_dir:
        debug_path = assets_dir.parent / "debug_source.md"
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(markdown_text)
        logger.info(f"디버그: 추출 원문 저장 → {debug_path}")

    logger.info(
        f"PDF→Markdown 추출 완료: p{page_num}, "
        f"{len(markdown_text)} chars, "
        f"{len(page_boxes)} blocks, "
        f"{len(assets)} images"
    )

    return {
        "markdown": markdown_text,
        "page_boxes": page_boxes,
        "assets": assets,
        "metadata": metadata,
    }


def _remove_markdown_tables(text: str) -> str:
    """Markdown 텍스트에서 테이블 구문을 제거한다.

    테이블은 `|`로 시작하고 `|`로 끝나는 연속된 줄로 판별.
    테이블이 아닌 줄을 만나면 테이블 영역이 끝난 것으로 간주.
    """
    lines = text.split("\n")
    result = []
    for line in lines:
        stripped = line.strip()
        is_table_line = stripped.startswith("|") and stripped.endswith("|")
        if not is_table_line:
            result.append(line)
    return "\n".join(result)
