"""
텍스트 번역 엔진 — PyMuPDF + DocLayout-YOLO + Ollama 직접 호출
pdf2zh 폴백용 자체 렌더링 파이프라인
"""
import json
import logging
import time
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional

import fitz  # PyMuPDF
import numpy as np
import requests

import config

logger = logging.getLogger(__name__)

# ── DocLayout-YOLO 싱글턴 ──

_layout_model = None
_layout_model_available = False

TRANSLATE_CLASSES = {"title", "plain text"}
CAPTURE_CLASSES = {"figure", "table", "isolate_formula"}
SKIP_CLASSES = {"abandon", "figure_caption", "table_caption",
                "table_footnote", "formula_caption"}


def _get_layout_model():
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


# ══════════════════════════════════════
# 레이아웃 감지
# ══════════════════════════════════════

def _iou(a: fitz.Rect, b: fitz.Rect) -> float:
    """두 Rect의 IoU 계산"""
    inter = a & b  # intersection
    if inter.is_empty:
        return 0.0
    inter_area = inter.width * inter.height
    union_area = a.width * a.height + b.width * b.height - inter_area
    return inter_area / union_area if union_area > 0 else 0.0


def _suppress_overlaps(regions: list[dict], iou_thresh: float = 0.3) -> list[dict]:
    """IoU > threshold인 영역 중 낮은 conf 쪽 제거 (NMS)"""
    if len(regions) <= 1:
        return regions
    # conf 내림차순 정렬
    sorted_r = sorted(regions, key=lambda r: r.get("conf", 1.0), reverse=True)
    keep = []
    for r in sorted_r:
        overlap = False
        for kept in keep:
            if _iou(r["bbox"], kept["bbox"]) > iou_thresh:
                overlap = True
                break
        if not overlap:
            keep.append(r)
    return keep


def _clip_against_captures(
    translate_regions: list[dict],
    capture_regions: list[dict],
) -> list[dict]:
    """translate bbox가 capture 영역과 겹치면 겹치지 않도록 클리핑.
    겹침이 50% 이상이면 해당 translate 영역 자체를 제거."""
    if not capture_regions:
        return translate_regions

    result = []
    for tr in translate_regions:
        bbox = fitz.Rect(tr["bbox"])
        tr_area = bbox.width * bbox.height
        if tr_area <= 0:
            continue

        clipped = fitz.Rect(bbox)
        drop = False
        for cap in capture_regions:
            inter = clipped & cap["bbox"]
            if inter.is_empty:
                continue
            overlap_ratio = (inter.width * inter.height) / tr_area
            if overlap_ratio > 0.5:
                drop = True
                break
            # 위/아래 클리핑: capture가 아래에 있으면 translate y1 줄임, 위에 있으면 y0 늘림
            cap_bbox = cap["bbox"]
            if inter.height < inter.width:
                # 수평으로 넓게 겹침 → 수직 클리핑
                if cap_bbox.y0 > clipped.y0:
                    clipped.y1 = min(clipped.y1, cap_bbox.y0)
                else:
                    clipped.y0 = max(clipped.y0, cap_bbox.y1)

        if drop or clipped.is_empty or clipped.height < 5:
            continue

        tr_copy = dict(tr)
        tr_copy["bbox"] = clipped
        # 클리핑된 영역의 텍스트 재추출은 비용이 크므로 원본 유지
        result.append(tr_copy)
    return result


def _detect_layout_yolo(page: fitz.Page) -> tuple[list[dict], list[dict]]:
    """DocLayout-YOLO로 레이아웃 감지 → (번역 영역, 캡처 영역)"""
    model = _get_layout_model()
    if model is None:
        return _detect_layout_fallback(page)

    pix = page.get_pixmap(dpi=72)
    image = np.frombuffer(pix.samples, np.uint8).reshape(
        pix.height, pix.width, 3
    )[:, :, ::-1]  # RGB → BGR

    results = model.predict(image)[0]
    page_center = page.rect.width / 2

    translate_regions = []
    capture_regions = []

    for box in results.boxes:
        cls_name = results.names[int(box.cls)]
        bbox = fitz.Rect(box.xyxy.tolist())
        conf = float(box.conf)

        if cls_name in TRANSLATE_CLASSES:
            text = _extract_text_with_bullets(page, bbox)
            if not text:
                text = page.get_text("text", clip=bbox).strip()
            if not text:
                continue

            # 컬럼 판별
            mid_x = bbox.x0 + bbox.width / 2
            if bbox.width / page.rect.width > 0.6:
                column = "full"
            elif mid_x < page_center:
                column = "left"
            else:
                column = "right"

            # 지배적 폰트 크기 추출
            font_size = _get_dominant_font_size(page, bbox)

            translate_regions.append({
                "bbox": bbox,
                "text": text,
                "cls": cls_name,
                "column": column,
                "font_size": font_size,
                "conf": conf,
            })

        elif cls_name in CAPTURE_CLASSES:
            capture_regions.append({
                "bbox": bbox,
                "cls": cls_name,
                "conf": conf,
            })
        # SKIP_CLASSES → 무시

    # 겹침 해소: 같은 클래스 내 높은 IoU → 낮은 conf 제거
    translate_regions = _suppress_overlaps(translate_regions, iou_thresh=0.3)
    capture_regions = _suppress_overlaps(capture_regions, iou_thresh=0.3)

    # capture 영역과 겹치는 translate bbox 클리핑
    translate_regions = _clip_against_captures(translate_regions, capture_regions)

    # Y 좌표순 정렬
    translate_regions.sort(key=lambda r: (r["column"] != "full", r["column"], r["bbox"].y0))

    return translate_regions, capture_regions


def _detect_layout_fallback(page: fitz.Page) -> tuple[list[dict], list[dict]]:
    """YOLO 불가 시 PyMuPDF get_text("dict") 기반 폴백"""
    page_dict = page.get_text("dict")
    page_center = page.rect.width / 2

    translate_regions = []

    for block in page_dict.get("blocks", []):
        if block.get("type") != 0:  # 텍스트 블록만
            continue
        bbox = fitz.Rect(block["bbox"])

        text = _extract_text_with_bullets(page, bbox)
        if not text:
            continue

        mid_x = bbox.x0 + bbox.width / 2
        if bbox.width / page.rect.width > 0.6:
            column = "full"
        elif mid_x < page_center:
            column = "left"
        else:
            column = "right"

        font_size = _get_dominant_font_size(page, bbox)

        translate_regions.append({
            "bbox": bbox,
            "text": text,
            "cls": "plain text",
            "column": column,
            "font_size": font_size,
            "conf": 1.0,
        })

    translate_regions = _suppress_overlaps(translate_regions, iou_thresh=0.3)
    translate_regions.sort(key=lambda r: (r["column"] != "full", r["column"], r["bbox"].y0))

    return translate_regions, []


def _get_dominant_font_size(page: fitz.Page, bbox: fitz.Rect) -> float:
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


# ── 심볼 폰트 불릿 치환 ──────────────────────────────────────────

# 불릿 기호로 사용되는 심볼 폰트 패밀리 (소문자 비교)
_SYMBOL_FONTS = {"symbolmt", "symbol", "wingdings", "zapfdingbats", "webdings"}


def _extract_text_with_bullets(page: fitz.Page, bbox: fitz.Rect) -> str:
    """
    get_text("dict")로 텍스트를 추출하되,
    심볼 폰트의 단독 문자(불릿)를 "•"로 치환.
    """
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
                # 심볼 폰트의 짧은 텍스트(1~2자) → 불릿 치환
                if font in _SYMBOL_FONTS and len(text.strip()) <= 2:
                    parts.append("\u2022")  # •
                else:
                    parts.append(text)
            joined = "".join(parts).strip()
            if joined:
                lines.append(joined)

    return "\n".join(lines)


# ══════════════════════════════════════
# Ollama 번역
# ══════════════════════════════════════

def _translate_text_ollama(text: str, model: str,
                           lang_in: str = "English",
                           lang_out: str = "Korean") -> str:
    """Ollama API로 텍스트 번역"""
    system_prompt = getattr(config, "TRANSLATOR_TEXT_CUSTOM_PROMPT", "")
    if not system_prompt:
        system_prompt = (
            f"You are a professional translator. "
            f"Translate {lang_in} to {lang_out} accurately."
        )

    user_prompt = (
        f"Translate the following text:\n\n{text}"
    )

    resp = requests.post(
        f"{config.OLLAMA_URL}/api/chat",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
        },
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def _translate_regions(regions: list[dict], model: str) -> list[str]:
    """영역 그룹별로 Ollama 번역 → 개별 번역 결과 리스트 반환"""
    if not regions:
        return []

    # 컬럼별 그룹화
    groups: dict[str, list[int]] = {}
    for i, r in enumerate(regions):
        col = r["column"]
        groups.setdefault(col, []).append(i)

    translations = [""] * len(regions)
    separator = "\n---\n"

    for col in ["full", "left", "right"]:
        indices = groups.get(col, [])
        if not indices:
            continue

        texts = [regions[i]["text"] for i in indices]

        if len(texts) == 1:
            translated = _translate_text_ollama(texts[0], model)
            translations[indices[0]] = translated
        else:
            combined = separator.join(texts)
            translated = _translate_text_ollama(combined, model)
            parts = translated.split("---")

            # 구분자가 유지되었으면 분리, 아니면 균등 분배
            if len(parts) == len(indices):
                for j, idx in enumerate(indices):
                    translations[idx] = parts[j].strip()
            else:
                # 폴백: 전체를 첫 번째에 넣고 나머지는 개별 번역
                logger.warning(
                    f"번역 구분자 불일치: {len(parts)} parts vs {len(indices)} blocks. "
                    f"개별 번역으로 폴백"
                )
                for idx in indices:
                    translations[idx] = _translate_text_ollama(
                        regions[idx]["text"], model
                    )

    return translations


# ══════════════════════════════════════
# PDF 재구성
# ══════════════════════════════════════

def _build_translated_pdf(
    orig_doc: fitz.Document,
    page_num: int,
    translate_regions: list[dict],
    capture_regions: list[dict],
    translations: list[str],
    font_scale: float = 0.75,
    min_scale: float = 0.5,
    font_family: str = "sans-serif",
) -> tuple[fitz.Document, list[dict]]:
    """번역 PDF 생성 → (새 문서, 매핑 데이터)"""
    orig_page = orig_doc[page_num - 1]

    new_doc = fitz.open()
    new_page = new_doc.new_page(
        width=orig_page.rect.width,
        height=orig_page.rect.height,
    )

    mapping_blocks = []

    # 1. 캡처 영역 (figure/table/formula) → 이미지로 삽입
    for cap in capture_regions:
        bbox = cap["bbox"]
        try:
            pix = orig_page.get_pixmap(clip=bbox, dpi=150)
            new_page.insert_image(bbox, pixmap=pix)
        except Exception as e:
            logger.warning(f"캡처 삽입 실패 ({cap['cls']}): {e}")

    # 2. 번역 텍스트 삽입
    for i, (region, translated) in enumerate(zip(translate_regions, translations)):
        if not translated:
            continue

        bbox = region["bbox"]
        orig_pt = region.get("font_size", 10.0)
        target_px = orig_pt * 1.33 * font_scale

        css = (
            f"* {{font-family: {font_family}; "
            f"font-size: {target_px:.1f}px; "
            f"color: black; line-height: 1.3;}}"
        )

        # \n → <br> 변환 (insert_htmlbox는 HTML 렌더러이므로 \n은 공백 취급)
        html_text = translated.replace("\n", "<br>")

        # 단일 호출: min_scale 하한으로 한 번만 렌더링 (이중 호출 방지)
        effective_min = max(min_scale, 0.25)  # 최소 25% (너무 작으면 읽을 수 없음)
        spare, scale = new_page.insert_htmlbox(bbox, html_text, css=css, scale_low=effective_min)

        # 매핑 데이터 (향후 마킹 동기화용)
        mapping_blocks.append({
            "id": i,
            "cls": region["cls"],
            "column": region["column"],
            "source_rect": list(bbox),
            "target_rect": list(bbox),
            "source_text": region["text"],
            "target_text": translated,
            "font_scale_applied": round(scale, 3) if isinstance(scale, float) else None,
        })

    new_doc.subset_fonts()
    return new_doc, mapping_blocks


# ══════════════════════════════════════
# 메인 파이프라인
# ══════════════════════════════════════

def translate_page(
    original_pdf_path: Path,
    output_dir: Path,
    page_num: int,
    model: str,
    font_scale: Optional[float] = None,
    progress_callback=None,
) -> dict:
    """
    단일 페이지 텍스트 번역 실행.

    Args:
        original_pdf_path: 원본 PDF 경로
        output_dir: pages/{N}/ 디렉토리 경로
        page_num: 1-based 페이지 번호
        model: Ollama 모델명
        font_scale: 폰트 스케일 (None이면 config 기본값)
        progress_callback: 진행 상태 콜백 함수

    Returns:
        결과 dict (status, elapsed_sec, ...)
    """
    start_time = time.monotonic()

    _font_scale = font_scale or getattr(config, "TRANSLATOR_TEXT_FONT_SCALE", 0.75)
    _min_scale = getattr(config, "TRANSLATOR_TEXT_MIN_SCALE", 0.5)
    _font_family = getattr(config, "TRANSLATOR_TEXT_FONT_FAMILY", "sans-serif")
    _min_text_length = getattr(config, "TRANSLATOR_TEXT_MIN_TEXT_LENGTH", 0)

    if progress_callback:
        progress_callback("PDF 분석 중...")

    # 1. 원본 PDF 열기
    orig_doc = fitz.open(str(original_pdf_path))
    total_pages = len(orig_doc)

    if page_num < 1 or page_num > total_pages:
        orig_doc.close()
        raise ValueError(f"유효하지 않은 페이지 번호: {page_num} (1~{total_pages})")

    # 2. 레이아웃 감지
    if progress_callback:
        progress_callback("레이아웃 분석 중...")

    page = orig_doc[page_num - 1]
    translate_regions, capture_regions = _detect_layout_yolo(page)

    # 최소 텍스트 길이 필터
    if _min_text_length > 0:
        translate_regions = [
            r for r in translate_regions
            if len(r["text"]) >= _min_text_length
        ]

    if not translate_regions:
        orig_doc.close()
        raise ValueError("번역할 텍스트를 찾을 수 없습니다")

    logger.info(
        f"p{page_num}: {len(translate_regions)} 번역 영역, "
        f"{len(capture_regions)} 캡처 영역 감지"
    )

    # 3. Ollama 번역
    if progress_callback:
        progress_callback("번역 중...")

    translations = _translate_regions(translate_regions, model)

    # 4. PDF 재구성
    if progress_callback:
        progress_callback("PDF 생성 중...")

    new_doc, mapping_blocks = _build_translated_pdf(
        orig_doc, page_num,
        translate_regions, capture_regions, translations,
        font_scale=_font_scale, min_scale=_min_scale,
        font_family=_font_family,
    )

    # 5. 저장
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / "text_translated.pdf"
    new_doc.save(str(pdf_path))
    new_doc.close()

    # 매핑 데이터 저장
    mapping_path = output_dir / "text_mapping.json"
    mapping_data = {
        "page": page_num,
        "model": model,
        "font_scale": _font_scale,
        "created_at": datetime.now().isoformat(),
        "blocks": mapping_blocks,
    }
    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump(mapping_data, f, ensure_ascii=False, indent=2)

    orig_doc.close()

    elapsed = time.monotonic() - start_time

    return {
        "status": "done",
        "elapsed_sec": round(elapsed, 1),
        "translate_regions": len(translate_regions),
        "capture_regions": len(capture_regions),
        "font_scale": _font_scale,
    }
