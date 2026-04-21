# -*- coding: utf-8 -*-
"""
DOCX 전처리 어댑터 패키지 — Plan-37

환경별 전처리 구현을 독립 모듈로 분리:
  - word_com.py       : Windows + MS Word COM (기존 word_preprocessor 이관)
  - libreoffice.py    : Linux + LibreOffice Headless (Phase 3 에 추가)
  - native.py         : Pure Python numbering.xml 파서 (Phase 4 에 추가)

Phase 1 시점에는 word_com 만 존재하며, 상위 shim (`../word_preprocessor.py`)
이 이 패키지를 참조해 하위 호환을 유지한다.
"""

from .word_com import preprocess_docx, preprocess_only, cleanup_stale_temp_files

__all__ = ["preprocess_docx", "preprocess_only", "cleanup_stale_temp_files"]
