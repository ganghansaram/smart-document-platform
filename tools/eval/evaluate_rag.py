#!/usr/bin/env python3
"""
RAG 검색 품질 평가 스크립트
- Recall@K: 기대 문서가 상위 K개 결과에 포함되는 비율
- MRR (Mean Reciprocal Rank): 첫 번째 관련 결과의 역순위 평균
- 검색 모드별 비교: keyword / vector / hybrid
- 카테고리별 분석: factual, semantic, cross-lingual, negative
"""
import json
import sys
import time
from pathlib import Path
from collections import defaultdict

import requests

# 설정
BACKEND_URL = "http://localhost:8000"
TOP_K = 5
SEARCH_MODES = ["keyword", "vector", "hybrid"]

SCRIPT_DIR = Path(__file__).parent
TEST_DATA_PATH = SCRIPT_DIR / "test_dataset.json"


def load_test_data():
    with open(TEST_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def search(query: str, search_type: str, top_k: int = TOP_K) -> dict:
    """백엔드 검색 API 호출"""
    r = requests.post(
        f"{BACKEND_URL}/api/search",
        json={"query": query, "top_k": top_k, "search_type": search_type},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def evaluate_retrieval(test_case: dict, results: list) -> dict:
    """단일 테스트 케이스의 검색 결과 평가"""
    expected_sids = set(test_case.get("expected_sections", []))
    expected_urls = set(test_case.get("expected_urls", []))
    is_negative = test_case["category"] == "negative"

    # negative 케이스: 결과가 없어야 정답
    if is_negative:
        return {
            "hit": len(results) == 0,
            "reciprocal_rank": 1.0 if len(results) == 0 else 0.0,
            "first_rank": 0 if len(results) == 0 else -1,
        }

    if not expected_sids and not expected_urls:
        return {"hit": False, "reciprocal_rank": 0.0, "first_rank": -1}

    # 결과에서 기대 문서 찾기
    first_rank = -1
    for i, r in enumerate(results):
        sid = r.get("section_id", "") or ""
        url = r.get("path", "") or ""

        # section_id 부분 매칭 (suffix -1, -2 등 허용)
        sid_match = any(sid.startswith(es) for es in expected_sids) if expected_sids else False
        url_match = url in expected_urls if expected_urls else False

        if sid_match or url_match:
            first_rank = i + 1  # 1-indexed
            break

    hit = first_rank > 0
    rr = 1.0 / first_rank if hit else 0.0

    return {"hit": hit, "reciprocal_rank": rr, "first_rank": first_rank}


def run_evaluation():
    test_data = load_test_data()
    print(f"테스트 케이스: {len(test_data)}개")
    print(f"검색 모드: {', '.join(SEARCH_MODES)}")
    print(f"Top-K: {TOP_K}")
    print("=" * 80)

    # 모드별 결과 수집
    mode_results = {mode: [] for mode in SEARCH_MODES}
    category_results = {mode: defaultdict(list) for mode in SEARCH_MODES}
    detail_rows = []

    for tc in test_data:
        tid = tc["id"]
        query = tc["query"]
        cat = tc["category"]
        row = {"id": tid, "query": query, "category": cat}

        for mode in SEARCH_MODES:
            try:
                resp = search(query, mode)
                results = resp.get("results", [])
                actual_mode = resp.get("search_type", mode)
                ev = evaluate_retrieval(tc, results)

                # 폴백 감지
                fell_back = actual_mode != mode
                ev["fell_back"] = fell_back
                ev["actual_mode"] = actual_mode
                ev["num_results"] = len(results)

                mode_results[mode].append(ev)
                category_results[mode][cat].append(ev)

                row[f"{mode}_hit"] = ev["hit"]
                row[f"{mode}_rr"] = ev["reciprocal_rank"]
                row[f"{mode}_rank"] = ev["first_rank"]
                row[f"{mode}_n"] = len(results)
                if fell_back:
                    row[f"{mode}_fb"] = actual_mode

            except Exception as e:
                print(f"  [ERROR] {tid} / {mode}: {e}")
                row[f"{mode}_hit"] = False
                row[f"{mode}_rr"] = 0.0

        detail_rows.append(row)

    # === 결과 출력 ===
    print()
    print("=" * 80)
    print("■ 종합 지표 (Overall Metrics)")
    print("=" * 80)
    print(f"{'Metric':<20} ", end="")
    for mode in SEARCH_MODES:
        print(f"{mode:>12}", end="")
    print()
    print("-" * 56)

    # Recall@K
    for mode in SEARCH_MODES:
        hits = [r["hit"] for r in mode_results[mode]]
        recall = sum(hits) / len(hits) if hits else 0
        mode_results[mode + "_recall"] = recall

    print(f"{'Recall@' + str(TOP_K):<20} ", end="")
    for mode in SEARCH_MODES:
        recall = mode_results[mode + "_recall"]
        print(f"{recall:>11.1%}", end="")
    print()

    # MRR
    print(f"{'MRR':<20} ", end="")
    for mode in SEARCH_MODES:
        rrs = [r["reciprocal_rank"] for r in mode_results[mode]]
        mrr = sum(rrs) / len(rrs) if rrs else 0
        print(f"{mrr:>11.3f}", end="")
    print()

    # Fallback count
    print(f"{'Fallback count':<20} ", end="")
    for mode in SEARCH_MODES:
        fb = sum(1 for r in mode_results[mode] if r.get("fell_back"))
        print(f"{fb:>12}", end="")
    print()

    # === 카테고리별 ===
    print()
    print("=" * 80)
    print("■ 카테고리별 Recall@K")
    print("=" * 80)
    all_cats = sorted(set(tc["category"] for tc in test_data))
    print(f"{'Category':<20} {'Count':>6}", end="")
    for mode in SEARCH_MODES:
        print(f"{mode:>12}", end="")
    print()
    print("-" * 62)

    for cat in all_cats:
        n = len(category_results[SEARCH_MODES[0]][cat])
        print(f"{cat:<20} {n:>6}", end="")
        for mode in SEARCH_MODES:
            hits = [r["hit"] for r in category_results[mode][cat]]
            recall = sum(hits) / len(hits) if hits else 0
            print(f"{recall:>11.1%}", end="")
        print()

    # === 개별 결과 ===
    print()
    print("=" * 80)
    print("■ 개별 테스트 결과")
    print("=" * 80)

    for row in detail_rows:
        status_parts = []
        for mode in SEARCH_MODES:
            hit = row.get(f"{mode}_hit", False)
            rank = row.get(f"{mode}_rank", -1)
            n = row.get(f"{mode}_n", 0)
            fb = row.get(f"{mode}_fb", "")

            if row["category"] == "negative":
                mark = "OK" if hit else f"LEAK({n})"
            else:
                mark = f"#{rank}" if hit else "MISS"
            if fb:
                mark += f"→{fb}"
            status_parts.append(f"{mode[0].upper()}:{mark}")

        status = "  ".join(status_parts)
        q_display = row["query"][:40]
        print(f"  {row['id']} [{row['category']:<15}] {q_display:<42} {status}")

    # === 요약 ===
    print()
    print("=" * 80)
    print("■ 요약")
    print("=" * 80)
    best_mode = max(SEARCH_MODES, key=lambda m: mode_results[m + "_recall"])
    best_recall = mode_results[best_mode + "_recall"]
    print(f"  최고 Recall@{TOP_K}: {best_mode} ({best_recall:.1%})")

    # 어떤 모드가 다른 모드보다 나은 케이스
    for i, mode_a in enumerate(SEARCH_MODES):
        for mode_b in SEARCH_MODES[i + 1:]:
            only_a = sum(1 for row in detail_rows if row.get(f"{mode_a}_hit") and not row.get(f"{mode_b}_hit"))
            only_b = sum(1 for row in detail_rows if row.get(f"{mode_b}_hit") and not row.get(f"{mode_a}_hit"))
            if only_a or only_b:
                print(f"  {mode_a}만 맞춘 케이스: {only_a}개, {mode_b}만 맞춘 케이스: {only_b}개")


if __name__ == "__main__":
    print("RAG 검색 품질 평가")
    print(f"Backend: {BACKEND_URL}")

    # 서버 연결 확인
    try:
        r = requests.get(f"{BACKEND_URL}/api/health", timeout=5)
        r.raise_for_status()
        print("서버 연결 OK")
    except Exception as e:
        print(f"서버 연결 실패: {e}")
        sys.exit(1)

    print()
    start = time.time()
    run_evaluation()
    elapsed = time.time() - start
    print(f"\n총 소요 시간: {elapsed:.1f}초")
