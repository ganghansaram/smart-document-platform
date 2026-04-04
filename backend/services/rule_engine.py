"""
규칙 엔진 — JSON 스키마 기반 규칙 로더 + 매처 + 리포터
Phase 5: 6개 타입(pattern/metric/sequence/section/cross_ref/dictionary) 지원
"""
import json
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

RULES_DIR = Path(__file__).resolve().parent.parent / "rules"

# ── 규칙 로드 ────────────────────────────────────

_rules_cache: dict[str, list[dict]] = {}


def load_all_rules(force: bool = False) -> list[dict]:
    """backend/rules/*.json에서 모든 규칙 로드 (캐싱)"""
    if _rules_cache.get("all") and not force:
        return _rules_cache["all"]

    all_rules = []
    for fp in sorted(RULES_DIR.glob("*.json")):
        if fp.name.startswith("_"):
            continue
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            rules = data.get("rules", [])
            all_rules.extend(rules)
        except Exception as e:
            logger.warning("규칙 파일 로드 실패: %s — %s", fp.name, e)

    _rules_cache["all"] = all_rules
    logger.info("규칙 엔진: %d개 규칙 로드 (%s)", len(all_rules),
                ", ".join(f.name for f in RULES_DIR.glob("*.json") if not f.name.startswith("_")))
    return all_rules


def get_rules_by_source(source: str) -> list[dict]:
    """특정 출처의 규칙만 반환"""
    return [r for r in load_all_rules() if r.get("source") == source]


def get_rule_by_id(rule_id: str) -> Optional[dict]:
    """ID로 규칙 조회"""
    for r in load_all_rules():
        if r["id"] == rule_id:
            return r
    return None


# ── 규칙 실행 ────────────────────────────────────

# 문장 분리 패턴
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(text: str) -> list[str]:
    """텍스트를 문장 단위로 분리"""
    parts = _SENT_SPLIT.split(text.strip())
    return [s for s in parts if s.strip()]


def run_rules(paragraphs: list[str], enabled_rules: list[dict],
              legacy_runners: dict = None) -> list[dict]:
    """활성화된 규칙 목록을 실행하고 이슈 목록 반환

    Args:
        paragraphs: 검사 대상 단락 배열
        enabled_rules: 활성화된 규칙 정의 목록 (JSON 스키마 규격)
        legacy_runners: 기존 규칙 함수 맵 {legacy_id: function}
    """
    issues = []
    legacy_runners = legacy_runners or {}

    for rule in enabled_rules:
        rule_id = rule["id"]
        legacy_id = rule.get("legacy_id")

        # legacy 규칙은 기존 함수에 위임
        if legacy_id and legacy_id in legacy_runners:
            runner = legacy_runners[legacy_id]
            severity = rule.get("severity", "warning")
            params = rule.get("params", {})
            found = runner(paragraphs, severity, params)
            for iss in found:
                iss["rule_id"] = rule_id
                iss["source"] = rule.get("source", "custom")
                if "category" not in iss:
                    iss["category"] = rule.get("category", "")
            issues.extend(found)
            continue

        # 새 엔진 타입별 디스패치
        rule_type = rule.get("type", "")
        try:
            if rule_type == "pattern":
                found = _run_pattern(paragraphs, rule)
            elif rule_type == "metric":
                found = _run_metric(paragraphs, rule)
            elif rule_type == "sequence":
                found = _run_sequence(paragraphs, rule)
            elif rule_type == "section":
                found = _run_section(paragraphs, rule)
            elif rule_type == "cross_ref":
                found = _run_cross_ref(paragraphs, rule)
            elif rule_type == "dictionary":
                found = _run_dictionary(paragraphs, rule)
            else:
                logger.warning("알 수 없는 규칙 타입: %s (rule=%s)", rule_type, rule_id)
                continue

            for iss in found:
                iss["rule_id"] = rule_id
                iss["source"] = rule.get("source", "custom")
                iss["category"] = rule.get("category", "")
                iss["severity"] = rule.get("severity", "warning")
            issues.extend(found)
        except Exception as e:
            logger.warning("규칙 실행 오류: %s — %s", rule_id, e)

    return issues


# ── 타입별 매처 ────────────────────────────────────

def _run_pattern(paragraphs: list[str], rule: dict) -> list[dict]:
    """정규식 패턴 매칭"""
    issues = []
    params = rule.get("params", {})
    patterns = params.get("patterns", [])
    exceptions = set(params.get("exceptions", []))
    scope = params.get("scope", "sentence")
    min_occ = params.get("min_occurrences", 1)
    msg_tpl = rule.get("message_template", "패턴 매칭: '{match}'")

    compiled = []
    for p in patterns:
        try:
            compiled.append(re.compile(p, re.IGNORECASE))
        except re.error:
            logger.warning("잘못된 정규식: %s (rule=%s)", p, rule["id"])

    for i, para in enumerate(paragraphs):
        targets = _split_sentences(para) if scope == "sentence" else [para]

        for target in targets:
            matches = []
            for regex in compiled:
                for m in regex.finditer(target):
                    matched = m.group(0)
                    # 예외 목록 체크
                    if matched.lower() in {e.lower() for e in exceptions}:
                        continue
                    matches.append((m.start(), m.end(), matched))

            if len(matches) >= min_occ:
                for start, end, matched in matches:
                    issues.append({
                        "message": msg_tpl.replace("{match}", matched),
                        "paragraph_index": i,
                        "char_start": start,
                        "char_end": end,
                        "context": target[max(0, start - 20):end + 20],
                    })

    return issues


_PROCEDURAL_PATTERN = re.compile(r"^\s*(\d+[\.\)]\s|[a-z][\.\)]\s|•\s|[-–]\s|Step\s)", re.IGNORECASE)


def _is_procedural_paragraph(para: str) -> bool:
    """절차문 단락인지 판별 (번호/불릿 목록으로 시작)"""
    return bool(_PROCEDURAL_PATTERN.match(para.strip()))


def _run_metric(paragraphs: list[str], rule: dict) -> list[dict]:
    """수치 기반 검사 (길이, 카운트)"""
    issues = []
    params = rule.get("params", {})
    target = params.get("target", "sentence_chars")
    max_val = params.get("max")
    min_val = params.get("min")
    sent_filter = params.get("sentence_filter")  # "procedural" | "descriptive" | None
    msg_tpl = rule.get("message_template", "수치 초과: {count} (최대 {max})")

    for i, para in enumerate(paragraphs):
        if target in ("sentence_words", "sentence_chars"):
            # 절차/설명 필터링
            if sent_filter:
                is_proc = _is_procedural_paragraph(para)
                if sent_filter == "procedural" and not is_proc:
                    continue
                if sent_filter == "descriptive" and is_proc:
                    continue

            sentences = _split_sentences(para)
            for sent in sentences:
                if target == "sentence_words":
                    count = len(sent.split())
                else:
                    count = len(sent)

                if max_val is not None and count > max_val:
                    issues.append({
                        "message": msg_tpl.replace("{count}", str(count)).replace("{max}", str(max_val)),
                        "paragraph_index": i,
                        "char_start": para.find(sent[:20]) if len(sent) > 20 else 0,
                        "char_end": min(len(para), (para.find(sent[:20]) if len(sent) > 20 else 0) + len(sent)),
                        "context": sent[:50],
                    })

        elif target == "paragraph_sentences":
            count = len(_split_sentences(para))
            if max_val is not None and count > max_val:
                issues.append({
                    "message": msg_tpl.replace("{count}", str(count)).replace("{max}", str(max_val)),
                    "paragraph_index": i,
                    "char_start": 0,
                    "char_end": len(para),
                    "context": para[:50],
                })

        elif target == "paragraph_words":
            count = len(para.split())
            if max_val is not None and count > max_val:
                issues.append({
                    "message": msg_tpl.replace("{count}", str(count)).replace("{max}", str(max_val)),
                    "paragraph_index": i,
                    "char_start": 0,
                    "char_end": len(para),
                    "context": para[:50],
                })

    return issues


def _run_sequence(paragraphs: list[str], rule: dict) -> list[dict]:
    """번호/순서 연속성 검사"""
    # 기존 numbering_continuity가 legacy로 처리되므로,
    # 여기서는 max_depth 같은 추가 검사만 수행
    issues = []
    params = rule.get("params", {})
    element = params.get("element", "heading")
    max_depth = params.get("max_depth", 6)
    msg_tpl = rule.get("message_template", "번호 깊이 초과: '{number}' ({depth}단계)")

    heading_pattern = re.compile(r"^(\d+(?:\.\d+)*)\.\s+")

    if element == "heading":
        for i, para in enumerate(paragraphs):
            m = heading_pattern.match(para.strip())
            if m:
                num = m.group(1)
                depth = len(num.split("."))
                if depth > max_depth:
                    issues.append({
                        "message": msg_tpl.replace("{number}", num).replace("{depth}", str(depth)),
                        "paragraph_index": i,
                        "char_start": 0,
                        "char_end": m.end(),
                        "context": para[:50],
                    })

    return issues


def _run_section(paragraphs: list[str], rule: dict) -> list[dict]:
    """필수 섹션 존재 / 섹션 내 금지 키워드 검사"""
    issues = []
    params = rule.get("params", {})
    msg_tpl = rule.get("message_template", "{section}")

    # 필수 섹션 존재 검사
    required = params.get("required_sections", [])
    if required:
        full_text_lines = [(i, p.strip()) for i, p in enumerate(paragraphs)]
        for sec in required:
            pattern = sec.get("pattern", "")
            title = sec.get("title", sec.get("number", ""))
            if not pattern:
                continue
            regex = re.compile(pattern, re.IGNORECASE)
            found = any(regex.match(line) for _, line in full_text_lines)
            if not found:
                issues.append({
                    "message": msg_tpl.replace("{section}", f"{sec.get('number', '')}. {title}"),
                    "paragraph_index": 0,
                    "char_start": 0,
                    "char_end": 0,
                    "context": "",
                })

    # 섹션 내 금지 키워드 검사
    target_sections = params.get("target_sections", [])
    forbidden_kw = params.get("forbidden_keywords", [])
    if target_sections and forbidden_kw:
        heading_pattern = re.compile(r"^(\d+)(?:\.\d+)*\.\s+")
        # 각 단락이 어느 섹션에 속하는지 판별
        current_section = None
        for i, para in enumerate(paragraphs):
            m = heading_pattern.match(para.strip())
            if m:
                current_section = m.group(1)  # 최상위 섹션 번호

            if current_section in target_sections:
                for kw in forbidden_kw:
                    kw_pattern = re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
                    for m_kw in kw_pattern.finditer(para):
                        issues.append({
                            "message": msg_tpl.replace("{keyword}", kw).replace("{section}", f"Section {current_section}"),
                            "paragraph_index": i,
                            "char_start": m_kw.start(),
                            "char_end": m_kw.end(),
                            "context": para[max(0, m_kw.start() - 20):m_kw.end() + 20],
                        })

    return issues


def _run_cross_ref(paragraphs: list[str], rule: dict) -> list[dict]:
    """교차참조 정합성 검사"""
    issues = []
    params = rule.get("params", {})
    ref_pattern_str = params.get("ref_pattern", "")
    check_existence = params.get("check_existence", False)
    check_order = params.get("check_order", False)
    msg_tpl = rule.get("message_template", "교차참조 이슈: '{ref}'")

    if not ref_pattern_str:
        return issues

    ref_regex = re.compile(ref_pattern_str, re.IGNORECASE)

    # 모든 참조와 대상을 수집
    refs = []  # (paragraph_index, number, type_label)
    targets = []  # (paragraph_index, number, type_label)

    for i, para in enumerate(paragraphs):
        for m in ref_regex.finditer(para):
            groups = m.groups()
            if len(groups) >= 2:
                type_label, number = groups[0], groups[1]
            elif len(groups) == 1:
                type_label, number = "", groups[0]
            else:
                continue

            # 단락 시작이 "Figure N." 또는 "Table N." 형태면 대상(정의)
            stripped = para.strip()
            if stripped.startswith(m.group(0)):
                targets.append((i, number, type_label))
            else:
                refs.append((i, number, type_label, m.start(), m.end()))

    if check_existence:
        target_numbers = {(t[2].lower(), t[1]) for t in targets}
        for ref_idx, num, tl, start, end in refs:
            if (tl.lower(), num) not in target_numbers:
                issues.append({
                    "message": msg_tpl.replace("{ref}", f"{tl} {num}".strip()).replace("{type}", tl),
                    "paragraph_index": ref_idx,
                    "char_start": start,
                    "char_end": end,
                    "context": paragraphs[ref_idx][max(0, start - 10):end + 10],
                })

    return issues


def _run_dictionary(paragraphs: list[str], rule: dict) -> list[dict]:
    """사전 기반 검사 (약어 첫 사용 등)"""
    issues = []
    params = rule.get("params", {})
    mode = params.get("mode", "blacklist")
    msg_tpl = rule.get("message_template", "사전 검사: '{abbr}'")
    sug_tpl = rule.get("suggestion_template", "")

    if mode == "first_use":
        # 약어 첫 사용 시 풀네임 존재 검사
        abbr_pattern = re.compile(r"\b([A-Z]{2,})\b")
        seen_abbrs = {}  # abbr -> first paragraph index
        defined_abbrs = set()

        # 정의 패턴: "Full Name (ABBR)" 또는 "ABBR (Full Name)"
        def_pattern1 = re.compile(r"\([A-Z]{2,}\)")  # (...ABBR...)
        def_pattern2 = re.compile(r"\b[A-Z]{2,}\b\s*\([^)]+\)")  # ABBR (...)

        for i, para in enumerate(paragraphs):
            # 정의 패턴 먼저 수집
            for m in def_pattern1.finditer(para):
                abbr = m.group(0).strip("()")
                defined_abbrs.add(abbr)
            for m in def_pattern2.finditer(para):
                abbr_m = re.match(r"([A-Z]{2,})", m.group(0))
                if abbr_m:
                    defined_abbrs.add(abbr_m.group(1))

            # 약어 사용 추적
            for m in abbr_pattern.finditer(para):
                abbr = m.group(1)
                if abbr not in seen_abbrs:
                    seen_abbrs[abbr] = (i, m.start(), m.end())

        # 정의 없는 약어 보고
        common_abbrs = {"WARNING", "CAUTION", "NOTE", "AND", "THE", "FOR", "NOT",
                        "ALL", "BUT", "ARE", "WAS", "HAS", "HAD", "MAY", "CAN",
                        "SHALL", "WILL", "SCOPE", "NOTES", "APPLICABLE", "DOCUMENTS",
                        "REQUIREMENTS", "VERIFICATION", "PACKAGING", "II", "III", "IV",
                        "SI", "AC", "DC", "RF", "IF", "OR", "NO", "ON", "OFF", "IN", "OF",
                        # 규격번호 접두사 (MIL-STD-xxx 등에서 추출되는 오탐 방지)
                        "MIL", "STD", "HDBK", "DTL", "PRF", "QPL", "SAE", "AMS",
                        "ASTM", "IEEE", "ISO", "IEC", "ANSI", "DID", "CDRL",
                        "ASD", "STE", "DO", "RTCA", "NASA", "FAA", "DoD", "DOD"}
        for abbr, (pi, start, end) in seen_abbrs.items():
            if abbr in defined_abbrs or abbr in common_abbrs:
                continue
            if len(abbr) <= 2:
                continue
            issues.append({
                "message": msg_tpl.replace("{abbr}", abbr),
                "paragraph_index": pi,
                "char_start": start,
                "char_end": end,
                "context": paragraphs[pi][max(0, start - 15):end + 15],
                "suggestion": sug_tpl.replace("{abbr}", abbr) if sug_tpl else "",
            })

    return issues
