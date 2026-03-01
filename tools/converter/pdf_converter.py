#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PDF to HTML Converter - TOC 기반 제목 구조 변환
"""

import json
import os
import re
import hashlib
import difflib
from pathlib import Path
from dataclasses import dataclass, field

try:
    import fitz  # PyMuPDF
except ImportError:
    raise ImportError("PyMuPDF 패키지가 필요합니다. pip install PyMuPDF 를 실행하세요.")

from utils import (
    get_logger, ensure_dir, get_image_dir, escape_html,
    ConversionResult
)


# ===== 데이터 클래스 =====

@dataclass
class TocEntry:
    """TOC 항목"""
    raw_text: str        # TOC 원본 텍스트
    clean_text: str      # 점선/페이지번호 제거된 텍스트
    heading_level: int   # 1=h1, 2=h2, ...
    page_number: int     # TOC에 표시된 페이지 번호
    is_section: bool     # True=섹션 제목, False=Figure/Table 참조
    numbering: str       # "3.2" 같은 번호 접두사


@dataclass
class MatchResult:
    """TOC-본문 매칭 결과"""
    toc_entry: TocEntry
    matched: bool
    matched_text: str = ""
    page_num: int = 0
    similarity: float = 0.0
    suggestions: list = field(default_factory=list)


class PdfConverter:
    """PDF 문서를 HTML로 변환하는 클래스 (TOC 기반)"""

    _CAPTION_PATTERN = re.compile(
        r'^(?:Figure|Fig\.?|Table|Tab\.?|그림|표)\s+'
        r'\d+(?:[-.]?\d+)*'
        r'\s*[:：–—\-.]',
        re.IGNORECASE
    )

    def __init__(self, config_path=None):
        """
        Args:
            config_path: 설정 파일 경로 (기본값: ../config.json)
        """
        self.config = self._load_config(config_path)
        self.pdf_config = self.config.get('pdf', self._default_pdf_config())
        self.logger = get_logger()

    def _load_config(self, config_path):
        """설정 파일 로드"""
        if config_path is None:
            base_dir = Path(__file__).parent
            config_path = base_dir / "config.json"

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {'pdf': self._default_pdf_config()}

    def _default_pdf_config(self):
        """기본 PDF 설정"""
        return {
            "toc_keywords": ["Table of Contents", "Contents", "목차"],
            "toc_max_search_pages": 10,
            "non_heading_prefixes": ["Figure", "Table", "그림", "표", "List of"],
            "heading_prefixes_as_section": ["Appendix", "부록"],
            "matching": {
                "fuzzy_threshold": 0.80,
                "suggestion_threshold": 0.50,
                "page_search_window": 2,
                "max_suggestions": 3
            },
            "options": {
                "generate_report": True,
                "extract_images": True,
                "extract_tables": True
            }
        }

    # ===== 공개 API =====

    def convert(self, input_path, output_path=None, options=None):
        """
        PDF 문서를 HTML로 변환

        Args:
            input_path: 입력 .pdf 파일 경로
            output_path: 출력 .html 파일 경로 (선택)
            options: 변환 옵션 오버라이드 (선택)

        Returns:
            ConversionResult: 변환 결과 정보
        """
        result = ConversionResult(input_path)
        input_path = Path(input_path)

        # 입력 파일 검증
        if not input_path.exists():
            result.error_message = f"파일을 찾을 수 없습니다: {input_path}"
            return result

        if input_path.suffix.lower() != '.pdf':
            result.error_message = f"지원하지 않는 파일 형식입니다: {input_path.suffix}"
            return result

        # 출력 경로 설정
        if output_path is None:
            output_path = input_path.with_suffix('.html')
        output_path = Path(output_path)
        result.output_path = output_path

        # 옵션 병합
        merged_options = {**self.pdf_config.get('options', {})}
        if options:
            merged_options.update(options)

        try:
            # PDF 열기
            doc = fitz.open(str(input_path))
            self.logger.info(f"PDF 로드 완료: {input_path} ({len(doc)}페이지)")

            # TOC 페이지 탐지
            toc_start, toc_end = self._find_toc_pages(doc)

            # TOC 항목 파싱
            toc_entries = []
            if toc_start is not None:
                toc_entries = self._parse_toc_entries(doc, toc_start, toc_end)
                self.logger.info(f"TOC 항목 {len(toc_entries)}개 파싱 완료")
            else:
                self.logger.warning("TOC를 찾을 수 없습니다. 모든 텍스트를 본문으로 처리합니다.")
                result.add_warning("TOC를 찾을 수 없어 제목 구조를 판별하지 못했습니다.")

            # 본문 시작 페이지 결정
            body_start = (toc_end + 1) if toc_end is not None else 0

            # 페이지별 텍스트 블록 추출
            pages_data = self._extract_pages_data(doc, body_start)

            # TOC-본문 매칭
            match_results = []
            if toc_entries:
                match_results = self._match_toc_to_body(toc_entries, pages_data, body_start)

                # 통계 집계
                for mr in match_results:
                    if mr.toc_entry.is_section:
                        level = mr.toc_entry.heading_level
                        tag = f'h{level}'
                        result.stats['headings'][tag] = result.stats['headings'].get(tag, 0) + 1

            # 이미지 추출
            image_map = {}
            if merged_options.get('extract_images', True):
                image_dir = get_image_dir(output_path)
                image_map = self._extract_images(doc, image_dir, output_path)
                result.stats['images'] = len(image_map)

            # HTML 생성
            html_content = self._generate_html(
                doc, pages_data, match_results, image_map, body_start, merged_options
            )

            # 테이블 수 집계
            if merged_options.get('extract_tables', True):
                for page_num in range(body_start, len(doc)):
                    page = doc[page_num]
                    try:
                        tables = page.find_tables()
                        result.stats['tables'] += len(tables.tables)
                    except Exception:
                        pass

            # 문단 수 집계
            result.stats['paragraphs'] = html_content.count('<p')

            # 파일 저장
            ensure_dir(output_path.parent)
            encoding = self.config.get('output', {}).get('encoding', 'utf-8')

            with open(output_path, 'w', encoding=encoding) as f:
                f.write(html_content)

            self.logger.info(f"HTML 변환 완료: {output_path}")

            # 매칭 리포트 생성
            if merged_options.get('generate_report', True) and match_results:
                report_path = output_path.with_name(f"{input_path.stem}_report.txt")
                self._generate_report(match_results, input_path.name, report_path)
                self.logger.info(f"매칭 리포트 생성: {report_path}")

            doc.close()
            result.success = True

        except Exception as e:
            result.error_message = str(e)
            self.logger.error(f"변환 실패: {input_path} - {e}")

        return result

    def analyze(self, input_path):
        """
        PDF 문서 구조 분석

        Args:
            input_path: 입력 .pdf 파일 경로

        Returns:
            dict: 문서 구조 정보
        """
        input_path = Path(input_path)

        if not input_path.exists():
            return {'error': f"파일을 찾을 수 없습니다: {input_path}"}

        try:
            doc = fitz.open(str(input_path))

            analysis = {
                'filename': input_path.name,
                'pages': len(doc),
                'headings': {'h1': 0, 'h2': 0, 'h3': 0, 'h4': 0, 'h5': 0, 'h6': 0},
                'images': 0,
                'tables': 0,
                'toc_found': False,
                'toc_entries': 0,
                'warnings': []
            }

            # TOC 탐지
            toc_start, toc_end = self._find_toc_pages(doc)
            if toc_start is not None:
                analysis['toc_found'] = True
                toc_entries = self._parse_toc_entries(doc, toc_start, toc_end)
                analysis['toc_entries'] = len(toc_entries)

                for entry in toc_entries:
                    if entry.is_section:
                        tag = f'h{entry.heading_level}'
                        analysis['headings'][tag] = analysis['headings'].get(tag, 0) + 1
            else:
                analysis['warnings'].append("TOC를 찾을 수 없습니다.")

            # 이미지/테이블 수
            for page in doc:
                analysis['images'] += len(page.get_images())
                try:
                    tables = page.find_tables()
                    analysis['tables'] += len(tables.tables)
                except Exception:
                    pass

            doc.close()
            return analysis

        except Exception as e:
            return {'error': str(e)}

    # ===== 캡션 감지 =====

    def _detect_caption(self, text):
        """캡션 패턴 감지 → caption ID 반환 또는 None"""
        if self._CAPTION_PATTERN.match(text):
            return self._make_caption_id(text)
        return None

    def _make_caption_id(self, text):
        """캡션 텍스트에서 ID 생성 (예: 'fig-2-1', 'tbl-3')"""
        m = re.match(
            r'^(Figure|Fig\.?|Table|Tab\.?|그림|표)\s+(\d+(?:[-.]?\d+)*)',
            text, re.IGNORECASE
        )
        if not m:
            return None
        keyword = m.group(1).rstrip('.').lower()
        number = m.group(2).replace('.', '-')
        prefix_map = {
            'figure': 'fig', 'fig': 'fig',
            'table': 'tbl', 'tab': 'tbl',
            '그림': 'fig', '표': 'tbl'
        }
        prefix = prefix_map.get(keyword, 'fig')
        return f'{prefix}-{number}'

    # ===== TOC 파싱 =====

    def _find_toc_pages(self, doc):
        """
        TOC 시작/끝 페이지 탐지

        Args:
            doc: fitz.Document 객체

        Returns:
            tuple: (toc_start, toc_end) 페이지 인덱스, 없으면 (None, None)
        """
        max_search = min(
            self.pdf_config.get('toc_max_search_pages', 10),
            len(doc)
        )
        toc_keywords = self.pdf_config.get('toc_keywords', [])
        dot_pattern = re.compile(r'\.{4,}')

        toc_start = None

        for page_num in range(max_search):
            page = doc[page_num]
            text = page.get_text()

            # TOC 키워드 탐지
            if toc_start is None:
                for keyword in toc_keywords:
                    if keyword.lower() in text.lower():
                        toc_start = page_num
                        break

            # TOC 시작 이후, 점선이 없어지면 TOC 끝
            if toc_start is not None and page_num > toc_start:
                if not dot_pattern.search(text):
                    # 이 페이지에 점선이 없으면 이전 페이지까지가 TOC
                    return toc_start, page_num - 1

        # TOC 시작은 찾았지만 끝이 명확하지 않은 경우
        if toc_start is not None:
            # 점선이 있는 마지막 페이지 찾기
            last_dot_page = toc_start
            for page_num in range(toc_start, max_search):
                page = doc[page_num]
                text = page.get_text()
                if dot_pattern.search(text):
                    last_dot_page = page_num
            return toc_start, last_dot_page

        return None, None

    def _parse_toc_entries(self, doc, toc_start, toc_end):
        """
        TOC 페이지에서 항목 파싱

        Args:
            doc: fitz.Document 객체
            toc_start: TOC 시작 페이지 인덱스
            toc_end: TOC 끝 페이지 인덱스

        Returns:
            list[TocEntry]: TOC 항목 리스트
        """
        entries = []
        toc_keywords_lower = [kw.lower() for kw in self.pdf_config.get('toc_keywords', [])]

        for page_num in range(toc_start, toc_end + 1):
            page = doc[page_num]
            text = page.get_text()
            lines = text.split('\n')

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # TOC 키워드 자체는 건너뜀
                if line.lower() in toc_keywords_lower:
                    continue

                # 점선 + 페이지번호 패턴이 있는 줄만 TOC 항목으로 판단
                # 패턴: "제목 텍스트 ..... 123" 또는 "제목 텍스트 123"
                page_num_match = re.search(r'[.\s]*(\d+)\s*$', line)
                if not page_num_match:
                    continue

                target_page = int(page_num_match.group(1))

                # clean_text: 점선과 페이지번호 제거
                clean = re.sub(r'\s*\.{2,}\s*\d+\s*$', '', line)
                clean = re.sub(r'\s+\d+\s*$', '', clean)
                clean = clean.strip()

                if not clean:
                    continue

                # 순수 숫자만으로 된 항목은 페이지 번호이므로 건너뜀
                if re.match(r'^\d+$', clean):
                    continue

                # 섹션 제목 여부 판단
                is_section = self._is_section_heading(clean)

                # 번호 접두사 추출 및 레벨 결정
                numbering = self._extract_numbering(clean)
                heading_level = self._determine_heading_level(clean, numbering)

                entries.append(TocEntry(
                    raw_text=line,
                    clean_text=clean,
                    heading_level=heading_level,
                    page_number=target_page,
                    is_section=is_section,
                    numbering=numbering
                ))

        return entries

    def _is_section_heading(self, text):
        """
        섹션 제목인지 판별 (Figure/Table 참조가 아닌지)

        Args:
            text: 정리된 TOC 텍스트

        Returns:
            bool: 섹션 제목이면 True
        """
        non_heading_prefixes = self.pdf_config.get('non_heading_prefixes', [])
        for prefix in non_heading_prefixes:
            if text.lower().startswith(prefix.lower()):
                return False
        return True

    def _extract_numbering(self, text):
        """
        텍스트에서 번호 접두사 추출

        Args:
            text: TOC 항목 텍스트

        Returns:
            str: 번호 접두사 (예: "3.2.1") 또는 빈 문자열
        """
        # "3.2.1 Title" 또는 "3.2.1. Title" 패턴
        match = re.match(r'^(\d+(?:\.\d+)*\.?)\s', text)
        if match:
            return match.group(1).rstrip('.')
        return ""

    def _determine_heading_level(self, text, numbering):
        """
        번호 패턴에서 제목 레벨 결정

        Args:
            text: TOC 항목 텍스트
            numbering: 추출된 번호 접두사

        Returns:
            int: 제목 레벨 (1~6)
        """
        if numbering:
            # 점(.) 개수 + 1 = 레벨: "1" → 1, "3.1" → 2, "4.1.1" → 3
            level = numbering.count('.') + 1
            return min(level, 6)

        # Appendix/부록 접두사 → h1
        section_prefixes = self.pdf_config.get('heading_prefixes_as_section', [])
        for prefix in section_prefixes:
            if text.lower().startswith(prefix.lower()):
                return 1

        # 번호 없는 항목 → h1 기본값
        return 1

    # ===== 본문 추출 =====

    def _extract_pages_data(self, doc, body_start):
        """
        본문 페이지에서 텍스트 블록 추출

        Args:
            doc: fitz.Document 객체
            body_start: 본문 시작 페이지 인덱스

        Returns:
            dict: {page_num: [text_blocks]} — 각 블록은 dict(text, bbox, flags)
        """
        pages_data = {}

        for page_num in range(body_start, len(doc)):
            page = doc[page_num]
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

            text_blocks = []
            for block in blocks:
                if block.get("type") != 0:  # 텍스트 블록만
                    continue

                block_text_parts = []
                is_bold = False
                is_italic = False

                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        span_text = span.get("text", "").strip()
                        if span_text:
                            block_text_parts.append(span_text)
                            flags = span.get("flags", 0)
                            # flags: bit 0 = superscript, bit 1 = italic, bit 4 = bold
                            if flags & (1 << 4):
                                is_bold = True
                            if flags & (1 << 1):
                                is_italic = True

                block_text = ' '.join(block_text_parts)
                if block_text.strip():
                    text_blocks.append({
                        'text': block_text.strip(),
                        'bbox': block.get("bbox", (0, 0, 0, 0)),
                        'is_bold': is_bold,
                        'is_italic': is_italic,
                    })

            pages_data[page_num] = text_blocks

        return pages_data

    # ===== TOC-본문 매칭 =====

    def _match_toc_to_body(self, toc_entries, pages_data, body_start):
        """
        TOC 항목을 본문 텍스트와 매칭

        Args:
            toc_entries: TocEntry 리스트
            pages_data: {page_num: [text_blocks]}
            body_start: 본문 시작 페이지 인덱스

        Returns:
            list[MatchResult]: 매칭 결과 리스트
        """
        matching_config = self.pdf_config.get('matching', {})
        fuzzy_threshold = matching_config.get('fuzzy_threshold', 0.80)
        suggestion_threshold = matching_config.get('suggestion_threshold', 0.50)
        page_window = matching_config.get('page_search_window', 2)
        max_suggestions = matching_config.get('max_suggestions', 3)

        results = []
        # 매칭된 블록을 추적하여 중복 매칭 방지
        matched_blocks = set()

        for entry in toc_entries:
            mr = MatchResult(toc_entry=entry, matched=False)

            if not entry.is_section:
                # Figure/Table 참조는 건너뜀
                results.append(mr)
                continue

            # 검색 범위: TOC 페이지번호 ± window
            # TOC의 page_number는 문서 표기 페이지이므로, 실제 인덱스로 변환 필요
            # 간단한 추정: body_start를 기준으로 오프셋
            estimated_page = body_start + entry.page_number - 1
            search_start = max(body_start, estimated_page - page_window)
            search_end = min(max(pages_data.keys()) + 1 if pages_data else body_start,
                            estimated_page + page_window + 1)

            toc_normalized = self._normalize_text(entry.clean_text)
            best_similarity = 0.0
            suggestions = []

            for pg in range(search_start, search_end):
                if pg not in pages_data:
                    continue

                for block_idx, block in enumerate(pages_data[pg]):
                    block_key = (pg, block_idx)
                    if block_key in matched_blocks:
                        continue

                    block_normalized = self._normalize_text(block['text'])

                    # 1차: 정규화 후 접두사 매칭
                    if block_normalized.startswith(toc_normalized):
                        mr.matched = True
                        mr.matched_text = block['text']
                        mr.page_num = pg
                        mr.similarity = 1.0
                        matched_blocks.add(block_key)
                        break

                    # 2차: 인접 블록 연결 (멀티라인 제목)
                    if block_idx + 1 < len(pages_data[pg]):
                        next_block = pages_data[pg][block_idx + 1]
                        combined = block_normalized + ' ' + self._normalize_text(next_block['text'])
                        if combined.startswith(toc_normalized):
                            mr.matched = True
                            mr.matched_text = block['text'] + ' ' + next_block['text']
                            mr.page_num = pg
                            mr.similarity = 1.0
                            matched_blocks.add(block_key)
                            matched_blocks.add((pg, block_idx + 1))
                            break

                    # 3차: 퍼지 매칭
                    similarity = difflib.SequenceMatcher(
                        None, toc_normalized, block_normalized
                    ).ratio()

                    if similarity >= fuzzy_threshold and similarity > best_similarity:
                        best_similarity = similarity
                        mr.matched = True
                        mr.matched_text = block['text']
                        mr.page_num = pg
                        mr.similarity = similarity
                        # 아직 break 안 함 — 더 높은 유사도 후보가 있을 수 있음

                    elif similarity >= suggestion_threshold:
                        suggestions.append({
                            'text': block['text'],
                            'page': pg,
                            'similarity': round(similarity, 2)
                        })

                if mr.matched and mr.similarity >= 1.0:
                    break

            # 매칭 성공 시 블록 등록
            if mr.matched and mr.similarity < 1.0:
                # 퍼지 매칭으로 찾은 경우, 해당 블록도 추적
                for pg in range(search_start, search_end):
                    if pg not in pages_data:
                        continue
                    for bi, block in enumerate(pages_data[pg]):
                        if block['text'] == mr.matched_text and (pg, bi) not in matched_blocks:
                            matched_blocks.add((pg, bi))
                            break

            # 실패 시 suggestions 저장
            if not mr.matched:
                suggestions.sort(key=lambda x: x['similarity'], reverse=True)
                mr.suggestions = suggestions[:max_suggestions]

            results.append(mr)

        return results

    def _normalize_text(self, text):
        """
        텍스트 정규화: 소문자화, 공백 축소, 후행 각주번호 제거

        Args:
            text: 원본 텍스트

        Returns:
            str: 정규화된 텍스트
        """
        text = text.lower()
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'(?<=\D)\s*\d+$', '', text)  # 후행 각주번호 제거 (문자 뒤에만)
        return text.strip()

    # ===== HTML 생성 =====

    def _generate_html(self, doc, pages_data, match_results, image_map, body_start, options):
        """
        HTML 생성

        Args:
            doc: fitz.Document 객체
            pages_data: {page_num: [text_blocks]}
            match_results: MatchResult 리스트
            image_map: {(page_num, img_idx): 상대경로}
            body_start: 본문 시작 페이지 인덱스
            options: 변환 옵션

        Returns:
            str: HTML 문자열
        """
        html_parts = []

        # 매칭된 텍스트 → (heading_level, toc_entry) 매핑 구축
        heading_map = {}
        for mr in match_results:
            if mr.matched and mr.toc_entry.is_section:
                normalized = self._normalize_text(mr.matched_text)
                if len(normalized) >= 2:  # 너무 짧은 키는 오매칭 방지
                    heading_map[normalized] = mr.toc_entry

        for page_num in sorted(pages_data.keys()):
            blocks = pages_data[page_num]

            # 테이블 추출
            if options.get('extract_tables', True):
                try:
                    page = doc[page_num]
                    tables = page.find_tables()
                    table_rects = []
                    for table in tables.tables:
                        table_rects.append(fitz.Rect(table.bbox))
                        table_html = self._table_to_html(table)
                        if table_html:
                            html_parts.append(table_html)
                except Exception:
                    table_rects = []
            else:
                table_rects = []

            # 이미지 추출
            page_images = {k: v for k, v in image_map.items() if k[0] == page_num}
            for img_key, img_path in page_images.items():
                html_parts.append(f'<p><img src="{escape_html(img_path)}" alt="" decoding="async"></p>')

            for block in blocks:
                block_text = block['text']
                block_rect = fitz.Rect(block['bbox'])

                # 테이블 영역 내의 텍스트 블록은 건너뜀 (이미 테이블로 처리)
                in_table = False
                for tr in table_rects:
                    if block_rect.intersects(tr):
                        in_table = True
                        break
                if in_table:
                    continue

                # 빈 텍스트 건너뜀
                if not block_text.strip():
                    continue

                # 단독 페이지 번호 건너뜀 (순수 숫자)
                if re.match(r'^\d+$', block_text.strip()):
                    continue

                # 제목 매칭 확인
                normalized = self._normalize_text(block_text)
                if normalized in heading_map:
                    entry = heading_map[normalized]
                    level = entry.heading_level
                    html_parts.append(f'<h{level}>{escape_html(block_text)}</h{level}>')
                else:
                    # 일반 본문
                    escaped = escape_html(block_text)
                    if block['is_bold']:
                        escaped = f'<strong>{escaped}</strong>'
                    if block['is_italic']:
                        escaped = f'<em>{escaped}</em>'
                    caption_id = self._detect_caption(block_text)
                    if caption_id:
                        html_parts.append(f'<p id="{caption_id}" class="caption">{escaped}</p>')
                    else:
                        html_parts.append(f'<p>{escaped}</p>')

        indent = self.config.get('output', {}).get('indent', True)
        if indent:
            return '\n\n'.join(html_parts)
        else:
            return ''.join(html_parts)

    def _table_to_html(self, table):
        """
        PyMuPDF Table 객체를 HTML로 변환

        Args:
            table: fitz Table 객체

        Returns:
            str: HTML table 문자열
        """
        try:
            data = table.extract()
        except Exception:
            return ''

        if not data:
            return ''

        rows_html = []
        for i, row in enumerate(data):
            cells_html = []
            for cell in row:
                cell_text = escape_html(str(cell).strip() if cell else '')
                if i == 0:
                    cells_html.append(f'<th>{cell_text}</th>')
                else:
                    cells_html.append(f'<td>{cell_text}</td>')
            rows_html.append('<tr>' + ''.join(cells_html) + '</tr>')

        if len(rows_html) > 1:
            thead = f'<thead>{rows_html[0]}</thead>'
            tbody = '<tbody>' + ''.join(rows_html[1:]) + '</tbody>'
            return f'<table>{thead}{tbody}</table>'
        elif rows_html:
            return f'<table><tbody>{"".join(rows_html)}</tbody></table>'
        return ''

    # ===== 이미지 추출 =====

    def _extract_images(self, doc, image_dir, output_path):
        """
        PDF에서 이미지를 추출하여 저장

        Args:
            doc: fitz.Document 객체
            image_dir: 이미지 저장 디렉토리
            output_path: HTML 출력 경로 (상대 경로 계산용)

        Returns:
            dict: {(page_num, img_idx): 상대경로}
        """
        image_map = {}
        has_images = False

        for page_num in range(len(doc)):
            page = doc[page_num]
            images = page.get_images()

            for img_idx, img_info in enumerate(images):
                xref = img_info[0]

                try:
                    img_data = doc.extract_image(xref)
                    if not img_data:
                        continue

                    image_bytes = img_data["image"]
                    ext = img_data.get("ext", "png")

                    # 이미지 디렉토리 생성 (최초 이미지 발견 시)
                    if not has_images:
                        ensure_dir(image_dir)
                        has_images = True

                    # 파일명 생성 (MD5 해시 기반)
                    hash_name = hashlib.md5(image_bytes).hexdigest()[:12]
                    filename = f"image_{hash_name}.{ext}"
                    image_path = image_dir / filename

                    # 이미지 저장
                    with open(image_path, 'wb') as f:
                        f.write(image_bytes)

                    # 상대 경로 계산
                    rel_path = os.path.relpath(image_path, output_path.parent)
                    rel_path = rel_path.replace('\\', '/')

                    image_map[(page_num, img_idx)] = rel_path
                    self.logger.debug(f"이미지 추출: {filename} (p.{page_num + 1})")

                except Exception as e:
                    self.logger.warning(f"이미지 추출 실패 (p.{page_num + 1}, xref={xref}): {e}")

        return image_map

    # ===== 리포트 생성 =====

    def _generate_report(self, match_results, filename, report_path):
        """
        매칭 리포트 생성

        Args:
            match_results: MatchResult 리스트
            filename: 원본 파일명
            report_path: 리포트 저장 경로
        """
        lines = []
        lines.append(f"[변환 리포트] {filename}")
        lines.append("─" * 50)

        section_total = 0
        section_matched = 0
        section_failed = 0

        for mr in match_results:
            entry = mr.toc_entry

            if not entry.is_section:
                lines.append(f'- [건너뜀] "{entry.clean_text}" (Figure/Table 참조)')
                continue

            section_total += 1
            level_label = f'h{entry.heading_level}'

            if mr.matched:
                section_matched += 1
                lines.append(
                    f'✓ {level_label}: "{entry.clean_text}" (p.{mr.page_num + 1}) '
                    f'→ 매칭 (유사도: {mr.similarity:.2f})'
                )
            else:
                section_failed += 1
                lines.append(
                    f'✗ {level_label}: "{entry.clean_text}" (p.{entry.page_number}) '
                    f'→ 매칭 실패'
                )
                for sug in mr.suggestions:
                    lines.append(
                        f'   유사 후보: "{sug["text"][:60]}" '
                        f'(p.{sug["page"] + 1}, {sug["similarity"]:.2f})'
                    )

        lines.append("─" * 50)
        match_rate = (section_matched / section_total * 100) if section_total > 0 else 0
        lines.append(
            f"섹션 제목: {section_total}개 | "
            f"매칭 성공: {section_matched} ({match_rate:.1f}%) | "
            f"실패: {section_failed}"
        )

        ensure_dir(report_path.parent)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))


# 테스트용
if __name__ == "__main__":
    converter = PdfConverter()
    print("PDF Config loaded:", json.dumps(converter.pdf_config, indent=2, ensure_ascii=False))
