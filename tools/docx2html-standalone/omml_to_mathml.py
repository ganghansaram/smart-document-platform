#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OMML (Office Math Markup Language) to MathML 변환기

Word 문서의 수식(OMML)을 브라우저 네이티브 MathML로 변환한다.
외부 JS 라이브러리 불필요 — 에어갭 환경에 적합.
"""

import re
from xml.etree.ElementTree import Element

# OMML 네임스페이스
MATH_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
WORD_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

# 연산자 문자 집합
OPERATORS = set('+-=<>≤≥≠≈∼±∓×÷·∘∧∨¬∀∃∈∉⊂⊃⊆⊇∪∩∑∏∫∮∞∂∇()[]{}|!,:;')

# 그리스 문자 (변수로 취급)
GREEK_LETTERS = set('αβγδεζηθικλμνξοπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ')

# 악센트 문자 매핑 (OMML chr 값 → MathML 결합 문자)
ACCENT_MAP = {
    '\u0302': '\u0302',   # 캐럿 (hat) — combining circumflex
    '\u0303': '\u0303',   # 물결 — combining tilde
    '\u0304': '\u0304',   # 윗줄 — combining macron
    '\u0305': '\u0305',   # 윗줄 (overline)
    '\u0307': '\u0307',   # 점 — combining dot above
    '\u0308': '\u0308',   # 쌍점 — combining diaeresis
    '\u20D7': '\u20D7',   # 벡터 화살표 — combining right arrow above
    '\u2192': '\u20D7',   # → (단독 화살표) → combining arrow
    '\u005E': '\u0302',   # ^ → hat
    '\u007E': '\u0303',   # ~ → tilde
    '\u00AF': '\u0305',   # macron
    '\u00B4': '\u0301',   # acute accent
    '\u0060': '\u0300',   # grave accent
}

# nary 연산자 매핑 (OMML chr 값 → MathML 연산자)
NARY_MAP = {
    '\u2211': '\u2211',   # ∑ 합
    '\u220F': '\u220F',   # ∏ 곱
    '\u222B': '\u222B',   # ∫ 적분
    '\u222C': '\u222C',   # ∬ 이중적분
    '\u222D': '\u222D',   # ∭ 삼중적분
    '\u222E': '\u222E',   # ∮ 선적분
    '\u22C0': '\u22C0',   # ⋀ 논리곱
    '\u22C1': '\u22C1',   # ⋁ 논리합
    '\u22C2': '\u22C2',   # ⋂ 교집합
    '\u22C3': '\u22C3',   # ⋃ 합집합
}

# 괄호(delimiter) 매핑
DELIM_MAP = {
    '(': '(', ')': ')',
    '[': '[', ']': ']',
    '{': '{', '}': '}',
    '|': '|',
    '\u2016': '\u2016',   # ‖ 이중 수직선
    '\u2308': '\u2308',   # ⌈ 왼쪽 올림
    '\u2309': '\u2309',   # ⌉ 오른쪽 올림
    '\u230A': '\u230A',   # ⌊ 왼쪽 내림
    '\u230B': '\u230B',   # ⌋ 오른쪽 내림
    '\u27E8': '\u27E8',   # ⟨ 왼쪽 꺾쇠
    '\u27E9': '\u27E9',   # ⟩ 오른쪽 꺾쇠
}

# groupChr 매핑 (position → munder/mover)
GROUP_CHR_MAP = {
    '\u23DE': '\u23DE',   # ⏞ 위 중괄호
    '\u23DF': '\u23DF',   # ⏟ 아래 중괄호
    '\u23DC': '\u23DC',   # ⏜ 위 소괄호
    '\u23DD': '\u23DD',   # ⏝ 아래 소괄호
}


def _ns(tag):
    """OMML 네임스페이스 접두사 추가"""
    return f'{{{MATH_NS}}}{tag}'


def _wns(tag):
    """Word 네임스페이스 접두사 추가"""
    return f'{{{WORD_NS}}}{tag}'


def _local(tag):
    """네임스페이스 제거하여 로컬 태그명 반환"""
    if '}' in tag:
        return tag.split('}', 1)[1]
    return tag


def _get_val(elem, prop_tag, attr='val'):
    """OMML 속성 요소에서 m:val 값 추출.

    예: <m:begChr m:val="["/> → '['
    """
    if elem is None:
        return None
    prop = elem.find(_ns(prop_tag))
    if prop is None:
        return None
    # m:val 또는 네임스페이스 없는 val
    return prop.get(f'{{{MATH_NS}}}{attr}') or prop.get(attr)


class OmmlToMathml:
    """OMML XML 요소를 MathML 문자열로 변환하는 클래스"""

    def convert_omath(self, omath_elem, display=False):
        """m:oMath 요소를 <math> 태그로 변환.

        Args:
            omath_elem: m:oMath XML Element
            display: True이면 display="block" 속성 추가 (디스플레이 수식)

        Returns:
            str: MathML HTML 문자열
        """
        inner = self._convert_children(omath_elem)
        if display:
            return f'<math display="block"><mrow>{inner}</mrow></math>'
        return f'<math><mrow>{inner}</mrow></math>'

    # ── 재귀 디스패치 ─────────────────────────────────────────────

    def _convert_element(self, elem):
        """단일 OMML 요소를 MathML로 변환 (디스패치)"""
        tag = _local(elem.tag)

        dispatch = {
            'r':         self._convert_run,
            'f':         self._convert_fraction,
            'sSub':      self._convert_ssub,
            'sSup':      self._convert_ssup,
            'sSubSup':   self._convert_ssubsup,
            'd':         self._convert_delimiter,
            'rad':       self._convert_radical,
            'nary':      self._convert_nary,
            'func':      self._convert_func,
            'acc':       self._convert_accent,
            'bar':       self._convert_bar,
            'm':         self._convert_matrix,
            'eqArr':     self._convert_eqarr,
            'limLow':    self._convert_limlow,
            'limUpp':    self._convert_limupp,
            'groupChr':  self._convert_groupchr,
            'sPre':      self._convert_spre,
            'box':       self._convert_box,
            'borderBox': self._convert_borderbox,
            'phant':     self._convert_phantom,
            # 하위 요소 (단독 출현 시 자식 재귀)
            'oMath':     lambda e: self._convert_children(e),
        }

        handler = dispatch.get(tag)
        if handler:
            return handler(elem)

        # 미지원 요소: 자식 재귀로 내용 보존
        return self._convert_children(elem)

    def _convert_children(self, elem):
        """요소의 모든 자식을 재귀 변환하여 결합"""
        parts = []
        for child in elem:
            tag = _local(child.tag)
            # 속성 요소(xxxPr)는 스킵
            if tag.endswith('Pr'):
                continue
            parts.append(self._convert_element(child))
        return ''.join(parts)

    # ── Run (m:r / m:t) ───────────────────────────────────────────

    def _convert_run(self, elem):
        """m:r 요소 변환: m:t 텍스트를 mn/mo/mi로 분류"""
        parts = []
        for child in elem:
            tag = _local(child.tag)
            if tag == 't':
                text = child.text or ''
                parts.append(self._classify_math_text(text))
            # rPr (run properties) 등은 스킵
        return ''.join(parts)

    def _classify_math_text(self, text):
        """텍스트를 MathML 요소로 분류.

        - 전체가 숫자(소수점 포함) → <mn>
        - 전체가 연산자 1문자 → <mo>
        - 함수 이름 (sin, cos 등) → <mi>
        - 혼합 → 문자 단위 분리
        """
        if not text:
            return ''

        text = text.strip()
        if not text:
            return ''

        # 숫자 (소수점, 콤마 포함)
        if re.match(r'^[\d.,]+$', text):
            return f'<mn>{_escape(text)}</mn>'

        # 단일 연산자
        if len(text) == 1 and text in OPERATORS:
            return f'<mo>{_escape(text)}</mo>'

        # 알려진 함수명
        known_funcs = {
            'sin', 'cos', 'tan', 'cot', 'sec', 'csc',
            'arcsin', 'arccos', 'arctan',
            'sinh', 'cosh', 'tanh', 'coth',
            'log', 'ln', 'exp', 'lim', 'sup', 'inf',
            'max', 'min', 'arg', 'det', 'dim', 'deg',
            'gcd', 'hom', 'ker', 'mod',
        }
        if text.lower() in known_funcs:
            return f'<mi>{_escape(text)}</mi>'

        # 단일 문자 (변수)
        if len(text) == 1:
            if text.isalpha() or text in GREEK_LETTERS:
                return f'<mi>{_escape(text)}</mi>'
            if text.isdigit():
                return f'<mn>{_escape(text)}</mn>'
            return f'<mo>{_escape(text)}</mo>'

        # 혼합 문자열: 문자 단위 분리
        parts = []
        i = 0
        while i < len(text):
            ch = text[i]
            # 연속 숫자 묶기
            if ch.isdigit() or (ch in '.,'):
                j = i
                while j < len(text) and (text[j].isdigit() or text[j] in '.,'):
                    j += 1
                parts.append(f'<mn>{_escape(text[i:j])}</mn>')
                i = j
            elif ch in OPERATORS:
                parts.append(f'<mo>{_escape(ch)}</mo>')
                i += 1
            elif ch.isalpha() or ch in GREEK_LETTERS:
                parts.append(f'<mi>{_escape(ch)}</mi>')
                i += 1
            elif ch.isspace():
                i += 1  # 공백 스킵
            else:
                parts.append(f'<mo>{_escape(ch)}</mo>')
                i += 1
        return ''.join(parts)

    # ── 분수 (m:f) ────────────────────────────────────────────────

    def _convert_fraction(self, elem):
        """m:f → <mfrac>"""
        num = elem.find(_ns('num'))
        den = elem.find(_ns('den'))
        num_ml = self._convert_children(num) if num is not None else '<mn>?</mn>'
        den_ml = self._convert_children(den) if den is not None else '<mn>?</mn>'

        # 분수 유형 확인
        fpr = elem.find(_ns('fPr'))
        ftype = _get_val(fpr, 'type') if fpr is not None else None

        if ftype == 'lin':
            # 선형 분수: a/b
            return f'<mrow>{num_ml}<mo>/</mo>{den_ml}</mrow>'
        if ftype == 'noBar':
            # 괄호 없는 분수 (이항계수 등)
            return f'<mfrac linethickness="0">{num_ml}{den_ml}</mfrac>'

        return f'<mfrac>{num_ml}{den_ml}</mfrac>'

    # ── 첨자 ──────────────────────────────────────────────────────

    def _convert_ssub(self, elem):
        """m:sSub → <msub>"""
        base = self._convert_e(elem)
        sub = self._convert_child(elem, 'sub')
        return f'<msub>{base}{sub}</msub>'

    def _convert_ssup(self, elem):
        """m:sSup → <msup>"""
        base = self._convert_e(elem)
        sup = self._convert_child(elem, 'sup')
        return f'<msup>{base}{sup}</msup>'

    def _convert_ssubsup(self, elem):
        """m:sSubSup → <msubsup>"""
        base = self._convert_e(elem)
        sub = self._convert_child(elem, 'sub')
        sup = self._convert_child(elem, 'sup')
        return f'<msubsup>{base}{sub}{sup}</msubsup>'

    # ── 괄호 / 구분자 (m:d) ───────────────────────────────────────

    def _convert_delimiter(self, elem):
        """m:d → <mrow><mo>(<mo>...<mo>)</mo></mrow>"""
        dpr = elem.find(_ns('dPr'))
        beg = _get_val(dpr, 'begChr') if dpr is not None else None
        end = _get_val(dpr, 'endChr') if dpr is not None else None
        sep = _get_val(dpr, 'sepChr') if dpr is not None else None

        if beg is None:
            beg = '('
        if end is None:
            end = ')'
        if sep is None:
            sep = '|'  # 기본 구분자

        # 빈 문자열이면 구분자 없음
        beg_ml = f'<mo>{_escape(beg)}</mo>' if beg else ''
        end_ml = f'<mo>{_escape(end)}</mo>' if end else ''

        # m:e 요소들 수집
        e_elems = elem.findall(_ns('e'))
        e_parts = []
        for i, e in enumerate(e_elems):
            if i > 0 and sep:
                e_parts.append(f'<mo>{_escape(sep)}</mo>')
            e_parts.append(f'<mrow>{self._convert_children(e)}</mrow>')

        return f'<mrow>{beg_ml}{"".join(e_parts)}{end_ml}</mrow>'

    # ── 근호 (m:rad) ──────────────────────────────────────────────

    def _convert_radical(self, elem):
        """m:rad → <msqrt> 또는 <mroot>"""
        deg = elem.find(_ns('deg'))
        base = self._convert_e(elem)

        # deg가 있고 내용이 있으면 n-제곱근
        if deg is not None:
            deg_content = self._convert_children(deg)
            if deg_content.strip():
                return f'<mroot>{base}{deg_content}</mroot>'

        # 속성에서 degHide 확인
        rad_pr = elem.find(_ns('radPr'))
        deg_hide = _get_val(rad_pr, 'degHide') if rad_pr is not None else None
        if deg_hide == '1' or deg is None or not deg_content.strip():
            return f'<msqrt>{base}</msqrt>'

        return f'<msqrt>{base}</msqrt>'

    # ── N-ary (합, 적분 등) (m:nary) ─────────────────────────────

    def _convert_nary(self, elem):
        """m:nary → <munderover> 또는 <msubsup> + <mo>∫</mo>"""
        nary_pr = elem.find(_ns('naryPr'))

        # 연산자 문자
        chr_val = _get_val(nary_pr, 'chr') if nary_pr is not None else None
        op = chr_val if chr_val else '\u222B'  # 기본: ∫

        # 상하한 숨김 여부
        sub_hide = _get_val(nary_pr, 'subHide') if nary_pr is not None else None
        sup_hide = _get_val(nary_pr, 'supHide') if nary_pr is not None else None

        # limLoc: undOvr(위아래) 또는 subSup(첨자)
        lim_loc = _get_val(nary_pr, 'limLoc') if nary_pr is not None else None

        sub_content = self._convert_child(elem, 'sub')
        sup_content = self._convert_child(elem, 'sup')
        base = self._convert_e(elem)

        op_ml = f'<mo>{_escape(op)}</mo>'

        has_sub = sub_hide != '1' and sub_content.strip()
        has_sup = sup_hide != '1' and sup_content.strip()

        if lim_loc == 'subSup' or (op in ('\u222B', '\u222C', '\u222D', '\u222E')):
            # 적분류: 첨자 형태
            if has_sub and has_sup:
                return f'<mrow><msubsup>{op_ml}{sub_content}{sup_content}</msubsup>{base}</mrow>'
            elif has_sub:
                return f'<mrow><msub>{op_ml}{sub_content}</msub>{base}</mrow>'
            elif has_sup:
                return f'<mrow><msup>{op_ml}{sup_content}</msup>{base}</mrow>'
            return f'<mrow>{op_ml}{base}</mrow>'
        else:
            # 합/곱 등: 위아래 형태
            if has_sub and has_sup:
                return f'<mrow><munderover>{op_ml}{sub_content}{sup_content}</munderover>{base}</mrow>'
            elif has_sub:
                return f'<mrow><munder>{op_ml}{sub_content}</munder>{base}</mrow>'
            elif has_sup:
                return f'<mrow><mover>{op_ml}{sup_content}</mover>{base}</mrow>'
            return f'<mrow>{op_ml}{base}</mrow>'

    # ── 함수 (m:func) ─────────────────────────────────────────────

    def _convert_func(self, elem):
        """m:func → <mrow>함수명 인수</mrow>"""
        fname = elem.find(_ns('fName'))
        base = self._convert_e(elem)

        fname_ml = self._convert_children(fname) if fname is not None else ''
        return f'<mrow>{fname_ml}<mo>&#x2061;</mo>{base}</mrow>'

    # ── 악센트 (m:acc) ─────────────────────────────────────────────

    def _convert_accent(self, elem):
        """m:acc → <mover>"""
        acc_pr = elem.find(_ns('accPr'))
        chr_val = _get_val(acc_pr, 'chr') if acc_pr is not None else None
        acc_char = ACCENT_MAP.get(chr_val, chr_val) if chr_val else '\u0302'

        base = self._convert_e(elem)
        return f'<mover accent="true">{base}<mo>{_escape(acc_char)}</mo></mover>'

    # ── 윗줄 / 아랫줄 (m:bar) ─────────────────────────────────────

    def _convert_bar(self, elem):
        """m:bar → <mover> 또는 <munder>"""
        bar_pr = elem.find(_ns('barPr'))
        pos = _get_val(bar_pr, 'pos') if bar_pr is not None else None

        base = self._convert_e(elem)

        if pos == 'bot':
            return f'<munder>{base}<mo>&#x0332;</mo></munder>'
        return f'<mover>{base}<mo>&#x00AF;</mo></mover>'

    # ── 행렬 (m:m) ────────────────────────────────────────────────

    def _convert_matrix(self, elem):
        """m:m → <mtable>"""
        rows = []
        for mr in elem.findall(_ns('mr')):
            cells = []
            for e in mr.findall(_ns('e')):
                cell_content = self._convert_children(e)
                cells.append(f'<mtd>{cell_content}</mtd>')
            rows.append(f'<mtr>{"".join(cells)}</mtr>')
        return f'<mtable>{"".join(rows)}</mtable>'

    # ── 수식 배열 (m:eqArr) ────────────────────────────────────────

    def _convert_eqarr(self, elem):
        """m:eqArr → <mtable> (각 e가 행)"""
        rows = []
        for e in elem.findall(_ns('e')):
            content = self._convert_children(e)
            rows.append(f'<mtr><mtd>{content}</mtd></mtr>')
        return f'<mtable columnalign="left">{"".join(rows)}</mtable>'

    # ── 극한 (m:limLow, m:limUpp) ─────────────────────────────────

    def _convert_limlow(self, elem):
        """m:limLow → <munder>"""
        base = self._convert_e(elem)
        lim = self._convert_child(elem, 'lim')
        return f'<munder>{base}{lim}</munder>'

    def _convert_limupp(self, elem):
        """m:limUpp → <mover>"""
        base = self._convert_e(elem)
        lim = self._convert_child(elem, 'lim')
        return f'<mover>{base}{lim}</mover>'

    # ── 그룹 문자 (m:groupChr) ─────────────────────────────────────

    def _convert_groupchr(self, elem):
        """m:groupChr → <munder> 또는 <mover>"""
        gpr = elem.find(_ns('groupChrPr'))
        chr_val = _get_val(gpr, 'chr') if gpr is not None else None
        pos = _get_val(gpr, 'pos') if gpr is not None else None

        group_char = chr_val if chr_val else '\u23DF'  # 기본: ⏟
        base = self._convert_e(elem)

        if pos == 'top':
            return f'<mover>{base}<mo>{_escape(group_char)}</mo></mover>'
        return f'<munder>{base}<mo>{_escape(group_char)}</mo></munder>'

    # ── 앞첨자 (m:sPre) ───────────────────────────────────────────

    def _convert_spre(self, elem):
        """m:sPre → <mmultiscripts>"""
        base = self._convert_e(elem)
        sub = self._convert_child(elem, 'sub')
        sup = self._convert_child(elem, 'sup')
        return f'<mmultiscripts>{base}<mprescripts/>{sub}{sup}</mmultiscripts>'

    # ── 박스 (m:box) ───────────────────────────────────────────────

    def _convert_box(self, elem):
        """m:box → <mrow>"""
        return f'<mrow>{self._convert_e(elem)}</mrow>'

    # ── 테두리 박스 (m:borderBox) ──────────────────────────────────

    def _convert_borderbox(self, elem):
        """m:borderBox → <menclose notation="box">"""
        return f'<menclose notation="box">{self._convert_e(elem)}</menclose>'

    # ── 팬텀 (m:phant) ────────────────────────────────────────────

    def _convert_phantom(self, elem):
        """m:phant → <mphantom>"""
        return f'<mphantom>{self._convert_e(elem)}</mphantom>'

    # ── 헬퍼 메서드 ───────────────────────────────────────────────

    def _convert_e(self, elem):
        """m:e (기본 인수) 요소를 변환"""
        e = elem.find(_ns('e'))
        if e is None:
            return '<mrow></mrow>'
        content = self._convert_children(e)
        return f'<mrow>{content}</mrow>' if content else '<mrow></mrow>'

    def _convert_child(self, elem, child_tag):
        """지정 태그의 자식 요소를 변환"""
        child = elem.find(_ns(child_tag))
        if child is None:
            return '<mrow></mrow>'
        content = self._convert_children(child)
        return f'<mrow>{content}</mrow>' if content else '<mrow></mrow>'


def _escape(text):
    """MathML용 HTML 이스케이프 (최소한)"""
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))
