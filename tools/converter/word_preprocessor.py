"""
Word COM 기반 DOCX 전처리 모듈

- 장절번호 평문화: 헤딩의 자동번호(ListString)를 텍스트로 삽입 후 번호 제거
- 필드 갱신: SEQ 필드(캡션 번호), 목차 등 일괄 갱신
- COM 실패 시 원본 파일을 그대로 반환 (graceful fallback)
"""
import os
import re
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_temp_dir():
    """config.py의 UPLOAD_TEMP_DIR 설정을 참조. 없으면 시스템 기본 temp 사용."""
    try:
        # backend에서 호출될 때 config 모듈 접근
        from config import UPLOAD_TEMP_DIR
        if UPLOAD_TEMP_DIR:
            os.makedirs(UPLOAD_TEMP_DIR, exist_ok=True)
            return UPLOAD_TEMP_DIR
    except ImportError:
        pass
    return None  # None이면 tempfile이 시스템 기본 사용


def preprocess_docx(input_path: str, output_path: str = None) -> str:
    """Word COM으로 DOCX 전처리 (장절번호 평문화 + 필드 갱신)

    Args:
        input_path: 원본 DOCX 파일 경로
        output_path: 결과 저장 경로 (None이면 임시 파일 생성)

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
        fd, output_path = tempfile.mkstemp(suffix=".docx", prefix="preprocessed_", dir=temp_dir)
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

        # SaveAs2: FileFormat 12 = docx
        doc.SaveAs2(output_path, FileFormat=12)
        logger.info("DOCX 전처리 완료: %s", output_path)
        return output_path

    except Exception as e:
        logger.warning("DOCX 전처리 실패 (원본 사용): %s", e)
        # 실패 시 임시 파일 정리
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


# 헤딩 스타일 이름 패턴: "Heading 1", "제목 1", "heading 2" 등
_HEADING_PATTERN = re.compile(r"^(heading|제목)\s*\d", re.IGNORECASE)


def _flatten_heading_numbers(doc):
    """헤딩 단락의 자동번호를 텍스트로 삽입하고 번호 서식을 제거

    2-pass 방식: RemoveNumbers()가 후속 단락의 번호를 리셋하므로
    먼저 모든 번호를 수집한 뒤, 역순으로 제거+삽입한다.
    """
    # Pass 1: 번호 수집
    targets = []
    for i, para in enumerate(doc.Paragraphs):
        style_name = para.Style.NameLocal
        if not _HEADING_PATTERN.match(style_name):
            continue

        list_string = para.Range.ListFormat.ListString
        if not list_string or not list_string.strip():
            continue

        number_text = list_string.strip().rstrip(".")  # 후행 점 제거 (1.1. → 1.1)
        targets.append((i + 1, number_text))  # Paragraphs는 1-based

    if not targets:
        return

    # Pass 2: 역순으로 적용 (뒤에서부터 처리하면 앞쪽 번호에 영향 없음)
    for para_index, number_text in reversed(targets):
        para = doc.Paragraphs(para_index)
        para.Range.ListFormat.RemoveNumbers()
        para.Range.InsertBefore(number_text + " ")

    logger.info("장절번호 평문화: %d개 헤딩 처리", len(targets))


def _update_fields(doc):
    """문서 내 모든 필드 갱신 (SEQ, TOC 등)"""
    try:
        for story_range in doc.StoryRanges:
            story_range.Fields.Update()
    except Exception as e:
        logger.warning("필드 갱신 중 오류 (무시): %s", e)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if len(sys.argv) < 2:
        print("사용법: python word_preprocessor.py <입력.docx> [출력.docx]")
        print("  출력 경로 생략 시 입력파일명_preprocessed.docx로 저장")
        sys.exit(1)

    src = sys.argv[1]
    if not os.path.isfile(src):
        print(f"파일을 찾을 수 없습니다: {src}")
        sys.exit(1)

    if len(sys.argv) >= 3:
        dst = sys.argv[2]
    else:
        p = Path(src)
        dst = str(p.parent / f"{p.stem}_preprocessed{p.suffix}")

    result = preprocess_docx(src, dst)

    if result == src:
        print("전처리 실패 — 원본이 그대로 반환되었습니다.")
        sys.exit(1)
    else:
        print(f"완료: {result}")
