#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DOCX → HTML 독립 변환기 (래퍼)

듀얼 모드:
  - 인자 없이 실행 → GUI
  - 인자 있으면   → CLI

엔진 위치 (Plan-37 Phase 2):
  - 개발 모드 (직접 실행): `../converter/` 를 sys.path 에 추가
  - PyInstaller 번들: `sys._MEIPASS` 에 엔진 파일들이 복사되어 있음 (spec 참조)
"""

import sys
import os
import re
import argparse
import logging
from pathlib import Path


def _setup_engine_import_path():
    """엔진 모듈을 import 할 수 있도록 sys.path 설정.

    - PyInstaller 번들 (sys.frozen=True): `_MEIPASS` 에 엔진 파일이 이미 복사되어
      있으므로 추가 작업 불필요.
    - 개발 모드: `../converter/` 를 sys.path 에 삽입하여 엔진 파일 로드 가능.
    """
    if getattr(sys, 'frozen', False):
        return  # PyInstaller 번들은 _MEIPASS 에서 자동 해결
    engine_dir = Path(__file__).resolve().parent.parent / 'converter'
    engine_str = str(engine_dir)
    if engine_str not in sys.path:
        sys.path.insert(0, engine_str)


_setup_engine_import_path()

# 전처리(Word COM) 행 방지용 타임아웃 (초) — 초과 시 Word 강제 종료 후 원본 변환
PREPROCESS_TIMEOUT = 90


def get_base_dir():
    """PyInstaller 번들 또는 스크립트 디렉토리 반환 (레거시 호환)"""
    return Path(getattr(sys, '_MEIPASS', Path(__file__).parent))


def _kill_word():
    """잔존 WINWORD 프로세스 강제 종료 (Windows 한정)."""
    if os.name != 'nt':
        return
    try:
        import subprocess
        subprocess.run(['taskkill', '/F', '/IM', 'WINWORD.EXE'],
                       capture_output=True, timeout=15)
    except Exception:
        pass


def _preprocess_with_timeout(input_path, timeout_sec, logger):
    """장절번호 평문화를 타임아웃 가드와 함께 실행.

    Word COM 이 특정 문서(외부 링크 등)에서 멈추는 사례가 있어, 별도 스레드로
    실행하고 timeout_sec 초과 시 Word 를 강제 종료하여 원본으로 폴백한다.

    Returns: (실제_입력경로, adapter_라벨)
    """
    import threading
    box = {"path": str(input_path)}

    def _work():
        try:
            from word_preprocessor import preprocess_docx
            box["path"] = preprocess_docx(str(input_path))
        except Exception as e:
            logger.warning("전처리 실패 (원본 사용): %s", e)

    t = threading.Thread(target=_work, daemon=True)
    t.start()
    t.join(timeout_sec)

    if t.is_alive():
        logger.warning("전처리 타임아웃(%ds) — Word 강제 종료 후 원본으로 변환합니다.",
                       timeout_sec)
        _kill_word()
        t.join(5)
        return str(input_path), "word_com_timeout"

    if box["path"] != str(input_path):
        return box["path"], "word_com"
    return str(input_path), "word_com_failed"


def _load_webbook_css():
    """번들된 표시용 CSS 로드 (없으면 빈 문자열)."""
    base_dir = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
    css_path = base_dir / "webbook-content.css"
    try:
        return css_path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _wrap_output_with_style(output_path, logger):
    """변환 결과(본문 조각)를 표시용 CSS 와 함께 자기완결 HTML 로 감싼다.

    결과 형태: [provenance 주석] + <style>…</style> + <div class="docx-content">…</div>
    웹북이 출력을 그대로 삽입해도 본사 화면과 동일하게 보이도록 한다.
    """
    css = _load_webbook_css()
    if not css:
        logger.warning("표시용 CSS 를 찾지 못해 스타일 내장을 건너뜁니다.")
        return
    p = Path(output_path)
    try:
        html = p.read_text(encoding="utf-8")
    except OSError as e:
        logger.warning("출력 HTML 재읽기 실패 — 스타일 내장 생략: %s", e)
        return

    # provenance 주석은 최상단에 유지
    prov = ""
    m = re.match(r'(<!--\s*converter:.*?-->\s*)', html, re.DOTALL)
    if m:
        prov = m.group(1)
        html = html[m.end():]

    wrapped = (f'{prov}<style>\n{css}\n</style>\n'
               f'<div class="docx-content">\n{html}\n</div>\n')
    p.write_text(wrapped, encoding="utf-8")


def run_cli(args=None):
    """CLI 모드 실행"""
    parser = argparse.ArgumentParser(
        prog='docx2html',
        description='DOCX 파일을 HTML로 변환합니다.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  docx2html 매뉴얼.docx
  docx2html 매뉴얼.docx -o output/
  docx2html 매뉴얼.docx --html-name content.html --image-dir img
  docx2html 매뉴얼.docx --image-prefix /static/images/
  docx2html 매뉴얼.docx --no-preprocess
"""
    )
    parser.add_argument('input', help='변환할 DOCX 파일 경로')
    parser.add_argument('-o', '--output', default=None,
                        help='출력 디렉토리 (기본: 입력파일 위치)')
    parser.add_argument('--html-name', default=None,
                        help='출력 HTML 파일명 (기본: 입력파일명.html)')
    parser.add_argument('--image-dir', default=None,
                        help='이미지 폴더명 (기본: {파일명}_images)')
    parser.add_argument('--image-prefix', default=None,
                        help='HTML 내 이미지 경로 접두사 (기본: 상대경로)')
    parser.add_argument('--preprocess', action='store_true',
                        help='장절번호 평문화 켜기 (Word 설치 필요, 기본 꺼짐). '
                             '미지정 시 변환기 자체 번호 생성 사용')
    parser.add_argument('--no-preprocess', action='store_true',
                        help='(기본값) 장절번호 평문화 건너뛰기 — 하위호환용')
    parser.add_argument('--no-style', action='store_true',
                        help='출력에 표시용 CSS 내장하지 않고 본문 조각만 출력')
    parser.add_argument('--preprocess-only', action='store_true',
                        help='전처리만 수행 (DRM 환경용, .docx 출력)')
    parser.add_argument('--verbose', action='store_true',
                        help='상세 로그 출력')

    parsed = parser.parse_args(args)

    # 로깅 설정
    log_level = logging.DEBUG if parsed.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger = logging.getLogger('docx2html')

    # 입력 파일 검증
    input_path = Path(parsed.input).resolve()
    if not input_path.exists():
        logger.error("파일을 찾을 수 없습니다: %s", input_path)
        return 2

    if input_path.suffix.lower() != '.docx':
        logger.error("지원하지 않는 파일 형식입니다: %s", input_path.suffix)
        return 2

    # 출력 경로 결정
    if parsed.output:
        output_dir = Path(parsed.output).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = input_path.parent

    if parsed.html_name:
        html_name = parsed.html_name
        if not html_name.endswith('.html'):
            html_name += '.html'
        output_path = output_dir / html_name
    else:
        output_path = output_dir / input_path.with_suffix('.html').name

    # 전처리 전용 모드
    if parsed.preprocess_only:
        preprocess_out = output_dir / f"{input_path.stem}_preprocessed.docx"
        try:
            from word_preprocessor import preprocess_only
            result_path = preprocess_only(str(input_path), str(preprocess_out))
            if result_path:
                logger.info("전처리 완료: %s", result_path)
                print(str(result_path))
                return 0
            else:
                logger.error("전처리 실패")
                return 1
        except Exception as e:
            logger.error("전처리 중 오류: %s", e)
            return 1

    # 전처리 (장절번호 평문화) — 기본 OFF. --preprocess 로만 켜며, Word COM
    # 행 방지를 위해 타임아웃 가드와 함께 실행. 미사용 시 변환기 자체 번호 생성.
    actual_input = input_path
    adapter_used = "skip"
    if parsed.preprocess and not parsed.no_preprocess:
        actual_str, adapter_used = _preprocess_with_timeout(
            input_path, PREPROCESS_TIMEOUT, logger)
        actual_input = Path(actual_str)
        if adapter_used == "word_com":
            logger.info("전처리 완료: %s", actual_input)

    # 변환 실행
    try:
        from converter import DocxConverter
        converter = DocxConverter()
        result = converter.convert(
            str(actual_input),
            str(output_path),
            image_dir_name=parsed.image_dir,
            image_prefix=parsed.image_prefix,
            provenance_adapter=adapter_used,
        )

        if result.success:
            # 표시용 CSS 내장 (기본) — 웹북이 출력을 그대로 삽입해도 본사와 동일 표시
            if not parsed.no_style:
                _wrap_output_with_style(result.output_path, logger)
            logger.info("변환 완료: %s", result.output_path)
            # stdout에 결과 경로 출력 (프로세스 연동용)
            print(str(result.output_path))
            if result.warnings:
                for w in result.warnings:
                    logger.warning("  %s", w)
            return 0
        else:
            logger.error("변환 실패: %s", result.error_message)
            return 1

    except Exception as e:
        logger.error("변환 중 오류: %s", e)
        return 1

    finally:
        # 전처리 임시 파일 정리
        if actual_input != input_path and actual_input.exists():
            try:
                actual_input.unlink()
            except OSError:
                pass


def run_gui():
    """GUI 모드 실행"""
    try:
        from gui import DocxConverterGUI
        app = DocxConverterGUI()
        app.run()
    except ImportError as e:
        print(f"GUI 모듈 로드 실패: {e}", file=sys.stderr)
        print("CLI 모드를 사용하세요: docx2html --help", file=sys.stderr)
        return 1
    return 0


def main():
    """메인 진입점: 인자 유무로 CLI/GUI 분기"""
    if len(sys.argv) > 1:
        sys.exit(run_cli())
    else:
        sys.exit(run_gui())


if __name__ == '__main__':
    main()
