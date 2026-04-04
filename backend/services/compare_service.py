"""
Compare 서비스 — 문서 텍스트 추출 + 검증 엔진 + AI 의미 분류
"""
import io
import json
import logging
import os
import re
from collections import Counter
from pathlib import Path
from typing import Optional

import httpx
import fitz  # PyMuPDF
from docx import Document

import config

logger = logging.getLogger(__name__)

RULES_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "compare-rules.json"


def extract_text(file_bytes: bytes, ext: str) -> dict:
    """확장자에 따라 텍스트 추출"""
    if ext == ".docx":
        return _extract_docx(file_bytes)
    elif ext == ".pdf":
        return _extract_pdf(file_bytes)
    else:
        raise ValueError(f"지원하지 않는 형식: {ext}")


def _extract_docx(file_bytes: bytes) -> dict:
    """python-docx로 단락별 텍스트 추출"""
    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return {"paragraphs": paragraphs, "page_count": None}


def _extract_pdf(file_bytes: bytes) -> dict:
    """PyMuPDF로 페이지별 → 단락별 텍스트 추출"""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    paragraphs = []
    for page in doc:
        blocks = page.get_text("blocks")  # (x0,y0,x1,y1,text,block_no,block_type)
        for b in blocks:
            if b[6] == 0:  # text block
                text = b[4].strip()
                if text:
                    paragraphs.append(text)
    page_count = len(doc)
    doc.close()
    return {"paragraphs": paragraphs, "page_count": page_count}


# ══════════════════════════════════════════
# 검증 엔진 (Validation Engine)
# ══════════════════════════════════════════

def load_rules() -> dict:
    """compare-rules.json 로드"""
    if not RULES_PATH.exists():
        return {"presets": {}, "active_preset": "technical"}
    with open(RULES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_rules(data: dict):
    """compare-rules.json 저장"""
    with open(RULES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def validate_paragraphs(paragraphs: list[str], preset: str | None = None) -> dict:
    """단락 배열에 대해 규칙 검증 수행 → 이슈 목록 반환"""
    rules_data = load_rules()
    preset = preset or rules_data.get("active_preset", "technical")
    preset_config = rules_data.get("presets", {}).get(preset)
    if not preset_config:
        return {"score": 100, "summary": {"error": 0, "warning": 0, "suggestion": 0}, "issues": []}

    rules = preset_config.get("rules", {})
    issues = []
    issue_counter = 0

    # 각 규칙 실행
    rule_runners = {
        "numbering_continuity": _check_numbering,
        "table_caption": _check_table_caption,
        "figure_caption": _check_figure_caption,
        "forbidden_terms": _check_forbidden_terms,
        "inconsistent_terms": _check_inconsistent_terms,
        "sentence_length": _check_sentence_length,
    }

    for rule_id, runner in rule_runners.items():
        rule_cfg = rules.get(rule_id, {})
        if not rule_cfg.get("enabled", False):
            continue
        severity = rule_cfg.get("severity", "warning")
        params = rule_cfg.get("params", {})
        found = runner(paragraphs, severity, params)
        for issue in found:
            issue["id"] = f"issue-{issue_counter}"
            issue["rule_id"] = rule_id
            issue_counter += 1
        issues.extend(found)

    # 점수 계산
    summary = {"error": 0, "warning": 0, "suggestion": 0}
    for iss in issues:
        sev = iss.get("severity", "warning")
        if sev in summary:
            summary[sev] += 1

    # ── 업계 표준 기반 스코어링 (Acrolinx/STE density 방식) ──
    # 기준: 단어 수 대비 가중 이슈 밀도 → 지수 감쇠 점수
    #   - 단어 수 기반: 빈 단락 부풀림 방지 (STE/Acrolinx 표준)
    #   - severity 가중치: error=5, warning=2, suggestion=1
    #   - density = weighted_issues / words_per_100
    #   - score = 100 × max(0, 1 - density / threshold)
    #   - threshold: density가 이 값에 도달하면 0점 (캘리브레이션 상수)
    SEVERITY_WEIGHT = {"error": 5, "warning": 2, "suggestion": 1}
    DENSITY_THRESHOLD = 5.0  # 100단어당 가중이슈 5개 → 0점
    MIN_WORDS = 200  # 최소 단어 수 하한 (짧은 문서 과대 감점 방지)

    total_words = max(sum(len(p.split()) for p in paragraphs), 1)
    effective_words = max(total_words, MIN_WORDS)
    weighted_issues = sum(SEVERITY_WEIGHT.get(iss.get("severity", "warning"), 1) for iss in issues)
    density = weighted_issues / (effective_words / 100)  # 100단어당 가중 이슈 수
    score = max(0, round(100 * max(0, 1 - density / DENSITY_THRESHOLD)))

    # 카테고리별 독립 점수 (Acrolinx 방식)
    CATEGORY_MAP = {
        "numbering_continuity": "structure",
        "table_caption": "structure",
        "figure_caption": "structure",
        "forbidden_terms": "terminology",
        "inconsistent_terms": "terminology",
        "sentence_length": "readability",
    }
    cat_weighted = {"structure": 0, "terminology": 0, "readability": 0}
    for iss in issues:
        cat = CATEGORY_MAP.get(iss.get("rule_id", ""), iss.get("category", ""))
        if cat in cat_weighted:
            cat_weighted[cat] += SEVERITY_WEIGHT.get(iss.get("severity", "warning"), 1)
    cat_density = {c: w / (effective_words / 100) for c, w in cat_weighted.items()}
    category_scores = {c: max(0, round(100 * max(0, 1 - d / DENSITY_THRESHOLD))) for c, d in cat_density.items()}

    # 인텔리전스 데이터
    structure = _analyze_structure(paragraphs)
    requirements = _classify_requirements(paragraphs)
    terms = _extract_terms(paragraphs)

    return {
        "score": score,
        "summary": summary,
        "issues": issues,
        "category_scores": category_scores,
        "word_count": total_words,
        "structure": structure,
        "requirements": requirements,
        "terms": terms,
    }


# ══════════════════════════════════════════
# 인텔리전스 분석 함수
# ══════════════════════════════════════════

# 헤딩 패턴: "1. Title", "1.2 Title", "1.2.3 Title" 등
_HEADING_PATTERN = re.compile(r"^(\d+(?:\.\d+)*)\.\s+(.+)")

# 표/그림 패턴
_TABLE_PATTERN = re.compile(r"(?:표|Table)\s*(\d+)[.:\s]*(.*)", re.IGNORECASE)
_FIGURE_PATTERN = re.compile(r"(?:그림|Figure)\s*(\d+)[.:\s]*(.*)", re.IGNORECASE)


def _analyze_structure(paragraphs: list[str]) -> dict:
    """문서 구조 분석 — 헤딩 트리, 섹션 분량, 표/그림 목록"""
    headings = []
    tables = []
    figures = []

    for i, para in enumerate(paragraphs):
        text = para.strip()
        if not text:
            continue

        # 헤딩 감지
        m = _HEADING_PATTERN.match(text)
        if m:
            num_str = m.group(1)
            title = m.group(2).strip()
            level = len(num_str.split("."))
            headings.append({
                "level": level,
                "number": num_str,
                "text": title,
                "paragraph_index": i,
            })

        # 표 감지
        tm = _TABLE_PATTERN.match(text)
        if tm:
            tables.append({
                "number": int(tm.group(1)),
                "caption": tm.group(2).strip()[:80],
                "paragraph_index": i,
            })

        # 그림 감지
        fm = _FIGURE_PATTERN.match(text)
        if fm:
            figures.append({
                "number": int(fm.group(1)),
                "caption": fm.group(2).strip()[:80],
                "paragraph_index": i,
            })

    # 섹션별 분량 계산 (헤딩 사이 단락 수)
    sections = []
    for hi, h in enumerate(headings):
        start = h["paragraph_index"]
        end = headings[hi + 1]["paragraph_index"] if hi + 1 < len(headings) else len(paragraphs)
        para_count = end - start
        # 문장 수 추정 (마침표 기준)
        section_text = " ".join(paragraphs[start:end])
        sentence_count = max(1, len(re.findall(r"[.!?。]\s", section_text)) + 1)
        sections.append({
            "heading": f"{h['number']}. {h['text']}",
            "paragraph_count": para_count,
            "sentence_count": sentence_count,
        })

    return {
        "headings": headings,
        "sections": sections,
        "tables": tables,
        "figures": figures,
        "total_paragraphs": len(paragraphs),
        "total_sentences": sum(
            max(1, len(re.findall(r"[.!?。]\s", p)) + 1)
            for p in paragraphs if p.strip()
        ),
    }


# 요구사항 분류 패턴 (영어 우선)
_REQ_PATTERNS = [
    ("shall", re.compile(r"\bshall\b|\bmust\b|\bis required to\b", re.IGNORECASE)),
    ("should", re.compile(r"\bshould\b|\bis recommended\b", re.IGNORECASE)),
    ("may", re.compile(r"\bmay\b|\bis permitted\b", re.IGNORECASE)),
    ("test_condition", re.compile(
        r"\bunder the condition\b|\btest at\b|\btest environment\b|\btested at\b|\btesting shall\b",
        re.IGNORECASE,
    )),
]


def _classify_requirements(paragraphs: list[str]) -> dict:
    """요구사항 문장 분류 — shall/should/may/test_condition/information"""
    counts = {"shall": 0, "should": 0, "may": 0, "test_condition": 0, "information": 0}
    details = []

    sentence_split = re.compile(r"(?<=[.!?。])\s+")

    for pi, para in enumerate(paragraphs):
        sentences = sentence_split.split(para.strip())
        for sent in sentences:
            sent = sent.strip()
            if len(sent) < 5:
                continue

            classified = False
            for req_type, pattern in _REQ_PATTERNS:
                if pattern.search(sent):
                    counts[req_type] += 1
                    details.append({
                        "type": req_type,
                        "text": sent[:120],
                        "paragraph_index": pi,
                    })
                    classified = True
                    break  # 첫 매칭만

            if not classified:
                counts["information"] += 1

    return {"counts": counts, "details": details}


# 규격 번호 패턴 (MIL-STD, MIL-DTL, AS, EN, KS, ISO, IEC, ASTM, SAE 등)
_SPEC_PATTERN = re.compile(
    r"\b(MIL-STD-\d+[A-Z]?(?:/\d+)?|MIL-DTL-\d+[A-Z]?|MIL-PRF-\d+[A-Z]?"
    r"|AS\s?\d{4,}[A-Z]?|EN\s?\d{4,}|KS\s?[A-Z]\s?\d{4,}"
    r"|ISO\s?\d{4,}(?:-\d+)?|IEC\s?\d{4,}(?:-\d+)?|ASTM\s?[A-Z]\d+"
    r"|SAE\s?(?:AS|AMS|J)\d+|DO-\d+[A-Z]?|RTCA\s?DO-\d+[A-Z]?)"
)

# 약어 패턴: 대문자 2~6글자 (문맥에서)
_ABBR_PATTERN = re.compile(r"\b([A-Z]{2,6})\b")

# 약어 정의 패턴: "Full Name (ABBR)" 또는 "ABBR (Full Name)"
_ABBR_DEF_PATTERN = re.compile(
    r"([A-Z][a-z]+(?:\s+[A-Za-z]+){1,5})\s*\(([A-Z]{2,6})\)"
    r"|([A-Z]{2,6})\s*\(([A-Z][a-z]+(?:\s+[A-Za-z]+){1,5})\)"
)

# 단위 패턴
_UNIT_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(kHz|MHz|GHz|Hz|V|mV|kV|A|mA|dB|dBm|dBμV|dBuV"
    r"|°C|°F|K|m|cm|mm|km|kg|g|mg|s|ms|μs|ns|W|mW|kW|Pa|kPa|MPa|psi|lbs?|ft|in)\b"
)

# SI 단위 집합
_SI_UNITS = {
    "Hz", "kHz", "MHz", "GHz", "V", "mV", "kV", "A", "mA",
    "dB", "dBm", "°C", "K", "m", "cm", "mm", "km", "kg", "g", "mg",
    "s", "ms", "W", "mW", "kW", "Pa", "kPa", "MPa",
}

# 흔한 영어 단어 (약어로 오인 방지)
_COMMON_WORDS = {
    "THE", "AND", "FOR", "NOT", "ARE", "BUT", "ALL", "ANY", "CAN",
    "HAD", "HER", "WAS", "ONE", "OUR", "OUT", "HAS", "HIS", "HOW",
    "ITS", "MAY", "NEW", "NOW", "OLD", "SEE", "WAY", "WHO", "DID",
    "GET", "LET", "SAY", "SHE", "TOO", "USE", "SET",
    # 규격 접두사 (MIL-STD 등의 부분 문자열)
    "MIL", "STD", "DTL", "PRF", "SAE", "AMS", "IEC", "ISO", "ASTM",
    "RTCA", "DO",
}


def _extract_terms(paragraphs: list[str]) -> dict:
    """문서 내 규격 번호, 약어, 단위를 추출한다."""
    full_text = "\n".join(paragraphs)

    # 규격 번호
    spec_counts: dict[str, dict] = {}
    for pi, para in enumerate(paragraphs):
        for m in _SPEC_PATTERN.finditer(para):
            spec_id = m.group(1).strip()
            if spec_id not in spec_counts:
                spec_counts[spec_id] = {"id": spec_id, "count": 0, "first_index": pi}
            spec_counts[spec_id]["count"] += 1

    # 약어 + 정의 (각 단락 내에서만 매칭하여 줄바꿈 섞임 방지)
    abbr_defs: dict[str, str] = {}
    for para in paragraphs:
        for m in _ABBR_DEF_PATTERN.finditer(para):
            if m.group(1) and m.group(2):
                abbr_defs[m.group(2)] = m.group(1).strip()
            elif m.group(3) and m.group(4):
                abbr_defs[m.group(3)] = m.group(4).strip()

    abbr_counts: dict[str, dict] = {}
    for pi, para in enumerate(paragraphs):
        for m in _ABBR_PATTERN.finditer(para):
            abbr = m.group(1)
            if abbr in _COMMON_WORDS or len(abbr) < 2:
                continue
            if abbr not in abbr_counts:
                abbr_counts[abbr] = {
                    "abbr": abbr,
                    "definition": abbr_defs.get(abbr, ""),
                    "count": 0,
                    "first_index": pi,
                }
            abbr_counts[abbr]["count"] += 1

    # 단위
    unit_counts: dict[str, dict] = {}
    for m in _UNIT_PATTERN.finditer(full_text):
        unit = m.group(2)
        if unit not in unit_counts:
            unit_counts[unit] = {
                "unit": unit,
                "count": 0,
                "si_compliant": unit in _SI_UNITS,
            }
        unit_counts[unit]["count"] += 1

    return {
        "specifications": sorted(spec_counts.values(), key=lambda x: -x["count"]),
        "abbreviations": sorted(
            [v for v in abbr_counts.values() if v["count"] >= 2],
            key=lambda x: -x["count"],
        ),
        "units": sorted(unit_counts.values(), key=lambda x: -x["count"]),
    }


# ── 규칙 구현 ──

# 번호 패턴: "1.", "1.2", "1.2.3", "(1)", "(가)" 등
_NUM_PATTERNS = [
    # N.N.N... 형 (최소 "1.")
    re.compile(r"^(\d+(?:\.\d+)*)\.\s"),
    # (N) 형
    re.compile(r"^\((\d+)\)\s"),
]


def _parse_section_number(text: str):
    """단락 시작에서 번호 추출 → (번호 문자열, 끝 위치) 또는 None"""
    for pat in _NUM_PATTERNS:
        m = pat.match(text)
        if m:
            return m.group(1), m.end() - 1  # char_end = 번호 끝
    return None


def _check_numbering(paragraphs, severity, params):
    """번호 체계 연속성 검사"""
    issues = []
    numbered = []  # (paragraph_index, number_str, level_tuple)

    for i, para in enumerate(paragraphs):
        result = _parse_section_number(para.strip())
        if result:
            num_str, end_pos = result
            parts = num_str.split(".")
            level = tuple(int(p) for p in parts)
            numbered.append((i, num_str, level, end_pos))

    # 같은 레벨(깊이) 내에서 연속성 검사
    by_depth = {}
    for entry in numbered:
        depth = len(entry[2])
        by_depth.setdefault(depth, []).append(entry)

    for depth, entries in by_depth.items():
        for j in range(1, len(entries)):
            prev = entries[j - 1]
            curr = entries[j]
            prev_level = prev[2]
            curr_level = curr[2]

            # 같은 부모 하위인지 확인
            if depth > 1 and prev_level[:-1] != curr_level[:-1]:
                continue

            expected_last = prev_level[-1] + 1
            actual_last = curr_level[-1]
            if actual_last != expected_last:
                num_text = curr[1] + "."
                issues.append({
                    "category": "structure",
                    "severity": severity,
                    "message": f"번호 체계 불연속: '{prev[1]}' 다음 '{curr[1]}'",
                    "paragraph_index": curr[0],
                    "char_start": 0,
                    "char_end": len(num_text),
                    "context": paragraphs[curr[0]][:40],
                    "suggestion": f"{'.'.join(str(x) for x in curr_level[:-1] + (expected_last,))}로 수정하세요",
                })

    return issues


def _check_caption(paragraphs, severity, params, label_ko, label_en):
    """표/그림 캡션 번호 연속성 + 본문 참조 확인"""
    issues = []
    pattern = re.compile(
        rf"(?:{re.escape(label_ko)}|{re.escape(label_en)})\s*(\d+)", re.IGNORECASE
    )

    # 캡션 수집
    captions = []
    full_text = "\n".join(paragraphs)

    for i, para in enumerate(paragraphs):
        for m in pattern.finditer(para):
            num = int(m.group(1))
            captions.append((i, num, m.start(), m.end()))

    # 번호 연속성
    seen_numbers = sorted(set(c[1] for c in captions))
    for j in range(1, len(seen_numbers)):
        if seen_numbers[j] != seen_numbers[j - 1] + 1:
            # 누락된 번호 찾기
            missing = seen_numbers[j - 1] + 1
            # 다음 캡션의 위치에서 경고
            for cap in captions:
                if cap[1] == seen_numbers[j]:
                    issues.append({
                        "category": "structure",
                        "severity": severity,
                        "message": f"{label_ko} 번호 불연속: {label_ko} {missing} 누락",
                        "paragraph_index": cap[0],
                        "char_start": cap[2],
                        "char_end": cap[3],
                        "context": paragraphs[cap[0]][:40],
                        "suggestion": f"{label_ko} 번호를 순서대로 정리하세요",
                    })
                    break

    # 본문 참조 확인: 캡션이 있는데 본문에서 참조가 없는 경우
    for cap in captions:
        num = cap[1]
        ref_pattern = re.compile(
            rf"(?:{re.escape(label_ko)}|{re.escape(label_en)})\s*{num}(?!\d)", re.IGNORECASE
        )
        ref_count = len(ref_pattern.findall(full_text))
        if ref_count <= 1:
            issues.append({
                "category": "structure",
                "severity": severity,
                "message": f"{label_ko} {num}: 본문에서 참조되지 않음",
                "paragraph_index": cap[0],
                "char_start": cap[2],
                "char_end": cap[3],
                "context": paragraphs[cap[0]][:40],
                "suggestion": f"본문에서 {label_ko} {num}을(를) 참조하세요",
            })

    return issues


def _check_table_caption(paragraphs, severity, params):
    return _check_caption(paragraphs, severity, params, "표", "Table")


def _check_figure_caption(paragraphs, severity, params):
    return _check_caption(paragraphs, severity, params, "그림", "Figure")


def _check_forbidden_terms(paragraphs, severity, params):
    """금지 용어 감지"""
    issues = []
    terms = params.get("terms", [])
    if not terms:
        return issues

    for term_entry in terms:
        term = term_entry.get("term", "")
        replacement = term_entry.get("replacement", "")
        if not term:
            continue

        for i, para in enumerate(paragraphs):
            start = 0
            while True:
                pos = para.find(term, start)
                if pos == -1:
                    break
                issues.append({
                    "category": "terminology",
                    "severity": severity,
                    "message": f'금지 용어: "{term}" → "{replacement}"',
                    "paragraph_index": i,
                    "char_start": pos,
                    "char_end": pos + len(term),
                    "context": para[max(0, pos - 10):pos + len(term) + 10],
                    "suggestion": f'"{replacement}"(으)로 대체하세요',
                })
                start = pos + len(term)

    return issues


def _check_inconsistent_terms(paragraphs, severity, params):
    """동일 그룹 내 복수 용어 사용 감지"""
    issues = []
    groups = params.get("groups", [])
    if not groups:
        return issues

    full_text = "\n".join(paragraphs)

    for group in groups:
        if len(group) < 2:
            continue

        # 각 용어 등장 횟수
        counts = Counter()
        for term in group:
            counts[term] = full_text.count(term)

        used = [t for t in group if counts[t] > 0]
        if len(used) < 2:
            continue

        # 최빈 용어 결정
        preferred = max(used, key=lambda t: counts[t])
        non_preferred = [t for t in used if t != preferred]

        for term in non_preferred:
            for i, para in enumerate(paragraphs):
                start = 0
                while True:
                    pos = para.find(term, start)
                    if pos == -1:
                        break
                    issues.append({
                        "category": "terminology",
                        "severity": severity,
                        "message": f'용어 불일치: "{term}" — "{preferred}"(으)로 통일 권장',
                        "paragraph_index": i,
                        "char_start": pos,
                        "char_end": pos + len(term),
                        "context": para[max(0, pos - 10):pos + len(term) + 10],
                        "suggestion": f'"{preferred}"(으)로 통일하세요',
                    })
                    start = pos + len(term)

    return issues


def _check_sentence_length(paragraphs, severity, params):
    """문장 길이 초과 감지"""
    issues = []
    max_chars = params.get("max_chars", 120)
    sentence_split = re.compile(r"(?<=[.!?。])\s*")

    for i, para in enumerate(paragraphs):
        sentences = sentence_split.split(para)
        offset = 0
        for sent in sentences:
            sent_stripped = sent.strip()
            if len(sent_stripped) > max_chars:
                # 문장 시작 위치 계산
                char_start = para.find(sent_stripped, offset)
                if char_start == -1:
                    char_start = offset
                issues.append({
                    "category": "readability",
                    "severity": severity,
                    "message": f"문장 길이 초과: {len(sent_stripped)}자 (최대 {max_chars}자)",
                    "paragraph_index": i,
                    "char_start": char_start,
                    "char_end": char_start + len(sent_stripped),
                    "context": sent_stripped[:40] + ("..." if len(sent_stripped) > 40 else ""),
                    "suggestion": "문장을 분리하세요",
                })
            offset += len(sent)

    return issues


# ══════════════════════════════════════════
# AI 의미 분류 (Phase 6)
# ══════════════════════════════════════════

VALID_TAGS = {"EDITORIAL", "CLARIFICATION", "STRICTER", "MORE_LENIENT", "EXPANDED", "RESTRUCTURED"}

_DEFAULT_SYSTEM_PROMPT = """당신은 기술문서 변경사항을 분류하는 전문가입니다.
두 문서 버전 간의 변경 구간을 받아, 각 변경의 의미적 유형을 분류합니다.

## 분류 태그 (정확히 6종 중 하나를 선택)

- EDITORIAL: 편집상 변경. 오타 수정, 표현 다듬기, 접속사/어미 변경 등. 의미에 영향 없음.
- CLARIFICATION: 기존 내용의 표현을 명확하게 보완. 약어 풀네임 병기, 용어 설명 추가 등. 의미 자체는 동일.
- STRICTER: 요구사항/기준/제약이 더 엄격해짐. 시스템이 달성해야 할 의무가 강화된 경우.
- MORE_LENIENT: 요구사항/기준/제약이 완화됨. 사용자에게 허용된 범위가 넓어지거나 의무가 줄어든 경우.
- EXPANDED: 기존에 없던 새 내용/범위/기능 추가. 새 섹션, 새 요구사항, 적용 범위 확대.
- RESTRUCTURED: 내용은 동일하나 위치/구조/번호 변경. 섹션 이동, 번호 재부여 등.

## 판단 기준

1. 수치 변경은 "의무 vs 허용" 관점으로 판단:
   - 시스템이 달성해야 할 의무가 늘어남 → STRICTER
     예: "응답 시간 3초→1초" (더 빠르게 응답해야 함), "동시 접속 50명→100명" (더 많은 사용자를 지원해야 함), "보관 기간 5년→10년" (더 오래 보관해야 함)
   - 사용자/운영자에 대한 제약이 줄어듦 → MORE_LENIENT
     예: "백업 매일→매주" (백업 빈도 의무 감소), "테스트 커버리지 80%→70%" (기준 완화), "업로드 제한 10MB→50MB" (사용자 허용 범위 확대)
2. 단순 표현 변경(~하며/~하고, 이를/이 문제를)은 EDITORIAL
3. 새 문장/절이 추가되어 기존 범위를 넘어서면 EXPANDED
4. 약어에 풀네임을 병기하는 것은 CLARIFICATION
5. 선택지가 추가되어 사용자의 선택 범위가 넓어진 경우("온프레미스"→"온프레미스 또는 클라우드")는 MORE_LENIENT

## 출력 규칙

각 변경에 대해 반드시 아래 JSON 형식으로 응답하세요:
- tag: 6종 태그 중 하나 (대문자 영어)
- confidence: 0.0~1.0 사이의 확신도
- explanation: 한국어 1문장으로 분류 이유 설명"""

_FEW_SHOT_EXAMPLES = """## 예시

입력:
[
  {"index": 0, "type": "modified", "text_a": "시스템 가용성은 99.5%를 보장한다.", "text_b": "시스템 가용성은 99.9%를 보장한다."},
  {"index": 1, "type": "modified", "text_a": "관리자는 사용자 권한을 설정한다.", "text_b": "관리자(Admin)는 사용자 권한을 설정한다."},
  {"index": 2, "type": "added", "text_a": null, "text_b": "4.1 감사 로그: 모든 데이터 변경 이력을 90일간 보관한다."},
  {"index": 3, "type": "modified", "text_a": "시스템은 동시 접속 사용자 200명을 지원해야 한다.", "text_b": "시스템은 동시 접속 사용자 500명을 지원해야 한다."},
  {"index": 4, "type": "modified", "text_a": "첨부파일 최대 크기는 5MB이다.", "text_b": "첨부파일 최대 크기는 20MB이다."}
]

출력:
[
  {"index": 0, "tag": "STRICTER", "confidence": 0.95, "explanation": "가용성 기준이 99.5%에서 99.9%로 강화되었습니다."},
  {"index": 1, "tag": "CLARIFICATION", "confidence": 0.9, "explanation": "관리자에 영문 약어(Admin)를 병기하여 의미를 명확히 했습니다."},
  {"index": 2, "tag": "EXPANDED", "confidence": 0.95, "explanation": "감사 로그 보관 요구사항이 새로 추가되었습니다."},
  {"index": 3, "tag": "STRICTER", "confidence": 0.9, "explanation": "시스템이 지원해야 하는 동시 접속 수가 200명에서 500명으로 강화되었습니다."},
  {"index": 4, "tag": "MORE_LENIENT", "confidence": 0.9, "explanation": "사용자가 업로드할 수 있는 최대 파일 크기가 5MB에서 20MB로 완화되었습니다."}
]"""

_JSON_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "index": {"type": "integer"},
            "tag": {
                "type": "string",
                "enum": ["EDITORIAL", "CLARIFICATION", "STRICTER",
                         "MORE_LENIENT", "EXPANDED", "RESTRUCTURED"]
            },
            "confidence": {"type": "number"},
            "explanation": {"type": "string"}
        },
        "required": ["index", "tag", "confidence", "explanation"]
    }
}


def _get_system_prompt() -> str:
    """관리자 커스텀 프롬프트 또는 기본 프롬프트 반환"""
    custom = getattr(config, "COMPARE_AI_SYSTEM_PROMPT", "")
    return custom if custom else _DEFAULT_SYSTEM_PROMPT


def _get_model() -> str:
    """Compare 전용 모델 또는 기본 모델 반환"""
    model = getattr(config, "COMPARE_AI_MODEL", "")
    return model if model else config.OLLAMA_MODEL


def _build_prompt(changes: list[dict]) -> str:
    """Few-shot + 변경 구간 데이터 → 사용자 프롬프트 조립"""
    items = []
    for c in changes:
        item = {"index": c["index"], "type": c["type"]}
        item["text_a"] = c.get("text_a")
        item["text_b"] = c.get("text_b")
        items.append(item)

    return f"""{_FEW_SHOT_EXAMPLES}

---

아래 변경 구간을 분류하세요:

{json.dumps(items, ensure_ascii=False, indent=2)}"""


async def _call_ollama_classify(changes: list[dict]) -> list[dict]:
    """Ollama 구조화 출력으로 변경 구간 분류"""
    model = _get_model()
    system = _get_system_prompt()
    prompt = _build_prompt(changes)
    temperature = getattr(config, "COMPARE_AI_TEMPERATURE", 0)
    if temperature is None:
        temperature = 0
    timeout = getattr(config, "COMPARE_AI_TIMEOUT", 60)
    if timeout is None:
        timeout = 60

    payload = {
        "model": model,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "format": _JSON_SCHEMA,
        "options": {"temperature": temperature},
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{config.OLLAMA_URL}/api/generate",
            json=payload,
            timeout=float(timeout),
        )
        resp.raise_for_status()
        data = resp.json()
        raw = data.get("response", "")

    parsed = json.loads(raw)
    if not isinstance(parsed, list):
        raise ValueError("LLM 응답이 배열 형식이 아닙니다")
    return parsed


def _validate_classifications(results: list[dict], expected_count: int) -> list[dict]:
    """분류 결과 검증 및 정규화"""
    validated = []
    result_map = {r.get("index"): r for r in results if isinstance(r, dict)}

    for i in range(expected_count):
        r = result_map.get(i)
        if r and r.get("tag") in VALID_TAGS:
            validated.append({
                "index": i,
                "tag": r["tag"],
                "confidence": max(0.0, min(1.0, float(r.get("confidence", 0.5)))),
                "explanation": str(r.get("explanation", "")),
            })
        else:
            validated.append({
                "index": i,
                "tag": "UNKNOWN",
                "confidence": 0.0,
                "explanation": "분류 실패",
            })

    return validated


async def classify_changes(changes: list[dict]) -> list[dict]:
    """
    변경 구간 목록을 AI로 의미 분류.
    배치 분할 → Ollama 호출 → 결과 병합 → 검증.
    """
    if not changes:
        return []

    batch_size = getattr(config, "COMPARE_AI_BATCH_SIZE", 20)
    if batch_size is None:
        batch_size = 20
    all_results = []

    for i in range(0, len(changes), batch_size):
        batch = changes[i:i + batch_size]

        try:
            results = await _call_ollama_classify(batch)
            all_results.extend(results)
        except Exception as e:
            logger.warning("AI 분류 배치 %d 실패, 재시도: %s", i // batch_size, e)
            # 1회 재시도
            try:
                results = await _call_ollama_classify(batch)
                all_results.extend(results)
            except Exception as e2:
                logger.error("AI 분류 배치 %d 재시도 실패: %s", i // batch_size, e2)
                # 실패한 배치의 항목은 UNKNOWN으로 채움
                for c in batch:
                    all_results.append({
                        "index": c["index"],
                        "tag": "UNKNOWN",
                        "confidence": 0.0,
                        "explanation": f"분류 실패: {e2}",
                    })

    return _validate_classifications(all_results, len(changes))
