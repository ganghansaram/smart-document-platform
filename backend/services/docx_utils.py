"""DOCX 파싱 공용 유틸리티 (Plan-53).

python-docx 의 doc.paragraphs / doc.tables 가 별개 컬렉션이라 원본 순서 손실.
이 모듈은 doc.element.body 의 child node 를 직접 순회해 원본 순서를 보존한다.

업계 표준 패턴:
- python-docx GitHub issue #40 의 long-standing 표준 답변
- pandoc DocX.hs / mammoth / Apache POI 모두 동일 접근

기존 사내 구현: tools/converter/converter.py:_iter_block_items
"""
from __future__ import annotations

from typing import Iterator


def iter_block_items(doc) -> Iterator:
    """Document body 의 paragraph + table 을 원본 순서대로 yield.

    Args:
        doc: python-docx Document 객체

    Yields:
        paragraph (docx.text.paragraph.Paragraph) 또는
        table (docx.table.Table) — XML 출현 순서.
    """
    para_idx = 0
    table_idx = 0
    for child in doc.element.body:
        tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
        if tag == 'p':
            if para_idx < len(doc.paragraphs):
                yield doc.paragraphs[para_idx]
                para_idx += 1
        elif tag == 'tbl':
            if table_idx < len(doc.tables):
                yield doc.tables[table_idx]
                table_idx += 1
