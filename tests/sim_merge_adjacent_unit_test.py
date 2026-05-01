"""Plan-51 Phase 1 — 매칭 병합 ri 단방향 검사 결함 회귀 테스트.

backend/services/similarity_engine.py 의 _merge_adjacent() 가
ti·ri 양방향 forward 진행 시에만 병합하는지 검증한다.

배경: 결함 발견 — ri 인접 검사가 단방향 (m.ri - prev.ri_end <= 2) 으로
prev.ri_end=50, m.ri=10 같은 역행 페어도 통과 → ri_end < ri_start 인
망가진 범위 생성 → 프론트 마킹 루프 0회 실행 → B 패널 미마킹.

핵심 케이스: D (ri 큰 역행), E (ri 1 역행) — 수정 전 FAIL, 수정 후 PASS.

실행: python tests/sim_merge_adjacent_unit_test.py
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

# Windows 콘솔 cp949 회피 — 출력에 한글·em-dash 사용
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from services.similarity_engine import (  # noqa: E402
    _merge_adjacent,
    TYPE_PARAPHRASE,
    TYPE_TRANSLATION,
    TYPE_IDENTICAL,
)


def _make_match(ti: int, ri: int, mtype: str = TYPE_PARAPHRASE, sim: float = 0.85) -> dict:
    """단순 매칭 객체 생성 (병합 검사에 필요한 필드만)."""
    return {
        "target_idx": ti,
        "ref_idx": ri,
        "target_text": f"t_sent_{ti}",
        "ref_text": f"r_sent_{ri}",
        "type": mtype,
        "similarity": sim,
        "scores": {"fingerprint": 0.5, "semantic": 0.8},
    }


CASES = []


# ─────────────────────────────────────────────────────────────
# Case A — Forward 정상 병합 (수정 전후 동일 동작, 회귀 방지)
# ti·ri 모두 +1 → gap=1 ≤ 2 → 병합
# ─────────────────────────────────────────────────────────────
def case_forward_normal_merge():
    matches = [_make_match(5, 10), _make_match(6, 11)]
    merged = _merge_adjacent(matches)
    assert len(merged) == 1, (
        f"Case A 실패: forward 인접 병합 안 됨 (merged={len(merged)}건)"
    )
    m = merged[0]
    assert m["target_idx"] == 5 and m.get("target_idx_end") == 6, (
        f"Case A 실패: ti 범위 [5..6] 아님 (ti={m['target_idx']}, ti_end={m.get('target_idx_end')})"
    )
    assert m["ref_idx"] == 10 and m.get("ref_idx_end") == 11, (
        f"Case A 실패: ri 범위 [10..11] 아님 (ri={m['ref_idx']}, ri_end={m.get('ref_idx_end')})"
    )


CASES.append(("A. Forward 정상 병합 [ti:5-6, ri:10-11]", case_forward_normal_merge))


# ─────────────────────────────────────────────────────────────
# Case B — Forward 경계 (gap=2) 병합 (회귀 방지)
# ti·ri 모두 +2 → gap=2 ≤ 2 → 병합
# ─────────────────────────────────────────────────────────────
def case_forward_boundary_merge():
    matches = [_make_match(5, 10), _make_match(7, 12)]
    merged = _merge_adjacent(matches)
    assert len(merged) == 1, (
        f"Case B 실패: gap=2 forward 병합 안 됨 (merged={len(merged)}건)"
    )
    m = merged[0]
    assert m.get("ref_idx_end") == 12, (
        f"Case B 실패: ri_end=12 아님 (ri_end={m.get('ref_idx_end')})"
    )


CASES.append(("B. Forward 경계 gap=2 병합 [ti:5-7, ri:10-12]", case_forward_boundary_merge))


# ─────────────────────────────────────────────────────────────
# Case C — Forward gap > 2 미병합 (회귀 방지)
# ti gap=3 → 조건 위배 → 미병합
# ─────────────────────────────────────────────────────────────
def case_forward_gap_too_large():
    matches = [_make_match(5, 10), _make_match(8, 13)]
    merged = _merge_adjacent(matches)
    assert len(merged) == 2, (
        f"Case C 실패: ti gap=3 인데 병합됨 (merged={len(merged)}건)"
    )


CASES.append(("C. Forward ti gap=3 미병합 → 2건 유지", case_forward_gap_too_large))


# ─────────────────────────────────────────────────────────────
# Case D ★ — ri 큰 역행 미병합 (수정 전 FAIL 예상)
# ti +1 (인접) but ri -40 (역행) → 수정 후 미병합
# 수정 전: ri 단방향 검사 (-40 ≤ 2) 통과로 잘못 병합 → ri_end < ri_start
# ─────────────────────────────────────────────────────────────
def case_ri_backward_large():
    matches = [_make_match(5, 50), _make_match(6, 10)]
    merged = _merge_adjacent(matches)
    assert len(merged) == 2, (
        f"Case D 실패: ri 역행 (-40) 잘못 병합됨 (merged={len(merged)}건). "
        f"merged[0].ri={merged[0]['ref_idx']}, ri_end={merged[0].get('ref_idx_end')}"
    )


CASES.append(("D. ★ ri 큰 역행 (-40) 미병합 — 핵심", case_ri_backward_large))


# ─────────────────────────────────────────────────────────────
# Case E ★ — ri 작은 역행 (-1) 미병합 (수정 전 FAIL 예상)
# ti +1 (인접) but ri -1 (역행) → 수정 후 미병합
# 수정 전: -1 ≤ 2 통과로 잘못 병합 → ri_end=9 < ri_start=10
# ─────────────────────────────────────────────────────────────
def case_ri_backward_small():
    matches = [_make_match(5, 10), _make_match(6, 9)]
    merged = _merge_adjacent(matches)
    assert len(merged) == 2, (
        f"Case E 실패: ri 1 역행 잘못 병합됨 (merged={len(merged)}건). "
        f"merged[0].ri={merged[0]['ref_idx']}, ri_end={merged[0].get('ref_idx_end')}"
    )


CASES.append(("E. ★ ri 작은 역행 (-1) 미병합", case_ri_backward_small))


# ─────────────────────────────────────────────────────────────
# Case F — Type 다르면 미병합 (회귀 방지)
# paraphrase ↔ translation 은 v3 같은 카테고리지만 type 다름 → 미병합
# ─────────────────────────────────────────────────────────────
def case_different_type_no_merge():
    matches = [
        _make_match(5, 10, TYPE_PARAPHRASE),
        _make_match(6, 11, TYPE_TRANSLATION),
    ]
    merged = _merge_adjacent(matches)
    assert len(merged) == 2, (
        f"Case F 실패: type 다른데 병합됨 (paraphrase + translation, merged={len(merged)}건)"
    )


CASES.append(("F. Type 다른 매칭 미병합 (paraphrase + translation)", case_different_type_no_merge))


# ─────────────────────────────────────────────────────────────
# Case G — 부수 보강: forward 3건 연쇄 병합 (회귀 방지)
# ─────────────────────────────────────────────────────────────
def case_forward_chain_merge():
    matches = [_make_match(5, 10), _make_match(6, 11), _make_match(7, 12)]
    merged = _merge_adjacent(matches)
    assert len(merged) == 1, (
        f"Case G 실패: forward 3건 연쇄 병합 안 됨 (merged={len(merged)}건)"
    )
    m = merged[0]
    assert m.get("target_idx_end") == 7 and m.get("ref_idx_end") == 12, (
        f"Case G 실패: 연쇄 병합 후 범위 [ti:5-7, ri:10-12] 아님 "
        f"(ti_end={m.get('target_idx_end')}, ri_end={m.get('ref_idx_end')})"
    )


CASES.append(("G. Forward 3건 연쇄 병합 [ti:5-7, ri:10-12]", case_forward_chain_merge))


# ─────────────────────────────────────────────────────────────
# Case H — Plan-52: exclusion_reason 다른 매칭은 병합 차단
# 일반 문장 (reason=None) + 헤더 (reason=table_structural) → 미병합
# 분자 inflation 방지
# ─────────────────────────────────────────────────────────────
def case_different_exclusion_reason_no_merge():
    m1 = _make_match(5, 10, TYPE_PARAPHRASE)
    m2 = _make_match(6, 11, TYPE_PARAPHRASE)
    m2["exclusion_reason"] = "table_structural"
    matches = [m1, m2]
    merged = _merge_adjacent(matches)
    assert len(merged) == 2, (
        f"Case H 실패: exclusion_reason 다른데 병합됨 (merged={len(merged)}건). "
        f"prev.reason={merged[0].get('exclusion_reason')}, m.reason="
        f"{merged[1].get('exclusion_reason') if len(merged)>1 else 'N/A'}"
    )


CASES.append(("H. exclusion_reason 다른 매칭 미병합 (None vs table_structural)", case_different_exclusion_reason_no_merge))


def main() -> int:
    print("Plan-51 Phase 1 — _merge_adjacent ri 방향 검증\n")
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
        print("=" * 60)
        print(f"PASS: {len(CASES)} 케이스 모두 통과 — ri 양방향 forward 보장")
        print("=" * 60)
        return 0
    print("=" * 60)
    print(f"FAIL: {fail}/{len(CASES)} 건 실패")
    print("  ★ Case D, E 가 수정 전 FAIL 인 것은 결함 객관 증거 — 정상")
    print("=" * 60)
    return 1


if __name__ == "__main__":
    sys.exit(main())
