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


def get_base_dir():
    """PyInstaller 번들 또는 스크립트 디렉토리 반환 (레거시 호환)"""
    return Path(getattr(sys, '_MEIPASS', Path(__file__).parent))


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
    parser.add_argument('--no-preprocess', action='store_true',
                        help='장절번호 평문화 건너뛰기')
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

    # 전처리 (장절번호 평문화)
    actual_input = input_path
    adapter_used = "skip"
    if not parsed.no_preprocess:
        try:
            from word_preprocessor import preprocess_docx
            preprocessed = preprocess_docx(str(input_path))
            if preprocessed != str(input_path):
                actual_input = Path(preprocessed)
                adapter_used = "word_com"
                logger.info("전처리 완료: %s", actual_input)
            else:
                adapter_used = "word_com_failed"
        except Exception as e:
            logger.warning("전처리 실패 (원본 사용): %s", e)
            print(f"[경고] 전처리 실패: {e} — 원본 파일로 변환합니다.", file=sys.stderr)
            adapter_used = "word_com_error"

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
