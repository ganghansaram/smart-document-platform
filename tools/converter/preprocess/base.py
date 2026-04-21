# -*- coding: utf-8 -*-
"""
Plan-37 Phase 3 — 전처리 어댑터 공통 타입·인터페이스

각 어댑터(word_com, libreoffice, native)는 PreprocessAdapter 인터페이스를
구현. 디스패처는 정책(auto/지정)에 따라 가용 어댑터를 선택·폴백.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PreprocessResult:
    """전처리 결과. 디스패처의 반환 타입.

    Attributes:
        path: 전처리된 파일 경로 (실패 시 원본 경로).
        adapter: 사용된 어댑터 이름 ('word_com', 'libreoffice', 'native', 'skip', 'none').
        ok: 전처리 성공 여부. False 이면 원본 반환.
        error: 실패 사유 (ok=False 일 때). None 이면 정상.
        tried: 디스패처 폴백 경로 기록 — [(adapter_name, reason_or_'ok'), ...]
    """
    path: str
    adapter: str
    ok: bool = True
    error: Optional[str] = None
    tried: list = field(default_factory=list)

    def __str__(self) -> str:
        status = "ok" if self.ok else f"FAIL:{self.error}"
        return f"<PreprocessResult adapter={self.adapter} {status} path={self.path}>"


class PreprocessAdapter:
    """어댑터 공통 인터페이스. 서브클래스는 name/is_available/preprocess 를 구현."""

    name: str = ""

    def is_available(self) -> bool:
        """이 어댑터를 현재 환경에서 실행할 수 있는지 확인.
        (예: word_com → pywin32 설치 + Word.Application dispatch 가능?
              libreoffice → soffice PATH 존재?)"""
        raise NotImplementedError

    def preprocess(self, input_path: str, output_path: Optional[str] = None) -> PreprocessResult:
        """전처리 수행. 실패 시 ok=False 반환.

        Args:
            input_path: 원본 DOCX 경로.
            output_path: 결과 저장 경로 (None 이면 어댑터가 임시 파일 생성).

        Returns:
            PreprocessResult — 성공 여부, 결과 경로, 어댑터 이름 포함.
        """
        raise NotImplementedError
