#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KF-21 웹북 - 검색 인덱스 생성 스크립트

이 스크립트는 contents/ 폴더의 모든 HTML 파일을 스캔하여
검색 인덱스 JSON 파일(data/search-index.json)을 생성합니다.

사용법:
    python build-search-index.py              # 섹션 단위 인덱싱 (기본)
    python build-search-index.py --page       # 페이지 단위 인덱싱

요구사항:
    Python 3.6 이상
"""

import os
import json
import re
import argparse
from pathlib import Path
from html_to_text import html_to_searchable_text

# ===================================
# 설정
# ===================================

# 프로젝트 루트 디렉터리 (스크립트 위치 기준)
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
CONTENTS_DIR = PROJECT_ROOT / 'contents'
OUTPUT_FILE = PROJECT_ROOT / 'data' / 'search-index.json'
MENU_FILE = PROJECT_ROOT / 'data' / 'menu.json'

# 섹션 인덱싱 설정
HEADING_LEVELS = [1, 2, 3]      # 분할 기준 헤딩 레벨
MAX_SECTION_LENGTH = 3200       # 섹션 최대 길이 (약 800토큰)
MIN_SECTION_LENGTH = 100        # 너무 짧은 섹션은 이전 섹션에 병합

# ===================================
# 유틸리티 함수
# ===================================

def strip_html_tags(html_content):
    """HTML 태그를 제거하고 텍스트만 추출"""
    text = re.sub(r'<[^>]+>', ' ', html_content)
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&amp;', '&')
    text = text.replace('&quot;', '"')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_title_from_html(html_content):
    """HTML에서 첫 번째 h1 태그의 텍스트를 제목으로 추출"""
    match = re.search(r'<h1[^>]*>(.*?)</h1>', html_content, re.IGNORECASE | re.DOTALL)
    if match:
        return strip_html_tags(match.group(1))
    return None


def generate_section_id(title, existing_ids):
    """
    섹션 ID 생성 (중복 방지)
    JavaScript의 정규식과 동일하게 ASCII 기반으로 처리
    """
    # 기본 ID 생성: 한글/영문/숫자/하이픈만 유지 (ASCII \w와 동일하게)
    base_id = re.sub(r'[^a-zA-Z0-9_\s가-힣-]', '', title)
    base_id = re.sub(r'\s+', '-', base_id.strip())
    base_id = base_id.lower()[:50]  # 최대 50자

    if not base_id:
        base_id = 'section'

    # 중복 방지
    section_id = base_id
    counter = 1
    while section_id in existing_ids:
        section_id = f"{base_id}-{counter}"
        counter += 1

    existing_ids.add(section_id)
    return section_id


def load_menu_structure():
    """menu.json을 로드하여 URL과 경로 매핑을 생성"""
    if not MENU_FILE.exists():
        return {}

    with open(MENU_FILE, 'r', encoding='utf-8') as f:
        menu_data = json.load(f)

    url_to_path = {}

    def traverse_menu(items, path_parts):
        for item in items:
            label = item.get('label', '')
            current_path = path_parts + [label]

            if 'url' in item:
                url_to_path[item['url']] = ' > '.join(current_path)

            if 'children' in item:
                traverse_menu(item['children'], current_path)

    traverse_menu(menu_data, [])
    return url_to_path


# ===================================
# 섹션 파싱
# ===================================

def parse_sections(html_content, heading_levels=HEADING_LEVELS, inject_ids=False):
    """
    HTML에서 헤딩 기준으로 섹션 분할

    Args:
        html_content: HTML 문자열
        heading_levels: 분할 기준 헤딩 레벨 리스트
        inject_ids: True면 ID가 없는 헤딩에 ID 주입 (HTML 수정)

    Returns:
        tuple: (sections list, modified html if inject_ids else original html)
    """
    # 헤딩 패턴 생성 (h1, h2, h3 등)
    levels_pattern = '|'.join([f'h{l}' for l in heading_levels])
    heading_pattern = re.compile(
        rf'<({levels_pattern})([^>]*)>(.*?)</\1>',
        re.IGNORECASE | re.DOTALL
    )

    sections = []
    existing_ids = set()
    modifications = []  # (start, end, new_tag) 튜플 리스트

    for match in heading_pattern.finditer(html_content):
        tag = match.group(1).lower()
        attrs = match.group(2)
        title_html = match.group(3)

        level = int(tag[1])
        title = strip_html_tags(title_html).strip()

        # 기존 id 속성 추출 또는 새로 생성
        id_match = re.search(r'id=["\']([^"\']+)["\']', attrs)
        if id_match:
            section_id = id_match.group(1)
            existing_ids.add(section_id)
        else:
            section_id = generate_section_id(title, existing_ids)
            # ID 주입이 필요한 경우 기록
            if inject_ids:
                new_tag = f'<{tag} id="{section_id}"{attrs}>{title_html}</{tag}>'
                modifications.append((match.start(), match.end(), new_tag))

        # 이전 섹션의 콘텐츠 범위 설정
        if sections:
            sections[-1]['_end'] = match.start()

        sections.append({
            'level': level,
            'title': title,
            'id': section_id,
            '_start': match.end(),
            '_end': len(html_content)  # 임시, 다음 섹션에서 업데이트
        })

    # 콘텐츠 추출
    for section in sections:
        content_html = html_content[section['_start']:section['_end']]
        section['content'] = html_to_searchable_text(content_html)
        del section['_start']
        del section['_end']

    # HTML 수정 (뒤에서부터 적용하여 인덱스 유지)
    modified_html = html_content
    if inject_ids and modifications:
        for start, end, new_tag in reversed(modifications):
            modified_html = modified_html[:start] + new_tag + modified_html[end:]

    return sections, modified_html


def merge_short_sections(sections, min_length=MIN_SECTION_LENGTH):
    """짧은 섹션을 이전 섹션에 병합"""
    if not sections:
        return sections

    merged = [sections[0]]

    for section in sections[1:]:
        if len(section['content']) < min_length and merged:
            # 이전 섹션에 병합
            merged[-1]['content'] += '\n\n' + section['title'] + '\n' + section['content']
        else:
            merged.append(section)

    return merged


def split_long_sections(sections, max_length=MAX_SECTION_LENGTH):
    """긴 섹션을 분할"""
    result = []

    for section in sections:
        content = section['content']

        if len(content) <= max_length:
            result.append(section)
            continue

        # 단락 단위로 분할
        paragraphs = re.split(r'\n\s*\n', content)
        current_chunk = ""
        chunk_index = 0

        for para in paragraphs:
            if len(current_chunk) + len(para) > max_length and current_chunk:
                # 현재 청크 저장
                result.append({
                    'level': section['level'],
                    'title': section['title'] + (f" (계속 {chunk_index + 1})" if chunk_index > 0 else ""),
                    'id': section['id'] + (f"-{chunk_index + 1}" if chunk_index > 0 else ""),
                    'content': current_chunk.strip()
                })
                current_chunk = para
                chunk_index += 1
            else:
                current_chunk += '\n\n' + para if current_chunk else para

        # 마지막 청크
        if current_chunk:
            result.append({
                'level': section['level'],
                'title': section['title'] + (f" (계속 {chunk_index + 1})" if chunk_index > 0 else ""),
                'id': section['id'] + (f"-{chunk_index + 1}" if chunk_index > 0 else ""),
                'content': current_chunk.strip()
            })

    return result


# ===================================
# 인덱싱 함수
# ===================================

def index_by_section(html_file, url, base_path, url_to_path, inject_ids=False):
    """섹션 단위로 인덱싱"""
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except Exception as e:
        print(f"경고: {html_file} 읽기 실패 - {e}")
        return []

    # 문서 제목
    doc_title = extract_title_from_html(html_content) or html_file.stem

    # 섹션 파싱 (ID 주입 옵션 포함)
    sections, modified_html = parse_sections(html_content, inject_ids=inject_ids)

    # HTML이 수정되었으면 파일 저장
    if inject_ids and modified_html != html_content:
        try:
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(modified_html)
            print(f"  → ID 주입됨: {html_file.name}")
        except Exception as e:
            print(f"  경고: {html_file} 저장 실패 - {e}")

    if not sections:
        # 섹션이 없으면 페이지 전체를 하나의 섹션으로
        content = html_to_searchable_text(html_content)
        if len(content) > MAX_SECTION_LENGTH:
            content = content[:MAX_SECTION_LENGTH]

        return [{
            'title': doc_title,
            'url': url,
            'path': url_to_path.get(url, base_path),
            'content': content,
            'section_id': None,
            'heading_level': 1
        }]

    # 짧은 섹션 병합, 긴 섹션 분할
    sections = merge_short_sections(sections)
    sections = split_long_sections(sections)

    # 인덱스 항목 생성
    index_items = []
    for section in sections:
        path = url_to_path.get(url, base_path)
        full_path = f"{path} > {section['title']}" if path else section['title']

        index_items.append({
            'title': section['title'],
            'url': url,
            'path': full_path,
            'content': section['content'],
            'section_id': section['id'],
            'heading_level': section['level']
        })

    return index_items


def index_by_page(html_file, url, base_path, url_to_path):
    """페이지 단위로 인덱싱 (기존 방식)"""
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except Exception as e:
        print(f"경고: {html_file} 읽기 실패 - {e}")
        return []

    title = extract_title_from_html(html_content) or html_file.stem
    content = html_to_searchable_text(html_content)

    if len(content) > 5000:
        content = content[:5000]

    return [{
        'title': title,
        'url': url,
        'path': url_to_path.get(url, base_path),
        'content': content,
        'section_id': None,
        'heading_level': None
    }]


def scan_html_files(mode='section', inject_ids=False):
    """contents/ 디렉터리의 모든 HTML 파일을 스캔하여 검색 인덱스 생성"""
    if not CONTENTS_DIR.exists():
        print(f"오류: {CONTENTS_DIR} 디렉터리를 찾을 수 없습니다.")
        return []

    url_to_path = load_menu_structure()
    index_data = []

    for html_file in CONTENTS_DIR.rglob('*.html'):
        relative_path = html_file.relative_to(PROJECT_ROOT)
        url = str(relative_path).replace('\\', '/')
        base_path = url

        if mode == 'section':
            items = index_by_section(html_file, url, base_path, url_to_path, inject_ids=inject_ids)
        else:
            items = index_by_page(html_file, url, base_path, url_to_path)

        index_data.extend(items)

        if mode == 'section':
            print(f"인덱싱: {url} - {len(items)}개 섹션")
        else:
            print(f"인덱싱: {url}")

    return index_data


def save_search_index(index_data):
    """검색 인덱스를 JSON 파일로 저장"""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)

    print(f"\n검색 인덱스 생성 완료: {OUTPUT_FILE}")
    print(f"총 {len(index_data)}개의 항목이 인덱싱되었습니다.")


# ===================================
# 메인
# ===================================

def main():
    global MAX_SECTION_LENGTH

    parser = argparse.ArgumentParser(description='KF-21 웹북 검색 인덱스 생성')
    parser.add_argument('--page', action='store_true', help='페이지 단위 인덱싱 (기본: 섹션 단위)')
    parser.add_argument('--max-length', type=int, default=3200,
                        help='섹션 최대 길이 (기본: 3200)')
    parser.add_argument('--inject-ids', action='store_true',
                        help='HTML 파일에 섹션 ID 직접 주입 (권장)')
    args = parser.parse_args()

    MAX_SECTION_LENGTH = args.max_length

    mode = 'page' if args.page else 'section'

    print("=" * 60)
    print("KF-21 웹북 - 검색 인덱스 생성")
    print(f"모드: {'페이지 단위' if mode == 'page' else '섹션 단위'}")
    if mode == 'section':
        print(f"섹션 최대 길이: {MAX_SECTION_LENGTH}자")
        if args.inject_ids:
            print("ID 주입: 활성화 (HTML 파일이 수정됩니다)")
    print("=" * 60)
    print()

    index_data = scan_html_files(mode, inject_ids=args.inject_ids)

    if not index_data:
        print("\n경고: 인덱싱할 HTML 파일이 없습니다.")
        return

    save_search_index(index_data)
    print("\n완료!")


if __name__ == '__main__':
    main()
