"""
Compare 서비스 — 문서 텍스트 추출 + 검증 엔진
"""
import io
import json
import os
import re
from collections import Counter
from pathlib import Path

import fitz  # PyMuPDF
from docx import Document

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

    score = max(0, 100 - (summary["error"] * 10 + summary["warning"] * 3 + summary["suggestion"] * 1))
    return {"score": score, "summary": summary, "issues": issues}


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
    max_chars = params.get("max_chars", 80)
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
