# -*- coding: utf-8 -*-
"""
LibreOffice Headless 전처리 어댑터 (Plan-37 Phase 3a)

Linux Docker (Word COM 없는) 환경에서 DOCX 전처리를 담당.
Windows/Word 환경에서는 디스패처가 word_com 을 우선하므로 이 어댑터는 폴백.

구현:
  방법 B (preferred): UNO 매크로로 heading 평문화 + Fields refresh
    - soffice 를 소켓 서버로 기동
    - 별도 Python 프로세스에서 lo_macro.py 실행 → UNO 연결 → 문서 편집 → 저장
    - Word COM 과 동등 결과 보장
  방법 A (fallback): 단순 재저장 (--convert-to docx)
    - Fields.Update 자동 수행 (LibreOffice 가 저장 시 캐시 갱신)
    - heading 평문화는 안 됨 (Phase 4 native numbering parser 로 담당)

보안 방어선:
  --safe-mode: 매크로·외부 참조·extension 전면 차단
  --headless --norestore --nologo: 불필요 UI 제거
  폐쇄망 환경이라 외부 통신은 이미 차단, 추가로 악성 macro 포함 DOCX 대응.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

from .base import PreprocessAdapter, PreprocessResult

logger = logging.getLogger(__name__)


class LibreOfficeAdapter(PreprocessAdapter):
    """LibreOffice Headless 전처리 어댑터."""

    name = "libreoffice"

    # soffice 공통 플래그 (모든 호출에 적용)
    SAFE_FLAGS = [
        "--headless",            # GUI 없이
        "--norestore",           # 충돌 복구 다이얼로그 차단
        "--nologo",              # 시작 로고 차단
        "--nofirststartwizard",  # 첫 실행 마법사 차단
        "--safe-mode",           # 매크로·외부 참조·extension 전면 차단
    ]

    # UNO 소켓 포트 (하드코딩 대신 사용자별 고정 고유값)
    UNO_PORT = 2202

    # subprocess timeout (초)
    TIMEOUT_SOFFICE_CONVERT = 120
    TIMEOUT_UNO_SERVER_START = 30
    TIMEOUT_UNO_MACRO = 180

    def is_available(self) -> bool:
        """soffice 실행파일 PATH 존재 여부."""
        return self._find_soffice() is not None

    def preprocess(self, input_path: str,
                   output_path: Optional[str] = None) -> PreprocessResult:
        soffice = self._find_soffice()
        if not soffice:
            return PreprocessResult(
                path=input_path, adapter=self.name, ok=False,
                error="soffice not found in PATH",
            )

        if output_path is None:
            fd, output_path = tempfile.mkstemp(
                suffix=".docx", prefix="preprocessed_lo_")
            os.close(fd)

        # 방법 B 시도 → 실패 시 방법 A 폴백
        try:
            n = self._preprocess_uno(soffice, input_path, output_path)
            logger.info("LibreOffice UNO 매크로 완료: headings=%d output=%s",
                        n, output_path)
            return PreprocessResult(
                path=output_path, adapter=self.name, ok=True,
            )
        except Exception as e:
            logger.warning("UNO 매크로 실패, 단순 재저장으로 폴백: %s", e)

        try:
            self._preprocess_simple(soffice, input_path, output_path)
            logger.info("LibreOffice 단순 재저장 완료: %s", output_path)
            return PreprocessResult(
                path=output_path, adapter=self.name, ok=True,
            )
        except Exception as e:
            # 모든 경로 실패
            try:
                os.unlink(output_path)
            except OSError:
                pass
            return PreprocessResult(
                path=input_path, adapter=self.name, ok=False,
                error=f"both UNO and simple-convert failed: {e}",
            )

    # ── 내부 구현 ─────────────────────────────────────────────────

    def _find_soffice(self) -> Optional[str]:
        """soffice 실행파일 탐색 (PATH 우선, 일반 설치 경로 fallback)."""
        for name in ("soffice", "libreoffice"):
            path = shutil.which(name)
            if path:
                return path
        # Linux 표준 경로
        for candidate in (
            "/usr/bin/soffice",
            "/usr/bin/libreoffice",
            "/opt/libreoffice/program/soffice",
        ):
            if os.path.isfile(candidate):
                return candidate
        return None

    def _preprocess_simple(self, soffice: str, input_path: str, output_path: str):
        """방법 A: soffice --convert-to docx.

        장점: 단순, Fields.Update 자동
        단점: heading 평문화 안 됨 (Phase 4 에서 numbering.xml 로 처리)
        """
        out_dir = tempfile.mkdtemp(prefix="lo_out_")
        try:
            cmd = [soffice] + self.SAFE_FLAGS + [
                "--convert-to", "docx:MS Word 2007 XML",
                "--outdir", out_dir,
                input_path,
            ]
            subprocess.run(
                cmd, check=True, timeout=self.TIMEOUT_SOFFICE_CONVERT,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            result_file = Path(out_dir) / (Path(input_path).stem + ".docx")
            if not result_file.exists():
                raise RuntimeError(f"LibreOffice output missing: {result_file}")
            shutil.move(str(result_file), output_path)
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

    def _preprocess_uno(self, soffice: str, input_path: str, output_path: str) -> int:
        """방법 B: UNO 매크로로 heading 평문화 + Fields refresh.

        Returns:
            평문화된 heading 개수 (성공 시).
        Raises:
            Exception — 연결 실패·매크로 실행 실패 등.
        """
        # 고유 user profile (동시 실행 충돌 방지)
        profile_dir = tempfile.mkdtemp(prefix="lo_profile_")
        profile_url = Path(profile_dir).as_uri()

        # soffice 를 UNO 소켓 서버로 기동
        server_cmd = [soffice] + self.SAFE_FLAGS + [
            f"-env:UserInstallation={profile_url}",
            f"--accept=socket,host=localhost,port={self.UNO_PORT};urp;",
        ]
        server_proc = subprocess.Popen(
            server_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        try:
            # soffice 기동 대기 (포트 리스닝)
            time.sleep(2)

            # lo_macro.py 실행 — LibreOffice 번들 Python 사용 권장
            # (시스템 Python 으로는 uno import 안 됨)
            macro_py = Path(__file__).parent / "lo_macro.py"
            lo_python = self._find_lo_python(soffice)
            if not lo_python:
                raise RuntimeError("LibreOffice 번들 Python 을 찾을 수 없습니다")

            cmd = [lo_python, str(macro_py), input_path, output_path,
                   str(self.UNO_PORT)]
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=self.TIMEOUT_UNO_MACRO,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"lo_macro.py 실패 (rc={result.returncode}): {result.stderr}"
                )

            # "flattened=N saved=..." 파싱
            flat = 0
            for line in result.stdout.splitlines():
                if line.startswith("flattened="):
                    try:
                        flat = int(line.split()[0].split("=")[1])
                    except (IndexError, ValueError):
                        pass
            return flat

        finally:
            # soffice 서버 종료
            try:
                server_proc.terminate()
                server_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_proc.kill()
            shutil.rmtree(profile_dir, ignore_errors=True)

    def _find_lo_python(self, soffice_path: str) -> Optional[str]:
        """LibreOffice 번들 Python 탐색."""
        soffice_dir = Path(soffice_path).parent
        candidates = [
            soffice_dir / "python",
            soffice_dir / "python.bin",
            soffice_dir.parent / "program" / "python",
            Path("/usr/bin/python3"),  # Debian/Ubuntu: python3-uno 시스템 패키지 사용 가능
        ]
        for c in candidates:
            if c.is_file() and os.access(c, os.X_OK):
                return str(c)
        return None
