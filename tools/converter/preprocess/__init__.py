# -*- coding: utf-8 -*-
"""
DOCX 전처리 어댑터 패키지 — Plan-37

환경별 전처리 구현을 독립 모듈로 분리한 뒤 런타임 디스패처가 선택:
  - word_com     : Windows + MS Word COM (Phase 1)
  - libreoffice  : Linux + LibreOffice Headless (Phase 3)
  - native       : Pure Python numbering.xml 파서 (Phase 4)

하위 호환:
  `word_preprocessor.py` shim 이 `preprocess_docx`, `preprocess_only`,
  `cleanup_stale_temp_files` 를 re-export — 기존 import 경로 유지.

신규 API (디스패처):
  from preprocess import preprocess
  result = preprocess(input_path, policy='auto')
  # result.path, result.adapter, result.ok, result.tried
"""
from __future__ import annotations

import logging
from typing import Optional

from .base import PreprocessResult, PreprocessAdapter
from . import word_com as _word_com

# 하위 호환: 기존 word_preprocessor 직접 호출 경로
from .word_com import preprocess_docx, preprocess_only, cleanup_stale_temp_files

logger = logging.getLogger(__name__)

# 디스패처 폴백 순서 (policy='auto' 일 때)
_ADAPTER_ORDER = ['word_com', 'libreoffice', 'native']


def _load_adapter(name: str) -> Optional[PreprocessAdapter]:
    """어댑터 이름 → 인스턴스 지연 로드. 실패 시 None."""
    try:
        if name == 'word_com':
            return _word_com.WordComAdapter()
        if name == 'libreoffice':
            from . import libreoffice as _lo
            return _lo.LibreOfficeAdapter()
        if name == 'native':
            # Phase 4 에서 구현 예정
            return None
    except Exception as e:
        logger.debug("어댑터 %s 로드 실패: %s", name, e)
    return None


def preprocess(input_path: str,
               output_path: Optional[str] = None,
               policy: str = 'auto') -> PreprocessResult:
    """환경 감지 후 가용 어댑터로 전처리.

    Args:
        input_path: 원본 DOCX 경로.
        output_path: 결과 저장 경로 (None 이면 어댑터가 임시 파일 생성).
        policy: 디스패처 정책.
            'auto'        — word_com → libreoffice → native 순서로 첫 가용 어댑터 사용 (기본)
            'word_com'    — Windows+Word 강제
            'libreoffice' — LibreOffice 강제
            'native'      — Python 파서 강제 (Phase 4)
            'skip'        — 전처리 없이 원본 반환 (디버그·사용자 이미 전처리한 경우)

    Returns:
        PreprocessResult — 성공 시 result.path 를 converter 입력으로 사용.
        실패 시 result.path == input_path, result.ok == False.
    """
    if policy == 'skip':
        return PreprocessResult(path=input_path, adapter='skip', ok=True)

    candidates = _ADAPTER_ORDER if policy == 'auto' else [policy]
    tried = []

    for name in candidates:
        adapter = _load_adapter(name)
        if adapter is None:
            tried.append((name, 'not implemented'))
            continue
        if not adapter.is_available():
            tried.append((name, 'unavailable'))
            continue
        try:
            result = adapter.preprocess(input_path, output_path)
        except Exception as e:
            tried.append((name, f'exception: {type(e).__name__}: {e}'))
            logger.warning("어댑터 %s 실행 중 예외: %s", name, e)
            continue

        if result.ok:
            tried.append((name, 'ok'))
            result.tried = tried
            return result
        tried.append((name, result.error or 'failed'))

    # 모든 어댑터 실패
    logger.warning("전처리 어댑터 모두 실패: %s", tried)
    return PreprocessResult(
        path=input_path, adapter='none', ok=False,
        error=f"all adapters failed: {tried}",
        tried=tried,
    )


__all__ = [
    # 신규 API
    "preprocess",
    "PreprocessResult",
    "PreprocessAdapter",
    # 하위 호환
    "preprocess_docx",
    "preprocess_only",
    "cleanup_stale_temp_files",
]
