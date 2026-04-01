"""
유사도 비교 엔진 — 문장 분리 → 임베딩 → 유사도 행렬 → 정렬 → 구간 병합

1:1 문서 비교 전용. 향후 1:N 확장 시 Stage 1(후보 선별)을 앞에 추가.
"""
import logging
import re
from typing import Optional

import numpy as np

import config

logger = logging.getLogger(__name__)

# ── 기본 임계값 ──
DEFAULT_THRESHOLD_HIGH = 0.85
DEFAULT_THRESHOLD_MEDIUM = 0.70

# ── 규격 번호 패턴 ──
SPEC_PATTERNS = [
    r"MIL-STD-\d+[A-Z]?",
    r"MIL-DTL-\d+[A-Z]?",
    r"MIL-PRF-\d+[A-Z]?",
    r"MIL-HDBK-\d+[A-Z]?",
    r"AS\d{4,}[A-Z]?",
    r"AMS\d{4,}[A-Z]?",
    r"EN\s?\d{3,}",
    r"ISO\s?\d{3,}",
    r"KS\s?[A-Z]\s?\d{4,}",
    r"ASTM\s?[A-Z]\d+",
    r"SAE\s?[A-Z]?\d+",
    r"RTCA\s?DO-\d+",
]
_spec_regex = re.compile("|".join(SPEC_PATTERNS), re.IGNORECASE)


def run_similarity(
    target_text: str,
    reference_text: str,
    threshold_high: Optional[float] = None,
    threshold_medium: Optional[float] = None,
) -> dict:
    """유사도 비교를 수행하여 매칭 결과를 반환한다.

    Args:
        target_text: 검사 대상 plain text
        reference_text: 참조 원문 plain text
        threshold_high: 높은 유사 임계값 (기본 0.85)
        threshold_medium: 중간 유사 임계값 (기본 0.70)

    Returns:
        {
            "summary": { total_sentences, high_count, medium_count, clean_count, similarity_score },
            "matches": [ { target_idx, target_text, ref_idx, ref_text, similarity, level, method } ],
            "target_sentences": [ str ],
            "reference_sentences": [ str ],
        }
    """
    th_high = threshold_high or getattr(config, "VERIFY_SIMILARITY_THRESHOLD_HIGH", DEFAULT_THRESHOLD_HIGH)
    th_medium = threshold_medium or getattr(config, "VERIFY_SIMILARITY_THRESHOLD_MEDIUM", DEFAULT_THRESHOLD_MEDIUM)

    # 1. 문장 분리
    target_sents = split_sentences(target_text)
    ref_sents = split_sentences(reference_text)

    if not target_sents or not ref_sents:
        return _empty_result(target_sents, ref_sents)

    # 2. 규격 번호 exact match
    spec_matches = find_spec_matches(target_sents, ref_sents)

    # 3. 임베딩 + 유사도 행렬
    sim_matrix = compute_similarity_matrix(target_sents, ref_sents)

    # 4. 최적 정렬 (DP + 규격 매칭 보너스)
    alignments = align_sentences(sim_matrix, spec_matches, th_medium)

    # 5. 임계값 분류 + 구간 병합
    matches = classify_and_merge(
        alignments, target_sents, ref_sents, th_high, th_medium
    )

    # 6. 요약 통계
    high_count = sum(1 for m in matches if m["level"] == "high")
    medium_count = sum(1 for m in matches if m["level"] == "medium")
    clean_count = len(target_sents) - high_count - medium_count

    # 유사율: 유사 문장 비율 (가중)
    if target_sents:
        similarity_score = round(
            (high_count * 1.0 + medium_count * 0.5) / len(target_sents) * 100, 1
        )
    else:
        similarity_score = 0.0

    return {
        "summary": {
            "total_sentences": len(target_sents),
            "high_count": high_count,
            "medium_count": medium_count,
            "clean_count": clean_count,
            "similarity_score": similarity_score,
        },
        "matches": matches,
        "target_sentences": target_sents,
        "reference_sentences": ref_sents,
    }


# ══════════════════════════════════════════
# 1. 문장 분리
# ══════════════════════════════════════════

def split_sentences(text: str) -> list:
    """텍스트를 문장 단위로 분리한다.

    한국어/영어 혼합 문서 지원. 빈 문장 제거.
    """
    if not text or not text.strip():
        return []

    # 줄바꿈 기준 단락 분리 → 단락 내 문장 분리
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

    sentences = []
    for para in paragraphs:
        # 문장 분리: 마침표/물음표/느낌표 + 공백 또는 끝
        # 단, 소수점(3.14), 규격번호(MIL-STD-810G.pdf), 약어(Dr. Mr.) 보호
        sents = _sentence_split(para)
        sentences.extend(sents)

    # 너무 짧은 문장 필터 (2단어 미만)
    sentences = [s for s in sentences if len(s.split()) >= 2]

    return sentences


def _sentence_split(text: str) -> list:
    """문장 경계 감지 (정규식 기반, 가벼운 폴백)"""
    # 마침표 뒤에 대문자 또는 한글이 오면 문장 경계
    # 단, 소수점/약어/규격번호는 분리하지 않음
    pattern = r'(?<=[.!?])\s+(?=[A-Z가-힣\"\'])'
    parts = re.split(pattern, text)
    return [p.strip() for p in parts if p.strip()]


# ══════════════════════════════════════════
# 2. 규격 번호 exact match
# ══════════════════════════════════════════

def find_spec_matches(target_sents: list, ref_sents: list) -> list:
    """규격 번호 기반 exact match 쌍을 찾는다.

    Returns: [(target_idx, ref_idx, matched_spec), ...]
    """
    # 각 문장에서 규격 번호 추출
    target_specs = [set(_spec_regex.findall(s.upper())) for s in target_sents]
    ref_specs = [set(_spec_regex.findall(s.upper())) for s in ref_sents]

    matches = []
    for ti, t_specs in enumerate(target_specs):
        if not t_specs:
            continue
        for ri, r_specs in enumerate(ref_specs):
            common = t_specs & r_specs
            if common:
                matches.append((ti, ri, list(common)[0]))

    return matches


# ══════════════════════════════════════════
# 3. 임베딩 + 유사도 행렬
# ══════════════════════════════════════════

def compute_similarity_matrix(target_sents: list, ref_sents: list) -> np.ndarray:
    """문장 쌍의 코사인 유사도 행렬을 계산한다.

    Returns: np.ndarray shape (len(target), len(ref)), 값 범위 0~1
    """
    from services.embedding_client import get_embeddings

    all_texts = target_sents + ref_sents
    logger.info(f"임베딩 요청: {len(all_texts)}개 문장 ({len(target_sents)} + {len(ref_sents)})")

    # Ollama 배치 크기 제한 대응: 청크 분할
    BATCH_SIZE = getattr(config, "VERIFY_SIMILARITY_BATCH_SIZE", 2)
    all_embeddings = []
    for i in range(0, len(all_texts), BATCH_SIZE):
        chunk = all_texts[i:i + BATCH_SIZE]
        all_embeddings.extend(get_embeddings(chunk))

    all_vecs = np.array(all_embeddings, dtype=np.float32)

    target_vecs = all_vecs[:len(target_sents)]
    ref_vecs = all_vecs[len(target_sents):]

    # 정규화 (코사인 유사도 = 정규화 후 내적)
    target_norms = np.linalg.norm(target_vecs, axis=1, keepdims=True)
    ref_norms = np.linalg.norm(ref_vecs, axis=1, keepdims=True)
    target_vecs = target_vecs / np.maximum(target_norms, 1e-10)
    ref_vecs = ref_vecs / np.maximum(ref_norms, 1e-10)

    # 유사도 행렬: (M x N)
    sim_matrix = target_vecs @ ref_vecs.T

    return sim_matrix


# ══════════════════════════════════════════
# 4. 최적 정렬 (Greedy + 규격 보너스)
# ══════════════════════════════════════════

def align_sentences(
    sim_matrix: np.ndarray,
    spec_matches: list,
    threshold: float,
) -> list:
    """유사도 행렬에서 최적 문장 쌍을 찾는다.

    규격 번호 매칭에 보너스를 주고, 임계값 이상인 쌍만 반환.

    Returns: [(target_idx, ref_idx, similarity, method), ...]
    """
    M, N = sim_matrix.shape

    # 규격 매칭 보너스 적용 (+0.1)
    spec_bonus = np.zeros_like(sim_matrix)
    spec_set = set()
    for ti, ri, spec in spec_matches:
        if ti < M and ri < N:
            spec_bonus[ti, ri] = 0.1
            spec_set.add((ti, ri))

    boosted = sim_matrix + spec_bonus
    boosted = np.clip(boosted, 0, 1.0)

    # Greedy 매칭: 각 target 문장에 대해 최고 유사도 ref 선택
    alignments = []
    used_refs = set()

    # 유사도 높은 순으로 정렬
    pairs = []
    for ti in range(M):
        for ri in range(N):
            if boosted[ti, ri] >= threshold:
                pairs.append((boosted[ti, ri], sim_matrix[ti, ri], ti, ri))

    pairs.sort(key=lambda x: x[0], reverse=True)

    used_targets = set()
    for boosted_sim, raw_sim, ti, ri in pairs:
        if ti in used_targets or ri in used_refs:
            continue
        method = "semantic+term" if (ti, ri) in spec_set else "semantic"
        alignments.append((ti, ri, float(raw_sim), method))
        used_targets.add(ti)
        used_refs.add(ri)

    # target_idx 순으로 정렬
    alignments.sort(key=lambda x: x[0])

    return alignments


# ══════════════════════════════════════════
# 5. 분류 + 구간 병합
# ══════════════════════════════════════════

def classify_and_merge(
    alignments: list,
    target_sents: list,
    ref_sents: list,
    th_high: float,
    th_medium: float,
) -> list:
    """정렬된 문장 쌍을 분류하고 인접 구간을 병합한다.

    Returns: [
        {
            target_idx, target_text,
            ref_idx, ref_text,
            similarity, level, method
        }, ...
    ]
    """
    matches = []
    for ti, ri, sim, method in alignments:
        if sim >= th_high:
            level = "high"
        elif sim >= th_medium:
            level = "medium"
        else:
            continue  # 임계값 미달은 제외

        matches.append({
            "target_idx": ti,
            "target_text": target_sents[ti],
            "ref_idx": ri,
            "ref_text": ref_sents[ri],
            "similarity": round(sim, 4),
            "level": level,
            "method": method,
        })

    # 구간 병합: 연속된 target_idx를 하나의 구간으로 (gap_tolerance=1)
    if len(matches) <= 1:
        return matches

    merged = [matches[0]]
    for m in matches[1:]:
        prev = merged[-1]
        # 같은 level이고 target/ref 모두 연속이면 병합
        if (m["level"] == prev["level"]
                and m["target_idx"] - prev["target_idx"] <= 2
                and m["ref_idx"] - prev["ref_idx"] <= 2):
            # 병합: 텍스트 합치기, 유사도는 평균
            prev["target_text"] += " " + m["target_text"]
            prev["ref_text"] += " " + m["ref_text"]
            prev["similarity"] = round(
                (prev["similarity"] + m["similarity"]) / 2, 4
            )
            prev["target_idx_end"] = m["target_idx"]
            prev["ref_idx_end"] = m["ref_idx"]
        else:
            merged.append(m)

    return merged


# ══════════════════════════════════════════
# 헬퍼
# ══════════════════════════════════════════

def _empty_result(target_sents, ref_sents):
    """빈 결과"""
    return {
        "summary": {
            "total_sentences": len(target_sents) if target_sents else 0,
            "high_count": 0,
            "medium_count": 0,
            "clean_count": len(target_sents) if target_sents else 0,
            "similarity_score": 0.0,
        },
        "matches": [],
        "target_sentences": target_sents or [],
        "reference_sentences": ref_sents or [],
    }
