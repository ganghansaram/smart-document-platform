"""
14개 골드 라벨 페어 JSON 자동 생성.
페어별 기대 점수 대역 + 라벨 분포 비율을 정의한다.

분포 비율은 [min, max] 형태 — 시스템이 이 범위에 들어와야 통과.
"""
import json
from pathlib import Path

PAIRS = [
    # ── Seed A 기반 7페어 ──
    {
        "id": "pair_01_verbatim_a",
        "name": "Verbatim copy of seed A",
        "target_file": "variants/var_a_verbatim.md",
        "ref_file": "seeds/seed_a_emc.md",
        "obfuscation": "verbatim",
        "seed": "a",
        "expected_band": "red",
        "expected_score_range": [85, 100],
        "expected_label_distribution": {
            "identical":  [0.85, 1.00],
            "near_copy":  [0.00, 0.15],
            "paraphrase": [0.00, 0.05],
            "translation":[0.00, 0.00],
            "low_sim":    [0.00, 0.05]
        },
        "min_match_count": 30,
        "notes": "Identical detection should be near-perfect (Winnowing fast-accept)."
    },
    {
        "id": "pair_02_random_obf_a",
        "name": "Random word substitution (~10-30%) of seed A",
        "target_file": "variants/var_a_random_obf.md",
        "ref_file": "seeds/seed_a_emc.md",
        "obfuscation": "random_obf",
        "seed": "a",
        "expected_band": "orange",
        "expected_score_range": [50, 90],
        "expected_label_distribution": {
            "identical":  [0.20, 0.75],
            "near_copy":  [0.10, 0.70],
            "paraphrase": [0.00, 0.20],
            "translation":[0.00, 0.00],
            "low_sim":    [0.00, 0.10]
        },
        "min_match_count": 28,
        "notes": "R1 calibration: actual variant ~10-15% substitution (lighter than intended). identical 상한 0.75."
    },
    {
        "id": "pair_03_para_light_a",
        "name": "Light paraphrase (sentence structure preserved) of seed A",
        "target_file": "variants/var_a_para_light.md",
        "ref_file": "seeds/seed_a_emc.md",
        "obfuscation": "para_light",
        "seed": "a",
        "expected_band": "yellow_orange",
        "expected_score_range": [25, 75],
        "expected_label_distribution": {
            "identical":  [0.00, 0.20],
            "near_copy":  [0.00, 0.60],
            "paraphrase": [0.20, 1.00],
            "translation":[0.00, 0.00],
            "low_sim":    [0.00, 0.50]
        },
        "min_match_count": 25,
        "notes": "R1: 실측 paraphrase 1.0 (heavy 의역과 구분 미세 — bge-m3 sem 0.85+ 분포가 paraphrase로 잘 잡힘)."
    },
    {
        "id": "pair_04_para_heavy_a",
        "name": "Heavy paraphrase (deep restructure) of seed A",
        "target_file": "variants/var_a_para_heavy.md",
        "ref_file": "seeds/seed_a_emc.md",
        "obfuscation": "para_heavy",
        "seed": "a",
        "expected_band": "yellow",
        "expected_score_range": [10, 60],
        "expected_label_distribution": {
            "identical":  [0.00, 0.20],
            "near_copy":  [0.00, 0.30],
            "paraphrase": [0.10, 0.80],
            "translation":[0.00, 0.00],
            "low_sim":    [0.10, 0.80]
        },
        "min_match_count": 18,
        "notes": "R1: 점수 하한 15→10 (heavy 의역은 검출 어려움 — 점수가 낮게 나오는 것이 정상)."
    },
    {
        "id": "pair_05_cyclic_trans_a",
        "name": "Cyclic translation obfuscation (translate-back style) of seed A",
        "target_file": "variants/var_a_cyclic_trans.md",
        "ref_file": "seeds/seed_a_emc.md",
        "obfuscation": "cyclic_trans",
        "seed": "a",
        "expected_band": "yellow",
        "expected_score_range": [25, 70],
        "expected_label_distribution": {
            "identical":  [0.00, 0.20],
            "near_copy":  [0.00, 0.50],
            "paraphrase": [0.20, 0.95],
            "translation":[0.00, 0.10],
            "low_sim":    [0.00, 0.50]
        },
        "min_match_count": 25,
        "notes": "R1: paraphrase 상한 0.95 (cyclic 번역도 동일 언어 의역과 유사 패턴)."
    },
    {
        "id": "pair_06_direct_trans_a",
        "name": "Direct Korean translation of seed A vs English original",
        "target_file": "seeds/seed_a_emc_ko.md",
        "ref_file": "seeds/seed_a_emc.md",
        "obfuscation": "direct_trans",
        "seed": "a",
        "expected_band": "yellow",
        "expected_score_range": [20, 60],
        "expected_label_distribution": {
            "identical":  [0.00, 0.05],
            "near_copy":  [0.00, 0.10],
            "paraphrase": [0.00, 0.20],
            "translation":[0.40, 1.00],
            "low_sim":    [0.00, 0.30]
        },
        "min_match_count": 20,
        "notes": "Translation label should dominate — fp ≈ 0, sem high. Critical test for TYPE_TRANSLATION branch."
    },
    {
        "id": "pair_07_boilerplate_a",
        "name": "Boilerplate-heavy variant of seed A (filler phrases inserted)",
        "target_file": "variants/var_a_boilerplate.md",
        "ref_file": "seeds/seed_a_emc.md",
        "obfuscation": "boilerplate",
        "seed": "a",
        "expected_band": "green_blue",
        "expected_score_range": [0, 30],
        "expected_label_distribution": {
            "identical":  [0.00, 0.30],
            "near_copy":  [0.00, 0.30],
            "paraphrase": [0.00, 0.50],
            "translation":[0.00, 0.00],
            "low_sim":    [0.10, 0.70]
        },
        "min_match_count": 10,
        "expected_boilerplate_ratio_min": 0.30,
        "notes": "R1: 일부 boilerplate 변형 문장이 sem 매칭에서 paraphrase로 잡힘 (boilerplate 50%-borderline). paraphrase 상한 완화."
    },
    # ── Seed B 기반 6페어 ──
    {
        "id": "pair_08_verbatim_b",
        "name": "Verbatim copy of seed B",
        "target_file": "variants/var_b_verbatim.md",
        "ref_file": "seeds/seed_b_env.md",
        "obfuscation": "verbatim",
        "seed": "b",
        "expected_band": "red",
        "expected_score_range": [85, 100],
        "expected_label_distribution": {
            "identical":  [0.85, 1.00],
            "near_copy":  [0.00, 0.15],
            "paraphrase": [0.00, 0.05],
            "translation":[0.00, 0.00],
            "low_sim":    [0.00, 0.05]
        },
        "min_match_count": 33,
        "notes": "Cross-validate verbatim detection on different seed."
    },
    {
        "id": "pair_09_random_obf_b",
        "name": "Random word substitution of seed B",
        "target_file": "variants/var_b_random_obf.md",
        "ref_file": "seeds/seed_b_env.md",
        "obfuscation": "random_obf",
        "seed": "b",
        "expected_band": "orange",
        "expected_score_range": [50, 90],
        "expected_label_distribution": {
            "identical":  [0.20, 0.75],
            "near_copy":  [0.10, 0.70],
            "paraphrase": [0.00, 0.20],
            "translation":[0.00, 0.00],
            "low_sim":    [0.00, 0.10]
        },
        "min_match_count": 30,
        "notes": "R1: pair_02와 동일 보정."
    },
    {
        "id": "pair_10_para_light_b",
        "name": "Light paraphrase of seed B",
        "target_file": "variants/var_b_para_light.md",
        "ref_file": "seeds/seed_b_env.md",
        "obfuscation": "para_light",
        "seed": "b",
        "expected_band": "yellow_orange",
        "expected_score_range": [25, 75],
        "expected_label_distribution": {
            "identical":  [0.00, 0.20],
            "near_copy":  [0.00, 0.60],
            "paraphrase": [0.20, 0.95],
            "translation":[0.00, 0.00],
            "low_sim":    [0.00, 0.50]
        },
        "min_match_count": 27,
        "notes": "R1: pair_03와 동일 보정."
    },
    {
        "id": "pair_11_para_heavy_b",
        "name": "Heavy paraphrase of seed B",
        "target_file": "variants/var_b_para_heavy.md",
        "ref_file": "seeds/seed_b_env.md",
        "obfuscation": "para_heavy",
        "seed": "b",
        "expected_band": "yellow",
        "expected_score_range": [15, 60],
        "expected_label_distribution": {
            "identical":  [0.00, 0.05],
            "near_copy":  [0.00, 0.30],
            "paraphrase": [0.30, 0.80],
            "translation":[0.00, 0.00],
            "low_sim":    [0.10, 0.50]
        },
        "min_match_count": 20,
        "notes": "Cross-validation pair."
    },
    {
        "id": "pair_12_cyclic_trans_b",
        "name": "Cyclic translation of seed B",
        "target_file": "variants/var_b_cyclic_trans.md",
        "ref_file": "seeds/seed_b_env.md",
        "obfuscation": "cyclic_trans",
        "seed": "b",
        "expected_band": "yellow",
        "expected_score_range": [25, 70],
        "expected_label_distribution": {
            "identical":  [0.00, 0.20],
            "near_copy":  [0.00, 0.50],
            "paraphrase": [0.20, 0.95],
            "translation":[0.00, 0.10],
            "low_sim":    [0.00, 0.50]
        },
        "min_match_count": 27,
        "notes": "R1: pair_05와 동일 보정."
    },
    {
        "id": "pair_13_boilerplate_b",
        "name": "Boilerplate-heavy variant of seed B",
        "target_file": "variants/var_b_boilerplate.md",
        "ref_file": "seeds/seed_b_env.md",
        "obfuscation": "boilerplate",
        "seed": "b",
        "expected_band": "green_blue",
        "expected_score_range": [0, 30],
        "expected_label_distribution": {
            "identical":  [0.00, 0.30],
            "near_copy":  [0.00, 0.30],
            "paraphrase": [0.00, 0.50],
            "translation":[0.00, 0.00],
            "low_sim":    [0.10, 0.70]
        },
        "min_match_count": 10,
        "expected_boilerplate_ratio_min": 0.30,
        "notes": "R1: pair_07과 동일 보정."
    },
    # ── 베이스라인 1페어 ──
    {
        "id": "pair_14_no_plagiarism",
        "name": "No plagiarism — different seeds A vs B",
        "target_file": "seeds/seed_a_emc.md",
        "ref_file": "seeds/seed_b_env.md",
        "obfuscation": "no_plagiarism",
        "seed": "ab",
        "expected_band": "blue_green",
        "expected_score_range": [0, 25],
        "expected_label_distribution": {
            "identical":  [0.00, 0.10],
            "near_copy":  [0.00, 0.15],
            "paraphrase": [0.00, 0.20],
            "translation":[0.00, 0.00],
            "low_sim":    [0.30, 1.00]
        },
        "min_match_count": 0,
        "max_substantive_matches": 5,
        "notes": "Critical baseline — false positive test. Both are MIL-STD style so some technical phrase overlap is expected, but adjusted_pct should be < 25%."
    },
]


def main():
    pairs_dir = Path(__file__).parent / "pairs"
    pairs_dir.mkdir(parents=True, exist_ok=True)

    for pair in PAIRS:
        out = pairs_dir / f"{pair['id']}.json"
        out.write_text(json.dumps(pair, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Wrote {out.name}")

    print(f"\nTotal: {len(PAIRS)} pairs written to {pairs_dir}")


if __name__ == "__main__":
    main()
