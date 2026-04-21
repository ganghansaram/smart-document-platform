# -*- coding: utf-8 -*-
"""
Plan-37 Phase 4a — word/numbering.xml 해석기

MS Word 의 heading 자동번호를 **전처리 없이 원본 XML 에서 직접 계산**.

배경:
  기존 converter 는 heading 번호가 본문 텍스트에 박혀있어야 표시 가능 (Word COM
  또는 LibreOffice 전처리 필요). Phase 4a 는 numbering.xml 을 스스로 해석해
  전처리 없이도 정확한 번호 prefix 를 생성한다.

지원 범위 (1차):
  - `<w:numFmt>` decimal, upperRoman, lowerRoman, upperLetter, lowerLetter
  - `<w:lvlText>` 템플릿 (%1, %2, ..., %9 치환)
  - `<w:start>` 초기값
  - `<w:lvlRestart>` 상위 레벨 증가 시 하위 리셋
  - `<w:lvlOverride>` + `<w:startOverride>` (numId 별 override)
  - `<w:ilvl>` 1~9

미지원 (확인 시 log + decimal 대체):
  - bullet, none, chicago, ordinal, cardinalText 등 비수치 포맷
  - 동적 포맷 확장자 (lowerLetterWithAlphaLevel 등)

의존성: python-docx + xml stdlib (폐쇄망 호환)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional

from docx.oxml.ns import qn

logger = logging.getLogger(__name__)


@dataclass
class LvlDef:
    """한 level 의 정의."""
    ilvl: int
    start: int = 1
    num_fmt: str = "decimal"
    lvl_text: str = "%1."
    lvl_restart: Optional[int] = None   # None=기본(상위 증가 시 리셋), 0=리셋 안 함, N=이 level 증가 시 리셋


@dataclass
class AbstractNumDef:
    """abstractNum 정의 — 한 multilevel list 의 규격."""
    abstract_num_id: str
    levels: Dict[int, LvlDef] = field(default_factory=dict)


@dataclass
class NumDef:
    """num (numId) — abstractNum 참조 + override."""
    num_id: str
    abstract_num_id: str
    level_overrides: Dict[int, LvlDef] = field(default_factory=dict)


# 한글/영문 숫자 변환 ─────────────────────────────────────────────

_ROMAN_VALUES = [
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
    (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
    (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
]


def _to_roman(n: int, upper: bool = True) -> str:
    if n <= 0:
        return str(n)
    out = []
    for value, numeral in _ROMAN_VALUES:
        while n >= value:
            out.append(numeral)
            n -= value
    s = "".join(out)
    return s if upper else s.lower()


def _to_letter(n: int, upper: bool = True) -> str:
    """1 → A, 26 → Z, 27 → AA, ..."""
    if n <= 0:
        return str(n)
    out = []
    while n > 0:
        n, r = divmod(n - 1, 26)
        out.append(chr(ord('A' if upper else 'a') + r))
    return "".join(reversed(out))


def _format_number(value: int, num_fmt: str) -> str:
    if num_fmt == "decimal":
        return str(value)
    if num_fmt == "decimalZero":
        return f"{value:02d}"
    if num_fmt == "upperRoman":
        return _to_roman(value, upper=True)
    if num_fmt == "lowerRoman":
        return _to_roman(value, upper=False)
    if num_fmt == "upperLetter":
        return _to_letter(value, upper=True)
    if num_fmt == "lowerLetter":
        return _to_letter(value, upper=False)
    # 한글(Chosung/Iroha/CardinalText 등) 은 미지원 — decimal 폴백
    return str(value)


# ── Parser & Resolver ──────────────────────────────────────────────

class NumberingResolver:
    """numbering.xml 해석 + 단락별 번호 계산.

    사용법:
        resolver = NumberingResolver(doc)
        # 문서 순회 중 heading/list 단락에서:
        num_text = resolver.format_number(num_id, ilvl)  # 예: "1.2.3"
        # 반드시 문서 순차 순서대로 호출 (counter 가 상태 유지)
    """

    def __init__(self, doc):
        self._abstract_defs: Dict[str, AbstractNumDef] = {}
        self._num_defs: Dict[str, NumDef] = {}
        self._counters: Dict[str, Dict[int, int]] = {}  # {num_id: {ilvl: current}}
        self._parse(doc)

    # ── 파싱 ──────────────────────────────────────────────────

    def _parse(self, doc):
        try:
            numbering_part = doc.part.numbering_part
        except Exception:
            numbering_part = None

        if numbering_part is None:
            return

        numbering_elem = numbering_part.element
        if numbering_elem is None:
            return

        # 1. abstractNum 수집
        for abs_num in numbering_elem.findall(qn('w:abstractNum')):
            abs_id = abs_num.get(qn('w:abstractNumId'))
            if abs_id is None:
                continue
            abs_def = AbstractNumDef(abstract_num_id=abs_id)
            for lvl in abs_num.findall(qn('w:lvl')):
                ld = self._parse_lvl(lvl)
                if ld is not None:
                    abs_def.levels[ld.ilvl] = ld
            self._abstract_defs[abs_id] = abs_def

        # 2. num (numId → abstractNumId 매핑 + override)
        for num in numbering_elem.findall(qn('w:num')):
            num_id = num.get(qn('w:numId'))
            if num_id is None:
                continue
            abs_ref_elem = num.find(qn('w:abstractNumId'))
            if abs_ref_elem is None:
                continue
            abs_id = abs_ref_elem.get(qn('w:val'))
            if abs_id is None:
                continue
            num_def = NumDef(num_id=num_id, abstract_num_id=abs_id)

            # lvlOverride (numId 별 start 재지정)
            for lvl_over in num.findall(qn('w:lvlOverride')):
                ilvl_s = lvl_over.get(qn('w:ilvl'))
                if ilvl_s is None:
                    continue
                ilvl = int(ilvl_s)
                start_over = lvl_over.find(qn('w:startOverride'))
                lvl_elem = lvl_over.find(qn('w:lvl'))
                if lvl_elem is not None:
                    ld = self._parse_lvl(lvl_elem)
                    if ld is not None:
                        num_def.level_overrides[ilvl] = ld
                elif start_over is not None:
                    # start 만 override
                    val = start_over.get(qn('w:val'))
                    if val and val.isdigit():
                        # 기존 abstractNum 의 level 복사 후 start 만 교체
                        abs_def = self._abstract_defs.get(abs_id)
                        if abs_def and ilvl in abs_def.levels:
                            base = abs_def.levels[ilvl]
                            num_def.level_overrides[ilvl] = LvlDef(
                                ilvl=ilvl,
                                start=int(val),
                                num_fmt=base.num_fmt,
                                lvl_text=base.lvl_text,
                                lvl_restart=base.lvl_restart,
                            )

            self._num_defs[num_id] = num_def

    @staticmethod
    def _parse_lvl(lvl_elem) -> Optional[LvlDef]:
        ilvl_s = lvl_elem.get(qn('w:ilvl'))
        if ilvl_s is None:
            return None
        ilvl = int(ilvl_s)
        ld = LvlDef(ilvl=ilvl)

        start = lvl_elem.find(qn('w:start'))
        if start is not None:
            val = start.get(qn('w:val'))
            if val and val.lstrip('-').isdigit():
                ld.start = int(val)

        num_fmt = lvl_elem.find(qn('w:numFmt'))
        if num_fmt is not None:
            val = num_fmt.get(qn('w:val'))
            if val:
                ld.num_fmt = val

        lvl_text = lvl_elem.find(qn('w:lvlText'))
        if lvl_text is not None:
            val = lvl_text.get(qn('w:val'))
            if val is not None:
                ld.lvl_text = val

        lvl_restart = lvl_elem.find(qn('w:lvlRestart'))
        if lvl_restart is not None:
            val = lvl_restart.get(qn('w:val'))
            if val and val.isdigit():
                ld.lvl_restart = int(val)

        return ld

    # ── Counter 관리 ──────────────────────────────────────────

    def _get_level_def(self, num_id: str, ilvl: int) -> Optional[LvlDef]:
        num_def = self._num_defs.get(num_id)
        if num_def is None:
            return None
        if ilvl in num_def.level_overrides:
            return num_def.level_overrides[ilvl]
        abs_def = self._abstract_defs.get(num_def.abstract_num_id)
        if abs_def is None:
            return None
        return abs_def.levels.get(ilvl)

    def _init_counter(self, num_id: str, ilvl: int) -> int:
        """처음 접근 시 start 값으로 초기화. 이미 있으면 그대로."""
        counter = self._counters.setdefault(num_id, {})
        if ilvl not in counter:
            ld = self._get_level_def(num_id, ilvl)
            counter[ilvl] = (ld.start if ld else 1) - 1  # -1 = "아직 시작 전"
        return counter[ilvl]

    def format_number(self, num_id: str, ilvl: int) -> Optional[str]:
        """현 단락의 (numId, ilvl) 에 대해 번호 prefix 생성.

        호출 즉시 해당 ilvl counter 증가 + 하위 ilvl 리셋.
        반환값 예: "1.2.3" (lvlText 가 "%1.%2.%3" 일 때).
        """
        ld = self._get_level_def(num_id, ilvl)
        if ld is None:
            return None

        counter = self._counters.setdefault(num_id, {})

        # 이 level counter 증가
        if ilvl not in counter:
            counter[ilvl] = ld.start
        else:
            counter[ilvl] += 1

        # 하위 level 리셋 (lvlRestart 규칙에 따라)
        for lower_ilvl in list(counter.keys()):
            if lower_ilvl <= ilvl:
                continue
            lower_ld = self._get_level_def(num_id, lower_ilvl)
            if lower_ld is None:
                continue
            # lvlRestart=0 이면 리셋하지 않음. None 이면 기본 동작(상위 증가 시 리셋).
            # lvlRestart=N 이면 level N 증가 시 리셋 — 해석상 이 N 은 0-based 또는
            # 1-based 인지 스펙 모호. MS Word 는 보통 1-based (ilvl+1) 기준.
            if lower_ld.lvl_restart == 0:
                continue
            # 기본/1-based 리셋: 현재 level 이 (lvl_restart-1) 이상이면 리셋
            if lower_ld.lvl_restart is None or (lower_ld.lvl_restart - 1) >= ilvl:
                counter.pop(lower_ilvl)

        # lvlText 템플릿 치환 (%1 → level 0, %2 → level 1, ...)
        text = ld.lvl_text
        for i in range(9, 0, -1):
            placeholder = f"%{i}"
            if placeholder not in text:
                continue
            level_ilvl = i - 1
            val = counter.get(level_ilvl)
            if val is None:
                level_ld = self._get_level_def(num_id, level_ilvl)
                val = level_ld.start if level_ld else 1
            level_ld = self._get_level_def(num_id, level_ilvl)
            fmt = level_ld.num_fmt if level_ld else "decimal"
            text = text.replace(placeholder, _format_number(val, fmt))

        return text
