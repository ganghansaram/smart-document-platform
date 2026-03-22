"""
PDF → Markdown 추출 모듈 (PyMuPDF4LLM 기반)

Plan 17 Phase 1: PDF 페이지를 Markdown + 이미지로 추출한다.
원문 Markdown은 번역 파이프라인(Phase 2)의 입력으로 사용되며,
번역 완료 후 translated.md만 최종 저장된다.

이미지 추출: PyMuPDF4LLM의 write_images 대신,
page_boxes의 picture bbox를 page.get_pixmap(clip=bbox)으로 영역 캡처한다.
이는 MinerU/텍스트 엔진과 동일한 업계 표준 방식이며, 잘림 문제를 방지한다.
"""

import logging
import re
from pathlib import Path
from typing import Optional

import fitz as _fitz
import numpy as _np
import config

logger = logging.getLogger(__name__)


# ══════════════════════════════════════
# DocLayout-YOLO 레이아웃 감지 (텍스트 엔진에서 이관)
# ══════════════════════════════════════

_layout_model = None
_layout_model_available = False

_YOLO_TRANSLATE_CLASSES = {"title", "plain text"}
_YOLO_CAPTURE_CLASSES = {"figure", "table", "isolate_formula"}
_YOLO_SKIP_CLASSES = {"abandon", "figure_caption", "table_caption",
                      "table_footnote", "formula_caption"}

# 불릿 기호로 사용되는 심볼 폰트 패밀리 (소문자 비교)
_SYMBOL_FONTS = {"symbolmt", "symbol", "wingdings", "zapfdingbats", "webdings"}


def _get_yolo_model():
    """BabelDOC DocLayout-YOLO ONNX 모델 로드 (싱글턴)"""
    global _layout_model, _layout_model_available
    if _layout_model is not None:
        return _layout_model
    try:
        from babeldoc.docvision.doclayout import OnnxModel
        _layout_model = OnnxModel.from_pretrained()
        _layout_model_available = True
        logger.info("DocLayout-YOLO 모델 로드 완료")
        return _layout_model
    except Exception as e:
        _layout_model_available = False
        logger.warning(f"DocLayout-YOLO 로드 실패 (X-gap 폴백 사용): {e}")
        return None


def _yolo_iou(a: _fitz.Rect, b: _fitz.Rect) -> float:
    """두 Rect의 IoU 계산"""
    inter = a & b
    if inter.is_empty:
        return 0.0
    inter_area = inter.width * inter.height
    union_area = a.width * a.height + b.width * b.height - inter_area
    return inter_area / union_area if union_area > 0 else 0.0


def _yolo_suppress_overlaps(regions: list[dict], iou_thresh: float = 0.3) -> list[dict]:
    """IoU > threshold인 영역 중 낮은 conf 쪽 제거 (NMS)"""
    if len(regions) <= 1:
        return regions
    sorted_r = sorted(regions, key=lambda r: r.get("conf", 1.0), reverse=True)
    keep = []
    for r in sorted_r:
        overlap = False
        for kept in keep:
            if _yolo_iou(r["bbox"], kept["bbox"]) > iou_thresh:
                overlap = True
                break
        if not overlap:
            keep.append(r)
    return keep


def _yolo_clip_against_captures(
    translate_regions: list[dict],
    capture_regions: list[dict],
) -> list[dict]:
    """translate bbox가 capture 영역과 겹치면 겹치지 않도록 클리핑.
    겹침이 50% 이상이면 해당 translate 영역 자체를 제거."""
    if not capture_regions:
        return translate_regions

    result = []
    for tr in translate_regions:
        bbox = _fitz.Rect(tr["bbox"])
        tr_area = bbox.width * bbox.height
        if tr_area <= 0:
            continue

        clipped = _fitz.Rect(bbox)
        drop = False
        for cap in capture_regions:
            inter = clipped & cap["bbox"]
            if inter.is_empty:
                continue
            overlap_ratio = (inter.width * inter.height) / tr_area
            if overlap_ratio > 0.5:
                drop = True
                break
            cap_bbox = cap["bbox"]
            if inter.height < inter.width:
                if cap_bbox.y0 > clipped.y0:
                    clipped.y1 = min(clipped.y1, cap_bbox.y0)
                else:
                    clipped.y0 = max(clipped.y0, cap_bbox.y1)

        if drop or clipped.is_empty or clipped.height < 5:
            continue

        tr_copy = dict(tr)
        tr_copy["bbox"] = clipped
        result.append(tr_copy)
    return result


def _yolo_get_dominant_font_size(page: _fitz.Page, bbox: _fitz.Rect) -> float:
    """영역 내 가장 많이 사용된 폰트 크기 반환 (pt)"""
    blocks = page.get_text("dict", clip=bbox)
    size_counts: dict[float, int] = {}

    for block in blocks.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                sz = round(span.get("size", 10), 1)
                text_len = len(span.get("text", "").strip())
                if text_len > 0:
                    size_counts[sz] = size_counts.get(sz, 0) + text_len

    if not size_counts:
        return 10.0
    return max(size_counts, key=size_counts.get)


def _yolo_extract_text_with_bullets(page: _fitz.Page, bbox: _fitz.Rect) -> str:
    """get_text("dict")로 텍스트를 추출하되,
    심볼 폰트의 단독 문자(불릿)를 "•"로 치환."""
    dict_data = page.get_text("dict", clip=bbox)
    lines = []

    for block in dict_data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            parts = []
            for span in line.get("spans", []):
                text = span.get("text", "")
                font = span.get("font", "").lower()
                if font in _SYMBOL_FONTS and len(text.strip()) <= 2:
                    parts.append("\u2022")  # •
                else:
                    parts.append(text)
            joined = "".join(parts).strip()
            if joined:
                lines.append(joined)

    return "\n".join(lines)


def _detect_layout_yolo(page: _fitz.Page) -> tuple[list[dict], list[dict]]:
    """DocLayout-YOLO로 레이아웃 감지 → (번역 영역, 캡처 영역)"""
    model = _get_yolo_model()
    if model is None:
        return _detect_layout_fallback(page)

    pix = page.get_pixmap(dpi=72)
    image = _np.frombuffer(pix.samples, _np.uint8).reshape(
        pix.height, pix.width, 3
    )[:, :, ::-1]  # RGB → BGR

    results = model.predict(image)[0]
    page_center = page.rect.width / 2

    translate_regions = []
    capture_regions = []

    for box in results.boxes:
        cls_name = results.names[int(box.cls)]
        bbox = _fitz.Rect(box.xyxy.tolist())
        conf = float(box.conf)

        if cls_name in _YOLO_TRANSLATE_CLASSES:
            text = _yolo_extract_text_with_bullets(page, bbox)
            if not text:
                text = page.get_text("text", clip=bbox).strip()
            if not text:
                continue

            mid_x = bbox.x0 + bbox.width / 2
            if bbox.width / page.rect.width > 0.6:
                column = "full"
            elif mid_x < page_center:
                column = "left"
            else:
                column = "right"

            font_size = _yolo_get_dominant_font_size(page, bbox)

            translate_regions.append({
                "bbox": bbox,
                "text": text,
                "cls": cls_name,
                "column": column,
                "font_size": font_size,
                "conf": conf,
            })

        elif cls_name in _YOLO_CAPTURE_CLASSES:
            capture_regions.append({
                "bbox": bbox,
                "cls": cls_name,
                "conf": conf,
            })

    translate_regions = _yolo_suppress_overlaps(translate_regions, iou_thresh=0.3)
    capture_regions = _yolo_suppress_overlaps(capture_regions, iou_thresh=0.3)
    translate_regions = _yolo_clip_against_captures(translate_regions, capture_regions)
    translate_regions.sort(key=lambda r: (r["column"] != "full", r["column"], r["bbox"].y0))

    return translate_regions, capture_regions


def _detect_layout_fallback(page: _fitz.Page) -> tuple[list[dict], list[dict]]:
    """YOLO 불가 시 PyMuPDF get_text("dict") 기반 폴백"""
    page_dict = page.get_text("dict")
    page_center = page.rect.width / 2

    translate_regions = []

    for block in page_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        bbox = _fitz.Rect(block["bbox"])

        text = _yolo_extract_text_with_bullets(page, bbox)
        if not text:
            continue

        mid_x = bbox.x0 + bbox.width / 2
        if bbox.width / page.rect.width > 0.6:
            column = "full"
        elif mid_x < page_center:
            column = "left"
        else:
            column = "right"

        font_size = _yolo_get_dominant_font_size(page, bbox)

        translate_regions.append({
            "bbox": bbox,
            "text": text,
            "cls": "plain text",
            "column": column,
            "font_size": font_size,
            "conf": 1.0,
        })

    translate_regions = _yolo_suppress_overlaps(translate_regions, iou_thresh=0.3)
    translate_regions.sort(key=lambda r: (r["column"] != "full", r["column"], r["bbox"].y0))

    return translate_regions, []


# ── column_boxes 실패 감지 ──

def _needs_yolo_fallback(page: _fitz.Page) -> bool:
    """column_boxes()가 컬럼을 감지하지 못하면 True 반환 (특수 PDF 감지)"""
    try:
        from pymupdf4llm.helpers.multi_column import column_boxes
        bboxes = column_boxes(page, footer_margin=50, header_margin=50)
        return len(bboxes) == 0
    except Exception:
        return False


def _extract_page_yolo_fallback(
    page: _fitz.Page,
    assets_dir: Optional[Path],
    image_dpi: int,
) -> dict:
    """DocLayout-YOLO로 레이아웃 감지 후 Markdown 조립 (column_boxes 실패 시 폴백)"""
    translate_regions, capture_regions = _detect_layout_yolo(page)

    if not translate_regions and not capture_regions:
        return None  # YOLO도 실패 → 기존 경로로 계속

    page_rect = page.rect
    BBOX_PADDING = 3

    # 번역 영역 → Markdown 텍스트 조립
    md_parts = []
    for region in translate_regions:
        text = region.get("text", "").strip()
        if not text:
            continue
        cls = region.get("cls", "plain text")
        if cls == "title":
            md_parts.append(f"## {text}")
        else:
            md_parts.append(text)
        md_parts.append("")  # 빈 줄 (단락 구분)

    markdown_text = "\n".join(md_parts)

    # 캡처 영역 → 이미지 저장
    assets = []
    if assets_dir is not None:
        assets_dir = Path(assets_dir)
        assets_dir.mkdir(parents=True, exist_ok=True)
        for i, region in enumerate(capture_regions):
            bbox = region.get("bbox")
            if not bbox:
                continue
            try:
                clip = _fitz.Rect(
                    max(bbox.x0 - BBOX_PADDING, page_rect.x0),
                    max(bbox.y0 - BBOX_PADDING, page_rect.y0),
                    min(bbox.x1 + BBOX_PADDING, page_rect.x1),
                    min(bbox.y1 + BBOX_PADDING, page_rect.y1),
                )
                pix = page.get_pixmap(clip=clip, dpi=image_dpi)
                cls = region.get("cls", "figure")
                fname = f"{cls}_{i}.png"
                pix.save(str(assets_dir / fname))
                assets.append(fname)

                # 이미지 폭 비율 계산
                width_pct = round(clip.width / page_rect.width * 100)
                width_pct = min(width_pct, 100)

                # Markdown에 figure 삽입
                fig_html = (
                    f'\n<figure style="max-width:{width_pct}%">'
                    f'<img src="assets/{fname}" alt="{cls}" style="width:100%">'
                    f'</figure>\n'
                )
                markdown_text += fig_html
            except Exception as e:
                logger.warning(f"YOLO 캡처 영역 이미지 저장 실패: {e}")

    # page_boxes 구성 (클릭 네비게이션용)
    page_boxes = []
    for idx, region in enumerate(translate_regions):
        bbox = region.get("bbox")
        page_boxes.append({
            "index": idx,
            "class": "section-header" if region.get("cls") == "title" else "text",
            "bbox": (int(bbox.x0), int(bbox.y0), int(bbox.x1), int(bbox.y1)),
        })
    for idx, region in enumerate(capture_regions):
        bbox = region.get("bbox")
        page_boxes.append({
            "index": len(translate_regions) + idx,
            "class": region.get("cls", "picture"),
            "bbox": (int(bbox.x0), int(bbox.y0), int(bbox.x1), int(bbox.y1)),
        })

    logger.info(f"YOLO 폴백 추출 완료: {len(translate_regions)}개 텍스트 + {len(capture_regions)}개 캡처")

    return {
        "markdown": markdown_text,
        "page_boxes": page_boxes,
        "assets": assets,
        "metadata": {},
    }


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
    fitz = _fitz

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")

    # 설정 읽기
    table_mode = getattr(config, "TRANSLATOR_WEB_TABLE_MODE", "extract")
    table_strategy = getattr(config, "TRANSLATOR_WEB_TABLE_STRATEGY", "lines_strict")
    image_dpi = getattr(config, "TRANSLATOR_WEB_IMAGE_DPI", 150)
    debug = getattr(config, "TRANSLATOR_WEB_DEBUG", False)

    # 페이지 번호 변환 (1-based → 0-based)
    page_index = page_num - 1

    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)

    if page_index < 0 or page_index >= total_pages:
        doc.close()
        raise ValueError(f"유효하지 않은 페이지 번호: {page_num} (1~{total_pages})")

    # ── DocLayout-YOLO 컬럼 감지 폴백 체크 ──
    # column_boxes()가 0개 반환 시 (특수 PDF) → YOLO로 레이아웃 감지
    page = doc[page_index]
    if _needs_yolo_fallback(page):
        logger.info(f"column_boxes() 실패 → DocLayout-YOLO 폴백: p{page_num}")
        yolo_result = _extract_page_yolo_fallback(page, assets_dir, image_dpi)
        if yolo_result is not None:
            doc.close()
            return yolo_result
        logger.warning("YOLO 폴백도 실패 → 기본 PyMuPDF4LLM 경로로 계속")

    # PyMuPDF4LLM 추출 (이미지는 write_images 사용하지 않음 — 영역 캡처로 대체)
    kwargs = {
        "pages": [page_index],
        "page_chunks": True,
        "table_strategy": table_strategy if table_mode == "extract" else "text",
    }

    logger.info(f"PDF→Markdown 추출 시작: p{page_num}, table_mode={table_mode}")

    chunks = pymupdf4llm.to_markdown(str(pdf_path), **kwargs)

    if not chunks:
        doc.close()
        raise ValueError(f"페이지 {page_num} 추출 결과가 비어있습니다")

    chunk = chunks[0]
    markdown_text = chunk.get("text", "")
    page_boxes = chunk.get("page_boxes", [])
    metadata = chunk.get("metadata", {})

    # ── 비텍스트 영역 일괄 이미지 캡처 ──
    # "본문 텍스트만 추출, 나머지(picture/table/formula 등)는 전부 이미지"
    TEXT_CLASSES = {"text", "section-header", "list-item", "caption", "page-header", "page-footer"}
    assets = []        # picture/formula 등 비텍스트 이미지
    image_widths = []
    table_assets = []  # table 전용 (table_mode="image" 시)
    table_widths = []
    page_width = 0.0

    if assets_dir is not None:
        assets_dir = Path(assets_dir)
        assets_dir.mkdir(parents=True, exist_ok=True)

        page = doc[page_index]
        page_width = page.rect.width
        page_rect = page.rect

        BBOX_PADDING = 3

        # 비텍스트 블록 캡처 (picture, formula 등 — table 제외, table은 별도 처리)
        non_text_boxes = [
            b for b in page_boxes
            if b.get("class") not in TEXT_CLASSES and b.get("class") != "table"
        ]
        for i, box in enumerate(non_text_boxes):
            bbox = box.get("bbox")
            if not bbox:
                continue
            try:
                clip = fitz.Rect(
                    max(bbox[0] - BBOX_PADDING, page_rect.x0),
                    max(bbox[1] - BBOX_PADDING, page_rect.y0),
                    min(bbox[2] + BBOX_PADDING, page_rect.x1),
                    min(bbox[3] + BBOX_PADDING, page_rect.y1),
                )
                pix = page.get_pixmap(clip=clip, dpi=image_dpi)
                cls = box.get("class", "figure")
                filename = f"{cls}_{i}.png"
                pix.save(str(assets_dir / filename))
                assets.append(filename)

                img_width_pct = round((bbox[2] - bbox[0]) / page_width * 100)
                img_width_pct = min(img_width_pct, 100)
                image_widths.append(img_width_pct)
                logger.debug(f"캡처: {filename} ({cls}, {clip}), width={img_width_pct}%")
            except Exception as e:
                logger.warning(f"캡처 실패 ({box.get('class')} {i}): {e}")
                image_widths.append(100)

        # table: table_mode에 따라 처리
        if table_mode == "image":
            table_boxes = [b for b in page_boxes if b.get("class") == "table"]
            for i, box in enumerate(table_boxes):
                bbox = box.get("bbox")
                if not bbox:
                    continue
                try:
                    clip = fitz.Rect(
                        max(bbox[0] - BBOX_PADDING, page_rect.x0),
                        max(bbox[1] - BBOX_PADDING, page_rect.y0),
                        min(bbox[2] + BBOX_PADDING, page_rect.x1),
                        min(bbox[3] + BBOX_PADDING, page_rect.y1),
                    )
                    pix = page.get_pixmap(clip=clip, dpi=image_dpi)
                    filename = f"table_{i}.png"
                    pix.save(str(assets_dir / filename))
                    table_assets.append(filename)

                    tbl_width_pct = round((bbox[2] - bbox[0]) / page_width * 100)
                    tbl_width_pct = min(tbl_width_pct, 100)
                    table_widths.append(tbl_width_pct)
                except Exception as e:
                    logger.warning(f"표 캡처 실패 (box {i}): {e}")

    doc.close()

    # ── 비텍스트 영역의 텍스트 제거 + 이미지 참조 삽입 ──
    if assets:
        non_text_boxes = [
            b for b in page_boxes
            if b.get("class") not in TEXT_CLASSES and b.get("class") != "table"
        ]
        markdown_text = _replace_picture_regions(
            markdown_text, page_boxes, non_text_boxes, assets, image_widths
        )

    # 표 모드별 후처리
    if table_mode == "image":
        markdown_text = _replace_tables_with_images(markdown_text, table_assets, table_widths)
        logger.info(f"table_mode=image: 표 {len(table_assets)}개를 이미지로 대체")
    elif table_mode == "off":
        markdown_text = _remove_markdown_tables(markdown_text)

    # ── 제목 이탤릭 제거 (가독성 개선) ──
    markdown_text = _clean_heading_styles(markdown_text)

    # ── PyMuPDF4LLM 아티팩트 제거 ──
    # omitted placeholder 줄 전체 제거
    markdown_text = re.sub(
        r"^.*==>.*?intentionally omitted.*?<==.*$", "", markdown_text, flags=re.MULTILINE
    )
    # 빈 서식 (****, **, __ 등 내용 없는 볼드/이탤릭) 제거 — 수평선으로 오인 방지
    markdown_text = re.sub(r"^\*{2,}$", "", markdown_text, flags=re.MULTILINE)
    markdown_text = re.sub(r"^_{2,}$", "", markdown_text, flags=re.MULTILINE)

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


def _replace_picture_regions(
    markdown_text: str,
    all_boxes: list[dict],
    picture_boxes: list[dict],
    assets: list[str],
    image_widths: list[int] = None,
) -> str:
    """picture 영역과 겹치는 텍스트를 제거하고, 이미지 참조로 대체한다.

    page_boxes의 pos (start, end) 필드를 사용하여 Markdown 텍스트 내
    picture 영역에 해당하는 구간을 이미지 참조로 교체한다.
    image_widths: 각 이미지의 페이지 대비 폭 비율 (%)
    """
    if not picture_boxes or not assets:
        return markdown_text
    if image_widths is None:
        image_widths = [100] * len(assets)

    # picture bbox와 겹치는 텍스트 블록의 pos 범위 수집
    replacements = []  # [(pos_start, pos_end, image_filename, width_pct)]

    for pic_idx, pic_box in enumerate(picture_boxes):
        pic_bbox = pic_box.get("bbox")
        pic_pos = pic_box.get("pos")
        if not pic_bbox or not pic_pos or pic_idx >= len(assets):
            continue

        pic_rect = (pic_bbox[0], pic_bbox[1], pic_bbox[2], pic_bbox[3])
        width_pct = image_widths[pic_idx] if pic_idx < len(image_widths) else 100

        # picture 자체의 pos 범위
        affected_start = pic_pos[0]
        affected_end = pic_pos[1]

        # picture bbox와 겹치는 다른 텍스트 블록도 범위에 포함
        for box in all_boxes:
            if box.get("class") == "picture":
                continue
            box_bbox = box.get("bbox")
            box_pos = box.get("pos")
            if not box_bbox or not box_pos:
                continue
            if _rects_overlap(pic_rect, (box_bbox[0], box_bbox[1], box_bbox[2], box_bbox[3])):
                affected_start = min(affected_start, box_pos[0])
                affected_end = max(affected_end, box_pos[1])

        replacements.append((affected_start, affected_end, assets[pic_idx], width_pct))

    if not replacements:
        return markdown_text

    # pos 역순 정렬 (뒤에서부터 대체하면 앞쪽 위치에 영향 없음)
    replacements.sort(key=lambda r: r[0], reverse=True)

    for start, end, filename, width_pct in replacements:
        # 이미지 바로 뒤의 캡션 텍스트 감지
        caption = _extract_caption_after(markdown_text, end, all_boxes, picture_boxes)

        # 이미지 태그 (원본 대비 폭 비율 적용 — Explorer converter.py 패턴)
        img_tag = f'<img src="assets/{filename}" alt="Figure" style="width: {width_pct}%">'

        if caption:
            image_ref = (
                f"\n\n<figure>\n\n"
                f"{img_tag}\n\n"
                f"<figcaption>{caption['text']}</figcaption>\n"
                f"</figure>\n\n"
            )
            markdown_text = markdown_text[:start] + image_ref + markdown_text[caption['end']:]
        else:
            image_ref = (
                f"\n\n<figure>\n\n"
                f"{img_tag}\n\n"
                f"</figure>\n\n"
            )
            markdown_text = markdown_text[:start] + image_ref + markdown_text[end:]

    return markdown_text


def _extract_caption_after(
    markdown_text: str,
    pic_end: int,
    all_boxes: list[dict],
    picture_boxes: list[dict],
) -> dict | None:
    """이미지 바로 뒤에 캡션 블록이 있는지 감지한다.

    page_boxes에서 class='caption'인 블록이 picture 바로 뒤에 있거나,
    텍스트가 "그림", "Figure", "Fig.", "표", "Table" 등으로 시작하면 캡션으로 판정.
    """
    # picture 바로 뒤의 텍스트 (공백/줄바꿈 건너뛰기)
    remaining = markdown_text[pic_end:].lstrip("\n ")
    if not remaining:
        return None

    # page_boxes에서 caption class 확인
    for box in all_boxes:
        if box.get("class") == "caption":
            pos = box.get("pos")
            if pos and pos[0] >= pic_end and pos[0] <= pic_end + 50:
                caption_text = markdown_text[pos[0]:pos[1]].strip()
                if caption_text:
                    return {"text": caption_text, "end": pos[1]}

    # 텍스트 패턴으로 캡션 감지 (그림 N, Figure N, Fig. N, 표 N, Table N)
    first_line = remaining.split("\n")[0].strip()
    caption_patterns = [
        r"^그림\s*[\dIVXLCDM]", r"^Figure\s*[\dIVXLCDM]", r"^Fig\.\s*[\dIVXLCDM]",
        r"^표\s*[\dIVXLCDM]", r"^Table\s*[\dIVXLCDM]", r"^Chart\s*[\dIVXLCDM]",
    ]
    for pattern in caption_patterns:
        if re.match(pattern, first_line, re.IGNORECASE):
            # 캡션 텍스트의 끝 위치 계산
            caption_end = pic_end + markdown_text[pic_end:].find(first_line) + len(first_line)
            return {"text": first_line, "end": caption_end}

    return None


def _rects_overlap(a: tuple, b: tuple) -> bool:
    """두 사각형 (x0, y0, x1, y1)이 겹치는지 판정. 50% 이상 포함 시 겹침."""
    # 교집합 계산
    ix0 = max(a[0], b[0])
    iy0 = max(a[1], b[1])
    ix1 = min(a[2], b[2])
    iy1 = min(a[3], b[3])

    if ix0 >= ix1 or iy0 >= iy1:
        return False

    intersection = (ix1 - ix0) * (iy1 - iy0)
    b_area = (b[2] - b[0]) * (b[3] - b[1])

    if b_area <= 0:
        return False

    # 텍스트 블록의 50% 이상이 picture 안에 있으면 겹침
    return intersection / b_area > 0.5


def _clean_heading_styles(text: str) -> str:
    """제목 줄에서 이탤릭/볼드 서식을 제거한다.

    PyMuPDF4LLM이 PDF 스타일을 그대로 가져와 ## _A. Title_ 같은 형태가 나오는데,
    웹 뷰에서는 가독성을 위해 서식 없이 깔끔한 제목만 표시.
    """
    lines = text.split("\n")
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            # 제목 레벨(## ) 분리
            hashes = ""
            rest = stripped
            while rest.startswith("#"):
                hashes += "#"
                rest = rest[1:]
            rest = rest.lstrip()

            # 이탤릭 제거: _text_ → text, *text* → text
            rest = re.sub(r"^_(.+)_$", r"\1", rest)
            rest = re.sub(r"^\*(.+)\*$", r"\1", rest)
            # 볼드+이탤릭 제거: **_text_** → text
            rest = re.sub(r"^\*\*_(.+)_\*\*$", r"\1", rest)
            rest = re.sub(r"^\*\*\*(.+)\*\*\*$", r"\1", rest)

            result.append(f"{hashes} {rest}")
        else:
            result.append(line)
    return "\n".join(result)


def _replace_tables_with_images(text: str, table_assets: list[str], table_widths: list[int]) -> str:
    """Markdown 테이블 구문을 이미지 참조로 대체한다.

    table_mode="image" 시 사용. 표 텍스트를 제거하고 캡처된 이미지로 교체.
    표 바로 다음 줄이 캡션 패턴이면 <figcaption>으로 래핑.
    """
    if not table_assets:
        return _remove_markdown_tables(text)

    # 캡션 패턴 (아라비아 숫자 + 로마 숫자)
    caption_patterns = [
        r"^표\s*[\dIVXLCDM]", r"^Table\s*[\dIVXLCDM]", r"^TABLE\s*[\dIVXLCDM]",
        r"^그림\s*[\dIVXLCDM]", r"^Figure\s*[\dIVXLCDM]", r"^Fig\.\s*[\dIVXLCDM]",
    ]

    lines = text.split("\n")
    result = []
    table_idx = 0
    in_table = False
    pending_figure_close = False  # </figure> 삽입 대기

    for line in lines:
        stripped = line.strip()
        is_table_line = stripped.startswith("|") and stripped.endswith("|")

        # 표 이미지 삽입 직후 — 캡션 감지
        if pending_figure_close:
            is_caption = False
            if stripped:
                for pat in caption_patterns:
                    if re.match(pat, stripped, re.IGNORECASE):
                        is_caption = True
                        break
                # 제목 서식(##)이 붙은 캡션도 감지
                caption_text = stripped.lstrip("#").strip()
                caption_text = re.sub(r"^_(.+)_$", r"\1", caption_text)
                for pat in caption_patterns:
                    if re.match(pat, caption_text, re.IGNORECASE):
                        is_caption = True
                        stripped = caption_text
                        break

            if is_caption:
                result.append(f"<figcaption>{stripped}</figcaption>")
                result.append("</figure>")
                result.append("")
                pending_figure_close = False
                continue
            else:
                result.append("</figure>")
                result.append("")
                pending_figure_close = False
                # 현재 줄은 아래에서 처리

        if is_table_line and not in_table:
            in_table = True
            if table_idx < len(table_assets):
                filename = table_assets[table_idx]
                width = table_widths[table_idx] if table_idx < len(table_widths) else 100
                img_tag = f'<img src="assets/{filename}" alt="Table" style="width: {width}%">'

                # 표 위쪽 캡션 감지: 직전 비어있지 않은 줄이 캡션 패턴인지 확인
                above_caption = None
                for k in range(len(result) - 1, -1, -1):
                    prev = result[k].strip()
                    if not prev:
                        continue
                    # 제목 서식 제거 후 패턴 매칭
                    prev_clean = prev.lstrip("#").strip()
                    prev_clean = re.sub(r"^_(.+)_$", r"\1", prev_clean)
                    for pat in caption_patterns:
                        if re.match(pat, prev_clean, re.IGNORECASE):
                            above_caption = (k, prev_clean)
                            break
                    break  # 첫 비어있지 않은 줄만 확인

                if above_caption:
                    cap_idx, cap_text = above_caption
                    result[cap_idx] = ""  # 원래 캡션 줄 제거
                    result.append("")
                    result.append("<figure>")
                    result.append(f"<figcaption>{cap_text}</figcaption>")
                    result.append("")
                    result.append(img_tag)
                    result.append("")
                else:
                    result.append("")
                    result.append("<figure>")
                    result.append("")
                    result.append(img_tag)
                    result.append("")

                table_idx += 1
                pending_figure_close = True
        elif is_table_line and in_table:
            continue
        else:
            if in_table:
                in_table = False
            result.append(line)

    # 마지막 표 뒤에 figure 닫기가 남아있으면
    if pending_figure_close:
        result.append("</figure>")
        result.append("")

    return "\n".join(result)


def _remove_markdown_tables(text: str) -> str:
    """Markdown 텍스트에서 테이블 구문을 제거한다."""
    lines = text.split("\n")
    result = []
    for line in lines:
        stripped = line.strip()
        is_table_line = stripped.startswith("|") and stripped.endswith("|")
        if not is_table_line:
            result.append(line)
    return "\n".join(result)
