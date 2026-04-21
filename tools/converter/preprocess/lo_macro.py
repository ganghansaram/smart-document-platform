# -*- coding: utf-8 -*-
"""
LibreOffice UNO 매크로 스크립트 (Plan-37 Phase 3a)

LibreOffice 번들 Python 에서 실행됨. soffice 가 UNO 소켓을 띄우면 별도
Python 프로세스가 이 스크립트를 통해 문서 열기/수정/저장.

사용:
    python3 lo_macro.py <input.docx> <output.docx> <socket_port>

수행 작업:
  1. UNO 로 soffice 연결
  2. 문서 열기
  3. 헤딩 단락 순회:
     - ParaStyleName 이 "Heading N" / "제목 N" 패턴이면
     - NumberingIsNumber == True 인 경우 ListLabelString 을 단락 시작부에 삽입
     - NumberingIsNumber = False 로 번호 제거
     - 역순 처리 (Word COM 과 동일 이유)
  4. 전체 필드 refresh (SEQ·TOC)
  5. Word 2007 XML (.docx) 로 저장

LibreOffice 없이도 구문 검증 가능하도록 uno import 는 함수 내부에서.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


HEADING_PATTERN = re.compile(r"^(heading|제목)\s*\d", re.IGNORECASE)


def _file_url(path: str) -> str:
    """OS 파일 경로를 LibreOffice file:/// URL 로 변환."""
    import uno
    return uno.systemPathToFileUrl(str(Path(path).resolve()))


def _connect(port: int, tries: int = 30):
    """UNO 소켓 연결 (재시도 포함)."""
    import uno
    from com.sun.star.connection import NoConnectException
    import time

    local_ctx = uno.getComponentContext()
    resolver = local_ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local_ctx)
    url = (f"uno:socket,host=localhost,port={port};urp;"
           "StarOffice.ComponentContext")
    last_err = None
    for _ in range(tries):
        try:
            ctx = resolver.resolve(url)
            smgr = ctx.ServiceManager
            desktop = smgr.createInstanceWithContext(
                "com.sun.star.frame.Desktop", ctx)
            return ctx, smgr, desktop
        except NoConnectException as e:  # noqa
            last_err = e
            time.sleep(0.5)
    raise RuntimeError(f"UNO 연결 실패: {last_err}")


def _make_prop(name, value):
    from com.sun.star.beans import PropertyValue
    p = PropertyValue()
    p.Name = name
    p.Value = value
    return p


def _iter_paragraphs(doc):
    """doc 본문(Text) 의 단락 enumerator → paragraph 순회."""
    enum = doc.Text.createEnumeration()
    while enum.hasMoreElements():
        para = enum.nextElement()
        # 표 내부 요소는 TextTable → 지금은 스킵 (헤딩은 보통 본문 단락)
        if para.supportsService("com.sun.star.text.Paragraph"):
            yield para


def flatten_headings(doc):
    """헤딩 단락의 ListLabelString 을 텍스트로 삽입하고 번호 제거.

    2-pass:
      Pass 1: 헤딩 단락 + 현재 번호 수집
      Pass 2: 역순으로 NumberingIsNumber=False + 텍스트 prepend
    """
    targets = []
    for para in _iter_paragraphs(doc):
        style = getattr(para, "ParaStyleName", "") or ""
        if not HEADING_PATTERN.match(style):
            continue
        # NumberingIsNumber=False 인 단락은 번호가 이미 없거나 수동 타이핑
        if not getattr(para, "NumberingIsNumber", False):
            continue
        label = getattr(para, "ListLabelString", "") or ""
        if not label.strip():
            continue
        number_text = label.strip().rstrip(".")
        targets.append((para, number_text))

    if not targets:
        return 0

    # 역순 처리 — 앞쪽 단락 번호에 영향 없도록
    for para, number_text in reversed(targets):
        try:
            para.NumberingIsNumber = False
            # 단락 시작부에 텍스트 삽입
            # setPropertyValue('String', ...) 로 직접 대입하면 전체 교체되므로
            # Cursor 를 통해 prepend
            doc.Text.insertString(para.Start, number_text + " ", False)
        except Exception as e:
            # 단락별 실패는 스킵하고 계속
            print(f"heading 평문화 스킵: {e}", file=sys.stderr)

    return len(targets)


def update_fields(doc):
    """SEQ / TOC 등 필드 갱신."""
    try:
        # 본문 텍스트 필드
        enum = doc.getTextFields().createEnumeration()
        while enum.hasMoreElements():
            field = enum.nextElement()
            if hasattr(field, "refresh"):
                field.refresh()
    except Exception as e:
        print(f"필드 refresh 실패 (무시): {e}", file=sys.stderr)


def main():
    if len(sys.argv) < 4:
        print("usage: lo_macro.py <input.docx> <output.docx> <port>", file=sys.stderr)
        sys.exit(2)

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    port = int(sys.argv[3])

    ctx, smgr, desktop = _connect(port)

    load_props = [
        _make_prop("Hidden", True),
        _make_prop("ReadOnly", False),
        _make_prop("MacroExecutionMode", 0),  # 0 = NEVER (매크로 차단)
    ]
    doc = desktop.loadComponentFromURL(
        _file_url(input_path), "_blank", 0, tuple(load_props))

    if doc is None:
        print("문서 로드 실패", file=sys.stderr)
        sys.exit(3)

    try:
        n = flatten_headings(doc)
        update_fields(doc)

        save_props = [
            _make_prop("FilterName", "MS Word 2007 XML"),
            _make_prop("Overwrite", True),
        ]
        doc.storeToURL(_file_url(output_path), tuple(save_props))
        print(f"flattened={n} saved={output_path}")
    finally:
        try:
            doc.close(True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
