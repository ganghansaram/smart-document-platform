#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DOCX to HTML Converter - 유틸리티
"""

import logging
import os
from pathlib import Path
from datetime import datetime


# ===== 커스텀 예외 클래스 =====

class ConverterError(Exception):
    """변환기 기본 예외"""
    pass


class FileNotFoundError(ConverterError):
    """파일을 찾을 수 없음"""
    pass


class InvalidFileError(ConverterError):
    """잘못된 파일 형식"""
    pass


class ConversionError(ConverterError):
    """변환 중 오류 발생"""
    pass


class ImageExtractionError(ConverterError):
    """이미지 추출 오류"""
    pass


# ===== 로깅 설정 =====

def setup_logging(log_dir=None, log_level=logging.INFO):
    """
    로깅 설정

    Args:
        log_dir: 로그 파일 저장 디렉토리 (None이면 콘솔만)
        log_level: 로그 레벨

    Returns:
        logging.Logger: 설정된 로거
    """
    logger = logging.getLogger('docx_converter')
    logger.setLevel(log_level)

    # 기존 핸들러 제거
    logger.handlers.clear()

    # 포맷 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 파일 핸들러 (log_dir이 지정된 경우)
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = log_dir / f'converter_{timestamp}.log'

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger():
    """
    기존 로거 반환 또는 새로 생성

    Returns:
        logging.Logger
    """
    logger = logging.getLogger('docx_converter')
    if not logger.handlers:
        setup_logging()
    return logger


# ===== 경로 유틸리티 =====

def ensure_dir(path):
    """
    디렉토리가 존재하지 않으면 생성

    Args:
        path: 디렉토리 경로

    Returns:
        Path: 생성된 경로
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_output_path(input_path, output_dir=None, suffix='.html'):
    """
    입력 파일에 대응하는 출력 경로 생성

    Args:
        input_path: 입력 파일 경로
        output_dir: 출력 디렉토리 (None이면 입력 파일과 같은 디렉토리)
        suffix: 출력 파일 확장자

    Returns:
        Path: 출력 파일 경로
    """
    input_path = Path(input_path)

    if output_dir:
        output_dir = Path(output_dir)
        return output_dir / input_path.with_suffix(suffix).name
    else:
        return input_path.with_suffix(suffix)


def get_image_dir(output_path):
    """
    이미지 저장 디렉토리 경로 생성 (문서명 기반)

    Args:
        output_path: HTML 출력 파일 경로

    Returns:
        Path: 이미지 디렉토리 경로 ({문서명}_images 형식)
    """
    output_path = Path(output_path)
    return output_path.parent / f"{output_path.stem}_images"


def find_docx_files(directory, recursive=True):
    """
    디렉토리에서 모든 .docx 파일 찾기

    Args:
        directory: 검색할 디렉토리
        recursive: 하위 디렉토리 포함 여부

    Returns:
        list[Path]: .docx 파일 경로 목록
    """
    directory = Path(directory)

    if recursive:
        return sorted(directory.rglob('*.docx'))
    else:
        return sorted(directory.glob('*.docx'))


def find_pdf_files(directory, recursive=True):
    """
    디렉토리에서 모든 .pdf 파일 찾기

    Args:
        directory: 검색할 디렉토리
        recursive: 하위 디렉토리 포함 여부

    Returns:
        list[Path]: .pdf 파일 경로 목록
    """
    directory = Path(directory)

    if recursive:
        return sorted(directory.rglob('*.pdf'))
    else:
        return sorted(directory.glob('*.pdf'))


def find_convertible_files(directory, recursive=True):
    """
    디렉토리에서 변환 가능한 모든 파일 찾기 (.docx + .pdf)

    Args:
        directory: 검색할 디렉토리
        recursive: 하위 디렉토리 포함 여부

    Returns:
        list[Path]: 변환 가능한 파일 경로 목록
    """
    docx_files = find_docx_files(directory, recursive)
    pdf_files = find_pdf_files(directory, recursive)
    return sorted(docx_files + pdf_files)


def sanitize_filename(filename):
    """
    파일명에서 특수문자 제거

    Args:
        filename: 원본 파일명

    Returns:
        str: 정리된 파일명
    """
    # Windows/Linux 파일명에서 허용되지 않는 문자 제거
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename


def get_relative_path(from_path, to_path):
    """
    두 경로 간의 상대 경로 계산

    Args:
        from_path: 시작 경로 (HTML 파일)
        to_path: 대상 경로 (이미지 파일)

    Returns:
        str: 상대 경로
    """
    from_path = Path(from_path).resolve().parent
    to_path = Path(to_path).resolve()

    try:
        rel_path = to_path.relative_to(from_path)
        return str(rel_path).replace('\\', '/')
    except ValueError:
        # 상대 경로 계산 불가시 절대 경로 반환
        return str(to_path).replace('\\', '/')


# ===== 텍스트 유틸리티 =====

def convert_smart_quotes(text):
    """
    스마트 인용부호를 일반 인용부호로 변환

    Args:
        text: 원본 텍스트

    Returns:
        str: 변환된 텍스트
    """
    replacements = {
        '\u2018': "'",  # '
        '\u2019': "'",  # '
        '\u201c': '"',  # "
        '\u201d': '"',  # "
        '\u2013': '-',  # en dash
        '\u2014': '-',  # em dash
        '\u2026': '...',  # ellipsis
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def escape_html(text):
    """
    HTML 특수문자 이스케이프

    Args:
        text: 원본 텍스트

    Returns:
        str: 이스케이프된 텍스트
    """
    if not text:
        return ''

    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;'))


# ===== 결과 클래스 =====

class ConversionResult:
    """변환 결과를 담는 클래스"""

    def __init__(self, input_path):
        self.input_path = Path(input_path)
        self.output_path = None
        self.success = False
        self.error_message = None
        self.warnings = []
        self.stats = {
            'paragraphs': 0,
            'headings': {'h1': 0, 'h2': 0, 'h3': 0, 'h4': 0, 'h5': 0, 'h6': 0},
            'tables': 0,
            'images': 0,
            'lists': 0
        }

    def add_warning(self, message):
        """경고 메시지 추가"""
        self.warnings.append(message)

    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            'input_path': str(self.input_path),
            'output_path': str(self.output_path) if self.output_path else None,
            'success': self.success,
            'error_message': self.error_message,
            'warnings': self.warnings,
            'stats': self.stats
        }


class BatchResult:
    """배치 변환 결과를 담는 클래스"""

    def __init__(self):
        self.results = []
        self.total = 0
        self.success_count = 0
        self.fail_count = 0

    def add(self, result):
        """개별 결과 추가"""
        self.results.append(result)
        self.total += 1
        if result.success:
            self.success_count += 1
        else:
            self.fail_count += 1

    def get_summary(self):
        """결과 요약"""
        return {
            'total': self.total,
            'success': self.success_count,
            'failed': self.fail_count,
            'warnings': sum(len(r.warnings) for r in self.results)
        }

    def export_csv(self, filepath):
        """결과를 CSV로 내보내기"""
        import csv

        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['입력 파일', '출력 파일', '성공 여부', '오류 메시지', '경고 수'])

            for r in self.results:
                writer.writerow([
                    str(r.input_path),
                    str(r.output_path) if r.output_path else '',
                    '성공' if r.success else '실패',
                    r.error_message or '',
                    len(r.warnings)
                ])
