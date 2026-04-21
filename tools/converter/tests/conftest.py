# -*- coding: utf-8 -*-
"""
Plan-37 Phase 0 — pytest 공통 설정

fixture DOCX 경로 선언, sys.path 설정, 공통 helper.
경로·카탈로그 상수는 `_paths.py` (pytest 의존성 없음) 에서 import.
"""
import sys
from pathlib import Path

# pytest 실행 시 이 디렉토리가 sys.path 에 없으면 _paths 를 못 찾음
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

import pytest

from _paths import (  # noqa: F401
    TESTS_DIR, CONVERTER_DIR, PROJECT_ROOT, SAMPLES_DIR, GOLDEN_DIR,
    FIXTURE_CATALOG,
)

# converter 모듈 import 가능하게 sys.path 조정
if str(CONVERTER_DIR) not in sys.path:
    sys.path.insert(0, str(CONVERTER_DIR))


def _fixture_docx_path(rel_path: str) -> Path:
    """fixture DOCX 의 절대 경로 반환. 존재하지 않으면 skip."""
    p = SAMPLES_DIR / rel_path
    if not p.exists():
        pytest.skip(f"Fixture 문서 없음: {p}")
    return p


@pytest.fixture(params=[f[0] for f in FIXTURE_CATALOG], ids=[f[0] for f in FIXTURE_CATALOG])
def fixture_case(request):
    """pytest parametrize fixture — 각 fixture 에 대해 테스트 반복 실행.

    반환 dict:
      - id: fixture 식별자
      - docx: 원본 DOCX 경로 (Path)
      - golden: 골든 HTML 경로 (Path, 존재하지 않을 수도 있음)
      - description: 설명 문자열
    """
    for entry in FIXTURE_CATALOG:
        if entry[0] == request.param:
            fid, rel_path, desc = entry
            return {
                "id": fid,
                "docx": _fixture_docx_path(rel_path),
                "golden": GOLDEN_DIR / f"{fid}.html",
                "description": desc,
            }
    pytest.fail(f"Unknown fixture id: {request.param}")


# ───────────────────────────────────────────────────────────────
# 공통 helper
# ───────────────────────────────────────────────────────────────

def run_current_converter(docx_path: Path, output_dir: Path, use_word_com: bool = False) -> Path:
    """현 Explorer converter 경로로 DOCX → HTML 변환.

    Phase 0 에선 `WORD_COM_PREPROCESS` 기본 False → preprocessing 없이 변환.
    use_word_com=True 로 명시 호출 시에만 Word COM 전처리 실행.

    Returns:
        변환된 HTML 파일 경로.
    """
    from converter import DocxConverter
    output_dir.mkdir(parents=True, exist_ok=True)
    output_html = output_dir / (docx_path.stem + ".html")

    preprocessed = None
    try:
        if use_word_com:
            try:
                from word_preprocessor import preprocess_docx
                preprocessed = preprocess_docx(str(docx_path))
            except Exception as e:
                # Word COM 실패 시 원본 사용 (로그만)
                import logging
                logging.getLogger(__name__).warning(
                    "Word COM preprocess 실패, 원본 사용: %s", e)
                preprocessed = None

        convert_input = preprocessed or str(docx_path)
        conv = DocxConverter(config_path=str(CONVERTER_DIR / "config.json"))
        result = conv.convert(convert_input, str(output_html))
        if not result.success:
            pytest.fail(f"변환 실패: {result.error_message}")
        return output_html

    finally:
        if preprocessed and preprocessed != str(docx_path):
            try:
                Path(preprocessed).unlink(missing_ok=True)
            except OSError:
                pass
