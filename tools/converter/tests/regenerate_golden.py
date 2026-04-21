# -*- coding: utf-8 -*-
"""
Plan-37 Phase 0 — 골든 HTML 재생성 스크립트

목적:
    fixture DOCX 를 현 Explorer converter 경로로 변환하여
    `golden/{id}.html` 에 저장. 이후 회귀 테스트의 비교 기준.

사용법:
    cd tools/converter/tests
    python regenerate_golden.py [--with-word-com]

옵션:
    --with-word-com    Word COM 전처리 활성화 (Windows + Word 설치 시)
                       기본: 전처리 없이 converter 직행 (현 Linux Docker 기본 동작 반영)

주의:
    - 이 스크립트를 돌릴 때 converter 동작을 "현재" 상태로 고정한다.
    - Phase 1~4 변경 후엔 **테스트 실패가 의도된 것인지** 판단 후
      필요 시 명시적으로 재실행 (설명과 함께 커밋).
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

# _paths 의 FIXTURE_CATALOG, SAMPLES_DIR, GOLDEN_DIR, CONVERTER_DIR 재사용
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import FIXTURE_CATALOG, SAMPLES_DIR, GOLDEN_DIR, CONVERTER_DIR  # noqa: E402

# converter 모듈 path
if str(CONVERTER_DIR) not in sys.path:
    sys.path.insert(0, str(CONVERTER_DIR))


def regenerate(use_word_com: bool = False) -> int:
    """모든 fixture 에 대해 골든 HTML 을 재생성. 성공한 fixture 수 반환."""
    from converter import DocxConverter

    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    success_count = 0

    for fid, rel_path, desc in FIXTURE_CATALOG:
        docx_path = SAMPLES_DIR / rel_path
        if not docx_path.exists():
            print(f"[SKIP] {fid}: 원본 DOCX 없음 — {docx_path}")
            continue

        print(f"[{fid}] {desc}")
        print(f"    원본: {docx_path}")

        output_html = GOLDEN_DIR / f"{fid}.html"
        preprocessed = None
        try:
            if use_word_com:
                try:
                    from word_preprocessor import preprocess_docx
                    preprocessed = preprocess_docx(str(docx_path))
                    print(f"    전처리: Word COM → {preprocessed}")
                except Exception as e:
                    print(f"    [WARN] Word COM 실패, 원본 사용: {e}")

            convert_input = preprocessed or str(docx_path)
            conv = DocxConverter(config_path=str(CONVERTER_DIR / "config.json"))
            result = conv.convert(convert_input, str(output_html))

            if result.success:
                stats = result.stats or {}
                print(f"    → {output_html}")
                print(f"    stats: headings={sum(stats.get('headings', {}).values()) if isinstance(stats.get('headings'), dict) else stats.get('headings', 0)}, "
                      f"tables={stats.get('tables', 0)}, images={stats.get('images', 0)}")
                success_count += 1
            else:
                print(f"    [FAIL] {result.error_message}")

        except Exception as e:
            print(f"    [ERROR] {type(e).__name__}: {e}")
        finally:
            if preprocessed and preprocessed != str(docx_path):
                try:
                    Path(preprocessed).unlink(missing_ok=True)
                except OSError:
                    pass
        print()

    return success_count


def main():
    parser = argparse.ArgumentParser(description="Plan-37 Phase 0 골든 HTML 재생성")
    parser.add_argument('--with-word-com', action='store_true',
                        help="Word COM 전처리 활성화 (Windows + Word 필요)")
    args = parser.parse_args()

    print(f"Samples dir: {SAMPLES_DIR}")
    print(f"Golden dir:  {GOLDEN_DIR}")
    print(f"Word COM:    {'ON' if args.with_word_com else 'OFF (converter 단독)'}")
    print("=" * 72)

    count = regenerate(use_word_com=args.with_word_com)

    print("=" * 72)
    print(f"총 {count}/{len(FIXTURE_CATALOG)} fixture 골든 재생성 완료.")
    return 0 if count == len(FIXTURE_CATALOG) else 1


if __name__ == "__main__":
    sys.exit(main())
