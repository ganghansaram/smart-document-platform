# -*- coding: utf-8 -*-
"""
하위 호환 Shim — `preprocess.word_com` 으로 이관됨 (Plan-37 Phase 1c)

기존 호출부:
    from word_preprocessor import preprocess_docx
가 계속 동작하도록 유지. 신규 코드는 `preprocess.word_com` 또는
`preprocess` 패키지를 직접 import 권장.
"""
from preprocess.word_com import (  # noqa: F401
    preprocess_docx,
    preprocess_only,
    cleanup_stale_temp_files,
)


if __name__ == "__main__":
    # 기존 CLI 호환 — preprocess.word_com 의 __main__ 블록 위임
    import runpy
    import sys
    # -m preprocess.word_com <args>  와 동일하게 실행
    sys.argv[0] = "preprocess.word_com"
    runpy.run_module("preprocess.word_com", run_name="__main__")
