# -*- coding: utf-8 -*-
"""
Plan-37 Phase 3 — fixture 4종을 컨테이너 LibreOffice 경로로 변환.

목적:
  - fixture (f) swa_kor: Linux Docker 에서 한글 heading 번호 보존 확인
  - fixture (a)(b)(c): Word COM (호스트 골든) vs LibreOffice (컨테이너) 본문 diff 측정
"""
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, "/app/tools/converter")

from preprocess import preprocess  # noqa: E402
from converter import DocxConverter  # noqa: E402


FIXTURES = [
    ("sample_small", "sample_20260317.docx"),
    ("mypaper",      "MyPaper/MyPaper_20251109_V2.8_Claude.docx"),
    ("swa_pms",      "SWA_PMS/SWA_PMS.docx"),
    ("swa_kor",      "SWA_Sample_KOR/SWA_Sample_KOR.docx"),
]

SAMPLES = Path("/app/contents/samples")
GOLDEN = Path("/app/tools/converter/tests/golden")
OUT = Path("/tmp/lo_out")
OUT.mkdir(exist_ok=True)


def _strip(html: str) -> str:
    """주석·이미지 경로 정규화 후 순수 본문만 남김."""
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
    html = re.sub(r'src="[^"]*_images/', 'src="_IMG_/', html)
    html = re.sub(r'\s+', ' ', html).strip()
    return html


def _heading_stats(html: str):
    """h1~h6 개수 + 번호 prefix 비율."""
    headings = re.findall(r'<(h[1-6])[^>]*>(.*?)</\1>', html, re.DOTALL)
    levels = {f'h{i}': 0 for i in range(1, 7)}
    numbered = 0
    for tag, content in headings:
        levels[tag] += 1
        text = re.sub(r'<[^>]+>', '', content).strip()
        if re.match(r'^[\d\.]+[\.\s]', text):
            numbered += 1
    return levels, len(headings), numbered


def main():
    results = []
    for fid, rel_path in FIXTURES:
        src = SAMPLES / rel_path
        golden_html_path = GOLDEN / f"{fid}.html"
        out_html = OUT / f"{fid}.html"

        print(f"\n=== {fid} ({rel_path}) ===")
        if not src.exists():
            print(f"  원본 없음: {src}")
            continue

        # LibreOffice 경로로 전처리 + 변환
        r = preprocess(str(src), policy='libreoffice')
        if not r.ok:
            print(f"  전처리 실패: {r.error}")
            continue

        conv = DocxConverter(config_path="/app/tools/converter/config.json")
        result = conv.convert(r.path, str(out_html), provenance_adapter=r.adapter)
        if not result.success:
            print(f"  변환 실패: {result.error_message}")
            continue

        lo_html = out_html.read_text(encoding="utf-8")
        lo_stats, lo_total, lo_numbered = _heading_stats(lo_html)

        # 임시 파일 정리
        try:
            Path(r.path).unlink(missing_ok=True)
        except OSError:
            pass

        # 골든 (Word COM 경로) 과 비교
        if golden_html_path.exists():
            golden_html = golden_html_path.read_text(encoding="utf-8")
            g_stats, g_total, g_numbered = _heading_stats(golden_html)

            lo_strip = _strip(lo_html)
            g_strip = _strip(golden_html)
            lo_hash = hashlib.sha256(lo_strip.encode()).hexdigest()[:12]
            g_hash = hashlib.sha256(g_strip.encode()).hexdigest()[:12]
            bytes_eq = lo_strip == g_strip
            print(f"  골든(Word COM):  headings={g_total} numbered={g_numbered} dist={g_stats}")
            print(f"  LO 컨테이너:     headings={lo_total} numbered={lo_numbered} dist={lo_stats}")
            print(f"  정규화 본문 동등: {bytes_eq}  (golden hash={g_hash}, lo hash={lo_hash})")
            print(f"  크기: golden={len(g_strip)}  lo={len(lo_strip)}  diff={len(lo_strip)-len(g_strip)}")

            results.append((fid, bytes_eq, lo_total, lo_numbered, g_total, g_numbered))
        else:
            print(f"  [SKIP] 골든 HTML 없음: {golden_html_path}")
            print(f"  LO:  headings={lo_total} numbered={lo_numbered}")

    # 요약
    print("\n" + "=" * 72)
    print(f"{'fixture':15s}  {'eq?':4s}  {'LO hdg':>7s}  {'LO #?':>6s}  {'Golden hdg':>10s}  {'Golden #?':>9s}")
    for fid, eq, lo_t, lo_n, g_t, g_n in results:
        print(f"  {fid:15s} {'OK' if eq else 'DIFF':4s}  {lo_t:>7}  {lo_n:>6}  {g_t:>10}  {g_n:>9}")
    print("=" * 72)


if __name__ == "__main__":
    main()
