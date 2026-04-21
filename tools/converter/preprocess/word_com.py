# -*- coding: utf-8 -*-
"""
Word COM 기반 DOCX 전처리 어댑터 (Windows + MS Word 필요)

기능:
  - 장절번호 평문화 — 헤딩의 자동번호(ListString)를 텍스트로 삽입 후 번호 제거
  - 필드 갱신 — SEQ(캡션 번호), TOC 등 일괄 refresh
  - DRM 우회 — `.docx_1` 확장자로 저장해 Windows DRM 재적용 회피
    python-docx 는 ZIP 시그니처로 읽으므로 확장자와 무관하게 정상 파싱

배경:
  Plan-37 §3 Phase 1c — standalone 의 word_preprocessor 를 엔진 SSOT 로 이관.
  하위 호환: `../word_preprocessor.py` 가 shim 으로 유지되어 기존 import 경로 보존.
"""
import glob
import os
import re
import time
import logging
import tempfile
from pathlib import Path
from typing import Optional

from .base import PreprocessAdapter, PreprocessResult

logger = logging.getLogger(__name__)


# 헤딩 스타일 이름 패턴: "Heading 1", "제목 1", "heading 2" 등
_HEADING_PATTERN = re.compile(r"^(heading|제목)\s*\d", re.IGNORECASE)

# 임시파일 접두사·확장자 규약
_TEMP_PREFIX = "preprocessed_"
_TEMP_SUFFIX = ".docx_1"  # Windows DRM 재적용 우회용


def _get_temp_dir():
    """Explorer 백엔드에서 호출 시 `config.UPLOAD_TEMP_DIR` 참조.
    standalone 등 config 없는 환경에선 None (시스템 기본 temp 사용)."""
    try:
        from config import UPLOAD_TEMP_DIR  # type: ignore
        if UPLOAD_TEMP_DIR:
            os.makedirs(UPLOAD_TEMP_DIR, exist_ok=True)
            return UPLOAD_TEMP_DIR
    except ImportError:
        pass
    return None


def preprocess_docx(input_path: str, output_path: str = None) -> str:
    """Word COM 으로 DOCX 전처리 (장절번호 평문화 + 필드 갱신).

    DRM 우회: 저장 확장자를 `.docx_1` 로 사용. python-docx 는 ZIP 시그니처로
    읽으므로 확장자 무관하게 동작하며, Windows DRM 은 `.docx` 패턴만 잠그므로
    저장 단계에서 재잠김 방지.

    Args:
        input_path: 원본 DOCX 파일 경로
        output_path: 결과 저장 경로 (None 이면 임시 파일 자동 생성)

    Returns:
        전처리된 파일 경로. COM 실패 시 input_path 그대로 반환.
    """
    try:
        import win32com.client
        import pythoncom
    except ImportError:
        logger.warning("pywin32 미설치 — 장절번호 전처리를 건너뜁니다.")
        return input_path

    input_path = str(Path(input_path).resolve())

    if output_path is None:
        temp_dir = _get_temp_dir()
        fd, output_path = tempfile.mkstemp(
            suffix=_TEMP_SUFFIX, prefix=_TEMP_PREFIX, dir=temp_dir)
        os.close(fd)
    else:
        output_path = str(Path(output_path).resolve())

    word = None
    doc = None
    try:
        pythoncom.CoInitialize()
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = False

        doc = word.Documents.Open(input_path, ReadOnly=True)

        _flatten_heading_numbers(doc)
        _update_fields(doc)

        # SaveAs2: FileFormat 12 = docx (확장자는 .docx_1 로 저장해도 내용은 docx)
        doc.SaveAs2(output_path, FileFormat=12)
        logger.info("DOCX 전처리 완료: %s", output_path)
        return output_path

    except Exception as e:
        logger.warning("DOCX 전처리 실패 (원본 사용): %s", e)
        if output_path != input_path and os.path.exists(output_path):
            try:
                os.unlink(output_path)
            except OSError:
                pass
        return input_path

    finally:
        try:
            if doc is not None:
                doc.Close(False)
        except Exception:
            pass
        try:
            if word is not None:
                word.Quit()
        except Exception:
            pass
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


def preprocess_only(input_path: str, output_path: str) -> str:
    """전처리만 수행하여 `.docx` 로 저장 (DRM 환경용 2단계 모드).

    흐름:
      1단계: 이 함수로 장절번호 평문화된 `.docx` 생성
      2단계: 사용자가 DRM 해제 후 변환기에 투입

    Args:
        input_path: 원본 DOCX 파일 경로
        output_path: 결과 저장 경로 (`.docx`)

    Returns:
        저장된 파일 경로. 실패 시 None.
    """
    try:
        import win32com.client
        import pythoncom
    except ImportError:
        logger.error("pywin32 미설치 — 전처리를 수행할 수 없습니다.")
        return None

    input_path = str(Path(input_path).resolve())
    output_path = str(Path(output_path).resolve())

    word = None
    doc = None
    try:
        pythoncom.CoInitialize()
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = False

        doc = word.Documents.Open(input_path, ReadOnly=True)
        _flatten_heading_numbers(doc)
        _update_fields(doc)

        doc.SaveAs2(output_path, FileFormat=12)
        logger.info("전처리 전용 저장 완료: %s", output_path)
        return output_path

    except Exception as e:
        logger.error("전처리 실패: %s", e)
        return None

    finally:
        try:
            if doc is not None:
                doc.Close(False)
        except Exception:
            pass
        try:
            if word is not None:
                word.Quit()
        except Exception:
            pass
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


class WordComAdapter(PreprocessAdapter):
    """디스패처용 어댑터 — 함수형 preprocess_docx 를 PreprocessAdapter 인터페이스로 래핑."""

    name = "word_com"

    def is_available(self) -> bool:
        """pywin32 설치 + Word COM dispatch 가능 여부."""
        try:
            import win32com.client  # noqa: F401
            import pythoncom  # noqa: F401
        except ImportError:
            return False
        # 실제 Word 설치까지 확인하면 Word 기동 비용이 들므로, pywin32 만 확인.
        # 실행 시점에 Dispatch 실패하면 preprocess() 가 fallback 처리.
        return os.name == 'nt'

    def preprocess(self, input_path: str,
                   output_path: Optional[str] = None) -> PreprocessResult:
        result_path = preprocess_docx(input_path, output_path)
        # 성공 판정: 결과가 원본과 같은 절대경로인지 비교
        # (preprocess_docx 는 실패 시 input 을 resolve 한 절대경로 반환)
        try:
            same_file = Path(result_path).resolve() == Path(input_path).resolve()
        except OSError:
            same_file = result_path == input_path
        ok = not same_file
        return PreprocessResult(
            path=result_path,
            adapter=self.name,
            ok=ok,
            error=None if ok else "preprocess_docx returned original (COM 실패 또는 스킵)",
        )


def cleanup_stale_temp_files(max_age_seconds: int = 86400) -> int:
    """서버 크래시·비정상 종료로 남은 `preprocessed_*.docx_1` 임시파일 정리.

    FastAPI startup event 에서 호출 권장. 24h 이상 된 파일만 삭제.

    Args:
        max_age_seconds: 이 시간보다 오래된 파일만 삭제 (기본 24h)

    Returns:
        삭제된 파일 수
    """
    temp_dir = _get_temp_dir() or tempfile.gettempdir()
    pattern = os.path.join(temp_dir, f"{_TEMP_PREFIX}*{_TEMP_SUFFIX}")
    cutoff = time.time() - max_age_seconds
    removed = 0
    for path in glob.glob(pattern):
        try:
            if os.path.getmtime(path) < cutoff:
                os.unlink(path)
                removed += 1
        except OSError:
            pass
    if removed:
        logger.info("stale preprocessed 파일 %d개 정리 (temp=%s)", removed, temp_dir)
    return removed


def _flatten_heading_numbers(doc):
    """헤딩 단락의 자동번호를 텍스트로 삽입하고 번호 서식을 제거.

    2-pass 방식: RemoveNumbers() 가 후속 단락의 번호를 리셋하므로
    먼저 모든 번호를 수집한 뒤, 역순으로 제거+삽입한다.
    """
    targets = []
    for i, para in enumerate(doc.Paragraphs):
        style_name = para.Style.NameLocal
        if not _HEADING_PATTERN.match(style_name):
            continue

        list_string = para.Range.ListFormat.ListString
        if not list_string or not list_string.strip():
            continue

        number_text = list_string.strip().rstrip(".")
        targets.append((i + 1, number_text))  # Paragraphs 는 1-based

    if not targets:
        return

    for para_index, number_text in reversed(targets):
        para = doc.Paragraphs(para_index)
        para.Range.ListFormat.RemoveNumbers()
        para.Range.InsertBefore(number_text + " ")

    logger.info("장절번호 평문화: %d개 헤딩 처리", len(targets))


def _update_fields(doc):
    """문서 내 모든 필드 갱신 (SEQ, TOC 등)."""
    try:
        for story_range in doc.StoryRanges:
            story_range.Fields.Update()
    except Exception as e:
        logger.warning("필드 갱신 중 오류 (무시): %s", e)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if len(sys.argv) < 2:
        print("사용법: python -m preprocess.word_com <입력.docx> [출력]")
        sys.exit(1)

    src = sys.argv[1]
    if not os.path.isfile(src):
        print(f"파일을 찾을 수 없습니다: {src}")
        sys.exit(1)

    dst = sys.argv[2] if len(sys.argv) >= 3 else None
    result = preprocess_docx(src, dst)
    if result == src:
        print("전처리 실패 — 원본이 그대로 반환되었습니다.")
        sys.exit(1)
    print(f"완료: {result}")
