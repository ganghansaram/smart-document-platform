"""
유사도 비교 엔진 — 다층 파이프라인

Layer 1: Winnowing (character n-gram fingerprint) — 정확/근사 매칭
Layer 3: Semantic Embedding (bge-m3) — 의미적 유사도 (패러프레이즈/번역)
정형 구문 필터: 도메인 표준 문구 제외

1:1 문서 비교 전용. 향후 1:N 확장 시 Stage 1(후보 선별)을 앞에 추가.
"""
import json
import logging
import re
from pathlib import Path
from typing import Optional

import numpy as np

import config

logger = logging.getLogger(__name__)

# ── 기본 임계값 ──
DEFAULT_THRESHOLD_HIGH = 0.85
DEFAULT_THRESHOLD_MEDIUM = 0.70

# ── 분류 유형 ──
TYPE_IDENTICAL = "identical"
TYPE_NEAR_COPY = "near_copy"
TYPE_PARAPHRASE = "paraphrase"
TYPE_TRANSLATION = "translation"
TYPE_LOW_SIM = "low_sim"
TYPE_BOILERPLATE = "boilerplate"

# ── 심각도 매핑 ──
SEVERITY_MAP = {
    TYPE_IDENTICAL: "critical",
    TYPE_NEAR_COPY: "high",
    TYPE_PARAPHRASE: "medium",
    TYPE_TRANSLATION: "medium",
    TYPE_LOW_SIM: "low",
    TYPE_BOILERPLATE: "none",
}

# ── 기존 level 호환 매핑 (프론트엔드 하위 호환) ──
LEVEL_COMPAT = {
    TYPE_IDENTICAL: "high",
    TYPE_NEAR_COPY: "high",
    TYPE_PARAPHRASE: "medium",
    TYPE_TRANSLATION: "medium",
    TYPE_LOW_SIM: "low",
    TYPE_BOILERPLATE: "none",
}

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

# ── Winnowing 파라미터 ──
WINNOW_K = 25       # character k-gram 크기
WINNOW_WINDOW = 4   # sliding window 크기

# ── 정형 구문 허용 목록 (lazy load) ──
_boilerplate_phrases = None


def _load_boilerplate():
    """정형 구문 허용 목록을 로드한다."""
    global _boilerplate_phrases
    if _boilerplate_phrases is not None:
        return _boilerplate_phrases

    bp_path = Path(__file__).parent.parent.parent / "data" / "boilerplate-phrases.json"
    try:
        with open(bp_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _boilerplate_phrases = [p.lower() for p in data.get("phrases", [])]
        logger.info("정형 구문 허용 목록 로드: %d개", len(_boilerplate_phrases))
    except Exception as e:
        logger.warning("정형 구문 허용 목록 로드 실패: %s", e)
        _boilerplate_phrases = []
    return _boilerplate_phrases


# ══════════════════════════════════════════
# 메인 진입점
# ══════════════════════════════════════════

def run_similarity(
    target_text: str,
    reference_text: str,
    threshold_high: Optional[float] = None,
    threshold_medium: Optional[float] = None,
) -> dict:
    """다층 파이프라인으로 유사도 비교를 수행한다.

    파이프라인:
      0. 전처리 + 문장 분리
      1. 정형 구문 필터 (허용 목록)
      2. Layer 1: Winnowing fingerprint (정확/근사 매칭)
      3. Layer 3: Semantic embedding (패러프레이즈/번역)
      4. 분류 + 구간 병합 + 통계
    """
    th_high = threshold_high or getattr(
        config, "VERIFY_SIMILARITY_THRESHOLD_HIGH", DEFAULT_THRESHOLD_HIGH
    )
    th_medium = threshold_medium or getattr(
        config, "VERIFY_SIMILARITY_THRESHOLD_MEDIUM", DEFAULT_THRESHOLD_MEDIUM
    )

    # 0. 문장 분리
    target_sents = split_sentences(target_text)
    ref_sents = split_sentences(reference_text)

    if not target_sents or not ref_sents:
        return _empty_result(target_sents, ref_sents)

    M, N = len(target_sents), len(ref_sents)
    logger.info("유사도 검사 시작: 대상 %d문장, 참조 %d문장", M, N)

    # 1. 정형 구문 필터
    boilerplate_indices = _detect_boilerplate(target_sents)

    # 2. Layer 1: Winnowing fingerprint
    fp_matrix = _compute_fingerprint_matrix(target_sents, ref_sents)

    # fast-accept: L1 >0.85 → 즉시 identical 분류
    l1_matches = []
    l3_candidates = []  # (ti, ri) — L3에서 추가 분석할 후보

    used_targets_l1 = set()
    used_refs_l1 = set()

    # L1 점수 높은 순으로 greedy 매칭
    l1_pairs = []
    for ti in range(M):
        if ti in boilerplate_indices:
            continue
        for ri in range(N):
            score = fp_matrix[ti, ri]
            if score > 0.05:
                l1_pairs.append((score, ti, ri))

    l1_pairs.sort(key=lambda x: x[0], reverse=True)

    for score, ti, ri in l1_pairs:
        if ti in used_targets_l1 or ri in used_refs_l1:
            continue
        if score >= 0.85:
            # fast-accept: identical
            l1_matches.append({
                "target_idx": ti,
                "ref_idx": ri,
                "type": TYPE_IDENTICAL,
                "scores": {"fingerprint": round(float(score), 4), "semantic": None},
                "detection_layer": "L1",
            })
            used_targets_l1.add(ti)
            used_refs_l1.add(ri)
        elif score >= 0.40:
            # 중간 대역: L3에서 보강 판정
            l3_candidates.append((ti, ri, float(score)))

    # 3. Layer 3: Semantic embedding
    # L1에서 확정되지 않은 문장들만 임베딩 대상
    need_embedding_t = set(range(M)) - used_targets_l1 - boilerplate_indices
    need_embedding_r = set(range(N)) - used_refs_l1

    l3_matches = []
    if need_embedding_t and need_embedding_r:
        sim_matrix = compute_similarity_matrix(target_sents, ref_sents)

        # L1 중간 대역 후보 먼저 처리
        used_targets_l3 = set()
        used_refs_l3 = set()

        for ti, ri, fp_score in l3_candidates:
            if ti in used_targets_l1 or ri in used_refs_l1:
                continue
            if ti in used_targets_l3 or ri in used_refs_l3:
                continue
            sem_score = float(sim_matrix[ti, ri])
            if sem_score >= th_medium:
                match_type = _classify_match(fp_score, sem_score, th_high)
                l3_matches.append({
                    "target_idx": ti,
                    "ref_idx": ri,
                    "type": match_type,
                    "scores": {"fingerprint": round(fp_score, 4), "semantic": round(sem_score, 4)},
                    "detection_layer": "L1+L3",
                })
                used_targets_l3.add(ti)
                used_refs_l3.add(ri)

        # 나머지: L1 미매칭 문장에서 greedy semantic 매칭
        sem_pairs = []
        for ti in need_embedding_t - used_targets_l3:
            if ti in boilerplate_indices:
                continue
            for ri in need_embedding_r - used_refs_l3:
                if ri in used_refs_l1:
                    continue
                sem_score = float(sim_matrix[ti, ri])
                if sem_score >= 0.65:  # low_sim 이상만 후보
                    fp_score = float(fp_matrix[ti, ri]) if ti < M and ri < N else 0.0
                    sem_pairs.append((sem_score, fp_score, ti, ri))

        sem_pairs.sort(key=lambda x: x[0], reverse=True)

        for sem_score, fp_score, ti, ri in sem_pairs:
            if ti in used_targets_l3 or ri in used_refs_l3:
                continue
            match_type = _classify_match(fp_score, sem_score, th_high)
            l3_matches.append({
                "target_idx": ti,
                "ref_idx": ri,
                "type": match_type,
                "scores": {"fingerprint": round(fp_score, 4), "semantic": round(sem_score, 4)},
                "detection_layer": "L3",
            })
            used_targets_l3.add(ti)
            used_refs_l3.add(ri)

    # 4. 정형 구문 매칭 생성 (점수 제외, 표시용)
    bp_matches = []
    for ti in boilerplate_indices:
        bp_matches.append({
            "target_idx": ti,
            "ref_idx": -1,
            "type": TYPE_BOILERPLATE,
            "scores": {"fingerprint": None, "semantic": None},
            "detection_layer": "filter",
        })

    # 5. 전체 매칭 통합 + 텍스트 채우기 + 구간 병합
    all_matches = l1_matches + l3_matches
    all_matches.sort(key=lambda x: x["target_idx"])

    # 텍스트 채우기 + 하위 호환 필드
    for m in all_matches:
        ti, ri = m["target_idx"], m["ref_idx"]
        m["target_text"] = target_sents[ti]
        m["ref_text"] = ref_sents[ri] if ri >= 0 else ""
        m["severity"] = SEVERITY_MAP[m["type"]]
        # 하위 호환
        m["level"] = LEVEL_COMPAT[m["type"]]
        m["similarity"] = m["scores"].get("semantic") or m["scores"].get("fingerprint") or 0
        m["method"] = m["detection_layer"]

    # 구간 병합
    merged = _merge_adjacent(all_matches)

    # 6. 통계 산출
    summary = _compute_summary(merged, bp_matches, target_sents)

    return {
        "summary": summary,
        "matches": merged,
        "target_sentences": target_sents,
        "reference_sentences": ref_sents,
    }


# ══════════════════════════════════════════
# 분류 로직
# ══════════════════════════════════════════

def _classify_match(fp_score: float, sem_score: float, th_high: float) -> str:
    """L1(fingerprint) + L3(semantic) 점수를 조합하여 매칭 유형을 결정한다."""
    if fp_score >= 0.85:
        return TYPE_IDENTICAL
    if fp_score >= 0.40 and sem_score >= th_high:
        return TYPE_NEAR_COPY
    if fp_score < 0.15 and sem_score >= 0.88:
        return TYPE_PARAPHRASE
    if sem_score >= th_high:
        return TYPE_NEAR_COPY
    if sem_score >= 0.65:
        return TYPE_LOW_SIM
    return TYPE_LOW_SIM


def _detect_boilerplate(sentences: list) -> set:
    """정형 구문이 포함된 문장 인덱스를 반환한다."""
    phrases = _load_boilerplate()
    if not phrases:
        return set()

    indices = set()
    for i, sent in enumerate(sentences):
        sent_lower = sent.lower()
        # 문장의 50% 이상이 정형 구문으로 구성되면 boilerplate 판정
        match_len = 0
        for phrase in phrases:
            if phrase in sent_lower:
                match_len += len(phrase)
        if len(sent_lower) > 0 and match_len / len(sent_lower) >= 0.5:
            indices.add(i)

    if indices:
        logger.info("정형 구문 감지: %d개 문장", len(indices))
    return indices


# ══════════════════════════════════════════
# Layer 1: Winnowing Fingerprint
# ══════════════════════════════════════════

def _compute_fingerprint_matrix(target_sents: list, ref_sents: list) -> np.ndarray:
    """Winnowing 기반 fingerprint 유사도 행렬을 계산한다.

    Returns: np.ndarray shape (M, N), 값 범위 0~1 (Jaccard 유사도)
    """
    M, N = len(target_sents), len(ref_sents)
    matrix = np.zeros((M, N), dtype=np.float32)

    target_fps = [_winnow(s) for s in target_sents]
    ref_fps = [_winnow(s) for s in ref_sents]

    for ti in range(M):
        if not target_fps[ti]:
            continue
        for ri in range(N):
            if not ref_fps[ri]:
                continue
            intersection = len(target_fps[ti] & ref_fps[ri])
            union = len(target_fps[ti] | ref_fps[ri])
            matrix[ti, ri] = intersection / union if union > 0 else 0.0

    return matrix


def _winnow(text: str) -> set:
    """텍스트의 Winnowing fingerprint를 생성한다.

    1. 정규화 (소문자, 공백 제거)
    2. character k-gram 생성
    3. Rabin-Karp rolling hash
    4. sliding window에서 최솟값 선택
    """
    # 정규화
    normalized = re.sub(r'\s+', '', text.lower())
    if len(normalized) < WINNOW_K:
        # 너무 짧으면 전체를 하나의 fingerprint로
        return {hash(normalized)} if normalized else set()

    # k-gram hash 생성
    hashes = []
    for i in range(len(normalized) - WINNOW_K + 1):
        kgram = normalized[i:i + WINNOW_K]
        hashes.append(hash(kgram))

    if not hashes:
        return set()

    # sliding window minimum selection
    fingerprints = set()
    for i in range(len(hashes) - WINNOW_WINDOW + 1):
        window = hashes[i:i + WINNOW_WINDOW]
        fingerprints.add(min(window))

    return fingerprints


# ══════════════════════════════════════════
# Layer 3: Semantic Embedding (기존 유지)
# ══════════════════════════════════════════

def compute_similarity_matrix(target_sents: list, ref_sents: list) -> np.ndarray:
    """문장 쌍의 코사인 유사도 행렬을 계산한다."""
    from services.embedding_client import get_embeddings

    all_texts = target_sents + ref_sents
    logger.info("임베딩 요청: %d개 문장 (%d + %d)", len(all_texts), len(target_sents), len(ref_sents))

    all_embeddings = get_embeddings(all_texts)
    all_vecs = np.array(all_embeddings, dtype=np.float32)

    target_vecs = all_vecs[:len(target_sents)]
    ref_vecs = all_vecs[len(target_sents):]

    # 정규화
    target_norms = np.linalg.norm(target_vecs, axis=1, keepdims=True)
    ref_norms = np.linalg.norm(ref_vecs, axis=1, keepdims=True)
    target_vecs = target_vecs / np.maximum(target_norms, 1e-10)
    ref_vecs = ref_vecs / np.maximum(ref_norms, 1e-10)

    return target_vecs @ ref_vecs.T


# ══════════════════════════════════════════
# 문장 분리 (기존 유지)
# ══════════════════════════════════════════

def split_sentences(text: str) -> list:
    """텍스트를 문장 단위로 분리한다."""
    if not text or not text.strip():
        return []

    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    sentences = []
    for para in paragraphs:
        sents = _sentence_split(para)
        sentences.extend(sents)

    sentences = [s for s in sentences if len(s.split()) >= 2]
    return sentences


def _sentence_split(text: str) -> list:
    """문장 경계 감지 (정규식 기반)"""
    pattern = r'(?<=[.!?])\s+(?=[A-Z가-힣\"\'])'
    parts = re.split(pattern, text)
    return [p.strip() for p in parts if p.strip()]


# ══════════════════════════════════════════
# 규격 번호 매칭 (기존 유지, 분류에 활용)
# ══════════════════════════════════════════

def find_spec_matches(target_sents: list, ref_sents: list) -> list:
    """규격 번호 기반 exact match 쌍을 찾는다."""
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
# 후처리
# ══════════════════════════════════════════

def _merge_adjacent(matches: list) -> list:
    """인접한 동일 유형 매칭을 병합한다."""
    if len(matches) <= 1:
        return matches

    merged = [matches[0].copy()]
    for m in matches[1:]:
        prev = merged[-1]
        if (m["type"] == prev["type"]
                and m["target_idx"] - prev.get("target_idx_end", prev["target_idx"]) <= 2
                and m["ref_idx"] >= 0 and prev["ref_idx"] >= 0
                and m["ref_idx"] - prev.get("ref_idx_end", prev["ref_idx"]) <= 2):
            prev["target_text"] += " " + m["target_text"]
            prev["ref_text"] += " " + m["ref_text"]
            prev["target_idx_end"] = m["target_idx"]
            prev["ref_idx_end"] = m["ref_idx"]
            # 유사도 평균
            prev["similarity"] = round((prev["similarity"] + m["similarity"]) / 2, 4)
            # scores: 더 높은 값 유지
            for key in ("fingerprint", "semantic"):
                p_val = prev["scores"].get(key)
                m_val = m["scores"].get(key)
                if p_val is not None and m_val is not None:
                    prev["scores"][key] = round(max(p_val, m_val), 4)
                elif m_val is not None:
                    prev["scores"][key] = m_val
        else:
            merged.append(m.copy())

    # ID 부여
    for i, m in enumerate(merged):
        m["id"] = i + 1

    return merged


def _match_sentence_count(m: dict) -> int:
    """병합된 매칭이 커버하는 target 문장 수를 반환한다."""
    start = m["target_idx"]
    end = m.get("target_idx_end", start)
    return end - start + 1


def _compute_summary(matches: list, bp_matches: list, target_sents: list) -> dict:
    """통계를 산출한다. 기존 필드 + 신규 breakdown/tiers 필드."""
    total = len(target_sents)
    type_counts = {}
    for t in (TYPE_IDENTICAL, TYPE_NEAR_COPY, TYPE_PARAPHRASE, TYPE_TRANSLATION, TYPE_LOW_SIM):
        type_counts[t] = sum(_match_sentence_count(m) for m in matches if m["type"] == t)
    bp_count = len(bp_matches)

    matched_count = sum(type_counts.values())
    clean_count = total - matched_count - bp_count

    # 3-tier 점수 산출
    substantive = type_counts[TYPE_IDENTICAL] + type_counts[TYPE_NEAR_COPY]
    derived = type_counts[TYPE_PARAPHRASE] + type_counts[TYPE_TRANSLATION]

    raw_pct = round((matched_count + bp_count) / max(total, 1) * 100, 1)
    substantive_pct = round(substantive / max(total, 1) * 100, 1)
    derived_pct = round(derived / max(total, 1) * 100, 1)
    bp_pct = round(bp_count / max(total, 1) * 100, 1)
    adjusted_pct = round((substantive + derived * 0.5) / max(total, 1) * 100, 1)

    # 기존 호환 필드
    high_count = type_counts[TYPE_IDENTICAL] + type_counts[TYPE_NEAR_COPY]
    medium_count = type_counts[TYPE_PARAPHRASE] + type_counts[TYPE_TRANSLATION] + type_counts[TYPE_LOW_SIM]

    return {
        # 기존 호환
        "total_sentences": total,
        "high_count": high_count,
        "medium_count": medium_count,
        "clean_count": clean_count,
        "similarity_score": adjusted_pct,
        # 신규: 유형별 breakdown
        "breakdown": {
            TYPE_IDENTICAL: {"count": type_counts[TYPE_IDENTICAL], "percentage": round(type_counts[TYPE_IDENTICAL] / max(total, 1) * 100, 1)},
            TYPE_NEAR_COPY: {"count": type_counts[TYPE_NEAR_COPY], "percentage": round(type_counts[TYPE_NEAR_COPY] / max(total, 1) * 100, 1)},
            TYPE_PARAPHRASE: {"count": type_counts[TYPE_PARAPHRASE], "percentage": round(type_counts[TYPE_PARAPHRASE] / max(total, 1) * 100, 1)},
            TYPE_TRANSLATION: {"count": type_counts[TYPE_TRANSLATION], "percentage": round(type_counts[TYPE_TRANSLATION] / max(total, 1) * 100, 1)},
            TYPE_LOW_SIM: {"count": type_counts[TYPE_LOW_SIM], "percentage": round(type_counts[TYPE_LOW_SIM] / max(total, 1) * 100, 1)},
            TYPE_BOILERPLATE: {"count": bp_count, "percentage": bp_pct},
        },
        # 신규: 3-tier 점수
        "tiers": {
            "raw": raw_pct,
            "adjusted": adjusted_pct,
            "substantive": substantive_pct,
            "derived": derived_pct,
            "boilerplate": bp_pct,
        },
    }


def _empty_result(target_sents, ref_sents):
    """빈 결과"""
    total = len(target_sents) if target_sents else 0
    return {
        "summary": {
            "total_sentences": total,
            "high_count": 0,
            "medium_count": 0,
            "clean_count": total,
            "similarity_score": 0.0,
            "breakdown": {t: {"count": 0, "percentage": 0.0} for t in
                          (TYPE_IDENTICAL, TYPE_NEAR_COPY, TYPE_PARAPHRASE, TYPE_TRANSLATION, TYPE_LOW_SIM, TYPE_BOILERPLATE)},
            "tiers": {"raw": 0.0, "adjusted": 0.0, "substantive": 0.0, "derived": 0.0, "boilerplate": 0.0},
        },
        "matches": [],
        "target_sentences": target_sents or [],
        "reference_sentences": ref_sents or [],
    }
