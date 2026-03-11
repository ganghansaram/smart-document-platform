"""
한국어 형태소 분석 토크나이저

kiwipiepy를 사용하여 의미 토큰만 추출한다.
kiwipiepy 미설치 시 공백 기반 폴백으로 동작 (기존 방식과 동일).
"""
import logging
import re
from typing import List

logger = logging.getLogger(__name__)

# kiwipiepy 사용 가능 여부
_kiwi = None
_kiwi_available = None

# 의미 있는 품사 태그 (조사/어미/기호 제외)
_MEANINGFUL_TAGS = {
    "NNG",   # 일반 명사
    "NNP",   # 고유 명사
    "NNB",   # 의존 명사
    "NR",    # 수사
    "NP",    # 대명사
    "VV",    # 동사
    "VA",    # 형용사
    "MAG",   # 일반 부사
    "SL",    # 영어
    "SH",    # 한자
    "SN",    # 숫자
    "XR",    # 어근
}


def _get_kiwi():
    """Kiwi 인스턴스 싱글턴"""
    global _kiwi, _kiwi_available

    if _kiwi_available is False:
        return None

    if _kiwi is not None:
        return _kiwi

    try:
        from kiwipiepy import Kiwi
        _kiwi = Kiwi()
        _kiwi_available = True
        logger.info("kiwipiepy 형태소 분석기 초기화 완료")
        return _kiwi
    except ImportError:
        _kiwi_available = False
        logger.info("kiwipiepy 미설치 - 공백 기반 토크나이저 폴백")
        return None
    except Exception as e:
        _kiwi_available = False
        logger.warning("kiwipiepy 초기화 실패 - 공백 기반 폴백: %s", e)
        return None


def tokenize(text: str) -> List[str]:
    """
    텍스트를 의미 토큰 리스트로 분리.

    kiwipiepy 사용 가능 시: 형태소 분석 후 의미 있는 품사만 추출
    미설치 시: 공백 기반 분리 + 2자 이상 필터 (기존 방식)
    """
    if not text:
        return []

    kiwi = _get_kiwi()

    if kiwi is not None:
        return _tokenize_kiwi(kiwi, text)
    else:
        return _tokenize_fallback(text)


def _tokenize_kiwi(kiwi, text: str) -> List[str]:
    """kiwipiepy 형태소 분석 기반 토크나이징"""
    tokens = []
    result = kiwi.tokenize(text)

    for token in result:
        form = token.form.strip()
        tag = token.tag

        if not form:
            continue

        # 의미 있는 품사만 추출
        if tag in _MEANINGFUL_TAGS:
            tokens.append(form.lower())

    return tokens


def _tokenize_fallback(text: str) -> List[str]:
    """공백 기반 폴백 토크나이저 (기존 방식)"""
    return [t.lower() for t in text.split() if len(t) >= 2]


def is_kiwi_available() -> bool:
    """kiwipiepy 사용 가능 여부"""
    _get_kiwi()
    return _kiwi_available is True
