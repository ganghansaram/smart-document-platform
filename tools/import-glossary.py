#!/usr/bin/env python3
"""
glossary.csv → glossary.json 변환 스크립트

사용법:
    python tools/import-glossary.py                          # 기본: data/glossary.csv → data/glossary.json
    python tools/import-glossary.py path/to/custom.csv       # 경로 지정
    python tools/import-glossary.py input.csv -o output.json  # 입출력 모두 지정

CSV 양식 (UTF-8 with BOM 권장):
    abbr,en,ko
    AAA,Anti-Aircraft Artillery,대공포
    ...

참고:
    - 첫 행은 헤더 (abbr, en, ko)
    - abbr 기준 알파벳 오름차순 정렬
    - 빈 행 및 abbr이 비어있는 행은 자동 스킵
    - 중복 항목 감지 시 경고 출력
"""

import csv
import json
import sys
import os
from pathlib import Path


def find_project_root():
    """프로젝트 루트 디렉토리 탐색 (index.html 기준)"""
    current = Path(__file__).resolve().parent
    for _ in range(5):
        if (current / 'index.html').exists():
            return current
        current = current.parent
    return Path(__file__).resolve().parent.parent


def import_glossary(csv_path, json_path):
    """CSV 파일을 읽어 glossary.json으로 변환"""

    # CSV 읽기 (BOM 자동 처리)
    terms = []
    seen = set()
    duplicates = 0

    with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)

        # 헤더 검증
        required = {'abbr', 'en'}
        if not required.issubset(set(reader.fieldnames or [])):
            print(f'오류: CSV 헤더에 필수 열이 없습니다: {required}')
            print(f'  현재 헤더: {reader.fieldnames}')
            sys.exit(1)

        for i, row in enumerate(reader, start=2):
            abbr = (row.get('abbr') or '').strip()
            en = (row.get('en') or '').strip()
            ko = (row.get('ko') or '').strip()

            # 빈 행 스킵
            if not abbr:
                continue

            # 중복 감지
            key = (abbr, en)
            if key in seen:
                duplicates += 1
                if duplicates <= 10:
                    print(f'  경고: 중복 항목 (행 {i}): {abbr} - {en}')
                continue
            seen.add(key)

            terms.append({
                'abbr': abbr,
                'en': en,
                'ko': ko
            })

    if duplicates > 10:
        print(f'  ... 외 {duplicates - 10}건의 중복 항목 스킵')

    # abbr 기준 정렬 (대소문자 무시, 같으면 en으로 2차 정렬)
    terms.sort(key=lambda x: (x['abbr'].upper(), x['en'].upper()))

    # JSON 쓰기
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(terms, f, ensure_ascii=False, indent=2)

    print(f'완료: {len(terms):,}개 용어 → {json_path}')
    if duplicates:
        print(f'  (중복 {duplicates}건 스킵)')


def main():
    root = find_project_root()
    default_csv = root / 'data' / 'glossary.csv'
    default_json = root / 'data' / 'glossary.json'

    # 인자 처리
    csv_path = default_csv
    json_path = default_json

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] in ('-o', '--output') and i + 1 < len(args):
            json_path = Path(args[i + 1])
            i += 2
        elif args[i] in ('-h', '--help'):
            print(__doc__)
            sys.exit(0)
        else:
            csv_path = Path(args[i])
            i += 1

    # 파일 존재 확인
    if not csv_path.exists():
        print(f'오류: CSV 파일을 찾을 수 없습니다: {csv_path}')
        sys.exit(1)

    print(f'입력: {csv_path}')
    print(f'출력: {json_path}')
    import_glossary(csv_path, json_path)


if __name__ == '__main__':
    main()
