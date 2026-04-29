"""Plan-50 Phase 0 — 유사도 v3 점수 공식 골든셋 단위 테스트.

backend/services/similarity_engine.py 의 _compute_summary() 가 Plan-45 v3
공식 (가중치 없음) 을 따르는지 검증한다.

실행: python tests/sim_score_v3_unit_test.py
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

# Windows 콘솔 cp949 회피 — 골든셋 출력에 한글·em-dash 사용
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from services.similarity_engine import (  # noqa: E402
    _compute_summary,
    TYPE_IDENTICAL,
    TYPE_NEAR_COPY,
    TYPE_PARAPHRASE,
    TYPE_TRANSLATION,
    TYPE_LOW_SIM,
    TYPE_BOILERPLATE,
)


def _make_match(idx: int, mtype: str, sim: float = 0.85, end: int | None = None) -> dict:
    """단순 매칭 객체 생성 (target_idx, type, similarity 만 유의미)."""
    m = {
        "target_idx": idx,
        "ref_idx": idx,
        "target_text": f"sentence {idx}",
        "ref_text": f"ref sentence {idx}",
        "type": mtype,
        "similarity": sim,
        "scores": {"fingerprint": 0.5, "semantic": 0.8},
    }
    if end is not None:
        m["target_idx_end"] = end
        m["ref_idx_end"] = end
    return m


def _make_target_sents(n: int) -> list[str]:
    return [f"sentence {i}" for i in range(n)]


CASES = []


# ─────────────────────────────────────────────────────────────
# Case A — 의역만 N건 (Plan-50 Phase 1 검증 핵심)
# v3: scored = N, total = N, score = N/N × 100 = 100%
# v2 옛 공식: scored = N × 0.5, score = 50%
# ─────────────────────────────────────────────────────────────
def case_paraphrase_only_should_be_100():
    matches = [_make_match(i, TYPE_PARAPHRASE) for i in range(10)]
    target_sents = _make_target_sents(10)
    summary = _compute_summary(matches, [], target_sents)
    score = summary["similarity_score"]
    assert score == 100.0, f"Case A 실패: 의역 10/10 인데 점수={score} (v3 기대=100.0)"


CASES.append(("A. 의역 10/10 → 100%", case_paraphrase_only_should_be_100))


# ─────────────────────────────────────────────────────────────
# Case B — 동일·거의 동일·의역 혼합
# 동일 2 + 거의 동일 1 + 의역 3 = 6, total 10
# v3: 6/10 = 60%
# v2: (3 + 3*0.5) / 10 = 45%
# ─────────────────────────────────────────────────────────────
def case_mixed_60pct():
    matches = [
        _make_match(0, TYPE_IDENTICAL),
        _make_match(1, TYPE_IDENTICAL),
        _make_match(2, TYPE_NEAR_COPY),
        _make_match(3, TYPE_PARAPHRASE),
        _make_match(4, TYPE_PARAPHRASE),
        _make_match(5, TYPE_PARAPHRASE),
    ]
    target_sents = _make_target_sents(10)
    summary = _compute_summary(matches, [], target_sents)
    score = summary["similarity_score"]
    assert score == 60.0, f"Case B 실패: 혼합 6/10 인데 점수={score} (v3 기대=60.0)"


CASES.append(("B. 동일2+거의동일1+의역3 → 60%", case_mixed_60pct))


# ─────────────────────────────────────────────────────────────
# Case C — 약한 유사 (low_sim) 는 분자 미반영
# 의역 4 + 약한 유사 4 = 8 매칭, total 10
# v3: scored = 4 (의역만), score = 4/10 = 40%
# 약한 유사는 분자에서 빠지지만 분모는 영향 없음
# ─────────────────────────────────────────────────────────────
def case_low_sim_excluded_from_numerator():
    matches = [_make_match(i, TYPE_PARAPHRASE) for i in range(4)]
    matches += [_make_match(i, TYPE_LOW_SIM) for i in range(4, 8)]
    target_sents = _make_target_sents(10)
    summary = _compute_summary(matches, [], target_sents)
    score = summary["similarity_score"]
    assert score == 40.0, f"Case C 실패: 의역4+약한4/10 인데 점수={score} (v3 기대=40.0)"


CASES.append(("C. 약한 유사 분자 미반영 → 40%", case_low_sim_excluded_from_numerator))


# ─────────────────────────────────────────────────────────────
# Case D — 동일만 N건 (가중치 무관, v3·v2 동일 결과)
# v3 = v2 = 5/10 = 50%
# ─────────────────────────────────────────────────────────────
def case_identical_only_50pct():
    matches = [_make_match(i, TYPE_IDENTICAL) for i in range(5)]
    target_sents = _make_target_sents(10)
    summary = _compute_summary(matches, [], target_sents)
    score = summary["similarity_score"]
    assert score == 50.0, f"Case D 실패: 동일 5/10 인데 점수={score} (v3 기대=50.0)"


CASES.append(("D. 동일만 5/10 → 50% (가중치 무관)", case_identical_only_50pct))


# ─────────────────────────────────────────────────────────────
# Case E — verdict_band 가 v3 점수 기반인지 (Phase 1 자동 파급 검증)
# Case A 100% → red, Case B 60% → orange, Case C 40% → yellow, Case D 50% → orange
# v2 였다면 Case A 50% → orange, Case B 45% → yellow 등으로 한 단계씩 아래
# ─────────────────────────────────────────────────────────────
def case_verdict_band_v3():
    # Case A 100% → red
    summary_a = _compute_summary(
        [_make_match(i, TYPE_PARAPHRASE) for i in range(10)],
        [], _make_target_sents(10),
    )
    assert summary_a["verdict"] == "red", f"Case E-A 실패: 100% verdict={summary_a['verdict']} (기대=red)"

    # Case C 40% → yellow
    matches_c = [_make_match(i, TYPE_PARAPHRASE) for i in range(4)]
    matches_c += [_make_match(i, TYPE_LOW_SIM) for i in range(4, 8)]
    summary_c = _compute_summary(matches_c, [], _make_target_sents(10))
    assert summary_c["verdict"] == "yellow", f"Case E-C 실패: 40% verdict={summary_c['verdict']} (기대=yellow)"


CASES.append(("E. verdict_band v3 정합 (100→red, 40→yellow)", case_verdict_band_v3))


def main() -> int:
    print("Plan-50 Phase 0 — sim_score_v3 골든셋 검증\n")
    fail = 0
    for name, fn in CASES:
        try:
            fn()
            print(f"  PASS  {name}")
        except AssertionError as e:
            print(f"  FAIL  {name}\n        {e}")
            fail += 1
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR {name}\n        {type(e).__name__}: {e}")
            fail += 1

    print()
    if fail == 0:
        print("=" * 50)
        print(f"PASS: 골든셋 {len(CASES)}건 모두 v3 공식 일치")
        print("=" * 50)
        return 0
    print("=" * 50)
    print(f"FAIL: {fail}/{len(CASES)} 건 실패 — 백엔드 공식이 v3 와 어긋남")
    print("=" * 50)
    return 1


if __name__ == "__main__":
    sys.exit(main())
