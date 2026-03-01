"""
Reader 서비스 — PDF 파싱, Ollama 번역, 문서 저장
"""
import json
import hashlib
import re
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

import requests

import config

# 번역 캐시 (md5 → translated)
_translation_cache: dict[str, str] = {}


def _ensure_data_dir():
    """data/reader 디렉토리 보장"""
    Path(config.READER_DATA_DIR).mkdir(parents=True, exist_ok=True)


def _pdf_dir() -> Path:
    return Path(config.READER_DATA_DIR) / "pdfs"


def _pdf_path(doc_id: str) -> Path:
    return _pdf_dir() / f"{doc_id}.pdf"


def get_pdf_path(doc_id: str) -> Optional[Path]:
    """PDF 파일 경로 반환 (존재 시), 없으면 None"""
    path = _pdf_path(doc_id)
    return path if path.exists() else None


def _index_path() -> Path:
    return Path(config.READER_DATA_DIR) / "_index.json"


def _doc_path(doc_id: str) -> Path:
    return Path(config.READER_DATA_DIR) / f"{doc_id}.json"


def _load_index() -> list[dict]:
    path = _index_path()
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_index(index: list[dict]):
    _ensure_data_dir()
    with open(_index_path(), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def _save_document(doc: dict):
    _ensure_data_dir()
    with open(_doc_path(doc["id"]), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)


def _generate_id() -> str:
    now = datetime.now()
    rand = hashlib.md5(os.urandom(8)).hexdigest()[:6]
    return f"{now.strftime('%Y%m%d_%H%M%S')}_{rand}"


def _classify_block(text: str) -> str:
    """블록 타입 분류: text / formula"""
    stripped = text.strip()
    if not stripped:
        return "text"
    # 수식 휴리스틱: 짧은 블록(100자 이하) + 특수문자 비율 높음
    if len(stripped) <= 100:
        special = sum(1 for c in stripped if c in "∑∫∂∇≈≠≤≥±×÷√∞αβγδεζηθλμπσφψω=+−/<>()[]{}^_|")
        if len(stripped) > 0 and special / len(stripped) > 0.3:
            return "formula"
    return "text"


def _images_dir() -> Path:
    return Path(config.READER_DATA_DIR) / "images"


def _crop_block_image(page, bbox, doc_id: str, page_num: int, block_idx: int) -> Optional[str]:
    """페이지에서 bbox 영역을 PNG로 크롭 저장, 파일명 반환"""
    import fitz
    try:
        clip = fitz.Rect(bbox)
        pix = page.get_pixmap(clip=clip, dpi=150)
        img_filename = f"{doc_id}_p{page_num}_b{block_idx}.png"
        img_dir = _images_dir()
        img_dir.mkdir(parents=True, exist_ok=True)
        pix.save(str(img_dir / img_filename))
        return img_filename
    except Exception:
        return None


def _rects_overlap(a, b, threshold=0.5) -> bool:
    """두 bbox [x0,y0,x1,y1]의 겹침 비율이 threshold 이상이면 True"""
    x0 = max(a[0], b[0])
    y0 = max(a[1], b[1])
    x1 = min(a[2], b[2])
    y1 = min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return False
    inter = (x1 - x0) * (y1 - y0)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    return area_a > 0 and inter / area_a >= threshold


def parse_pdf(pdf_bytes: bytes, filename: str):
    """
    PDF 파싱 제너레이터 — 페이지별 진행률 이벤트 + 최종 결과 반환
    yields: dict (progress events)
    최종 yield: {"step": "done", ...} with document data
    """
    import fitz  # PyMuPDF

    doc_id = _generate_id()

    # PDF 원본 바이너리 저장
    _pdf_dir().mkdir(parents=True, exist_ok=True)
    _pdf_path(doc_id).write_bytes(pdf_bytes)

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_pages = len(doc)
    title = doc.metadata.get("title", "").strip() or Path(filename).stem

    paragraphs = []
    para_id = 0

    for page_num in range(total_pages):
        yield {
            "step": "parsing",
            "status": "progress",
            "current": page_num + 1,
            "total": total_pages,
        }

        page = doc[page_num]
        blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no, block_type)

        page_rect = page.rect  # PDF 페이지 원본 크기 (width, height)

        # 테이블 영역 감지 — find_tables()로 bbox 수집
        table_rects = []
        try:
            tables = page.find_tables()
            for table in tables:
                table_rects.append(list(table.bbox))  # [x0, y0, x1, y1]
        except Exception:
            pass

        # 이미 크롭한 테이블 추적 (중복 방지)
        cropped_tables = set()

        for block in blocks:
            block_type = block[6]  # 0=text, 1=image
            bbox = [round(block[0], 2), round(block[1], 2),
                    round(block[2], 2), round(block[3], 2)]

            if block_type == 1:
                # Figure — 해당 영역 크롭 이미지 저장
                img_file = _crop_block_image(page, bbox, doc_id, page_num + 1, block[5])
                paragraphs.append({
                    "id": para_id,
                    "page": page_num + 1,
                    "text": "[Figure]",
                    "translated": None,
                    "type": "figure",
                    "image": img_file,
                    "bbox": bbox,
                    "page_size": [round(page_rect.width, 2), round(page_rect.height, 2)],
                })
                para_id += 1
                continue

            text = block[4].strip()
            if not text:
                continue

            # 테이블 영역과 겹치는지 확인
            matched_table = None
            for ti, trect in enumerate(table_rects):
                if _rects_overlap(bbox, trect):
                    matched_table = ti
                    break

            if matched_table is not None:
                if matched_table not in cropped_tables:
                    # 테이블 첫 등장 — 테이블 전체 영역 크롭 이미지
                    cropped_tables.add(matched_table)
                    trect = table_rects[matched_table]
                    img_file = _crop_block_image(page, trect, doc_id, page_num + 1, f"t{matched_table}")
                    paragraphs.append({
                        "id": para_id,
                        "page": page_num + 1,
                        "text": text,
                        "translated": None,
                        "type": "table",
                        "image": img_file,
                        "bbox": [round(trect[0], 2), round(trect[1], 2),
                                 round(trect[2], 2), round(trect[3], 2)],
                        "page_size": [round(page_rect.width, 2), round(page_rect.height, 2)],
                    })
                    para_id += 1
                # 이미 크롭된 테이블과 겹치는 블록은 스킵
                continue

            ptype = _classify_block(text)
            paragraphs.append({
                "id": para_id,
                "page": page_num + 1,
                "text": text,
                "translated": None,
                "type": ptype,
                "bbox": bbox,
                "page_size": [round(page_rect.width, 2), round(page_rect.height, 2)],
            })
            para_id += 1

    doc.close()

    document = {
        "id": doc_id,
        "filename": filename,
        "title": title,
        "pages": total_pages,
        "paragraphs": len(paragraphs),
        "has_pdf": True,
        "content": paragraphs,
        "created_at": datetime.now().isoformat(),
    }

    _save_document(document)

    # 인덱스 갱신
    index = _load_index()
    index.append({
        "id": doc_id,
        "filename": filename,
        "title": title,
        "pages": total_pages,
        "paragraphs": len(paragraphs),
        "has_pdf": True,
        "translated": 0,
        "created_at": document["created_at"],
    })
    _save_index(index)

    yield {
        "step": "done",
        "status": "completed",
        "document_id": doc_id,
        "meta": {
            "pages": total_pages,
            "paragraphs": len(paragraphs),
        },
    }


def translate_paragraph(text: str) -> str:
    """단일 문단 Ollama 번역"""
    cache_key = hashlib.md5(text.encode()).hexdigest()
    if cache_key in _translation_cache:
        return _translation_cache[cache_key]

    prompt = (
        "You are an expert academic translator. "
        "Translate the following English text to Korean. "
        "Keep technical terms, abbreviations, and proper nouns in English. "
        "Output ONLY the translation, no explanation.\n\n"
        f"{text}"
    )

    try:
        resp = requests.post(
            f"{config.OLLAMA_URL}/api/generate",
            json={
                "model": config.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1},
            },
            timeout=config.READER_TRANSLATION_TIMEOUT,
        )
        resp.raise_for_status()
        translated = resp.json().get("response", "").strip()
        # 한글 번역 줄바꿈 정리: 단일 \n → 공백, \n\n(문단 구분)은 유지
        translated = re.sub(r'(?<!\n)\n(?!\n)', ' ', translated).strip()
    except Exception as e:
        translated = f"[번역 오류: {e}]"

    _translation_cache[cache_key] = translated
    return translated


def translate_document(doc_id: str, paragraph_ids: Optional[list[int]] = None):
    """
    문서 번역 제너레이터 — 단락별 진행률 yield
    paragraph_ids가 None이면 미번역 전체, 리스트면 해당 단락만
    """
    doc_file = _doc_path(doc_id)
    if not doc_file.exists():
        yield {"step": "error", "status": "error", "message": "Document not found"}
        return

    with open(doc_file, "r", encoding="utf-8") as f:
        document = json.load(f)

    content = document["content"]

    # 번역 대상 필터링 (table/figure/formula는 항상 스킵)
    skip_types = {"figure", "table", "formula"}
    if paragraph_ids is not None:
        targets = [p for p in content
                   if p["id"] in paragraph_ids and p.get("type") not in skip_types]
    else:
        targets = [p for p in content
                   if p["translated"] is None and p["type"] == "text"]

    total = len(targets)
    if total == 0:
        yield {"step": "done", "status": "completed", "translated_count": 0}
        return

    translated_count = 0
    for i, para in enumerate(targets):
        translated = translate_paragraph(para["text"])
        para["translated"] = translated
        translated_count += 1

        yield {
            "step": "translate",
            "status": "progress",
            "paragraph_id": para["id"],
            "translated": translated,
            "current": i + 1,
            "total": total,
        }

        # 매 5단락마다 중간 저장
        if (i + 1) % 5 == 0:
            _save_document(document)

    # 최종 저장
    _save_document(document)

    # 인덱스의 translated 카운트 갱신
    total_translated = sum(1 for p in content if p["translated"] is not None)
    index = _load_index()
    for entry in index:
        if entry["id"] == doc_id:
            entry["translated"] = total_translated
            break
    _save_index(index)

    yield {
        "step": "done",
        "status": "completed",
        "translated_count": translated_count,
    }


def get_documents() -> list[dict]:
    """문서 목록 반환"""
    return _load_index()


def get_document(doc_id: str) -> Optional[dict]:
    """문서 상세 반환"""
    doc_file = _doc_path(doc_id)
    if not doc_file.exists():
        return None
    with open(doc_file, "r", encoding="utf-8") as f:
        return json.load(f)


def delete_document(doc_id: str) -> bool:
    """문서 삭제"""
    doc_file = _doc_path(doc_id)
    if doc_file.exists():
        doc_file.unlink()

    # PDF 바이너리도 삭제
    pdf_file = _pdf_path(doc_id)
    if pdf_file.exists():
        pdf_file.unlink()

    # 번역 PDF 삭제
    translated_pdf = _pdf_dir() / f"{doc_id}_translated.pdf"
    if translated_pdf.exists():
        translated_pdf.unlink()

    # 크롭 이미지 삭제
    img_dir = _images_dir()
    if img_dir.exists():
        for img_file in img_dir.glob(f"{doc_id}_*.png"):
            img_file.unlink()

    index = _load_index()
    new_index = [e for e in index if e["id"] != doc_id]
    if len(new_index) == len(index):
        return False
    _save_index(new_index)
    return True


def get_reader_image_path(filename: str) -> Optional[Path]:
    """크롭 이미지 경로 반환 (존재 시)"""
    # 경로 조작 방지
    if "/" in filename or "\\" in filename or ".." in filename:
        return None
    path = _images_dir() / filename
    return path if path.exists() else None


def get_translated_pdf_path(doc_id: str) -> Optional[Path]:
    """번역 PDF 경로 반환 (존재 시)"""
    path = _pdf_dir() / f"{doc_id}_translated.pdf"
    return path if path.exists() else None


def invalidate_translated_pdf(doc_id: str):
    """번역 PDF 캐시 무효화"""
    path = _pdf_dir() / f"{doc_id}_translated.pdf"
    if path.exists():
        path.unlink()


TRANSLATED_BBOX_EXPAND = 1.5  # bbox 높이 확장 비율 (overflow 방지)
TRANSLATED_FONTSIZE_MIN = 5.0  # 번역 폰트 최소 크기
TRANSLATED_FONTSIZE_FALLBACK = 8.0  # 원본 폰트 감지 실패 시 기본값


def generate_translated_pdf(doc_data: dict):
    """원본 PDF 위에 번역 텍스트를 오버레이한 PDF 생성"""
    import fitz

    doc_id = doc_data["id"]
    src_path = _pdf_path(doc_id)
    if not src_path.exists():
        raise FileNotFoundError(f"원본 PDF 없음: {doc_id}")

    # 폰트 경로
    font_path = Path(__file__).parent.parent / "fonts" / "MalgunGothic.ttf"
    if not font_path.exists():
        raise FileNotFoundError(f"폰트 파일 없음: {font_path}")

    doc = fitz.open(str(src_path))

    # ── 페이지별 원본 폰트 사이즈 맵 구축 ──
    # page.get_text("dict")로 span별 폰트 크기를 추출하여
    # 각 단락 bbox 영역의 대표 폰트 크기를 결정
    page_font_cache: dict[int, list] = {}  # page_idx → [(span_rect, fontsize)]

    def _get_page_fonts(page_idx: int) -> list:
        if page_idx in page_font_cache:
            return page_font_cache[page_idx]
        page = doc[page_idx]
        spans = []
        for block in page.get_text("dict")["blocks"]:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    if span["text"].strip():
                        sb = fitz.Rect(span["bbox"])
                        spans.append((sb, span["size"]))
        page_font_cache[page_idx] = spans
        return spans

    def _detect_fontsize(page_idx: int, rect: fitz.Rect) -> float:
        """원본 PDF에서 rect 영역과 겹치는 span들의 대표 폰트 크기 반환"""
        spans = _get_page_fonts(page_idx)
        sizes = []
        for sb, sz in spans:
            if rect.intersects(sb):
                sizes.append(sz)
        if not sizes:
            return TRANSLATED_FONTSIZE_FALLBACK
        # 중앙값 사용 (이상치 영향 최소화)
        sizes.sort()
        mid = len(sizes) // 2
        return max(TRANSLATED_FONTSIZE_MIN, sizes[mid])

    # ── 페이지별 table/figure bbox 수집 (텍스트 단락 중 테이블 영역 내/인접 항목 스킵용) ──
    skip_types = {"figure", "table", "formula"}
    NONTRANSLATE_MARGIN = 15.0  # 테이블/그림 bbox 확장 마진 (인접 캡션/섹션 헤더 포함)
    page_nontranslate_rects: dict[int, list] = {}
    for para in doc_data["content"]:
        if para.get("type") in skip_types and "bbox" in para:
            pidx = para["page"] - 1
            if pidx not in page_nontranslate_rects:
                page_nontranslate_rects[pidx] = []
            r = fitz.Rect(para["bbox"])
            # 마진 확장: 테이블 인접 캡션/섹션 헤더도 스킵하도록
            expanded = fitz.Rect(
                r.x0 - NONTRANSLATE_MARGIN, r.y0 - NONTRANSLATE_MARGIN,
                r.x1 + NONTRANSLATE_MARGIN, r.y1 + NONTRANSLATE_MARGIN,
            )
            page_nontranslate_rects[pidx].append(expanded)

    def _overlaps_nontranslate(page_idx: int, rect: fitz.Rect) -> bool:
        """rect가 해당 페이지의 table/figure 확장 영역과 겹치는지 확인"""
        for nr in page_nontranslate_rects.get(page_idx, []):
            if rect.intersects(nr):
                return True
        return False

    # 페이지별로 redact 영역을 모아서 처리
    page_redacts: dict[int, list] = {}  # page_idx → [(orig_rect, expanded, translated, fontsize)]

    for para in doc_data["content"]:
        if not para.get("translated"):
            continue
        if para.get("type") in skip_types:
            continue

        page_idx = para["page"] - 1
        if page_idx < 0 or page_idx >= len(doc):
            continue

        orig_rect = fitz.Rect(para["bbox"])

        # table/figure 영역과 겹치는 텍스트 단락 스킵
        if _overlaps_nontranslate(page_idx, orig_rect):
            continue

        # 원본 폰트 크기 감지
        fontsize = _detect_fontsize(page_idx, orig_rect)

        # bbox 높이를 확장하여 한국어 텍스트 overflow 방지
        expanded = fitz.Rect(
            orig_rect.x0, orig_rect.y0,
            orig_rect.x1, orig_rect.y0 + (orig_rect.height * TRANSLATED_BBOX_EXPAND)
        )
        if page_idx not in page_redacts:
            page_redacts[page_idx] = []
        page_redacts[page_idx].append((orig_rect, expanded, para["translated"], fontsize))

    for page_idx, items in page_redacts.items():
        page = doc[page_idx]

        # 1) 흰색 사각형으로 원본 텍스트 영역 덮기 (확장 영역 포함)
        # NOTE: apply_redactions()는 PDF.js에서 폰트 리소스를 손상시켜
        #       한국어 텍스트가 렌더링되지 않는 문제가 있어 draw_rect 사용
        for orig_rect, expanded, _, _ in items:
            page.draw_rect(expanded, color=None, fill=(1, 1, 1))

        # 2) 확장 영역에 원본 매칭 폰트 크기로 번역 텍스트 삽입
        for _, expanded, translated, fontsize in items:
            rc = page.insert_textbox(
                expanded,
                translated,
                fontname="malgun",
                fontfile=str(font_path),
                fontsize=fontsize,
                align=0,  # TEXT_ALIGN_LEFT
            )
            # overflow 시 폰트 축소 재시도
            if rc < 0:
                page.draw_rect(expanded, color=None, fill=(1, 1, 1))
                smaller = max(TRANSLATED_FONTSIZE_MIN, fontsize * 0.7)
                page.insert_textbox(
                    expanded,
                    translated,
                    fontname="malgun",
                    fontfile=str(font_path),
                    fontsize=smaller,
                    align=0,
                )

    output_path = _pdf_dir() / f"{doc_id}_translated.pdf"
    doc.save(str(output_path))
    doc.close()
