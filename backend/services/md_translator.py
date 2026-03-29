"""
Markdown 블록 번역 모듈

Plan 17 Phase 2: PyMuPDF4LLM으로 추출된 Markdown을 블록 단위로
Ollama 번역하여 web_translated.md를 생성한다.

파이프라인:
  extract_page() → Markdown 원문
    → parse_blocks() → 블록 분리
    → translate_blocks() → Ollama 블록 번역
    → assemble_translated_md() → 번역 Markdown + frontmatter
    → save + 검색 인덱스 갱신
"""

import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

import config

logger = logging.getLogger(__name__)


# ══════════════════════════════════════
# Markdown 블록 파서
# ══════════════════════════════════════

# 블록 유형
BLOCK_HEADING = "heading"
BLOCK_PARAGRAPH = "paragraph"
BLOCK_TABLE = "table"
BLOCK_LIST = "list"
BLOCK_IMAGE = "image"
BLOCK_BLANK = "blank"

def parse_blocks(markdown_text: str) -> list[dict]:
    """Markdown 텍스트를 블록 단위로 분리한다.

    Returns:
        [{"type": "heading", "text": "## 제목", "translatable": True}, ...]
    """
    lines = markdown_text.split("\n")
    blocks = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 빈 줄
        if not stripped:
            blocks.append({"type": BLOCK_BLANK, "text": "", "translatable": False})
            i += 1
            continue

        # 이미지
        if stripped.startswith("!["):
            blocks.append({"type": BLOCK_IMAGE, "text": line, "translatable": False})
            i += 1
            continue

        # details/summary (원본 표 이미지 접기)
        if stripped.startswith("<details") or stripped.startswith("</details") or stripped.startswith("<summary"):
            blocks.append({"type": BLOCK_IMAGE, "text": line, "translatable": False})
            i += 1
            continue

        # 제목
        if stripped.startswith("#"):
            blocks.append({"type": BLOCK_HEADING, "text": line, "translatable": True})
            i += 1
            continue

        # 테이블 (| 로 시작하는 연속 줄)
        if stripped.startswith("|") and stripped.endswith("|"):
            table_lines = []
            while i < len(lines):
                s = lines[i].strip()
                if s.startswith("|") and s.endswith("|"):
                    table_lines.append(lines[i])
                    i += 1
                else:
                    break
            blocks.append({
                "type": BLOCK_TABLE,
                "text": "\n".join(table_lines),
                "translatable": True,
            })
            continue

        # 리스트 (- 또는 숫자. 로 시작하는 연속 줄)
        if re.match(r"^(\s*[-*+]|\s*\d+\.)\s", stripped):
            list_lines = []
            while i < len(lines):
                s = lines[i].strip()
                if re.match(r"^([-*+]|\d+\.)\s", s) or (s and lines[i].startswith("  ")):
                    list_lines.append(lines[i])
                    i += 1
                elif not s:
                    break
                else:
                    break
            blocks.append({
                "type": BLOCK_LIST,
                "text": "\n".join(list_lines),
                "translatable": True,
            })
            continue

        # 일반 단락 (빈 줄 또는 다른 블록 시작까지)
        para_lines = []
        while i < len(lines):
            s = lines[i].strip()
            if not s:
                break
            if s.startswith("#") or s.startswith("![") or (s.startswith("|") and s.endswith("|")):
                break
            if s.startswith("<details") or s.startswith("</details") or s.startswith("<summary"):
                break
            if re.match(r"^([-*+]|\d+\.)\s", s):
                break
            para_lines.append(lines[i])
            i += 1

        if para_lines:
            blocks.append({
                "type": BLOCK_PARAGRAPH,
                "text": "\n".join(para_lines),
                "translatable": True,
            })

    return blocks


# ══════════════════════════════════════
# 표 셀 번역
# ══════════════════════════════════════

def _parse_table_cells(table_text: str) -> tuple[list[str], list[list[str]], str]:
    """Markdown 테이블을 파싱하여 (헤더, 데이터 행들, 구분선)을 반환."""
    lines = [l.strip() for l in table_text.strip().split("\n") if l.strip()]
    if len(lines) < 2:
        return [], [], ""

    def split_cells(line):
        # | A | B | → ['A', 'B']
        return [c.strip() for c in line.strip("|").split("|")]

    header = split_cells(lines[0])
    separator = lines[1]  # |---|---|
    data_rows = [split_cells(l) for l in lines[2:]]

    return header, data_rows, separator


def _rebuild_table(header: list[str], data_rows: list[list[str]], separator: str) -> str:
    """파싱된 테이블 데이터를 Markdown 테이블 문자열로 재조립."""
    def row_to_line(cells):
        return "| " + " | ".join(cells) + " |"

    lines = [row_to_line(header), separator]
    for row in data_rows:
        # 열 수 맞추기
        while len(row) < len(header):
            row.append("")
        lines.append(row_to_line(row[:len(header)]))

    return "\n".join(lines)


def _translate_table(table_text: str, model: str,
                     glossary_entries: list[dict] | None = None) -> str:
    """Markdown 테이블의 셀 내용만 번역하고, 구조(|, ---)는 보존."""
    header, data_rows, separator = _parse_table_cells(table_text)
    if not header:
        return table_text  # 파싱 실패 시 원본 반환

    # 모든 셀 텍스트를 수집하여 한 번에 번역
    all_cells = header.copy()
    for row in data_rows:
        all_cells.extend(row)

    # 빈 셀과 숫자만 있는 셀은 번역 불필요
    translatable = []
    for i, cell in enumerate(all_cells):
        stripped = cell.strip().replace("**", "")
        if not stripped or re.match(r"^[\d.,\-+%()]+$", stripped):
            translatable.append((i, False))
        else:
            translatable.append((i, True))

    texts_to_translate = [all_cells[i] for i, t in translatable if t]

    if not texts_to_translate:
        return table_text  # 번역할 셀 없음

    # 구분자로 일괄 번역
    separator_token = "\n---\n"
    combined = separator_token.join(texts_to_translate)
    translated = _translate_text(combined, model, glossary_entries=glossary_entries)
    parts = translated.split("---")

    if len(parts) == len(texts_to_translate):
        translated_cells = [p.strip() for p in parts]
    else:
        # 폴백: 개별 번역
        logger.warning(f"표 셀 일괄 번역 구분자 불일치, 개별 번역 폴백")
        translated_cells = [
            _translate_text(t, model, glossary_entries=glossary_entries)
            for t in texts_to_translate
        ]

    # 번역 결과를 원래 위치에 배치
    t_idx = 0
    for i, is_translatable in translatable:
        if is_translatable and t_idx < len(translated_cells):
            all_cells[i] = translated_cells[t_idx]
            t_idx += 1

    # 재조립
    translated_header = all_cells[:len(header)]
    translated_rows = []
    idx = len(header)
    for row in data_rows:
        row_len = len(row)
        translated_rows.append(all_cells[idx:idx + row_len])
        idx += row_len

    return _rebuild_table(translated_header, translated_rows, separator)


# ══════════════════════════════════════
# Ollama 번역 (text_translator.py 패턴 재활용)
# ══════════════════════════════════════

_WEB_TRANSLATE_SYSTEM_PROMPT = (
    "You are a professional translator. "
    "Translate English to Korean accurately.\n\n"
    "## Rules\n"
    "1. Preserve all Markdown formatting: headings (##), bold (**), italic (*), "
    "lists (- or 1.), links, etc.\n"
    "2. Do NOT translate or remove Markdown syntax characters.\n"
    "3. If you see '---' separators between texts, keep them in the output.\n"
    "4. Output ONLY the translated text. No explanations.\n"
    "5. If you see a [Glossary: ...] hint at the end, use those term mappings "
    "for translation but do NOT include the [Glossary: ...] tag in your output."
)


def _translate_text(text: str, model: str,
                    glossary_entries: list[dict] | None = None) -> str:
    """Ollama API로 텍스트 번역. Markdown 서식 보존 지시 포함."""
    system_prompt = _WEB_TRANSLATE_SYSTEM_PROMPT

    glossary_note = ""
    if glossary_entries:
        terms = ", ".join(f"{e['source']}={e['target']}" for e in glossary_entries)
        glossary_note = f"\n\n[Glossary: {terms}]"

    user_prompt = f"Translate the following text:\n\n{text}{glossary_note}"

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


# ══════════════════════════════════════
# 블록 번역 + 조립
# ══════════════════════════════════════

def translate_blocks(blocks: list[dict], model: str,
                     glossary_entries: list[dict] | None = None,
                     progress_callback=None) -> list[dict]:
    """블록 리스트를 순회하며 번역. 결과를 blocks에 "translated" 키로 추가.

    인접한 paragraph/heading/list 블록을 --- 구분자로 묶어 일괄 번역하여
    Ollama 호출 수를 줄인다. 표는 구조 보존이 필요하므로 개별 처리.
    """
    # 스킵 대상 처리
    for block in blocks:
        if not block.get("translatable"):
            block["translated"] = block["text"]

    # 번역 대상 블록을 그룹으로 묶기: 표는 개별, 나머지는 일괄
    translatable = [(i, b) for i, b in enumerate(blocks) if b.get("translatable")]
    if not translatable:
        return blocks

    # 그룹 분리: 표는 단독, 텍스트 블록은 연속 묶음
    groups = []  # [(indices, "batch"|"table")]
    current_batch = []

    for idx, block in translatable:
        if block["type"] == BLOCK_TABLE:
            if current_batch:
                groups.append((current_batch, "batch"))
                current_batch = []
            groups.append(([idx], "table"))
        else:
            current_batch.append(idx)

    if current_batch:
        groups.append((current_batch, "batch"))

    total_groups = len(groups)
    done = 0

    for indices, group_type in groups:
        done += 1
        if progress_callback:
            progress_callback(f"번역 중... ({done}/{total_groups})")

        try:
            if group_type == "table":
                block = blocks[indices[0]]
                block["translated"] = _translate_table(
                    block["text"], model, glossary_entries=glossary_entries
                )
            elif len(indices) == 1:
                block = blocks[indices[0]]
                block["translated"] = _translate_text(
                    block["text"], model, glossary_entries=glossary_entries
                )
            else:
                # 일괄 번역: --- 구분자로 결합
                texts = [blocks[i]["text"] for i in indices]
                combined = "\n---\n".join(texts)
                translated = _translate_text(combined, model,
                                             glossary_entries=glossary_entries)
                parts = translated.split("---")

                if len(parts) == len(indices):
                    for i, idx in enumerate(indices):
                        blocks[idx]["translated"] = parts[i].strip()
                else:
                    # 구분자 불일치 — 개별 폴백
                    logger.warning(
                        f"일괄 번역 구분자 불일치: {len(parts)} vs {len(indices)}. 개별 폴백"
                    )
                    for idx in indices:
                        blocks[idx]["translated"] = _translate_text(
                            blocks[idx]["text"], model,
                            glossary_entries=glossary_entries
                        )
        except Exception as e:
            logger.warning(f"블록 그룹 번역 실패: {e}")
            for idx in indices:
                blocks[idx]["translated"] = blocks[idx]["text"]

    return blocks


def assemble_translated_md(
    blocks: list[dict],
    page_num: int,
    total_pages: int,
    model: str,
    title: str = "",
    assets_dir: Optional[Path] = None,
) -> str:
    """번역된 블록들을 frontmatter 포함 Markdown으로 조립.

    이미지 경로를 assets/ 상대경로로 변환.
    """
    # frontmatter (title/model의 따옴표 이스케이프)
    safe_title = title.replace('"', '\\"')
    safe_model = model.replace('"', '\\"')
    fm = (
        "---\n"
        f"title: \"{safe_title}\"\n"
        f"page: {page_num}\n"
        f"total_pages: {total_pages}\n"
        f"model: \"{safe_model}\"\n"
        f"translated_at: \"{datetime.now().isoformat()}\"\n"
        "summary: \"\"\n"
        "keywords: []\n"
        "tags: []\n"
        "---\n\n"
    )

    # 블록 조립 + 이미지 경로 변환
    parts = []
    for block in blocks:
        text = block.get("translated", block["text"])

        # 이미지 절대경로 → assets/ 상대경로로 변환
        if block["type"] == BLOCK_IMAGE and assets_dir:
            text = _convert_image_path(text, assets_dir)

        parts.append(text)

    body = "\n".join(parts)
    return fm + body


def assemble_extracted_md(
    markdown: str,
    page_num: int,
    total_pages: int,
    title: str = "",
    assets_dir: Optional[Path] = None,
) -> str:
    """추출된 원문 MD에 frontmatter 부착. 번역 없이 원본 그대로 저장."""
    safe_title = title.replace('"', '\\"')
    fm = (
        "---\n"
        f"title: \"{safe_title}\"\n"
        f"page: {page_num}\n"
        f"total_pages: {total_pages}\n"
        f"extracted_at: \"{datetime.now().isoformat()}\"\n"
        "summary: \"\"\n"
        "keywords: []\n"
        "---\n\n"
    )

    # 이미지 절대경로 → assets/ 상대경로로 변환
    body = markdown
    if assets_dir:
        body = _convert_image_path(body, assets_dir)

    return fm + body


def _convert_image_path(text: str, assets_dir: Path) -> str:
    """이미지 참조의 절대경로를 assets/ 상대경로로 변환."""
    def replacer(match):
        alt = match.group(1)
        path = match.group(2)
        filename = Path(path).name
        return f"![{alt}](assets/{filename})"

    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", replacer, text)


# ══════════════════════════════════════
# 전체 병합
# ══════════════════════════════════════

def merge_full_document(
    doc_dir: Path,
    total_pages: int,
    title: str = "",
    source: str = "translated",
) -> Optional[Path]:
    """페이지별 MD를 하나의 전체 문서로 병합.

    Args:
        source: "translated" → web_translated.md / full_translated.md
                "extracted"  → web_extracted.md  / full_extracted.md
    """
    pages_dir = doc_dir / "pages"
    if not pages_dir.exists():
        return None

    page_filename = f"web_{source}.md"
    merged_parts = []
    collected_pages = []

    # frontmatter에서 날짜 필드 이름 결정
    date_field = "translated_at" if source == "translated" else "extracted_at"

    for page_num in range(1, total_pages + 1):
        md_path = pages_dir / str(page_num) / page_filename
        if not md_path.exists():
            continue

        content = md_path.read_text(encoding="utf-8")

        # frontmatter 제거 (--- ... --- 블록)
        body = _strip_frontmatter(content)

        # 페이지별 모델/일자 정보 추출
        model = _extract_frontmatter_field(content, "model") if source == "translated" else ""
        date_val = _extract_frontmatter_field(content, date_field)
        date_str = date_val[:10] if date_val else ""

        comment = f"<!-- Page {page_num} | {model} | {date_str} -->" if source == "translated" \
            else f"<!-- Page {page_num} | {date_str} -->"
        merged_parts.append(comment)
        merged_parts.append(body.strip())
        merged_parts.append("")
        collected_pages.append(page_num)

    if not merged_parts:
        return None

    # 전체 frontmatter
    pages_key = f"pages_{source}"
    header = (
        "---\n"
        f"title: \"{title}\"\n"
        f"{pages_key}: {collected_pages}\n"
        f"pages_total: {total_pages}\n"
        f"last_merged: \"{datetime.now().isoformat()}\"\n"
        "---\n\n"
    )

    full_path = doc_dir / f"full_{source}.md"
    full_path.write_text(header + "\n".join(merged_parts), encoding="utf-8")
    logger.info(f"전체 병합 완료 ({source}): {len(collected_pages)}/{total_pages} pages → {full_path}")
    return full_path


def merge_full_translated(doc_dir: Path, total_pages: int, title: str = "") -> Optional[Path]:
    """번역된 페이지들을 full_translated.md로 병합. (하위 호환 래퍼)"""
    return merge_full_document(doc_dir, total_pages, title, source="translated")


def _strip_frontmatter(text: str) -> str:
    """Markdown 텍스트에서 YAML frontmatter(--- ... ---)를 제거."""
    if not text.startswith("---"):
        return text
    end = text.find("---", 3)
    if end == -1:
        return text
    return text[end + 3:].lstrip("\n")


def _extract_frontmatter_field(text: str, field: str) -> str:
    """frontmatter에서 특정 필드 값을 추출."""
    match = re.search(rf'^{field}:\s*"?([^"\n]+)"?', text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def update_frontmatter_keywords(md_path: Path, keywords: list[str]) -> bool:
    """Markdown 파일의 frontmatter에 keywords 필드를 업데이트.
    keywords: [] 형태가 이미 있으면 덮어쓰고, 없으면 frontmatter 끝에 추가.
    반환: 성공 여부.
    """
    if not md_path.exists():
        return False
    text = md_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return False

    import json as _json
    kw_json = _json.dumps(keywords, ensure_ascii=False)

    # 기존 keywords 필드가 있으면 교체
    new_text, count = re.subn(
        r'^keywords:\s*\[.*?\]',
        f'keywords: {kw_json}',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count > 0:
        md_path.write_text(new_text, encoding="utf-8")
        return True

    # 없으면 frontmatter 닫힘(---) 직전에 추가
    end_idx = text.find("---", 3)
    if end_idx == -1:
        return False
    insert_line = f"keywords: {kw_json}\n"
    new_text = text[:end_idx] + insert_line + text[end_idx:]
    md_path.write_text(new_text, encoding="utf-8")
    return True
