#!/usr/bin/env python3
"""
유사도 검사 골드셋 평가 도구 (Plan-38 Phase 0)

골드셋 페어를 backend/services/similarity_engine.run_similarity()로 검사하고
다음 지표를 측정한다:

  - 점수 대역 적중 (expected_score_range 안에 들어왔는가)
  - 라벨 분포 적중 (각 라벨 비율이 expected_label_distribution 범위에 들어왔는가)
  - 최소 매칭 수 (min_match_count 이상인가)
  - 보일러플레이트 비율 (expected_boilerplate_ratio_min 이상인가)

실행:
  cd backend && python ../tools/eval/similarity_eval.py
  또는
  PYTHONPATH=backend python tools/eval/similarity_eval.py [--pair pair_01] [--json out.json]

종료 코드:
  0: 모든 페어가 모든 검사를 통과
  1: 일부 페어가 검사 실패 (캘리브레이션 필요)
  2: 실행 오류 (모델 로드 실패 등)
"""
import argparse
import io
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

# Windows 콘솔 cp949 → UTF-8 강제 (체크마크 등 출력 위함)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = ROOT / "backend"
GOLDSET_DIR = ROOT / "data" / "similarity-goldset"

# backend 모듈 import 가능하도록
sys.path.insert(0, str(BACKEND_DIR))


def _load_pairs(filter_id: str = None) -> list:
    pairs = []
    for fp in sorted((GOLDSET_DIR / "pairs").glob("*.json")):
        pair = json.loads(fp.read_text(encoding="utf-8"))
        if filter_id and pair["id"] != filter_id and not pair["id"].startswith(filter_id):
            continue
        pairs.append(pair)
    return pairs


def _load_text(rel_path: str) -> str:
    return (GOLDSET_DIR / rel_path).read_text(encoding="utf-8")


def _evaluate_pair(pair: dict, run_similarity) -> dict:
    """단일 페어 평가."""
    target = _load_text(pair["target_file"])
    ref = _load_text(pair["ref_file"])

    t0 = time.time()
    try:
        result = run_similarity(
            target_text=target,
            reference_text=ref,
            target_markdown=target,
            reference_markdown=ref,
        )
    except Exception as e:
        return {
            "id": pair["id"],
            "passed": False,
            "error": f"{type(e).__name__}: {e}",
            "elapsed_ms": int((time.time() - t0) * 1000),
        }

    elapsed = int((time.time() - t0) * 1000)
    summary = result.get("summary", {})
    matches = result.get("matches", [])
    breakdown = summary.get("breakdown", {})
    tiers = summary.get("tiers", {})
    actual_score = tiers.get("adjusted") if tiers else summary.get("similarity_score", 0)

    # ── 1. 점수 대역 검사 ──
    band_lo, band_hi = pair["expected_score_range"]
    score_pass = band_lo <= actual_score <= band_hi

    # ── 2. 라벨 분포 검사 (substantive matches 대비) ──
    total_matches = sum(
        breakdown.get(k, {}).get("count", 0)
        for k in ("identical", "near_copy", "paraphrase", "translation", "low_sim")
    ) or 1  # 0 div 방지

    label_results = {}
    for label, (lo, hi) in pair["expected_label_distribution"].items():
        actual_count = breakdown.get(label, {}).get("count", 0)
        actual_ratio = actual_count / total_matches if total_matches else 0
        in_range = lo <= actual_ratio <= hi
        label_results[label] = {
            "actual_count": actual_count,
            "actual_ratio": round(actual_ratio, 3),
            "expected_range": [lo, hi],
            "passed": in_range,
        }

    # ── 3. 최소 매칭 수 (커버된 문장 수 기준) ──
    # _merge_adjacent로 인접 매칭이 병합되므로, 단순 len(matches) 대신
    # 커버된 문장 수를 계산한다 (target_idx_end - target_idx + 1 합산).
    actual_match_count = len(matches)
    covered_sentences = sum(
        m.get("target_idx_end", m.get("target_idx", 0)) - m.get("target_idx", 0) + 1
        for m in matches
    )
    min_count = pair.get("min_match_count", 0)
    count_pass = covered_sentences >= min_count

    # ── 4. 최대 substantive 매칭 (no_plag용) ──
    max_subst_pass = True
    if "max_substantive_matches" in pair:
        substantive = breakdown.get("identical", {}).get("count", 0) + \
                      breakdown.get("near_copy", {}).get("count", 0)
        max_subst_pass = substantive <= pair["max_substantive_matches"]

    # ── 5. 보일러플레이트 비율 ──
    bp_pass = True
    bp_ratio = breakdown.get("boilerplate", {}).get("count", 0) / max(actual_match_count + breakdown.get("boilerplate", {}).get("count", 0), 1)
    if "expected_boilerplate_ratio_min" in pair:
        bp_pass = bp_ratio >= pair["expected_boilerplate_ratio_min"]

    label_pass = all(r["passed"] for r in label_results.values())
    overall = score_pass and label_pass and count_pass and max_subst_pass and bp_pass

    return {
        "id": pair["id"],
        "obfuscation": pair["obfuscation"],
        "passed": overall,
        "elapsed_ms": elapsed,
        "actual_score": actual_score,
        "expected_score_range": [band_lo, band_hi],
        "score_pass": score_pass,
        "actual_match_count": actual_match_count,
        "covered_sentences": covered_sentences,
        "min_match_count": min_count,
        "count_pass": count_pass,
        "label_results": label_results,
        "label_pass": label_pass,
        "max_substantive_pass": max_subst_pass,
        "boilerplate_ratio": round(bp_ratio, 3),
        "boilerplate_pass": bp_pass,
        "breakdown": {k: breakdown.get(k, {}).get("count", 0)
                      for k in ("identical", "near_copy", "paraphrase",
                                "translation", "low_sim", "boilerplate")},
        "tiers": tiers,
    }


def _print_pair_row(r: dict):
    """콘솔 출력 — 한 줄 요약."""
    status = "[PASS]" if r["passed"] else "[FAIL]"
    if r.get("error"):
        print(f"  {status} {r['id']:32s} ERROR: {r['error'][:80]}")
        return

    score = r["actual_score"]
    lo, hi = r["expected_score_range"]
    score_marker = "✓" if r["score_pass"] else "✗"
    print(f"  {status} {r['id']:32s} score={score:5.1f}% [{lo}-{hi}]{score_marker} "
          f"sents={r['covered_sentences']:3d}(>={r['min_match_count']:2d})"
          f"{'✓' if r['count_pass'] else '✗'} "
          f"labels={'✓' if r['label_pass'] else '✗'} "
          f"bp={'✓' if r['boilerplate_pass'] else '✗'} "
          f"({r['elapsed_ms']}ms)")

    if not r["passed"]:
        # 실패한 라벨 상세 출력
        for label, lr in r["label_results"].items():
            if not lr["passed"]:
                print(f"        ↳ {label}: ratio={lr['actual_ratio']} "
                      f"(expected {lr['expected_range']})")


def _print_summary(results: list):
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    errors = sum(1 for r in results if r.get("error"))
    score_band_acc = sum(1 for r in results if r.get("score_pass")) / max(total, 1)

    print(f"\n{'='*80}")
    print(f"  Summary: {passed}/{total} pairs passed (errors: {errors})")
    print(f"  Score band accuracy: {score_band_acc:.1%}")
    print(f"{'='*80}")

    # 변형 유형별 집계
    by_obf = defaultdict(lambda: {"pass": 0, "total": 0})
    for r in results:
        if "obfuscation" in r:
            by_obf[r["obfuscation"]]["total"] += 1
            if r["passed"]:
                by_obf[r["obfuscation"]]["pass"] += 1

    print(f"\n  변형 유형별 통과율:")
    for obf, stats in sorted(by_obf.items()):
        pct = stats["pass"] / max(stats["total"], 1) * 100
        print(f"    {obf:20s} {stats['pass']}/{stats['total']} ({pct:.0f}%)")


def main():
    parser = argparse.ArgumentParser(description="유사도 골드셋 평가")
    parser.add_argument("--pair", help="특정 페어만 실행 (예: pair_01)")
    parser.add_argument("--json", help="상세 결과를 JSON으로 저장할 경로")
    parser.add_argument("--quiet", action="store_true", help="요약만 출력")
    args = parser.parse_args()

    print(f"Loading similarity engine from {BACKEND_DIR}...")
    try:
        from services.similarity_engine import run_similarity
    except ImportError as e:
        print(f"\nERROR: backend 모듈 로드 실패. PYTHONPATH=backend로 실행하세요.\n  {e}")
        return 2
    except Exception as e:
        print(f"\nERROR: 초기화 실패 ({type(e).__name__}: {e})")
        return 2

    pairs = _load_pairs(args.pair)
    if not pairs:
        print(f"No pairs matching filter '{args.pair}'")
        return 1

    print(f"\nEvaluating {len(pairs)} pair(s)...\n")
    results = []
    for pair in pairs:
        r = _evaluate_pair(pair, run_similarity)
        results.append(r)
        if not args.quiet:
            _print_pair_row(r)

    _print_summary(results)

    if args.json:
        out = Path(args.json)
        out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n  Detailed results saved to {out}")

    failed = sum(1 for r in results if not r["passed"])
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
