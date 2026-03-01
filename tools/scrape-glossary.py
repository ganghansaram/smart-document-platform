"""
KAI 항공용어집 수집 스크립트
https://www.koreaaero.com/KO/MediaCenter/AviationGlossary.aspx

수집한 데이터를 data/glossary.json으로 저장

응답 구조:
  { IsSucceed: true, Data: { totalrecords, pagenum, totalpage, rows: [...] } }
  rows[i]: { Abrv, Word, Mean, ... }
"""
import json
import sys
import time
import requests
from pathlib import Path

BASE_URL = "https://www.koreaaero.com"
PAGE_URL = f"{BASE_URL}/KO/MediaCenter/AviationGlossary.aspx"
ALPHA_API = f"{BASE_URL}/KO/Services/Front/FlightWord/GetFlightWordAlphabetList.aspx"

OUTPUT_PATH = Path(__file__).parent.parent / "data" / "glossary.json"
PAGE_SIZE = 100


def get_session():
    """세션 생성 (쿠키 획득)"""
    session = requests.Session()
    resp = session.get(PAGE_URL, timeout=30)
    resp.raise_for_status()
    session.headers.update({
        "X-Requested-With": "XMLHttpRequest",
        "Referer": PAGE_URL,
    })
    return session


def fetch_page(session, letter, page=1):
    """알파벳별 용어 목록 조회 (한 페이지)"""
    data = {
        "SearchText": letter,
        "PageNumber": str(page),
        "PageSize": str(PAGE_SIZE),
        "ModelType": "Models.Logical.CommonSearchModel",
        "SearchField": "",
    }
    resp = session.post(ALPHA_API, data=data, timeout=30)
    resp.raise_for_status()
    # 서버가 제어 문자를 포함할 수 있어 strict=False 사용
    import json as _json
    return _json.loads(resp.text, strict=False)


def scrape_all(session):
    """A-Z 전체 수집"""
    all_items = []
    letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    for letter in letters:
        page = 1
        letter_count = 0
        total_records = None

        while True:
            try:
                result = fetch_page(session, letter, page)
                if not result.get("IsSucceed"):
                    print(f"  {letter} page {page}: API error", file=sys.stderr)
                    break

                data = result.get("Data", {})
                rows = data.get("rows", [])
                if total_records is None:
                    total_records = int(data.get("totalrecords", 0))

                if not rows:
                    break

                for row in rows:
                    entry = {
                        "abbr": (row.get("Abrv") or "").strip(),
                        "en": (row.get("Word") or "").strip(),
                        "ko": (row.get("Mean") or "").strip(),
                    }
                    if entry["abbr"] or entry["en"]:
                        all_items.append(entry)
                        letter_count += 1

                # totalpage가 항상 "1" 반환 (서버 버그) → totalrecords로 계산
                if len(rows) < PAGE_SIZE:
                    break
                if total_records and letter_count >= total_records:
                    break

                page += 1
                time.sleep(0.2)

            except Exception as e:
                print(f"  {letter} page {page} error: {e}", file=sys.stderr)
                break

        print(f"  {letter}: {letter_count}/{total_records or '?'}")
        time.sleep(0.2)

    return all_items


def deduplicate(items):
    """중복 제거 (abbr + en 기준)"""
    seen = set()
    unique = []
    for item in items:
        key = (item["abbr"], item["en"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def main():
    print("=" * 60)
    print("KAI Aviation Glossary Scraper")
    print("=" * 60)

    session = get_session()
    print("Session ready\n")

    # API 구조 확인
    print("Testing API (letter=A, page=1)...")
    test = fetch_page(session, "A", 1)
    data = test.get("Data", {})
    rows = data.get("rows", [])
    print(f"  IsSucceed: {test.get('IsSucceed')}")
    print(f"  totalrecords: {data.get('totalrecords')}")
    print(f"  totalpage: {data.get('totalpage')}")
    print(f"  rows: {len(rows)}")
    if rows:
        print(f"  sample: {rows[0]}")

    print("\nScraping A-Z...")
    all_items = scrape_all(session)

    if not all_items:
        print("\nNo items collected.")
        return

    unique_items = deduplicate(all_items)
    unique_items.sort(key=lambda x: (x["abbr"].lower(), x["en"].lower()))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(unique_items, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"Done: {len(unique_items)} unique terms")
    print(f"Saved: {OUTPUT_PATH}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
