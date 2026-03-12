"""
Compare 서비스 — 문서 텍스트 추출
"""
import io
import fitz  # PyMuPDF
from docx import Document


def extract_text(file_bytes: bytes, ext: str) -> dict:
    """확장자에 따라 텍스트 추출"""
    if ext == ".docx":
        return _extract_docx(file_bytes)
    elif ext == ".pdf":
        return _extract_pdf(file_bytes)
    else:
        raise ValueError(f"지원하지 않는 형식: {ext}")


def _extract_docx(file_bytes: bytes) -> dict:
    """python-docx로 단락별 텍스트 추출"""
    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return {"paragraphs": paragraphs, "page_count": None}


def _extract_pdf(file_bytes: bytes) -> dict:
    """PyMuPDF로 페이지별 → 단락별 텍스트 추출"""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    paragraphs = []
    for page in doc:
        blocks = page.get_text("blocks")  # (x0,y0,x1,y1,text,block_no,block_type)
        for b in blocks:
            if b[6] == 0:  # text block
                text = b[4].strip()
                if text:
                    paragraphs.append(text)
    page_count = len(doc)
    doc.close()
    return {"paragraphs": paragraphs, "page_count": page_count}
