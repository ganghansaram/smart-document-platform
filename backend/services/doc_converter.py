"""
.doc (Word 97-2003) → .docx 변환 유틸리티

LibreOffice CLI (soffice --headless) 사용.
Windows에서 LibreOffice 미설치 시 COM(Word.Application) 폴백.
"""
import logging
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# LibreOffice 변환 타임아웃 (초)
CONVERSION_TIMEOUT = 60


def convert_doc_to_docx(doc_bytes: bytes) -> bytes:
    """`.doc` 바이트를 `.docx` 바이트로 변환한다.

    Returns:
        변환된 .docx 파일 바이트

    Raises:
        RuntimeError: 변환 도구를 찾을 수 없거나 변환 실패 시
    """
    tmpdir = tempfile.mkdtemp(prefix="doc2docx_")
    try:
        input_path = os.path.join(tmpdir, "input.doc")
        with open(input_path, "wb") as f:
            f.write(doc_bytes)

        # LibreOffice CLI 시도
        if _try_libreoffice(tmpdir, input_path):
            return _read_result(tmpdir)

        # Windows COM 폴백
        if platform.system() == "Windows" and _try_com(tmpdir, input_path):
            return _read_result(tmpdir)

        raise RuntimeError(
            ".doc 변환 실패: LibreOffice(soffice)를 찾을 수 없습니다. "
            "LibreOffice를 설치하거나 .docx 형식을 사용하세요."
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _try_libreoffice(tmpdir: str, input_path: str) -> bool:
    """LibreOffice CLI로 변환을 시도한다."""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        logger.debug("soffice/libreoffice 바이너리를 찾을 수 없음")
        return False

    profile_dir = os.path.join(tmpdir, "profile")
    env_uri = "file://" + profile_dir.replace("\\", "/")

    cmd = [
        soffice,
        "--headless",
        "--norestore",
        f"-env:UserInstallation={env_uri}",
        "--convert-to", "docx",
        "--outdir", tmpdir,
        input_path,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=CONVERSION_TIMEOUT,
        )
        if result.returncode != 0:
            logger.warning("LibreOffice 변환 실패: %s", result.stderr)
            return False

        output_path = os.path.join(tmpdir, "input.docx")
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info("LibreOffice .doc → .docx 변환 완료")
            return True

        logger.warning("LibreOffice 변환 결과 파일 없음")
        return False

    except FileNotFoundError:
        logger.debug("soffice 실행 실패 (FileNotFoundError)")
        return False
    except subprocess.TimeoutExpired:
        logger.warning("LibreOffice 변환 타임아웃 (%ds)", CONVERSION_TIMEOUT)
        return False


def _try_com(tmpdir: str, input_path: str) -> bool:
    """Windows COM(Word.Application)으로 변환을 시도한다."""
    try:
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        try:
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            word.DisplayAlerts = 0

            abs_input = os.path.abspath(input_path)
            output_path = os.path.join(tmpdir, "input.docx")
            abs_output = os.path.abspath(output_path)

            doc = word.Documents.Open(abs_input, ReadOnly=True)
            # SaveAs2 format 16 = wdFormatXMLDocument (.docx)
            doc.SaveAs2(abs_output, FileFormat=16)
            doc.Close(False)
            word.Quit()

            if os.path.exists(abs_output) and os.path.getsize(abs_output) > 0:
                logger.info("COM .doc → .docx 변환 완료")
                return True
            return False
        finally:
            pythoncom.CoUninitialize()

    except ImportError:
        logger.debug("pywin32 미설치 — COM 폴백 불가")
        return False
    except Exception as e:
        logger.warning("COM 변환 실패: %s", e)
        return False


def _read_result(tmpdir: str) -> bytes:
    """변환 결과 .docx 파일을 읽어 바이트로 반환한다."""
    output_path = os.path.join(tmpdir, "input.docx")
    with open(output_path, "rb") as f:
        return f.read()
