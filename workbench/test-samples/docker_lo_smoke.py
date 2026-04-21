# -*- coding: utf-8 -*-
"""
Plan-37 Phase 3 — Docker 컨테이너 내부 LibreOffice 스모크 테스트

컨테이너 기동 후 `docker exec` 로 이 스크립트를 실행해서:
  1. soffice 실행파일 탐지
  2. python3-uno import 가능 여부
  3. LibreOfficeAdapter.is_available() True 확인
  4. 실제 LO 경로로 전처리 → converter 변환 → provenance adapter=libreoffice 확인
"""
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

SAMPLE = Path("/app/contents/samples/sample_20260317.docx")


def check_soffice() -> bool:
    paths = []
    for name in ("soffice", "libreoffice"):
        p = shutil.which(name)
        if p:
            paths.append(p)
    for c in ("/usr/bin/soffice", "/opt/libreoffice/program/soffice"):
        if Path(c).is_file():
            paths.append(c)
    print(f"[1] soffice 탐지: {paths or 'NOT FOUND'}")
    if not paths:
        return False
    try:
        r = subprocess.run([paths[0], "--version"], capture_output=True,
                           text=True, timeout=10)
        print(f"    version: {r.stdout.strip() or r.stderr.strip()}")
    except Exception as e:
        print(f"    version 조회 실패: {e}")
    return True


def check_uno() -> bool:
    """시스템 python3 (`/usr/bin/python3`) 에서 uno import 가능한지 subprocess 로 확인.

    Debian 패키지 `libreoffice-script-provider-python` 은 `/usr/lib/python3/dist-packages/uno.py`
    를 시스템 python3 에만 설치한다. 컨테이너 메인 Python (python:3.11-slim) 에선
    import 안 되지만, lo_macro.py 는 subprocess 로 /usr/bin/python3 을 호출하므로 OK.
    """
    try:
        r = subprocess.run(
            ["/usr/bin/python3", "-c", "import uno; print(uno.__file__)"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0:
            print(f"[2] uno OK (/usr/bin/python3): {r.stdout.strip()}")
            return True
        print(f"[2] /usr/bin/python3 uno import 실패: {r.stderr.strip()}")
        return False
    except Exception as e:
        print(f"[2] /usr/bin/python3 실행 실패: {e}")
        return False


def check_adapter() -> bool:
    sys.path.insert(0, "/app/tools/converter")
    try:
        from preprocess.libreoffice import LibreOfficeAdapter
        a = LibreOfficeAdapter()
        avail = a.is_available()
        print(f"[3] LibreOfficeAdapter.is_available(): {avail}")
        return avail
    except Exception as e:
        print(f"[3] LibreOfficeAdapter 로드 실패: {e}")
        traceback.print_exc()
        return False


def run_conversion() -> bool:
    if not SAMPLE.exists():
        print(f"[4] 샘플 없음: {SAMPLE}")
        return False

    sys.path.insert(0, "/app/tools/converter")
    from preprocess import preprocess
    from converter import DocxConverter

    print(f"[4] 전처리 시도 (policy='libreoffice') — {SAMPLE.name}")
    r = preprocess(str(SAMPLE), policy='libreoffice')
    print(f"    adapter={r.adapter} ok={r.ok}")
    print(f"    path={r.path}")
    if r.tried:
        print(f"    tried:")
        for name, reason in r.tried:
            print(f"      - {name}: {reason}")

    if not r.ok:
        print(f"    ERROR: {r.error}")
        return False

    # 변환
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out.html"
        conv = DocxConverter(config_path="/app/tools/converter/config.json")
        result = conv.convert(r.path, str(out), provenance_adapter=r.adapter)
        if not result.success:
            print(f"[5] 변환 실패: {result.error_message}")
            return False
        html = out.read_text(encoding="utf-8")
        prov = html.split("\n", 1)[0]
        print(f"[5] 변환 성공 ({len(html)} bytes)")
        print(f"    provenance: {prov}")
        # heading 번호 prefix 비율
        import re
        headings = re.findall(r'<h[1-6][^>]*>(.*?)</h[1-6]>', html)
        numbered = [h for h in headings
                    if re.match(r'^[\d\.]+[\.\s]', re.sub(r'<[^>]+>', '', h))]
        print(f"    heading 번호 prefix: {len(numbered)}/{len(headings)}")

    # 임시 파일 정리
    try:
        Path(r.path).unlink(missing_ok=True)
    except Exception:
        pass
    return True


def main() -> int:
    ok1 = check_soffice()
    ok2 = check_uno()
    ok3 = check_adapter()
    ok4 = run_conversion() if ok3 else False

    print()
    print("=" * 50)
    print(f"  soffice        : {'OK' if ok1 else 'FAIL'}")
    print(f"  python-uno     : {'OK' if ok2 else 'FAIL'}")
    print(f"  adapter        : {'OK' if ok3 else 'FAIL'}")
    print(f"  conversion     : {'OK' if ok4 else 'FAIL'}")
    print("=" * 50)
    return 0 if (ok1 and ok2 and ok3 and ok4) else 1


if __name__ == "__main__":
    sys.exit(main())
