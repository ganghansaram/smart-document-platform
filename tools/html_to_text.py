#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML → 검색용 텍스트 변환기

테이블 → 마크다운 테이블, 수식(MathML) → LaTeX로 변환하여
검색 인덱스에서 구조 정보를 보존한다.

외부 의존성 없음 (순수 Python stdlib) — 폐쇄망 호환.
"""

import re
import html as html_module
from xml.etree import ElementTree as ET

# MathML 네임스페이스
MATHML_NS = 'http://www.w3.org/1998/Math/MathML'


# ===================================================================
# TableConverter — HTML <table> → 마크다운 테이블
# ===================================================================

class TableConverter:
    """HTML 테이블을 마크다운 형식으로 변환."""

    # 테이블 블록 추출 패턴
    _TABLE_RE = re.compile(r'<table[^>]*>.*?</table>', re.DOTALL | re.IGNORECASE)
    _ROW_RE = re.compile(r'<tr[^>]*>(.*?)</tr>', re.DOTALL | re.IGNORECASE)
    _CELL_RE = re.compile(
        r'<(th|td)([^>]*)>(.*?)</\1>',
        re.DOTALL | re.IGNORECASE
    )
    _COLSPAN_RE = re.compile(r'colspan=["\']?(\d+)', re.IGNORECASE)
    _ROWSPAN_RE = re.compile(r'rowspan=["\']?(\d+)', re.IGNORECASE)
    _TAG_RE = re.compile(r'<[^>]+>')

    def convert_all(self, html):
        """HTML 내 모든 <table> 블록을 마크다운으로 치환."""
        def _replace(match):
            try:
                return self._convert_table(match.group(0))
            except Exception:
                # 파싱 실패 시 태그만 제거
                return self._strip_tags(match.group(0))
        return self._TABLE_RE.sub(_replace, html)

    def _convert_table(self, table_html):
        """단일 테이블 HTML → 마크다운."""
        rows_raw = self._ROW_RE.findall(table_html)
        if not rows_raw:
            return self._strip_tags(table_html)

        # 셀 파싱
        parsed_rows = []
        has_merge = False
        for row_html in rows_raw:
            cells = []
            for tag, attrs, content in self._CELL_RE.findall(row_html):
                is_header = tag.lower() == 'th'
                text = self._strip_tags(content).strip()
                # 셀 내 줄바꿈을 공백으로
                text = re.sub(r'\s+', ' ', text)

                cs_m = self._COLSPAN_RE.search(attrs)
                rs_m = self._ROWSPAN_RE.search(attrs)
                colspan = int(cs_m.group(1)) if cs_m else 1
                rowspan = int(rs_m.group(1)) if rs_m else 1
                if colspan > 1 or rowspan > 1:
                    has_merge = True

                cells.append({
                    'text': text,
                    'colspan': colspan,
                    'rowspan': rowspan,
                    'is_header': is_header,
                })
            if cells:
                parsed_rows.append(cells)

        if not parsed_rows:
            return self._strip_tags(table_html)

        if has_merge:
            return self._to_kv_format(parsed_rows)
        return self._to_gfm_table(parsed_rows)

    def _to_gfm_table(self, rows):
        """단순 테이블 → GFM 마크다운 테이블."""
        if not rows:
            return ''

        # 열 개수 결정
        num_cols = max(len(row) for row in rows)

        # 헤더 행 판별: 첫 행이 모두 th이면 헤더
        header_row = rows[0]
        is_header = all(c['is_header'] for c in header_row)

        lines = []
        for i, row in enumerate(rows):
            cells_text = [c['text'] for c in row]
            # 열 수 맞추기
            while len(cells_text) < num_cols:
                cells_text.append('')
            line = '| ' + ' | '.join(cells_text) + ' |'
            lines.append(line)

            # 헤더 구분선
            if i == 0 and is_header:
                sep = '| ' + ' | '.join(['---'] * num_cols) + ' |'
                lines.append(sep)

        # 헤더가 없으면 첫 행 뒤에 구분선 삽입 (GFM 필수)
        if not is_header and len(rows) > 1:
            sep = '| ' + ' | '.join(['---'] * num_cols) + ' |'
            lines.insert(1, sep)

        return '\n' + '\n'.join(lines) + '\n'

    def _to_kv_format(self, rows):
        """병합 셀이 있는 테이블 → 행별 key-value 형식."""
        # 2D 그리드 구축 (colspan/rowspan 확장)
        grid = self._build_grid(rows)
        if not grid or not grid[0]:
            return self._rows_to_plain(rows)

        # 첫 행을 헤더로 사용
        headers = grid[0]
        lines = []
        for r in range(1, len(grid)):
            parts = []
            for c in range(len(grid[r])):
                header = headers[c] if c < len(headers) else f'Col{c+1}'
                value = grid[r][c]
                if value and value != header:
                    parts.append(f'{header}: {value}')
            if parts:
                lines.append(' | '.join(parts))

        if not lines:
            # 데이터 행이 없으면 헤더만 출력
            return '\n' + ' | '.join(headers) + '\n'
        return '\n' + '\n'.join(lines) + '\n'

    def _build_grid(self, rows):
        """colspan/rowspan을 확장한 2D 텍스트 그리드."""
        # 최대 열 수 계산
        max_cols = 0
        for row in rows:
            cols = sum(c['colspan'] for c in row)
            max_cols = max(max_cols, cols)

        num_rows = len(rows)
        # 빈 그리드
        grid = [['' for _ in range(max_cols)] for _ in range(num_rows)]
        # 점유 플래그
        occupied = [[False] * max_cols for _ in range(num_rows)]

        for r, row in enumerate(rows):
            col_idx = 0
            for cell in row:
                # 이미 점유된 슬롯 건너뛰기
                while col_idx < max_cols and occupied[r][col_idx]:
                    col_idx += 1
                if col_idx >= max_cols:
                    break

                text = cell['text']
                cs = cell['colspan']
                rs = cell['rowspan']

                for dr in range(rs):
                    for dc in range(cs):
                        rr = r + dr
                        cc = col_idx + dc
                        if rr < num_rows and cc < max_cols:
                            occupied[rr][cc] = True
                            grid[rr][cc] = text

                col_idx += cs

        return grid

    def _rows_to_plain(self, rows):
        """폴백: 셀 텍스트를 줄바꿈으로 연결."""
        texts = []
        for row in rows:
            texts.append(' | '.join(c['text'] for c in row))
        return '\n' + '\n'.join(texts) + '\n'

    def _strip_tags(self, html):
        """HTML 태그 제거."""
        text = self._TAG_RE.sub(' ', html)
        return re.sub(r'\s+', ' ', text).strip()


# ===================================================================
# MathConverter — MathML → LaTeX
# ===================================================================

class MathConverter:
    """MathML을 LaTeX 문자열로 변환."""

    # display math: <div class="math-display"><math display="block">...</math></div>
    _DISPLAY_MATH_RE = re.compile(
        r'<div\s+class="math-display">\s*<math[^>]*>.*?</math>\s*</div>',
        re.DOTALL | re.IGNORECASE
    )
    # inline math: <math>...</math> (display math가 아닌 것)
    _INLINE_MATH_RE = re.compile(
        r'<math[^>]*>.*?</math>',
        re.DOTALL | re.IGNORECASE
    )
    _TAG_RE = re.compile(r'<[^>]+>')

    # 특수 기호 → LaTeX 매핑
    _SYMBOL_MAP = {
        '\u00B7': r'\cdot',
        '\u00D7': r'\times',
        '\u00F7': r'\div',
        '\u2212': '-',
        '\u2013': '-',       # en-dash
        '\u2014': '-',       # em-dash
        '\u2032': "'",       # prime
        '\u2033': "''",      # double prime
        '\u2026': r'\ldots',
        '\u22C5': r'\cdot',
        '\u2264': r'\leq',
        '\u2265': r'\geq',
        '\u2260': r'\neq',
        '\u2248': r'\approx',
        '\u221E': r'\infty',
        '\u2202': r'\partial',
        '\u2207': r'\nabla',
        '\u2211': r'\sum',
        '\u220F': r'\prod',
        '\u222B': r'\int',
        '\u222C': r'\iint',
        '\u222D': r'\iiint',
        '\u222E': r'\oint',
        '\u2208': r'\in',
        '\u2209': r'\notin',
        '\u2282': r'\subset',
        '\u2283': r'\supset',
        '\u2286': r'\subseteq',
        '\u2287': r'\supseteq',
        '\u222A': r'\cup',
        '\u2229': r'\cap',
        '\u2227': r'\wedge',
        '\u2228': r'\vee',
        '\u00AC': r'\neg',
        '\u2200': r'\forall',
        '\u2203': r'\exists',
        '\u2190': r'\leftarrow',
        '\u2192': r'\rightarrow',
        '\u21D0': r'\Leftarrow',
        '\u21D2': r'\Rightarrow',
        '\u21D4': r'\Leftrightarrow',
        '\u2061': '',        # function application (invisible)
        '\u2062': '',        # invisible times
        '\u2063': '',        # invisible separator
    }

    # 그리스 문자 → LaTeX
    _GREEK_MAP = {
        '\u03B1': r'\alpha', '\u03B2': r'\beta', '\u03B3': r'\gamma',
        '\u03B4': r'\delta', '\u03B5': r'\epsilon', '\u03B6': r'\zeta',
        '\u03B7': r'\eta', '\u03B8': r'\theta', '\u03B9': r'\iota',
        '\u03BA': r'\kappa', '\u03BB': r'\lambda', '\u03BC': r'\mu',
        '\u03BD': r'\nu', '\u03BE': r'\xi', '\u03C0': r'\pi',
        '\u03C1': r'\rho', '\u03C3': r'\sigma', '\u03C4': r'\tau',
        '\u03C5': r'\upsilon', '\u03C6': r'\phi', '\u03C7': r'\chi',
        '\u03C8': r'\psi', '\u03C9': r'\omega',
        '\u0393': r'\Gamma', '\u0394': r'\Delta', '\u0398': r'\Theta',
        '\u039B': r'\Lambda', '\u039E': r'\Xi', '\u03A0': r'\Pi',
        '\u03A3': r'\Sigma', '\u03A6': r'\Phi', '\u03A8': r'\Psi',
        '\u03A9': r'\Omega',
    }

    def convert_all(self, html):
        """HTML 내 모든 MathML을 LaTeX로 치환."""
        # display math 먼저 (더 구체적 패턴)
        html = self._DISPLAY_MATH_RE.sub(self._replace_display, html)
        # inline math
        html = self._INLINE_MATH_RE.sub(self._replace_inline, html)
        return html

    def _replace_display(self, match):
        try:
            latex = self._mathml_to_latex(match.group(0), display=True)
            return f'\n$${latex}$$\n'
        except Exception:
            return self._strip_tags(match.group(0))

    def _replace_inline(self, match):
        try:
            latex = self._mathml_to_latex(match.group(0), display=False)
            return f'${latex}$'
        except Exception:
            return self._strip_tags(match.group(0))

    def _mathml_to_latex(self, mathml_str, display=False):
        """MathML 문자열 → LaTeX 문자열."""
        # <math ...> 태그만 추출 (display div wrapper 제거)
        math_match = re.search(r'<math[^>]*>.*</math>', mathml_str, re.DOTALL)
        if not math_match:
            raise ValueError('No <math> tag found')

        math_str = math_match.group(0)

        # 네임스페이스 정리 (파싱 용이하게)
        math_str = re.sub(r'\s+xmlns[^"]*"[^"]*"', '', math_str)
        math_str = math_str.replace('&nbsp;', ' ')

        root = ET.fromstring(math_str)
        return self._convert_node(root).strip()

    def _convert_node(self, node):
        """MathML 노드를 LaTeX로 재귀 변환."""
        tag = self._local_tag(node)

        dispatch = {
            'math': self._conv_children,
            'mrow': self._conv_children,
            'mn': self._conv_text,
            'mi': self._conv_mi,
            'mo': self._conv_mo,
            'mtext': self._conv_mtext,
            'ms': self._conv_text,
            'mspace': lambda n: ' ',
            'mfrac': self._conv_mfrac,
            'msub': self._conv_msub,
            'msup': self._conv_msup,
            'msubsup': self._conv_msubsup,
            'msqrt': self._conv_msqrt,
            'mroot': self._conv_mroot,
            'munder': self._conv_munder,
            'mover': self._conv_mover,
            'munderover': self._conv_munderover,
            'mtable': self._conv_mtable,
            'mtr': self._conv_mtr,
            'mtd': self._conv_children,
            'mfenced': self._conv_mfenced,
            'menclose': self._conv_menclose,
            'mphantom': self._conv_mphantom,
            'mmultiscripts': self._conv_mmultiscripts,
            'mprescripts': lambda n: '',
            'none': lambda n: '',
        }

        handler = dispatch.get(tag)
        if handler:
            return handler(node)
        # 미지원 태그: 자식 재귀
        return self._conv_children(node)

    def _conv_children(self, node):
        """모든 자식 노드를 변환하여 결합."""
        parts = []
        for child in node:
            parts.append(self._convert_node(child))
        return ''.join(parts)

    def _conv_text(self, node):
        """텍스트 노드 (mn, ms 등)."""
        text = self._get_text(node)
        return self._escape_latex(text)

    def _conv_mi(self, node):
        """<mi> — 변수/식별자."""
        text = self._get_text(node)
        if not text:
            return ''
        # 그리스 문자
        if text in self._GREEK_MAP:
            return self._GREEK_MAP[text]
        # 단일 문자면 그대로 (이탤릭은 LaTeX 기본)
        if len(text) == 1:
            return self._escape_latex(text)
        # 여러 문자 식별자 (함수명 등)
        return r'\mathrm{' + self._escape_latex(text) + '}'

    def _conv_mo(self, node):
        """<mo> — 연산자."""
        text = self._get_text(node)
        if not text:
            return ''
        # 기호 매핑
        if text in self._SYMBOL_MAP:
            result = self._SYMBOL_MAP[text]
            if result and result.startswith('\\'):
                return result + ' '
            return result
        if text in self._GREEK_MAP:
            return self._GREEK_MAP[text]
        # 기본 연산자
        return self._escape_latex(text)

    def _conv_mtext(self, node):
        """<mtext> — 일반 텍스트."""
        text = self._get_text(node)
        if not text or not text.strip():
            return ' '
        return r'\text{' + text + '}'

    def _conv_mfrac(self, node):
        """<mfrac> → \\frac{num}{den}.

        MathML 스펙상 mfrac은 자식 2개여야 하나,
        OMML 변환기가 mrow 없이 여러 자식을 넣는 경우가 있음.
        이때 마지막 자식 = 분모, 나머지 = 분자로 해석.
        """
        children = list(node)
        if len(children) < 2:
            return self._conv_children(node)
        if len(children) == 2:
            num = self._convert_node(children[0])
            den = self._convert_node(children[1])
        else:
            # 마지막 = 분모, 나머지 = 분자
            num = ''.join(self._convert_node(c) for c in children[:-1])
            den = self._convert_node(children[-1])
        return r'\frac{' + num + '}{' + den + '}'

    def _conv_msub(self, node):
        """<msub> → base_{sub}."""
        children = list(node)
        if len(children) < 2:
            return self._conv_children(node)
        base = self._convert_node(children[0])
        sub = self._convert_node(children[1])
        return base + '_{' + sub + '}'

    def _conv_msup(self, node):
        """<msup> → base^{sup}."""
        children = list(node)
        if len(children) < 2:
            return self._conv_children(node)
        base = self._convert_node(children[0])
        sup = self._convert_node(children[1])
        return base + '^{' + sup + '}'

    def _conv_msubsup(self, node):
        """<msubsup> → base_{sub}^{sup}."""
        children = list(node)
        if len(children) < 3:
            return self._conv_children(node)
        base = self._convert_node(children[0])
        sub = self._convert_node(children[1])
        sup = self._convert_node(children[2])
        return base + '_{' + sub + '}^{' + sup + '}'

    def _conv_msqrt(self, node):
        """<msqrt> → \\sqrt{content}."""
        content = self._conv_children(node)
        return r'\sqrt{' + content + '}'

    def _conv_mroot(self, node):
        """<mroot> → \\sqrt[n]{content}."""
        children = list(node)
        if len(children) < 2:
            return r'\sqrt{' + self._conv_children(node) + '}'
        base = self._convert_node(children[0])
        index = self._convert_node(children[1])
        return r'\sqrt[' + index + ']{' + base + '}'

    def _conv_munder(self, node):
        """<munder> → base 아래 첨자."""
        children = list(node)
        if len(children) < 2:
            return self._conv_children(node)
        base = self._convert_node(children[0])
        under = self._convert_node(children[1])

        # 합/적분 등 큰 연산자
        base_stripped = base.strip()
        if base_stripped in (r'\sum', r'\prod', r'\int', r'\lim',
                             r'\bigcup', r'\bigcap', r'\coprod'):
            return base_stripped + '_{' + under + '}'
        return r'\underset{' + under + '}{' + base + '}'

    def _conv_mover(self, node):
        """<mover> → base 위 첨자."""
        children = list(node)
        if len(children) < 2:
            return self._conv_children(node)
        base = self._convert_node(children[0])
        over = self._convert_node(children[1])

        # accent (hat, bar, vec, tilde 등)
        over_stripped = over.strip()
        accent_map = {
            '\u0302': 'hat', '\u0303': 'tilde', '\u0304': 'bar',
            '\u0305': 'bar', '\u00AF': 'bar', '\u20D7': 'vec',
            '\u0307': 'dot', '\u0308': 'ddot',
        }
        for char, cmd in accent_map.items():
            if over_stripped == char or over_stripped == self._escape_latex(char):
                return '\\' + cmd + '{' + base + '}'

        base_stripped = base.strip()
        if base_stripped in (r'\sum', r'\prod', r'\int'):
            return base_stripped + '^{' + over + '}'
        return r'\overset{' + over + '}{' + base + '}'

    def _conv_munderover(self, node):
        """<munderover> → base_{under}^{over}."""
        children = list(node)
        if len(children) < 3:
            return self._conv_children(node)
        base = self._convert_node(children[0])
        under = self._convert_node(children[1])
        over = self._convert_node(children[2])
        return base.strip() + '_{' + under + '}^{' + over + '}'

    def _conv_mtable(self, node):
        """<mtable> → LaTeX array/matrix."""
        rows = []
        for child in node:
            tag = self._local_tag(child)
            if tag == 'mtr':
                rows.append(self._conv_mtr(child))
        return r'\begin{matrix}' + r' \\ '.join(rows) + r'\end{matrix}'

    def _conv_mtr(self, node):
        """<mtr> → row cells joined by &."""
        cells = []
        for child in node:
            tag = self._local_tag(child)
            if tag == 'mtd':
                cells.append(self._conv_children(child))
        return ' & '.join(cells)

    def _conv_mfenced(self, node):
        """<mfenced> → \\left( ... \\right)."""
        open_d = node.get('open', '(')
        close_d = node.get('close', ')')
        sep = node.get('separators', ',')
        children = list(node)
        parts = []
        for i, child in enumerate(children):
            if i > 0 and sep:
                parts.append(sep[min(i-1, len(sep)-1)])
            parts.append(self._convert_node(child))
        return r'\left' + open_d + ' '.join(parts) + r'\right' + close_d

    def _conv_menclose(self, node):
        """<menclose> → 내용만 추출 (notation 무시)."""
        return self._conv_children(node)

    def _conv_mphantom(self, node):
        """<mphantom> → \\phantom{content}."""
        return r'\phantom{' + self._conv_children(node) + '}'

    def _conv_mmultiscripts(self, node):
        """<mmultiscripts> → 앞첨자/뒤첨자."""
        # 단순 처리: prescripts 이전이 base+sub+sup, 이후가 presub+presup
        children = list(node)
        pre_idx = None
        for i, child in enumerate(children):
            if self._local_tag(child) == 'mprescripts':
                pre_idx = i
                break

        if pre_idx is not None and pre_idx >= 1:
            base = self._convert_node(children[0])
            # prescripts 이후
            pre_parts = children[pre_idx+1:]
            pre_sub = self._convert_node(pre_parts[0]) if len(pre_parts) > 0 else ''
            pre_sup = self._convert_node(pre_parts[1]) if len(pre_parts) > 1 else ''
            result = ''
            if pre_sub:
                result += '_{' + pre_sub + '}'
            if pre_sup:
                result += '^{' + pre_sup + '}'
            result += base
            return result

        return self._conv_children(node)

    # ── 유틸리티 ──────────────────────────────────────────────────

    def _local_tag(self, node):
        """네임스페이스 제거."""
        tag = node.tag
        if '}' in tag:
            return tag.split('}', 1)[1]
        return tag

    def _get_text(self, node):
        """노드의 직접 텍스트 + 자식 텍스트 수집."""
        # itertext()로 모든 하위 텍스트 수집
        return ''.join(node.itertext())

    def _escape_latex(self, text):
        """LaTeX 특수 문자 이스케이프 (최소한)."""
        if not text:
            return ''
        # 기호 변환
        result = []
        for ch in text:
            if ch in self._SYMBOL_MAP:
                mapped = self._SYMBOL_MAP[ch]
                result.append(mapped + ' ' if mapped.startswith('\\') else mapped)
            elif ch in self._GREEK_MAP:
                result.append(self._GREEK_MAP[ch])
            else:
                result.append(ch)
        return ''.join(result)

    def _strip_tags(self, html):
        """HTML 태그 제거."""
        text = self._TAG_RE.sub(' ', html)
        return re.sub(r'\s+', ' ', text).strip()


# ===================================================================
# 통합 함수
# ===================================================================

def html_to_searchable_text(html_content):
    """
    HTML → 검색용 텍스트 변환 (구조 보존).

    1. <table> → 마크다운 테이블
    2. MathML → LaTeX
    3. 나머지 HTML 태그 제거 + 엔티티 디코딩 + 공백 정리
    """
    if not html_content:
        return ''

    text = html_content

    # 1. 테이블 변환
    table_conv = TableConverter()
    text = table_conv.convert_all(text)

    # 2. 수식 변환
    math_conv = MathConverter()
    text = math_conv.convert_all(text)

    # 3. 나머지 HTML 태그 제거
    text = re.sub(r'<[^>]+>', ' ', text)

    # 4. HTML 엔티티 디코딩
    text = html_module.unescape(text)

    # 5. 공백 정리 (마크다운 테이블의 줄바꿈은 보존)
    # 연속 빈줄 → 단일 빈줄
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 각 줄의 앞뒤 공백 정리
    lines = text.split('\n')
    lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in lines]
    # 빈줄만 있는 연속 줄 제거
    cleaned = []
    prev_empty = False
    for line in lines:
        if not line:
            if not prev_empty:
                cleaned.append('')
            prev_empty = True
        else:
            cleaned.append(line)
            prev_empty = False
    text = '\n'.join(cleaned).strip()

    return text
