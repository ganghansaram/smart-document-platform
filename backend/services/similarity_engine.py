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
DEFAULT_THRESHOLD_MEDIUM = 0.75

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

# ── Winnowing 파라미터 (config에서 런타임 오버라이드 가능) ──
def _winnow_k():
    return getattr(config, "VERIFY_SIMILARITY_WINNOW_K", 25)

def _winnow_window():
    return getattr(config, "VERIFY_SIMILARITY_WINNOW_WINDOW", 4)

# ── 분류 임계값 (Phase 1.1 — 하드코딩 제거) ──
def _para_fp_max():
    return getattr(config, "VERIFY_SIMILARITY_PARA_FP_MAX", 0.40)

def _trans_fp_max():
    return getattr(config, "VERIFY_SIMILARITY_TRANS_FP_MAX", 0.10)

# ── 짧은 매칭 필터 (Phase 1.3) ──
def _min_match_words():
    return getattr(config, "VERIFY_SIMILARITY_MIN_MATCH_WORDS", 8)

# ── Cross-language sem 임계값 (R1 캘리브레이션) ──
def _cross_lang_sem_th():
    return getattr(config, "VERIFY_SIMILARITY_CROSS_LANG_SEM_TH", 0.65)

# ── 검사 설정 기본값 (Phase 1.4) ──
def _exclusion_defaults():
    return getattr(config, "VERIFY_SIMILARITY_DEFAULTS", {
        "exclude_boilerplate": True,
        "exclude_short_match": True,
        "exclude_toc": True,
        "exclude_caption": True,
        "exclude_cited_quote": False,
        "exclude_table_structural": True,
    })

# ── 정형 구문 허용 목록 + 패턴 (lazy load) ──
_boilerplate_phrases = None
_boilerplate_patterns = None


def _load_boilerplate():
    """정형 구문 허용 목록을 로드한다 (phrases + patterns)."""
    global _boilerplate_phrases, _boilerplate_patterns
    if _boilerplate_phrases is not None:
        return _boilerplate_phrases

    bp_path = Path(__file__).parent.parent.parent / "data" / "boilerplate-phrases.json"
    try:
        with open(bp_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _boilerplate_phrases = [p.lower() for p in data.get("phrases", [])]
        _boilerplate_patterns = [re.compile(p, re.IGNORECASE) for p in data.get("patterns", [])]
        logger.info("정형 구문 로드: phrases=%d, patterns=%d",
                    len(_boilerplate_phrases), len(_boilerplate_patterns))
    except Exception as e:
        logger.warning("정형 구문 로드 실패: %s", e)
        _boilerplate_phrases = []
        _boilerplate_patterns = []
    return _boilerplate_phrases


def _load_boilerplate_patterns():
    """정형 구문 정규식 패턴 (header/caption 제외용)."""
    if _boilerplate_patterns is None:
        _load_boilerplate()
    return _boilerplate_patterns or []


# ══════════════════════════════════════════
# 메인 진입점
# ══════════════════════════════════════════

def run_similarity(
    target_text: str,
    reference_text: str,
    threshold_high: Optional[float] = None,
    threshold_medium: Optional[float] = None,
    target_markdown: Optional[str] = None,
    reference_markdown: Optional[str] = None,
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

    # 0. 문장 분리 (markdown이 있으면 페이지 마커 추출)
    target_sents, target_page_breaks = split_sentences(
        target_markdown or target_text, extract_pages=bool(target_markdown)
    )
    ref_sents, ref_page_breaks = split_sentences(
        reference_markdown or reference_text, extract_pages=bool(reference_markdown)
    )

    if not target_sents or not ref_sents:
        return _empty_result(target_sents, ref_sents, target_page_breaks, ref_page_breaks)

    M, N = len(target_sents), len(ref_sents)
    logger.info("유사도 검사 시작: 대상 %d문장, 참조 %d문장", M, N)

    # 1. 정형 구문 + exclusion 검출 (Phase 1.4)
    boilerplate_indices = _detect_boilerplate(target_sents)
    exclusion_map = _detect_exclusions(target_sents)
    # 백엔드 자동 제외 인덱스: BP + ALWAYS_SKIP
    auto_skip_indices = set(boilerplate_indices) | {
        idx for idx, reason in exclusion_map.items() if reason in ALWAYS_SKIP_REASONS
    }

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
        if ti in auto_skip_indices:
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
    need_embedding_t = set(range(M)) - used_targets_l1 - auto_skip_indices
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
                cross_lang = _is_cross_language(target_sents[ti], ref_sents[ri])
                match_type = _classify_match(fp_score, sem_score, th_high, th_medium, cross_lang)
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
            if ti in auto_skip_indices:
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
            cross_lang = _is_cross_language(target_sents[ti], ref_sents[ri])
            match_type = _classify_match(fp_score, sem_score, th_high, th_medium, cross_lang)
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

    # 텍스트 채우기 + 하위 호환 필드 + 카테고리 exclusion_reason (Phase 1.4)
    for m in all_matches:
        ti, ri = m["target_idx"], m["ref_idx"]
        m["target_text"] = target_sents[ti]
        m["ref_text"] = ref_sents[ri] if ri >= 0 else ""
        m["severity"] = SEVERITY_MAP[m["type"]]
        # 하위 호환
        m["level"] = LEVEL_COMPAT[m["type"]]
        m["similarity"] = m["scores"].get("semantic") or m["scores"].get("fingerprint") or 0
        m["method"] = m["detection_layer"]
        # exclusion_reason: 카테고리 기반만 우선 부여 (short_match는 병합 후 적용)
        m["exclusion_reason"] = exclusion_map.get(ti)

    # 구간 병합
    merged = _merge_adjacent(all_matches)

    # Phase 1.3: 짧은 매칭 필터 — 병합 후 매칭 영역의 전체 단어 수 기준
    # 마크다운 줄바꿈으로 분할된 짧은 조각도 병합되면 의미 있는 매칭일 수 있음
    min_words = _min_match_words()
    for m in merged:
        if m.get("exclusion_reason"):
            continue  # 카테고리 제외 우선
        if len(m["target_text"].split()) < min_words:
            m["exclusion_reason"] = "short_match"

    # 6. 통계 산출 (exclusion_map 전달 — 분모 보정 + breakdown)
    summary = _compute_summary(merged, bp_matches, target_sents, exclusion_map)

    return {
        "summary": summary,
        "matches": merged,
        "target_sentences": target_sents,
        "reference_sentences": ref_sents,
        "display_html_a": _build_tagged_html(target_sents, target_page_breaks),
        "display_html_b": _build_tagged_html(ref_sents, ref_page_breaks),
    }


# ══════════════════════════════════════════
# 분류 로직
# ══════════════════════════════════════════

_KOREAN_RE = re.compile(r'[\uac00-\ud7a3]')


def _is_cross_language(target_text: str, ref_text: str) -> bool:
    """대상 vs 참조 문장이 다른 언어(스크립트)인지 감지.

    Translation 분류는 실제 언어 차이가 있을 때만 적용되어야 한다.
    Paraphrase의 fp < 0.10은 흔하므로 (영어→영어 중량 의역도 가능),
    스크립트 차이로 cross-language 여부를 명확히 판정한다.
    """
    t_kor = bool(_KOREAN_RE.search(target_text))
    r_kor = bool(_KOREAN_RE.search(ref_text))
    return t_kor != r_kor


def _classify_match(fp_score: float, sem_score: float, th_high: float,
                    th_medium: float = None,
                    cross_language: bool = False) -> str:
    """L1(fingerprint) + L3(semantic) 점수를 조합하여 매칭 유형을 결정한다.

    Plan-38 Phase 1.1 — 4분기 명시화 + cross-language 감지:
      - identical:    fp ≥ 0.85
      - near_copy:    fp 0.40~0.85 + sem ≥ th_high
      - translation:  fp < 0.10 + sem ≥ th_high + **cross_language=True** (다른 언어)
      - paraphrase:   fp < para_max + sem ≥ th_high (의역, 동일 언어)
      - near_copy(약):fp ≥ 0.40 + sem ≥ th_medium
      - low_sim:      sem ≥ 0.65

    cross_language=False면 fp가 낮아도 paraphrase로 분류 — translation 오분류 방지.
    """
    if th_medium is None:
        th_medium = getattr(config, "VERIFY_SIMILARITY_THRESHOLD_MEDIUM",
                            DEFAULT_THRESHOLD_MEDIUM)
    para_max = _para_fp_max()
    trans_max = _trans_fp_max()

    if fp_score >= 0.85:
        return TYPE_IDENTICAL
    # near_copy 우선 (어휘 일치도 높을 때, high threshold)
    if fp_score >= 0.40 and sem_score >= th_high:
        return TYPE_NEAR_COPY
    # translation: 다른 언어 + 어휘 거의 0 + 의미 cross-lang 임계값 이상
    # R1 캘리브레이션: bge-m3 cross-lingual 점수 분포 반영 (Korean-English 정상 0.65~0.75)
    cross_lang_th = _cross_lang_sem_th()
    if cross_language and fp_score < trans_max and sem_score >= cross_lang_th:
        return TYPE_TRANSLATION
    # paraphrase: 어휘 낮음 + 의미 medium 이상 (동일 언어 의역)
    # heavily paraphrased 영문도 bge-m3 sem_score가 0.75~0.85 구간에 분포
    if fp_score < para_max and sem_score >= th_medium:
        return TYPE_PARAPHRASE
    # near_copy 약화 (의미 medium이지만 어휘 일치도 ≥ 0.40)
    if fp_score >= 0.40 and sem_score >= th_medium:
        return TYPE_NEAR_COPY
    # 약한 유사
    if sem_score >= 0.65:
        return TYPE_LOW_SIM
    return TYPE_LOW_SIM


def _detect_boilerplate(sentences: list) -> set:
    """정형 구문이 포함된 문장 인덱스를 반환한다.

    Plan-38 Phase 1.2 — 문자 인덱스 커버리지 기반 (중복 누적 방지).
    이전 버전: `match_len += len(phrase)` → 겹치는 구문이 누적되어 비율 >1.0 가능
    개선: 문자 인덱스 set으로 정확한 커버리지 계산.
    """
    phrases = _load_boilerplate()
    if not phrases:
        return set()

    bp_threshold = getattr(config, "VERIFY_SIMILARITY_BOILERPLATE_TH", 0.40)
    indices = set()
    for i, sent in enumerate(sentences):
        sent_lower = sent.lower()
        if len(sent_lower) == 0:
            continue
        # 문자 인덱스 커버리지 (중복 제거)
        covered = set()
        for phrase in phrases:
            start = 0
            while True:
                pos = sent_lower.find(phrase, start)
                if pos == -1:
                    break
                for j in range(pos, pos + len(phrase)):
                    covered.add(j)
                start = pos + 1
        # 임계값 이상이 정형 구문으로 구성되면 boilerplate 판정 (기본 40%)
        if len(covered) / len(sent_lower) >= bp_threshold:
            indices.add(i)

    if indices:
        logger.info("정형 구문 감지: %d개 문장", len(indices))
    return indices


# ══════════════════════════════════════════
# Phase 1.4: exclusion_reason 검출 (검사 설정 5+2 옵션)
# ══════════════════════════════════════════

# 정규식: 한 번 컴파일
_TOC_HEADING_RE = re.compile(r'^\s*\d+(\.\d+)*\s+[A-Z가-힣]')
_REFERENCES_HEADER_RE = re.compile(
    r'^\s*(References|Bibliography|참고\s*문헌|인용\s*문헌)\b',
    re.IGNORECASE
)
_CAPTION_RE = re.compile(
    r'^\s*(Figure|Fig\.?|Table|Tbl\.?|그림|표)\s+\d+',
    re.IGNORECASE
)
_CITED_QUOTE_PATTERNS = [
    re.compile(r'"[^"]{15,}"'),         # ASCII 인용 (15자+)
    re.compile(r'\u201c[^\u201d]{15,}\u201d'),  # 유니코드 따옴표
    re.compile(r'\u300e[^\u300f]+\u300f'),       # 한국어 책 인용 『...』
    re.compile(r'\[\d+(?:[,\s\d]+)?\]'),         # [1] [1,2] 인용 마커
    re.compile(r'\([A-Z][a-z]+(?:\s+(?:and|&|et\s+al\.?)\s+[A-Z][a-z]+)?,?\s*\d{4}\)'),  # (Author, 2020)
]


def _is_new_section_header(sent: str) -> bool:
    """새 섹션 헤더 패턴 (참고문헌 종료 감지용)."""
    s = sent.strip()
    return bool(re.match(r'^\d+\.?\s+[A-Z가-힣]{2,}', s)) or \
           bool(re.match(r'^[A-Z]{3,}(\s+[A-Z]+){0,3}$', s))


def _detect_cited_quote(sent: str) -> bool:
    for pat in _CITED_QUOTE_PATTERNS:
        if pat.search(sent):
            return True
    return False


def _detect_spec_only(sent: str) -> bool:
    """규격 번호만으로 구성된 짧은 문장."""
    sent_strip = sent.strip()
    words = sent_strip.split()
    if len(words) > 5:
        return False
    spec_matches = list(_spec_regex.finditer(sent_strip))
    if not spec_matches:
        return False
    spec_chars = sum(m.end() - m.start() for m in spec_matches)
    return spec_chars / max(len(sent_strip), 1) >= 0.40


# ── Plan-52: GFM 테이블 행 검출 + 구조성 판정 ──
def _is_table_row(sent: str) -> bool:
    """문장이 GFM 테이블 행 형태인지 판정.

    조건: '|' 로 시작/종료 + 최소 2개 셀 (파이프 ≥3).
    예: '| 항목 | 값 |' → True, '일반 문장입니다.' → False.
    """
    s = sent.strip()
    return s.startswith('|') and s.endswith('|') and s.count('|') >= 3


def _parse_table_cells(row: str) -> list:
    """GFM 테이블 행 → 셀 텍스트 배열 (양쪽 공백 제거)."""
    s = row.strip()
    if s.startswith('|'):
        s = s[1:]
    if s.endswith('|'):
        s = s[:-1]
    return [c.strip() for c in s.split('|')]


def _is_short_cell_row(sent: str) -> bool:
    """모든 셀이 짧은 (≤3 단어) 테이블 행인지 — 구조성 강한 신호."""
    if not _is_table_row(sent):
        return False
    cells = _parse_table_cells(sent)
    if not cells:
        return False
    return all(len(c.split()) <= 3 for c in cells)


def _detect_table_structural(sentences: list) -> set:
    """문맥 기반 테이블 구조 행 인덱스 집합.

    검출 규칙:
      1. 연속 테이블 행 블록의 **첫 행** → 헤더 (구조성)
      2. 모든 셀이 짧은 행 → 구조성 (위치 무관)
      3. 비테이블 문장은 무시

    반환: {sent_idx, ...}
    """
    structural: set = set()
    n = len(sentences)
    i = 0
    while i < n:
        if _is_table_row(sentences[i]):
            # 테이블 블록 시작 — 첫 행은 헤더로 간주
            structural.add(i)
            j = i + 1
            while j < n and _is_table_row(sentences[j]):
                if _is_short_cell_row(sentences[j]):
                    structural.add(j)
                j += 1
            i = j
        else:
            i += 1
    return structural


def _detect_exclusions(sentences: list) -> dict:
    """
    문장별 exclusion_reason 검출 (Plan §6.4).

    반환: {sent_idx: reason_str}
    Reasons:
      - "toc_heading"        목차/장절 헤딩
      - "references_section" 참고문헌 섹션 이후 (백엔드 자동)
      - "caption"            표/그림 캡션
      - "cited_quote"        인용·출처 표시
      - "spec_number_only"   규격 번호 단독 매칭 (백엔드 자동)
      - "boilerplate_pattern" boilerplate-phrases.json patterns 매칭
    """
    exclusions = {}
    bp_patterns = _load_boilerplate_patterns()
    in_references = False
    ref_started_at = -1

    for i, sent in enumerate(sentences):
        sent_strip = sent.strip()

        # references_section 진입/종료 추적
        if in_references:
            if (i - ref_started_at) >= 1 and _is_new_section_header(sent_strip):
                in_references = False
            else:
                exclusions[i] = "references_section"
                continue

        if _REFERENCES_HEADER_RE.match(sent_strip):
            in_references = True
            ref_started_at = i
            exclusions[i] = "references_section"
            continue

        # 우선순위 (먼저 매칭되는 것 적용):
        # 1. boilerplate patterns (Figure/Table 헤더 등)
        for pat in bp_patterns:
            if pat.match(sent_strip):
                exclusions[i] = "boilerplate_pattern"
                break
        if i in exclusions:
            continue

        # 2. caption (정규식 패턴 미스 시 보강)
        if _CAPTION_RE.match(sent_strip):
            exclusions[i] = "caption"
            continue

        # 3. toc_heading (1.1 SCOPE 형태)
        if _TOC_HEADING_RE.match(sent_strip):
            exclusions[i] = "toc_heading"
            continue

        # 4. spec_number_only
        if _detect_spec_only(sent_strip):
            exclusions[i] = "spec_number_only"
            continue

        # 5. cited_quote (마지막 — 다른 패턴이 없을 때)
        if _detect_cited_quote(sent_strip):
            exclusions[i] = "cited_quote"
            continue

    # 6. Plan-52: table_structural (테이블 헤더 + 짧은 셀 행)
    table_struct_indices = _detect_table_structural(sentences)
    for idx in table_struct_indices:
        if idx not in exclusions:  # 다른 사유가 이미 있으면 보존
            exclusions[idx] = "table_structural"

    if exclusions:
        from collections import Counter
        cnt = Counter(exclusions.values())
        logger.info("exclusion 검출: %s", dict(cnt))
    return exclusions


# 백엔드 자동 처리 (사용자 토글 X) — 항상 매칭에서 제외
ALWAYS_SKIP_REASONS = {"references_section", "spec_number_only", "boilerplate_pattern"}

# 사용자 토글 가능 (기본 ON) — 매칭은 수행, exclusion_reason 부여
TOGGLEABLE_EXCLUSIONS = {"toc_heading", "caption", "cited_quote", "table_structural"}


# ══════════════════════════════════════════
# Phase 2: 5단계 신호등 (Plan §7.1)
# ══════════════════════════════════════════

# Turnitin 산업 표준 5단계 — Blue / Green / Yellow / Orange / Red
VERDICT_BAND_NAMES = ["blue", "green", "yellow", "orange", "red"]
VERDICT_LABELS_KO = {
    "blue":   "매칭 없음",
    "green":  "양호",
    "yellow": "검토 필요",
    "orange": "상당량 매칭",
    "red":    "위험",
}


def _compute_verdict_band(score: float) -> str:
    """유사율(%)을 5단계 신호등 색상으로 매핑.

    bands = [green_min, yellow_min, orange_min, red_min] (기본 [0, 25, 50, 75])
      - blue:   score == 0 (또는 < bands[0])
      - green:  bands[0] < score < bands[1]
      - yellow: bands[1] ≤ score < bands[2]
      - orange: bands[2] ≤ score < bands[3]
      - red:    bands[3] ≤ score
    """
    bands = getattr(config, "VERIFY_SIMILARITY_VERDICT_BANDS", [0, 25, 50, 75])
    if score <= bands[0]:
        return "blue"
    if score < bands[1]:
        return "green"
    if score < bands[2]:
        return "yellow"
    if score < bands[3]:
        return "orange"
    return "red"


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
    k = _winnow_k()
    w = _winnow_window()
    normalized = re.sub(r'\s+', '', text.lower())
    if len(normalized) < k:
        # 너무 짧으면 전체를 하나의 fingerprint로
        return {hash(normalized)} if normalized else set()

    # k-gram hash 생성
    hashes = []
    for i in range(len(normalized) - k + 1):
        kgram = normalized[i:i + k]
        hashes.append(hash(kgram))

    if not hashes:
        return set()

    # sliding window minimum selection
    fingerprints = set()
    for i in range(len(hashes) - w + 1):
        window = hashes[i:i + w]
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

def split_sentences(text: str, extract_pages: bool = False) -> tuple:
    """텍스트를 문장 단위로 분리한다.

    Args:
        text: 분리할 텍스트 (markdown일 경우 <!-- Page N --> 마커 포함 가능)
        extract_pages: True면 페이지 마커를 추출하여 page_breaks 반환

    Returns:
        (sentences, page_breaks) 튜플.
        page_breaks: {sent_idx: page_num} 딕셔너리 (페이지 경계 문장 인덱스 → 페이지 번호)
    """
    if not text or not text.strip():
        return [], {}

    page_breaks = {}
    current_page = None
    next_page = None
    _page_re = re.compile(r'<!--\s*Page\s+(\d+)\s*-->')
    # Plan-52: GFM 테이블 구분선 (| --- | --- |) 은 의미 없는 표시용 → 항상 제외
    _gfm_sep_re = re.compile(r'^\|[\s\-:|]+\|$')

    paragraphs = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        # 페이지 마커 감지
        if extract_pages:
            pm = _page_re.match(stripped)
            if pm:
                next_page = int(pm.group(1))
                continue
            # 수평선 (--- 등)은 페이지 마커 뒤에 오면 건너뜀
            if next_page is not None and re.match(r'^---+$', stripped):
                continue
        # Plan-52: GFM 테이블 구분선 제외 (문장 아님, 시각/매칭 모두 무관)
        if _gfm_sep_re.match(stripped):
            continue
        paragraphs.append(stripped)
        # 이 단락의 첫 문장이 새 페이지의 시작
        if next_page is not None:
            page_breaks[len(paragraphs) - 1] = next_page
            current_page = next_page
            next_page = None

    sentences = []
    sent_page_breaks = {}
    for pi, para in enumerate(paragraphs):
        sent_start_idx = len(sentences)
        sents = _sentence_split(para)
        sents = [s for s in sents if len(s.split()) >= 2]
        sentences.extend(sents)
        # 이 단락이 페이지 경계이면 첫 문장에 마킹
        if pi in page_breaks and sents:
            sent_page_breaks[sent_start_idx] = page_breaks[pi]

    return sentences, sent_page_breaks


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
                and 0 <= m["ref_idx"] - prev.get("ref_idx_end", prev["ref_idx"]) <= 2
                # Plan-52: exclusion_reason 다르면 병합 차단 (헤더+일반 문장 inflation 방지)
                and m.get("exclusion_reason") == prev.get("exclusion_reason")):
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


def _compute_summary(matches: list, bp_matches: list, target_sents: list,
                     exclusion_map: dict = None) -> dict:
    """통계를 산출한다.

    Plan-38 Phase 1.2 + 1.4:
      - adjusted_pct 분모: total - 활성 제외 sentence index 집합 (중복 제거)
      - 분자: 활성 제외 카테고리 매칭은 카운트에서 빠짐
      - exclusion_breakdown 신규 필드
    """
    if exclusion_map is None:
        exclusion_map = {}
    defaults = _exclusion_defaults()
    total = len(target_sents)

    # exclusion_reason → default key 매핑
    excl_to_key = {
        "boilerplate": "exclude_boilerplate",
        "boilerplate_pattern": "exclude_boilerplate",
        "short_match": "exclude_short_match",
        "toc_heading": "exclude_toc",
        "caption": "exclude_caption",
        "cited_quote": "exclude_cited_quote",
        "table_structural": "exclude_table_structural",  # Plan-52
    }

    def _is_active_exclusion(reason: str) -> bool:
        """주어진 exclusion_reason이 현재 설정에서 활성(점수 제외)인가."""
        if not reason:
            return False
        if reason in ALWAYS_SKIP_REASONS:
            return True  # 백엔드 자동 제외
        return defaults.get(excl_to_key.get(reason, ""), False)

    # ── 활성 제외 sentence index 집합 (중복 제거) ──
    bp_indices = {bp["target_idx"] for bp in bp_matches}
    active_excluded_idx = set()
    if defaults.get("exclude_boilerplate", True):
        active_excluded_idx |= bp_indices
    for idx, reason in exclusion_map.items():
        if _is_active_exclusion(reason):
            active_excluded_idx.add(idx)

    # 매칭 sentence 카운트 (병합된 sentence count 합산, 활성 제외는 빠짐)
    type_counts = {t: 0 for t in (TYPE_IDENTICAL, TYPE_NEAR_COPY, TYPE_PARAPHRASE,
                                    TYPE_TRANSLATION, TYPE_LOW_SIM)}
    excluded_match_sents = 0
    for m in matches:
        sc = _match_sentence_count(m)
        reason = m.get("exclusion_reason")
        # 활성 제외 카테고리이거나 short_match이면 분자에서 제외
        if _is_active_exclusion(reason):
            excluded_match_sents += sc
            continue
        if m["type"] in type_counts:
            type_counts[m["type"]] += sc

    bp_count = len(bp_matches)
    matched_count = sum(type_counts.values())
    excluded_total = len(active_excluded_idx)
    clean_count = max(0, total - matched_count - excluded_total)

    # 3-tier 점수 산출
    substantive = type_counts[TYPE_IDENTICAL] + type_counts[TYPE_NEAR_COPY]
    derived = type_counts[TYPE_PARAPHRASE] + type_counts[TYPE_TRANSLATION]

    # 분모: 전체 - 활성 제외 인덱스 (중복 제거)
    effective_total = max(total - excluded_total, 1)

    raw_pct = round((matched_count + excluded_match_sents) / max(total, 1) * 100, 1)
    substantive_pct = round(substantive / effective_total * 100, 1)
    derived_pct = round(derived / effective_total * 100, 1)
    bp_pct = round(bp_count / max(total, 1) * 100, 1)
    # Plan-50 Phase 1: v3 공식 통일 — 의역 가중치 0.5 → 1.0 (Copyleaks 표준).
    # 분자 = substantive(동일+거의동일) + derived(의역+번역). 약한 유사는 미반영.
    adjusted_pct = round((substantive + derived) / effective_total * 100, 1)
    # 안전장치: 100% 초과 방지 (가능성 낮지만 _match_sentence_count 오버랩 시)
    adjusted_pct = min(adjusted_pct, 100.0)
    excluded_pct = round(excluded_total / max(total, 1) * 100, 1)

    # 기존 호환 필드
    high_count = type_counts[TYPE_IDENTICAL] + type_counts[TYPE_NEAR_COPY]
    medium_count = type_counts[TYPE_PARAPHRASE] + type_counts[TYPE_TRANSLATION] + type_counts[TYPE_LOW_SIM]

    # exclusion_breakdown (Phase 1.4 신규)
    from collections import Counter
    excl_counter = Counter(exclusion_map.values())
    short_match_count = sum(1 for m in matches
                            if m.get("exclusion_reason") == "short_match")
    exclusion_breakdown = {
        "boilerplate": bp_count,
        "toc_heading": excl_counter.get("toc_heading", 0),
        "caption": excl_counter.get("caption", 0),
        "references_section": excl_counter.get("references_section", 0),
        "cited_quote": excl_counter.get("cited_quote", 0),
        "spec_number_only": excl_counter.get("spec_number_only", 0),
        "boilerplate_pattern": excl_counter.get("boilerplate_pattern", 0),
        "short_match": short_match_count,
        "table_structural": excl_counter.get("table_structural", 0),  # Plan-52
    }

    # ── Phase 2: 5단계 신호등 verdict (Plan §7.1) ──
    verdict_band = _compute_verdict_band(adjusted_pct)
    verdict_label = VERDICT_LABELS_KO[verdict_band]

    # ── Phase 2: sources 구조 (1:1 단일 출처, 1:N 확장 대비 Plan §7.3) ──
    # 활성 제외가 아닌 매칭만 출처 기여로 카운트
    matched_sents = sum(_match_sentence_count(m) for m in matches
                        if not _is_active_exclusion(m.get("exclusion_reason")))
    matched_words = sum(len(m.get("target_text", "").split()) for m in matches
                        if not _is_active_exclusion(m.get("exclusion_reason")))
    sources = []
    if matched_sents > 0:
        sources.append({
            "id": 1,
            "name": "",  # 프론트가 파일명 채움 (백엔드는 파일명 모름)
            "matched_sents": matched_sents,
            "matched_words": matched_words,
            "match_pct": adjusted_pct,
        })

    return {
        # 기존 호환
        "total_sentences": total,
        "high_count": high_count,
        "medium_count": medium_count,
        "clean_count": clean_count,
        "similarity_score": adjusted_pct,
        # 유형별 breakdown (호환 유지)
        "breakdown": {
            TYPE_IDENTICAL: {"count": type_counts[TYPE_IDENTICAL], "percentage": round(type_counts[TYPE_IDENTICAL] / max(total, 1) * 100, 1)},
            TYPE_NEAR_COPY: {"count": type_counts[TYPE_NEAR_COPY], "percentage": round(type_counts[TYPE_NEAR_COPY] / max(total, 1) * 100, 1)},
            TYPE_PARAPHRASE: {"count": type_counts[TYPE_PARAPHRASE], "percentage": round(type_counts[TYPE_PARAPHRASE] / max(total, 1) * 100, 1)},
            TYPE_TRANSLATION: {"count": type_counts[TYPE_TRANSLATION], "percentage": round(type_counts[TYPE_TRANSLATION] / max(total, 1) * 100, 1)},
            TYPE_LOW_SIM: {"count": type_counts[TYPE_LOW_SIM], "percentage": round(type_counts[TYPE_LOW_SIM] / max(total, 1) * 100, 1)},
            TYPE_BOILERPLATE: {"count": bp_count, "percentage": bp_pct},
        },
        # 3-tier 점수 (호환 유지 + excluded 신규)
        "tiers": {
            "raw": raw_pct,
            "adjusted": adjusted_pct,
            "substantive": substantive_pct,
            "derived": derived_pct,
            "boilerplate": bp_pct,
            "excluded": excluded_pct,
        },
        # 신규: exclusion_reason별 카운트 (Phase 1.4)
        "exclusion_breakdown": exclusion_breakdown,
        # Phase 2: 5단계 신호등 + sources
        "verdict": verdict_band,           # "blue"/"green"/"yellow"/"orange"/"red"
        "verdict_label": verdict_label,    # 한국어 라벨 (예: "양호")
        "sources": sources,
    }


def _build_tagged_html(sentences: list, page_breaks: dict = None) -> str:
    """문장 배열을 data-sent-idx 태깅된 HTML로 변환한다.

    백엔드에서 확정적으로 태깅하므로 프론트에서 매핑 불필요.
    page_breaks가 있으면 해당 sent_idx 앞에 페이지 구분선을 삽입한다.

    Plan-52: 연속 GFM 테이블 행은 <table> 로 그룹화하여 시각 보존.
    각 행은 <tr data-sent-idx="i" class="sim-sent"> 로 태깅됨.
    """
    import html as html_mod
    parts = []
    n = len(sentences)
    i = 0
    while i < n:
        # 페이지 구분선 (블록 진입 직전)
        if page_breaks and i in page_breaks:
            parts.append(f'<div class="cp-page-break"><span>Page {page_breaks[i]}</span></div>')

        sent = sentences[i]
        if _is_table_row(sent):
            # 연속 테이블 블록 수집 — 페이지 경계가 가르면 분리
            j = i + 1
            while j < n and _is_table_row(sentences[j]):
                if page_breaks and j in page_breaks:
                    break
                j += 1
            parts.append(_render_table_block(sentences, i, j, html_mod))
            i = j
        else:
            escaped = html_mod.escape(sent)
            parts.append(f'<p data-sent-idx="{i}" class="sim-sent">{escaped}</p>')
            i += 1
    return "\n".join(parts)


def _render_table_block(sentences: list, start: int, end: int, html_mod) -> str:
    """[start, end) 범위 sentence 들을 <table> HTML 로 변환.

    각 행 = <tr data-sent-idx="i" class="sim-sent">.
    첫 행은 thead/<th>, 나머지는 tbody/<td>.
    """
    rows_html = []
    for i in range(start, end):
        cells = _parse_table_cells(sentences[i])
        cell_tag = 'th' if i == start else 'td'
        cells_html = ''.join(
            f'<{cell_tag}>{html_mod.escape(c)}</{cell_tag}>' for c in cells
        )
        rows_html.append(
            f'<tr data-sent-idx="{i}" class="sim-sent">{cells_html}</tr>'
        )
    if not rows_html:
        return ""
    if len(rows_html) == 1:
        return f'<table class="sim-md-table">{rows_html[0]}</table>'
    return (
        f'<table class="sim-md-table">'
        f'<thead>{rows_html[0]}</thead>'
        f'<tbody>{"".join(rows_html[1:])}</tbody>'
        f'</table>'
    )


def _empty_result(target_sents, ref_sents, target_page_breaks=None, ref_page_breaks=None):
    """빈 결과 (Phase 2: verdict/sources/exclusion_breakdown 신규 필드 포함)"""
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
            "tiers": {"raw": 0.0, "adjusted": 0.0, "substantive": 0.0, "derived": 0.0, "boilerplate": 0.0, "excluded": 0.0},
            "exclusion_breakdown": {k: 0 for k in ("boilerplate", "toc_heading", "caption",
                                                    "references_section", "cited_quote",
                                                    "spec_number_only", "boilerplate_pattern", "short_match",
                                                    "table_structural")},
            "verdict": "blue",
            "verdict_label": VERDICT_LABELS_KO["blue"],
            "sources": [],
        },
        "matches": [],
        "target_sentences": target_sents or [],
        "reference_sentences": ref_sents or [],
        "display_html_a": _build_tagged_html(target_sents or [], target_page_breaks),
        "display_html_b": _build_tagged_html(ref_sents or [], ref_page_breaks),
    }
