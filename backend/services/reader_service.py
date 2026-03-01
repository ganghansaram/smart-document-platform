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

        for block in blocks:
            block_type = block[6]  # 0=text, 1=image
            if block_type == 1:
                paragraphs.append({
                    "id": para_id,
                    "page": page_num + 1,
                    "text": "[Figure]",
                    "translated": None,
                    "type": "figure",
                })
                para_id += 1
                continue

            text = block[4].strip()
            if not text:
                continue

            ptype = _classify_block(text)
            paragraphs.append({
                "id": para_id,
                "page": page_num + 1,
                "text": text,
                "translated": None,
                "type": ptype,
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

    # 번역 대상 필터링
    if paragraph_ids is not None:
        targets = [p for p in content if p["id"] in paragraph_ids]
    else:
        targets = [p for p in content if p["translated"] is None and p["type"] == "text"]

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

    index = _load_index()
    new_index = [e for e in index if e["id"] != doc_id]
    if len(new_index) == len(index):
        return False
    _save_index(new_index)
    return True
